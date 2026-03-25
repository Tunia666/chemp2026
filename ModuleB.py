
"""
Базовые классы кибериммунной системы управления светофором.
Используются во всех модулях соревнований.

Архитектура основана на принципах кибериммунности (ГОСТ Р 72118-2025):
- Монитор безопасности — доверенная компонента (TCB)
- Система управления — недоверенный компонент
- LightsGPIO — исполнительный компонент
"""

from queue import Queue
from threading import Thread
import time
from datetime import datetime


# =============================================================================
# ДОПУСТИМЫЕ СОСТОЯНИЯ СВЕТОФОРА (WHITELIST)
# Формат: (car_red, car_yellow, car_green, ped_green)
# =============================================================================
ALLOWED_STATES = [
    (True, False, False, True),   # Красный авто + Зелёный пешеход
    (False, False, True, False),  # Зелёный авто
    (False, True, False, False),  # Жёлтый авто
    (True, False, False, False),  # Красный авто
    (False, False, False, False), # Всё выключено
]
# ЗАПРЕЩЕНО: одновременно car_green=True и ped_green=True (опасно для людей!)


class Event:
    """
    Событие в системе — единица передачи данных между компонентами.
    Все коммуникации в системе происходят только через события.
    """

    def __init__(self, source, destination, operation: str, params: dict):
        """
        Инициализация события.

        Args:
            source: компонент-отправитель события
            destination: компонент-получатель события
            operation: название операции (например, "set_state")
            params: словарь с параметрами операции
        """
        self.source = source
        self.destination = destination
        self.operation = operation
        self.params = params
        self.timestamp = datetime.now()  # время создания события

    def __repr__(self):
        src_name = getattr(self.source, '__class__', type(self.source)).__name__
        dst_name = getattr(self.destination, '__class__', type(self.destination)).__name__ if self.destination else "None"
        return (
            f"Event(op={self.operation!r}, "
            f"from={src_name}, to={dst_name}, "
            f"params={self.params}, "
            f"ts={self.timestamp.strftime('%H:%M:%S.%f')[:-3]})"
        )


class Monitor:
    """
    Монитор безопасности — доверенная компонента (TCB).

    Является единственным каналом связи между недоверенными компонентами
    и исполнительными устройствами. Проверяет все события на соответствие
    политикам безопасности.
    """

    def __init__(self, lights: "LightsGPIO"):
        """
        Инициализация монитора.

        Args:
            lights: экземпляр LightsGPIO — исполнительный компонент
        """
        self.lights = lights
        self.events_queue = Queue()
        self.policies = []
        self.violations_log = []   # журнал нарушений
        self._running = False

    def add_policy(self, policy_func):
        """
        Добавить политику безопасности.

        Args:
            policy_func: функция f(event) -> bool,
                         возвращает True если событие разрешено
        """
        self.policies.append(policy_func)

    def _check_policies(self, event: Event) -> bool:
        """
        Проверить событие по всем политикам безопасности.

        Returns:
            True если все политики разрешают событие, иначе False
        """
        for policy in self.policies:
            if not policy(event):
                return False
        return True

    def log_violation(self, event: Event, reason: str = ""):
        """
        Записать нарушение политики безопасности в журнал.

        Args:
            event: событие, которое нарушило политику
            reason: описание причины нарушения
        """
        record = {
            "timestamp": datetime.now().isoformat(),
            "event": repr(event),
            "reason": reason,
        }
        self.violations_log.append(record)
        print(f"[МОНИТОР] НАРУШЕНИЕ ПОЛИТИКИ: {reason} | {repr(event)}")

    def run(self):
        """Основной цикл обработки событий монитора (запускается в потоке)."""
        self._running = True
        while self._running:
            event = self.events_queue.get()
            if event is None:  # сигнал остановки
                break
            if self._check_policies(event):
                # Передаём событие исполнительному компоненту
                if event.destination is not None:
                    event.destination.events_queue.put(event)
                else:
                    self.lights.events_queue.put(event)
            else:
                self.log_violation(event, "Политика безопасности запрещает это событие")

    def stop(self):
        """Остановить монитор."""
        self._running = False
        self.events_queue.put(None)  # сигнал остановки


class ControlSystem:
    """
    Система управления светофором — НЕДОВЕРЕННЫЙ компонент.

    Отправляет команды через монитор безопасности.
    Не имеет прямого доступа к LightsGPIO.
    """

    def __init__(self, monitor: Monitor):
        """
        Инициализация системы управления.

        Args:
            monitor: экземпляр монитора безопасности
        """
        self.monitor = monitor
        self.events_queue = Queue()
        self._running = False

    def request_state_change(self, new_state: tuple):
        """
        Запросить изменение состояния светофора.

        Args:
            new_state: кортеж (car_red, car_yellow, car_green, ped_green)
        """
        event = Event(
            source=self,
            destination=None,   # монитор сам определит получателя
            operation="set_state",
            params={"state": new_state},
        )
        self.monitor.events_queue.put(event)

    def run(self):
        """Стандартный цикл управления: красный → зелёный → жёлтый → красный."""
        self._running = True
        while self._running:
            # Красный
            self.request_state_change((True, False, False, False))
            time.sleep(5)
            # Зелёный
            self.request_state_change((False, False, True, False))
            time.sleep(5)
            # Жёлтый
            self.request_state_change((False, True, False, False))
            time.sleep(2)

    def stop(self):
        """Остановить систему управления."""
        self._running = False


class LightsGPIO:
    """
    Исполнительный компонент — управляет физическими светодиодами.

    Принимает только события от монитора безопасности.
    Не содержит логики принятия решений — только исполнение.
    """

    def __init__(self):
        """Инициализация исполнительного компонента."""
        self.events_queue = Queue()
        self.current_state = (False, False, False, False)  # всё выключено
        self._running = False

    def set_state(self, state: tuple):
        """
        Установить новое состояние светодиодов.

        Args:
            state: кортеж (car_red, car_yellow, car_green, ped_green)
        """
        self.current_state = state
        self._update_leds()

    def _update_leds(self):
        """
        Обновить состояние физических светодиодов (GPIO).
        В реальной системе здесь будет управление GPIO-пинами.
        """
        car_red, car_yellow, car_green, ped_green = self.current_state
        # Симуляция GPIO-вывода
        r_sym = "🔴" if car_red else "⚫"
        y_sym = "🟡" if car_yellow else "⚫"
        g_sym = "🟢" if car_green else "⚫"
        p_sym = "🟢" if ped_green else "🔴"
        print(
            f"[GPIO] Авто: {r_sym}R {y_sym}Y {g_sym}G  |  "
            f"Пешеход: {p_sym}  |  "
            f"Состояние: {self.current_state}"
        )

    def run(self):
        """Основной цикл обработки событий (запускается в потоке)."""
        self._running = True
        while self._running:
            event = self.events_queue.get()
            if event is None:  # сигнал остановки
                break
            if event.operation == "set_state":
                self.set_state(event.params["state"])

    def stop(self):
        """Остановить исполнительный компонент."""
        self._running = False
        self.events_queue.put(None)  # сигнал остановки


class PedestrianButton:
    """
    Кнопка вызова пешехода — недоверенный компонент.

    Когда пешеход нажимает кнопку, система должна перейти в состояние
    "красный авто + зелёный пешеход" при первой возможности.
    """

    def __init__(self, monitor: Monitor):
        """
        Инициализация кнопки пешехода.

        Args:
            monitor: экземпляр монитора безопасности
        """
        self.monitor = monitor
        self.events_queue = Queue()
        self._pressed = False

    def press(self):
        """
        Нажать кнопку пешехода.
        Отправляет запрос на переход в режим "красный авто + зелёный пешеход".
        """
        if not self._pressed:
            self._pressed = True
            print("[КНОПКА] Пешеход нажал кнопку!")
            event = Event(
                source=self,
                destination=None,
                operation="set_state",
                params={"state": (True, False, False, True)},  # красный авто + зелёный пешеход
            )
            self.monitor.events_queue.put(event)

    def reset(self):
        """Сбросить состояние кнопки."""
        self._pressed = False


def create_default_whitelist_policy():
    """
    Создать стандартную политику whitelist для монитора.

    Returns:
        Функция-политика f(event) -> bool
    """
    def whitelist_policy(event: Event) -> bool:
        """Разрешать только допустимые состояния из ALLOWED_STATES."""
        if event.operation == "set_state":
            requested_state = event.params.get("state")
            if requested_state not in ALLOWED_STATES:
                return False
        return True

    return whitelist_policy


def build_system():
    """
    Собрать полную систему из компонентов.

    Returns:
        Кортеж (monitor, control_system, lights, ped_button)
    """
    lights = LightsGPIO()
    monitor = Monitor(lights)
    monitor.add_policy(create_default_whitelist_policy())
    control_system = ControlSystem(monitor)
    ped_button = PedestrianButton(monitor)
    return monitor, control_system, lights, ped_button


if __name__ == "__main__":
    # Быстрая проверка работоспособности
    print("=== Проверка базовых компонентов ===")
    monitor, ctrl, lights, btn = build_system()

    # Запуск в потоках
    threads = [
        Thread(target=monitor.run, daemon=True),
        Thread(target=lights.run, daemon=True),
    ]
    for t in threads:
        t.start()

    # Тест: допустимое состояние
    print("\n[ТЕСТ] Отправка допустимого состояния: зелёный авто")
    ctrl.request_state_change((False, False, True, False))
    time.sleep(0.2)

    # Тест: запрещённое состояние
    print("\n[ТЕСТ] Попытка запрещённого состояния: зелёный авто + зелёный пешеход")
    ctrl.request_state_change((False, False, True, True))
    time.sleep(0.2)

    print(f"\nНарушений зафиксировано: {len(monitor.violations_log)}")
    print("=== Проверка завершена ===")
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
