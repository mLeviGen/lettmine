import json
import os

# Корень проекта (папка, где лежат main.py / app.py) — чтобы пути не зависели
# от текущей рабочей директории при запуске.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "app", "data")

DEFAULT_CONFIG = {
    "java_path": "",
    "launcher_path": "",
    "allocated_memory": 2,
    "downloaded_versions": [],
    "fabric_loader_version": "",
    "minecraft_directory": ".lettmine",
    "profiles": [],
}


class Config:
    def __init__(self):
        self.config_path = os.path.join(DATA_DIR, "config.json")
        self.styles_path = os.path.join(DATA_DIR, "styles.json")
        self.load_config()
        self.load_styles()

    def load_config(self):
        try:
            with open(self.config_path, "r", encoding="utf-8") as file:
                self.config = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            self.config = {}
        for key, value in DEFAULT_CONFIG.items():
            self.config.setdefault(key, list(value) if isinstance(value, list) else value)

    def save_config(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as file:
            json.dump(self.config, file, indent=4, ensure_ascii=False)

    def load_styles(self):
        try:
            with open(self.styles_path, "r", encoding="utf-8") as file:
                self.styles = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            self.styles = {}

    def save_styles(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(self.styles_path, "w", encoding="utf-8") as file:
            json.dump(self.styles, file, indent=4, ensure_ascii=False)

    @property
    def java_path(self):
        return self.config.get("java_path", "")

    @java_path.setter
    def java_path(self, value):
        self.config["java_path"] = value
        self.save_config()

    @property
    def launcher_path(self):
        return self.config.get("launcher_path", "")

    @launcher_path.setter
    def launcher_path(self, value):
        self.config["launcher_path"] = value
        self.save_config()

    @property
    def allocated_memory(self):
        return self.config.get("allocated_memory", 2)

    @allocated_memory.setter
    def allocated_memory(self, value):
        self.config["allocated_memory"] = value
        self.save_config()

    @property
    def downloaded_versions(self):
        return self.config.get("downloaded_versions", [])

    def add_downloaded_version(self, version):
        if version not in self.config["downloaded_versions"]:
            self.config["downloaded_versions"].append(version)
            self.save_config()

    @property
    def fabric_loader_version(self):
        return self.config.get("fabric_loader_version", "")

    @fabric_loader_version.setter
    def fabric_loader_version(self, value):
        self.config["fabric_loader_version"] = value
        self.save_config()

    def set_fabric_loader_version(self, value):
        self.fabric_loader_version = value

    @property
    def minecraft_directory(self):
        """Абсолютный путь к папке игры (относительные пути — от корня проекта)."""
        path = self.config.get("minecraft_directory", ".lettmine")
        if not os.path.isabs(path):
            path = os.path.join(BASE_DIR, path)
        return os.path.normpath(path)

    @minecraft_directory.setter
    def minecraft_directory(self, value):
        self.config["minecraft_directory"] = value
        self.save_config()

    def add_profile(self, profile):
        self.config["profiles"].append(profile)
        self.save_config()

    def remove_profile(self, profile_name):
        self.config["profiles"] = [
            p for p in self.config["profiles"] if p["name"] != profile_name
        ]
        self.save_config()

    def get_profiles(self):
        return self.config.get("profiles", [])

    def get_styles(self):
        return self.styles

    def set_style(self, key, value):
        self.styles[key] = value
        self.save_styles()
