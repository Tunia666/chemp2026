#!/usr/bin/env python
# coding: utf-8

# # Модуль В: Сценарии атак и защита
# ## Задание соревнований «КиберИммунный Светофор»
# 
# ---
# 
# В этом модуле вы будете работать с **реальными сценариями кибератак** на систему светофора.
# Для каждой атаки:
# 1. Код атаки уже написан — изучите его
# 2. Реализуйте защиту (TODO)
# 3. Убедитесь, что тест атаки проходит
# 
# **Атаки и очки:**
# | Атака | Название 
# |-------|----------
# | CybTL_01 | Инъекция запрещённого состояния |
# | CybTL_02 | Подмена источника команды |
# | CybTL_03 | Флуд командами (DoS) |
# | CybTL_04 | Повторное воспроизведение (Replay) |
# 
# 

# In[13]:


# ===== БАЗОВЫЕ КОМПОНЕНТЫ (не изменять) =====
from queue import Queue
from threading import Thread
import time
from datetime import datetime
from collections import deque

ALLOWED_STATES = [
    (True, False, False, True),
    (False, False, True, False),
    (False, True, False, False),
    (True, False, False, False),
    (False, False, False, False),
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
        print(f"[GPIO] Авто:{r}{y}{g}  Пешеход:{p}")
    
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
            source=self, destination=None,
            operation="set_state",
            params={"state": new_state},
        )
        self.monitor.events_queue.put(event)


print("Базовые компоненты загружены.")


# ---
# ## CybTL_01: Инъекция запрещённого состояния
# 
# ### Описание атаки
# 
# **Цель злоумышленника:** Напрямую поместить в очередь монитора событие с запрещённым состоянием.
# В кибериммунной системе злоумышленник **не имеет прямого доступа** к исполнительным компонентам,
# но может отправить событие через монитор.
# 
# **Запрещённое состояние:** `(False, False, True, True)` — одновременно зелёный для авто и пешеходов.⚠️
# 
# ### Для чего защита
# Монитор должен проверять каждое входящее событие по whitelist и блокировать запрещённые состояния,
# **независимо от источника запроса**.

# In[14]:


# ===== КОД АТАКИ CybTL_01 (не изменять) =====

class Attacker_CybTL01:
    """Злоумышленник: инъекция запрещённого состояния."""
    
    def __init__(self, name="Attacker_01"):
        self.name = name
    
    def inject_forbidden_state(self, monitor):
        """Напрямую внедрить запрещённое состояние в очередь монитора."""
        forbidden_state = (False, False, True, True)  # зелёный авто + зелёный пешеход!
        malicious_event = Event(
            source=self,
            destination=None,
            operation="set_state",
            params={"state": forbidden_state},
        )
        print(f"[АТАКА CybTL_01] Инъекция запрещённого состояния: {forbidden_state}")
        monitor.events_queue.put(malicious_event)

print("Симулятор атаки CybTL_01 готов.")


# In[15]:


# ===== ЗАЩИТА от CybTL_01 — Ваш код =====

class Monitor_CybTL01:
    """Monitor с защитой от инъекции запрещённого состояния."""
    
    def __init__(self, lights):
        self.lights = lights
        self.events_queue = Queue()
        self.violations_log = []
    
    def _is_state_allowed(self, state) -> bool:
        """Проверяет допустимость запрошенного состояния светофора."""
        return state in ALLOWED_STATES
    
    def run(self):
        """Основной цикл монитора."""
        while True:
            event = self.events_queue.get()
            if event is None:
                break
            
            if event.operation == "set_state":
                state = event.params.get("state")
                if self._is_state_allowed(state):
                    self.lights.events_queue.put(event)
                else:
                    src_name = type(event.source).__name__ if event.source else "?"
                    violation = {
                        "timestamp": datetime.now().isoformat(),
                        "source": src_name,
                        "state": state,
                        "reason": "Запрещённое состояние",
                    }
                    self.violations_log.append(violation)
                    print(f"[МОНИТОР] ЗАБЛОКИРОВАНО: {src_name} → {state}")


# In[16]:


# ===== ТЕСТ CybTL_01 =====

def test_cybtl01():
    lights = LightsGPIO()
    monitor = Monitor_CybTL01(lights)
    attacker = Attacker_CybTL01()
    
    Thread(target=lights.run, daemon=True).start()
    Thread(target=monitor.run, daemon=True).start()
    
    # Сначала нормальное состояние
    ctrl = ControlSystem(monitor)
    ctrl.request_state_change((True, False, False, False))  # красный
    time.sleep(0.2)
    state_before_attack = lights.current_state
    
    # Атака!
    attacker.inject_forbidden_state(monitor)
    time.sleep(0.2)
    
    # Проверки
    assert lights.current_state == state_before_attack, (
        f"АТАКА УСПЕШНА! Монитор пропустил запрещённое состояние! "
        f"Было: {state_before_attack}, стало: {lights.current_state}"
    )
    assert len(monitor.violations_log) >= 1, \
        "Атака должна быть зафиксирована в журнале нарушений"
    assert monitor.violations_log[0]["source"] == "Attacker_CybTL01", \
        "В журнале должен быть записан источник атаки"
    
    print("✓ CybTL_01: атака инъекции ЗАБЛОКИРОВАНА")
    print(f"  Состояние не изменилось: {lights.current_state}")
    print(f"  Источник атаки записан: {monitor.violations_log[0]['source']}")


test_cybtl01()
print("\n[CybTL_01] Все тесты пройдены")


# ---
# ## CybTL_02: Подмена источника команды
# 
# ### Описание атаки
# 
# **Цель злоумышленника:** Создать поддельный компонент `FakeControlSystem`, который
# выдаёт себя за легитимный `ControlSystem`.
# 
# **Сценарий:** В более сложных системах монитор должен проверять не только
# содержимое команды, но и **кто** её отправил. Только авторизованные компоненты
# могут выдавать команды.
# 
# ### Ваша задача
# Реализовать **регистрацию доверенных источников** в мониторе.
# Монитор должен принимать команды **только от зарегистрированных компонентов**.

# In[19]:


# ===== КОД АТАКИ CybTL_02 (не изменять) =====

class FakeControlSystem:
    """Злоумышленник: поддельная система управления."""
    
    def __init__(self):
        self.events_queue = Queue()
    
    def send_malicious_command(self, monitor, state):
        """Отправить команду от имени поддельного источника."""
        event = Event(
            source=self,
            destination=None,
            operation="set_state",
            params={"state": state},
        )
        print(f"[АТАКА CybTL_02] Поддельная команда от FakeControlSystem: {state}")
        monitor.events_queue.put(event)

print("Симулятор атаки CybTL_02 готов.")


# In[20]:


# ===== ЗАЩИТА от CybTL_02 — Ваш код =====
class Monitor_CybTL02:
    """Монитор с регистрацией доверенных источников."""

    def __init__(self, lights):
        self.lights = lights
        self.events_queue = Queue()
        self.violations_log = []
        self.trusted_sources = set()

    def register_trusted_source(self, component):
        self.trusted_sources.add(id(component))

    def _is_source_trusted(self, event) -> bool:
        return event.source is not None and id(event.source) in self.trusted_sources

    def _is_state_allowed(self, state) -> bool:
        return state in ALLOWED_STATES

    def log_violation(self, event, reason):
        src_name = event.source.__class__.__name__ if event.source else "?"
        self.violations_log.append({
            "timestamp": datetime.now().isoformat(),
            "source": src_name,
            "reason": reason,
            "event": repr(event),
        })
        print(f"[МОНИТОР] {reason}: {src_name}")

    def run(self):
        while True:
            event = self.events_queue.get()
            if event is None:
                break

            if not self._is_source_trusted(event):
                self.log_violation(event, "Недоверенный источник команды")
                continue

            if event.operation == "set_state":
                state = event.params.get("state")
                if not self._is_state_allowed(state):
                    self.log_violation(event, "Запрещённое состояние")
                    continue

            self.lights.events_queue.put(event)


# In[21]:


# ===== ТЕСТ CybTL_02 =====

def test_cybtl02():
    lights = LightsGPIO()
    monitor = Monitor_CybTL02(lights)
    
    # Регистрируем легитимный контроллер
    ctrl = ControlSystem(monitor)
    monitor.register_trusted_source(ctrl)
    
    # Злоумышленник НЕ зарегистрирован
    fake = FakeControlSystem()
    
    Thread(target=lights.run, daemon=True).start()
    Thread(target=monitor.run, daemon=True).start()
    
    # Легитимная команда — должна пройти
    ctrl.request_state_change((False, False, True, False))
    time.sleep(0.2)
    legitimate_state = lights.current_state
    
    # Атака: команда от поддельного источника
    fake.send_malicious_command(monitor, (True, False, False, False))
    time.sleep(0.2)
    
    assert lights.current_state == legitimate_state, (
        f"АТАКА УСПЕШНА! Команда от поддельного источника прошла! "
        f"Было: {legitimate_state}, стало: {lights.current_state}"
    )
    assert len(monitor.violations_log) >= 1, \
        "Попытка незарегистрированного источника должна логироваться"
    
    # Знаем точно, что легитимная команда прошла
    assert lights.current_state == (False, False, True, False), \
        f"Легитимная команда должна была применится: {lights.current_state}"
    
    print("✓ CybTL_02: атака подмены источника ЗАБЛОКИРОВАНА")
    print(f"  Состояние осталось от легитимной команды: {lights.current_state}")


test_cybtl02()
print("\n[CybTL_02] Все тесты пройдены")


# ---
# ## CybTL_03: Флуд командами (DoS-атака)
# 
# ### Описание атаки
# 
# **Цель злоумышленника:** Заблокировать нормальную работу системы, генерируя тысячи
# команд в секунду. Это может привести к:
# - Переполнению очереди событий монитора
# - Задержкам обработки легитимных команд
# - Хаотичному поведению светофора ("мигание")
# 
# ### Ваша задача
# Реализовать **rate limiting** — ограничение количества обрабатываемых событий
# от одного источника в единицу времени.
# 
# **Требования:**
# - Не более `5` событий в секунду от одного источника
# - При превышении: блокировать и логировать
# - Легитимные медленные команды не должны блокироваться

# In[6]:


# ===== КОД АТАКИ CybTL_03 (не изменять) =====

class Attacker_CybTL03:
    """Злоумышленник: DoS-атака флудом команд."""
    
    def flood_monitor(self, monitor, count=50):
        """Отправить count команд мгновенно."""
        print(f"[АТАКА CybTL_03] Начинаю флуд: {count} команд мгновенно")
        for i in range(count):
            event = Event(
                source=self,
                destination=None,
                operation="set_state",
                params={"state": (True, False, False, False)},
            )
            monitor.events_queue.put(event)
        print(f"[АТАКА CybTL_03] Отправлено {count} команд")

print("Симулятор атаки CybTL_03 готов.")


# In[22]:


# ===== ЗАЩИТА от CybTL_03 — Ваш код =====

RATE_LIMIT_PER_SOURCE = 5  # максимум событий в секунду от одного источника


class Monitor_CybTL03:
    """Monitor с rate limiting по источнику."""
    
    def __init__(self, lights):
        self.lights = lights
        self.events_queue = Queue()
        self.violations_log = []
        self.source_timestamps = {}
    
    def _check_rate_limit_for_source(self, source) -> bool:
        """Ограничение частоты запросов от конкретного источника."""
        source_id = id(source)
        now = time.time()

        if source_id not in self.source_timestamps:
            self.source_timestamps[source_id] = deque()

        timestamps = self.source_timestamps[source_id]

        while timestamps and now - timestamps[0] >= 1.0:
            timestamps.popleft()

        if len(timestamps) >= RATE_LIMIT_PER_SOURCE:
            return False

        timestamps.append(now)
        return True
    
    def _is_state_allowed(self, state) -> bool:
        return state in ALLOWED_STATES
    
    def run(self):
        while True:
            event = self.events_queue.get()
            if event is None:
                break
            
            if not self._check_rate_limit_for_source(event.source):
                src_name = type(event.source).__name__ if event.source else "?"
                self.violations_log.append({
                    "timestamp": datetime.now().isoformat(),
                    "source": src_name,
                    "reason": "Rate limit превышен",
                })
                continue
            
            if event.operation == "set_state" and not self._is_state_allowed(event.params.get("state")):
                self.violations_log.append({"reason": "Запрещённое состояние"})
                continue
            
            self.lights.events_queue.put(event)


# In[12]:


# ===== ТЕСТ CybTL_03 =====

def test_cybtl03():
    lights = LightsGPIO()
    monitor = Monitor_CybTL03(lights)
    attacker = Attacker_CybTL03()
    
    Thread(target=lights.run, daemon=True).start()
    Thread(target=monitor.run, daemon=True).start()
    
    # Легитимный медленный контроллер
    ctrl = ControlSystem(monitor)
    ctrl.request_state_change((False, False, True, False))
    time.sleep(0.3)
    legit_state = lights.current_state
    assert legit_state == (False, False, True, False), \
        f"Легитимная команда должна пройти: {legit_state}"
    
    # Атака: флуд 50 команд
    violations_before = len(monitor.violations_log)
    attacker.flood_monitor(monitor, count=50)
    time.sleep(1.0)  # ждём обработки
    
    blocked_count = len(monitor.violations_log) - violations_before
    passed_count = 50 - blocked_count
    
    assert blocked_count >= 40, (
        f"При флуде 50 команд должно быть заблокировано минимум 40. "
        f"Заблокировано: {blocked_count}, прошло: {passed_count}"
    )
    
    print("✓ CybTL_03: DoS-атака флудом ЗАБЛОКИРОВАНА")
    print(f"  Из 50 флуд-команд заблокировано: {blocked_count}, прошло: {passed_count}")


test_cybtl03()
print("\n[CybTL_03] Все тесты пройдены")


# ---
# ## CybTL_04: Атака воспроизведения (Replay Attack)
# 
# ### Описание атаки
# 
# **Цель злоумышленника:** Перехватить легитимное событие, сохранить его,
# и отправить повторно позже — в нужный злоумышленнику момент.
# 
# **Сценарий:**
# 1. Пешеход нажал кнопку → система переключилась на "красный авто + зелёный пешеход"
# 2. Злоумышленник перехватил это событие
# 3. Спустя 10 секунд злоумышленник повторяет это событие в неправильный момент
# 
# ### Ваша задача
# Реализовать **проверку свежести события** — монитор должен отклонять устаревшие события.
# 
# **Требования:**
# - Устаревшие события (старше допустимого порога) — блокировать
# - Свежие события — пропускать

# In[23]:


# ===== КОД АТАКИ CybTL_04 (не изменять) =====

class Attacker_CybTL04:
    """Злоумышленник: атака повторного воспроизведения (Replay)."""
    
    def __init__(self):
        self.captured_event = None
    
    def capture_event(self, event):
        """Перехватить событие (сохранить копию)."""
        self.captured_event = event
        print(f"[АТАКА CybTL_04] Событие перехвачено: {repr(event)}")
    
    def replay_attack(self, monitor, delay_seconds=2):
        """Воспроизвести перехваченное событие через delay секунд."""
        if not self.captured_event:
            print("[АТАКА] Нет перехваченного события!")
            return
        
        print(f"[АТАКА CybTL_04] Ожидание {delay_seconds} сек перед replay...")
        time.sleep(delay_seconds)
        print(f"[АТАКА CybTL_04] Воспроизведение старого события: {repr(self.captured_event)}")
        monitor.events_queue.put(self.captured_event)

print("Симулятор атаки CybTL_04 готов.")


# In[24]:


# ===== ЗАЩИТА от CybTL_04 — Ваш код =====

MAX_EVENT_AGE_SECONDS = 1  # событие не должно быть старше 1 секунды


class Monitor_CybTL04:
    """Monitor с проверкой свежести события."""
    
    def __init__(self, lights):
        self.lights = lights
        self.events_queue = Queue()
        self.violations_log = []
    
    def _is_event_fresh(self, event) -> bool:
        """Проверяет актуальность события (защита от повторного воспроизведения)."""
        age = (datetime.now() - event.timestamp).total_seconds()
        return age <= MAX_EVENT_AGE_SECONDS
    
    def _is_state_allowed(self, state) -> bool:
        return state in ALLOWED_STATES
    
    def run(self):
        while True:
            event = self.events_queue.get()
            if event is None:
                break
            
            if not self._is_event_fresh(event):
                age = (datetime.now() - event.timestamp).total_seconds()
                self.violations_log.append({
                    "timestamp": datetime.now().isoformat(),
                    "event_age": age,
                    "reason": f"Устаревшее событие (возраст: {age:.1f} сек)",
                })
                print(f"[МОНИТОР] REPLAY ЗАБЛОКИРОВАН: событие возрастом {age:.1f} сек")
                continue
            
            if event.operation == "set_state" and not self._is_state_allowed(event.params.get("state")):
                self.violations_log.append({"reason": "Запрещённое состояние"})
                continue
            
            self.lights.events_queue.put(event)


# > ⏱️ **Внимание:** Следующий тест занимает **~3 секунды** из-за симуляции временной задержки при атаке воспроизведения. Это нормально — дождитесь завершения выполнения ячейки.

# In[25]:


# ===== ТЕСТ CybTL_04 =====
# ВНИМАНИЕ: этот тест занимает ~3 секунды из-за симуляции задержки

def test_cybtl04():
    lights = LightsGPIO()
    monitor = Monitor_CybTL04(lights)
    attacker = Attacker_CybTL04()
    
    Thread(target=lights.run, daemon=True).start()
    Thread(target=monitor.run, daemon=True).start()
    
    ctrl = ControlSystem(monitor)
    
    # Шаг 1: легитимная команда (злоумышленник её "перехватывает")
    ped_event = Event(
        source=ctrl,
        destination=None,
        operation="set_state",
        params={"state": (True, False, False, True)},  # красный авто + зелёный пешеход
    )
    attacker.capture_event(ped_event)  # злоумышленник перехватывает
    monitor.events_queue.put(ped_event)  # легитимная отправка
    time.sleep(0.2)
    
    # Проверяем что легитимная команда прошла
    assert lights.current_state == (True, False, False, True), \
        f"Свежая команда должна пройти: {lights.current_state}"
    
    # Шаг 2: переключаем снова
    ctrl.request_state_change((False, False, True, False))  # зелёный авто
    time.sleep(0.2)
    state_after_switch = lights.current_state
    
    # Шаг 3: Replay-атака (через 2 секунды — больше MAX_EVENT_AGE_SECONDS=1)
    print(f"Текущее состояние: {state_after_switch}")
    print("Запускаем Replay-атаку (с задержкой 2 сек)...")
    
    replay_thread = Thread(target=attacker.replay_attack, args=(monitor, 2), daemon=True)
    replay_thread.start()
    replay_thread.join(timeout=4)
    time.sleep(0.3)
    
    # Проверяем: состояние НЕ должно измениться
    assert lights.current_state == state_after_switch, (
        f"REPLAY АТАКА УСПЕШНА! Состояние изменилось!\n"
        f"Было: {state_after_switch}, стало: {lights.current_state}"
    )
    assert len(monitor.violations_log) >= 1, \
        "Replay-атака должна быть зафиксирована"
    assert monitor.violations_log[-1]["event_age"] > MAX_EVENT_AGE_SECONDS, \
        "В журнале должен быть возраст события"
    
    print("✓ CybTL_04: Replay-атака ЗАБЛОКИРОВАНА")
    print(f"  Состояние не изменилось: {lights.current_state}")
    print(f"  Возраст заблокированного события: {monitor.violations_log[-1]['event_age']:.1f} сек")


test_cybtl04()
print("\n[CybTL_04] Все тесты пройдены")


# ---
# ## Итоги Модуля В
# 
# Если все тесты пройдены, модуль завершён!
# 
# | Атака | Тип | Защита 
# |-------|-----|--------
# | CybTL_01 | Инъекция состояния | Whitelist |
# | CybTL_02 | Подмена источника | Регистрация источников |
# | CybTL_03 | DoS-флуд | Rate limiting |
# | CybTL_04 | Replay-атака | Проверка свежести |
# 
# Переходите к **Модулю Г** для интеграции с городской системой управления!

# ## Комбинированный тест: все защиты вместе
# 
# Проверка, что все 4 защитных механизма работают совместно.
# CybTL_01 (whitelist) + CybTL_02 (trusted sources) + CybTL_03 (rate limiting) + CybTL_04 (replay guard) — единый монитор.

# In[26]:


# === Комбинированный тест: все атаки вместе (В.5.1 + В.5.2) ===

class MonitorFull(Monitor_CybTL04):
    """Комбинированный монитор: объедините все 4 механизма защиты."""

    def __init__(self, lights):
        super().__init__(lights)

    def register_trusted_source(self, component):
        """Регистрирует компонент как доверенный источник команд."""
        pass  # Реализуйте регистрацию

    def _check_policies(self, event) -> bool:
        """Полная проверка: все 4 механизма защиты."""
        return True  # Реализуйте комбинированную проверку


def test_combined():
    """Все атаки CybTL_01–04 против единого монитора"""
    print("=" * 60)
    print("КОМБИНИРОВАННЫЙ ТЕСТ: все защиты вместе")
    print("=" * 60)

    gpio = LightsGPIO()
    monitor = MonitorFull(gpio)
    cs = ControlSystem(monitor)
    monitor.register_trusted_source(cs)

    results = []

    # --- CybTL_01: инъекция запрещённого состояния ---
    dangerous = {"car_red": False, "car_yellow": False, "lcar_green": True, "ped_green": True}
    event_01 = Event(source=cs, destination=gpio, operation="set_state", params=dangerous)
    result_01 = monitor._check_policies(event_01)
    status_01 = "PASSED" if not result_01 else "FAILED"
    results.append(("CybTL_01 (whitelist)", status_01))
    print(f"  CybTL_01 — инъекция запрещённого состояния: {status_01}")

    # --- CybTL_02: подмена источника ---
    class FakeComponent:
        pass
    fake = FakeComponent()
    safe_state = {"car_red": True, "car_yellow": False, "car_green": False, "ped_green": True}
    event_02 = Event(source=fake, destination=gpio, operation="set_state", params=safe_state)
    result_02 = monitor._check_policies(event_02)
    status_02 = "PASSED" if not result_02 else "FAILED"
    results.append(("CybTL_02 (trusted source)", status_02))
    print(f"  CybTL_02 — подмена источника: {status_02}")

    # --- CybTL_03: DoS-флуд ---
    blocked_count = 0
    for i in range(20):
        flood_event = Event(source=cs, destination=gpio, operation="set_state", params=safe_state)
        if not monitor._check_policies(flood_event):
            blocked_count += 1
    status_03 = "PASSED" if blocked_count >= 14 else "FAILED"
    results.append(("CybTL_03 (rate limiting)", status_03))
    print(f"  CybTL_03 — DoS-флуд (заблокировано {blocked_count}/20): {status_03}")

    # --- CybTL_04: replay-атака ---
    import time
    old_event = Event(source=cs, destination=gpio, operation="set_state", params=safe_state)
    time.sleep(2)  # Ждём, чтобы событие устарело
    result_04 = monitor._check_policies(old_event)
    status_04 = "PASSED" if not result_04 else "FAILED"
    results.append(("CybTL_04 (replay guard)", status_04))
    print(f"  CybTL_04 — replay-атака: {status_04}")

    # --- Итоговый отчёт ---
    print("\n" + "=" * 60)
    passed = sum(1 for _, s in results if s == "PASSED")
    total = len(results)
    print(f"ИТОГО: {passed}/{total} тестов PASSED")
    for name, status in results:
        print(f"  [{status}] {name}")
    print("=" * 60)

    assert all(s == "PASSED" for _, s in results), f"FAIL: не все тесты пройдены ({passed}/{total})"
    print("\n✅ Комбинированный тест пройден: все 4 защиты работают совместно")

test_combined()


# In[ ]:




