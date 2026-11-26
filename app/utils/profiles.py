"""Профили-сборки: версия игры, загрузчик и своя папка (моды, миры, настройки).

Версии, библиотеки, ассеты и Java общие — лежат в папке игры (.lettmine) один раз.
Папка профиля — .lettmine/instances/<id>; у перенесённого «Основного» профиля
это сама .lettmine, чтобы старые моды и миры остались на месте.
"""
import os
import re
import shutil
import uuid as uuid_mod

from app.i18n import tr

VANILLA, FABRIC = "vanilla", "fabric"


def version_id(profile):
    if profile.get("loader") == FABRIC and profile.get("loader_version"):
        return f"fabric-loader-{profile['loader_version']}-{profile['mc']}"
    return profile["mc"]


def parse_version_id(vid):
    m = re.match(r"fabric-loader-([\d.]+)-(.+)", vid or "")
    if m:
        return m.group(2), FABRIC, m.group(1)
    return vid, VANILLA, None


def game_dir(config, profile):
    if profile.get("dir") == "":
        return config.minecraft_directory
    return os.path.join(config.minecraft_directory, "instances", profile["id"])


def mods_dir(config, profile):
    path = os.path.join(game_dir(config, profile), "mods")
    os.makedirs(path, exist_ok=True)
    return path


def _slug(name):
    s = re.sub(r"[^A-Za-z0-9_-]+", "-", name.strip().lower()).strip("-")
    return s[:24] or "profile"


def get_profiles(config):
    """Список профилей; при первом запуске — «Основной» из последней выбранной версии."""
    cfg = config.config
    if "instances" not in cfg:
        last = cfg.get("last_version")
        if last:
            mc, loader, lv = parse_version_id(last)
            cfg["instances"] = [{
                "id": "main", "name": tr("Основной"), "mc": mc, "loader": loader,
                "loader_version": lv, "dir": "", "memory": 0,
            }]
            cfg["selected_instance"] = "main"
        else:
            cfg["instances"] = []
        cfg.pop("last_version", None)
        config.save_config()
    return cfg["instances"]


def get(config, pid):
    return next((p for p in get_profiles(config) if p["id"] == pid), None)


def selected(config):
    profiles = get_profiles(config)
    p = get(config, config.config.get("selected_instance"))
    return p or (profiles[0] if profiles else None)


def select(config, pid):
    config.config["selected_instance"] = pid
    config.save_config()


def create(config, name, mc, loader, memory=0):
    profiles = get_profiles(config)
    base = _slug(name)
    pid = base
    while any(p["id"] == pid for p in profiles):
        pid = f"{base}-{uuid_mod.uuid4().hex[:4]}"
    profile = {"id": pid, "name": name.strip(), "mc": mc, "loader": loader,
               "loader_version": None, "memory": memory}
    profiles.append(profile)
    os.makedirs(mods_dir(config, profile), exist_ok=True)
    select(config, pid)
    config.save_config()
    return profile


def update(config, pid, **changes):
    p = get(config, pid)
    if p is None:
        return None
    if ("mc" in changes and changes["mc"] != p["mc"]) or ("loader" in changes and changes["loader"] != p["loader"]):
        changes.setdefault("loader_version", None)  # другой загрузчик/версия — поставим свежий Fabric
    p.update(changes)
    config.save_config()
    return p


def delete(config, pid, remove_files=False):
    p = get(config, pid)
    if p is None:
        return
    if remove_files and p.get("dir") != "":
        shutil.rmtree(game_dir(config, p), ignore_errors=True)
    config.config["instances"] = [x for x in get_profiles(config) if x["id"] != pid]
    if config.config.get("selected_instance") == pid:
        rest = config.config["instances"]
        config.config["selected_instance"] = rest[0]["id"] if rest else None
    config.save_config()


def icon(config, profile):
    """Иконка профиля для отрисовки: {"emoji": …} или {"image": абсолютный путь}; None — обычная."""
    ic = (profile or {}).get("icon")
    if not ic:
        return None
    if ic.get("image"):
        path = os.path.join(game_dir(config, profile), ic["image"])
        return {"image": path} if os.path.isfile(path) else None
    return dict(ic)


def set_image_icon(config, pid, source):
    """Копирует выбранную картинку в папку профиля (profile-icon.*) и делает её иконкой."""
    p = get(config, pid)
    if p is None or not os.path.isfile(source):
        return
    folder = game_dir(config, p)
    os.makedirs(folder, exist_ok=True)
    for old in os.listdir(folder):
        if old.startswith("profile-icon."):
            os.remove(os.path.join(folder, old))
    ext = os.path.splitext(source)[1].lower() or ".png"
    name = "profile-icon" + ext
    shutil.copyfile(source, os.path.join(folder, name))
    p["icon"] = {"image": name}
    config.save_config()
