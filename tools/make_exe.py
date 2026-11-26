"""Собирает LettMine.exe в папке проекта и ярлык LettMine.lnk с иконкой.

Нужен компилятор MinGW (gcc + windres), например из MSYS2:
    .venv\\Scripts\\python tools\\make_exe.py
    .venv\\Scripts\\python tools\\make_exe.py --no-shortcut   # только exe (для сборки релиза)

Без компилятора лаунчер всё равно работает через pythonw (LettMine.bat), только
в диспетчере задач он будет называться «Python».
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from app.version import VERSION  # noqa: E402

SRC = os.path.join(ROOT, "tools", "launcher")
VENV_SCRIPTS = os.path.join(ROOT, ".venv", "Scripts")
EXE = os.path.join(ROOT, "LettMine.exe")  # рядом с app.py — из него удобно делать ярлык
OLD_EXE = os.path.join(VENV_SCRIPTS, "LettMine.exe")  # прежнее место
SHORTCUT = os.path.join(ROOT, "LettMine.lnk")
MSYS_BINS = (r"C:\msys64\mingw64\bin", r"C:\msys64\ucrt64\bin")


def find_tool(name):
    path = shutil.which(name)
    if path:
        return path
    for folder in MSYS_BINS:
        candidate = os.path.join(folder, name + ".exe")
        if os.path.isfile(candidate):
            return candidate
    return None


def version_defines():
    parts = [int(x) for x in VERSION.split(".")[:3]] + [0, 0, 0]
    num = ",".join(str(x) for x in parts[:4])
    return [f"-DVER_NUM={num}", f'-DVER_STR=\\"{VERSION}\\"']


def build():
    gcc, windres = find_tool("gcc"), find_tool("windres")
    if not gcc or not windres:
        print("Не найден MinGW (gcc/windres) — LettMine.exe не собран.")
        return False
    env = dict(os.environ)
    env["PATH"] = os.path.dirname(gcc) + os.pathsep + env.get("PATH", "")
    res = os.path.join(SRC, "launcher.res")
    subprocess.run([windres, *version_defines(), "launcher.rc", "-O", "coff", "-o", res],
                   cwd=SRC, env=env, check=True)
    subprocess.run([gcc, "-O2", "-municode", "-mwindows", "-static", "launcher.c", res, "-lshell32", "-o", EXE],
                   cwd=SRC, env=env, check=True)
    os.remove(res)
    if os.path.isfile(OLD_EXE):
        os.remove(OLD_EXE)
    print(f"Собран: {EXE} (версия {VERSION})")
    return True


def make_shortcut(target, args=""):
    """Ярлык в папке проекта (его можно скопировать на рабочий стол или закрепить)."""
    icon = os.path.join(ROOT, "app", "assets", "icon.ico")
    ps = (
        "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{lnk}');"
        "$s.TargetPath='{target}';$s.Arguments='{args}';$s.WorkingDirectory='{root}';"
        "$s.IconLocation='{icon}';$s.Description='LettMine';$s.Save()"
    ).format(lnk=SHORTCUT, target=target, args=args, root=ROOT, icon=icon)
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True)
    print("Ярлык:", SHORTCUT)


if __name__ == "__main__":
    if os.name != "nt":
        sys.exit("Только для Windows.")
    built = build()
    if "--no-shortcut" in sys.argv:
        sys.exit(0 if built else 1)
    if built:
        make_shortcut(EXE)
    else:
        make_shortcut(os.path.join(VENV_SCRIPTS, "pythonw.exe"), "app.py")
