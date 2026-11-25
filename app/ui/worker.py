import minecraft_launcher_lib
from PyQt6.QtCore import QThread, pyqtSignal

from app.i18n import tr
from app.ui.logbus import log
from app.utils import account as acc_mod
from app.utils import profiles as prof
from app.utils.versions import Versions, build_launch_command, launch


class GameWorker(QThread):
    """Установка версии профиля (и Fabric) и запуск игры в фоне, чтобы окно не зависало."""

    status = pyqtSignal(str)
    progress = pyqtSignal(float)
    failed = pyqtSignal(str)
    loader_resolved = pyqtSignal(str, str)   # (id профиля, версия Fabric)
    launched = pyqtSignal(object)            # subprocess.Popen
    account_refreshed = pyqtSignal(dict)     # новые данные лицензии (refresh_token меняется)

    def __init__(self, config, profile, account=None, client_id="", launch_after=True):
        super().__init__()
        self.config = config
        self.profile = dict(profile)
        self.account = dict(account or {})
        self.client_id = client_id
        self.launch_after = launch_after
        self.versions = Versions()
        self._max = 0
        self._last_status = ""

    def _say(self, text):
        self.status.emit(text)
        if text != self._last_status:
            self._last_status = text
            log(text)

    def _callback(self):
        return {
            "setStatus": lambda s: self._say(str(s)),
            "setMax": self._set_max,
            "setProgress": self._set_progress,
        }

    def _set_max(self, value):
        self._max = value

    def _set_progress(self, value):
        if self._max:
            self.progress.emit(value / self._max)

    def _credentials(self):
        """(ник, uuid, токен): для лицензии — свежий токен Microsoft, для оффлайна — только ник."""
        if self.account.get("type") == acc_mod.MICROSOFT:
            ms = self.account.get("microsoft") or {}
            if not self.client_id:
                raise RuntimeError(tr("Не указан Client ID приложения Azure (Настройки → Вход по лицензии)."))
            self._say(tr("Вход в аккаунт Microsoft..."))
            data = acc_mod.refresh(self.client_id, ms["refresh_token"])
            self.account_refreshed.emit(
                {"name": data["name"], "id": data["id"], "refresh_token": data["refresh_token"]})
            return data["name"], data["id"], data["access_token"]
        return self.account.get("offline_name"), None, None

    def run(self):
        try:
            p = self.profile
            mc_dir = self.config.minecraft_directory
            mc = p["mc"]
            log(tr("Профиль «{name}»: Minecraft {mc}, {loader}", name=p["name"], mc=mc,
                   loader="Fabric" if p.get("loader") == prof.FABRIC else "Vanilla"))
            fresh = mc not in Versions.installed_versions(mc_dir)
            self._say(tr("Установка Minecraft {mc}...", mc=mc) if fresh else tr("Проверка файлов..."))
            # Для уже установленной версии это быстрая проверка, докачивающая битые файлы
            self.versions.install_version(mc, mc_dir, self._callback())
            self.config.add_downloaded_version(mc)

            if p.get("loader") == prof.FABRIC:
                lv = p.get("loader_version")
                if not lv:
                    if not minecraft_launcher_lib.fabric.is_minecraft_version_supported(mc):
                        raise RuntimeError(tr("Fabric не поддерживает версию {mc}", mc=mc))
                    lv = minecraft_launcher_lib.fabric.get_latest_loader_version()
                    p["loader_version"] = lv
                    self.loader_resolved.emit(p["id"], lv)
                if prof.version_id(p) not in Versions.installed_versions(mc_dir):
                    self._say(tr("Установка Fabric {lv}...", lv=lv))
                    self.versions.install_fabric_version(mc, lv, mc_dir, self._callback())
                self.config.add_downloaded_version(prof.version_id(p))
            self.progress.emit(0.0)

            if self.launch_after:
                name, player_uuid, token = self._credentials()
                self._say(tr("Запуск..."))
                gdir = prof.game_dir(self.config, p)
                command = build_launch_command(self.config, prof.version_id(p), name, player_uuid, token,
                                               game_dir=gdir, memory=p.get("memory") or None)
                shown = " ".join(command)
                if token:
                    shown = shown.replace(token, "***")  # токен в лог не пишем
                log(tr("Команда запуска:") + " " + shown)
                self.launched.emit(launch(command, gdir, capture=True))
        except Exception as e:
            msg = acc_mod.explain_error(e)
            log(tr("Ошибка:") + " " + msg)
            self.failed.emit(msg)


class LoginWorker(QThread):
    """Ждёт возврата из браузера и завершает вход Microsoft."""

    succeeded = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, client_id, state, code_verifier):
        super().__init__()
        self.client_id, self.state, self.code_verifier = client_id, state, code_verifier
        self.cancelled = False

    def run(self):
        try:
            url = acc_mod.wait_for_redirect(should_stop=lambda: self.cancelled)
            data = acc_mod.finish_login(self.client_id, url, self.state, self.code_verifier)
            self.succeeded.emit({"name": data["name"], "id": data["id"], "refresh_token": data["refresh_token"]})
        except Exception as e:
            if not self.cancelled:
                self.failed.emit(acc_mod.explain_error(e))


class VersionListWorker(QThread):
    """Список версий Minecraft с серверов Mojang (в фоне — запрос может занять пару секунд)."""

    loaded = pyqtSignal(list)

    def __init__(self, kind="release"):
        super().__init__()
        self.kind = kind

    def run(self):
        self.loaded.emit(Versions.available_versions(None, self.kind))
