import os
import sys
from pathlib import Path

# Base Paths (Supports both dev environment and packaged PyInstaller .exe)
if getattr(sys, 'frozen', False):
    exe_dir = Path(sys.executable).resolve().parent
    # If running from inside 'dist' directory, project root is the parent folder
    if exe_dir.name.lower() == "dist":
        BASE_DIR = exe_dir.parent
    else:
        BASE_DIR = exe_dir
else:
    BASE_DIR = Path(__file__).resolve().parent
DOC_DIR = BASE_DIR / "doc"
ASSETS_DIR = BASE_DIR / "assets"
PIPELINE_DIR = BASE_DIR / "pipeline"
OUTPUT_DIR = BASE_DIR / "output"

# Ensure runtime directories exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
(OUTPUT_DIR / "chunks").mkdir(parents=True, exist_ok=True)
(OUTPUT_DIR / "beats").mkdir(parents=True, exist_ok=True)
(OUTPUT_DIR / "audio").mkdir(parents=True, exist_ok=True)
(OUTPUT_DIR / "manim_scenes").mkdir(parents=True, exist_ok=True)
(OUTPUT_DIR / "videos").mkdir(parents=True, exist_ok=True)

# DeepSeek API Configuration
# Reads from environment variable or fallback to provided key
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

# TTS Configuration
# Options: zh-CN-YunxiNeural (沉稳富有张力), zh-CN-XiaoxiaoNeural, zh-CN-YunjianNeural
TTS_VOICE = os.environ.get("TTS_VOICE", "zh-CN-YunxiNeural")
TTS_RATE = os.environ.get("TTS_RATE", "-10%")  # -10% Slower, clear, pedagogical articulation
TTS_VOLUME = os.environ.get("TTS_VOLUME", "+0%")

# Visual & Timing Constants
DEFAULT_PAUSE_BUFFER = 3.5  # Extended 3.5s deliberate cognitive digestion pause after each slide
MIN_ACTION_DURATION = 2.0   # Minimum seconds for any visual action

# Default CUDA Document
DEFAULT_PDF_PATH = BASE_DIR / "cuda-programming-guide.pdf"

# Execution & Checkpoint Cache Mode
DEFAULT_RESUME_MODE = True  # Automatically resume from cached intermediate steps
FORCE_REGENERATE = False    # When True, ignores cache and regenerates all slides/audio

# Automatic FFmpeg Auto-Discovery & Path Injection
def setup_ffmpeg_path():
    """Ensures ffmpeg is discoverable by system PATH and subprocesses."""
    import shutil
    if shutil.which("ffmpeg"):
        return

    # Check local venv Scripts
    venv_ffmpeg = BASE_DIR / ".venv" / "Scripts" / "ffmpeg.exe"
    if venv_ffmpeg.exists():
        os.environ["PATH"] = f"{venv_ffmpeg.parent};" + os.environ.get("PATH", "")
        return

    # Check imageio_ffmpeg binary
    try:
        import imageio_ffmpeg
        ffmpeg_bin = Path(imageio_ffmpeg.get_ffmpeg_exe())
        if ffmpeg_bin.exists():
            os.environ["PATH"] = f"{ffmpeg_bin.parent};" + os.environ.get("PATH", "")
            return
    except Exception:
        pass

setup_ffmpeg_path()

