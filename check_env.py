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
    binary = config.ffmpeg_binary()
    if binary.exists() or shutil.which(str(binary)):
        ok, out = run_silent([str(binary), "-version"])
        version = out.split("\n")[0] if ok and out else "已找到"
        return {
            "name": "FFmpeg 视频编解码器",
            "status": "PASS" if ok else "WARN",
            "detail": f"{binary} ({version[:50]})",
            "advice": "" if ok else "文件存在但无法执行，请检查安装或改用 pip install imageio-ffmpeg。",
        }

    return {
        "name": "FFmpeg 视频编解码器",
        "status": "FAIL",
        "detail": "未找到 ffmpeg（PATH / .venv / imageio-ffmpeg 均不可用）",
        "advice": "pip install imageio-ffmpeg 或 winget install Gyan.FFmpeg",
    }




def check_manim() -> Dict[str, Any]:
    try:
        from pipeline.manim_renderer import find_manim_python

        found = find_manim_python()
    except Exception as exc:
        return {"name": "Manim 动画引擎", "status": "FAIL", "detail": f"探测失败: {exc}", "advice": "pip install manim"}

    if not found:
        return {
            "name": "Manim 动画引擎",
            "status": "FAIL",
            "detail": "找不到可 import manim 的 Python 解释器",
            "advice": "pip install manim，并确保主程序与 Manim 使用同一解释器。",
        }
    python_bin, version = found
    return {
        "name": "Manim 动画引擎",
        "status": "PASS",
        "detail": f"Manim Community v{version} via {python_bin}",
        "advice": "",
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
    try:
        from pipeline.deepseek_client import DeepSeekClient, diagnose

        result = diagnose(DeepSeekClient())
        return {
            "name": "DeepSeek API 大模型",
            "status": result["status"],
            "detail": result["detail"],
            "advice": result.get("advice", ""),
        }
    except Exception as exc:
        return {
            "name": "DeepSeek API 大模型",
            "status": "WARN",
            "detail": f"探测失败: {exc}",
            "advice": "检查 pipeline/deepseek_client.py 与网络设置。",
        }


def check_video_geometry() -> Dict[str, Any]:
    return {
        "name": "视频输出规格",
        "status": "PASS",
        "detail": (
            f"{config.VIDEO_WIDTH}x{config.VIDEO_HEIGHT}@{config.VIDEO_FPS}fps "
            f"（内容 {config.CONTENT_WIDTH}x{config.CONTENT_HEIGHT} + "
            f"{config.SUBTITLE_BAND_HEIGHT}px 字幕条带）"
        ),
        "advice": "",
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
        check_video_geometry(),
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
