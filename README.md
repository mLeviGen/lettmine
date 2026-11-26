# LettMine

A Minecraft: Java Edition launcher for Windows, part of the LettCup app family.

![LettMine](docs/screenshot.png)

* **Profiles.** Each profile has its own game version, loader (Vanilla or Fabric), memory, icon and folder with mods, worlds and settings. Versions, libraries and Java are downloaded once and shared by all profiles.
* **Account.** Play with an offline nickname or sign in with a Microsoft account that owns the game.
* **Mods** are switched on and off with checkboxes right in the profile.
* **Log** of the game and the launcher in a tab — no console window.
* **Java** is picked automatically for the game version.
* Russian and English interface, selectable accent color.

## Installation

1. Install [Python 3.11 or newer](https://www.python.org/downloads/) with “Add python.exe to PATH” checked.
2. Download `LettMine-<version>-windows.zip` from the [releases](https://github.com/mLeviGen/lettmine/releases/latest) page and unpack it anywhere.
3. Run `LettMine.bat`. On the first run it prepares the environment (about a minute); after that the launcher opens right away.
4. From then on, start `LettMine.exe` — you can create a shortcut to it or pin it to the taskbar.

Game data is stored in the `.lettmine` folder next to the launcher, settings in `app/data/config.json`.

## Licensed sign-in

It needs the Client ID of an Azure app that Mojang has granted access to the Minecraft API:

1. [portal.azure.com](https://portal.azure.com) → Microsoft Entra ID → App registrations → New registration.
2. Supported account types must include **personal Microsoft accounts**. Redirect URI: “Public client/native (mobile & desktop)”, `http://localhost:51735`.
3. Apply to Mojang: [aka.ms/mce-reviewappid](https://aka.ms/mce-reviewappid).
4. Paste the Client ID into Settings → Licensed sign-in.

## Development

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python app.py
```

| Command | What it does |
|---|---|
| `tools\make_exe.py` | builds `LettMine.exe` and a shortcut (needs MinGW: gcc + windres) |
| `tools\make_icon.py` | rebuilds the icons from the logo |
| `tools\check_i18n.py` | checks that every string has an English translation |
| `tools\package.py` | builds the release archive into `dist\` |

Design rules shared by LettCup apps are in [docs/DESIGN.md](docs/DESIGN.md) (in Russian).

## Releases

The version is defined in one place — `app/version.py`. To publish a release:

```powershell
git commit -am "LettMine 0.9.1: ..."
git tag v0.9.1
git push --follow-tags
```

GitHub Actions builds `LettMine.exe` and the archive and publishes the release with a changelog. The tag must match the version in `app/version.py`.

## Third-party components

* [minecraft-launcher-lib](https://codeberg.org/JakobDev/minecraft-launcher-lib), [PyQt6](https://www.riverbankcomputing.com/software/pyqt/).
* [Nunito](https://github.com/googlefonts/nunito) font — SIL Open Font License 1.1 (`app/assets/fonts/OFL.txt`).

Minecraft is a trademark of Mojang Studios. LettMine is an unofficial launcher, not affiliated with Mojang or Microsoft.
