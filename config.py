"""
Central configuration for CudaStudy Video Studio.

Key points:
- Works both in a dev checkout and in a PyInstaller frozen bundle.
- Loads a project-local ``.env`` file (no third-party dependency required).
- Exposes one API-key entry point so the GUI, CLI, detectors and generators
  all agree on which key is in use.
- Defines the single video geometry used by every layer: 1280x720 output with a
  dedicated 88px subtitle band, so burned-in subtitles never cover the picture.
"""

import os
import sys
from pathlib import Path


# --------------------------------------------------------------------------
# Paths (dev checkout + frozen exe)
# --------------------------------------------------------------------------
def _resolve_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        # Historical layout: <project>/dist/CudaVideoStudio.exe
        if exe_dir.name.lower() == "dist":
            return exe_dir.parent
        return exe_dir
    return Path(__file__).resolve().parent


BASE_DIR = _resolve_base_dir()


def _load_dotenv(path: Path) -> None:
    """Minimal .env loader. Existing environment variables always win."""
    if not path.exists():
        return
    try:
        for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
    except OSError:
        pass


_load_dotenv(BASE_DIR / ".env")

DOC_DIR = BASE_DIR / "doc"
ASSETS_DIR = BASE_DIR / "assets"
PIPELINE_DIR = BASE_DIR / "pipeline"
OUTPUT_DIR = BASE_DIR / "output"

# Ensure runtime directories exist (best-effort: a read-only install must not crash)
for _sub in ("", "chunks", "beats", "audio", "manim_scenes", "videos", "decks", "deep_decks", "slide_images", "curriculum"):
    try:
        (OUTPUT_DIR / _sub).mkdir(parents=True, exist_ok=True)
    except OSError:
        pass


# --------------------------------------------------------------------------
# DeepSeek API
# --------------------------------------------------------------------------
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1").rstrip("/")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_TIMEOUT = int(os.environ.get("DEEPSEEK_TIMEOUT", "120"))
DEEPSEEK_MAX_TOKENS = int(os.environ.get("DEEPSEEK_MAX_TOKENS", "8192"))


def set_api_key(key: str) -> None:
    """Single entry point used by the GUI/CLI to activate a key for this process."""
    global DEEPSEEK_API_KEY
    key = (key or "").strip()
    DEEPSEEK_API_KEY = key
    if key:
        os.environ["DEEPSEEK_API_KEY"] = key
    else:
        os.environ.pop("DEEPSEEK_API_KEY", None)


def save_api_key(key: str) -> Path:
    """
    Persist the key to ``<project>/.env`` so the GUI fills it next launch.

    Existing comments/settings are preserved; only DEEPSEEK_API_KEY is replaced.
    ``.env`` is already ignored by git.
    """
    key = (key or "").strip()
    if not key:
        raise ValueError("API key is empty")

    env_path = Path(BASE_DIR) / ".env"
    lines = []
    if env_path.exists():
        try:
            lines = env_path.read_text(encoding="utf-8-sig").splitlines()
        except OSError:
            lines = []

    replaced = False
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#") or "=" not in stripped:
            continue
        name = stripped.split("=", 1)[0].strip()
        if name == "DEEPSEEK_API_KEY":
            lines[index] = f"DEEPSEEK_API_KEY={key}"
            replaced = True
            break
    if not replaced:
        if lines and lines[-1].strip():
            lines.append("")
        lines.append(f"DEEPSEEK_API_KEY={key}")

    env_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = env_path.with_name(".env.tmp")
    temporary.write_text("\n".join(lines) + "\n", encoding="utf-8")
    temporary.replace(env_path)

    set_api_key(key)
    return env_path


def clear_api_key() -> Path:
    """Remove the saved key from .env, preserving all other settings."""
    env_path = Path(BASE_DIR) / ".env"
    if env_path.exists():
        lines = []
        try:
            lines = env_path.read_text(encoding="utf-8-sig").splitlines()
        except OSError:
            lines = []
        kept = []
        for line in lines:
            stripped = line.strip()
            if not stripped.startswith("#") and "=" in stripped:
                name = stripped.split("=", 1)[0].strip()
                if name == "DEEPSEEK_API_KEY":
                    continue
            kept.append(line)
        temporary = env_path.with_name(".env.tmp")
        temporary.write_text("\n".join(kept).rstrip() + "\n", encoding="utf-8")
        temporary.replace(env_path)
    set_api_key("")
    return env_path


def api_key() -> str:
    """Always read from the live environment so a GUI-entered key takes effect."""
    return (os.environ.get("DEEPSEEK_API_KEY") or DEEPSEEK_API_KEY or "").strip()


def has_api_key() -> bool:
    return bool(api_key())


# --------------------------------------------------------------------------
# Video geometry: 1280x720 total = 1280x632 content + 88px subtitle band
# --------------------------------------------------------------------------
VIDEO_WIDTH = 1280
VIDEO_HEIGHT = 720
SUBTITLE_BAND_HEIGHT = 88
CONTENT_WIDTH = VIDEO_WIDTH
CONTENT_HEIGHT = VIDEO_HEIGHT - SUBTITLE_BAND_HEIGHT  # 632
VIDEO_FPS = 30

# Manim renders directly at the content size (no scaling artefacts).
MANIM_RESOLUTION = f"{CONTENT_WIDTH},{CONTENT_HEIGHT}"
MANIM_FRAME_RATE = str(VIDEO_FPS)

# Legacy quality flag kept for the old template renderer.
MANIM_QUALITY = os.environ.get("MANIM_QUALITY", "-qm")

# TTS
TTS_VOICE = os.environ.get("TTS_VOICE", "zh-CN-YunxiNeural")
TTS_RATE = os.environ.get("TTS_RATE", "-8%")
TTS_VOLUME = os.environ.get("TTS_VOLUME", "+0%")

# Timing
DEFAULT_PAUSE_BUFFER = float(os.environ.get("PAUSE_BUFFER", "2.2"))
MIN_ACTION_DURATION = 2.0
MAX_SLIDES_PER_SECTION = int(os.environ.get("MAX_SLIDES_PER_SECTION", "10"))

# Execution
DEFAULT_RESUME_MODE = True
FORCE_REGENERATE = False

# Default CUDA document
DEFAULT_PDF_PATH = BASE_DIR / "cuda-programming-guide.pdf"

# Bump when deck/scene schemas change so on-disk caches are invalidated.
SCHEMA_VERSION = "2026.11-pedagogy-v1"

# Bump when subtitle layout/segmentation changes, so already-rendered videos get
# re-composited (clips are reused; only SRT + burn are redone).
SUBTITLE_VERSION = "single-line-v4"


# --------------------------------------------------------------------------
# FFmpeg auto-discovery
# --------------------------------------------------------------------------
def ffmpeg_binary() -> Path:
    """Return a usable ffmpeg path (venv -> imageio-ffmpeg -> PATH)."""
    import shutil

    found = shutil.which("ffmpeg")
    if found:
        return Path(found)

    candidates = [
        BASE_DIR / ".venv" / "Scripts" / "ffmpeg.exe",
        Path(sys.executable).resolve().parent / "ffmpeg.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate

    try:
        import imageio_ffmpeg

        return Path(imageio_ffmpeg.get_ffmpeg_exe())
    except Exception:
        return Path("ffmpeg")


def setup_ffmpeg_path() -> None:
    binary = ffmpeg_binary()
    if binary.name.lower() in ("ffmpeg", "ffmpeg.exe") and not binary.exists():
        return
    parent = str(binary.parent)
    if parent and parent not in os.environ.get("PATH", ""):
        os.environ["PATH"] = parent + os.pathsep + os.environ.get("PATH", "")


setup_ffmpeg_path()
