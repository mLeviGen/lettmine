"""Перевод интерфейса. Строки в коде — русские, tr() подставляет английские.

Новую строку достаточно обернуть в tr() и добавить в EN; проверка полноты —
tools/check_i18n.py.
"""

LANGS = {"ru": "Русский", "en": "English"}
_lang = "ru"


def set_language(lang):
    global _lang
    _lang = lang if lang in LANGS else "ru"


def language():
    return _lang


def tr(text, **kw):
    s = EN.get(text, text) if _lang == "en" else text
    return s.format(**kw) if kw else s


EN = {
    # Меню и страницы
    "Главная": "Home",
    "Профили": "Profiles",
    "Лог": "Log",
    "Настройки": "Settings",
    "Свернуть": "Minimize",
    "Развернуть": "Maximize",
    "Восстановить": "Restore",
    "Закрыть": "Close",

    # Главная
    "АККАУНТ": "ACCOUNT",
    "ПРОФИЛЬ ДЛЯ ИГРЫ": "PROFILE TO PLAY",
    "Без регистрации": "Offline",
    "Лицензия": "Licensed",
    "Ваш ник": "Your nickname",
    "Без ника": "No nickname",
    "без регистрации · оффлайн": "offline · no account",
    "Введите ник, чтобы играть": "Enter a nickname to play",
    "Одиночная игра и серверы без проверки лицензии": "Singleplayer and servers without license checks",
    "3–16 символов: латиница, цифры и «_»": "3–16 characters: Latin letters, digits and “_”",
    "Вход не выполнен": "Not signed in",
    "лицензия Minecraft": "Minecraft license",
    "вход через аккаунт Microsoft": "sign in with a Microsoft account",
    "Завершите вход в открывшемся браузере…": "Finish signing in in the browser…",
    "Аккаунт сохранён — при запуске лаунчер сам обновит вход.":
        "Account saved — the launcher refreshes the sign-in on launch.",
    "Войдите аккаунтом Microsoft, на котором куплена Minecraft: Java Edition.":
        "Sign in with the Microsoft account that owns Minecraft: Java Edition.",
    "Войти через Microsoft": "Sign in with Microsoft",
    "Отмена": "Cancel",
    "Выйти": "Sign out",
    "Для входа по лицензии нужен Client ID приложения Azure.\n\nУкажите его в «Настройки → Вход по лицензии».":
        "Licensed sign-in needs an Azure app Client ID.\n\nSet it in “Settings → Licensed sign-in”.",
    "Ошибка": "Error",
    "Вход не выполнен.": "Sign-in failed.",
    "Создать профиль": "Create profile",
    "Нет профилей": "No profiles yet",
    "создайте первый на вкладке «Профили»": "create one on the Profiles tab",

    # Профили
    "Новый профиль": "New profile",
    "Профиль": "Profile",
    "Название": "Name",
    "Версия Minecraft": "Minecraft version",
    "Загрузчик": "Loader",
    "Память": "Memory",
    "как в настройках": "as in settings",
    "Моды": "Mods",
    "Моды доступны с загрузчиком Fabric.": "Mods are available with the Fabric loader.",
    "Снимите галочку, чтобы отключить мод.": "Uncheck a mod to disable it.",
    "Папка модов пуста": "The mods folder is empty",
    "Сохраните профиль, чтобы добавить моды.": "Save the profile to add mods.",
    "Сохранить": "Save",
    "Создать": "Create",
    "Удалить": "Delete",
    "Папка профиля": "Profile folder",
    "Папка модов": "Mods folder",
    "Обновить": "Refresh",
    "Назад": "Back",
    "Играть": "Play",
    "Изменить": "Edit",
    "Удалить профиль «{name}»?": "Delete profile “{name}”?",
    "Удалить и папку профиля с модами и мирами?": "Also delete the profile folder with mods and worlds?",
    "Введите название профиля.": "Enter a profile name.",
    "Выберите версию Minecraft.": "Choose a Minecraft version.",
    "Загрузка списка версий…": "Loading versions…",
    "Нет связи с серверами Mojang — доступны установленные версии.":
        "No connection to Mojang servers — installed versions only.",
    "Снапшоты": "Snapshots",
    "установлена": "installed",
    "Fabric {lv}": "Fabric {lv}",
    "Fabric · новейший": "Fabric · latest",
    "Основной": "Main",
    "{n} ГБ": "{n} GB",
    "Не удалось переименовать: {e}": "Could not rename: {e}",

    # Лог
    "Копировать": "Copy",
    "Очистить": "Clear",
    "Папка логов": "Logs folder",
    "Здесь появятся сообщения лаунчера и вывод игры.": "Launcher messages and game output appear here.",

    # Настройки
    "ЯЗЫК": "LANGUAGE",
    "ПАМЯТЬ": "MEMORY",
    "Оперативная память для игры по умолчанию": "Default game memory",
    "JAVA": "JAVA",
    "Автоматически — встроенная Java нужной версии": "Automatic — bundled Java of the right version",
    "Обзор": "Browse",
    "Авто": "Auto",
    "ПАПКА ИГРЫ": "GAME FOLDER",
    "Открыть": "Open",
    "Сменить": "Change",
    "ВХОД ПО ЛИЦЕНЗИИ": "LICENSED SIGN-IN",
    "Client ID приложения Azure": "Azure app Client ID",
    "Приложение Azure для личных аккаунтов Microsoft, платформа «Мобильные и настольные», адрес перенаправления {uri}. Доступ к Minecraft API для нового Client ID одобряет Mojang: aka.ms/mce-reviewappid":
        "Azure app for personal Microsoft accounts, “Mobile and desktop” platform, redirect URI {uri}. "
        "Mojang approves Minecraft API access for new Client IDs: aka.ms/mce-reviewappid",
    "АКЦЕНТНЫЙ ЦВЕТ": "ACCENT COLOR",
    "Свой цвет": "Custom",
    "Акцентный цвет": "Accent color",
    "Коралл": "Coral", "Персик": "Peach", "Сирень": "Lilac", "Мята": "Mint", "Небо": "Sky", "Лимон": "Lemon",
    "Выберите java.exe": "Choose java.exe",
    "Все файлы": "All files",

    # Запуск
    "Игра запущена": "Game is running",
    "Игра завершилась с ошибкой ({code}) — подробности во вкладке «Лог»":
        "The game exited with an error ({code}) — see the Log tab",
    "Игра закрыта": "Game closed",
    "Войдите через Microsoft на главной.": "Sign in with Microsoft on the Home tab.",
    "Введите ник на главной (3–16 символов: латиница, цифры, «_»).":
        "Enter a nickname on the Home tab (3–16 characters: Latin letters, digits, “_”).",
    "Создайте профиль на вкладке «Профили».": "Create a profile on the Profiles tab.",
    "Подготовка...": "Preparing...",
    "Не указан Client ID приложения Azure (Настройки → Вход по лицензии).":
        "Azure app Client ID is not set (Settings → Licensed sign-in).",
    "Вход в аккаунт Microsoft...": "Signing in to Microsoft...",
    "Профиль «{name}»: Minecraft {mc}, {loader}": "Profile “{name}”: Minecraft {mc}, {loader}",
    "Установка Minecraft {mc}...": "Installing Minecraft {mc}...",
    "Проверка файлов...": "Checking files...",
    "Fabric не поддерживает версию {mc}": "Fabric does not support {mc}",
    "Установка Fabric {lv}...": "Installing Fabric {lv}...",
    "Запуск...": "Launching...",
    "Команда запуска:": "Launch command:",
    "Ошибка:": "Error:",
    "Игра завершилась, код {code}": "Game exited with code {code}",

    # Аккаунт (ошибки входа)
    "Приложению Azure не разрешён доступ к Minecraft API. Новые Client ID нужно одобрить у Mojang: https://aka.ms/mce-reviewappid":
        "The Azure app is not allowed to use the Minecraft API. New Client IDs must be approved by Mojang: "
        "https://aka.ms/mce-reviewappid",
    "На этом аккаунте Microsoft нет купленной Minecraft: Java Edition.":
        "This Microsoft account does not own Minecraft: Java Edition.",
    "Сессия устарела — войдите через Microsoft ещё раз.": "Session expired — sign in with Microsoft again.",
    "Нет соединения с серверами Microsoft.": "No connection to Microsoft servers.",
    "Порт {port} занят — закройте программу, которая его использует.":
        "Port {port} is busy — close the program that uses it.",
    "Вход не завершён — время ожидания истекло.": "Sign-in was not completed — timed out.",
}
