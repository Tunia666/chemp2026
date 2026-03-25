import time
from datetime import datetime
from queue import Queue, Empty
from threading import Thread


# ─────────────────────────────────────────────────────
# Задание А.4: Архитектурная диаграмма
# ─────────────────────────────────────────────────────

ARCH_DIAGRAM = r"""
                ┌──────────────────────────────┐
                │      PedestrianButton        │
                │       (недоверенный)         │
                └──────────────┬───────────────┘
                               │ Event
                               ▼
┌──────────────────────────────┴──────────────────────────────┐
│                        Monitor (TCB)                        │
│  - проверяет все события по политикам безопасности          │
│  - ведёт журнал нарушений                                   │
│  - пропускает только разрешённые команды                    │
└───────────────┬───────────────────────────────┬─────────────┘
                │ Event                         │ Event
                │                               │
                ▼                               ▲
      ┌──────────────────────┐        ┌──────────────────────┐
      │    LightsGPIO        │        │   ControlSystem      │
      │    (исполнитель)     │        │   (недоверенный)     │
      │  применяет состояние │        │  генерирует команды  │
      └──────────────────────┘        └──────────────────────┘

Правило архитектуры:
ControlSystem НЕ может обращаться к LightsGPIO напрямую.
Все команды проходят через Monitor.
"""

print(ARCH_DIAGRAM)


# ─────────────────────────────────────────────────────
# Задание А.1: Цели и предположения безопасности
# ─────────────────────────────────────────────────────

SECURITY_GOALS = {
    "ЦБ-1": "Монитор безопасности должен разрешать применение только допустимых состояний светофора к исполнительному компоненту LightsGPIO.",
    "ЦБ-2": "Система управления должна передавать команды изменения состояния светофора только через монитор безопасности.",
    "ЦБ-3": "Монитор безопасности должен блокировать и регистрировать каждую команду, приводящую к физически опасной комбинации сигналов светофора.",
}

SECURITY_ASSUMPTIONS = {
    "ПБ-1": "Исполнительный компонент LightsGPIO и монитор безопасности считаются доверенными и не скомпрометированными.",
    "ПБ-2": "Физический доступ нарушителя к линиям управления светодиодами и доверенной вычислительной базе отсутствует.",
}

# Вывод для проверки
print("Цели безопасности:")
for key, value in SECURITY_GOALS.items():
    print(f"  {key}: {value}")

print("\nПредположения безопасности:")
for key, value in SECURITY_ASSUMPTIONS.items():
    print(f"  {key}: {value}")


# ===== ТЕСТ А.1 — автоматическая проверка =====

def test_security_goals():
    assert len(SECURITY_GOALS) >= 3, "Должно быть не менее 3 целей безопасности"
    for key, value in SECURITY_GOALS.items():
        assert "TODO" not in value, f"{key}: замените TODO на реальное описание"
        assert len(value) > 20, f"{key}: описание слишком короткое (минимум 20 символов)"
    print("✓ Тест А.1 пройден: цели безопасности определены корректно")


def test_security_assumptions():
    assert len(SECURITY_ASSUMPTIONS) >= 2, "Должно быть не менее 2 предположений безопасности"
    for key, value in SECURITY_ASSUMPTIONS.items():
        assert "TODO" not in value, f"{key}: замените TODO на реальное описание"
        assert len(value) > 15, f"{key}: описание слишком короткое"
    print("✓ Тест А.1б пройден: предположения безопасности определены корректно")


test_security_goals()
test_security_assumptions()
print("\n[А.1] Все тесты пройдены")


# ─────────────────────────────────────────────────────
# Задание А.2: Реализуйте класс Event
# ─────────────────────────────────────────────────────

class Event:
    """Событие в системе. Реализуйте в соответствии с архитектурой."""

    def __init__(self, source, destination, operation: str, params: dict):
        self.source = source
        self.destination = destination
        self.operation = operation
        self.params = params
        self.timestamp = datetime.now()

    def __repr__(self):
        return (
            f"Event(source={self.source!r}, destination={self.destination!r}, "
            f"operation={self.operation!r}, params={self.params!r}, "
            f"timestamp={self.timestamp.isoformat(timespec='seconds')})"
        )


# ─────────────────────────────────────────────────────
# Задание А.2б: Определите допустимые состояния светофора
# ─────────────────────────────────────────────────────
# Формат: (car_red, car_yellow, car_green, ped_green)

ALLOWED_STATES = [
    (True,  False, False, False),  # авто красный
    (True,  True,  False, False),  # авто красный+жёлтый
    (False, False, True,  False),  # авто зелёный
    (False, True,  False, False),  # авто жёлтый
    (True,  False, False, True),   # авто красный, пешеход зелёный
]

print(f"Определено {len(ALLOWED_STATES)} допустимых состояний")


# ===== ТЕСТ А.2 =====

def test_event_class():
    # Проверка создания события
    e = Event(source="src", destination="dst", operation="test_op", params={"key": "val"})

    assert hasattr(e, 'source'), "Event должен иметь поле 'source'"
    assert hasattr(e, 'destination'), "Event должен иметь поле 'destination'"
    assert hasattr(e, 'operation'), "Event должен иметь поле 'operation'"
    assert hasattr(e, 'params'), "Event должен иметь поле 'params'"
    assert hasattr(e, 'timestamp'), "Event должен иметь поле 'timestamp'"

    assert e.source == "src", "source должен сохраняться"
    assert e.destination == "dst", "destination должен сохраняться"
    assert e.operation == "test_op", "operation должен сохраняться"
    assert e.params == {"key": "val"}, "params должен сохраняться"
    assert isinstance(e.timestamp, datetime), "timestamp должен быть типа datetime"

    repr_str = repr(e)
    assert "TODO" not in repr_str, "__repr__ должен возвращать реальное описание, не TODO"

    print("✓ Тест А.2: класс Event реализован корректно")
    print(f"  Пример события: {repr(e)}")


def test_allowed_states():
    assert len(ALLOWED_STATES) >= 4, "Должно быть не менее 4 допустимых состояний"

    # Проверка формата
    for state in ALLOWED_STATES:
        assert len(state) == 4, f"Каждое состояние — кортеж из 4 элементов: {state}"
        assert all(isinstance(v, bool) for v in state), f"Все значения должны быть bool: {state}"

    # Проверка безопасности: нет запрещённых состояний
    for state in ALLOWED_STATES:
        car_red, car_yellow, car_green, ped_green = state

        assert not (car_green and ped_green), \
            f"ОПАСНОЕ состояние: car_green=True и ped_green=True одновременно! {state}"

    # Проверка: состояния не дублируются (А.2.4)
    assert len(ALLOWED_STATES) == len(set(ALLOWED_STATES)), "FAIL: ALLOWED_STATES содержит дубликаты"

    # Обязательные состояния
    assert (True, False, False, False) in ALLOWED_STATES, \
        "Красный авто (True, False, False, False) должен быть в ALLOWED_STATES"
    assert (False, False, True, False) in ALLOWED_STATES, \
        "Зелёный авто (False, False, True, False) должен быть в ALLOWED_STATES"

    print(f"✓ Тест А.2б: ALLOWED_STATES содержит {len(ALLOWED_STATES)} безопасных состояний")


test_event_class()
test_allowed_states()
print("\n[А.2] Все тесты пройдены")


# ─────────────────────────────────────────────────────
# Задание А.3: Реализуйте компоненты системы
# ─────────────────────────────────────────────────────

class LightsGPIO:
    """Исполнительный компонент — управляет физическими сигналами светофора."""

    def __init__(self):
        self.command_queue = Queue()
        self.current_state = (True, False, False, False)  # безопасное начальное состояние
        self.state_log = [self.current_state]

    def apply_state(self, state):
        self.current_state = state
        self.state_log.append(state)

    def run(self):
        while True:
            try:
                event = self.command_queue.get(timeout=0.1)
                if event.operation == "set_state":
                    state = event.params.get("state")
                    self.apply_state(state)
            except Empty:
                continue


class Monitor:
    """Монитор безопасности — доверенная компонента (TCB).
    Обеспечивает проверку всех команд перед их исполнением."""

    def __init__(self, lights):
        self.lights = lights
        self.input_queue = Queue()
        self.policies = []
        self.violations_log = []

    def add_policy(self, policy):
        self.policies.append(policy)

    def submit_event(self, event: Event):
        self.input_queue.put(event)

    def check_event(self, event: Event):
        for policy in self.policies:
            if not policy(event):
                self.violations_log.append({
                    "timestamp": datetime.now(),
                    "event": event,
                    "reason": f"Blocked by policy {policy.__name__}",
                })
                return False
        return True

    def forward_event(self, event: Event):
        forwarded = Event(
            source="Monitor",
            destination="LightsGPIO",
            operation=event.operation,
            params=event.params,
        )
        self.lights.command_queue.put(forwarded)

    def run(self):
        while True:
            try:
                event = self.input_queue.get(timeout=0.1)
                if self.check_event(event):
                    self.forward_event(event)
            except Empty:
                continue


class ControlSystem:
    """Система управления — недоверенный компонент.
    Взаимодействует с LightsGPIO ТОЛЬКО через Monitor."""

    def __init__(self, monitor):
        self.monitor = monitor

    def request_state_change(self, state):
        event = Event(
            source="ControlSystem",
            destination="Monitor",
            operation="set_state",
            params={"state": state},
        )
        self.monitor.submit_event(event)


print("Классы определены. Запустите тест ниже.")


# Политика whitelist — используется ниже в тестах
def whitelist_policy(event):
    """Политика безопасности: проверяет допустимость запрошенного состояния."""
    if event.operation != "set_state":
        return False

    state = event.params.get("state")
    return state in ALLOWED_STATES


print("Политика определена.")


# ===== ТЕСТ А.3 =====

def test_monitor_allows_valid_state():
    """Тест: монитор пропускает допустимое состояние."""
    lights = LightsGPIO()
    monitor = Monitor(lights)
    monitor.add_policy(whitelist_policy)

    # Запуск в потоках
    t_lights = Thread(target=lights.run, daemon=True)
    t_monitor = Thread(target=monitor.run, daemon=True)
    t_lights.start()
    t_monitor.start()

    ctrl = ControlSystem(monitor)

    # Отправляем допустимое состояние
    ctrl.request_state_change((False, False, True, False))  # зелёный авто
    time.sleep(0.3)

    assert lights.current_state == (False, False, True, False), \
        f"Монитор должен пропустить допустимое состояние. Текущее: {lights.current_state}"
    assert len(monitor.violations_log) == 0, "Нарушений быть не должно"

    print("✓ Тест А.3а: монитор корректно пропускает допустимое состояние")


def test_monitor_blocks_invalid_state():
    """Тест: монитор блокирует запрещённое состояние."""
    lights = LightsGPIO()
    monitor = Monitor(lights)
    monitor.add_policy(whitelist_policy)

    t_lights = Thread(target=lights.run, daemon=True)
    t_monitor = Thread(target=monitor.run, daemon=True)
    t_lights.start()
    t_monitor.start()

    ctrl = ControlSystem(monitor)
    initial_state = lights.current_state

    # Отправляем ЗАПРЕЩЁННОЕ состояние: зелёный авто + зелёный пешеход
    ctrl.request_state_change((False, False, True, True))
    time.sleep(0.3)

    assert lights.current_state == initial_state, \
        f"Монитор ДОЛЖЕН заблокировать опасное состояние! Текущее: {lights.current_state}"
    assert len(monitor.violations_log) >= 1, \
        "Нарушение должно быть зафиксировано в журнале"

    print("✓ Тест А.3б: монитор корректно блокирует запрещённое состояние")
    print(f"  Нарушений зафиксировано: {len(monitor.violations_log)}")


test_monitor_allows_valid_state()
test_monitor_blocks_invalid_state()
print("\n[А.3] Все тесты пройдены")