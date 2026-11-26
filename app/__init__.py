"""Пакет лаунчера.

Здесь ничего не импортируется заранее: app.version и app.i18n должны читаться
без зависимостей (их используют сборка exe и релиза, где PyQt6 и
minecraft-launcher-lib не установлены).
"""


def setup_launcher():
    """Подготовить папку игры: launcher_profiles.json и нужные папки."""
    from .utils.config import Config
    from .utils.launcher import check_launcher_files, create_launcher_profiles

    config = Config()
    create_launcher_profiles(config)
    check_launcher_files(config)
