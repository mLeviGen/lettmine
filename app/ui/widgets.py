"""Виджеты LettMine в стиле Lettudio: 3D-кнопки, меню с «таблеткой», карточки, панель запуска.

Все элементы рисуются вручную, чтобы анимации (нажатие, наведение, волна, свечение)
были плавными и не зависели от возможностей QSS.
"""
import math

from PyQt6.QtCore import (
    QEvent, QObject, QPointF, QRectF, QSize, Qt, QTimer, QVariantAnimation, pyqtSignal,
)
from PyQt6.QtGui import (
    QColor, QFont, QFontDatabase, QFontMetrics, QLinearGradient, QPainter, QPainterPath, QPen,
)
from PyQt6.QtWidgets import (
    QAbstractButton, QGraphicsEffect, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget,
)

from . import theme as th
from .theme import T, alpha, mix


class G:
    """Глифы Segoe Fluent Icons / Segoe MDL2 Assets (есть в Windows 10/11)."""
    MIN, MAX, RESTORE, CLOSE = 0xE921, 0xE922, 0xE923, 0xE8BB
    HOME, LIBRARY, MODS, SETTINGS = 0xE80F, 0xE8F1, 0xE7B8, 0xE713
    PLAY, ADD, FOLDER, DOWNLOAD, GAME = 0xF5B0, 0xE710, 0xE838, 0xE896, 0xE7FC
    REFRESH, EDIT, CHECK, PERSON = 0xE72C, 0xE70F, 0xE73E, 0xE77B
    LOG, BACK, DELETE, COPY, CLEAR = 0xE756, 0xE72B, 0xE74D, 0xE8C8, 0xE894
    IMAGE = 0xE8B9


_icon_family = None


def icon_family():
    global _icon_family
    if _icon_family is None:
        families = QFontDatabase.families()
        _icon_family = next(
            (f for f in ("Segoe Fluent Icons", "Segoe MDL2 Assets") if f in families), "Segoe UI Symbol"
        )
    return _icon_family


def icon_font(px):
    f = QFont(icon_family())
    f.setPixelSize(int(px))
    f.setHintingPreference(QFont.HintingPreference.PreferVerticalHinting)
    return f


def ui_font(px, weight=QFont.Weight.Normal):
    f = QFont(th.FONT)
    f.setPixelSize(int(px))
    f.setWeight(weight)
    # Без хинтинга при дробном масштабе Windows (125%) буквы «пляшут» по высоте
    f.setHintingPreference(QFont.HintingPreference.PreferVerticalHinting)
    return f


def label(text="", role=None, parent=None):
    lbl = QLabel(text, parent)
    if role:
        lbl.setProperty("role", role)
    return lbl


def stadium(rect, radius=None):
    path = QPainterPath()
    r = rect.height() / 2 if radius is None else min(radius, rect.height() / 2)
    path.addRoundedRect(rect, r, r)
    return path


# ---------------------------------------------------------------- анимации

class Tween(QVariantAnimation):
    """Число 0..1, плавно идущее к цели; на каждом шаге перерисовывает виджет."""

    def __init__(self, widget, value=0.0):
        super().__init__(widget)
        self._w = widget
        self.value = value
        self.valueChanged.connect(self._step)

    def _step(self, v):
        self.value = float(v)
        self._w.update()

    def to(self, target, duration=th.NORMAL, curve=th.CURVE):
        self.stop()
        if abs(self.value - target) < 1e-4:
            return
        self.setStartValue(self.value)
        self.setEndValue(float(target))
        self.setDuration(duration)
        self.setEasingCurve(curve)
        self.start()


class ScaleEffect(QGraphicsEffect):
    """Масштабирует отрисовку виджета целиком (вместе с дочерними) вокруг центра."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scale = 1.0

    def set_scale(self, s):
        self.scale = s
        self.update()

    def draw(self, painter):
        if abs(self.scale - 1.0) < 1e-3:
            self.drawSource(painter)
            return
        pm, offset = self.sourcePixmap(Qt.CoordinateSystem.LogicalCoordinates)
        rect = self.sourceBoundingRect()
        c = rect.center()
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.translate(c)
        painter.scale(self.scale, self.scale)
        painter.translate(-c)
        painter.drawPixmap(offset, pm)
        painter.restore()


class _PressFilter(QObject):
    def __init__(self, widget, scale):
        super().__init__(widget)
        self.effect = ScaleEffect(widget)
        widget.setGraphicsEffect(self.effect)
        self.pressed_scale = scale
        self.anim = QVariantAnimation(self)
        self.anim.valueChanged.connect(lambda v: self.effect.set_scale(float(v)))
        widget.installEventFilter(self)

    def _go(self, target, duration, curve):
        self.anim.stop()
        self.anim.setStartValue(self.effect.scale)
        self.anim.setEndValue(target)
        self.anim.setDuration(duration)
        self.anim.setEasingCurve(curve)
        self.anim.start()

    def eventFilter(self, obj, e):
        t = e.type()
        if t == QEvent.Type.MouseButtonPress and e.button() == Qt.MouseButton.LeftButton:
            self._go(self.pressed_scale, th.FAST, th.CURVE)
        elif t in (QEvent.Type.MouseButtonRelease, QEvent.Type.Leave):
            self._go(1.0, th.SLOW, th.SPRING)
        return False


def pressable(widget, scale=0.96):
    """Мягкое «вдавливание» любого виджета при нажатии (как Tap в Lettudio)."""
    widget._press_filter = _PressFilter(widget, scale)
    return widget


# ---------------------------------------------------------------- кнопки

class Button3D(QAbstractButton):
    """Объёмная кнопка: «бортик» снизу, при нажатии лицевая часть опускается на него.

    Эффекты: блик сверху, свечение акцента при наведении, волна от точки нажатия,
    упругий возврат.
    """

    GLOW = 8  # запас по краям под свечение

    def __init__(self, text="", glyph=None, kind="neutral", height=40, depth=4, min_width=0, parent=None):
        super().__init__(parent)
        self.setText(text)
        self.glyph = glyph
        self.kind = kind  # accent | neutral
        self.face_h = height
        self.depth = depth
        self.min_width = min_width
        self.font_px = 15 if height >= 44 else 14
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.press = Tween(self)
        self.hover = Tween(self)
        self.ripples = []

    def sizeHint(self):
        fm = QFontMetrics(ui_font(self.font_px, QFont.Weight.Bold))
        w = fm.horizontalAdvance(self.text()) if self.text() else 0
        if self.glyph:
            w += self.font_px + 2 + (10 if self.text() else 0)
        w = max(w + (44 if self.text() else 0), self.face_h, self.min_width)
        return QSize(int(w) + self.GLOW * 2, self.face_h + self.depth + self.GLOW * 2)

    def minimumSizeHint(self):
        return self.sizeHint()

    # --- события
    def enterEvent(self, e):
        self.hover.to(1.0, th.NORMAL)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self.hover.to(0.0, th.NORMAL)
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self.isEnabled():
            self.press.to(1.0, th.FAST // 2 + 30, th.CURVE)
            self._ripple(e.position())
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        self.press.to(0.0, th.SLOW, th.SPRING)
        super().mouseReleaseEvent(e)

    def changeEvent(self, e):
        if e.type() == QEvent.Type.EnabledChange:
            self.update()
        super().changeEvent(e)

    def _ripple(self, pos):
        anim = QVariantAnimation(self)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setDuration(th.SLOW + 200)
        anim.setEasingCurve(th.CURVE)
        item = [QPointF(pos), 0.0]
        anim.valueChanged.connect(lambda v: (item.__setitem__(1, float(v)), self.update()))
        anim.finished.connect(lambda: (self.ripples.remove(item), anim.deleteLater(), self.update()))
        self.ripples.append(item)
        anim.start()

    # --- отрисовка
    def colors(self):
        enabled = self.isEnabled()
        if self.kind == "accent":
            base = QColor(T["accent"]) if enabled else mix(T["accent"], T["surface"], 0.65)
            fg = th.on_color(T["accent"]) if enabled else QColor(T["text_dim"])
        else:
            base = QColor(T["surface_2"]) if enabled else QColor(T["surface"])
            fg = QColor(T["text"]) if enabled else QColor(T["text_dim"])
        return base, fg

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        g = self.GLOW
        w = self.width() - g * 2
        x = g + (self.width() - g * 2 - w) / 2
        y0 = (self.height() - self.face_h - self.depth) / 2
        base, fg = self.colors()
        hov, prs = self.hover.value, self.press.value
        sink = self.depth * prs
        face = QRectF(x, y0 + sink, w, self.face_h)
        lip = QRectF(x, y0 + self.depth, w, self.face_h)

        # Свечение (акцент) или мягкая тень (обычные) — тускнеет при нажатии
        if self.isEnabled():
            glow_col = QColor(T["accent"]) if self.kind == "accent" else QColor(0, 0, 0)
            strength = (0.10 + 0.22 * hov) if self.kind == "accent" else 0.22
            strength *= 1 - 0.6 * prs
            for i in range(g, 0, -1):
                k = 1 - i / g
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(alpha(glow_col, strength * k * k * 0.35))
                p.drawPath(stadium(lip.adjusted(-i, -i + 2, i, i)))

        # Бортик: тёмная копия цвета
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(base.darker(165))
        p.drawPath(stadium(lip))

        # Лицевая часть: светлеет при наведении, темнеет при нажатии
        face_col = mix(base, QColor("#ffffff"), 0.10 * hov)
        face_col = mix(face_col, QColor("#000000"), 0.10 * prs)
        path = stadium(face)
        p.setBrush(face_col)
        p.drawPath(path)

        # Блик сверху — даёт объём
        grad = QLinearGradient(face.topLeft(), face.bottomLeft())
        grad.setColorAt(0.0, alpha("#ffffff", 0.22 * (1 - 0.5 * prs)))
        grad.setColorAt(0.5, alpha("#ffffff", 0.0))
        p.setBrush(grad)
        p.drawPath(path)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(alpha("#ffffff", 0.14), 1))
        p.drawPath(stadium(face.adjusted(0.5, 0.5, -0.5, -0.5)))

        # Волна от точки нажатия
        if self.ripples:
            p.save()
            p.setClipPath(path)
            p.setPen(Qt.PenStyle.NoPen)
            reach = math.hypot(face.width(), face.height())
            for pos, t in self.ripples:
                p.setBrush(alpha(fg, 0.28 * (1 - t)))
                p.drawEllipse(pos, reach * t, reach * t)
            p.restore()

        # Содержимое
        p.setPen(fg)
        text = self.text()
        tf = ui_font(self.font_px, QFont.Weight.Bold)
        tw = QFontMetrics(tf).horizontalAdvance(text) if text else 0
        gw = (self.font_px + 2) if self.glyph else 0
        gap = 10 if (text and self.glyph) else 0
        cx = face.center().x() - (tw + gw + gap) / 2
        if self.glyph:
            p.setFont(icon_font(self.font_px + 2))
            p.drawText(QRectF(cx, face.top(), gw, face.height()), Qt.AlignmentFlag.AlignCenter, chr(self.glyph))
        if text:
            p.setFont(tf)
            p.drawText(QRectF(cx + gw + gap, face.top(), tw + 2, face.height()),
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)
        p.end()


class IconTap(QAbstractButton):
    """Кнопка-иконка без подложки: круг при наведении и сжатие до 0.86 при нажатии (Tap в Lettudio)."""

    def __init__(self, glyph, tooltip="", size=40, icon_px=12, danger=False, parent=None):
        super().__init__(parent)
        self.glyph, self.icon_px, self.danger = glyph, icon_px, danger
        self.setToolTip(tooltip)
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.hover = Tween(self)
        self.press = Tween(self)

    def enterEvent(self, e):
        self.hover.to(1.0, th.FAST)

    def leaveEvent(self, e):
        self.hover.to(0.0, th.NORMAL)

    def mousePressEvent(self, e):
        self.press.to(1.0, th.FAST)
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        self.press.to(0.0, th.SLOW, th.SPRING)
        super().mouseReleaseEvent(e)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect())
        s = 1 - 0.14 * self.press.value
        p.translate(r.center())
        p.scale(s, s)
        p.translate(-r.center())
        bg = QColor("#c42b1c") if self.danger else QColor(T["surface_2"])
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(alpha(bg, self.hover.value))
        p.drawRoundedRect(r.adjusted(2, 2, -2, -2), 12, 12)
        p.setPen(QColor(T["text"]))
        p.setFont(icon_font(self.icon_px))
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, chr(self.glyph))
        p.end()


class ColorChip(QAbstractButton):
    """Круглый образец цвета для выбора акцента."""

    def __init__(self, color, tooltip="", parent=None):
        super().__init__(parent)
        self.color = color
        self.setToolTip(tooltip)
        self.setCheckable(True)
        self.setFixedSize(44, 44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sel = Tween(self)
        self.press = Tween(self)
        self.toggled.connect(lambda on: self.sel.to(1.0 if on else 0.0, th.NORMAL, th.SPRING if on else th.CURVE))

    def mousePressEvent(self, e):
        self.press.to(1.0, th.FAST)
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        self.press.to(0.0, th.SLOW, th.SPRING)
        super().mouseReleaseEvent(e)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = QPointF(self.width() / 2, self.height() / 2)
        sel = self.sel.value
        if sel > 0.01:
            p.setPen(QPen(alpha(T["text"], sel), 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(c, 20, 20)
        rad = (15 - 2 * self.press.value) * (1 - 0.12 * sel)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(self.color).darker(150))
        p.drawEllipse(c + QPointF(0, 2), rad, rad)
        p.setBrush(QColor(self.color))
        p.drawEllipse(c, rad, rad)
        p.end()


# ---------------------------------------------------------------- заголовок окна

class CaptionButton(QAbstractButton):
    """Кнопка окна как в Windows 11: 46 px шириной, на всю высоту заголовка, без скругления.

    Наведение — лёгкая подсветка (у «Закрыть» — красная #C42B1C), глиф 10 px.
    """

    W = 46

    def __init__(self, glyph, tooltip="", close=False, parent=None):
        super().__init__(parent)
        self.glyph, self.close = glyph, close
        self.setToolTip(tooltip)
        self.setFixedWidth(self.W)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.hover = Tween(self)
        self.down = False

    def enterEvent(self, e):
        self.hover.to(1.0, 90)

    def leaveEvent(self, e):
        self.hover.to(0.0, 150)

    def mousePressEvent(self, e):
        self.down = True
        self.update()
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        self.down = False
        self.update()
        super().mouseReleaseEvent(e)

    def paintEvent(self, _):
        p = QPainter(self)
        h = self.hover.value
        if self.close:
            bg = alpha("#c42b1c", h * (0.9 if self.down else 1.0))
            fg = mix(T["text"], "#ffffff", h)
        else:
            bg = alpha("#ffffff", h * (0.04 if self.down else 0.065))
            fg = alpha(T["text"], 0.8 if self.down else 1.0)
        p.fillRect(self.rect(), bg)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        p.setPen(fg)
        p.setFont(icon_font(10))
        p.drawText(QRectF(self.rect()), Qt.AlignmentFlag.AlignCenter, chr(self.glyph))
        p.end()


class TitleBar(QWidget):
    HEIGHT = 40

    def __init__(self, title, parent=None):
        super().__init__(parent)
        from app.i18n import tr
        self.setFixedHeight(self.HEIGHT)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(th.EDGE + 6, 0, 0, 0)
        lay.setSpacing(0)
        self.logo = QLabel()
        self.logo.setFixedSize(20, 20)
        self.title = label(title)
        self.title.setObjectName("WindowTitle")
        self.min_btn = CaptionButton(G.MIN, tr("Свернуть"))
        self.max_btn = CaptionButton(G.MAX, tr("Развернуть"))
        self.close_btn = CaptionButton(G.CLOSE, tr("Закрыть"), close=True)
        lay.addWidget(self.logo)
        lay.addSpacing(10)
        lay.addWidget(self.title)
        lay.addStretch()
        for w in (self.min_btn, self.max_btn, self.close_btn):
            lay.addWidget(w)
        self.min_btn.clicked.connect(lambda: self.window().showMinimized())
        self.max_btn.clicked.connect(self.toggle_max)
        self.close_btn.clicked.connect(lambda: self.window().close())

    def recolor(self):
        self.logo.setPixmap(logo_pixmap(20))
        self.update()

    def toggle_max(self):
        w = self.window()
        w.showNormal() if w.isMaximized() else w.showMaximized()

    def update_max_icon(self, maximized):
        from app.i18n import tr
        self.max_btn.glyph = G.RESTORE if maximized else G.MAX
        self.max_btn.setToolTip(tr("Восстановить") if maximized else tr("Развернуть"))
        self.max_btn.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.window().windowHandle().startSystemMove()

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.toggle_max()


def render_logo(px, accent=None, soft=False):
    """Логотип: «блок» с бортиком — тот же 3D-мотив, что у кнопок.

    Нарисован в сетке 22×22 и масштабируется в любой размер без потери чёткости
    (иконка окна, панели задач, ярлыка). Возвращает QImage px×px.
    soft=True — объём без тени: боковая грань — тот же цвет, чуть темнее,
    плюс мягкий блик сверху (варианты иконки).
    """
    from PyQt6.QtGui import QImage
    accent = QColor(accent or T["accent"])
    img = QImage(px, px, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    u = px / 22.0
    p.scale(u, u)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(accent.darker(122 if soft else 165))     # боковая грань (бортик)
    p.drawRoundedRect(QRectF(1, 4, 20, 17), 6, 6)
    face = QRectF(1, 1, 20, 17)
    if soft:
        grad = QLinearGradient(face.topLeft(), face.bottomLeft())
        grad.setColorAt(0, accent.lighter(108))
        grad.setColorAt(1, accent)
        p.setBrush(grad)
    else:
        p.setBrush(accent)                               # лицевая часть
    p.drawRoundedRect(face, 6, 6)
    if soft:
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(alpha("#ffffff", 0.35), 0.5))
        p.drawRoundedRect(face.adjusted(0.4, 0.4, -0.4, -0.4), 5.6, 5.6)
    p.setPen(th.on_color(accent))
    font = QFont(th.FONT)
    font.setPixelSize(max(1, round(12.1 * u)))           # 22 × 0.55, как у маленького логотипа
    font.setWeight(QFont.Weight.Black)
    p.save()
    p.scale(1 / u, 1 / u)                                # текст — в настоящих пикселях, без ступенек
    p.setFont(font)
    p.drawText(QRectF(face.x() * u, face.y() * u, face.width() * u, face.height() * u),
               Qt.AlignmentFlag.AlignCenter, "L")
    p.restore()
    p.end()
    return img


def logo_pixmap(size, scale=2):
    from PyQt6.QtGui import QPixmap
    pm = QPixmap.fromImage(render_logo(size * scale))
    pm.setDevicePixelRatio(scale)
    return pm


def logo_icon(accent=None):
    """Иконка окна/панели задач во всех нужных размерах."""
    from PyQt6.QtGui import QIcon, QPixmap
    icon = QIcon()
    for px in (16, 20, 24, 32, 40, 48, 64, 128, 256):
        icon.addPixmap(QPixmap.fromImage(render_logo(px, accent)))
    return icon


# ---------------------------------------------------------------- меню слева

class NavRail(QWidget):
    """Меню как в Lettudio: панель радиуса 22, отступ 5, пункты-«таблетки» по 40 px.

    Индикатор выбранного пункта плавно переезжает; иконка выбранного — акцентом.
    """

    page_selected = pyqtSignal(str)
    WIDTH = 168

    def __init__(self, parent=None):
        super().__init__(parent)
        self.items = []  # (key, glyph, text) или None — разделитель
        self.current = 0
        self.indicator = Tween(self)
        self.hover_idx = -1
        self.hover = Tween(self)
        self.press_idx = -1
        self.press = Tween(self)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedWidth(self.WIDTH)

    def add_item(self, key, glyph, text):
        self.items.append((key, glyph, text))
        self._resize()

    def add_separator(self):
        self.items.append(None)
        self._resize()

    def _layout(self):
        y = th.NAV_PAD
        rects = []
        for it in self.items:
            if it is None:
                rects.append(QRectF(th.NAV_PAD + 12, y + 5, self.WIDTH - 2 * th.NAV_PAD - 24, 1))
                y += 11
            else:
                rects.append(QRectF(th.NAV_PAD, y + 1.5, self.WIDTH - 2 * th.NAV_PAD, th.NAV_ITEM_H))
                y += th.NAV_ITEM_H + 3
        return rects, y + th.NAV_PAD

    def _resize(self):
        self.setFixedHeight(int(self._layout()[1]))

    def _index_at(self, pos):
        for i, r in enumerate(self._layout()[0]):
            if self.items[i] is not None and r.contains(QPointF(pos)):
                return i
        return -1

    def select(self, key, animate=True):
        for i, it in enumerate(self.items):
            if it and it[0] == key:
                self.current = i
                y = self._layout()[0][i].top()
                if animate:
                    self.indicator.to(y, th.NORMAL, th.CURVE)
                else:
                    self.indicator.value = y
                    self.update()

    def mouseMoveEvent(self, e):
        i = self._index_at(e.position())
        if i != self.hover_idx:
            self.hover_idx = i
            self.hover.value = 0.0
            self.hover.to(1.0 if i >= 0 else 0.0, th.FAST)

    def leaveEvent(self, e):
        self.hover.to(0.0, th.NORMAL)

    def mousePressEvent(self, e):
        i = self._index_at(e.position())
        if i >= 0:
            self.press_idx = i
            self.press.to(1.0, th.FAST)

    def mouseReleaseEvent(self, e):
        i = self._index_at(e.position())
        self.press.to(0.0, th.SLOW, th.SPRING)
        if i >= 0 and i == self.press_idx:
            self.page_selected.emit(self.items[i][0])

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(T["surface"]))
        p.drawRoundedRect(QRectF(self.rect()), th.NAV_RADIUS, th.NAV_RADIUS)

        rects, _ = self._layout()
        step = th.NAV_ITEM_H + 3
        ind_y = self.indicator.value
        if 0 <= self.current < len(rects):
            r = rects[self.current]
            ind = QRectF(r.left(), ind_y, r.width(), r.height())
            p.setBrush(QColor(T["surface_2"]))
            p.drawPath(stadium(ind))

        for i, (it, r) in enumerate(zip(self.items, rects)):
            if it is None:
                p.setBrush(alpha(T["text_dim"], 0.25))
                p.drawRect(r)
                continue
            key, glyph, text = it
            # Насколько индикатор «над» этим пунктом: цвета меняются, пока он едет
            k = max(0.0, 1.0 - abs(ind_y - r.top()) / step)
            if i == self.hover_idx and i != self.current:
                p.setBrush(alpha(T["surface_2"], 0.45 * self.hover.value * (1 - k)))
                p.drawPath(stadium(r))
            p.save()
            if i == self.press_idx and self.press.value > 0:
                s = 1 - 0.06 * self.press.value
                p.translate(r.center())
                p.scale(s, s)
                p.translate(-r.center())
            p.setPen(mix(T["text_dim"], T["accent"], k))
            p.setFont(icon_font(18))
            p.drawText(QRectF(r.left() + 11, r.top(), 22, r.height()), Qt.AlignmentFlag.AlignCenter, chr(glyph))
            p.setPen(mix(T["text_dim"], T["text"], k))
            p.setFont(ui_font(15, QFont.Weight.Bold if k > 0.5 else QFont.Weight.Medium))
            p.drawText(QRectF(r.left() + 43, r.top(), r.width() - 50, r.height()),
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)
            p.restore()
        p.end()


# ---------------------------------------------------------------- карточки

EMOJI_FONT = "Segoe UI Emoji"


def paint_cover(p, r, text="", glyph=None, round_=True, icon=None, radius=12):
    """Обложка: круг/скруглённый квадрат с буквой, глифом, эмодзи или картинкой.

    icon — иконка профиля: {"emoji": "⛏"} или {"image": "путь к файлу"}.
    """
    from PyQt6.QtGui import QPixmap
    path = QPainterPath()
    if round_:
        path.addEllipse(r)
    else:
        path.addRoundedRect(r, radius, radius)  # концентрично радиусу карточки 18 с отступом ~6
    image = (icon or {}).get("image")
    pm = QPixmap(image) if image else None
    if pm is not None and not pm.isNull():
        p.save()
        p.setClipPath(path)
        scaled = pm.scaled(int(r.width() * 2), int(r.height() * 2),
                           Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                           Qt.TransformationMode.SmoothTransformation)
        src = QRectF((scaled.width() - r.width() * 2) / 2, (scaled.height() - r.height() * 2) / 2,
                     r.width() * 2, r.height() * 2)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.drawPixmap(r, scaled, src)
        p.restore()
        return
    grad = QLinearGradient(r.topLeft(), r.bottomRight())
    grad.setColorAt(0, mix(T["accent"], T["surface"], 0.25))
    grad.setColorAt(1, th.fill())
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(grad)
    p.drawPath(path)
    emoji = (icon or {}).get("emoji")
    if emoji:
        f = QFont(EMOJI_FONT)
        f.setPixelSize(int(r.height() * 0.52))
        p.setFont(f)
        p.setPen(QColor("#ffffff"))
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, emoji)
        return
    p.setPen(QColor("#ffffff"))
    if glyph:
        p.setFont(icon_font(r.height() * 0.43))
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, chr(glyph))
    else:
        p.setFont(ui_font(r.height() * 0.41, QFont.Weight.Bold))
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, text[:1].upper())


class Avatar(QWidget):
    """Обложка карточки: круг с буквой (аккаунт) или скруглённый квадрат с иконкой (профиль)."""

    def __init__(self, text="", glyph=None, round_=True, icon=None, size=46, parent=None):
        super().__init__(parent)
        self.text, self.glyph, self.round, self.icon = text, glyph, round_, icon
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        paint_cover(p, QRectF(self.rect()), self.text, self.glyph, self.round, self.icon,
                    radius=12 * self.width() / 46)
        p.end()


class IconChip(QAbstractButton):
    """Вариант иконки профиля в редакторе: маленькая обложка с кольцом выбора."""

    def __init__(self, icon=None, glyph=None, tooltip="", parent=None):
        super().__init__(parent)
        self.icon, self.glyph = icon, glyph
        self.setToolTip(tooltip)
        self.setCheckable(True)
        self.setFixedSize(46, 46)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sel = Tween(self)
        self.press = Tween(self)
        self.toggled.connect(lambda on: self.sel.to(1.0 if on else 0.0, th.NORMAL, th.SPRING if on else th.CURVE))

    def mousePressEvent(self, e):
        self.press.to(1.0, th.FAST)
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        self.press.to(0.0, th.SLOW, th.SPRING)
        super().mouseReleaseEvent(e)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        sel = self.sel.value
        if sel > 0.01:
            p.setPen(QPen(alpha(T["accent"], sel), 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 13, 13)
        inset = 5 + 2 * self.press.value
        paint_cover(p, QRectF(self.rect()).adjusted(inset, inset, -inset, -inset), glyph=self.glyph,
                    round_=False, icon=self.icon, radius=9)
        p.end()


class Card(QWidget):
    """Карточка «обложка + название + подпись», как блок «Недавние» в Lettudio."""

    clicked = pyqtSignal()
    context_requested = pyqtSignal(object)

    def __init__(self, title, subtitle, avatar, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(70)
        self.setMinimumWidth(220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.hover = Tween(self)
        self.sel = Tween(self)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 12, 16, 12)
        lay.setSpacing(14)
        self.avatar = avatar
        lay.addWidget(avatar)
        texts = QVBoxLayout()
        texts.setSpacing(0)
        self.title = label(title, "title")
        self.subtitle = label(subtitle, "subtitle")
        texts.addStretch()
        texts.addWidget(self.title)
        texts.addWidget(self.subtitle)
        texts.addStretch()
        lay.addLayout(texts, 1)
        pressable(self, 0.97)

    def set_selected(self, selected, animate=False):
        if animate:
            self.sel.to(1.0 if selected else 0.0, th.NORMAL)
        else:
            self.sel.value = 1.0 if selected else 0.0
            self.update()

    def enterEvent(self, e):
        self.hover.to(1.0, th.FAST)

    def leaveEvent(self, e):
        self.hover.to(0.0, th.NORMAL)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self.rect().contains(e.position().toPoint()):
            self.clicked.emit()

    def contextMenuEvent(self, e):
        self.context_requested.emit(e.globalPos())

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        bg = mix(T["surface"], T["text"], 0.05 * self.hover.value)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(bg)
        p.drawRoundedRect(r, th.RADIUS, th.RADIUS)
        sel = self.sel.value
        if sel > 0.01:
            # Выбранная карточка: коралловая обводка и мягкая подсветка слева
            grad = QLinearGradient(r.topLeft(), r.topRight())
            grad.setColorAt(0, alpha(T["accent"], 0.16 * sel))
            grad.setColorAt(0.6, alpha(T["accent"], 0.0))
            p.setBrush(grad)
            p.drawRoundedRect(r, th.RADIUS, th.RADIUS)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(alpha(T["accent"], sel), 2))
            p.drawRoundedRect(r.adjusted(0.5, 0.5, -0.5, -0.5), th.RADIUS, th.RADIUS)
        p.end()


# ---------------------------------------------------------------- статус запуска

class LaunchStatus(QWidget):
    """Компактный статус рядом с кнопкой «Играть»: текст и тонкая полоса прогресса.

    Виден только во время установки/запуска или когда есть сообщение.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(260, 44)
        self.progress = Tween(self)
        self.visible_t = Tween(self)
        self.busy = False
        self.text = ""
        self.shimmer = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)

    def set_text(self, text):
        self.text = text or ""
        self.visible_t.to(1.0 if (self.busy or self.text) else 0.0, th.NORMAL)
        self.update()

    def set_progress(self, value):
        self.progress.to(max(0.0, min(1.0, value)), th.NORMAL)

    def set_busy(self, busy):
        self.busy = busy
        self._timer.start() if busy else self._timer.stop()
        if not busy:
            self.progress.to(0.0, th.SLOW)
        self.set_text(self.text if not busy else (self.text or "Подготовка..."))

    def _tick(self):
        self.shimmer = (self.shimmer + 0.015) % 1.5
        self.update()

    def paintEvent(self, _):
        v = self.visible_t.value
        if v <= 0.01:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setOpacity(v)
        w = float(self.width())
        p.setPen(QColor(T["text_dim"]))
        p.setFont(ui_font(13, QFont.Weight.Medium))
        fm = QFontMetrics(p.font())
        p.drawText(QRectF(0, 4, w, 20), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                   fm.elidedText(self.text, Qt.TextElideMode.ElideRight, int(w)))
        if self.busy or self.progress.value > 0:
            track = QRectF(0, 31, w, 3)  # дорожка 3 px, как sliderTheme в Lettudio
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(T["surface_2"]))
            p.drawPath(stadium(track))
            p.save()
            p.setClipPath(stadium(track))
            prog = self.progress.value
            if prog > 0:
                p.setBrush(QColor(T["accent"]))
                p.drawRect(QRectF(0, track.top(), w * prog, track.height()))
            if self.busy:  # бегущий блик, пока идёт работа
                x = w * (self.shimmer - 0.25)
                grad = QLinearGradient(QPointF(x - 50, 0), QPointF(x + 50, 0))
                grad.setColorAt(0, alpha(T["accent"], 0))
                grad.setColorAt(0.5, alpha(T["accent"], 0.75))
                grad.setColorAt(1, alpha(T["accent"], 0))
                p.setBrush(grad)
                p.drawRect(track)
            p.restore()
        p.end()


# ---------------------------------------------------------------- аккаунт

class Panel(QWidget):
    """Плашка surface со скруглением 18 — основа блоков на страницах."""

    def __init__(self, parent=None):
        super().__init__(parent)
        # По высоте — сколько нужно содержимому, лишнее место забирает отступ страницы
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(T["surface"]))
        p.drawRoundedRect(QRectF(self.rect()), th.RADIUS, th.RADIUS)
        p.end()


class Segmented(QWidget):
    """Переключатель из «таблеток»; выделение переезжает так же, как индикатор меню."""

    changed = pyqtSignal(int)

    def __init__(self, options, parent=None):
        super().__init__(parent)
        self.options = options
        self.index = 0
        self.pos_t = Tween(self)
        self.hover_idx = -1
        self.setFixedHeight(40)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        fm = QFontMetrics(ui_font(14, QFont.Weight.Bold))
        self.seg_w = max(fm.horizontalAdvance(o) for o in options) + 36
        self.setFixedWidth(int(self.seg_w * len(options) + 8))

    def set_index(self, i, animate=True):
        self.index = i
        if animate:
            self.pos_t.to(float(i), th.NORMAL)
        else:
            self.pos_t.value = float(i)
            self.update()

    def _at(self, x):
        return int(min(len(self.options) - 1, max(0, (x - 4) // self.seg_w)))

    def mouseMoveEvent(self, e):
        self.hover_idx = self._at(e.position().x())
        self.update()

    def leaveEvent(self, e):
        self.hover_idx = -1
        self.update()

    def mouseReleaseEvent(self, e):
        i = self._at(e.position().x())
        if i != self.index:
            self.set_index(i)
            self.changed.emit(i)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        # Подложка контрастна месту: на плашке — цвет фона, на фоне страницы — цвет плашки
        on_panel, w = False, self.parentWidget()
        while w is not None:
            if isinstance(w, Panel):
                on_panel = True
                break
            w = w.parentWidget()
        p.setBrush(QColor(T["background"] if on_panel else T["surface"]))
        p.drawPath(stadium(QRectF(self.rect())))
        x = 4 + self.pos_t.value * self.seg_w
        p.setBrush(QColor(T["surface_2"]))
        p.drawPath(stadium(QRectF(x, 4, self.seg_w, self.height() - 8)))
        for i, text in enumerate(self.options):
            k = max(0.0, 1.0 - abs(self.pos_t.value - i))
            r = QRectF(4 + i * self.seg_w, 0, self.seg_w, self.height())
            col = mix(T["text_dim"], T["text"], max(k, 0.5 if i == self.hover_idx else 0.0))
            p.setPen(col)
            p.setFont(ui_font(14, QFont.Weight.Bold if k > 0.5 else QFont.Weight.Medium))
            p.drawText(r, Qt.AlignmentFlag.AlignCenter, text)
        p.end()


class FlowGrid(QWidget):
    """Сетка карточек, которая сама меняет число колонок под ширину (адаптивность)."""

    def __init__(self, min_col_width=260, max_cols=3, stretch=True, parent=None):
        super().__init__(parent)
        from PyQt6.QtWidgets import QGridLayout
        self.min_col_width, self.max_cols, self.stretch = min_col_width, max_cols, stretch
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(th.EDGE)
        self.items = []
        self.cols = 0
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)

    def set_items(self, widgets):
        for w in self.items:
            self.grid.removeWidget(w)
            w.hide()
            w.deleteLater()
        self.items = list(widgets)
        self.cols = 0
        self._relayout()

    def _columns(self):
        w = max(1, self.width())
        return max(1, min(self.max_cols, (w + th.EDGE) // (self.min_col_width + th.EDGE)))

    def _relayout(self):
        cols = self._columns()
        if cols == self.cols and all(self.grid.indexOf(w) >= 0 for w in self.items):
            return
        self.cols = cols
        for w in self.items:
            self.grid.removeWidget(w)
        for i, w in enumerate(self.items):
            self.grid.addWidget(w, i // cols, i % cols)
        for c in range(self.max_cols):
            self.grid.setColumnStretch(c, 1 if (self.stretch and c < cols) else 0)
        if not self.stretch:  # мелкие элементы (иконки) — плотно слева, без растягивания
            self.grid.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        # Расставить карточки сразу, а не в следующем цикле событий — иначе они
        # на кадр появляются в углу и «проскакивают» на место
        self.grid.activate()

    def minimumSizeHint(self):
        # Минимум — одна колонка, иначе сетка не даст окну сузиться
        from PyQt6.QtCore import QSize
        widest = max((w.minimumSizeHint().width() for w in self.items), default=0)
        return QSize(max(widest, 200), super().minimumSizeHint().height())

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._relayout()


class EmptyHint(QWidget):
    """Смайлик-каомодзи и шутка на пустом месте. Клик — следующая, с упругим «прыжком»."""

    def __init__(self, items, parent=None):
        super().__init__(parent)
        import random
        self.items = list(items)
        random.shuffle(self.items)
        self.index = 0
        self.bounce = Tween(self, 1.0)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(150)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self.items:
            self.index = (self.index + 1) % len(self.items)
            self.bounce.value = 0.6
            self.bounce.to(1.0, th.SLOW + 200, th.SPRING)

    def paintEvent(self, _):
        if not self.items:
            return
        face, text = self.items[self.index]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        r = QRectF(self.rect())
        c = r.center()
        s = self.bounce.value
        p.save()
        p.translate(c.x(), c.y() - 14)
        p.scale(s, s)
        p.setPen(alpha(T["accent"], 0.85))
        f = ui_font(44, QFont.Weight.Bold)
        p.setFont(f)
        p.drawText(QRectF(-r.width() / 2, -40, r.width(), 64), Qt.AlignmentFlag.AlignCenter, face)
        p.restore()
        p.setPen(QColor(T["text_dim"]))
        p.setFont(ui_font(14, QFont.Weight.Medium))
        p.drawText(QRectF(0, c.y() + 30, r.width(), 24), Qt.AlignmentFlag.AlignCenter, text)
        p.end()


class PageFade(QWidget):
    """Переход между страницами: снимок новой страницы проявляется поверх фона со сдвигом.

    Анимируется картинка, а не живые виджеты — у карточек свои эффекты нажатия,
    и вложенные QGraphicsEffect в Qt на первых кадрах рисуются со смещением.
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.pix = None
        self.t = Tween(self, 1.0)
        self.t.finished.connect(self.hide)
        self.hide()

    def start(self, pixmap):
        self.pix = pixmap
        self.setGeometry(self.parentWidget().rect())
        self.raise_()
        self.show()
        self.t.value = 0.0
        self.t.to(1.0, th.NORMAL, th.CURVE)

    def paintEvent(self, _):
        if self.pix is None:
            return
        p = QPainter(self)
        t = self.t.value
        p.fillRect(self.rect(), QColor(T["background"]))
        p.setOpacity(t)
        p.drawPixmap(0, round(8 * (1 - t)), self.pix)
        p.end()
