"""Проверяет, что у всех строк tr("...") в коде есть английский перевод.

    .venv\\Scripts\\python tools\\check_i18n.py
"""
import ast
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app.i18n import EN  # noqa: E402


def strings(path):
    tree = ast.parse(open(path, encoding="utf-8").read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "tr" and node.args:
            arg = node.args[0]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                yield node.lineno, arg.value
    # Списки, которые переводятся через tr(переменная): шутки главной (FUN, второй
    # элемент) и названия цветов (ACCENT_PRESETS, первый). Читаем из кода, без импорта —
    # так проверка работает и там, где PyQt6 не установлен (сборка релиза).
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            name = getattr(node.targets[0], "id", None)
            if name in ("FUN", "ACCENT_PRESETS"):
                for pair in ast.literal_eval(node.value):
                    yield node.lineno, pair[1] if name == "FUN" else pair[0]


missing = []
for folder, _, files in os.walk(os.path.join(ROOT, "app")):
    for f in files:
        if f.endswith(".py"):
            path = os.path.join(folder, f)
            for line, s in strings(path):
                if s not in EN:
                    missing.append(f"{os.path.relpath(path, ROOT)}:{line}: {s!r}")

print("\n".join(missing) if missing else "Все строки переведены.")
sys.exit(1 if missing else 0)
