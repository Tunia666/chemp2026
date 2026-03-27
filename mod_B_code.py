#!/usr/bin/env python
# coding: utf-8

# # Модуль Б: Монитор безопасности
# ## Задание соревнований «КиберИммунный Светофор»
# 
# ---
# 
# В этом модуле вам **дан готовый каркас системы**, но три ключевые функции монитора не реализованы.
# 
# **Ваша задача:**
# 1. **Б.1** — Реализовать политику whitelist (проверку допустимых состояний)
# 2. **Б.2** — Добавить детальное логирование нарушений
# 3. **Б.3** — Реализовать защиту от «аварийного мигания» (rate limiting)
# 
# 
# 
# ---
# 
# ### Почему это важно?
# 
# Монитор безопасности — это **доверенная вычислительная база (TCB)**.
# Если монитор неверно реализован, система уязвима. Даже безобидный баг в мониторе
# может привести к тому, что **запрещённое состояние пройдёт**, и светофор
# откроет движение одновременно для автомобилей и пешеходов.
# 
# **Последствие:** реальная угроза жизни людей на перекрёстке.

# In[9]:


# ===== ГОТОВЫЙ КОД СИСТЕМЫ (не изменять) =====
from queue import Queue
from threading import Thread
import time
from datetime import datetime
from collections import deque

# Допустимые состояния светофора (whitelist)
# (car_red, car_yellow, car_green, ped_green)
ALLOWED_STATES = [
    (True, False, False, True),  # Красный авто + Зелёный пешеход
    (False, False, True, False),  # Зелёный авто
    (False, True, False, False),  # Жёлтый авто
    (True, False, False, False),  # Красный авто
    (False, False, False, False),  # Всё выключено
]


class Event:
    def __init__(self, source, destination, operation, params):
        self.source = source
        self.destination = destination
        self.operation = operation
        self.params = params
        self.timestamp = datetime.now()

    def __repr__(self):
        src = type(self.source).__name__ if self.source else "None"
        return f"Event(op={self.operation!r}, from={src}, params={self.params})"


class LightsGPIO:
    def __init__(self):
        self.events_queue = Queue()
        self.current_state = (False, False, False, False)

    def set_state(self, state):
        self.current_state = state
        car_red, car_yellow, car_green, ped_green = state
        r = "🔴" if car_red else "⚫"
        y = "🟡" if car_yellow else "⚫"
        g = "🟢" if car_green else "⚫"
        p = "🟢" if ped_green else "🔴"
        print(f"[GPIO] Авто:{r}{y}{g}  Пешеход:{p}  ← {state}")

    def run(self):
        while True:
            event = self.events_queue.get()
            if event is None:
                break
            if event.operation == "set_state":
                self.set_state(event.params["state"])


class ControlSystem:
    def __init__(self, monitor):
        self.monitor = monitor
        self.events_queue = Queue()

    def request_state_change(self, new_state):
        event = Event(
            source=self,
            destination=None,
            operation="set_state",
            params={"state": new_state},
        )
        self.monitor.events_queue.put(event)


print("Базовые компоненты загружены.")


# ---
# ## Задание Б.1: Политика whitelist
# 
# Реализуйте класс `Monitor` с функцией проверки допустимых состояний.
# 
# **Требования:**
# - Монитор должен проверять каждое событие по всем зарегистрированным политикам
# - Ваша политика должна отклонять недопустимые состояния светофора
# - Допустимые состояния определены в `ALLOWED_STATES`

# In[11]:


class Monitor:
    """Монитор безопасности — доверенная компонента (TCB)."""

    def __init__(self, lights: LightsGPIO):
        self.lights = lights
        self.events_queue = Queue()
        self.policies = []
        self.violations_log = []

    def add_policy(self, policy_func):
        """Добавить политику безопасности."""
        self.policies.append(policy_func)

    def _check_policies(self, event) -> bool:
        """Проверяет событие по всем зарегистрированным политикам."""
        for policy in self.policies:
            if not policy(event):
                return False
        return True

    def log_violation(self, event, reason=""):
        """Записывает нарушение (реализуется в Б.2)."""
        print(f"[НАРУШЕНИЕ] {reason}")
        self.violations_log.append({"reason": reason, "event": repr(event)})

    def run(self):
        """Основной цикл монитора."""
        while True:
            event = self.events_queue.get()
            if event is None:
                break
            if self._check_policies(event):
                self.lights.events_queue.put(event)
            else:
                self.log_violation(event, "Политика безопасности запрещает это событие")


# ─────────────────────────────────────────────────────
# Задание Б.1: Реализуйте политику whitelist
# ─────────────────────────────────────────────────────
def monitor_policy(event) -> bool:
    """Политика безопасности: проверка допустимости запрошенного состояния.
    Должна вернуть True, если событие допустимо, False — если нет."""
    if event.operation != "set_state":
        return False

    state = event.params.get("state")
    return state in ALLOWED_STATES


print("Monitor определён. Запустите тест ниже.")


# In[12]:


# ===== ТЕСТ Б.1 =====

def run_system_short(test_states):
    """Вспомогательная функция: запустить систему и отправить состояния."""
    lights = LightsGPIO()
    monitor = Monitor(lights)
    monitor.add_policy(monitor_policy)

    Thread(target=lights.run, daemon=True).start()
    Thread(target=monitor.run, daemon=True).start()

    ctrl = ControlSystem(monitor)
    for state in test_states:
        ctrl.request_state_change(state)
        time.sleep(0.15)

    return lights, monitor


def test_b1_whitelist_pass():
    """Монитор пропускает все допустимые состояния."""
    for state in ALLOWED_STATES:
        lights, monitor = run_system_short([state])
        assert monitor.violations_log == [], \
            f"Монитор не должен блокировать допустимое состояние {state}. " \
            f"Нарушений: {monitor.violations_log}"
    print(f"✓ Тест Б.1а: все {len(ALLOWED_STATES)} допустимых состояния пропущены")


def test_b1_whitelist_block():
    """Монитор блокирует запрещённые состояния."""
    forbidden_states = [
        (False, False, True, True),  # ОПАСНО: зелёный авто + зелёный пешеход
        (True, True, False, False),  # Некорректно: красный + жёлтый
        (True, False, True, False),  # Некорректно: красный + зелёный
        (False, True, True, False),  # Некорректно: жёлтый + зелёный
    ]

    for state in forbidden_states:
        lights, monitor = run_system_short([state])
        initial_state = (False, False, False, False)
        assert lights.current_state == initial_state, \
            f"Монитор ДОЛЖЕН заблокировать {state}! Текущее состояние: {lights.current_state}"
        assert len(monitor.violations_log) >= 1, \
            f"Нарушение для {state} должно быть в журнале"

    print(f"✓ Тест Б.1б: все {len(forbidden_states)} запрещённых состояния заблокированы")


test_b1_whitelist_pass()
test_b1_whitelist_block()
print("\n[Б.1] Все тесты пройдены")


# ---
# ## Задание Б.2: Детальное логирование нарушений
# 
# Базовая запись нарушений есть, но она слишком примитивная.
# Для реального расследования инцидентов нужна детальная информация.
# 
# **Требования:**
# - Реализуйте детальное журналирование нарушений политик безопасности
# - Каждая запись должна содержать достаточно информации для расследования инцидента
# - Записи хранятся в `self.violations_log`
# 
# Изучите тесты ниже, чтобы понять, какие поля и форматы ожидаются.

# In[13]:


class MonitorV2(Monitor):
    """Monitor с улучшенным логированием (Задание Б.2)."""

    def log_violation(self, event, reason=""):
        """Фиксирует нарушение политики безопасности в журнал.
        Запись должна содержать достаточно информации для последующего расследования инцидента."""
        record = {
            "timestamp": datetime.now().isoformat(),
            "source": type(event.source).__name__ if event.source is not None else "None",
            "operation": event.operation,
            "params": event.params,
            "reason": reason,
        }
        self.violations_log.append(record)
        print(f"[НАРУШЕНИЕ] {record}")


# In[14]:


# ===== ТЕСТ Б.2 =====

def test_b2_detailed_logging():
    """Тест: журнал нарушений содержит детальную информацию."""
    lights = LightsGPIO()
    monitor = MonitorV2(lights)
    monitor.add_policy(monitor_policy)

    Thread(target=lights.run, daemon=True).start()
    Thread(target=monitor.run, daemon=True).start()

    ctrl = ControlSystem(monitor)

    # Отправляем запрещённое состояние
    ctrl.request_state_change((False, False, True, True))
    time.sleep(0.3)

    assert len(monitor.violations_log) >= 1, "Должно быть хотя бы одно нарушение"

    record = monitor.violations_log[0]

    # Проверяем наличие всех обязательных полей
    required_keys = ["timestamp", "source", "operation", "params", "reason"]
    for key in required_keys:
        assert key in record, \
            f"В записи нарушения отсутствует поле '{key}'. Запись: {record}"

    # Проверяем содержимое
    assert record["operation"] == "set_state", \
        f"Неверная операция в записи: {record['operation']}"
    assert "state" in record["params"], \
        f"В params должен быть ключ 'state': {record['params']}"
    assert isinstance(record["timestamp"], str), \
        f"timestamp должен быть строкой ISO: {record['timestamp']}"
    assert len(record["timestamp"]) > 10, \
        f"timestamp слишком короткий: {record['timestamp']}"

    print("✓ Тест Б.2: детальное логирование работает корректно")
    print(f"  Запись нарушения: {record}")


def test_b2_multiple_violations():
    """Тест: все нарушения логируются независимо."""
    lights = LightsGPIO()
    monitor = MonitorV2(lights)
    monitor.add_policy(monitor_policy)

    Thread(target=lights.run, daemon=True).start()
    Thread(target=monitor.run, daemon=True).start()

    ctrl = ControlSystem(monitor)

    # 3 запрещённых состояния
    ctrl.request_state_change((False, False, True, True))
    ctrl.request_state_change((True, True, False, False))
    ctrl.request_state_change((True, False, True, False))
    time.sleep(0.5)

    assert len(monitor.violations_log) >= 3, \
        f"Должно быть 3 нарушения, получено: {len(monitor.violations_log)}"

    # Все записи должны иметь разные timestamps (или хотя бы валидные)
    for rec in monitor.violations_log:
        assert "timestamp" in rec, f"Каждая запись должна иметь timestamp: {rec}"

    print(f"✓ Тест Б.2б: зафиксировано {len(monitor.violations_log)} нарушений")


test_b2_detailed_logging()
test_b2_multiple_violations()
print("\n[Б.2] Все тесты пройдены")


# ---
# ## Задание Б.3: Защита от «аварийного мигания»
# 
# **Атака:** Злоумышленник может попытаться вывести светофор из строя, генерируя тысячи
# команд переключения в секунду. Это может привести к:
# - Перегрузке системы (DoS)
# - «Аварийному миганию» — хаотичным переключениям, опасным для участников движения
# 
# **Ваша задача:** Реализовать **rate limiting** — ограничение частоты обработки событий.
# 
# **Требования:**
# - Максимум `MAX_EVENTS_PER_SECOND = 5` событий в секунду
# - При превышении лимита — блокировать команду и записывать нарушение
# - Ограничение должно работать по скользящему временному окну

# In[23]:


MAX_EVENTS_PER_SECOND = 5


class MonitorV3(MonitorV2):
    """Monitor с защитой от аварийного мигания (Задание Б.3)."""

    def __init__(self, lights: LightsGPIO):
        super().__init__(lights)
        self._event_times = deque()

    def _check_rate_limit(self) -> bool:
        """Ограничение частоты запросов. Возвращает True, если запрос допустим по частоте."""
        now = time.time()

        while self._event_times and now - self._event_times[0] >= 1.0:
            self._event_times.popleft()

        if len(self._event_times) >= MAX_EVENTS_PER_SECOND:
            return False

        self._event_times.append(now)
        return True

    def run(self):
        """Основной цикл обработки событий с учётом ограничения частоты."""
        while True:
            event = self.events_queue.get()
            if event is None:
                break

            if not self._check_rate_limit():
                self.log_violation(event, f"Превышен лимит: более {MAX_EVENTS_PER_SECOND} команд/сек")
                continue

            if self._check_policies(event):
                self.lights.events_queue.put(event)
            else:
                self.log_violation(event, "Политика безопасности запрещает это событие")


# In[24]:


# ===== ТЕСТ Б.3 =====

def test_b3_rate_limit_normal():
    """Тест: при нормальной частоте команды проходят."""
    lights = LightsGPIO()
    monitor = MonitorV3(lights)
    monitor.add_policy(monitor_policy)

    Thread(target=lights.run, daemon=True).start()
    Thread(target=monitor.run, daemon=True).start()

    ctrl = ControlSystem(monitor)
    violations_before = len(monitor.violations_log)

    # 3 команды с интервалом 0.3 сек (итого 3 команд/сек < 5)
    states = [
        (True, False, False, False),
        (False, False, True, False),
        (False, True, False, False),
    ]
    for state in states:
        ctrl.request_state_change(state)
        time.sleep(0.3)

    rate_violations = len(monitor.violations_log) - violations_before
    assert rate_violations == 0, \
        f"При нормальной частоте нарушений быть не должно. Нарушений: {rate_violations}"
    assert lights.current_state == (False, True, False, False), \
        f"Последнее состояние должно применится. Текущее: {lights.current_state}"

    print("✓ Тест Б.3а: нормальная частота команд проходит без ограничений")


def test_b3_rate_limit_flood():
    """Тест: флуд команд блокируется."""
    lights = LightsGPIO()
    monitor = MonitorV3(lights)
    monitor.add_policy(monitor_policy)

    Thread(target=lights.run, daemon=True).start()
    Thread(target=monitor.run, daemon=True).start()

    ctrl = ControlSystem(monitor)

    # Отправляем 20 команд мгновенно (флуд!)
    for i in range(20):
        ctrl.request_state_change((True, False, False, False))

    time.sleep(0.5)

    total_violations = len(monitor.violations_log)
    assert total_violations >= 14, \
        f"При флуде 20 команд должно быть заблокировано минимум 14 (лимит 5/сек). Заблокировано: {total_violations}"

    print(f"✓ Тест Б.3б: из 20 флуд-команд заблокировано {total_violations}")
    print(f"  (допущено не более {MAX_EVENTS_PER_SECOND} команд/сек)")


test_b3_rate_limit_normal()
test_b3_rate_limit_flood()
print("\n[Б.3] Все тесты пройдены")


# ---
# ## Итоги Модуля Б
# 
# Если все тесты пройдены, модуль завершён!
# 
# | Задание | Описание | Тест        |
# |---------|------------|-------------|
# | Б.1 | Политика whitelist | `test_b1_*` |
# | Б.2 | Детальное логирование | `test_b2_*` |
# | Б.3 | Rate limiting (защита от флуда) | `test_b3_*` |
# 
# Переходите к **Модулю В** — сценариям атак и защите!

# ## Итоговый тест модуля Б
# 
# Запуск всех тестов модуля Б в совокупности.

# In[25]:


# === Итоговый тест модуля Б (Б.3.5) ===
print("=" * 60)
print("ИТОГОВЫЙ ТЕСТ МОДУЛЯ Б")
print("=" * 60)

results = []

# --- Тесты Б.1 (whitelist) ---
try:
    test_b1_whitelist_pass()
    results.append(("Б.1 — whitelist (допустимые)", "PASSED"))
except Exception as e:
    results.append(("Б.1 — whitelist (допустимые)", f"FAILED: {e}"))

try:
    test_b1_whitelist_block()
    results.append(("Б.1 — whitelist (запрещённые)", "PASSED"))
except Exception as e:
    results.append(("Б.1 — whitelist (запрещённые)", f"FAILED: {e}"))

# --- Тесты Б.2 (логирование) ---
try:
    test_b2_detailed_logging()
    results.append(("Б.2 — журнал нарушений", "PASSED"))
except Exception as e:
    results.append(("Б.2 — журнал нарушений", f"FAILED: {e}"))

try:
    test_b2_multiple_violations()
    results.append(("Б.2 — множественные нарушения", "PASSED"))
except Exception as e:
    results.append(("Б.2 — множественные нарушения", f"FAILED: {e}"))

# --- Тесты Б.3 (rate limiting) ---
try:
    test_b3_rate_limit_normal()
    results.append(("Б.3 — нормальный режим", "PASSED"))
except Exception as e:
    results.append(("Б.3 — нормальный режим", f"FAILED: {e}"))

try:
    test_b3_rate_limit_flood()
    results.append(("Б.3 — флуд", "PASSED"))
except Exception as e:
    results.append(("Б.3 — флуд", f"FAILED: {e}"))

passed = sum(1 for _, s in results if s == "PASSED")
total = len(results)

print(f"\nИТОГО: {passed}/{total} тестов PASSED")
for name, status in results:
    marker = "✅" if status == "PASSED" else "❌"
    print(f"  {marker} {name}: {status}")

assert passed == total, f"FAIL: {total - passed} тест(ов) не пройдено"
print(f"\n✅ Все тесты модуля Б пройдены ({passed}/{total})")


# In[ ]:




