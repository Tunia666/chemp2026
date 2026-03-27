#!/usr/bin/env python
# coding: utf-8

# # Модуль Г: Интеграция с внешними системами
# ## Задание соревнований «КиберИммунный Светофор»
# 
# ---
# 
# В реальных умных городах светофоры управляются не только локально,
# но и **централизованными городскими системами управления дорожным движением**.
# 
# В этом модуле вы расширите кибериммунную систему, добавив поддержку
# команд от внешней городской системы.
# 
# **Ваша задача:**
# 1. **Г.1** — Реализовать `CitySystemConnector` — компонент для получения команд от городской системы
# 2. **Г.2** — Обновить политику монитора для проверки авторизации городских команд
# 
# 
# 
# ---
# 
# ### Почему это сложно?
# 
# Городская система — это **внешний, недоверенный источник данных**.
# Даже если мы сами написали коннектор, данные приходят из сети и могут быть:
# - Подделаны (MITM-атака)
# - Содержать вредоносные команды
# - Отправлены неавторизованным агентом
# 
# Поэтому коннектор должен **валидировать** входящие данные,
# а монитор — **проверять авторизацию** городских команд.

# In[4]:


# ===== БАЗОВЫЕ КОМПОНЕНТЫ (не изменять) =====
from queue import Queue
from threading import Thread
import time
import json
from datetime import datetime

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
            source=self, destination=None,
            operation="set_state",
            params={"state": new_state},
        )
        self.monitor.events_queue.put(event)


# Базовая политика whitelist
def whitelist_policy(event):
    if event.operation == "set_state":
        return event.params.get("state") in ALLOWED_STATES
    return True


class Monitor:
    def __init__(self, lights):
        self.lights = lights
        self.events_queue = Queue()
        self.policies = []
        self.violations_log = []
    
    def add_policy(self, policy_func):
        self.policies.append(policy_func)
    
    def _check_policies(self, event):
        for policy in self.policies:
            if not policy(event):
                return False
        return True
    
    def run(self):
        while True:
            event = self.events_queue.get()
            if event is None:
                break
            if self._check_policies(event):
                self.lights.events_queue.put(event)
            else:
                src = type(event.source).__name__ if event.source else "?"
                record = {
                    "timestamp": datetime.now().isoformat(),
                    "source": src,
                    "operation": event.operation,
                    "params": event.params,
                    "reason": "Политика безопасности запрещает событие",
                }
                self.violations_log.append(record)
                print(f"[МОНИТОР] НАРУШЕНИЕ: {src} → {event.operation}({event.params})")


print("Базовые компоненты загружены.")


# ---
# ## Задание Г.1: Реализация CitySystemConnector
# 
# ### Описание
# 
# `CitySystemConnector` — компонент, который:
# 1. Периодически запрашивает команды у городской API
# 2. Валидирует полученные данные
# 3. Формирует Event и отправляет в монитор
# 
# ### Требования к реализации
# 
# **Метод `get_command_from_city()`:**
# - В тестовом режиме возвращает mock-данные (словарь)
# - При отсутствии команд — возвращает `None`
# 
# **Метод `validate_command(command)`:**
# - Проведите валидацию входящей команды
# - При невалидных данных — вернуть `False`
# 
# **Метод `send_command_to_monitor(command)`:**
# - Создайте Event для передачи городской команды в монитор безопасности
# 
# **Метод `_log_city_command(event)`:**
# - Журналирует городскую команду для аудита (критерий Г.3.2)
# - Метод `_log_city_command` должен вызываться при обработке городских команд
# 
# ### Mock-данные для тестирования
# 
# Поскольку реального HTTP-сервера нет, используйте внутреннюю очередь
# `self._mock_commands` для симуляции входящих команд.

# In[5]:


class CitySystemConnector:
    """Коннектор к городской системе управления — НЕДОВЕРЕННЫЙ компонент.
    
    В реальной системе делал бы HTTP-запросы к городскому API.
    В данной реализации использует внутреннюю очередь mock-команд.
    """
    
    def __init__(self, monitor, city_api_url: str = "http://localhost:8080"):
        self.monitor = monitor
        self.city_api_url = city_api_url
        self._mock_commands = []
        self._command_index = 0
        self.city_commands_log = []
    
    def add_mock_command(self, state: tuple, authorized: bool = True):
        """Добавить mock-команду для тестирования.
        
        Args:
            state: кортеж из 4 bool — новое состояние светофора
            authorized: является ли команда авторизованной
        """
        self._mock_commands.append({"state": list(state), "authorized": authorized})
    
    def get_command_from_city(self):
        """Получает следующую команду от городской системы."""
        if self._command_index >= len(self._mock_commands):
            return None

        command = self._mock_commands[self._command_index]
        self._command_index += 1
        return command
    
    def validate_command(self, command: dict) -> bool:
        """Проверяет валидность команды от городской системы."""
        if not isinstance(command, dict):
            return False

        if "state" not in command or "authorized" not in command:
            return False

        state = command["state"]
        authorized = command["authorized"]

        if not isinstance(state, list):
            return False

        if len(state) != 4:
            return False

        if not all(isinstance(x, bool) for x in state):
            return False

        if not isinstance(authorized, bool):
            return False

        return True
    
    def send_command_to_monitor(self, command: dict):
        """Отправляет валидную команду в монитор безопасности через Event."""
        event = Event(
            source=self,
            destination=None,
            operation="set_state",
            params={
                "state": tuple(command["state"]),
                "from_city": True,
                "authorized": command["authorized"],
            },
        )
        self._log_city_command(event)
        self.monitor.events_queue.put(event)
    
    def _log_city_command(self, event):
        """Журналирует городскую команду для аудита."""
        record = {
            "timestamp": datetime.now().isoformat(),
            "source": type(event.source).__name__ if event.source else "None",
            "operation": event.operation,
            "params": event.params,
        }
        self.city_commands_log.append(record)
    
    def run(self):
        """Основной цикл опроса городской системы."""
        while True:
            command = self.get_command_from_city()
            if command is not None:
                if self.validate_command(command):
                    self.send_command_to_monitor(command)
                    print(f"[CITY] Команда отправлена: {command}")
                else:
                    print(f"[CITY] Невалидная команда отброшена: {command}")
            time.sleep(0.1)


print("CitySystemConnector определён.")


# In[6]:


# ===== ТЕСТ Г.1 =====

def test_g1_connector_valid_command():
    """Тест: коннектор корректно обрабатывает валидную команду."""
    lights = LightsGPIO()
    monitor = Monitor(lights)
    monitor.add_policy(whitelist_policy)
    
    Thread(target=lights.run, daemon=True).start()
    Thread(target=monitor.run, daemon=True).start()
    
    connector = CitySystemConnector(monitor)
    
    # Добавляем mock-команды
    connector.add_mock_command((False, False, True, False), authorized=True)
    connector.add_mock_command((True, False, False, False), authorized=True)
    
    # Получаем и обрабатываем первую команду
    cmd = connector.get_command_from_city()
    assert cmd is not None, "get_command_from_city() должна вернуть команду"
    assert "state" in cmd, "Команда должна содержать поле 'state'"
    assert "authorized" in cmd, "Команда должна содержать поле 'authorized'"
    print(f"  Получена команда: {cmd}")
    
    assert connector.validate_command(cmd), "Валидная команда должна проходить валидацию"
    
    connector.send_command_to_monitor(cmd)
    time.sleep(0.3)
    
    print("✓ Тест Г.1а: коннектор корректно получает и отправляет команду")


def test_g1_connector_invalid_command():
    """Тест: коннектор отклоняет невалидные команды."""
    lights = LightsGPIO()
    monitor = Monitor(lights)
    connector = CitySystemConnector(monitor)
    
    invalid_commands = [
        None,
        {},
        {"state": [True, False]},           # слишком короткий state
        {"state": "green"},                  # state не список
        {"authorized": True},                # нет поля state
        {"state": [True, False, True, False]},  # нет поля authorized
    ]
    
    for cmd in invalid_commands:
        if cmd is None:
            continue
        result = connector.validate_command(cmd)
        assert result is False, \
            f"Невалидная команда должна быть отклонена: {cmd}, результат: {result}"
    
    print(f"✓ Тест Г.1б: все {len(invalid_commands)-1} невалидных команд отклонены")


def test_g1_event_has_from_city_flag():
    """Тест: события от коннектора содержат флаг from_city."""
    lights = LightsGPIO()
    
    # Перехватываем события для проверки
    received_events = []
    
    class SpyMonitor:
        def __init__(self):
            self.events_queue = Queue()
        
        def put_event(self, event):
            received_events.append(event)
    
    spy = SpyMonitor()
    
    # Патчим очередь для перехвата
    import queue
    original_put = spy.events_queue.put
    def intercepting_put(event):
        received_events.append(event)
        original_put(event)
    spy.events_queue.put = intercepting_put
    
    connector = CitySystemConnector(spy)
    connector.add_mock_command((True, False, False, False), authorized=True)
    
    cmd = connector.get_command_from_city()
    if connector.validate_command(cmd):
        connector.send_command_to_monitor(cmd)
    
    time.sleep(0.1)
    
    assert len(received_events) >= 1, "Событие должно быть отправлено"
    event = received_events[0]
    assert "from_city" in event.params, \
        f"Событие от коннектора должно содержать флаг 'from_city' в params: {event.params}"
    assert event.params["from_city"] is True, \
        f"Флаг from_city должен быть True: {event.params}"
    assert "authorized" in event.params, \
        f"Событие должно содержать флаг 'authorized' в params: {event.params}"
    
    print("✓ Тест Г.1в: события от CitySystemConnector содержат флаг from_city")


test_g1_connector_valid_command()
test_g1_connector_invalid_command()
test_g1_event_has_from_city_flag()
print("\n[Г.1] Все тесты пройдены")


# ---
# ## Задание Г.2: Политика авторизации городских команд
# 
# ### Описание
# 
# Получив команду от городской системы, монитор должен проверить её авторизацию.
# 
# **Общие требования:**
# - Команды от городской системы должны быть авторизованы
# - Локальные команды (не от города) должны проходить без дополнительных проверок
# 
# ### Зачем это нужно?
# 
# Представьте сценарий: злоумышленник взломал городской сервер и начал
# отправлять команды со своего IP. Коннектор получит эти команды, но
# они придут без флага авторизации. Монитор должен их заблокировать.

# In[7]:


# ===== Задание Г.2: Политика авторизации городских команд =====

def city_authorization_policy(event) -> bool:
    """Политика авторизации: проверяет право городской системы управлять светофором.
    Локальные команды (без поля from_city) должны проходить без дополнительных проверок.
    Если поля from_city / authorized присутствуют, команда допустима только при
    from_city=True и authorized=True.
    """
    params = event.params if isinstance(event.params, dict) else {}

    if "from_city" not in params and "authorized" not in params:
        return True

    return params.get("from_city") is True and params.get("authorized") is True


print("Политика авторизации определена.")


# In[8]:


# ===== ТЕСТ Г.2 =====

def setup_system_with_city_policy():
    """Создать систему с обеими политиками."""
    lights = LightsGPIO()
    monitor = Monitor(lights)
    monitor.add_policy(whitelist_policy)              # стандартная whitelist
    monitor.add_policy(city_authorization_policy)     # авторизация городских команд
    
    Thread(target=lights.run, daemon=True).start()
    Thread(target=monitor.run, daemon=True).start()
    
    return lights, monitor


def test_g2_authorized_city_command_passes():
    """Тест: авторизованная команда от города проходит."""
    lights, monitor = setup_system_with_city_policy()
    connector = CitySystemConnector(monitor)
    
    # Авторизованная команда
    connector.add_mock_command((False, False, True, False), authorized=True)
    cmd = connector.get_command_from_city()
    
    if connector.validate_command(cmd):
        connector.send_command_to_monitor(cmd)
    time.sleep(0.3)
    
    assert lights.current_state == (False, False, True, False), (
        f"Авторизованная городская команда должна пройти. "
        f"Текущее состояние: {lights.current_state}"
    )
    violations = [v for v in monitor.violations_log if v.get("source") == "CitySystemConnector"]
    assert len(violations) == 0, f"Авторизованная команда не должна создавать нарушений: {violations}"
    
    print("✓ Тест Г.2а: авторизованная городская команда прошла")


def test_g2_unauthorized_city_command_blocked():
    """Тест: неавторизованная команда от города блокируется."""
    lights, monitor = setup_system_with_city_policy()
    
    # Устанавливаем начальное состояние через локальный контроллер
    ctrl = ControlSystem(monitor)
    ctrl.request_state_change((True, False, False, False))
    time.sleep(0.2)
    state_before = lights.current_state
    
    # Создаём коннектор и отправляем НЕАВТОРИЗОВАННУЮ команду от города
    connector = CitySystemConnector(monitor)
    connector.add_mock_command((False, False, True, False), authorized=False)  # НЕ авторизована!
    cmd = connector.get_command_from_city()
    
    if connector.validate_command(cmd):
        connector.send_command_to_monitor(cmd)
    time.sleep(0.3)
    
    assert lights.current_state == state_before, (
        f"АТАКА УСПЕШНА! Неавторизованная городская команда прошла!\n"
        f"Было: {state_before}, стало: {lights.current_state}"
    )
    assert len(monitor.violations_log) >= 1, \
        "Неавторизованная команда должна быть зафиксирована в журнале"
    
    print("✓ Тест Г.2б: неавторизованная городская команда ЗАБЛОКИРОВАНА")
    print(f"  Состояние не изменилось: {lights.current_state}")


def test_g2_local_command_unaffected():
    """Тест: политика не влияет на локальные команды (без from_city)."""
    lights, monitor = setup_system_with_city_policy()
    
    ctrl = ControlSystem(monitor)
    ctrl.request_state_change((False, True, False, False))  # жёлтый
    time.sleep(0.3)
    
    assert lights.current_state == (False, True, False, False), (
        f"Локальная команда должна работать без изменений. "
        f"Текущее: {lights.current_state}"
    )
    
    print("✓ Тест Г.2в: локальные команды работают без ограничений")


def test_g2_from_city_false_authorized_true_blocked():
    """Тест Г.2.4: from_city=False, authorized=True → блокируется."""
    lights, monitor = setup_system_with_city_policy()
    
    ctrl = ControlSystem(monitor)
    ctrl.request_state_change((True, False, False, False))
    time.sleep(0.2)
    state_before = lights.current_state
    
    # Событие с from_city=False, authorized=True — должно блокироваться
    event = Event(
        source=ctrl, destination=None,
        operation="set_state",
        params={"state": (False, False, True, False), "from_city": False, "authorized": True},
    )
    monitor.events_queue.put(event)
    time.sleep(0.3)
    
    assert lights.current_state == state_before, (
        f"from_city=False, authorized=True — должно блокироваться! "
        f"Было: {state_before}, стало: {lights.current_state}"
    )
    print("✓ Тест Г.2г: from_city=False, authorized=True → ЗАБЛОКИРОВАНО")


def test_g2_from_city_false_authorized_false_blocked():
    """Тест Г.2.4: from_city=False, authorized=False → блокируется."""
    lights, monitor = setup_system_with_city_policy()
    
    ctrl = ControlSystem(monitor)
    ctrl.request_state_change((True, False, False, False))
    time.sleep(0.2)
    state_before = lights.current_state
    
    # Событие с from_city=False, authorized=False — должно блокироваться
    event = Event(
        source=ctrl, destination=None,
        operation="set_state",
        params={"state": (False, False, True, False), "from_city": False, "authorized": False},
    )
    monitor.events_queue.put(event)
    time.sleep(0.3)
    
    assert lights.current_state == state_before, (
        f"from_city=False, authorized=False — должно блокироваться! "
        f"Было: {state_before}, стало: {lights.current_state}"
    )
    print("✓ Тест Г.2д: from_city=False, authorized=False → ЗАБЛОКИРОВАНО")


test_g2_authorized_city_command_passes()
test_g2_unauthorized_city_command_blocked()
test_g2_local_command_unaffected()
test_g2_from_city_false_authorized_true_blocked()
test_g2_from_city_false_authorized_false_blocked()
print("\n[Г.2] Все тесты пройдены")


# ---
# ## Итоги Модуля Г
# 
# Если все тесты пройдены, модуль завершён!
# 
# | Задание | Описание | Тест 
# |---------|----------------|
# | Г.1 | CitySystemConnector | `test_g1_*` |
# | Г.2 | Политика авторизации городских команд | `test_g2_*` |
# 
# ---
# 
# ## Итоги всех модулей
# 
# | Модуль | Тема |
# |--------|------|
# | А | Базовая кибериммунная архитектура |
# | Б | Монитор безопасности |
# | В | Сценарии атак и защита |
# | Г | Интеграция с внешними системами |
# 
# **Поздравляем с завершением соревнований!** 🏆

# ## Итоговый тест модуля Г
# 
# Запуск всех тестов модуля Г в совокупности.

# In[9]:


# === Итоговый тест модуля Г (Г.3.3) ===
print("=" * 60)
print("ИТОГОВЫЙ ТЕСТ МОДУЛЯ Г")
print("=" * 60)

results = []

try:
    test_g1_connector_valid_command()
    results.append(("Г.1 — CitySystemConnector", "PASSED"))
except Exception as e:
    results.append(("Г.1 — CitySystemConnector", f"FAILED: {e}"))

try:
    test_g1_event_has_from_city_flag()
    results.append(("Г.1 — from_city flag", "PASSED"))
except Exception as e:
    results.append(("Г.1 — from_city flag", f"FAILED: {e}"))

try:
    test_g2_authorized_city_command_passes()
    results.append(("Г.2 — авторизованная команда", "PASSED"))
except Exception as e:
    results.append(("Г.2 — авторизованная команда", f"FAILED: {e}"))

try:
    test_g2_unauthorized_city_command_blocked()
    results.append(("Г.2 — неавторизованная команда", "PASSED"))
except Exception as e:
    results.append(("Г.2 — неавторизованная команда", f"FAILED: {e}"))

passed = sum(1 for _, s in results if s == "PASSED")
total = len(results)

print(f"\nИТОГО: {passed}/{total} тестов PASSED")
for name, status in results:
    marker = "✅" if status == "PASSED" else "❌"
    print(f"  {marker} {name}: {status}")

assert passed == total, f"FAIL: {total - passed} тест(ов) не пройдено"
print(f"\n✅ Все тесты модуля Г пройдены ({passed}/{total})")


# In[ ]:




