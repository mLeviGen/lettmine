"""Тема LettMine: палитра, отступы и тайминги — как в Lettudio, акцент — коралловый."""
import os

from PyQt6.QtCore import QEasingCurve
from PyQt6.QtGui import QColor, QFontDatabase

ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
FONT = "Nunito"

# Палитра Lettudio (theme.dart) + свой акцент
DEFAULT_THEME = {
    "accent": "#ff7f50",       # коралловый
    "background": "#161616",
    "surface": "#232323",      # плашки: меню, карточки, плеер
    "surface_2": "#3a3a3a",    # индикатор меню, дорожки, вторичные кнопки
    "text": "#ededed",
    "text_dim": "#8f8f8f",
}

ACCENT_PRESETS = [
    ("Коралл", "#ff7f50"),
    ("Персик", "#ffab76"),
    ("Сирень", "#cfa3cc"),
    ("Мята", "#6fd6b0"),
    ("Небо", "#6fb3ff"),
    ("Лимон", "#e8d45a"),
]

# Отступы и радиусы (Lettudio: _edge = 10, radius = 18, меню: padding 5, пункт 40)
EDGE = 10
RADIUS = 18
NAV_RADIUS = 22
NAV_PAD = 5
NAV_ITEM_H = 40

# Анимации (Lettudio: Motion.fast / normal / slow, easeOutCubic)
FAST, NORMAL, SLOW = 180, 280, 420
CURVE = QEasingCurve.Type.OutCubic
CURVE_IN = QEasingCurve.Type.InCubic
SPRING = QEasingCurve.Type.OutBack

# Текущая тема — читают виджеты при отрисовке
T = dict(DEFAULT_THEME)


def load_fonts():
    folder = os.path.join(ASSETS, "fonts")
    if os.path.isdir(folder):
        for name in os.listdir(folder):
            if name.lower().endswith(".ttf"):
                QFontDatabase.addApplicationFont(os.path.join(folder, name))


def resolve(styles):
    theme = dict(DEFAULT_THEME)
    accent = (styles or {}).get("accent")
    if accent and QColor(accent).isValid():
        theme["accent"] = accent
    T.clear()
    T.update(theme)
    return theme


def mix(a, b, t):
    """Смешать два цвета: t=0 → a, t=1 → b."""
    a, b = QColor(a), QColor(b)
    return QColor(
        round(a.red() + (b.red() - a.red()) * t),
        round(a.green() + (b.green() - a.green()) * t),
        round(a.blue() + (b.blue() - a.blue()) * t),
        round(a.alpha() + (b.alpha() - a.alpha()) * t),
    )


def alpha(color, a):
    c = QColor(color)
    c.setAlphaF(max(0.0, min(1.0, a)))
    return c


def on_color(color):
    """Цвет текста поверх заливки — как ThemeData.estimateBrightnessForColor во Flutter."""
    c = QColor(color)

    def lin(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

    lum = 0.2126 * lin(c.red()) + 0.7152 * lin(c.green()) + 0.0722 * lin(c.blue())
    return QColor("#1a1a1a") if (lum + 0.05) ** 2 > 0.15 else QColor("#ffffff")


def fill(t=None):
    """Приглушённый акцент для заливок (как fill #654365 у сиреневой темы Lettudio)."""
    t = t or T
    return mix(t["accent"], t["surface"], 0.55)


def stylesheet(t):
    check = os.path.join(ASSETS, "check.svg").replace("\\", "/")
    hover = mix(t["surface"], t["text"], 0.06).name()
    a = QColor(t["accent"])
    focus = f"rgba({a.red()}, {a.green()}, {a.blue()}, 0.65)"  # как focusedInputBorder в Lettudio
    return f"""
    * {{ font-family: "{FONT}", "Segoe UI"; color: {t['text']}; outline: none; }}
    QMainWindow, #Root, QDialog {{ background: {t['background']}; }}
    QToolTip {{ background: {t['surface_2']}; color: {t['text']}; border: none; padding: 6px 10px; border-radius: 10px; }}

    #WindowTitle {{ font-size: 15px; font-weight: 600; }}

    QLabel[role="section"] {{ color: {t['text_dim']}; font-size: 12px; font-weight: 400; letter-spacing: 1.2px; }}
    QLabel[role="title"] {{ font-size: 15px; font-weight: 600; }}
    QLabel[role="subtitle"] {{ color: {t['text_dim']}; font-size: 12px; }}
    QLabel[role="hint"] {{ color: {t['text_dim']}; font-size: 13px; }}
    QLabel[role="pageTitle"] {{ font-size: 24px; font-weight: 700; }}

    QLineEdit, QSpinBox, QComboBox {{
        background: {t['surface']}; border: 1px solid transparent; border-radius: {RADIUS}px;
        padding: 8px 15px; font-size: 14px; min-height: 20px;
        selection-background-color: {t['accent']}; selection-color: {on_color(t['accent']).name()};
    }}
    QLineEdit:hover, QSpinBox:hover, QComboBox:hover {{ background: {hover}; }}
    QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{ border-color: {focus}; }}
    QLineEdit[readOnly="true"] {{ color: {t['text_dim']}; }}
    /* Поле внутри плашки surface — на цвете фона, иначе сливается */
    Panel QLineEdit, Panel QSpinBox, Panel QComboBox {{ background: {t['background']}; }}
    Panel QLineEdit:hover, Panel QSpinBox:hover, Panel QComboBox:hover {{ background: {mix(t['background'], t['text'], 0.05).name()}; }}
    QSpinBox::up-button, QSpinBox::down-button {{ width: 0; border: none; }}
    QComboBox::drop-down {{ border: none; width: 24px; }}
    QComboBox QAbstractItemView {{
        background: {t['surface']}; border: none; padding: 5px; outline: none;
        selection-background-color: {t['surface_2']}; selection-color: {t['text']};
    }}

    QCheckBox {{ font-size: 14px; spacing: 10px; }}
    QCheckBox::indicator, QListWidget::indicator {{
        width: 20px; height: 20px; border-radius: 7px; background: {t['surface_2']};
    }}
    QCheckBox::indicator:checked, QListWidget::indicator:checked {{ background: {t['accent']}; image: url({check}); }}

    QPlainTextEdit#LogView {{
        background: {t['surface']}; border: none; border-radius: {RADIUS}px; padding: 10px 6px 10px 14px;
        font-family: "Cascadia Mono", "Consolas", monospace; font-size: 12px;
        selection-background-color: {t['accent']}; selection-color: {on_color(t['accent']).name()};
    }}
    QListWidget {{ background: transparent; border: none; font-size: 14px; }}
    QListWidget::item {{
        background: {t['surface']}; border-radius: 14px; padding: 5px 14px; margin: 2px 0;
        border: 2px solid transparent; color: {t['text']};
    }}
    QListWidget::item:hover {{ background: {hover}; }}
    QListWidget::item:selected {{ background: {hover}; border-color: {t['accent']}; }}

    QScrollArea {{ background: transparent; border: none; }}
    QScrollArea > QWidget > QWidget {{ background: transparent; }}
    QScrollBar:vertical, QScrollBar:horizontal {{ background: transparent; width: 10px; height: 10px; margin: 2px; }}
    QScrollBar::handle {{ background: {t['surface_2']}; border-radius: 3px; min-height: 30px; min-width: 30px; }}
    QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{ width: 0; height: 0; background: none; }}

    QMenu {{ background: {t['surface']}; border: 1px solid {t['surface_2']}; border-radius: 14px; padding: 6px; }}
    QMenu::item {{ padding: 8px 20px; border-radius: 9px; }}
    QMenu::item:selected {{ background: {t['surface_2']}; }}

    QDialog QPushButton, QMessageBox QPushButton, QInputDialog QPushButton {{
        background: {t['surface_2']}; border: none; border-radius: 16px; padding: 7px 20px; min-width: 70px;
    }}
    QDialog QPushButton:hover {{ background: {mix(t['surface_2'], t['text'], 0.1).name()}; }}
    QDialog QPushButton:default {{ background: {t['accent']}; color: {on_color(t['accent']).name()}; }}
    """
