"""Launcher desktop per Cicerone.

Avvia Streamlit IN-PROCESS (non subprocess) in un thread daemon, attende
che il server risponda al health endpoint, apre una finestra pywebview che
punta all'URL e chiude tutto alla chiusura della finestra.

Perché in-process e non subprocess:
- In un bundle PyInstaller `sys.executable` punta al launcher bundlato; un
  `sys.executable -m streamlit run` farebbe ri-eseguire il main del bundle
  (fork bomb). `streamlit.web.bootstrap.run` parte direttamente nello
  stesso interprete e funziona sia in dev sia in bundle.

Funziona sia in dev (`uv run python -m cicerone.desktop`) sia dentro un
bundle PyInstaller (legge `sys._MEIPASS` per i path).
"""
from __future__ import annotations

import os
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path


def _porta_libera() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _base_path() -> Path:
    """Radice da cui risolvere i file dati.

    In bundle PyInstaller `sys._MEIPASS` punta alla cartella con tutti i
    dati raccolti dallo spec. In dev usa la root del repo.
    """
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent


def _setup_db_path() -> Path:
    """Forza la DB su una location scrivibile.

    In bundle l'app è read-only: serve una directory utente. In dev
    rispetta il default di `cicerone.db.connection` (data/ nel repo).
    """
    if getattr(sys, "frozen", False):
        support = Path.home() / "Library" / "Application Support" / "Cicerone"
    else:
        support = _base_path() / "cicerone" / "data"
    support.mkdir(parents=True, exist_ok=True)
    db_path = support / "cicerone.sqlite"
    os.environ["CICERONE_DB_PATH"] = str(db_path)
    return db_path


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

    # Chiavi CLI-style (`_`, non `.`): bootstrap.load_config_options le
    # converte in dotted internamente.
    flag_options: dict = {
        "server_port": porta,
        "server_address": "127.0.0.1",
        "server_headless": True,
        "browser_gatherUsageStats": False,
        "server_fileWatcherType": "none",
        "global_developmentMode": False,
    }

    def _run() -> None:
        # streamlit.bootstrap registra signal handler (SIGTERM/SIGINT) e
        # signal.signal funziona solo nel main thread. Qui siamo in un
        # daemon thread: neutralizziamo signal.signal a no-op così
        # bootstrap.run non crasha. Effetto collaterale: streamlit non
        # gestisce shutdown via signal, ma il thread è daemon — termina
        # quando il processo principale (pywebview) esce.
        import signal as _sig

        _sig.signal = lambda *a, **kw: None  # type: ignore[assignment]
        from streamlit.web import bootstrap

        # Applica le option PRIMA del run (altrimenti partono i default).
        bootstrap.load_config_options(flag_options=flag_options)
        # Firma stabile recente: (main_script_path, is_hello, args, flag_options)
        bootstrap.run(str(app_path), False, [], flag_options)

    t = threading.Thread(target=_run, daemon=True, name="streamlit-bootstrap")
    t.start()
    return t


def main() -> int:
    import webview

    _setup_db_path()
    porta = _porta_libera()
    _avvia_streamlit_in_thread(porta)

    pronto = {"ok": False}

    def _check_ready() -> None:
        pronto["ok"] = _attendi_streamlit(porta, timeout=40)

    threading.Thread(target=_check_ready, daemon=True).start()

    url = f"http://127.0.0.1:{porta}"
    splash = (
        "<html><head><style>"
        "@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;1,400&display=swap');"
        "body{margin:0;height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;"
        "font-family:'Cormorant Garamond',Garamond,serif;background:#fff;color:#222}"
        ".wm{font-size:3.2rem;border-bottom:2px solid #E8B84B;padding-bottom:.15rem}"
        ".tl{font-style:italic;color:#7A7A7A;margin-top:.8rem;font-size:1.1rem}"
        ".ld{margin-top:2rem;width:42px;height:42px;border:3px solid rgba(232,184,75,.22);"
        "border-top-color:#E8B84B;border-radius:50%;animation:s .9s linear infinite}"
        "@keyframes s{to{transform:rotate(360deg)}}"
        "</style></head><body>"
        "<div class='wm'>Cicerone</div>"
        "<div class='tl'>Avvio in corso&hellip;</div>"
        "<div class='ld'></div>"
        "</body></html>"
    )
    window = webview.create_window(
        "Cicerone",
        html=splash,
        width=1200,
        height=800,
        min_size=(900, 600),
    )

    def _on_loaded() -> None:
        # Polling in background fino a server pronto, poi naviga all'URL vero.
        for _ in range(120):
            if pronto["ok"]:
                window.load_url(url)
                return
            time.sleep(0.3)
        window.load_html(
            "<div style='font-family:sans-serif;padding:2rem'>"
            "<h2>Cicerone non si è avviato in tempo.</h2>"
            "<p>Chiudi la finestra e riprova.</p></div>"
        )

    threading.Thread(target=_on_loaded, daemon=True).start()

    # webview.start() blocca finché la finestra non si chiude. Il thread
    # streamlit è daemon, quindi termina con il processo principale.
    webview.start()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
