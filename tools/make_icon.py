"""Собирает иконку приложения из логотипа: app/assets/icon.ico и icon.png.

    .venv\\Scripts\\python tools\\make_icon.py
"""
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from PyQt6.QtCore import QBuffer, QIODevice  # noqa: E402
from PyQt6.QtGui import QGuiApplication  # noqa: E402

from app.ui import theme as th  # noqa: E402
from app.ui.widgets import render_logo  # noqa: E402

ICO_SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)
# Значки других приложений LettCup в том же стиле (объём без тени)
VARIANTS = {"Lettudio": "#f2f2f2", "LettCups_Browser": "#6fd6b0", "LettTube": "#5aa9ff"}


def png_bytes(img):
    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(buf, "PNG")
    return bytes(buf.data())


def write_ico(path, images):
    """ICO с PNG внутри — так Windows хранит иконки любых размеров (Vista+)."""
    header = struct.pack("<HHH", 0, 1, len(images))
    entries, blobs = b"", b""
    offset = 6 + 16 * len(images)
    for size, data in images:
        dim = 0 if size >= 256 else size  # 0 означает 256
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(data), offset)
        blobs += data
        offset += len(data)
    with open(path, "wb") as f:
        f.write(header + entries + blobs)


def main():
    app = QGuiApplication(sys.argv)  # noqa: F841 — нужен для шрифтов
    th.load_fonts()
    accent = th.DEFAULT_THEME["accent"]
    out = os.path.join(ROOT, "app", "assets")
    write_ico(os.path.join(out, "icon.ico"), [(s, png_bytes(render_logo(s, accent))) for s in ICO_SIZES])
    render_logo(512, accent).save(os.path.join(out, "icon.png"))
    print("Готово:", os.path.join(out, "icon.ico"), "и icon.png")

    # Значки приложений LettCup: белый, мятный, синий
    variants = os.path.join(out, "icons")
    os.makedirs(variants, exist_ok=True)
    for name, color in VARIANTS.items():
        base = os.path.join(variants, name)
        write_ico(base + ".ico", [(s, png_bytes(render_logo(s, color, soft=True))) for s in ICO_SIZES])
        render_logo(512, color, soft=True).save(base + ".png")
        print("Вариант:", base + ".ico")


if __name__ == "__main__":
    main()
