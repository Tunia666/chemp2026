
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


# ===== ЗАЩИТА от CybTL_02 — Ваш код =====

class Monitor_CybTL02:
    """Monitor с регистрацией доверенных источников."""

    def __init__(self, lights):
        self.lights = lights
        self.events_queue = Queue()
        self.violations_log = []
        self.trusted_sources = set()

    def register_trusted_source(self, component):
        """Регистрирует компонент как доверенный источник команд."""
        self.trusted_sources.add(id(component))

    def _is_source_trusted(self, event) -> bool:
        """Проверяет, что источник события является доверенным."""
        return event.source is not None and id(event.source) in self.trusted_sources

    def _is_state_allowed(self, state) -> bool:
        return state in ALLOWED_STATES

    def run(self):
        while True:
            event = self.events_queue.get()
            if event is None:
                break

            if not self._is_source_trusted(event):
                src_name = type(event.source).__name__ if event.source else "?"
                self.violations_log.append({
                    "timestamp": datetime.now().isoformat(),
                    "source": src_name,
                    "reason": "Недоверенный источник команды",
                })
                print(f"[МОНИТОР] НЕДОВЕРЕННЫЙ ИСТОЧНИК: {src_name}")
                continue

            if event.operation == "set_state" and not self._is_state_allowed(event.params.get("state")):
                self.violations_log.append({
                    "timestamp": datetime.now().isoformat(),
                    "reason": "Запрещённое состояние",
                })
                continue

            self.lights.events_queue.put(event)


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

# === Комбинированный тест: все атаки вместе (В.5.1 + В.5.2) ===

class MonitorFull(Monitor_CybTL04):
    """Комбинированный монитор: объедините все 4 механизма защиты."""

    def __init__(self, lights):
        super().__init__(lights)
        self.trusted_sources = set()
        self.source_timestamps = {}

    def register_trusted_source(self, component):
        """Регистрирует компонент как доверенный источник команд."""
        self.trusted_sources.add(id(component))

    def _normalize_state(self, state):
        """Приводит состояние к кортежу из 4 bool."""
        if isinstance(state, tuple) and len(state) == 4:
            return state

        if isinstance(state, dict):
            required_keys = ["car_red", "car_yellow", "car_green", "ped_green"]
            if all(k in state for k in required_keys):
                return (
                    bool(state["car_red"]),
                    bool(state["car_yellow"]),
                    bool(state["car_green"]),
                    bool(state["ped_green"]),
                )
        return None

    def _is_source_trusted(self, event) -> bool:
        return event.source is not None and id(event.source) in self.trusted_sources

    def _check_rate_limit_for_source(self, source) -> bool:
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

    def _check_policies(self, event) -> bool:
        """Полная проверка: all 4 механизма защиты."""
        if not self._is_source_trusted(event):
            return False

        if not self._check_rate_limit_for_source(event.source):
            return False

        if not self._is_event_fresh(event):
            return False

        if event.operation == "set_state":
            raw_state = event.params
            if isinstance(event.params, dict) and "state" in event.params:
                raw_state = event.params.get("state")

            normalized_state = self._normalize_state(raw_state)
            if normalized_state not in ALLOWED_STATES:
                return False

        return True