import os
import re

from PyQt6.QtCore import Qt, QEvent, QTimer, QUrl
from PyQt6.QtGui import QColor, QDesktopServices
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QColorDialog, QComboBox, QFileDialog, QGridLayout, QHBoxLayout,
    QInputDialog, QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMenu, QMessageBox,
    QPushButton, QScrollArea, QSpinBox, QStackedWidget, QVBoxLayout, QWidget, QFrame,
)

from app.utils.config import Config
from app.utils.versions import Versions
from app.ui import theme as th
from app.ui.widgets import (
    G, Card, IconButton, PatternArt, ProgressPanel, Sidebar, Tile, TitleBar, label,
)
from app.ui.worker import GameWorker

APP_TITLE = "LettMine"
APP_VERSION = "0.7"
PATTERNS = ("lattice", "stripes", "circles", "waves", "dots")
RESIZE_MARGIN = 6


def pill(text, kind="pill"):
    btn = QPushButton(text)
    btn.setProperty("kind", kind)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    return btn


def scroll_page(margins=(16, 8, 24, 16)):
    """Страница со скроллом; возвращает (scroll, вертикальный layout содержимого)."""
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    body = QWidget()
    lay = QVBoxLayout(body)
    lay.setContentsMargins(*margins)
    lay.setSpacing(14)
    area.setWidget(body)
    return area, lay


def describe_version(version_id):
    m = re.match(r"fabric-loader-([\d.]+)-(.+)", version_id)
    if m:
        return m.group(2), f"Fabric {m.group(1)}", G.MODS
    return version_id, "Vanilla", G.GAME


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = Config()
        self.theme = th.resolve(self.config.get_styles())
        self.worker = None
        self.game = None
        self.history, self.future = [], []
        self.current_page = None
        self.art_widgets = []  # постоянные узорные виджеты, рисуются цветами темы
        self.card_arts = []    # узоры карточек главной (пересоздаются)

        self.setWindowTitle(APP_TITLE)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.resize(1080, 760)
        self.setMinimumSize(820, 600)

        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 8)
        outer.setSpacing(0)

        self.title_bar = TitleBar(APP_TITLE)
        outer.addWidget(self.title_bar)

        middle = QHBoxLayout()
        middle.setContentsMargins(8, 0, 0, 8)
        middle.setSpacing(12)
        self.sidebar = Sidebar()
        self.sidebar.add_item("home", G.HOME, "Главная")
        self.sidebar.add_item("versions", G.LIBRARY, "Версии")
        self.sidebar.add_item("mods", G.MODS, "Моды")
        self.sidebar.add_separator()
        self.sidebar.add_item("general", G.SLIDERS, "Общие")
        self.sidebar.add_item("themes", G.PALETTE, "Темы")
        self.sidebar.finish()
        side_wrap = QVBoxLayout()
        side_wrap.addStretch(1)
        side_wrap.addWidget(self.sidebar, 6)
        side_wrap.addStretch(1)
        middle.addLayout(side_wrap)

        self.stack = QStackedWidget()
        middle.addWidget(self.stack, 1)
        outer.addLayout(middle, 1)

        outer.addLayout(self.build_bottom_bar())

        self.pages = {
            "home": self.build_home(),
            "versions": self.build_versions(),
            "mods": self.build_mods(),
            "general": self.build_general(),
            "themes": self.build_themes(),
        }
        for page in self.pages.values():
            self.stack.addWidget(page)

        self.sidebar.page_selected.connect(self.open_page)
        self.title_bar.menu_clicked.connect(self.sidebar.toggle_collapsed)
        self.title_bar.back_clicked.connect(self.go_back)
        self.title_bar.forward_clicked.connect(self.go_forward)

        self.game_timer = QTimer(self)
        self.game_timer.timeout.connect(self.check_game)

        QApplication.instance().installEventFilter(self)
        self.apply_theme()
        self.refresh_home()
        self.open_page("home", record=False)

    # ---------- общие настройки ----------
    def setting(self, key, default=None):
        return self.config.config.get(key, default)

    def set_setting(self, key, value):
        self.config.config[key] = value
        self.config.save_config()

    @property
    def selected_version(self):
        installed = Versions.installed_versions(self.config.minecraft_directory)
        v = self.setting("last_version")
        if v in installed:
            return v
        return sorted(installed, reverse=True)[0] if installed else None

    @property
    def selected_profile(self):
        names = [p["name"] for p in self.config.get_profiles()]
        p = self.setting("last_profile")
        if p in names:
            return p
        return names[0] if names else None

    # ---------- навигация ----------
    def open_page(self, key, record=True):
        if key == self.current_page:
            return
        if record and self.current_page:
            self.history.append(self.current_page)
            self.future.clear()
        self.current_page = key
        self.stack.setCurrentWidget(self.pages[key])
        self.sidebar.select(key)
        if key == "mods":
            self.refresh_mods()
        elif key == "home":
            self.refresh_home()
        self.title_bar.set_nav_state(bool(self.history), bool(self.future), self.theme)

    def go_back(self):
        if self.history:
            self.future.append(self.current_page)
            self.open_page(self.history.pop(), record=False)

    def go_forward(self):
        if self.future:
            self.history.append(self.current_page)
            self.open_page(self.future.pop(), record=False)

    # ---------- главная ----------
    def build_home(self):
        area, lay = scroll_page()
        lay.addWidget(label("ПРОФИЛИ", "section"))
        self.profiles_grid = QGridLayout()
        self.profiles_grid.setSpacing(12)
        lay.addLayout(self.profiles_grid)

        lay.addSpacing(10)
        lay.addWidget(label("УСТАНОВЛЕННЫЕ ВЕРСИИ", "section"))
        self.versions_grid = QGridLayout()
        self.versions_grid.setSpacing(12)
        lay.addLayout(self.versions_grid)

        lay.addSpacing(10)
        lay.addWidget(label("БЫСТРЫЕ ДЕЙСТВИЯ", "section"))
        tiles = QHBoxLayout()
        tiles.setSpacing(14)
        for text, glyph, pattern, action in (
            ("Скачать версию", G.DOWNLOAD, "lattice", lambda: self.open_page("versions")),
            ("Моды", G.MODS, "stripes", lambda: self.open_page("mods")),
            ("Папка игры", G.FOLDER, "waves", lambda: self.open_folder(self.config.minecraft_directory)),
            ("Сменить тему", G.PALETTE, "circles", lambda: self.open_page("themes")),
        ):
            tile = Tile(text, glyph, pattern)
            tile.clicked.connect(action)
            self.art_widgets.append(tile.art)
            tiles.addWidget(tile)
        tiles.addStretch()
        lay.addLayout(tiles)
        lay.addStretch()
        return area

    @staticmethod
    def clear_grid(grid):
        while grid.count():
            w = grid.takeAt(0).widget()
            if w:
                w.deleteLater()

    def refresh_home(self):
        self.card_arts = []
        # Профили
        self.clear_grid(self.profiles_grid)
        current = self.selected_profile
        cards = []
        for i, profile in enumerate(self.config.get_profiles()):
            name = profile["name"]
            card = Card(name, "профиль · оффлайн", PATTERNS[i % len(PATTERNS)], G.PERSON)
            card.set_selected(name == current)
            card.clicked.connect(lambda n=name: self.select_profile(n))
            card.context_requested.connect(lambda pos, n=name: self.profile_menu(n, pos))
            cards.append(card)
        add = Card("Новый профиль", "добавить ник", "dots", G.ADD)
        add.clicked.connect(self.add_profile)
        cards.append(add)
        self.place_cards(self.profiles_grid, cards)

        # Версии
        self.clear_grid(self.versions_grid)
        current = self.selected_version
        installed = sorted(Versions.installed_versions(self.config.minecraft_directory), reverse=True)
        cards = []
        for i, vid in enumerate(installed):
            mc, kind, glyph = describe_version(vid)
            card = Card(mc, kind.lower(), "stripes" if glyph == G.MODS else "lattice", glyph)
            card.set_selected(vid == current)
            card.setToolTip(vid)
            card.clicked.connect(lambda v=vid: self.select_version(v))
            cards.append(card)
        if not cards:
            empty = Card("Нет версий", "скачайте во вкладке «Версии»", "dots", G.DOWNLOAD)
            empty.clicked.connect(lambda: self.open_page("versions"))
            cards.append(empty)
        self.place_cards(self.versions_grid, cards)
        self.update_bottom_bar()

    def place_cards(self, grid, cards, columns=2):
        for i, card in enumerate(cards):
            card.art.set_colors(self.theme)
            self.card_arts.append(card.art)
            grid.addWidget(card, i // columns, i % columns)

    def select_profile(self, name):
        self.set_setting("last_profile", name)
        self.refresh_home()

    def select_version(self, vid):
        self.set_setting("last_version", vid)
        self.refresh_home()

    def add_profile(self):
        name, ok = QInputDialog.getText(self, "Новый профиль", "Ник в игре:")
        name = name.strip()
        if not ok or not name:
            return
        if not re.fullmatch(r"[A-Za-z0-9_]{3,16}", name):
            QMessageBox.warning(self, APP_TITLE, "Ник: 3–16 символов, латиница, цифры и «_» — иначе серверы его не примут.")
            return
        if name in [p["name"] for p in self.config.get_profiles()]:
            return
        self.config.add_profile({"name": name, "email": "", "password": ""})
        self.select_profile(name)

    def profile_menu(self, name, pos):
        menu = QMenu(self)
        menu.addAction("Выбрать", lambda: self.select_profile(name))
        menu.addAction("Удалить", lambda: self.remove_profile(name))
        menu.exec(pos)

    def remove_profile(self, name):
        if QMessageBox.question(self, APP_TITLE, f"Удалить профиль «{name}»?") == QMessageBox.StandardButton.Yes:
            self.config.remove_profile(name)
            self.refresh_home()

    # ---------- версии ----------
    def build_versions(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(16, 8, 24, 16)
        lay.setSpacing(14)
        lay.addWidget(label("Версии", "pageTitle"))

        row = QHBoxLayout()
        self.version_filter = QLineEdit()
        self.version_filter.setPlaceholderText("Поиск версии...")
        self.version_filter.textChanged.connect(self.filter_versions)
        self.version_type = QComboBox()
        self.version_type.addItem("Релизы", "release")
        self.version_type.addItem("Снапшоты", "snapshot")
        self.version_type.currentIndexChanged.connect(self.load_available_versions)
        self.fabric_check = QCheckBox("С Fabric")
        self.fabric_check.setChecked(True)
        row.addWidget(self.version_filter, 1)
        row.addWidget(self.version_type)
        row.addWidget(self.fabric_check)
        lay.addLayout(row)

        self.version_list = QListWidget()
        self.version_list.itemDoubleClicked.connect(lambda _: self.install_selected())
        lay.addWidget(self.version_list, 1)

        bottom = QHBoxLayout()
        self.version_hint = label("Жирным отмечены установленные версии", "hint")
        bottom.addWidget(self.version_hint, 1)
        self.install_btn = pill("Установить", "accent")
        self.install_btn.clicked.connect(self.install_selected)
        bottom.addWidget(self.install_btn)
        lay.addLayout(bottom)

        QTimer.singleShot(0, self.load_available_versions)
        return page

    def load_available_versions(self):
        self.version_list.clear()
        mc_dir = self.config.minecraft_directory
        available = Versions.available_versions(mc_dir, self.version_type.currentData())
        installed = set(Versions.installed_versions(mc_dir))
        if not available:
            self.version_hint.setText("Нет связи с серверами Mojang — показаны только установленные версии")
            available = sorted(v for v in installed if not v.startswith("fabric"))
        for vid in available:
            item = QListWidgetItem(vid)
            if vid in installed:
                font = item.font()
                font.setBold(True)
                item.setFont(font)
            self.version_list.addItem(item)
        self.filter_versions(self.version_filter.text())

    def filter_versions(self, text):
        for i in range(self.version_list.count()):
            item = self.version_list.item(i)
            item.setHidden(text.strip().lower() not in item.text().lower())

    def install_selected(self):
        item = self.version_list.currentItem()
        if not item:
            QMessageBox.information(self, APP_TITLE, "Выберите версию в списке.")
            return
        self.start_worker(item.text(), fabric=self.fabric_check.isChecked(), launch_after=False)

    # ---------- моды ----------
    def build_mods(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(16, 8, 24, 16)
        lay.setSpacing(14)
        lay.addWidget(label("Моды", "pageTitle"))
        lay.addWidget(label("Снимите галочку, чтобы отключить мод (например, если он для другой версии игры).", "hint"))
        self.mods_list = QListWidget()
        self.mods_list.itemChanged.connect(self.toggle_mod)
        lay.addWidget(self.mods_list, 1)
        row = QHBoxLayout()
        row.addStretch()
        refresh = pill("Обновить")
        refresh.clicked.connect(self.refresh_mods)
        open_btn = pill("Открыть папку модов", "accent")
        open_btn.clicked.connect(lambda: self.open_folder(self.mods_dir()))
        row.addWidget(refresh)
        row.addWidget(open_btn)
        lay.addLayout(row)
        return page

    def mods_dir(self):
        path = os.path.join(self.config.minecraft_directory, "mods")
        os.makedirs(path, exist_ok=True)
        return path

    def refresh_mods(self):
        self.mods_list.blockSignals(True)
        self.mods_list.clear()
        for name in sorted(os.listdir(self.mods_dir()), key=str.lower):
            if not (name.endswith(".jar") or name.endswith(".jar.disabled")):
                continue
            enabled = name.endswith(".jar")
            item = QListWidgetItem(name.removesuffix(".disabled"))
            item.setData(Qt.ItemDataRole.UserRole, name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if enabled else Qt.CheckState.Unchecked)
            self.mods_list.addItem(item)
        if not self.mods_list.count():
            self.mods_list.addItem(QListWidgetItem("Папка модов пуста"))
        self.mods_list.blockSignals(False)

    def toggle_mod(self, item):
        old = item.data(Qt.ItemDataRole.UserRole)
        if not old:
            return
        base = old.removesuffix(".disabled")
        new = base if item.checkState() == Qt.CheckState.Checked else base + ".disabled"
        if new != old:
            try:
                os.rename(os.path.join(self.mods_dir(), old), os.path.join(self.mods_dir(), new))
                item.setData(Qt.ItemDataRole.UserRole, new)
            except OSError as e:
                QMessageBox.warning(self, APP_TITLE, f"Не удалось переименовать: {e}")
                self.refresh_mods()

    # ---------- общие настройки ----------
    def build_general(self):
        area, lay = scroll_page()
        lay.addWidget(label("Общие", "pageTitle"))

        lay.addWidget(label("ПАМЯТЬ", "section"))
        mem_row = QHBoxLayout()
        self.memory_spin = QSpinBox()
        self.memory_spin.setRange(1, 32)
        self.memory_spin.setSuffix(" ГБ")
        self.memory_spin.setValue(self.config.allocated_memory)
        self.memory_spin.setFixedWidth(120)
        self.memory_spin.valueChanged.connect(self.set_memory)
        mem_row.addWidget(self.memory_spin)
        mem_row.addWidget(label("Сколько оперативной памяти отдать игре (-Xmx)", "hint"), 1)
        lay.addLayout(mem_row)

        lay.addSpacing(6)
        lay.addWidget(label("JAVA", "section"))
        java_row = QHBoxLayout()
        self.java_edit = QLineEdit(self.config.java_path)
        self.java_edit.setPlaceholderText("Автоматически (встроенная Java нужной версии)")
        self.java_edit.editingFinished.connect(lambda: setattr(self.config, "java_path", self.java_edit.text().strip()))
        browse = pill("Обзор...")
        browse.clicked.connect(self.browse_java)
        auto = pill("Авто")
        auto.clicked.connect(lambda: (self.java_edit.clear(), setattr(self.config, "java_path", "")))
        java_row.addWidget(self.java_edit, 1)
        java_row.addWidget(browse)
        java_row.addWidget(auto)
        lay.addLayout(java_row)

        lay.addSpacing(6)
        lay.addWidget(label("ПАПКА ИГРЫ", "section"))
        dir_row = QHBoxLayout()
        self.dir_edit = QLineEdit(self.config.minecraft_directory)
        self.dir_edit.setReadOnly(True)
        change = pill("Изменить...")
        change.clicked.connect(self.browse_game_dir)
        open_dir = pill("Открыть", "accent")
        open_dir.clicked.connect(lambda: self.open_folder(self.config.minecraft_directory))
        dir_row.addWidget(self.dir_edit, 1)
        dir_row.addWidget(change)
        dir_row.addWidget(open_dir)
        lay.addLayout(dir_row)

        lay.addSpacing(6)
        lay.addWidget(label("О ЛАУНЧЕРЕ", "section"))
        lay.addWidget(label(f"{APP_TITLE} v{APP_VERSION} · PyQt6 · minecraft-launcher-lib", "hint"))
        lay.addStretch()
        return area

    def set_memory(self, value):
        self.config.allocated_memory = value
        self.update_bottom_bar()

    def browse_java(self):
        path, _ = QFileDialog.getOpenFileName(self, "Выберите java.exe", "", "Java (java.exe javaw.exe);;Все файлы (*)")
        if path:
            self.java_edit.setText(path)
            self.config.java_path = path

    def browse_game_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Папка игры", self.config.minecraft_directory)
        if path:
            self.config.minecraft_directory = path
            self.dir_edit.setText(self.config.minecraft_directory)
            from app import setup_launcher
            setup_launcher()
            self.refresh_home()
            self.load_available_versions()

    # ---------- темы ----------
    def build_themes(self):
        area, lay = scroll_page()
        lay.addWidget(label("Темы", "pageTitle"))
        lay.addWidget(label("ЦВЕТА", "section"))
        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(10)
        self.swatches = {}
        for row, key in enumerate(th.DEFAULT_THEME):
            grid.addWidget(label(th.THEME_LABELS[key], "title"), row, 0)
            btn = pill("", "swatch")
            btn.clicked.connect(lambda _=False, k=key: self.pick_color(k))
            self.swatches[key] = btn
            grid.addWidget(btn, row, 1)
        grid.setColumnStretch(2, 1)
        lay.addLayout(grid)

        lay.addSpacing(10)
        lay.addWidget(label("ПРЕВЬЮ", "section"))
        preview = QHBoxLayout()
        preview.setSpacing(12)
        for pattern in PATTERNS:
            art = PatternArt(pattern, G.GAME, 14)
            art.setFixedSize(72, 72)
            self.art_widgets.append(art)
            preview.addWidget(art)
        preview.addStretch()
        lay.addLayout(preview)

        lay.addSpacing(10)
        reset = pill("Сбросить к стандартной")
        reset.clicked.connect(self.reset_theme)
        row = QHBoxLayout()
        row.addWidget(reset)
        row.addStretch()
        lay.addLayout(row)
        lay.addStretch()
        return area

    def pick_color(self, key):
        color = QColorDialog.getColor(QColor(self.theme[key]), self, th.THEME_LABELS[key])
        if color.isValid():
            self.config.set_style(key, color.name())
            self.apply_theme()

    def reset_theme(self):
        self.config.styles = {}
        self.config.save_styles()
        self.apply_theme()

    def apply_theme(self):
        self.theme = th.resolve(self.config.get_styles())
        QApplication.instance().setStyleSheet(th.stylesheet(self.theme))
        self.title_bar.recolor(self.theme)
        self.sidebar.recolor(self.theme)
        for b in (self.folder_btn, self.more_btn):
            b.recolor(self.theme["text"])
        self.play_btn.recolor("#ffffff")
        self.progress_panel.set_colors(self.theme)
        for art in self.art_widgets + self.card_arts:
            art.set_colors(self.theme)
        for key, btn in getattr(self, "swatches", {}).items():
            btn.setStyleSheet(f"background: {self.theme[key]};")

    # ---------- нижняя панель ----------
    def build_bottom_bar(self):
        bar = QHBoxLayout()
        bar.setContentsMargins(8, 0, 8, 0)
        bar.setSpacing(12)
        self.progress_panel = ProgressPanel()
        bar.addWidget(self.progress_panel, 1)

        right = QFrame()
        right.setObjectName("BarRight")
        right.setFixedHeight(72)
        rl = QHBoxLayout(right)
        rl.setContentsMargins(14, 0, 14, 0)
        rl.setSpacing(8)
        self.folder_btn = IconButton(G.FOLDER, "Папка игры", 20)
        self.folder_btn.clicked.connect(lambda: self.open_folder(self.config.minecraft_directory))
        self.play_btn = IconButton(G.PLAY, "Играть", 22)
        self.play_btn.setObjectName("PlayButton")
        self.play_btn.clicked.connect(self.launch_game)
        self.memory_pill = QPushButton()
        self.memory_pill.setObjectName("Pill")
        self.memory_pill.setToolTip("Выделенная память")
        self.memory_pill.setCursor(Qt.CursorShape.PointingHandCursor)
        self.memory_pill.clicked.connect(lambda: self.open_page("general"))
        self.more_btn = IconButton(G.MORE, "Настройки", 20)
        self.more_btn.clicked.connect(lambda: self.open_page("general"))
        for w in (self.folder_btn, self.play_btn, self.memory_pill, self.more_btn):
            rl.addWidget(w)
        bar.addWidget(right)
        return bar

    def update_bottom_bar(self):
        version = self.selected_version
        title = ""
        if version:
            mc, kind, _ = describe_version(version)
            title = f"{mc} · {kind}"
        self.progress_panel.set_info(title, self.selected_profile)
        self.memory_pill.setText(f"{self.config.allocated_memory} ГБ")
        if not self.busy():
            self.progress_panel.status.setText("Игра запущена" if self.game_running() else "Готово к запуску")

    # ---------- запуск ----------
    def busy(self):
        return bool(self.worker and self.worker.isRunning())

    def game_running(self):
        return bool(self.game and self.game.poll() is None)

    def launch_game(self):
        version, profile = self.selected_version, self.selected_profile
        if not profile:
            QMessageBox.warning(self, APP_TITLE, "Сначала создайте профиль на главной.")
            return
        if not version:
            QMessageBox.warning(self, APP_TITLE, "Сначала установите версию во вкладке «Версии».")
            return
        self.start_worker(version, username=profile, launch_after=True)

    def start_worker(self, version, username=None, fabric=False, launch_after=True):
        if self.busy():
            return
        self.play_btn.setEnabled(False)
        self.install_btn.setEnabled(False)
        self.worker = GameWorker(self.config, version, username, fabric, launch_after)
        self.worker.status.connect(self.progress_panel.status.setText)
        self.worker.progress.connect(self.progress_panel.set_progress)
        self.worker.failed.connect(lambda msg: QMessageBox.critical(self, "Ошибка", msg))
        self.worker.installed.connect(self.on_installed)
        self.worker.launched.connect(self.on_launched)
        self.worker.finished.connect(self.on_worker_finished)
        self.worker.start()

    def on_installed(self, vid):
        if not self.worker.launch_after:
            self.set_setting("last_version", vid)
            self.load_available_versions()
        self.refresh_home()

    def on_launched(self, proc):
        self.game = proc
        self.game_timer.start(1500)

    def on_worker_finished(self):
        self.progress_panel.set_progress(0)
        self.install_btn.setEnabled(True)
        self.play_btn.setEnabled(not self.game_running())
        self.update_bottom_bar()

    def check_game(self):
        if not self.game_running():
            self.game_timer.stop()
            code = self.game.returncode if self.game else 0
            self.game = None
            self.play_btn.setEnabled(not self.busy())
            self.update_bottom_bar()
            if code not in (0, None):
                self.progress_panel.status.setText(f"Игра завершилась с ошибкой ({code})")

    # ---------- разное ----------
    def open_folder(self, path):
        os.makedirs(path, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def changeEvent(self, e):
        if e.type() == QEvent.Type.WindowStateChange:
            self.title_bar.update_max_icon(self.isMaximized())
        super().changeEvent(e)

    def edges_at(self, global_pos):
        if self.isMaximized():
            return Qt.Edge(0)
        pos = self.mapFromGlobal(global_pos)
        w, h, m = self.width(), self.height(), RESIZE_MARGIN
        edges = Qt.Edge(0)
        if pos.x() <= m:
            edges |= Qt.Edge.LeftEdge
        if pos.x() >= w - m:
            edges |= Qt.Edge.RightEdge
        if pos.y() <= m:
            edges |= Qt.Edge.TopEdge
        if pos.y() >= h - m:
            edges |= Qt.Edge.BottomEdge
        return edges

    def eventFilter(self, obj, e):
        """Изменение размера окна без рамки: тянем за край."""
        t = e.type()
        if t in (QEvent.Type.MouseMove, QEvent.Type.MouseButtonPress) and isinstance(obj, QWidget) and obj.window() is self:
            edges = self.edges_at(e.globalPosition().toPoint())
            if t == QEvent.Type.MouseButtonPress and edges and e.button() == Qt.MouseButton.LeftButton:
                self.windowHandle().startSystemResize(edges)
                return True
            if t == QEvent.Type.MouseMove and not e.buttons():
                E = Qt.Edge
                if edges in (E.LeftEdge | E.TopEdge, E.RightEdge | E.BottomEdge):
                    shape = Qt.CursorShape.SizeFDiagCursor
                elif edges in (E.RightEdge | E.TopEdge, E.LeftEdge | E.BottomEdge):
                    shape = Qt.CursorShape.SizeBDiagCursor
                elif edges & (E.LeftEdge | E.RightEdge):
                    shape = Qt.CursorShape.SizeHorCursor
                elif edges & (E.TopEdge | E.BottomEdge):
                    shape = Qt.CursorShape.SizeVerCursor
                else:
                    shape = None
                if shape is not None:
                    self.setCursor(shape)
                else:
                    self.unsetCursor()
        return super().eventFilter(obj, e)
