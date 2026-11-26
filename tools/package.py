"""Собирает архив релиза: dist/LettMine-<версия>-windows.zip.

    .venv\\Scripts\\python tools\\package.py

В архиве — папка LettMine с кодом, ресурсами, LettMine.exe (если собран) и
LettMine.bat. Личные настройки (config.json, styles.json), окружение .venv
и данные игры в архив не попадают.
"""
import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from app.version import VERSION  # noqa: E402

INCLUDE = ["app", "tools", "docs", "app.py", "main.py", "requirements.txt", "LettMine.bat",
           "LettMine.exe", "README.md", "LICENSE"]
SKIP_DIRS = {"__pycache__"}
SKIP_FILES = {os.path.join("app", "data", "config.json"), os.path.join("app", "data", "styles.json")}
SKIP_EXT = {".pyc", ".res", ".lnk"}


def files():
    for item in INCLUDE:
        path = os.path.join(ROOT, item)
        if os.path.isfile(path):
            yield item
        elif os.path.isdir(path):
            for folder, dirs, names in os.walk(path):
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
                for name in names:
                    rel = os.path.relpath(os.path.join(folder, name), ROOT)
                    if rel in SKIP_FILES or os.path.splitext(name)[1] in SKIP_EXT:
                        continue
                    yield rel


def main():
    out_dir = os.path.join(ROOT, "dist")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f"LettMine-{VERSION}-windows.zip")
    count = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in files():
            z.write(os.path.join(ROOT, rel), os.path.join("LettMine", rel))
            count += 1
    print(f"Архив: {out} ({count} файлов, {os.path.getsize(out) // 1024} КБ)")
    if not os.path.isfile(os.path.join(ROOT, "LettMine.exe")):
        print("Внимание: LettMine.exe не собран — в архиве только запуск через LettMine.bat.")


if __name__ == "__main__":
    main()
