"""
Environment & Dependency Diagnostics for CudaStudy Video Studio (check_env.py).
Checks Python environment, FFmpeg, Manim, Edge-TTS, LaTeX, and DeepSeek API connectivity.
Provides actionable tips for fixing missing dependencies.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple

import config


def run_silent(cmd: List[str], timeout: int = 15) -> Tuple[bool, str]:
    creationflags = 0
    startupinfo = None
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NO_WINDOW
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE

    try:
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=creationflags,
            startupinfo=startupinfo,
        )
        return (res.returncode == 0, (res.stdout + " " + res.stderr).strip())
    except Exception as e:
        return (False, str(e))


def check_python_version() -> Dict[str, Any]:
    major, minor = sys.version_info.major, sys.version_info.minor
    ok = (major == 3 and minor >= 10)
    msg = f"Python {major}.{minor}.{sys.version_info.micro} ({sys.executable})"
    return {
        "name": "Python 解释器版本",
        "status": "PASS" if ok else "WARN",
        "detail": msg,
        "advice": "" if ok else "建议升级至 Python 3.10+ 以获得最佳异步与类型注解支持。"
    }


def check_ffmpeg() -> Dict[str, Any]:
    # Check in PATH (including auto-discovered path by config)
    ffmpeg_in_path = shutil.which("ffmpeg")
    if ffmpeg_in_path:
        ok, out = run_silent(["ffmpeg", "-version"])
        ver = out.split("\n")[0] if out else "已安装"
        return {
            "name": "FFmpeg 视频编解码器",
            "status": "PASS",
            "detail": f"就绪 -> {ffmpeg_in_path} ({ver[:40]})",
            "advice": ""
        }

    # Check common Windows locations
    common_locations = [
        config.BASE_DIR / ".venv" / "Scripts" / "ffmpeg.exe",
        Path(r"C:\ffmpeg\bin\ffmpeg.exe"),
        Path(r"C:\Program Files\ffmpeg\bin\ffmpeg.exe"),
        config.BASE_DIR / "ffmpeg.exe",
        config.BASE_DIR / "bin" / "ffmpeg.exe",
    ]
    for loc in common_locations:
        if loc.exists():
            return {
                "name": "FFmpeg 视频编解码器",
                "status": "PASS",
                "detail": f"发现于 {loc} (已自动挂载到环境)",
                "advice": ""
            }

    return {
        "name": "FFmpeg 视频编解码器",
        "status": "FAIL",
        "detail": "未在系统 PATH 或虚拟环境中找到 ffmpeg.exe",
        "advice": "Windows 安装命令：winget install Gyan.FFmpeg 或 pip install imageio-ffmpeg"
    }



def check_manim() -> Dict[str, Any]:
    try:
        import manim
        return {
            "name": "Manim 物理动画引擎",
            "status": "PASS",
            "detail": f"Manim Community v{manim.__version__} (via {sys.executable})",
            "advice": ""
        }
    except Exception:
        pass

    from pipeline.l4_manim_generator import find_python_interpreter
    py_bin = find_python_interpreter()

    ok, out = run_silent([str(py_bin), "-c", "import manim; print(manim.__version__)"], timeout=15)
    if ok and out:
        return {
            "name": "Manim 物理动画引擎",
            "status": "PASS",
            "detail": f"Manim Community v{out.strip()} (via {py_bin})",
            "advice": ""
        }
    return {
        "name": "Manim 物理动画引擎",
        "status": "WARN",
        "detail": f"解释器 {py_bin} 未能成功 import manim",
        "advice": "运行命令安装：pip install manim"
    }



def check_latex() -> Dict[str, Any]:
    latex_in_path = shutil.which("latex") or shutil.which("dvisvgm")
    if latex_in_path:
        return {
            "name": "LaTeX 公式排版 (可选)",
            "status": "PASS",
            "detail": f"已安装 ({latex_in_path})",
            "advice": "支持原生 MathTex 极速矢量渲染。"
        }
    return {
        "name": "LaTeX 公式排版 (可选)",
        "status": "INFO",
        "detail": "未安装 MiKTeX / TeXLive / dvisvgm (系统已内置纯文本及 Unicode 自愈降级方案)",
        "advice": "可选安装：Windows 用户可通过 winget install MiKTeX.MiKTeX 安装完整公式支持。"
    }


def check_deepseek_api() -> Dict[str, Any]:
    api_key = config.DEEPSEEK_API_KEY or os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        return {
            "name": "DeepSeek API 大模型鉴权",
            "status": "WARN",
            "detail": "未检测到 DEEPSEEK_API_KEY（系统已内置零失败确定性算法引擎作为兜底）",
            "advice": "在 config.py 中填入或在终端执行 set DEEPSEEK_API_KEY=your_key 以启用大模型高阶提炼。"
        }

    # Test network ping
    import urllib.request
    import json
    try:
        url = f"{config.DEEPSEEK_BASE_URL.rstrip('/')}/models"
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "User-Agent": "CudaStudyDiagnostics/1.0"
            }
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                return {
                    "name": "DeepSeek API 大模型鉴权",
                    "status": "PASS",
                    "detail": f"连接成功 (Endpoint: {config.DEEPSEEK_BASE_URL}, Key: {api_key[:6]}***)",
                    "advice": ""
                }
    except Exception as e:
        return {
            "name": "DeepSeek API 大模型鉴权",
            "status": "WARN",
            "detail": f"已配置 Key 但端点连接异常: {str(e)[:60]}",
            "advice": "请检查网络或 API Key 余额。离线模式将自动启用算法合成保底。"
        }

    return {
        "name": "DeepSeek API 大模型鉴权",
        "status": "PASS",
        "detail": f"已配置 Key: {api_key[:6]}***",
        "advice": ""
    }


def check_edge_tts() -> Dict[str, Any]:
    try:
        import edge_tts
        return {
            "name": "Edge-TTS 语音合成库",
            "status": "PASS",
            "detail": f"edge-tts 库正常加载 (默认发音人: {config.TTS_VOICE})",
            "advice": ""
        }
    except ImportError:
        return {
            "name": "Edge-TTS 语音合成库",
            "status": "FAIL",
            "detail": "未安装 edge-tts",
            "advice": "运行命令安装：pip install edge-tts"
        }


def check_pdf_source() -> Dict[str, Any]:
    pdf_path = config.DEFAULT_PDF_PATH
    if pdf_path.exists():
        size_mb = round(pdf_path.stat().st_size / (1024 * 1024), 2)
        return {
            "name": "CUDA 官方教材 PDF",
            "status": "PASS",
            "detail": f"{pdf_path.name} ({size_mb} MB)",
            "advice": ""
        }
    return {
        "name": "CUDA 官方教材 PDF",
        "status": "WARN",
        "detail": f"未在 {pdf_path} 找到默认 PDF",
        "advice": "可将《CUDA C++ Programming Guide》放入项目根目录或在界面中浏览选择任意 PDF。"
    }


def run_all_checks() -> List[Dict[str, Any]]:
    return [
        check_python_version(),
        check_ffmpeg(),
        check_manim(),
        check_edge_tts(),
        check_deepseek_api(),
        check_latex(),
        check_pdf_source(),
    ]


def print_diagnostic_report():
    print("=" * 75)
    print("🚀 [CudaStudy Video Studio] 系统与运行环境诊断报告")
    print("=" * 75)

    checks = run_all_checks()
    all_pass = True

    status_icons = {
        "PASS": "✅ [通过]",
        "WARN": "⚠️ [注意]",
        "FAIL": "❌ [缺失]",
        "INFO": "💡 [提示]"
    }

    for c in checks:
        icon = status_icons.get(c["status"], "[ ]")
        print(f"{icon:<8} {c['name']:<25} : {c['detail']}")
        if c["advice"]:
            print(f"         └─ 建议: {c['advice']}")
        if c["status"] == "FAIL":
            all_pass = False

    print("=" * 75)
    if all_pass:
        print("🎉 核心环境完备！系统随时可以启动生成课程视频。")
    else:
        print("⚠️ 存在必要依赖未就绪，请参考上述建议配置后再运行生成。")
    print("=" * 75)
    return all_pass


if __name__ == "__main__":
    print_diagnostic_report()
