import os
import uuid
import hashlib
import subprocess

import minecraft_launcher_lib


class Versions:
    def install_version(self, version, minecraft_directory, callback=None):
        minecraft_launcher_lib.install.install_minecraft_version(
            version, minecraft_directory, callback=callback
        )

    def install_fabric_version(self, version, loader_version, minecraft_directory, callback=None):
        minecraft_launcher_lib.fabric.install_fabric(
            minecraft_version=version,
            minecraft_directory=minecraft_directory,
            loader_version=loader_version,
            callback=callback,
        )

    @staticmethod
    def installed_versions(minecraft_directory):
        try:
            return [v["id"] for v in minecraft_launcher_lib.utils.get_installed_versions(minecraft_directory)]
        except Exception:
            return []

    @staticmethod
    def available_versions(minecraft_directory=None, type="release"):
        """Список версий с серверов Mojang; при отсутствии интернета — пустой."""
        try:
            return [
                v["id"]
                for v in minecraft_launcher_lib.utils.get_version_list()
                if v["type"] == type
            ]
        except Exception:
            return []


def offline_uuid(username):
    """UUID как у оффлайн-сервера Minecraft: стабилен для одного ника,
    поэтому инвентарь/прогресс в мирах не теряется между запусками."""
    digest = bytearray(hashlib.md5(("OfflinePlayer:" + username).encode("utf-8")).digest())
    digest[6] = (digest[6] & 0x0F) | 0x30  # версия 3
    digest[8] = (digest[8] & 0x3F) | 0x80  # вариант RFC 4122
    return str(uuid.UUID(bytes=bytes(digest)))


def build_launch_command(config, version, username, player_uuid=None, token=None, game_dir=None, memory=None):
    """Собирает команду запуска игры для minecraft-launcher-lib 8.x.

    Без player_uuid/token — оффлайн-режим (UUID по нику), с ними — лицензия.
    game_dir — папка профиля (моды, миры, настройки); версии и библиотеки общие.
    """
    mem = memory or config.allocated_memory
    options = {
        "username": username,
        "uuid": player_uuid or offline_uuid(username),
        "token": token or "0",
        "launcherName": "LettMine",
        "launcherVersion": "0.9",
        "jvmArguments": [f"-Xmx{mem}G", f"-Xms{min(mem, 1)}G"],
    }
    if game_dir:
        options["gameDirectory"] = game_dir
    # Свой Java используем, только если путь реально существует. Иначе библиотека
    # сама подберёт нужную JVM (Java 17 для 1.20.x, Java 21 для 1.21+).
    if config.java_path and os.path.isfile(config.java_path):
        options["executablePath"] = config.java_path

    return minecraft_launcher_lib.command.get_minecraft_command(
        version, config.minecraft_directory, options
    )


def launch(command, cwd, capture=False):
    """Запускает игру, не блокируя вызывающий код.

    capture=True — без отдельного окна консоли, вывод игры читается через proc.stdout
    (его показывает вкладка «Лог»).
    """
    os.makedirs(cwd, exist_ok=True)
    if not capture:
        return subprocess.Popen(command, cwd=cwd)
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    return subprocess.Popen(
        command, cwd=cwd, creationflags=flags,
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace", bufsize=1,
    )
