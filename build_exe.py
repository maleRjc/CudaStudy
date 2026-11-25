"""
Build Script for packaging CudaVideoStudio into a Windows GUI executable (.exe).
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PYINSTALLER_EXE = BASE_DIR / ".venv" / "Scripts" / "pyinstaller.exe"

def build():
    print("=" * 70)
    print("🔨 Starting PyInstaller packaging for CudaVideoStudio...")
    print("=" * 70)

    # Clean previous build artifacts
    for d in [BASE_DIR / "build", BASE_DIR / "dist"]:
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)

    cmd = [
        str(PYINSTALLER_EXE),
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name", "CudaVideoStudio",
        "--add-data", f"{BASE_DIR / 'assets'};assets",
        "--add-data", f"{BASE_DIR / 'pipeline'};pipeline",
        "--add-data", f"{BASE_DIR / 'config.py'};.",
        "--collect-data", "customtkinter",
        "--collect-submodules", "pipeline",
        "--collect-submodules", "assets",
        "--hidden-import", "customtkinter",
        "--hidden-import", "darkdetect",
        "--hidden-import", "PIL",
        "--hidden-import", "PIL.Image",
        "--hidden-import", "edge_tts",
        "--hidden-import", "pypdf",
        "--hidden-import", "av",
        "--hidden-import", "manim",
        str(BASE_DIR / "app_gui.py")
    ]

    print(f"[*] Running command:\n{' '.join(cmd)}\n")
    proc = subprocess.run(cmd, cwd=str(BASE_DIR))

    if proc.returncode == 0:
        dist_exe = BASE_DIR / "dist" / "CudaVideoStudio.exe"
        if dist_exe.exists():
            # Also copy to root for immediate access
            root_exe = BASE_DIR / "CudaVideoStudio.exe"
            shutil.copy2(dist_exe, root_exe)
            
            size_mb = round(root_exe.stat().st_size / 1024 / 1024, 2)
            print("=" * 70)
            print(f"🎉 [BUILD SUCCESS] Packaged GUI Executable created!")
            print(f"📍 Location 1: {dist_exe} ({size_mb} MB)")
            print(f"📍 Location 2 (Root): {root_exe} ({size_mb} MB)")
            print("=" * 70)
            return True

    print("[!] Build failed with exit code:", proc.returncode)
    return False

if __name__ == "__main__":
    success = build()
    sys.exit(0 if success else 1)
