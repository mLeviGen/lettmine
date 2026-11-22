import minecraft_launcher_lib
from PyQt6.QtCore import QThread, pyqtSignal

from app.utils.versions import Versions, build_launch_command, launch


class GameWorker(QThread):
    """Установка версии (и Fabric) и/или запуск игры в фоне, чтобы окно не зависало."""

    status = pyqtSignal(str)
    progress = pyqtSignal(float)
    failed = pyqtSignal(str)
    installed = pyqtSignal(str)       # id установленной версии
    launched = pyqtSignal(object)     # subprocess.Popen

    def __init__(self, config, version, username=None, fabric=False, launch_after=True):
        super().__init__()
        self.config = config
        self.version = version
        self.username = username
        self.fabric = fabric
        self.launch_after = launch_after
        self.versions = Versions()
        self._max = 0

    def _callback(self):
        return {
            "setStatus": lambda s: self.status.emit(str(s)),
            "setMax": self._set_max,
            "setProgress": self._set_progress,
        }

    def _set_max(self, value):
        self._max = value

    def _set_progress(self, value):
        if self._max:
            self.progress.emit(value / self._max)

    def run(self):
        try:
            mc_dir = self.config.minecraft_directory
            version = self.version
            fresh = version not in Versions.installed_versions(mc_dir)
            self.status.emit("Установка..." if fresh else "Проверка файлов...")
            # Для уже установленной версии это быстрая проверка, докачивающая битые файлы
            self.versions.install_version(version, mc_dir, self._callback())
            self.config.add_downloaded_version(version)

            if self.fabric:
                if not minecraft_launcher_lib.fabric.is_minecraft_version_supported(version):
                    raise RuntimeError(f"Fabric не поддерживает версию {version}")
                loader = minecraft_launcher_lib.fabric.get_latest_loader_version()
                fabric_id = f"fabric-loader-{loader}-{version}"
                if fabric_id not in Versions.installed_versions(mc_dir):
                    self.status.emit("Установка Fabric...")
                    self.versions.install_fabric_version(version, loader, mc_dir, self._callback())
                self.config.add_downloaded_version(fabric_id)
                self.config.set_fabric_loader_version(loader)
                version = fabric_id

            self.installed.emit(version)
            self.progress.emit(0.0)

            if self.launch_after:
                self.status.emit("Запуск...")
                command = build_launch_command(self.config, version, self.username)
                print("Команда для запуска Minecraft:", " ".join(command))
                self.launched.emit(launch(command, mc_dir))
        except Exception as e:
            self.failed.emit(f"{type(e).__name__}: {e}")
