"""Нативная рамка Windows 11 для окна со своим заголовком.

Окну возвращаются стили обычного окна (WS_CAPTION | WS_THICKFRAME), а системная рамка
прячется обработкой WM_NCCALCSIZE. Благодаря этому Windows сама даёт:
скруглённые углы, тень, анимации сворачивания, Aero Snap (привязку к краям),
меню раскладок при наведении на «Развернуть» и правильный разворот без перекрытия
панели задач. Заголовок и края окна отдаются системе через WM_NCHITTEST.
"""
import ctypes
import ctypes.wintypes as wt
import os

from PyQt6.QtCore import QPoint
from PyQt6.QtGui import QCursor

if os.name == "nt":
    user32 = ctypes.windll.user32
    dwmapi = ctypes.windll.dwmapi

WM_NCCALCSIZE, WM_NCHITTEST = 0x0083, 0x0084
WM_NCMOUSEMOVE, WM_NCLBUTTONDOWN, WM_NCLBUTTONUP, WM_NCMOUSELEAVE = 0x00A0, 0x00A1, 0x00A2, 0x02A2
HTCLIENT, HTCAPTION, HTMAXBUTTON = 1, 2, 9
HTLEFT, HTRIGHT, HTTOP, HTTOPLEFT, HTTOPRIGHT, HTBOTTOM, HTBOTTOMLEFT, HTBOTTOMRIGHT = 10, 11, 12, 13, 14, 15, 16, 17
GWL_STYLE = -16
WS_CAPTION, WS_THICKFRAME, WS_MINIMIZEBOX, WS_MAXIMIZEBOX = 0x00C00000, 0x00040000, 0x00020000, 0x00010000
SWP_FLAGS = 0x0020 | 0x0002 | 0x0001 | 0x0004  # FRAMECHANGED | NOMOVE | NOSIZE | NOZORDER
SM_CXSIZEFRAME, SM_CXPADDEDBORDER = 32, 92
DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWCP_ROUND, DWMWCP_ROUNDSMALL = 2, 3
RESIZE_BORDER = 6  # логические пиксели


class MARGINS(ctypes.Structure):
    _fields_ = [("l", ctypes.c_int), ("r", ctypes.c_int), ("t", ctypes.c_int), ("b", ctypes.c_int)]


class TRACKMOUSEEVENT(ctypes.Structure):
    _fields_ = [("cbSize", wt.DWORD), ("dwFlags", wt.DWORD), ("hwndTrack", wt.HWND), ("dwHoverTime", wt.DWORD)]


def set_corners(widget, small=False):
    """Скругление углов окна/всплывающего окна средствами Windows 11."""
    if os.name != "nt":
        return
    try:
        pref = ctypes.c_int(DWMWCP_ROUNDSMALL if small else DWMWCP_ROUND)
        dwmapi.DwmSetWindowAttribute(int(widget.winId()), DWMWA_WINDOW_CORNER_PREFERENCE,
                                     ctypes.byref(pref), ctypes.sizeof(pref))
    except Exception:
        pass


def install(window):
    """Вернуть окну стили обычного окна; системная рамка спрячется в WM_NCCALCSIZE."""
    if os.name != "nt":
        return
    hwnd = int(window.winId())
    style = user32.GetWindowLongW(hwnd, GWL_STYLE)
    user32.SetWindowLongW(hwnd, GWL_STYLE, style | WS_CAPTION | WS_THICKFRAME | WS_MINIMIZEBOX | WS_MAXIMIZEBOX)
    # Тонкая «рамка» в клиентскую область — без неё DWM не рисует тень
    margins = MARGINS(0, 0, 1, 0)
    dwmapi.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(margins))
    set_corners(window)
    user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, SWP_FLAGS)


def _frame_thickness():
    return user32.GetSystemMetrics(SM_CXSIZEFRAME) + user32.GetSystemMetrics(SM_CXPADDEDBORDER)


def handle(window, message):
    """Обработать сообщение Windows. Возвращает (обработано, результат) для nativeEvent."""
    msg = wt.MSG.from_address(int(message))
    m = msg.message

    if m == WM_NCCALCSIZE and msg.wParam:
        if window.isMaximized():
            # Развёрнутое окно Windows выдвигает за край экрана на толщину рамки — подрезаем
            rect = wt.RECT.from_address(msg.lParam)
            t = _frame_thickness()
            rect.left += t
            rect.top += t
            rect.right -= t
            rect.bottom -= t
        return True, 0  # вся площадь окна — клиентская: системной рамки не видно

    if m == WM_NCHITTEST:
        return True, hit_test(window)

    bar = window.title_bar
    if m == WM_NCMOUSEMOVE:
        over = msg.wParam == HTMAXBUTTON
        bar.max_btn.hover.to(1.0 if over else 0.0, 90 if over else 150)
        if over:
            tme = TRACKMOUSEEVENT(ctypes.sizeof(TRACKMOUSEEVENT), 0x00000002 | 0x00000010, msg.hWnd, 0)
            user32.TrackMouseEvent(ctypes.byref(tme))  # TME_LEAVE | TME_NONCLIENT
        return False, 0
    if m == WM_NCMOUSELEAVE:
        bar.max_btn.hover.to(0.0, 150)
        return False, 0
    if m == WM_NCLBUTTONDOWN and msg.wParam == HTMAXBUTTON:
        bar.max_btn.down = True
        bar.max_btn.update()
        return True, 0
    if m == WM_NCLBUTTONUP and msg.wParam == HTMAXBUTTON:
        bar.max_btn.down = False
        bar.max_btn.hover.to(0.0, 150)
        bar.toggle_max()
        return True, 0
    return False, 0


def hit_test(window):
    pos = window.mapFromGlobal(QCursor.pos())
    x, y, w, h = pos.x(), pos.y(), window.width(), window.height()
    if not window.isMaximized():
        b = RESIZE_BORDER
        left, right, top, bottom = x < b, x >= w - b, y < b, y >= h - b
        if top and left:
            return HTTOPLEFT
        if top and right:
            return HTTOPRIGHT
        if bottom and left:
            return HTBOTTOMLEFT
        if bottom and right:
            return HTBOTTOMRIGHT
        if left:
            return HTLEFT
        if right:
            return HTRIGHT
        if top:
            return HTTOP
        if bottom:
            return HTBOTTOM

    bar = window.title_bar
    if y < bar.height():
        child = bar.childAt(bar.mapFrom(window, QPoint(x, y)))
        if child is bar.max_btn:
            return HTMAXBUTTON  # Windows 11 покажет меню раскладок (Snap Layouts)
        if child in (bar.min_btn, bar.close_btn):
            return HTCLIENT
        return HTCAPTION  # перетаскивание, двойной клик, Aero Snap — средствами Windows
    return HTCLIENT
