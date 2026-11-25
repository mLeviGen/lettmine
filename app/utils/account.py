"""Аккаунт игрока: оффлайн-ник без регистрации или лицензия Microsoft.

Вход по лицензии — OAuth с PKCE: открывается браузер, Microsoft возвращает код
на http://localhost:<порт>, лаунчер обменивает его на токен Minecraft.
Для этого нужен Client ID приложения Azure, которому Mojang выдала доступ
к Minecraft API (форма: https://aka.ms/mce-reviewappid).
"""
import html
import re
import socket
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

import minecraft_launcher_lib

from app.i18n import tr
from minecraft_launcher_lib.exceptions import (
    AccountNotOwnMinecraft, AzureAppNotPermitted, InvalidRefreshToken,
)

REDIRECT_PORT = 51735
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}"
NICK_RE = re.compile(r"[A-Za-z0-9_]{3,16}")

OFFLINE, MICROSOFT = "offline", "microsoft"


def valid_nick(name):
    return bool(NICK_RE.fullmatch(name or ""))


def get_account(config):
    """Аккаунт из config.json; старые «профили» превращаются в один оффлайн-ник."""
    cfg = config.config
    if "account" not in cfg:
        names = [p.get("name", "") for p in cfg.get("profiles", [])]
        last = cfg.get("last_profile")
        nick = last if last in names else (names[0] if names else "")
        cfg["account"] = {"type": OFFLINE, "offline_name": nick if valid_nick(nick) else ""}
        cfg.pop("profiles", None)
        cfg.pop("last_profile", None)
        config.save_config()
    acc = cfg["account"]
    acc.setdefault("type", OFFLINE)
    acc.setdefault("offline_name", "")
    acc.setdefault("microsoft", None)  # {"name", "id", "refresh_token"}
    return acc


def save_account(config, **changes):
    acc = get_account(config)
    acc.update(changes)
    config.save_config()
    return acc


def display_name(acc):
    if acc["type"] == MICROSOFT:
        return (acc.get("microsoft") or {}).get("name", "")
    return acc.get("offline_name", "")


def ready(acc):
    if acc["type"] == MICROSOFT:
        return bool((acc.get("microsoft") or {}).get("refresh_token"))
    return valid_nick(acc.get("offline_name"))


# ---------------------------------------------------------------- Microsoft

def start_login(client_id):
    """Ссылка для браузера + данные для проверки ответа: (url, state, code_verifier)."""
    return minecraft_launcher_lib.microsoft_account.get_secure_login_data(client_id, REDIRECT_URI)


_DONE_PAGE = """<!doctype html><meta charset="utf-8"><title>LettMine</title>
<body style="margin:0;height:100vh;display:grid;place-items:center;background:#161616;color:#ededed;
font-family:Nunito,Segoe UI,sans-serif"><div style="background:#232323;padding:32px 40px;border-radius:18px;
text-align:center"><div style="font-size:22px;font-weight:700;margin-bottom:8px">{title}</div>
<div style="color:#8f8f8f">{text}</div></div></body>"""


def wait_for_redirect(timeout=300, should_stop=lambda: False):
    """Ждёт, пока браузер вернётся на localhost с кодом; возвращает полный URL ответа."""
    result = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            if "code" in params or "error" in params:
                result["url"] = REDIRECT_URI + self.path
                ok = "code" in params
                body = _DONE_PAGE.format(
                    title="Готово" if ok else "Вход отменён",
                    text="Вернитесь в LettMine — вкладку можно закрыть." if ok
                    else html.escape(params.get("error_description", ["Попробуйте ещё раз."])[0]),
                )
            else:
                body = _DONE_PAGE.format(title="LettMine", text="Ожидание входа…")
            data = body.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    try:
        server = HTTPServer(("127.0.0.1", REDIRECT_PORT), Handler)
    except OSError:
        raise RuntimeError(tr("Порт {port} занят — закройте программу, которая его использует.", port=REDIRECT_PORT))
    server.timeout = 1
    waited = 0
    try:
        while "url" not in result and waited < timeout and not should_stop():
            server.handle_request()
            waited += 1
    finally:
        server.server_close()
    if "url" not in result:
        raise TimeoutError(tr("Вход не завершён — время ожидания истекло."))
    return result["url"]


def finish_login(client_id, url, state, code_verifier):
    """Обмен кода на аккаунт Minecraft: {"name", "id", "access_token", "refresh_token", ...}."""
    params = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    if "error" in params:
        raise RuntimeError(params.get("error_description", params["error"])[0])
    code = minecraft_launcher_lib.microsoft_account.parse_auth_code_url(url, state)
    return minecraft_launcher_lib.microsoft_account.complete_login(client_id, None, REDIRECT_URI, code, code_verifier)


def refresh(client_id, refresh_token):
    """Свежий токен перед запуском (токен Minecraft живёт около суток)."""
    return minecraft_launcher_lib.microsoft_account.complete_refresh(client_id, None, REDIRECT_URI, refresh_token)


def explain_error(e):
    if isinstance(e, AzureAppNotPermitted):
        return tr("Приложению Azure не разрешён доступ к Minecraft API. "
                  "Новые Client ID нужно одобрить у Mojang: https://aka.ms/mce-reviewappid")
    if isinstance(e, AccountNotOwnMinecraft):
        return tr("На этом аккаунте Microsoft нет купленной Minecraft: Java Edition.")
    if isinstance(e, InvalidRefreshToken):
        return tr("Сессия устарела — войдите через Microsoft ещё раз.")
    if isinstance(e, (socket.gaierror, ConnectionError)):
        return tr("Нет соединения с серверами Microsoft.")
    return f"{type(e).__name__}: {e}"
