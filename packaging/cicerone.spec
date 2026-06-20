# PyInstaller spec — bundle macOS .app per Cicerone
#
# Eseguibile in dist/Cicerone.app. One-folder (NON onefile) per startup veloce
# e per non rompere il caricamento dei moduli Streamlit.
#
# Build:
#   uv run pyinstaller packaging/cicerone.spec --clean --noconfirm

from pathlib import Path

from PyInstaller.utils.hooks import (
    collect_all,
    collect_data_files,
    collect_submodules,
    copy_metadata,
)

# Project root: lo .spec è in packaging/, root è una su.
ROOT = Path(SPECPATH).resolve().parent  # type: ignore[name-defined]


# ----------------------------------------------------------------------------
# Datas: file non-Python da trasportare nel bundle.
# Formato: (sorgente_assoluta_o_relativa_a_cwd, destinazione_relativa_nel_bundle)
# ----------------------------------------------------------------------------
datas = [
    (str(ROOT / "cicerone" / "db" / "schema.sql"), "cicerone/db"),
    (str(ROOT / "cicerone" / "ui" / "style.css"), "cicerone/ui"),
    (str(ROOT / "cicerone" / "ui" / "app.py"), "cicerone/ui"),
    (str(ROOT / "resources" / "MatriceDB.xlsx"), "resources"),
    (str(ROOT / "resources" / "Criteri_Readiness_Maturity.md"), "resources"),
    (str(ROOT / "resources" / "branding" / "logo.png"), "resources/branding"),
    (str(ROOT / ".streamlit" / "config.toml"), ".streamlit"),
]

# Knowledge base: NON bundlata. Il launcher mostra setup first-run che
# clona il repo privato cicerone-knowledge o copia da cartella locale.
# Override path runtime via CICERONE_KNOWLEDGE_DIR (settato da desktop.py).

# Asset statici di Streamlit (frontend React, CSS, file di config).
datas += collect_data_files("streamlit")
# Certificati SSL (litellm via httpx).
datas += collect_data_files("certifi")

# Package metadata: streamlit usa `importlib.metadata.version("streamlit")`
# all'import. Senza i .dist-info corrispondenti dentro il bundle, l'import
# crasha con PackageNotFoundError. copy_metadata trasporta i .dist-info.
datas += copy_metadata("streamlit")
datas += copy_metadata("httpx")
datas += copy_metadata("openpyxl")
datas += copy_metadata("python-dotenv")

# litellm + dipendenze pesanti (tiktoken/openai/tokenizers): hanno data file
# (es. model_prices, encodings) e molti import lazy. collect_all prende
# datas+binaries+hiddenimports in un colpo. litellm legge anche la propria
# versione via importlib.metadata → serve copy_metadata.
binaries = []
collected_hidden = []
for _pkg in ("litellm", "tiktoken", "tiktoken_ext", "openai", "tokenizers"):
    try:
        _d, _b, _h = collect_all(_pkg)
        datas += _d
        binaries += _b
        collected_hidden += _h
    except Exception:
        pass
for _meta in ("litellm", "openai", "tiktoken"):
    try:
        datas += copy_metadata(_meta)
    except Exception:
        pass


# ----------------------------------------------------------------------------
# Hidden imports: moduli importati dinamicamente che PyInstaller non rileva
# da static analysis. Streamlit e anthropic ne hanno parecchi.
# ----------------------------------------------------------------------------
hiddenimports = []
# Tutto il package cicerone: app.py è trasportata come data file (per
# `streamlit run`), quindi i suoi import (cicerone.db.seed, .mcda, .llm…)
# non vengono rilevati dall'analisi statica di PyInstaller. Forziamo.
hiddenimports += collect_submodules("cicerone")

# Belt-and-suspenders: in alcuni env (cicerone non installato come
# pacchetto), collect_submodules può tornare incompleto. Enumeriamo
# manualmente i moduli dal filesystem.
def _walk_cicerone_modules():
    out = []
    pkg_root = ROOT / "cicerone"
    for py in pkg_root.rglob("*.py"):
        if "__pycache__" in py.parts:
            continue
        rel = py.relative_to(ROOT).with_suffix("")
        parts = list(rel.parts)
        if parts[-1] == "__init__":
            parts.pop()
        if parts:
            out.append(".".join(parts))
    return out

hiddenimports += _walk_cicerone_modules()
hiddenimports += collect_submodules("streamlit")
hiddenimports += collect_submodules("httpx")
hiddenimports += collect_submodules("httpcore")
hiddenimports += collect_submodules("h11")
# litellm + deps (raccolti sopra con collect_all)
hiddenimports += collected_hidden
hiddenimports += [
    "openpyxl",
    "dotenv",
    "certifi",
]


block_cipher = None


a = Analysis(
    [str(ROOT / "cicerone" / "desktop" / "launcher.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "PyQt5",
        "PyQt6",
        "PySide2",
        "PySide6",
        "matplotlib",
        "numpy.f2py",
        # Slim: l'app non usa dataframe/tabelle/chart/mappe Streamlit.
        # pyarrow (~121M), pydeck (~23M), altair (~5.7M) sono importati
        # da Streamlit solo lazy per quelle feature → esclusi. Streamlit
        # degrada con messaggio se servissero, ma qui non vengono mai usati.
        "pyarrow",
        "pydeck",
        "altair",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="cicerone",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="cicerone",
)

app = BUNDLE(
    coll,
    name="Cicerone.app",
    icon=str(ROOT / "packaging" / "icon.icns"),
    bundle_identifier="com.cicerone.desktop",
    info_plist={
        "CFBundleName": "Cicerone",
        "CFBundleDisplayName": "Cicerone",
        "CFBundleShortVersionString": "0.2.1",
        "CFBundleVersion": "0.2.1",
        "LSUIElement": False,
        "NSHighResolutionCapable": True,
        "NSHumanReadableCopyright": "© 2026 Cicerone",
        "NSPrincipalClass": "NSApplication",
    },
)
