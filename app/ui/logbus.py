"""Общий журнал: сообщения лаунчера и вывод игры для вкладки «Лог».

Живёт отдельно от окна: при смене языка окно пересоздаётся, а журнал и
наблюдение за запущенной игрой продолжаются.
"""
import threading
import time
from collections import deque

from PyQt6.QtCore import QObject, pyqtSignal


class LogBus(QObject):
    line = pyqtSignal(str, str)      # (источник: "launcher" | "game", текст)
    game_exited = pyqtSignal(int)    # код завершения игры
    MAX_LINES = 5000

    def __init__(self):
        super().__init__()
        self.lines = deque(maxlen=self.MAX_LINES)
        self.game = None  # subprocess.Popen запущенной игры

    def write(self, text, source="launcher"):
        for part in str(text).splitlines() or [""]:
            if source == "launcher":
                part = f"[{time.strftime('%H:%M:%S')}] [LettMine] {part}"
            self.lines.append((source, part))
            self.line.emit(source, part)

    def clear(self):
        self.lines.clear()

    def game_running(self):
        return bool(self.game and self.game.poll() is None)

    def watch_game(self, proc):
        """Пересылает вывод игры в журнал. Поток-демон: не мешает закрыть лаунчер."""
        self.game = proc

        def pump():
            if proc.stdout:
                for raw in proc.stdout:
                    self.write(raw.rstrip(), "game")
            self.game_exited.emit(proc.wait())

        threading.Thread(target=pump, daemon=True).start()


bus = LogBus()


def log(text):
    bus.write(text, "launcher")
