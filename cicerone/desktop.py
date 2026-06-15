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

import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

APP_SUPPORT = Path.home() / "Library" / "Application Support" / "Cicerone"
KNOWLEDGE_TARGET = APP_SUPPORT / "knowledge" / "frameworks"
DEFAULT_REPO_URL = "https://github.com/FloshDev/cicerone-knowledge.git"


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
        APP_SUPPORT.mkdir(parents=True, exist_ok=True)
        db_path = APP_SUPPORT / "cicerone.sqlite"
    else:
        support = _base_path() / "cicerone" / "data"
        support.mkdir(parents=True, exist_ok=True)
        db_path = support / "cicerone.sqlite"
    os.environ["CICERONE_DB_PATH"] = str(db_path)
    return db_path


def _knowledge_presente(d: Path) -> bool:
    return d.is_dir() and any(d.glob("*.md"))


def _trova_frameworks_dir(root: Path) -> Path | None:
    """Cerca la sottocartella `frameworks/` (con .md) dentro `root`.

    Tollera due layout del repo knowledge:
      root/frameworks/*.md    (atteso)
      root/*.md               (md direttamente in root)
    """
    candidate = root / "frameworks"
    if _knowledge_presente(candidate):
        return candidate
    if _knowledge_presente(root):
        return root
    # Ricerca ricorsiva limitata: prima dir con .md dentro
    for sub in root.rglob("*"):
        if sub.is_dir() and any(sub.glob("*.md")):
            # Evita di matchare cartelle nascoste
            if not any(p.startswith(".") for p in sub.relative_to(root).parts):
                return sub
    return None


def _resolve_knowledge_dev() -> Path | None:
    """In dev, prova a riusare la knowledge nel repo se presente."""
    if getattr(sys, "frozen", False):
        return None
    candidate = _base_path() / "knowledge" / "frameworks"
    if _knowledge_presente(candidate):
        return candidate
    return None


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
# Setup knowledge base (first-run)
# ---------------------------------------------------------------------------


def _clone_repo_knowledge(token: str, repo_url: str) -> tuple[bool, str]:
    """Clona il repo privato usando il PAT come basic-auth.

    Strategia: rimpiazza `https://` con `https://<token>@` nell'URL. Funziona
    con GitHub PAT classic e fine-grained. Token NON viene salvato.
    """
    if not token.strip():
        return False, "Token vuoto."
    if not repo_url.strip().startswith("https://"):
        return False, "Repo URL deve iniziare con https://"

    auth_url = repo_url.strip().replace("https://", f"https://{token.strip()}@", 1)
    APP_SUPPORT.mkdir(parents=True, exist_ok=True)
    clone_dir = APP_SUPPORT / "knowledge_repo"
    if clone_dir.exists():
        shutil.rmtree(clone_dir)

    try:
        result = subprocess.run(
            ["git", "clone", "--depth", "1", auth_url, str(clone_dir)],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except FileNotFoundError:
        return False, "git non disponibile. Installa Xcode Command Line Tools."
    except subprocess.TimeoutExpired:
        return False, "Clone in timeout (120s). Controlla connessione."

    if result.returncode != 0:
        # Filtra il token da eventuali messaggi di errore prima di tornarli
        stderr_safe = result.stderr.replace(token.strip(), "***TOKEN***")
        return False, f"Clone fallito: {stderr_safe.strip()[:300]}"

    src = _trova_frameworks_dir(clone_dir)
    if src is None:
        return False, "Repo clonato ma nessun .md trovato."

    KNOWLEDGE_TARGET.parent.mkdir(parents=True, exist_ok=True)
    if KNOWLEDGE_TARGET.exists():
        shutil.rmtree(KNOWLEDGE_TARGET)
    shutil.copytree(src, KNOWLEDGE_TARGET)
    return True, f"Knowledge installata ({len(list(KNOWLEDGE_TARGET.glob('*.md')))} file)."


def _copia_da_cartella(source_path: str) -> tuple[bool, str]:
    src = Path(source_path).expanduser().resolve()
    if not src.is_dir():
        return False, "Cartella non valida."
    found = _trova_frameworks_dir(src)
    if found is None:
        return False, "Nessun file .md trovato nella cartella indicata."

    KNOWLEDGE_TARGET.parent.mkdir(parents=True, exist_ok=True)
    if KNOWLEDGE_TARGET.exists():
        shutil.rmtree(KNOWLEDGE_TARGET)
    shutil.copytree(found, KNOWLEDGE_TARGET)
    return True, f"Knowledge importata ({len(list(KNOWLEDGE_TARGET.glob('*.md')))} file)."


def _setup_html(default_repo_url: str) -> str:
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Cicerone — Setup</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;0,600;1,400&family=Inter:wght@400;500&display=swap');
*{{box-sizing:border-box}}
body{{margin:0;min-height:100vh;background:#fafaf7;color:#222;
  font-family:'Inter',-apple-system,sans-serif;display:flex;align-items:center;justify-content:center;padding:2rem}}
.card{{max-width:560px;width:100%;background:#fff;border:1px solid #e6e2d6;border-radius:8px;padding:2.2rem 2.4rem;
  box-shadow:0 6px 24px rgba(40,30,10,.06)}}
h1{{font-family:'Cormorant Garamond',serif;font-size:2.2rem;font-weight:600;margin:0 0 .15rem;
  border-bottom:2px solid #E8B84B;display:inline-block;padding-bottom:.1rem}}
.sub{{color:#7A7A7A;font-style:italic;margin:.4rem 0 1.6rem;font-family:'Cormorant Garamond',serif;font-size:1.05rem}}
.tabs{{display:flex;gap:.4rem;margin-bottom:1.2rem;border-bottom:1px solid #e6e2d6}}
.tab{{padding:.6rem 1rem;cursor:pointer;font-size:.9rem;color:#7A7A7A;border-bottom:2px solid transparent;margin-bottom:-1px}}
.tab.active{{color:#222;border-bottom-color:#E8B84B}}
.panel{{display:none}}
.panel.active{{display:block}}
label{{display:block;font-size:.82rem;color:#555;margin:.9rem 0 .25rem}}
input[type=text],input[type=password]{{width:100%;padding:.55rem .7rem;border:1px solid #d6d2c4;border-radius:4px;
  font-size:.92rem;font-family:inherit;background:#fff}}
input:focus{{outline:none;border-color:#E8B84B;box-shadow:0 0 0 2px rgba(232,184,75,.18)}}
button{{background:#E8B84B;border:none;color:#fff;padding:.65rem 1.4rem;border-radius:4px;font-size:.92rem;
  font-weight:500;cursor:pointer;margin-top:1.2rem;font-family:inherit}}
button:hover{{background:#d4a73e}}
button:disabled{{background:#c9c3b1;cursor:not-allowed}}
button.secondary{{background:transparent;color:#555;border:1px solid #d6d2c4}}
button.secondary:hover{{background:#f4efe3;color:#222}}
.hint{{font-size:.78rem;color:#7A7A7A;margin-top:.4rem;line-height:1.45}}
.status{{margin-top:1rem;padding:.6rem .8rem;border-radius:4px;font-size:.85rem;display:none}}
.status.err{{display:block;background:#fde9e6;color:#a4392a;border:1px solid #f1c5be}}
.status.ok{{display:block;background:#e7f5ec;color:#1f6a3a;border:1px solid #c2e2cf}}
.status.info{{display:block;background:#f4efe3;color:#5a4a1f;border:1px solid #e6dcc4}}
.row{{display:flex;gap:.6rem;align-items:center}}
.row input{{flex:1}}
</style></head><body>
<div class="card">
  <h1>Cicerone</h1>
  <div class="sub">Configurazione knowledge base — primo avvio</div>
  <div class="tabs">
    <div class="tab active" data-tab="repo" onclick="switchTab('repo')">Repo privato GitHub</div>
    <div class="tab" data-tab="folder" onclick="switchTab('folder')">Cartella locale</div>
  </div>
  <div class="panel active" id="panel-repo">
    <label>Personal Access Token (scope: repo:read)</label>
    <input type="password" id="token" placeholder="ghp_…"/>
    <label>URL repository</label>
    <input type="text" id="repo" value="{default_repo_url}"/>
    <div class="hint">Il token NON viene salvato. Serve solo a scaricare i file .md una volta. La knowledge resta in <code>~/Library/Application Support/Cicerone/knowledge/</code>.</div>
    <button id="btn-clone" onclick="doClone()">Scarica knowledge</button>
  </div>
  <div class="panel" id="panel-folder">
    <label>Percorso cartella con i file .md (o cartella padre)</label>
    <div class="row">
      <input type="text" id="folderpath" placeholder="/Users/.../cicerone-knowledge/frameworks"/>
      <button class="secondary" onclick="pickFolder()">Sfoglia…</button>
    </div>
    <div class="hint">Indica la cartella che contiene i .md dei framework, oppure la cartella padre. Cicerone copia i file nella user data dir.</div>
    <button id="btn-folder" onclick="doFolder()">Importa</button>
  </div>
  <div class="status" id="status"></div>
</div>
<script>
function switchTab(name){{
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab===name));
  document.querySelectorAll('.panel').forEach(p => p.classList.toggle('active', p.id==='panel-'+name));
  setStatus('', '');
}}
function setStatus(msg, kind){{
  const s = document.getElementById('status');
  s.className = 'status' + (kind ? ' '+kind : '');
  s.textContent = msg;
}}
function lockUI(locked){{
  document.getElementById('btn-clone').disabled = locked;
  document.getElementById('btn-folder').disabled = locked;
}}
async function doClone(){{
  const token = document.getElementById('token').value;
  const repo = document.getElementById('repo').value;
  if(!token){{ setStatus('Inserisci un Personal Access Token.', 'err'); return; }}
  lockUI(true); setStatus('Clonazione in corso…', 'info');
  const res = await window.pywebview.api.clone_repo(token, repo);
  lockUI(false);
  if(res.ok){{ setStatus(res.msg, 'ok'); setTimeout(() => window.pywebview.api.finalize(), 700); }}
  else setStatus(res.msg, 'err');
}}
async function pickFolder(){{
  const path = await window.pywebview.api.pick_folder();
  if(path) document.getElementById('folderpath').value = path;
}}
async function doFolder(){{
  const path = document.getElementById('folderpath').value;
  if(!path){{ setStatus('Indica una cartella.', 'err'); return; }}
  lockUI(true); setStatus('Copia in corso…', 'info');
  const res = await window.pywebview.api.import_folder(path);
  lockUI(false);
  if(res.ok){{ setStatus(res.msg, 'ok'); setTimeout(() => window.pywebview.api.finalize(), 700); }}
  else setStatus(res.msg, 'err');
}}
</script>
</body></html>
"""


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

    splash_html = (
        "<html><head><style>"
        "@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;1,400&display=swap');"
        "body{margin:0;height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;"
        "font-family:'Cormorant Garamond',Garamond,serif;background:#fafaf7;color:#222}"
        ".wm{font-size:3.2rem;font-weight:600;border-bottom:2px solid #E8B84B;padding-bottom:.15rem}"
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
        try:
            window.load_html(splash_html)
        except Exception:
            pass
        # Polling streamlit health
        if _attendi_streamlit(porta, timeout=40):
            try:
                window.load_url(f"http://127.0.0.1:{porta}")
            except Exception:
                pass
        else:
            try:
                window.load_html(
                    "<div style='font-family:sans-serif;padding:2rem'>"
                    "<h2>Cicerone non si è avviato in tempo.</h2>"
                    "<p>Chiudi la finestra e riprova.</p></div>"
                )
            except Exception:
                pass

    threading.Thread(target=_orchestratore, daemon=True).start()

    webview.start()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
