"""Тема оформления: формы как у Lettudio, акцент — свой (darkviolet + pink)."""
from PyQt6.QtGui import QColor

DEFAULT_THEME = {
    "accent": "#9400d3",       # darkviolet — фирменный цвет LettMine
    "accent_2": "#ffc0cb",     # pink — обводка/подсветка
    "background": "#141414",
    "surface": "#1f1f1f",
    "surface_2": "#2b2b2b",
    "text": "#ffffff",
    "text_dim": "#9a9a9a",
}

THEME_LABELS = {
    "accent": "Акцентный цвет",
    "accent_2": "Второй акцент (обводка)",
    "background": "Фон окна",
    "surface": "Панели",
    "surface_2": "Карточки",
    "text": "Текст",
    "text_dim": "Второстепенный текст",
}


def resolve(styles):
    theme = dict(DEFAULT_THEME)
    theme.update({k: v for k, v in (styles or {}).items() if k in DEFAULT_THEME})
    return theme


def mix(a, b, t):
    """Смешать два цвета: t=0 → a, t=1 → b."""
    a, b = QColor(a), QColor(b)
    return QColor(
        round(a.red() + (b.red() - a.red()) * t),
        round(a.green() + (b.green() - a.green()) * t),
        round(a.blue() + (b.blue() - a.blue()) * t),
    )


def stylesheet(t):
    hover = mix(t["surface_2"], t["text"], 0.08).name()
    accent_hover = mix(t["accent"], "#ffffff", 0.15).name()
    accent_muted = mix(t["accent"], t["surface_2"], 0.45).name()
    return f"""
    * {{
        font-family: "Segoe UI Variable Text", "Segoe UI";
        color: {t['text']};
        outline: none;
    }}
    QMainWindow, #Root {{ background: {t['background']}; }}
    QToolTip {{ background: {t['surface_2']}; border: none; padding: 6px; border-radius: 8px; }}

    /* Заголовок окна */
    #TitleBar QPushButton {{
        background: transparent; border: none; border-radius: 8px;
        min-width: 40px; min-height: 36px;
    }}
    #TitleBar QPushButton:hover {{ background: {t['surface_2']}; }}
    #TitleBar QPushButton#CloseButton:hover {{ background: #c42b1c; }}
    #WindowTitle {{ font-size: 15px; }}

    /* Боковая панель */
    #Sidebar {{ background: {t['surface']}; border-radius: 26px; }}
    #Sidebar QPushButton {{
        background: transparent; border: none; border-radius: 22px;
        color: {t['text_dim']}; font-size: 15px; text-align: left;
        padding: 11px 16px;
    }}
    #Sidebar QPushButton:hover {{ background: {hover}; color: {t['text']}; }}
    #Sidebar QPushButton:checked {{ background: {t['surface_2']}; color: {t['text']}; font-weight: 600; }}
    #SidebarLine {{ background: {t['surface_2']}; max-height: 1px; min-height: 1px; }}

    /* Заголовки секций */
    QLabel[role="section"] {{
        color: {t['text_dim']}; font-size: 13px; letter-spacing: 1.5px; font-weight: 600;
    }}
    QLabel[role="title"] {{ font-size: 15px; }}
    QLabel[role="subtitle"] {{ color: {t['text_dim']}; font-size: 12px; }}
    QLabel[role="hint"] {{ color: {t['text_dim']}; font-size: 13px; }}
    QLabel[role="pageTitle"] {{ font-size: 26px; font-weight: 600; }}

    /* Карточки */
    #Card {{ background: {t['surface']}; border: 2px solid transparent; border-radius: 18px; }}
    #Card:hover {{ background: {t['surface_2']}; }}
    #Card[selected="true"] {{ background: {t['surface_2']}; border: 2px solid {t['accent']}; }}

    /* Нижняя панель */
    #BarRight {{ background: {t['surface']}; border-radius: 26px; }}
    #BarRight QPushButton {{ background: transparent; border: none; border-radius: 20px; min-width: 40px; min-height: 40px; }}
    #BarRight QPushButton:hover {{ background: {t['surface_2']}; }}
    #BarRight QPushButton#PlayButton {{
        background: {t['accent']}; border: 2px solid {t['accent_2']};
        border-radius: 24px; min-width: 48px; min-height: 48px;
    }}
    #BarRight QPushButton#PlayButton:hover {{ background: {accent_hover}; }}
    #BarRight QPushButton#PlayButton:disabled {{ background: {accent_muted}; border-color: {accent_muted}; }}
    #BarRight QPushButton#Pill {{
        background: {accent_muted}; border-radius: 16px; min-width: 60px; min-height: 32px;
        font-weight: 600; padding: 0 12px;
    }}
    #BarRight QPushButton#Pill:hover {{ background: {t['accent']}; }}
    #NowTitle {{ font-size: 18px; font-weight: 600; }}
    #NowSub {{ color: {t['text_dim']}; font-size: 11px; letter-spacing: 0.5px; }}
    #NowStatus {{ color: {t['text_dim']}; font-size: 14px; }}

    /* Обычные кнопки и поля */
    QPushButton[kind="pill"] {{
        background: {t['surface_2']}; border: 2px solid transparent; border-radius: 18px;
        padding: 6px 18px; min-height: 20px; font-size: 14px;
    }}
    QPushButton[kind="pill"]:hover {{ background: {hover}; }}
    QPushButton[kind="accent"] {{
        background: {t['accent']}; border: 2px solid {t['accent_2']}; border-radius: 18px;
        padding: 6px 20px; min-height: 20px; font-size: 14px; font-weight: 600;
    }}
    QPushButton[kind="accent"]:hover {{ background: {accent_hover}; }}
    QPushButton[kind="accent"]:disabled {{ background: {accent_muted}; border-color: {accent_muted}; color: {t['text_dim']}; }}
    QPushButton[kind="swatch"] {{ border: 2px solid {t['surface_2']}; border-radius: 16px; min-width: 64px; min-height: 32px; }}

    QLineEdit, QSpinBox, QComboBox {{
        background: {t['surface_2']}; border: 2px solid transparent; border-radius: 18px;
        padding: 7px 14px; font-size: 14px; selection-background-color: {t['accent']};
    }}
    QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{ border-color: {t['accent']}; }}
    QSpinBox::up-button, QSpinBox::down-button {{ width: 0; border: none; }}
    QComboBox::drop-down {{ border: none; width: 26px; }}
    QComboBox QAbstractItemView {{
        background: {t['surface_2']}; border: none; border-radius: 12px; padding: 6px;
        selection-background-color: {t['accent']};
    }}
    QCheckBox {{ font-size: 14px; spacing: 10px; }}
    QCheckBox::indicator {{ width: 20px; height: 20px; border-radius: 6px; background: {t['surface_2']}; }}
    QCheckBox::indicator:checked {{ background: {t['accent']}; border: 2px solid {t['accent_2']}; }}

    QListWidget {{
        background: transparent; border: none; font-size: 14px;
    }}
    QListWidget::item {{ background: {t['surface']}; border-radius: 14px; padding: 8px 14px; margin: 2px 0; border: 2px solid transparent; }}
    QListWidget::item:hover {{ background: {t['surface_2']}; }}
    QListWidget::item:selected {{ background: {t['surface_2']}; border: 2px solid {t['accent']}; }}
    QListWidget::indicator {{ width: 20px; height: 20px; border-radius: 6px; background: {t['surface_2']}; }}
    QListWidget::indicator:checked {{ background: {t['accent']}; }}

    QScrollArea {{ background: transparent; border: none; }}
    QScrollArea > QWidget > QWidget {{ background: transparent; }}
    QScrollBar:vertical, QScrollBar:horizontal {{ background: transparent; width: 10px; height: 10px; margin: 4px; }}
    QScrollBar::handle {{ background: {t['surface_2']}; border-radius: 3px; min-height: 30px; min-width: 30px; }}
    QScrollBar::handle:hover {{ background: {hover}; }}
    QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{ width: 0; height: 0; background: none; }}

    QMenu {{ background: {t['surface_2']}; border-radius: 12px; padding: 6px; }}
    QMenu::item {{ padding: 8px 18px; border-radius: 8px; }}
    QMenu::item:selected {{ background: {t['accent']}; }}
    QInputDialog, QMessageBox, QColorDialog, QFileDialog {{ background: {t['surface']}; }}
    """
