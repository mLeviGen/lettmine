/*
 * LettMine.exe — запускатель лаунчера.
 *
 * Запускает Python прямо в своём процессе (Py_Main из python3.dll), поэтому в диспетчере
 * задач и на панели задач приложение называется LettMine и имеет свою иконку, а не «Python».
 *
 * Лежит в .venv\Scripts\: рядом с родительской папкой есть pyvenv.cfg, по нему Python
 * находит и стандартную библиотеку (home = ...), и пакеты окружения (.venv\Lib\site-packages).
 * Скрипт — <папка проекта>\app.py. Собирается tools\make_exe.py.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <shellapi.h>
#include <stdio.h>
#include <wchar.h>

typedef int (*PyMainFn)(int, wchar_t **);

static void fail(const wchar_t *msg) {
    MessageBoxW(NULL, msg, L"LettMine", MB_ICONERROR | MB_OK);
}

static void parent_dir(wchar_t *path) {
    wchar_t *slash = wcsrchr(path, L'\\');
    if (slash) *slash = 0;
}

static int read_home(const wchar_t *cfg_path, wchar_t *home, size_t size) {
    FILE *f = _wfopen(cfg_path, L"r, ccs=UTF-8");
    wchar_t line[1024];
    if (!f) return 0;
    while (fgetws(line, 1024, f)) {
        wchar_t *eq;
        if (wcsncmp(line, L"home", 4) != 0 || !(eq = wcschr(line, L'='))) continue;
        eq++;
        while (*eq == L' ' || *eq == L'\t') eq++;
        size_t n = wcslen(eq);
        while (n && (eq[n - 1] == L'\n' || eq[n - 1] == L'\r' || eq[n - 1] == L' ')) eq[--n] = 0;
        wcsncpy(home, eq, size - 1);
        home[size - 1] = 0;
        fclose(f);
        return 1;
    }
    fclose(f);
    return 0;
}

int WINAPI wWinMain(HINSTANCE inst, HINSTANCE prev, PWSTR cmd, int show) {
    (void)inst; (void)prev; (void)cmd; (void)show;
    wchar_t exe[MAX_PATH], venv[MAX_PATH], root[MAX_PATH], cfg[MAX_PATH], home[MAX_PATH], script[MAX_PATH];

    GetModuleFileNameW(NULL, exe, MAX_PATH);
    wcscpy(venv, exe);
    parent_dir(venv);           /* ...\.venv\Scripts */
    parent_dir(venv);           /* ...\.venv */
    wcscpy(root, venv);
    parent_dir(root);           /* папка проекта */

    swprintf(cfg, MAX_PATH, L"%ls\\pyvenv.cfg", venv);
    if (!read_home(cfg, home, MAX_PATH)) {
        fail(L"Не найден .venv\\pyvenv.cfg. Запустите LettMine.bat, чтобы подготовить окружение.");
        return 1;
    }

    /* python3.dll перенаправляет вызовы в python3XX.dll — версия Python не зашита */
    SetDllDirectoryW(home);
    wchar_t dll[MAX_PATH];
    swprintf(dll, MAX_PATH, L"%ls\\python3.dll", home);
    HMODULE py = LoadLibraryW(dll);
    if (!py) {
        fail(L"Не удалось загрузить Python (python3.dll). Проверьте, что Python установлен.");
        return 1;
    }
    PyMainFn py_main = (PyMainFn)GetProcAddress(py, "Py_Main");
    if (!py_main) {
        fail(L"В python3.dll нет Py_Main.");
        return 1;
    }

    swprintf(script, MAX_PATH, L"%ls\\app.py", root);
    SetCurrentDirectoryW(root);

    int argc;
    wchar_t **cmd_argv = CommandLineToArgvW(GetCommandLineW(), &argc);
    wchar_t *argv[64];
    int n = 0;
    argv[n++] = exe;
    argv[n++] = script;
    for (int i = 1; i < argc && n < 63; i++) argv[n++] = cmd_argv[i];
    argv[n] = NULL;
    return py_main(n, argv);
}
