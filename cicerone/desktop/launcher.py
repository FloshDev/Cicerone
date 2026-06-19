"""Launcher desktop per Cicerone.

Avvia Streamlit IN-PROCESS (non subprocess) in un thread daemon, attende
che il server risponda al health endpoint, apre una finestra pywebview che
punta all'URL e chiude tutto alla chiusura della finestra.

Al primo avvio, se la knowledge base privata non è presente nella user
data dir, mostra una finestra di setup (HTML inline) che permette di:
  A) clonare il repo privato `cicerone-knowledge` via Personal Access Token
  B) puntare a una cartella locale esistente con i `.md` dei framework

Perché in-process e non subprocess:
- In un bundle PyInstaller `sys.executable` punta al launcher bundlato; un
  `sys.executable -m streamlit run` farebbe ri-eseguire il main del bundle
  (fork bomb). `streamlit.web.bootstrap.run` parte direttamente nello
  stesso interprete e funziona sia in dev sia in bundle.

Funziona sia in dev (`uv run python -m cicerone.desktop`) sia dentro un
bundle PyInstaller (legge `sys._MEIPASS` per i path).
"""
from __future__ import annotations

import contextlib
import os
import socket
import threading
import time
import urllib.error
import urllib.request

from cicerone.desktop._html import _setup_html, _splash_html
from cicerone.desktop.paths import (
    DEFAULT_REPO_URL,
    KNOWLEDGE_TARGET,
    _base_path,
    _setup_db_path,
)
from cicerone.desktop.setup_knowledge import (
    _clone_repo_knowledge,
    _copia_da_cartella,
    _knowledge_presente,
    _resolve_knowledge_dev,
)


def _porta_libera() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _attendi_streamlit(porta: int, timeout: float = 30.0) -> bool:
    url = f"http://127.0.0.1:{porta}/_stcore/health"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            pass
        time.sleep(0.3)
    return False


def _avvia_streamlit_in_thread(porta: int) -> threading.Thread:
    """Avvia il server Streamlit in un thread daemon nello stesso processo."""
    app_path = _base_path() / "cicerone" / "ui" / "app.py"
    if not app_path.exists():
        raise FileNotFoundError(f"app.py non trovato: {app_path}")

    flag_options: dict = {
        "server_port": porta,
        "server_address": "127.0.0.1",
        "server_headless": True,
        "browser_gatherUsageStats": False,
        "server_fileWatcherType": "none",
        "global_developmentMode": False,
        # Tema light forzato: nel bundle il .streamlit/config.toml può non essere
        # raccolto e in dark mode del SO la finestra diventava nera/illeggibile.
        # Passando il tema qui è sempre il "classico" chiaro.
        "theme_base": "light",
        "theme_primaryColor": "#E8B84B",
        "theme_backgroundColor": "#FAFAF7",
        "theme_secondaryBackgroundColor": "#F2EFE8",
        "theme_textColor": "#1F2329",
    }

    def _run() -> None:
        import signal as _sig

        _sig.signal = lambda *a, **kw: None  # type: ignore[assignment]
        from streamlit.web import bootstrap

        bootstrap.load_config_options(flag_options=flag_options)
        bootstrap.run(str(app_path), False, [], flag_options)

    t = threading.Thread(target=_run, daemon=True, name="streamlit-bootstrap")
    t.start()
    return t


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    import webview

    _setup_db_path()

    # Risoluzione knowledge: 1) env var già impostata, 2) user data dir,
    # 3) dev fallback su repo locale, 4) setup interattivo
    if not os.environ.get("CICERONE_KNOWLEDGE_DIR"):
        if _knowledge_presente(KNOWLEDGE_TARGET):
            os.environ["CICERONE_KNOWLEDGE_DIR"] = str(KNOWLEDGE_TARGET)
        else:
            dev_knowledge = _resolve_knowledge_dev()
            if dev_knowledge is not None:
                os.environ["CICERONE_KNOWLEDGE_DIR"] = str(dev_knowledge)

    needs_setup = not os.environ.get("CICERONE_KNOWLEDGE_DIR")

    porta = _porta_libera()
    pronto = {"streamlit": False, "started": False}

    def _start_streamlit_once() -> None:
        if pronto["started"]:
            return
        pronto["started"] = True
        _avvia_streamlit_in_thread(porta)

    if not needs_setup:
        _start_streamlit_once()

    setup_finalized = threading.Event()
    if not needs_setup:
        setup_finalized.set()

    class _Api:
        def clone_repo(self, token: str, repo_url: str) -> dict:
            ok, msg = _clone_repo_knowledge(token, repo_url)
            if ok:
                os.environ["CICERONE_KNOWLEDGE_DIR"] = str(KNOWLEDGE_TARGET)
            return {"ok": ok, "msg": msg}

        def import_folder(self, path: str) -> dict:
            ok, msg = _copia_da_cartella(path)
            if ok:
                os.environ["CICERONE_KNOWLEDGE_DIR"] = str(KNOWLEDGE_TARGET)
            return {"ok": ok, "msg": msg}

        def pick_folder(self) -> str | None:
            res = window.create_file_dialog(webview.FOLDER_DIALOG)
            if not res:
                return None
            return res[0] if isinstance(res, (list, tuple)) else res

        def finalize(self) -> None:
            _start_streamlit_once()
            setup_finalized.set()

    splash_html = _splash_html()

    initial_html = _setup_html(DEFAULT_REPO_URL) if needs_setup else splash_html
    window = webview.create_window(
        "Cicerone",
        html=initial_html,
        width=1200,
        height=800,
        min_size=(900, 600),
        js_api=_Api() if needs_setup else None,
    )

    def _orchestratore() -> None:
        # Attende che il setup (se necessario) sia finalizzato
        setup_finalized.wait()
        # Mostra splash mentre streamlit boota
        with contextlib.suppress(Exception):
            window.load_html(splash_html)
        # Polling streamlit health
        if _attendi_streamlit(porta, timeout=40):
            with contextlib.suppress(Exception):
                window.load_url(f"http://127.0.0.1:{porta}")
        else:
            with contextlib.suppress(Exception):
                window.load_html(
                    "<div style='font-family:sans-serif;padding:2rem'>"
                    "<h2>Cicerone non si è avviato in tempo.</h2>"
                    "<p>Chiudi la finestra e riprova.</p></div>"
                )

    threading.Thread(target=_orchestratore, daemon=True).start()

    webview.start()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
