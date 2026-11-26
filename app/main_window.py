import ctypes
import html
import os

from PyQt6.QtCore import QEvent, QPoint, Qt, QTimer, QUrl
from PyQt6.QtGui import QColor, QDesktopServices, QFont, QGuiApplication
from PyQt6.QtWidgets import (
    QApplication, QButtonGroup, QBoxLayout, QCheckBox, QColorDialog, QComboBox, QFileDialog,
    QGridLayout, QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem,
    QMainWindow, QMenu, QMessageBox, QPlainTextEdit, QScrollArea, QSpinBox, QStackedWidget,
    QVBoxLayout, QWidget,
)

from app import i18n
from app.i18n import tr
from app.ui import theme as th
from app.ui import winframe
from app.ui.logbus import bus, log
from app.ui.widgets import (
    G, Avatar, Button3D, Card, ColorChip, EmptyHint, FlowGrid, IconChip, LaunchStatus, NavRail, PageFade,
    Panel, Segmented, TitleBar, label, logo_icon,
)
from app.ui.worker import GameWorker, LoginWorker, VersionListWorker
from app.utils import account as acc_mod
from app.utils import profiles as prof
from app.utils.config import Config
from app.utils.versions import Versions

APP_TITLE = "LettMine"
from app.version import VERSION as APP_VERSION  # noqa: E402
NARROW = 720  # уже этого (без меню) — блоки перестраиваются в колонку

PROFILE_EMOJI = ["⛏️", "🗡️", "🏰", "🌲", "💎", "🔥", "🐷", "🧱", "🍄", "🐉", "🌙", "⚡"]

FUN = [
    ("^_^", "Алмазы сами себя не накопают"),
    ("\\(^o^)/", "Сегодня точно без лавы"),
    ("¯\\_(ツ)_/¯", "Где мой дом? Где-то там"),
    ("(¬‿¬)", "Свинья одобряет этот лаунчер"),
    ("(-_-) zzZ", "Ещё один блок — и спать"),
    ("(⌐■_■)", "Криперы не пройдут"),
    ("(o_O)", "Копать вниз — плохая идея. Но мы копаем"),
    ("(•‿•)", "Не забудь взять кровать"),
]

_windows = []  # держим ссылку на окно (при смене языка создаётся новое)


def scroll_page():
    """Страница со скроллом; возвращает (scroll, вертикальный layout содержимого)."""
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    body = QWidget()
    lay = QVBoxLayout(body)
    lay.setContentsMargins(th.EDGE, 4, th.EDGE * 2, th.EDGE)
    lay.setSpacing(12)
    area.setWidget(body)
    return area, lay


def plain_page():
    page = QWidget()
    lay = QVBoxLayout(page)
    lay.setContentsMargins(th.EDGE, 4, th.EDGE * 2, 0)
    lay.setSpacing(12)
    return page, lay


def wrap_label(text, role="hint"):
    lbl = label(text, role)
    lbl.setWordWrap(True)
    return lbl


def profile_subtitle(p):
    loader = "Fabric" if p.get("loader") == prof.FABRIC else "Vanilla"
    return f"Minecraft {p['mc']} · {loader}"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = Config()
        i18n.set_language(self.config.config.get("language", "ru"))
        self.theme = th.resolve(self.config.get_styles())
        self.worker = None
        self.login_worker = None
        self.version_worker = None
        self.current_page = None
        self.editing = None  # id редактируемого профиля, None — новый
        self.pending_version = None
        self.available_versions = []
        self.home_cards, self.list_cards = {}, {}
        self._home_sig = self._list_sig = None  # профили не пересоздаются без изменений
        self.ed_icon = None          # иконка профиля в редакторе
        self.ed_icon_file = None     # выбранная картинка (ещё не скопирована)
        self.account = acc_mod.get_account(self.config)
        prof.get_profiles(self.config)  # перенос старых настроек в профили

        self.setWindowTitle(APP_TITLE)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setMinimumSize(640, 520)
        self.fit_to_work_area(1080, 740)

        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, th.EDGE)
        outer.setSpacing(0)

        self.title_bar = TitleBar(APP_TITLE)
        outer.addWidget(self.title_bar)

        middle = QHBoxLayout()
        middle.setContentsMargins(th.EDGE, th.EDGE, 0, th.EDGE)
        middle.setSpacing(th.EDGE)
        self.nav = NavRail()
        self.nav.add_item("home", G.HOME, tr("Главная"))
        self.nav.add_item("profiles", G.LIBRARY, tr("Профили"))
        self.nav.add_item("log", G.LOG, tr("Лог"))
        self.nav.add_separator()
        self.nav.add_item("settings", G.SETTINGS, tr("Настройки"))
        nav_col = QVBoxLayout()
        nav_col.addStretch(1)
        nav_col.addWidget(self.nav)
        nav_col.addStretch(1)
        middle.addLayout(nav_col)

        self.stack = QStackedWidget()
        middle.addWidget(self.stack, 1)
        outer.addLayout(middle, 1)
        outer.addLayout(self.build_bottom_bar())

        self.pages = {
            "home": self.build_home(),
            "profiles": self.build_profiles(),
            "log": self.build_log(),
            "settings": self.build_settings(),
        }
        for page in self.pages.values():
            self.stack.addWidget(page)

        self.nav.page_selected.connect(self.open_page)
        bus.game_exited.connect(self.on_game_exited)

        QApplication.instance().installEventFilter(self)
        self.apply_theme()
        self.refresh_home()
        self.refresh_profiles()
        self.open_page("home", animate=False)
        self.update_play_state()
        QTimer.singleShot(0, lambda: winframe.install(self))

    # ---------- настройки ----------
    def setting(self, key, default=None):
        return self.config.config.get(key, default)

    def set_setting(self, key, value):
        self.config.config[key] = value
        self.config.save_config()

    @property
    def player_name(self):
        return acc_mod.display_name(self.account)

    @property
    def client_id(self):
        return self.setting("microsoft_client_id", "").strip()

    # ---------- навигация ----------
    def open_page(self, key, animate=True):
        if key == self.current_page:
            if key == "profiles" and self.profiles_stack.currentIndex() != 0:
                self.show_profile_list()
            return
        self.current_page = key
        page = self.pages[key]
        self.stack.setCurrentWidget(page)
        self.nav.select(key, animate)
        if key == "home":
            self.refresh_home()
        elif key == "profiles":
            self.refresh_profiles()
        if animate:
            self.animate_page(page)

    @staticmethod
    def settle_layout(page):
        """Рассчитать раскладку страницы сейчас, до первого кадра: иначе карточки
        несколько кадров стоят «как попало» и проскакивают на место."""
        parent = page.parentWidget()
        if parent is not None:
            # Скрытая страница стека хранит старую геометрию (по умолчанию 640×480) —
            # без этого она на мгновение рисуется не того размера и «съезжает»
            page.setGeometry(parent.rect())
        for _ in range(3):  # вложенные раскладки (страница → скролл → сетка) — по цепочке
            QApplication.sendPostedEvents(None, QEvent.Type.LayoutRequest)
            for lay in [page.layout()] + [w.layout() for w in page.findChildren(QWidget)]:
                if lay is not None:
                    lay.activate()

    def animate_page(self, page):
        """Появление страницы: проявление и лёгкий сдвиг снизу (как меню в Lettudio)."""
        self.settle_layout(page)
        parent = page.parentWidget()
        fader = getattr(parent, "_fader", None)
        if fader is None:
            fader = parent._fader = PageFade(parent)
        fader.start(self.snapshot(page))

    def snapshot(self, page):
        """Снимок области страницы прямо из окна — с настоящим фоном, как на экране."""
        from PyQt6.QtCore import QRect
        top_left = page.mapTo(self, QPoint(0, 0))
        return self.grab(QRect(top_left, page.size()))

    # ---------- главная ----------
    def build_home(self):
        area, lay = scroll_page()
        lay.addWidget(label(tr("АККАУНТ"), "section"))
        lay.addWidget(self.build_account())
        lay.addSpacing(th.EDGE)
        lay.addWidget(label(tr("ПРОФИЛЬ ДЛЯ ИГРЫ"), "section"))
        self.home_grid = FlowGrid()
        lay.addWidget(self.home_grid)
        self.home_hint = EmptyHint([(face, tr(text)) for face, text in FUN])
        lay.addWidget(self.home_hint, 1)
        return area

    def profile_avatar(self, p, size=46):
        glyph = G.MODS if p.get("loader") == prof.FABRIC else G.GAME
        return Avatar(glyph=glyph, round_=False, icon=prof.icon(self.config, p), size=size)

    @staticmethod
    def profiles_signature(profiles, current):
        return (tuple((p["id"], p["name"], p["mc"], p.get("loader"), repr(p.get("icon"))) for p in profiles),
                current["id"] if current else None, i18n.language())

    def profile_card(self, p, on_click):
        card = Card(p["name"], profile_subtitle(p), self.profile_avatar(p))
        pid = p["id"]
        card.clicked.connect(lambda: on_click(pid))
        card.context_requested.connect(lambda pos: self.profile_menu(pid, pos))
        return card

    def refresh_home(self):
        self.refresh_account()
        current = prof.selected(self.config)
        profiles = prof.get_profiles(self.config)
        sig = self.profiles_signature(profiles, current)
        if sig == self._home_sig:  # ничего не поменялось — карточки остаются на месте
            self.update_play_state()
            return
        self._home_sig = sig
        cards = []
        self.home_cards = {}
        for p in prof.get_profiles(self.config):
            card = self.profile_card(p, self.select_profile)
            card.set_selected(bool(current) and p["id"] == current["id"])
            self.home_cards[p["id"]] = card
            cards.append(card)
        if not cards:
            empty = Card(tr("Нет профилей"), tr("создайте первый на вкладке «Профили»"),
                         Avatar(glyph=G.ADD, round_=False))
            empty.clicked.connect(self.new_profile_from_home)
            cards.append(empty)
        self.home_grid.set_items(cards)
        self.update_play_state()

    def new_profile_from_home(self):
        self.open_page("profiles")
        self.edit_profile(None)

    def select_profile(self, pid):
        prof.select(self.config, pid)
        profiles, current = prof.get_profiles(self.config), prof.selected(self.config)
        if self._home_sig is not None:
            self._home_sig = self.profiles_signature(profiles, current)
        if self._list_sig is not None:
            self._list_sig = self.profiles_signature(profiles, current)
        for cid, card in self.home_cards.items():
            card.set_selected(cid == pid, animate=True)
        for cid, card in self.list_cards.items():
            card.set_selected(cid == pid, animate=True)
        self.update_play_state()

    def profile_menu(self, pid, pos):
        menu = QMenu(self)
        menu.addAction(tr("Играть"), lambda: (self.select_profile(pid), self.launch_game()))
        menu.addAction(tr("Изменить"), lambda: (self.open_page("profiles"), self.edit_profile(pid)))
        menu.addAction(tr("Удалить"), lambda: self.delete_profile(pid))
        menu.exec(pos)

    # ---------- аккаунт ----------
    def build_account(self):
        panel = Panel()
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(12, 12, 12, 14)
        lay.setSpacing(12)

        self.account_top = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self.account_top.setSpacing(14)
        who = QHBoxLayout()
        who.setSpacing(14)
        self.account_avatar = Avatar("?")
        who.addWidget(self.account_avatar)
        texts = QVBoxLayout()
        texts.setSpacing(0)
        self.account_title = label("", "title")
        self.account_sub = label("", "subtitle")
        texts.addStretch()
        texts.addWidget(self.account_title)
        texts.addWidget(self.account_sub)
        texts.addStretch()
        who.addLayout(texts, 1)
        self.account_top.addLayout(who, 1)
        self.account_mode = Segmented([tr("Без регистрации"), tr("Лицензия")])
        self.account_mode.changed.connect(self.set_account_mode)
        self.account_top.addWidget(self.account_mode, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        lay.addLayout(self.account_top)

        # Два режима — два блока; показан только один (скрытый не держит ширину/высоту)
        offline = QWidget()
        self.offline_page = offline
        self.offline_row = QBoxLayout(QBoxLayout.Direction.LeftToRight, offline)
        self.offline_row.setContentsMargins(0, 0, 0, 0)
        self.offline_row.setSpacing(th.EDGE)
        self.nick_edit = QLineEdit(self.account.get("offline_name", ""))
        self.nick_edit.setPlaceholderText(tr("Ваш ник"))
        self.nick_edit.setMaxLength(16)
        self.nick_edit.setMinimumWidth(180)
        self.nick_edit.setMaximumWidth(280)
        self.nick_edit.textChanged.connect(self.nick_changed)
        self.nick_hint = wrap_label("")
        self.offline_row.addWidget(self.nick_edit)
        self.offline_row.addWidget(self.nick_hint, 1)
        lay.addWidget(offline)

        licensed = QWidget()
        self.licensed_page = licensed
        self.licensed_row = QBoxLayout(QBoxLayout.Direction.LeftToRight, licensed)
        self.licensed_row.setContentsMargins(0, 0, 0, 0)
        self.licensed_row.setSpacing(th.EDGE)
        self.ms_hint = wrap_label("")
        self.ms_login_btn = Button3D(tr("Войти через Microsoft"), G.PERSON, "accent")
        self.ms_login_btn.clicked.connect(self.microsoft_login)
        self.ms_cancel_btn = Button3D(tr("Отмена"))
        self.ms_cancel_btn.clicked.connect(self.cancel_login)
        self.ms_logout_btn = Button3D(tr("Выйти"))
        self.ms_logout_btn.clicked.connect(self.microsoft_logout)
        self.licensed_row.addWidget(self.ms_hint, 1)
        btns = QHBoxLayout()
        btns.setSpacing(0)
        for b in (self.ms_cancel_btn, self.ms_logout_btn, self.ms_login_btn):
            btns.addWidget(b)
        self.licensed_row.addLayout(btns)
        lay.addWidget(licensed)
        return panel

    def refresh_account(self, animate=False):
        acc = self.account
        licensed = acc["type"] == acc_mod.MICROSOFT
        self.account_mode.set_index(1 if licensed else 0, animate)
        self.offline_page.setVisible(not licensed)
        self.licensed_page.setVisible(licensed)
        name = self.player_name
        self.account_avatar.text = name or "?"
        self.account_avatar.update()
        ms = acc.get("microsoft")
        logging_in = bool(self.login_worker and self.login_worker.isRunning())
        if licensed:
            self.account_title.setText(name or tr("Вход не выполнен"))
            self.account_sub.setText(tr("лицензия Minecraft") if ms else tr("вход через аккаунт Microsoft"))
            if logging_in:
                self.ms_hint.setText(tr("Завершите вход в открывшемся браузере…"))
            elif ms:
                self.ms_hint.setText(tr("Аккаунт сохранён — при запуске лаунчер сам обновит вход."))
            else:
                self.ms_hint.setText(tr("Войдите аккаунтом Microsoft, на котором куплена Minecraft: Java Edition."))
        self.ms_login_btn.setVisible(licensed and not ms and not logging_in)
        self.ms_cancel_btn.setVisible(licensed and logging_in)
        self.ms_logout_btn.setVisible(licensed and bool(ms) and not logging_in)
        if not licensed:
            self.account_title.setText(name or tr("Без ника"))
            self.account_sub.setText(tr("без регистрации · оффлайн"))
            self.update_nick_hint()
        self.update_play_state()

    def update_nick_hint(self):
        nick = self.nick_edit.text().strip()
        if not nick:
            self.nick_hint.setText(tr("Введите ник, чтобы играть"))
        elif acc_mod.valid_nick(nick):
            self.nick_hint.setText(tr("Одиночная игра и серверы без проверки лицензии"))
        else:
            self.nick_hint.setText(tr("3–16 символов: латиница, цифры и «_»"))

    def nick_changed(self, text):
        nick = text.strip()
        if acc_mod.valid_nick(nick) or not nick:
            self.account = acc_mod.save_account(self.config, offline_name=nick)
        self.account_title.setText(nick or tr("Без ника"))
        self.account_avatar.text = nick or "?"
        self.account_avatar.update()
        self.update_nick_hint()
        self.update_play_state()

    def set_account_mode(self, index):
        self.account = acc_mod.save_account(self.config, type=acc_mod.MICROSOFT if index else acc_mod.OFFLINE)
        self.refresh_account(animate=True)

    def microsoft_login(self):
        if not self.client_id:
            QMessageBox.information(self, APP_TITLE, tr(
                "Для входа по лицензии нужен Client ID приложения Azure.\n\n"
                "Укажите его в «Настройки → Вход по лицензии»."))
            self.open_page("settings")
            return
        try:
            url, state, verifier = acc_mod.start_login(self.client_id)
        except Exception as e:
            QMessageBox.critical(self, tr("Ошибка"), acc_mod.explain_error(e))
            return
        self.login_worker = LoginWorker(self.client_id, state, verifier)
        self.login_worker.succeeded.connect(self.on_login)
        self.login_worker.failed.connect(lambda msg: QMessageBox.critical(self, tr("Вход не выполнен."), msg))
        self.login_worker.finished.connect(self.refresh_account)
        self.login_worker.start()
        QDesktopServices.openUrl(QUrl(url))
        self.refresh_account()

    def cancel_login(self):
        if self.login_worker:
            self.login_worker.cancelled = True

    def on_login(self, data):
        self.account = acc_mod.save_account(self.config, microsoft=data)
        self.refresh_account()

    def on_account_refreshed(self, data):
        self.account = acc_mod.save_account(self.config, microsoft=data)
        self.refresh_account()

    def microsoft_logout(self):
        self.account = acc_mod.save_account(self.config, microsoft=None)
        self.refresh_account()

    # ---------- профили ----------
    def build_profiles(self):
        self.profiles_stack = QStackedWidget()

        # Список профилей
        area, lay = scroll_page()
        head = QHBoxLayout()
        head.setSpacing(0)
        head.addWidget(label(tr("Профили"), "pageTitle"), 1)
        create = Button3D(tr("Создать профиль"), G.ADD, "accent")
        create.clicked.connect(lambda: self.edit_profile(None))
        head.addWidget(create)
        lay.addLayout(head)
        self.list_grid = FlowGrid()
        lay.addWidget(self.list_grid)
        lay.addStretch()
        self.profiles_stack.addWidget(area)

        # Редактор профиля
        area, lay = scroll_page()
        head = QHBoxLayout()
        head.setSpacing(6)
        back = Button3D("", G.BACK)
        back.setToolTip(tr("Назад"))
        back.clicked.connect(self.show_profile_list)
        head.addWidget(back)
        self.editor_title = label("", "pageTitle")
        head.addWidget(self.editor_title, 1)
        self.ed_delete = Button3D("", G.DELETE)
        self.ed_delete.setToolTip(tr("Удалить"))
        self.ed_delete.clicked.connect(lambda: self.delete_profile(self.editing))
        head.addWidget(self.ed_delete)
        lay.addLayout(head)

        form_panel = Panel()
        form = QGridLayout(form_panel)
        form.setContentsMargins(16, 16, 16, 16)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(12)
        form.setColumnStretch(1, 1)

        self.ed_name = QLineEdit()
        self.ed_name.setMaxLength(40)
        form.addWidget(label(tr("Название"), "title"), 0, 0)
        form.addWidget(self.ed_name, 0, 1)

        ver_col = QVBoxLayout()
        ver_col.setSpacing(8)
        self.ed_version = QComboBox()
        self.ed_version.setMaxVisibleItems(14)
        self.ed_version.setMinimumWidth(120)
        self.ed_snapshots = QCheckBox(tr("Снапшоты"))
        self.ed_snapshots.toggled.connect(self.load_version_list)
        ver_col.addWidget(self.ed_version)
        ver_col.addWidget(self.ed_snapshots)
        form.addWidget(label(tr("Версия Minecraft"), "title"), 1, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        form.addLayout(ver_col, 1, 1)

        self.ed_loader = Segmented(["Vanilla", "Fabric"])
        self.ed_loader.changed.connect(lambda _: self.update_mods_section())
        form.addWidget(label(tr("Загрузчик"), "title"), 2, 0)
        form.addWidget(self.ed_loader, 2, 1, Qt.AlignmentFlag.AlignLeft)

        self.ed_memory = QSpinBox()
        self.ed_memory.setRange(0, 32)
        self.ed_memory.setSpecialValueText(tr("как в настройках"))
        self.ed_memory.setSuffix(" GB" if i18n.language() == "en" else " ГБ")
        self.ed_memory.setFixedWidth(190)
        form.addWidget(label(tr("Память"), "title"), 3, 0)
        form.addWidget(self.ed_memory, 3, 1, Qt.AlignmentFlag.AlignLeft)

        self.icon_group = QButtonGroup(self)
        self.icon_group.setExclusive(True)
        self.icon_chips = []
        chips = [IconChip(None, G.GAME, tr("Обычная"))] + [IconChip({"emoji": e}, None, e) for e in PROFILE_EMOJI]
        self.custom_chip = IconChip({"image": ""}, G.IMAGE, tr("Своя картинка"))
        chips.append(self.custom_chip)
        for chip in chips:
            self.icon_group.addButton(chip)
            chip.clicked.connect(lambda _=False, c=chip: self.choose_icon(c))
            self.icon_chips.append(chip)
        self.icon_grid = FlowGrid(min_col_width=46, max_cols=len(chips), stretch=False)
        self.icon_grid.grid.setSpacing(4)
        self.icon_grid.set_items(chips)
        form.addWidget(label(tr("Иконка"), "title"), 4, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        form.addWidget(self.icon_grid, 4, 1)
        lay.addWidget(form_panel)

        actions = QHBoxLayout()
        actions.setSpacing(0)
        self.ed_save = Button3D(tr("Сохранить"), G.CHECK, "accent")
        self.ed_save.clicked.connect(self.save_profile)
        self.ed_folder = Button3D(tr("Папка профиля"), G.FOLDER)
        self.ed_folder.clicked.connect(self.open_profile_folder)
        actions.addWidget(self.ed_save)
        actions.addWidget(self.ed_folder)
        actions.addStretch()
        lay.addLayout(actions)

        lay.addSpacing(6)
        lay.addWidget(label(tr("Моды").upper(), "section"))
        self.mods_hint = wrap_label("")
        lay.addWidget(self.mods_hint)
        self.mods_list = QListWidget()
        self.mods_list.setMinimumHeight(180)
        self.mods_list.itemChanged.connect(self.toggle_mod)
        lay.addWidget(self.mods_list)
        mods_actions = QHBoxLayout()
        mods_actions.setSpacing(0)
        mods_actions.addStretch()
        self.mods_refresh = Button3D(tr("Обновить"), G.REFRESH)
        self.mods_refresh.clicked.connect(self.refresh_mods)
        self.mods_open = Button3D(tr("Папка модов"), G.FOLDER, "accent")
        self.mods_open.clicked.connect(self.open_mods_folder)
        mods_actions.addWidget(self.mods_refresh)
        mods_actions.addWidget(self.mods_open)
        lay.addLayout(mods_actions)
        lay.addStretch()
        self.profiles_stack.addWidget(area)
        return self.profiles_stack

    def refresh_profiles(self):
        current = prof.selected(self.config)
        sig = self.profiles_signature(prof.get_profiles(self.config), current)
        if sig == self._list_sig:
            return
        self._list_sig = sig
        self.list_cards = {}
        cards = []
        for p in prof.get_profiles(self.config):
            card = self.profile_card(p, self.edit_profile)
            card.set_selected(bool(current) and p["id"] == current["id"])
            self.list_cards[p["id"]] = card
            cards.append(card)
        new = Card(tr("Новый профиль"), tr("Создать профиль"), Avatar(glyph=G.ADD, round_=False))
        new.clicked.connect(lambda: self.edit_profile(None))
        cards.append(new)
        self.list_grid.set_items(cards)

    def show_profile_list(self):
        self.refresh_profiles()
        self.profiles_stack.setCurrentIndex(0)
        self.animate_page(self.profiles_stack.currentWidget())

    def edit_profile(self, pid):
        self.editing = pid
        p = prof.get(self.config, pid) if pid else None
        self.editor_title.setText(p["name"] if p else tr("Новый профиль"))
        self.ed_name.setText(p["name"] if p else "")
        self.ed_name.setPlaceholderText(tr("Новый профиль"))
        self.ed_loader.set_index(1 if (p is None or p.get("loader") == prof.FABRIC) else 0, animate=False)
        self.ed_memory.setValue(p.get("memory", 0) if p else 0)
        self.ed_icon = dict(p["icon"]) if p and p.get("icon") else None
        self.ed_icon_file = None
        self.sync_icon_chips(prof.icon(self.config, p) if p else None)
        self.ed_save.setText(tr("Сохранить") if p else tr("Создать"))
        self.ed_save.updateGeometry()
        self.ed_folder.setVisible(bool(p))
        self.ed_delete.setVisible(bool(p))
        self.pending_version = p["mc"] if p else None
        self.ed_version.clear()
        self.fill_version_combo()
        if not self.available_versions:
            self.load_version_list()
        self.update_mods_section()
        self.profiles_stack.setCurrentIndex(1)
        self.animate_page(self.profiles_stack.currentWidget())
        if not p:
            self.ed_name.setFocus()

    def load_version_list(self):
        if self.version_worker and self.version_worker.isRunning():
            return
        self.pending_version = self.ed_version.currentData() or self.pending_version
        self.ed_version.clear()
        self.ed_version.addItem(tr("Загрузка списка версий…"), None)
        self.version_worker = VersionListWorker("snapshot" if self.ed_snapshots.isChecked() else "release")
        self.version_worker.loaded.connect(self.on_versions_loaded)
        self.version_worker.start()

    def on_versions_loaded(self, versions):
        self.available_versions = versions
        self.ed_version.clear()
        self.fill_version_combo()

    def fill_version_combo(self):
        keep = self.ed_version.currentData() or self.pending_version
        installed = set(Versions.installed_versions(self.config.minecraft_directory))
        versions = list(self.available_versions)
        if not versions:
            versions = sorted((v for v in installed if not v.startswith("fabric")), reverse=True)
        if keep and keep not in versions:
            versions.insert(0, keep)
        self.ed_version.clear()
        for v in versions:
            text = f"{v}  ·  {tr('установлена')}" if v in installed else v
            self.ed_version.addItem(text, v)
        if keep:
            i = self.ed_version.findData(keep)
            if i >= 0:
                self.ed_version.setCurrentIndex(i)

    # ---------- иконка профиля ----------
    def sync_icon_chips(self, icon):
        """Отметить выбранную иконку; своя картинка показывается в последней ячейке."""
        self.custom_chip.icon = {"image": icon["image"]} if icon and icon.get("image") else {"image": ""}
        self.custom_chip.update()
        target = self.icon_chips[0]
        if icon and icon.get("emoji"):
            target = next((c for c in self.icon_chips if (c.icon or {}).get("emoji") == icon["emoji"]), target)
        elif icon and icon.get("image"):
            target = self.custom_chip
        target.setChecked(True)

    def choose_icon(self, chip):
        if chip is self.custom_chip:
            path, _ = QFileDialog.getOpenFileName(self, tr("Своя картинка"), "",
                                                  f"{tr('Картинки')} (*.png *.jpg *.jpeg *.webp *.bmp)")
            if not path:  # отменили — вернуть отметку на прежнюю иконку
                if self.ed_icon_file:
                    self.sync_icon_chips({"image": self.ed_icon_file})
                elif (self.ed_icon or {}).get("image"):
                    self.sync_icon_chips(prof.icon(self.config, prof.get(self.config, self.editing)))
                else:
                    self.sync_icon_chips(self.ed_icon)
                return
            self.ed_icon_file = path
            self.ed_icon = {"image": path}
            self.sync_icon_chips({"image": path})
            return
        self.ed_icon_file = None
        self.ed_icon = dict(chip.icon) if chip.icon else None

    def update_mods_section(self):
        p = prof.get(self.config, self.editing) if self.editing else None
        fabric = self.ed_loader.index == 1
        show_list = bool(p) and fabric and p.get("loader") == prof.FABRIC
        if not fabric:
            self.mods_hint.setText(tr("Моды доступны с загрузчиком Fabric."))
        elif not show_list:
            self.mods_hint.setText(tr("Сохраните профиль, чтобы добавить моды."))
        else:
            self.mods_hint.setText(tr("Снимите галочку, чтобы отключить мод."))
        for w in (self.mods_list, self.mods_refresh, self.mods_open):
            w.setVisible(show_list)
        if show_list:
            self.refresh_mods()

    def save_profile(self):
        name = self.ed_name.text().strip()
        mc = self.ed_version.currentData()
        if not name:
            QMessageBox.warning(self, APP_TITLE, tr("Введите название профиля."))
            return
        if not mc:
            QMessageBox.warning(self, APP_TITLE, tr("Выберите версию Minecraft."))
            return
        loader = prof.FABRIC if self.ed_loader.index == 1 else prof.VANILLA
        memory = self.ed_memory.value()
        icon = self.ed_icon if (self.ed_icon or {}).get("emoji") else None
        if self.editing:
            p = prof.update(self.config, self.editing, name=name, mc=mc, loader=loader, memory=memory)
        else:
            p = prof.create(self.config, name, mc, loader, memory)
        if self.ed_icon_file:
            prof.set_image_icon(self.config, p["id"], self.ed_icon_file)
        elif (self.ed_icon or {}).get("image") is None:
            prof.update(self.config, p["id"], icon=icon)
        log(f"{p['name']}: {profile_subtitle(p)}")
        self.edit_profile(p["id"])
        self.refresh_home()

    def delete_profile(self, pid):
        p = prof.get(self.config, pid)
        if not p:
            return
        if QMessageBox.question(self, APP_TITLE, tr("Удалить профиль «{name}»?", name=p["name"])) \
                != QMessageBox.StandardButton.Yes:
            return
        remove = False
        if p.get("dir") != "":
            remove = QMessageBox.question(self, APP_TITLE, tr("Удалить и папку профиля с модами и мирами?")) \
                == QMessageBox.StandardButton.Yes
        prof.delete(self.config, pid, remove_files=remove)
        self.show_profile_list()
        self.refresh_home()

    def open_profile_folder(self):
        p = prof.get(self.config, self.editing)
        if p:
            self.open_folder(prof.game_dir(self.config, p))

    def open_mods_folder(self):
        p = prof.get(self.config, self.editing)
        if p:
            self.open_folder(prof.mods_dir(self.config, p))

    def refresh_mods(self):
        p = prof.get(self.config, self.editing)
        if not p:
            return
        folder = prof.mods_dir(self.config, p)
        self.mods_list.blockSignals(True)
        self.mods_list.clear()
        for name in sorted(os.listdir(folder), key=str.lower):
            if not (name.endswith(".jar") or name.endswith(".jar.disabled")):
                continue
            item = QListWidgetItem(name.removesuffix(".disabled"))
            item.setData(Qt.ItemDataRole.UserRole, name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if name.endswith(".jar") else Qt.CheckState.Unchecked)
            self.mods_list.addItem(item)
        if not self.mods_list.count():
            self.mods_list.addItem(QListWidgetItem(tr("Папка модов пуста")))
        self.mods_list.blockSignals(False)

    def toggle_mod(self, item):
        old = item.data(Qt.ItemDataRole.UserRole)
        p = prof.get(self.config, self.editing)
        if not old or not p:
            return
        folder = prof.mods_dir(self.config, p)
        base = old.removesuffix(".disabled")
        new = base if item.checkState() == Qt.CheckState.Checked else base + ".disabled"
        if new != old:
            try:
                os.rename(os.path.join(folder, old), os.path.join(folder, new))
                item.setData(Qt.ItemDataRole.UserRole, new)
            except OSError as e:
                QMessageBox.warning(self, APP_TITLE, tr("Не удалось переименовать: {e}", e=e))
                self.refresh_mods()

    # ---------- лог ----------
    def build_log(self):
        page, lay = plain_page()
        head = QHBoxLayout()
        head.setSpacing(0)
        head.addWidget(label(tr("Лог"), "pageTitle"), 1)
        copy = Button3D("", G.COPY)
        copy.setToolTip(tr("Копировать"))
        copy.clicked.connect(lambda: QGuiApplication.clipboard().setText(self.log_view.toPlainText()))
        clear = Button3D("", G.CLEAR)
        clear.setToolTip(tr("Очистить"))
        clear.clicked.connect(self.clear_log)
        folder = Button3D(tr("Папка логов"), G.FOLDER)
        folder.clicked.connect(self.open_logs_folder)
        for b in (copy, clear, folder):
            head.addWidget(b)
        lay.addLayout(head)
        self.log_view = QPlainTextEdit()
        self.log_view.setObjectName("LogView")
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(bus.MAX_LINES)
        self.log_view.setPlaceholderText(tr("Здесь появятся сообщения лаунчера и вывод игры."))
        self.log_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        lay.addWidget(self.log_view, 1)
        for source, text in bus.lines:
            self.append_log(source, text)
        bus.line.connect(self.append_log)
        return page

    def append_log(self, source, text):
        t = self.theme
        if source == "launcher":
            color = t["accent"]
        elif "/ERROR]" in text or "Exception" in text or text.startswith("\tat "):
            color = "#ff6b6b"
        elif "/WARN]" in text:
            color = "#e8c15a"
        else:
            color = t["text_dim"]
        bar = self.log_view.verticalScrollBar()
        at_end = bar.value() >= bar.maximum() - 4
        self.log_view.appendHtml(f'<span style="color:{color}; white-space:pre">{html.escape(text)}</span>')
        if at_end:
            bar.setValue(bar.maximum())

    def clear_log(self):
        bus.clear()
        self.log_view.clear()

    def open_logs_folder(self):
        p = prof.selected(self.config)
        base = prof.game_dir(self.config, p) if p else self.config.minecraft_directory
        self.open_folder(os.path.join(base, "logs"))

    # ---------- настройки ----------
    def build_settings(self):
        area, lay = scroll_page()
        lay.addWidget(label(tr("Настройки"), "pageTitle"))

        lay.addWidget(label(tr("ЯЗЫК"), "section"))
        codes = list(i18n.LANGS)
        self.lang_switch = Segmented([i18n.LANGS[c] for c in codes])
        self.lang_switch.set_index(codes.index(i18n.language()), animate=False)
        self.lang_switch.changed.connect(lambda i: QTimer.singleShot(th.NORMAL, lambda: self.set_language(codes[i])))
        lay.addWidget(self.lang_switch)

        lay.addSpacing(6)
        lay.addWidget(label(tr("ПАМЯТЬ"), "section"))
        mem_row = QHBoxLayout()
        self.memory_spin = QSpinBox()
        self.memory_spin.setRange(1, 32)
        self.memory_spin.setSuffix(" GB" if i18n.language() == "en" else " ГБ")
        self.memory_spin.setValue(self.config.allocated_memory)
        self.memory_spin.setFixedWidth(110)
        self.memory_spin.valueChanged.connect(lambda v: setattr(self.config, "allocated_memory", v))
        mem_row.addWidget(self.memory_spin)
        mem_row.addSpacing(6)
        mem_row.addWidget(wrap_label(tr("Оперативная память для игры по умолчанию")), 1)
        lay.addLayout(mem_row)

        lay.addSpacing(6)
        lay.addWidget(label(tr("JAVA"), "section"))
        java_row = QHBoxLayout()
        java_row.setSpacing(0)
        self.java_edit = QLineEdit(self.config.java_path)
        self.java_edit.setPlaceholderText(tr("Автоматически — встроенная Java нужной версии"))
        self.java_edit.editingFinished.connect(lambda: setattr(self.config, "java_path", self.java_edit.text().strip()))
        browse = Button3D("", G.FOLDER)
        browse.setToolTip(tr("Обзор"))
        browse.clicked.connect(self.browse_java)
        auto = Button3D(tr("Авто"))
        auto.clicked.connect(lambda: (self.java_edit.clear(), setattr(self.config, "java_path", "")))
        java_row.addWidget(self.java_edit, 1)
        java_row.addSpacing(4)
        java_row.addWidget(browse)
        java_row.addWidget(auto)
        lay.addLayout(java_row)

        lay.addSpacing(6)
        lay.addWidget(label(tr("ПАПКА ИГРЫ"), "section"))
        dir_row = QHBoxLayout()
        dir_row.setSpacing(0)
        self.dir_edit = QLineEdit(self.config.minecraft_directory)
        self.dir_edit.setReadOnly(True)
        change = Button3D(tr("Сменить"))
        change.clicked.connect(self.browse_game_dir)
        open_dir = Button3D(tr("Открыть"), G.FOLDER, "accent")
        open_dir.clicked.connect(lambda: self.open_folder(self.config.minecraft_directory))
        dir_row.addWidget(self.dir_edit, 1)
        dir_row.addSpacing(4)
        dir_row.addWidget(change)
        dir_row.addWidget(open_dir)
        lay.addLayout(dir_row)

        lay.addSpacing(6)
        lay.addWidget(label(tr("ВХОД ПО ЛИЦЕНЗИИ"), "section"))
        self.client_id_edit = QLineEdit(self.client_id)
        self.client_id_edit.setPlaceholderText(tr("Client ID приложения Azure"))
        self.client_id_edit.editingFinished.connect(
            lambda: self.set_setting("microsoft_client_id", self.client_id_edit.text().strip()))
        lay.addWidget(self.client_id_edit)
        lay.addWidget(wrap_label(tr(
            "Приложение Azure для личных аккаунтов Microsoft, платформа «Мобильные и настольные», "
            "адрес перенаправления {uri}. Доступ к Minecraft API для нового Client ID одобряет Mojang: "
            "aka.ms/mce-reviewappid", uri=acc_mod.REDIRECT_URI)))

        lay.addSpacing(6)
        lay.addWidget(label(tr("АКЦЕНТНЫЙ ЦВЕТ"), "section"))
        chips = QHBoxLayout()
        chips.setSpacing(4)
        self.chips = []
        for name, color in th.ACCENT_PRESETS:
            chip = ColorChip(color, tr(name))
            chip.clicked.connect(lambda _=False, c=color: self.set_accent(c))
            self.chips.append(chip)
            chips.addWidget(chip)
        chips.addSpacing(8)
        custom = Button3D(tr("Свой цвет"))
        custom.clicked.connect(self.pick_accent)
        chips.addWidget(custom)
        chips.addStretch()
        lay.addLayout(chips)

        lay.addSpacing(6)
        lay.addWidget(label(f"{APP_TITLE} v{APP_VERSION}", "hint"))
        lay.addStretch()
        return area

    def set_language(self, lang):
        if lang == i18n.language():
            return
        if self.busy():
            self.lang_switch.set_index(list(i18n.LANGS).index(i18n.language()))
            return
        self.set_setting("language", lang)
        i18n.set_language(lang)
        # Пересобираем окно на новом языке на том же месте; журнал и игра не прерываются
        new = MainWindow()
        new.setGeometry(self.geometry())
        new.open_page("settings", animate=False)
        if self.isMaximized():
            new.showMaximized()
        else:
            new.show()
        _windows.append(new)
        self.close()
        if self in _windows:
            _windows.remove(self)
        self.deleteLater()

    def browse_java(self):
        path, _ = QFileDialog.getOpenFileName(self, tr("Выберите java.exe"), "",
                                              f"Java (java.exe javaw.exe);;{tr('Все файлы')} (*)")
        if path:
            self.java_edit.setText(path)
            self.config.java_path = path

    def browse_game_dir(self):
        path = QFileDialog.getExistingDirectory(self, tr("ПАПКА ИГРЫ"), self.config.minecraft_directory)
        if path:
            self.config.minecraft_directory = path
            self.dir_edit.setText(self.config.minecraft_directory)
            from app import setup_launcher
            setup_launcher()
            self.refresh_home()
            self.refresh_profiles()

    def set_accent(self, color):
        self.config.set_style("accent", color)
        self.apply_theme()

    def pick_accent(self):
        color = QColorDialog.getColor(QColor(self.theme["accent"]), self, tr("Акцентный цвет"))
        if color.isValid():
            self.set_accent(color.name())

    def apply_theme(self):
        self.theme = th.resolve(self.config.get_styles())
        QApplication.instance().setStyleSheet(th.stylesheet(self.theme))
        self.title_bar.recolor()
        QApplication.instance().setWindowIcon(logo_icon(self.theme["accent"]))  # иконка следует акценту
        for chip in self.chips:
            chip.setChecked(chip.color.lower() == self.theme["accent"].lower())
        for w in self.findChildren(QWidget):  # нарисованные вручную виджеты берут цвета из th.T
            w.update()

    # ---------- нижняя панель ----------
    def build_bottom_bar(self):
        bar = QHBoxLayout()
        bar.setContentsMargins(th.EDGE, 0, th.EDGE - Button3D.GLOW, 0)
        bar.setSpacing(th.EDGE)
        bar.addStretch(1)
        self.launch_status = LaunchStatus()
        bar.addWidget(self.launch_status, 0, Qt.AlignmentFlag.AlignVCenter)
        self.play_btn = Button3D(tr("Играть"), G.PLAY, "accent", height=46, depth=5, min_width=170)
        self.play_btn.clicked.connect(self.launch_game)
        bar.addWidget(self.play_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        return bar

    def update_play_state(self):
        if not hasattr(self, "play_btn"):
            return
        p = prof.selected(self.config)
        if p:
            self.play_btn.setToolTip(f"{p['name']} · {profile_subtitle(p)} · {self.player_name or '—'}")
        running = bus.game_running()
        self.play_btn.setEnabled(not running and not self.busy())
        if not self.busy():
            self.launch_status.set_text(tr("Игра запущена") if running else "")

    # ---------- запуск ----------
    def busy(self):
        return bool(self.worker and self.worker.isRunning())

    def launch_game(self):
        p = prof.selected(self.config)
        if not acc_mod.ready(self.account):
            msg = (tr("Войдите через Microsoft на главной.") if self.account["type"] == acc_mod.MICROSOFT
                   else tr("Введите ник на главной (3–16 символов: латиница, цифры, «_»)."))
            QMessageBox.warning(self, APP_TITLE, msg)
            self.open_page("home")
            return
        if not p:
            QMessageBox.warning(self, APP_TITLE, tr("Создайте профиль на вкладке «Профили»."))
            self.open_page("profiles")
            return
        if self.busy() or bus.game_running():
            return
        self.play_btn.setEnabled(False)
        self.launch_status.set_busy(True)
        self.worker = GameWorker(self.config, p, self.account, self.client_id, launch_after=True)
        self.worker.status.connect(self.launch_status.set_text)
        self.worker.progress.connect(self.launch_status.set_progress)
        self.worker.failed.connect(lambda msg: QMessageBox.critical(self, tr("Ошибка"), msg))
        self.worker.loader_resolved.connect(lambda pid, lv: prof.update(self.config, pid, loader_version=lv))
        self.worker.account_refreshed.connect(self.on_account_refreshed)
        self.worker.launched.connect(bus.watch_game)
        self.worker.finished.connect(self.on_worker_finished)
        self.worker.start()

    def on_worker_finished(self):
        self.launch_status.set_busy(False)
        self.update_play_state()

    def on_game_exited(self, code):
        log(tr("Игра завершилась, код {code}", code=code))
        self.update_play_state()
        if code not in (0, None):
            self.launch_status.set_text(tr("Игра завершилась с ошибкой ({code}) — подробности во вкладке «Лог»",
                                           code=code))

    # ---------- окно ----------
    def open_folder(self, path):
        os.makedirs(path, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def closeEvent(self, e):
        if self.busy():
            # Установка идёт в фоне — дождёмся её, иначе поток оборвётся на середине
            self.worker.wait(15000)
        try:
            bus.game_exited.disconnect(self.on_game_exited)
            bus.line.disconnect(self.append_log)
        except TypeError:
            pass
        super().closeEvent(e)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if not hasattr(self, "account_top"):
            return
        narrow = self.width() - NavRail.WIDTH < NARROW
        d = QBoxLayout.Direction.TopToBottom if narrow else QBoxLayout.Direction.LeftToRight
        for box in (self.account_top, self.offline_row, self.licensed_row):
            if box.direction() != d:
                box.setDirection(d)
        self.nick_edit.setMaximumWidth(16777215 if narrow else 280)
        # Перенос строк подсказок — только в узком окне: в широком перенос по слишком
        # маленькой оценке ширины раздувал высоту плашки аккаунта
        for hint in (self.nick_hint, self.ms_hint):
            hint.setWordWrap(narrow)

    def work_area(self):
        """Рабочая область экрана без панели задач (где бы она ни стояла: сверху, сбоку, снизу)."""
        screen = self.screen() or QApplication.primaryScreen()
        return screen.availableGeometry()

    def fit_to_work_area(self, width, height):
        """Размер и положение окна — внутри рабочей области, по центру."""
        area = self.work_area()
        w = min(width, area.width() - 2 * th.EDGE)
        h = min(height, area.height() - 2 * th.EDGE)
        self.resize(w, h)
        self.move(area.left() + (area.width() - w) // 2, area.top() + (area.height() - h) // 2)

    def keep_in_work_area(self):
        """Не даём заголовку окна уйти под панель задач — иначе окно не за что взять."""
        if self.isMaximized() or self.isMinimized():
            return
        area = self.work_area()
        g = self.frameGeometry()
        x = min(max(g.left(), area.left() - g.width() + 120), area.right() - 120)
        y = min(max(g.top(), area.top()), area.bottom() - self.title_bar.height())
        if (x, y) != (g.left(), g.top()):
            self.move(x, y)

    def moveEvent(self, e):
        super().moveEvent(e)
        if not QApplication.mouseButtons():  # пока окно тянут мышью — не мешаем
            self.keep_in_work_area()

    def changeEvent(self, e):
        if e.type() == QEvent.Type.WindowStateChange:
            self.title_bar.update_max_icon(self.isMaximized())
            if not self.isMaximized():
                QTimer.singleShot(0, self.keep_in_work_area)
        super().changeEvent(e)

    def nativeEvent(self, event_type, message):
        """Рамка Windows 11: углы, тень, Snap, изменение размера — см. app/ui/winframe.py."""
        if event_type == b"windows_generic_MSG":
            handled, result = winframe.handle(self, message)
            if handled:
                return True, result
        # Не super().nativeEvent: в PyQt6 вызов базовой реализации роняет процесс
        return False, 0

    def eventFilter(self, obj, e):
        """Всплывающие окна (меню, списки, подсказки) скругляет Windows 11, как у системных."""
        if e.type() == QEvent.Type.Show and isinstance(obj, QWidget) and obj.isWindow() and obj is not self:
            flags = obj.windowFlags()
            if flags & Qt.WindowType.Popup == Qt.WindowType.Popup or isinstance(obj, QMenu):
                winframe.set_corners(obj)
        return super().eventFilter(obj, e)
