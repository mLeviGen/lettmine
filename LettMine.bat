@echo off
rem Запуск LettMine. При первом запуске создаёт окружение, ставит зависимости,
rem собирает LettMine.exe (если есть MinGW) и ярлык с иконкой.
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".venv\Scripts\pythonw.exe" (
    echo Первый запуск: подготовка окружения...
    python -m venv .venv || (echo Не найден Python 3.11+. Установите его с python.org & pause & exit /b 1)
    ".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt || (echo Не удалось установить зависимости. & pause & exit /b 1)
)

if not exist ".venv\Scripts\LettMine.exe" (
    ".venv\Scripts\python.exe" tools\make_exe.py >nul 2>&1
)

if exist ".venv\Scripts\LettMine.exe" (
    start "" ".venv\Scripts\LettMine.exe"
) else (
    start "" ".venv\Scripts\pythonw.exe" app.py
)