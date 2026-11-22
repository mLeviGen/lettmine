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
    def available_versions(minecraft_directory, type="release"):
        """Список версий с серверов Mojang; при отсутствии интернета — пустой."""
        try:
            return [
                v["id"]
                for v in minecraft_launcher_lib.utils.get_version_list()
                if v["type"] == type
            ]
        except Exception as e:
            print("Не удалось получить список версий (нет интернета?):", e)
            return []


def offline_uuid(username):
    """UUID как у оффлайн-сервера Minecraft: стабилен для одного ника,
    поэтому инвентарь/прогресс в мирах не теряется между запусками."""
    digest = bytearray(hashlib.md5(("OfflinePlayer:" + username).encode("utf-8")).digest())
    digest[6] = (digest[6] & 0x0F) | 0x30  # версия 3
    digest[8] = (digest[8] & 0x3F) | 0x80  # вариант RFC 4122
    return str(uuid.UUID(bytes=bytes(digest)))


def build_launch_command(config, version, username):
    """Собирает команду запуска игры для minecraft-launcher-lib 8.x."""
    options = {
        "username": username,
        "uuid": offline_uuid(username),
        "token": "0",
        "launcherName": "LettMine",
        "launcherVersion": "0.7",
        "jvmArguments": [f"-Xmx{config.allocated_memory}G", f"-Xms{min(config.allocated_memory, 1)}G"],
    }
    # Свой Java используем, только если путь реально существует. Иначе библиотека
    # сама подберёт нужную JVM (Java 17 для 1.20.x, Java 21 для 1.21+).
    if config.java_path and os.path.isfile(config.java_path):
        options["executablePath"] = config.java_path

    return minecraft_launcher_lib.command.get_minecraft_command(
        version, config.minecraft_directory, options
    )


def launch(command, minecraft_directory):
    """Запускает игру, не блокируя вызывающий код."""
    return subprocess.Popen(command, cwd=minecraft_directory)
