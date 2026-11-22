"""Консольный запуск без GUI.

    python main.py                      # 1.21.1 + Fabric 0.16.10, ник loka
    python main.py 1.20.4 0.15.11 nick  # своя версия / лоадер / ник
"""
import sys

from app import setup_launcher
from app.utils.config import Config
from app.utils.versions import Versions, build_launch_command, launch


def main():
    setup_launcher()

    config = Config()
    versions = Versions()

    args = sys.argv[1:]
    version = args[0] if len(args) > 0 else "1.21.1"
    fabric_loader_version = args[1] if len(args) > 1 else "0.16.10"
    username = args[2] if len(args) > 2 else "loka"
    fabric_id = f"fabric-loader-{fabric_loader_version}-{version}"

    installed = Versions.installed_versions(config.minecraft_directory)

    # Ванильная версия: ставим или докачиваем недостающие файлы
    versions.install_version(version, config.minecraft_directory)
    config.add_downloaded_version(version)

    if fabric_id not in installed:
        versions.install_fabric_version(version, fabric_loader_version, config.minecraft_directory)
        config.add_downloaded_version(fabric_id)
    config.set_fabric_loader_version(fabric_loader_version)

    command = build_launch_command(config, fabric_id, username)
    print("Команда для запуска Minecraft:", " ".join(command))
    sys.exit(launch(command, config.minecraft_directory).wait())


if __name__ == "__main__":
    main()
