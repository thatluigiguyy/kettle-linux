"""Shared code for Kettle Studio, the Kettle Store and the Kettle app runner.

A Kettle app is just a folder:
    my-app/
        kettle.json   name, icon, description, version, author, window size
        main.qml      the app itself (QML, the language KDE apps are built with)
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

from templates import TEMPLATES

HERE = Path(__file__).resolve().parent
HOME = Path(os.environ.get("KETTLE_HOME") or Path.home())
DATA = Path(os.environ.get("XDG_DATA_HOME") or HOME / ".local" / "share")
PROJECTS_DIR = HOME / "Kettle Apps"              # apps you are making
INSTALLED_DIR = DATA / "kettle" / "apps"         # apps you downloaded
LAUNCHER_DIR = DATA / "applications"             # app-menu entries

STORE_TOPIC = "kettle-app"
REPO_PREFIX = "kettle-app-"
ACCENT = "#ffb347"
USER_AGENT = "KettleStore/1.0 (+https://github.com/thatluigiguyy/kettle-linux)"
MAX_DOWNLOAD = 20 * 1024 * 1024

DEFAULT_META = {
    "name": "My App",
    "icon": "\U0001FAD6",       # teapot emoji
    "description": "",
    "version": "1.0",
    "author": "",
    "width": 480,
    "height": 360,
}


def slugify(text):
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:40] or "my-app"


# ---------------------------------------------------------------- apps --

class KettleApp:
    def __init__(self, folder):
        self.folder = Path(folder)
        self.meta = {}
        self.reload_meta()

    @property
    def main(self):
        return self.folder / "main.qml"

    @property
    def meta_path(self):
        return self.folder / "kettle.json"

    @property
    def id(self):
        return slugify(self.meta.get("id") or self.folder.name)

    @property
    def name(self):
        return self.meta.get("name") or self.folder.name

    @property
    def icon(self):
        return self.meta.get("icon") or DEFAULT_META["icon"]

    def reload_meta(self):
        meta = dict(DEFAULT_META, name=self.folder.name)
        try:
            meta.update(json.loads(self.meta_path.read_text("utf-8")))
        except (OSError, ValueError):
            pass
        self.meta = meta

    def save_meta(self):
        self.meta_path.write_text(json.dumps(self.meta, indent=2, ensure_ascii=False) + "\n", "utf-8")

    def read_code(self):
        try:
            return self.main.read_text("utf-8")
        except OSError:
            return ""

    def write_code(self, text):
        self.main.write_text(text, "utf-8")

    @classmethod
    def create(cls, name, template_key="hello", parent=None):
        parent = Path(parent or PROJECTS_DIR)
        parent.mkdir(parents=True, exist_ok=True)
        folder = unique_folder(parent, slugify(name))
        folder.mkdir(parents=True)
        tpl = TEMPLATES.get(template_key) or TEMPLATES["hello"]
        app = cls(folder)
        app.write_code(tpl["qml"])
        app.meta = dict(DEFAULT_META, id=folder.name, name=name, icon=tpl["icon"],
                        description=tpl["description"], width=tpl.get("width", 480),
                        height=tpl.get("height", 360))
        app.save_meta()
        return app


def unique_folder(parent, base):
    folder, n = parent / base, 2
    while folder.exists():
        folder, n = parent / f"{base}-{n}", n + 1
    return folder


def list_projects():
    if not PROJECTS_DIR.is_dir():
        return []
    apps = [KettleApp(p) for p in PROJECTS_DIR.iterdir() if (p / "main.qml").is_file()]
    return sorted(apps, key=lambda a: a.name.lower())


def list_installed():
    if not INSTALLED_DIR.is_dir():
        return []
    apps = [KettleApp(p) for p in INSTALLED_DIR.iterdir() if (p / "main.qml").is_file()]
    return sorted(apps, key=lambda a: a.name.lower())


# ------------------------------------------------- running & app menu --

def run_app(folder):
    """Open an app in its own window."""
    return subprocess.Popen([sys.executable, str(HERE / "run.py"), str(folder)])


def launcher_path(key):
    return LAUNCHER_DIR / f"kettle-app-{slugify(key)}.desktop"


def _desktop_quote(value):
    for ch in ("\\", '"', "`", "$"):
        value = value.replace(ch, "\\" + ch)
    return f'"{value}"'


def _desktop_text(value):
    return str(value).replace("\n", " ").strip()


def install_launcher(app, key=None):
    """Put the app in the Kettle app menu."""
    LAUNCHER_DIR.mkdir(parents=True, exist_ok=True)
    path = launcher_path(key or app.id)
    path.write_text(
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={_desktop_text(app.name)}\n"
        f"Comment={_desktop_text(app.meta.get('description', ''))}\n"
        f"Exec=kettle-run {_desktop_quote(str(app.folder))}\n"
        "Icon=kettle-app\n"
        "Categories=Kettle;Utility;\n"
        "X-Kettle-App=true\n",
        "utf-8",
    )
    refresh_menu()
    return path


def remove_launcher(key):
    try:
        launcher_path(key).unlink()
    except OSError:
        pass
    refresh_menu()


def refresh_menu():
    tool = shutil.which("kbuildsycoca6")
    if tool:
        subprocess.Popen([tool], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def open_terminal(cmd):
    """Run a command in a terminal window the user can see and type into."""
    for term in (["konsole", "--hold", "-e"], ["x-terminal-emulator", "-e"]):
        if shutil.which(term[0]):
            subprocess.Popen(term + cmd)
            return True
    return False


# ------------------------------------------------------------- GitHub --

class StepFailed(Exception):
    pass


def _run(cmd, cwd=None, log=None, check=True, timeout=180):
    if log:
        log("$ " + " ".join(cmd))
    try:
        res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise StepFailed(f"{cmd[0]} could not run: {exc}") from exc
    out = (res.stdout + res.stderr).strip()
    if log and out:
        log(out)
    if check and res.returncode != 0:
        raise StepFailed(out or f"{cmd[0]} failed")
    return res


def gh_available():
    return shutil.which("gh") is not None and shutil.which("git") is not None


def gh_user():
    """The signed-in GitHub username, or None."""
    if not gh_available():
        return None
    try:
        res = _run(["gh", "api", "user", "--jq", ".login"], check=False, timeout=20)
    except StepFailed:
        return None
    login = res.stdout.strip()
    return login if res.returncode == 0 and login else None


def repo_name(app):
    return REPO_PREFIX + app.id


def write_readme(app, user):
    m = app.meta
    (app.folder / "README.md").write_text(
        f"# {app.icon} {app.name}\n\n"
        f"{m.get('description') or 'A Kettle app.'}\n\n"
        f"Version {m.get('version', '1.0')}"
        + (f" by {m['author']}" if m.get("author") else f" by @{user}") + "\n\n"
        "Made with **Kettle Studio** on "
        "[Kettle Linux](https://github.com/thatluigiguyy/kettle-linux). "
        "Install it from the **Kettle Store**.\n",
        "utf-8",
    )


def publish(app, user, log):
    """Upload the app to github.com/<user>/kettle-app-<id> and tag it for the Store."""
    folder, repo = str(app.folder), repo_name(app)
    if not app.meta.get("author"):
        app.meta["author"] = user
        app.save_meta()
    write_readme(app, user)

    log("Preparing your app...")
    if not (app.folder / ".git").exists():
        _run(["git", "init", "-b", "main"], folder, log)
    _run(["git", "config", "user.name", user], folder)
    _run(["git", "config", "user.email", f"{user}@users.noreply.github.com"], folder)
    _run(["gh", "auth", "setup-git"], folder, check=False)
    _run(["git", "add", "-A"], folder, log)
    if _run(["git", "status", "--porcelain"], folder).stdout.strip():
        version = app.meta.get("version", "1.0")
        _run(["git", "commit", "-m", f"{app.name} {version}"], folder, log)

    has_remote = _run(["git", "remote", "get-url", "origin"], folder, check=False).returncode == 0
    if not has_remote:
        log("Creating your GitHub project...")
        desc = (app.meta.get("description") or f"{app.name}, a Kettle app")[:300]
        _run(["gh", "repo", "create", repo, "--public", "--source", ".", "--remote", "origin",
              "--push", "--description", desc], folder, log)
    else:
        log("Uploading changes...")
        _run(["git", "push", "-u", "origin", "main"], folder, log)

    log("Adding it to the Kettle Store...")
    _run(["gh", "repo", "edit", f"{user}/{repo}", "--add-topic", STORE_TOPIC], folder, log)
    return f"https://github.com/{user}/{repo}"


# ------------------------------------------- Popular apps (Flathub) --

FLATHUB_REPO = "https://dl.flathub.org/repo/flathub.flatpakrepo"
GPU_NOTE = " Needs a real graphics card, so it won't run well inside a virtual machine."

# (Flathub id, name, emoji, description, section)
POPULAR = [
    ("com.valvesoftware.Steam", "Steam", "\U0001F3AE",
     "Thousands of games, like Counter-Strike 2, Geometry Dash and Among Us." + GPU_NOTE, "Games"),
    ("org.prismlauncher.PrismLauncher", "Minecraft (Prism Launcher)", "⛏️",
     "Play Minecraft: Java Edition with your Microsoft account." + GPU_NOTE, "Games"),
    ("com.heroicgameslauncher.hgl", "Heroic Games Launcher", "\U0001F6E1️",
     "Play your Epic Games and GOG games, including the free ones." + GPU_NOTE, "Games"),
    ("net.supertuxkart.SuperTuxKart", "SuperTuxKart", "\U0001F3CE️",
     "Free 3D kart racing with Tux and friends.", "Games"),
    ("com.discordapp.Discord", "Discord", "\U0001F4AC", "Chat and call with your friends.", "Chat, music & web"),
    ("com.spotify.Client", "Spotify", "\U0001F3B5", "Millions of songs and podcasts.", "Chat, music & web"),
    ("com.google.Chrome", "Google Chrome", "\U0001F310", "Google's web browser.", "Chat, music & web"),
    ("org.mozilla.Thunderbird", "Thunderbird", "✉️", "Email and calendar.", "Chat, music & web"),
    ("org.libreoffice.LibreOffice", "LibreOffice", "\U0001F4C4",
     "Documents, spreadsheets and slides. Opens Microsoft Office files.", "Work"),
    ("org.videolan.VLC", "VLC", "\U0001F3AC", "Plays almost any video or music file.", "Work"),
    ("com.visualstudio.code", "Visual Studio Code", "\U0001F4BB", "A powerful code editor.", "Create"),
    ("org.gimp.GIMP", "GIMP", "\U0001F5BC️", "Edit photos and pictures.", "Create"),
    ("org.kde.krita", "Krita", "\U0001F58C️", "Digital painting and drawing.", "Create"),
    ("com.obsproject.Studio", "OBS Studio", "\U0001F534", "Record and stream your screen.", "Create"),
    ("org.blender.Blender", "Blender", "\U0001F9CA", "3D modelling and animation.", "Create"),
]


def is_live_session():
    """True when Kettle is running from the ISO (nothing is kept after shutdown)."""
    try:
        return "boot=live" in Path("/proc/cmdline").read_text()
    except OSError:
        return False


def flatpak_available():
    return shutil.which("flatpak") is not None


def flatpak_installed():
    if not flatpak_available():
        return set()
    res = subprocess.run(["flatpak", "list", "--app", "--columns=application"],
                         capture_output=True, text=True)
    return set(res.stdout.split())


def flatpak_install(app_id, log):
    _run(["flatpak", "remote-add", "--user", "--if-not-exists", "flathub", FLATHUB_REPO], log=log)
    proc = subprocess.Popen(["flatpak", "install", "--user", "-y", "--noninteractive",
                             "flathub", app_id],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    last = ""
    for line in proc.stdout:          # flatpak updates its progress with \r, which splits lines
        line = line.strip()
        if line:
            last = line
            log(line)
    if proc.wait() != 0:
        raise StepFailed(last or "flatpak install failed")
    return app_id


def flatpak_uninstall(app_id, log=None):
    _run(["flatpak", "uninstall", "-y", "--noninteractive", app_id], log=log)
    return app_id


def flatpak_run(app_id):
    return subprocess.Popen(["flatpak", "run", app_id])


# -------------------------------------------------------------- Store --

def http_get(url, timeout=20, limit=MAX_DOWNLOAD):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                               "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read(limit + 1)
    if len(data) > limit:
        raise ValueError("download is too big")
    return data


def search_store():
    """Every public GitHub project tagged kettle-app."""
    url = ("https://api.github.com/search/repositories?q=topic:" + STORE_TOPIC
           + "&sort=updated&order=desc&per_page=60")
    items = json.loads(http_get(url)).get("items", [])
    return [{
        "owner": it["owner"]["login"],
        "repo": it["name"],
        "branch": it.get("default_branch") or "main",
        "description": it.get("description") or "",
        "stars": it.get("stargazers_count", 0),
        "url": it.get("html_url", ""),
        "updated": it.get("pushed_at", ""),
    } for it in items]


def fetch_meta(entry):
    url = (f"https://raw.githubusercontent.com/{entry['owner']}/{entry['repo']}/"
           f"{entry['branch']}/kettle.json")
    try:
        meta = json.loads(http_get(url, limit=64 * 1024))
        return meta if isinstance(meta, dict) else {}
    except Exception:
        return {}


def installed_key(entry):
    return f"{entry['owner']}--{entry['repo']}".lower()


def installed_folder(entry):
    return INSTALLED_DIR / installed_key(entry)


def download_app(entry):
    """Download a Store app, unpack it safely and add it to the app menu."""
    url = (f"https://codeload.github.com/{entry['owner']}/{entry['repo']}"
           f"/zip/refs/heads/{entry['branch']}")
    data = http_get(url, timeout=60)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        files = []
        for info in zf.infolist():
            parts = Path(info.filename).parts[1:]        # drop "repo-branch/"
            if not parts or info.is_dir():
                continue
            if any(p in ("..", "") or ":" in p for p in parts) or parts[0] == ".git":
                continue
            files.append((parts, info))
        if not any(parts == ("main.qml",) for parts, _ in files):
            raise ValueError("this project has no main.qml, so it isn't a Kettle app")
        if sum(info.file_size for _, info in files) > MAX_DOWNLOAD:
            raise ValueError("app is too big")

        dest = installed_folder(entry)
        tmp = dest.with_name(dest.name + ".part")
        shutil.rmtree(tmp, ignore_errors=True)
        tmp.mkdir(parents=True)
        try:
            for parts, info in files:
                target = tmp.joinpath(*parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(zf.read(info))
        except Exception:
            shutil.rmtree(tmp, ignore_errors=True)
            raise
    (tmp / ".kettle-source.json").write_text(json.dumps(entry, indent=2), "utf-8")
    shutil.rmtree(dest, ignore_errors=True)
    tmp.rename(dest)
    app = KettleApp(dest)
    install_launcher(app, installed_key(entry))
    return app


def uninstall_app(entry):
    shutil.rmtree(installed_folder(entry), ignore_errors=True)
    remove_launcher(installed_key(entry))


def source_of(app):
    try:
        return json.loads((app.folder / ".kettle-source.json").read_text("utf-8"))
    except (OSError, ValueError):
        return None


def remix(app):
    """Copy an app into 'Kettle Apps' so you can change it in Studio."""
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    folder = unique_folder(PROJECTS_DIR, slugify(app.name) + "-remix")
    shutil.copytree(app.folder, folder, ignore=shutil.ignore_patterns(".git", ".kettle-source.json"))
    copy = KettleApp(folder)
    original = app.meta.get("author") or ""
    copy.meta.update(id=folder.name, name=f"{app.name} Remix", author="",
                     description=(copy.meta.get("description") or "")
                     + (f" (remixed from {original})" if original else ""))
    copy.save_meta()
    return copy
