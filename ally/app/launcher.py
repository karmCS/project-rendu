"""Rendu Ally launcher.

Starts the FastAPI backend on localhost:8000, opens the browser, and keeps
running in the background. Designed to be packaged into Rendu.exe via
PyInstaller for one-tap startup on Windows.

Data layout:
- Read-only bundle (inside the exe): static frontend + default settings.json
- Writable user data (%LOCALAPPDATA%\\Rendu): database.db + storage/ + settings.json
"""

import os
import shutil
import sys
import threading
import time
import webbrowser
from pathlib import Path

PORT = 8000
APP_NAME = "Rendu"


def _bundle_dir() -> Path:
    """Return the directory containing read-only bundled resources."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent


def _data_dir() -> Path:
    """Return the writable per-user data directory."""
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    path = Path(base) / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def _ensure_user_files(bundle: Path, data: Path) -> None:
    (data / "storage" / "audio").mkdir(parents=True, exist_ok=True)
    (data / "storage" / "transcripts").mkdir(parents=True, exist_ok=True)

    user_settings = data / "settings.json"
    if not user_settings.exists():
        bundled = bundle / "settings.json"
        if bundled.exists():
            shutil.copy(bundled, user_settings)


def _open_browser_when_ready() -> None:
    import urllib.request
    import urllib.error

    url = f"http://localhost:{PORT}"
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{url}/health", timeout=1) as resp:
                if resp.status == 200:
                    webbrowser.open(url)
                    return
        except (urllib.error.URLError, ConnectionError, OSError):
            time.sleep(0.5)
    webbrowser.open(url)


def main() -> None:
    bundle = _bundle_dir()
    data = _data_dir()
    _ensure_user_files(bundle, data)

    os.environ["RENDU_STATIC_DIR"] = str(bundle / "static")
    os.chdir(data)

    sys.path.insert(0, str(bundle))

    threading.Thread(target=_open_browser_when_ready, daemon=True).start()

    try:
        # Stub stdout/stderr — noconsole exe has neither, and uvicorn's
        # default logging calls sys.stdout.isatty() which would crash.
        if sys.stdout is None:
            sys.stdout = open(os.devnull, "w")
        if sys.stderr is None:
            sys.stderr = open(os.devnull, "w")

        import uvicorn
        from main import app
        uvicorn.run(app, host="127.0.0.1", port=PORT, log_config=None)
    except BaseException as exc:
        import traceback
        log = data / "launcher_error.log"
        log.write_text(
            f"FATAL: {exc!r}\n\n{traceback.format_exc()}",
            encoding="utf-8",
        )
        raise


if __name__ == "__main__":
    main()
