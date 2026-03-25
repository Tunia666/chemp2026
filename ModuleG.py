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
