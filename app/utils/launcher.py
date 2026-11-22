import os
import json


def create_launcher_profiles(config):
    """Fabric-установщику нужен launcher_profiles.json в папке игры."""
    os.makedirs(config.minecraft_directory, exist_ok=True)
    launcher_profiles_path = os.path.join(config.minecraft_directory, "launcher_profiles.json")
    if not os.path.exists(launcher_profiles_path):
        profiles = {
            "profiles": {},
            "settings": {"settingsVersion": 1, "locale": "en-US"},
            "version": 3,
        }
        with open(launcher_profiles_path, "w", encoding="utf-8") as file:
            json.dump(profiles, file, indent=4)
        print(f"Создан файл {launcher_profiles_path}")


def check_and_create_directories(config):
    for directory in ("mods", "shaderpacks", "resourcepacks", "config"):
        os.makedirs(os.path.join(config.minecraft_directory, directory), exist_ok=True)


def check_launcher_files(config):
    check_and_create_directories(config)
    if config.java_path and not os.path.isfile(config.java_path):
        print(f"Java из настроек не найдена ({config.java_path}) — будет выбрана автоматически.")
