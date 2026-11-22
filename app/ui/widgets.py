"""Виджеты в стиле Lettudio: заголовок окна, боковое меню, карточки, плитки, нижняя панель."""
from PyQt6.QtCore import Qt, QRectF, QPointF, QSize, pyqtSignal
from PyQt6.QtGui import (
    QColor, QFont, QFontDatabase, QIcon, QPainter, QPainterPath, QPen, QPixmap,
)
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

from .theme import mix


class G:
    """Глифы Segoe Fluent Icons / Segoe MDL2 Assets (есть в Windows 10/11)."""
    MENU, BACK, FORWARD = 0xE700, 0xE72B, 0xE72A
    MIN, MAX, RESTORE, CLOSE = 0xE921, 0xE922, 0xE923, 0xE8BB
    HOME, LIBRARY, MODS, SLIDERS, PALETTE = 0xE80F, 0xE8F1, 0xE7B8, 0xE9E9, 0xE790
    PLAY, STOP, ADD, MORE, FOLDER = 0xE768, 0xE71A, 0xE710, 0xE712, 0xE838
    DOWNLOAD, GAME, PERSON, REFRESH, SEARCH = 0xE896, 0xE7FC, 0xE77B, 0xE72C, 0xE721


_icon_family = None


def icon_family():
    global _icon_family
    if _icon_family is None:
        families = QFontDatabase.families()
        _icon_family = next(
            (f for f in ("Segoe Fluent Icons", "Segoe MDL2 Assets") if f in families),
            "Segoe UI Symbol",
        )
    return _icon_family


def glyph_pixmap(code, color, size=20, scale=2):
    pm = QPixmap(size * scale, size * scale)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    font = QFont(icon_family())
    font.setPixelSize(int(size * scale * 0.8))
    p.setFont(font)
    p.setPen(QColor(color))
    p.drawText(pm.rect(), Qt.AlignmentFlag.AlignCenter, chr(code))
    p.end()
    pm.setDevicePixelRatio(scale)
    return pm


def glyph_icon(code, color, size=20, checked_color=None):
    icon = QIcon()
    icon.addPixmap(glyph_pixmap(code, color, size), QIcon.Mode.Normal, QIcon.State.Off)
    icon.addPixmap(glyph_pixmap(code, checked_color or color, size), QIcon.Mode.Normal, QIcon.State.On)
    return icon


def label(text="", role=None, parent=None):
    lbl = QLabel(text, parent)
    if role:
        lbl.setProperty("role", role)
    return lbl


class IconButton(QPushButton):
    def __init__(self, glyph, tooltip="", size=18, parent=None):
        super().__init__(parent)
        self.glyph, self.icon_px = glyph, size
        self._color = "#ffffff"
        self.setToolTip(tooltip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setIconSize(QSize(size, size))

    def set_glyph(self, glyph):
        self.glyph = glyph
        self.recolor(self._color)

    def recolor(self, color):
        self._color = color
        self.setIcon(glyph_icon(self.glyph, color, self.icon_px))


class TitleBar(QWidget):
    """Свой заголовок окна (как в Lettudio): меню, назад/вперёд, название, кнопки окна."""

    menu_clicked = pyqtSignal()
    back_clicked = pyqtSignal()
    forward_clicked = pyqtSignal()

    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setObjectName("TitleBar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedHeight(56)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 0, 6, 0)
        lay.setSpacing(2)

        self.menu_btn = IconButton(G.MENU, "Свернуть меню")
        self.back_btn = IconButton(G.BACK, "Назад")
        self.forward_btn = IconButton(G.FORWARD, "Вперёд")
        self.title = label(title)
        self.title.setObjectName("WindowTitle")
        self.min_btn = IconButton(G.MIN, "Свернуть", 12)
        self.max_btn = IconButton(G.MAX, "Развернуть", 12)
        self.close_btn = IconButton(G.CLOSE, "Закрыть", 12)
        self.close_btn.setObjectName("CloseButton")

        for w in (self.menu_btn, self.back_btn, self.forward_btn):
            lay.addWidget(w)
        lay.addSpacing(8)
        lay.addWidget(self.title)
        lay.addStretch()
        for w in (self.min_btn, self.max_btn, self.close_btn):
            lay.addWidget(w)

        self.menu_btn.clicked.connect(self.menu_clicked)
        self.back_btn.clicked.connect(self.back_clicked)
        self.forward_btn.clicked.connect(self.forward_clicked)
        self.min_btn.clicked.connect(lambda: self.window().showMinimized())
        self.max_btn.clicked.connect(self.toggle_max)
        self.close_btn.clicked.connect(lambda: self.window().close())

    def recolor(self, theme):
        for b in (self.menu_btn, self.min_btn, self.max_btn, self.close_btn):
            b.recolor(theme["text"])
        self.set_nav_state(self.back_btn.isEnabled(), self.forward_btn.isEnabled(), theme)

    def set_nav_state(self, can_back, can_forward, theme):
        self.back_btn.setEnabled(can_back)
        self.forward_btn.setEnabled(can_forward)
        self.back_btn.recolor(theme["text"] if can_back else theme["text_dim"])
        self.forward_btn.recolor(theme["text"] if can_forward else mix(theme["text_dim"], theme["background"], 0.4).name())

    def toggle_max(self):
        w = self.window()
        w.showNormal() if w.isMaximized() else w.showMaximized()

    def update_max_icon(self, maximized):
        self.max_btn.set_glyph(G.RESTORE if maximized else G.MAX)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.window().windowHandle().startSystemMove()

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.toggle_max()


class Sidebar(QFrame):
    """Скруглённое боковое меню с «таблеткой» выбранного пункта."""

    page_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(8, 10, 8, 10)
        self.lay.setSpacing(2)
        self.buttons = {}
        self.collapsed = False
        self.setFixedWidth(200)

    def add_item(self, key, glyph, text):
        text = "  " + text  # отступ между иконкой и подписью
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setAutoExclusive(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setIconSize(QSize(22, 22))
        btn.glyph, btn.full_text = glyph, text
        btn.clicked.connect(lambda: self.page_selected.emit(key))
        self.buttons[key] = btn
        self.lay.addWidget(btn)

    def add_separator(self):
        line = QFrame()
        line.setObjectName("SidebarLine")
        wrap = QVBoxLayout()
        wrap.setContentsMargins(14, 8, 14, 8)
        wrap.addWidget(line)
        self.lay.addLayout(wrap)

    def finish(self):
        self.lay.addStretch()

    def recolor(self, theme):
        for b in self.buttons.values():
            b.setIcon(glyph_icon(b.glyph, theme["text_dim"], 22, theme["text"]))

    def select(self, key):
        if key in self.buttons:
            self.buttons[key].setChecked(True)

    def toggle_collapsed(self):
        self.collapsed = not self.collapsed
        for b in self.buttons.values():
            b.setText("" if self.collapsed else b.full_text)
            b.setToolTip(b.full_text if self.collapsed else "")
        self.setFixedWidth(70 if self.collapsed else 200)


class PatternArt(QWidget):
    """Узорная подложка в цветах акцента — как обложки подборок в Lettudio."""

    def __init__(self, pattern="lattice", glyph=None, radius=12, parent=None):
        super().__init__(parent)
        self.pattern, self.glyph, self.radius = pattern, glyph, radius
        self.base = QColor("#5a3a6a")
        self.ink = QColor("#ffffff")
        self.text = ""
        self.glyph_size = 22
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def set_colors(self, theme):
        self.base = mix(theme["accent"], theme["surface_2"], 0.45)
        self.ink = QColor(theme["text"])
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect())
        clip = QPainterPath()
        clip.addRoundedRect(r, self.radius, self.radius)
        p.setClipPath(clip)
        p.fillRect(r, self.base)

        light = QColor(255, 255, 255, 34)
        dark = QColor(0, 0, 0, 60)
        w, h = r.width(), r.height()
        step = max(14.0, min(w, h) / 3.2)
        if self.pattern == "lattice":
            p.setPen(QPen(dark, step * 0.35))
            i = -h
            while i < w + h:
                p.drawLine(QPointF(i, 0), QPointF(i + h, h))
                p.drawLine(QPointF(i + h, 0), QPointF(i, h))
                i += step
        elif self.pattern == "stripes":
            p.setPen(QPen(light, step * 0.45))
            i = -h
            while i < w + h:
                p.drawLine(QPointF(i, h), QPointF(i + h, 0))
                i += step * 1.2
        elif self.pattern == "circles":
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(light)
            for cx, cy, cr in ((0.85, 0.15, 0.35), (0.7, 0.85, 0.45), (1.0, 0.7, 0.3), (0.2, 1.05, 0.3)):
                p.drawEllipse(QPointF(w * cx, h * cy), min(w, h) * cr, min(w, h) * cr)
        elif self.pattern == "waves":
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(dark, step * 0.25))
            for k in range(1, 8):
                p.drawEllipse(QPointF(w * 0.5, h * 0.5), k * step * 0.5, k * step * 0.5)
        elif self.pattern == "dots":
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(dark)
            s = step * 0.5
            y, row = 0.0, 0
            while y < h + s:
                x = (s / 2) if row % 2 else 0.0
                while x < w + s:
                    p.drawEllipse(QPointF(x, y), s * 0.22, s * 0.22)
                    x += s
                y += s * 0.6
                row += 1

        if self.glyph:
            font = QFont(icon_family())
            font.setPixelSize(self.glyph_size)
            p.setFont(font)
            p.setPen(self.ink)
            if self.text:  # большая плитка: иконка в левом верхнем углу
                p.drawText(QRectF(18, 16, 40, 40), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, chr(self.glyph))
            else:
                p.drawText(r, Qt.AlignmentFlag.AlignCenter, chr(self.glyph))
        if self.text:
            font = QFont("Segoe UI Variable Text")
            font.setPixelSize(18)
            p.setFont(font)
            p.setPen(self.ink)
            p.drawText(r.adjusted(18, 0, -14, -16), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom | Qt.TextFlag.TextWordWrap, self.text)
        p.end()


class Card(QFrame):
    """Карточка «иконка + название + подпись» (как блок «Недавние»)."""

    clicked = pyqtSignal()
    context_requested = pyqtSignal(object)

    def __init__(self, title, subtitle, pattern="lattice", glyph=None, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(72)
        self.setMinimumWidth(240)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 12, 16, 12)
        lay.setSpacing(14)
        self.art = PatternArt(pattern, glyph, 12)
        self.art.setFixedSize(48, 48)
        lay.addWidget(self.art)
        texts = QVBoxLayout()
        texts.setSpacing(0)
        self.title = label(title, "title")
        self.subtitle = label(subtitle, "subtitle")
        texts.addStretch()
        texts.addWidget(self.title)
        texts.addWidget(self.subtitle)
        texts.addStretch()
        lay.addLayout(texts, 1)

    def set_selected(self, selected):
        self.setProperty("selected", "true" if selected else "false")
        self.style().unpolish(self)
        self.style().polish(self)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self.rect().contains(e.position().toPoint()):
            self.clicked.emit()

    def contextMenuEvent(self, e):
        self.context_requested.emit(e.globalPos())


class Tile(QWidget):
    """Большая узорная плитка (как блок «Рекомендуем»)."""

    clicked = pyqtSignal()

    def __init__(self, text, glyph, pattern, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(188, 170)
        self.art = PatternArt(pattern, glyph, 22, self)
        self.art.text = text
        self.art.glyph_size = 26
        self.art.setGeometry(self.rect())

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()


class ProgressPanel(QWidget):
    """Левая часть нижней панели: аватар, версия, ник и заливка прогресса акцентом."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(72)
        self.progress = 0.0
        self.bg = QColor("#2b2b2b")
        self.fill = QColor("#5a3a6a")
        self.avatar_color = QColor("#9400d3")
        self.initial = "?"
        lay = QHBoxLayout(self)
        lay.setContentsMargins(76, 10, 22, 10)
        texts = QVBoxLayout()
        texts.setSpacing(0)
        self.title = QLabel("—")
        self.title.setObjectName("NowTitle")
        self.sub = QLabel("")
        self.sub.setObjectName("NowSub")
        texts.addStretch()
        texts.addWidget(self.title)
        texts.addWidget(self.sub)
        texts.addStretch()
        lay.addLayout(texts, 1)
        self.status = QLabel("")
        self.status.setObjectName("NowStatus")
        lay.addWidget(self.status)

    def set_colors(self, theme):
        self.bg = QColor(theme["surface_2"])
        self.fill = mix(theme["accent"], theme["surface_2"], 0.4)
        self.avatar_color = QColor(theme["accent"])
        self.update()

    def set_info(self, version, profile):
        self.title.setText(version.upper() if version else "ВЕРСИЯ НЕ ВЫБРАНА")
        self.sub.setText(profile.upper() if profile else "ПРОФИЛЬ НЕ ВЫБРАН")
        self.initial = (profile or "?")[:1].upper()
        self.update()

    def set_progress(self, value):
        self.progress = max(0.0, min(1.0, value))
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect())
        clip = QPainterPath()
        clip.addRoundedRect(r, 26, 26)
        p.setClipPath(clip)
        p.fillRect(r, self.bg)
        if self.progress > 0:
            p.fillRect(QRectF(0, 0, r.width() * self.progress, r.height()), self.fill)
        # Круглый аватар с первой буквой ника
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self.avatar_color)
        p.drawEllipse(QRectF(10, 10, 52, 52))
        font = QFont("Segoe UI Variable Display")
        font.setPixelSize(22)
        font.setBold(True)
        p.setFont(font)
        p.setPen(QColor("#ffffff"))
        p.drawText(QRectF(10, 10, 52, 52), Qt.AlignmentFlag.AlignCenter, self.initial)
        p.end()
