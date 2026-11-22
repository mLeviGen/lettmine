import json

import os
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "config.json")


def load_config():
    # Загрузка конфигурации из config.json
    try:
        with open(CONFIG_PATH, "r") as file:
            config = json.load(file)
            return config
    except FileNotFoundError:
        print("Config file not found, using default config.")
        return {}


def save_config(config):
    # Сохранение конфигурации в config.json
    with open(CONFIG_PATH, "w") as file:
        json.dump(config, file, indent=4)
    print("Config saved:", config)


def update_config(config, key, value):
    config[key] = value
    save_config(config)
