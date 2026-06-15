"""HTML inline per il launcher desktop.

`_setup_html(default_repo_url)` genera la finestra di setup first-run.
`_splash_html()` ritorna lo splash mostrato durante il boot di Streamlit.
Modulo standalone: nessun import da altri moduli del package.
"""
from __future__ import annotations


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


def _splash_html() -> str:
    return (
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
