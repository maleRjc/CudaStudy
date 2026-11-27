"""
CUDA Educational Video Generator GUI (CudaVideoStudio)
Modern CustomTkinter Desktop Interface for 5-Layer Cognitive Animation Pipeline.
"""

import os
import sys
import io
import time
import queue
import threading
import subprocess
import traceback
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

import config
import check_env
from pipeline.l1_chunker import CudaChunker, CORE_COGNITIVE_UNITS
from pipeline.l1_full_parser import FullBookPdfParser
from pipeline.l2_deep_deck import DeepPedagogicalDeckGenerator
from pipeline.l2_deck_generator import LectureDeckGenerator
from pipeline.l2b_slide_exporter import export_deck_to_markdown_ppt, export_deck_to_html_presentation
from pipeline.l2_deepseek_beats import DeepSeekBeatGenerator
from pipeline.l3_audio_timing import AudioTimingEngine
from pipeline.l4_manim_generator import ManimEngine
from pipeline.l4b_slide_renderer import SlideVideoRenderer
from pipeline.l5_video_composer import VideoComposer
from pipeline.chapter_orchestrator import ChapterOrchestrator
from pipeline.full_book_orchestrator import FullBookOrchestrator


# UI Theme Configuration
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")

COLOR_ACCENT = "#76B900"        # NVIDIA Green
COLOR_ACCENT_HOVER = "#8CE000"
COLOR_BG_DARK = "#0D1117"
COLOR_CARD_BG = "#161B22"
COLOR_CARD_BORDER = "#30363D"
COLOR_TEXT_MUTED = "#8B949E"


class LogEmitter:
    """Thread-safe log interceptor that sends messages to the GUI queue."""
    encoding = "utf-8"
    errors = "replace"

    def __init__(self, log_queue: queue.Queue):
        self.log_queue = log_queue

    def write(self, msg: str):
        if msg and msg.strip():
            self.log_queue.put(("log", msg.rstrip()))

    def flush(self):
        pass

    def isatty(self) -> bool:
        return False

    def fileno(self):
        raise io.UnsupportedOperation("LogEmitter has no file descriptor")


class CudaStudioApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window settings
        self.title("CUDA 教学微视频可视化生成器 · CudaVideoStudio v2.0")
        self.geometry("1180x760")
        self.minsize(980, 640)
        self.configure(fg_color=COLOR_BG_DARK)

        # Runtime State
        self.log_queue = queue.Queue()
        self.worker_thread = None
        self.is_running = False
        self.last_produced_video = None
        self.last_produced_srt = None
        self.last_produced_scene = None
        self.last_produced_ppt = None
        self.remember_key_var = tk.BooleanVar(value=True)
        self._last_saved_key = ""

        # Curriculum Sections (Dynamically loaded from PDF)
        self.curriculum_sections = []
        self.chunk_options = {}
        self._load_curriculum_from_pdf(config.DEFAULT_PDF_PATH)

        # Build Interface
        self._build_header()
        self._build_main_layout()
        self._poll_log_queue()

        # Load initial chunks if needed
        self.after(100, self._initial_check)

    def _build_header(self):
        """Top Header Banner."""
        header_frame = ctk.CTkFrame(self, fg_color=COLOR_CARD_BG, corner_radius=0, height=70)
        header_frame.pack(fill="x", side="top")
        header_frame.pack_propagate(False)

        title_label = ctk.CTkLabel(
            header_frame,
            text="⚡ CUDA 教学微视频自动化生成器",
            font=ctk.CTkFont(family="Microsoft YaHei", size=22, weight="bold"),
            text_color="#FFFFFF"
        )
        title_label.pack(side="left", padx=25, pady=(12, 0))

        sub_label = ctk.CTkLabel(
            header_frame,
            text="基于认知冲突模型 · 3Blue1Brown 风格 Manim 动画 · 音频优先时钟驱动 · 刻意顿悟留白",
            font=ctk.CTkFont(family="Microsoft YaHei", size=12),
            text_color=COLOR_ACCENT
        )
        sub_label.pack(side="left", padx=25, pady=(38, 0))

        # Status badge
        self.status_badge = ctk.CTkLabel(
            header_frame,
            text="● 系统就绪",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13, weight="bold"),
            text_color="#10B981"
        )
        self.status_badge.pack(side="right", padx=25)

    def _build_main_layout(self):
        """Main Split Layout: Left Controls + Right Monitor & Output."""
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=15)

        # ----------------- LEFT CONTROL PANEL -----------------
        left_panel = ctk.CTkScrollableFrame(container, fg_color=COLOR_CARD_BG, width=440, corner_radius=12)
        left_panel.pack(side="left", fill="both", padx=(0, 10))

        # 1. Document & Chunk Section
        sec1_lbl = ctk.CTkLabel(left_panel, text="📌 知识源与概念切片", font=ctk.CTkFont(family="Microsoft YaHei", size=15, weight="bold"), text_color="#FFFFFF")
        sec1_lbl.pack(anchor="w", padx=15, pady=(15, 8))

        ctk.CTkLabel(left_panel, text="CUDA 手册 PDF 路径:", font=ctk.CTkFont(size=12), text_color=COLOR_TEXT_MUTED).pack(anchor="w", padx=15)
        pdf_row = ctk.CTkFrame(left_panel, fg_color="transparent")
        pdf_row.pack(fill="x", padx=15, pady=(2, 10))
        
        self.pdf_entry = ctk.CTkEntry(pdf_row, height=32, font=ctk.CTkFont(size=12))
        self.pdf_entry.insert(0, str(config.DEFAULT_PDF_PATH))
        self.pdf_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        btn_browse = ctk.CTkButton(pdf_row, text="浏览...", width=60, height=32, command=self._browse_pdf)
        btn_browse.pack(side="right")

        ctk.CTkLabel(left_panel, text="选择生成的目标章节 / 概念切片:", font=ctk.CTkFont(size=12), text_color=COLOR_TEXT_MUTED).pack(anchor="w", padx=15)
        combo_vals = list(self.chunk_options.values()) if self.chunk_options else ["暂无可用章节"]
        self.chunk_combo = ctk.CTkComboBox(
            left_panel,
            values=combo_vals,
            height=34,
            font=ctk.CTkFont(family="Microsoft YaHei", size=12)
        )
        if combo_vals:
            self.chunk_combo.set(combo_vals[0])
        self.chunk_combo.pack(fill="x", padx=15, pady=(2, 15))

        # 2. DeepSeek AI Settings
        sec2_lbl = ctk.CTkLabel(left_panel, text="🧠 DeepSeek AI 认知提炼设置", font=ctk.CTkFont(family="Microsoft YaHei", size=15, weight="bold"), text_color="#FFFFFF")
        sec2_lbl.pack(anchor="w", padx=15, pady=(10, 8))

        ctk.CTkLabel(left_panel, text="DeepSeek API Key (必需，填一次可保存):", font=ctk.CTkFont(size=12), text_color=COLOR_TEXT_MUTED).pack(anchor="w", padx=15)
        key_row = ctk.CTkFrame(left_panel, fg_color="transparent")
        key_row.pack(fill="x", padx=15, pady=(2, 2))

        self.api_key_entry = ctk.CTkEntry(key_row, height=32, show="•", placeholder_text="sk-...", font=ctk.CTkFont(size=12))
        existing_key = config.api_key()
        if existing_key:
            self.api_key_entry.insert(0, existing_key)
        self.api_key_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.api_key_entry.bind("<FocusOut>", self._on_key_focus_out)
        self.api_key_entry.bind("<Return>", self._on_key_focus_out)

        btn_test_key = ctk.CTkButton(key_row, text="测试连接", width=70, height=32, command=self._test_api_key)
        btn_test_key.pack(side="right")

        self.remember_key_check = ctk.CTkCheckBox(
            left_panel,
            text="记住 Key（保存到本机 .env，下次自动填入；已被 git 忽略）",
            variable=self.remember_key_var,
            font=ctk.CTkFont(family="Microsoft YaHei", size=11),
            checkbox_width=18,
            checkbox_height=18,
            border_width=2,
            text_color=COLOR_TEXT_MUTED,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
        )
        self.remember_key_check.pack(anchor="w", padx=18, pady=(0, 4))

        btn_clear_key = ctk.CTkButton(
            left_panel,
            text="清除已保存 Key",
            width=120,
            height=26,
            font=ctk.CTkFont(family="Microsoft YaHei", size=11),
            fg_color="#3A1F2A",
            hover_color="#5A2A3A",
            text_color="#FF9AA8",
            command=self._clear_saved_key,
        )
        btn_clear_key.pack(anchor="w", padx=18, pady=(0, 10))

        # 3. Audio & Voiceover Settings
        sec3_lbl = ctk.CTkLabel(left_panel, text="🎙️ 语音旁白与音色设定", font=ctk.CTkFont(family="Microsoft YaHei", size=15, weight="bold"), text_color="#FFFFFF")
        sec3_lbl.pack(anchor="w", padx=15, pady=(10, 8))

        voices = [
            "zh-CN-YunxiNeural (沉稳富有教学张力 - 推荐)",
            "zh-CN-XiaoxiaoNeural (清新明亮)",
            "zh-CN-YunjianNeural (深沉磁性解说)"
        ]
        self.voice_combo = ctk.CTkComboBox(left_panel, values=voices, height=34, font=ctk.CTkFont(size=12))
        self.voice_combo.set(voices[0])
        self.voice_combo.pack(fill="x", padx=15, pady=(2, 15))

        # 4. Manim Video Quality
        sec4_lbl = ctk.CTkLabel(left_panel, text="🎬 动画渲染画质与执行策略", font=ctk.CTkFont(family="Microsoft YaHei", size=15, weight="bold"), text_color="#FFFFFF")
        sec4_lbl.pack(anchor="w", padx=15, pady=(10, 8))

        self.quality_seg = ctk.CTkSegmentedButton(
            left_panel,
            values=["720P + 88px 字幕条带 (固定)"],
            selected_color=COLOR_ACCENT,
            selected_hover_color=COLOR_ACCENT_HOVER,
            height=34
        )
        self.quality_seg.set("720P + 88px 字幕条带 (固定)")
        self.quality_seg.pack(fill="x", padx=15, pady=(2, 10))

        # Checkpoint Resume Toggle
        self.resume_var = ctk.BooleanVar(value=True)
        self.resume_check = ctk.CTkCheckBox(
            left_panel,
            text="启用断点续跑 (跳过已渲染视频与分镜)",
            variable=self.resume_var,
            font=ctk.CTkFont(size=12),
            text_color="#E0E6ED"
        )
        self.resume_check.pack(anchor="w", padx=15, pady=(2, 12))

        # 5. Action Buttons (Run Pipeline + Env Check)
        self.btn_run = ctk.CTkButton(
            left_panel,
            text="🚀 一键生成 PPT 讲稿与精讲视频",
            font=ctk.CTkFont(family="Microsoft YaHei", size=16, weight="bold"),
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            height=46,
            corner_radius=8,
            command=self._start_pipeline
        )
        self.btn_run.pack(fill="x", padx=15, pady=(5, 8))

        self.btn_check_env = ctk.CTkButton(
            left_panel,
            text="🔍 运行系统依赖体检 (FFmpeg / Manim / TTS)",
            font=ctk.CTkFont(family="Microsoft YaHei", size=12),
            fg_color="#2A2F3A",
            hover_color="#3A404F",
            height=32,
            corner_radius=6,
            command=self._run_env_check
        )
        self.btn_check_env.pack(fill="x", padx=15, pady=(2, 15))


        # ----------------- RIGHT MONITOR & OUTPUT PANEL -----------------
        right_panel = ctk.CTkFrame(container, fg_color=COLOR_CARD_BG, corner_radius=12)
        right_panel.pack(side="right", fill="both", expand=True)

        # Stage Progress Stepper
        step_title = ctk.CTkLabel(right_panel, text="⚙️ 五层管线实时推进状态", font=ctk.CTkFont(family="Microsoft YaHei", size=15, weight="bold"), text_color="#FFFFFF")
        step_title.pack(anchor="w", padx=20, pady=(15, 8))

        self.stages_frame = ctk.CTkFrame(right_panel, fg_color="#1F242C", corner_radius=8)
        self.stages_frame.pack(fill="x", padx=20, pady=(0, 10))

        self.stage_labels = []
        stage_names = ["1. 语义切片", "2. PPT讲稿生成", "3. 口播音频对齐", "4. Manim场景渲染", "5. 长片混流交付"]
        for i, name in enumerate(stage_names):
            lbl = ctk.CTkLabel(self.stages_frame, text=name, font=ctk.CTkFont(size=12), text_color=COLOR_TEXT_MUTED)
            lbl.grid(row=0, column=i, padx=12, pady=10, sticky="ew")
            self.stages_frame.grid_columnconfigure(i, weight=1)
            self.stage_labels.append(lbl)

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(right_panel, height=8, progress_color=COLOR_ACCENT)
        self.progress_bar.pack(fill="x", padx=20, pady=(0, 6))
        self.progress_bar.set(0.0)

        self.detail_status = ctk.CTkLabel(right_panel, text="等待触发生成...", font=ctk.CTkFont(size=12), text_color=COLOR_TEXT_MUTED)
        self.detail_status.pack(anchor="w", padx=20, pady=(0, 10))

        # Realtime Log Console
        log_head = ctk.CTkLabel(right_panel, text="💻 实时执行日志", font=ctk.CTkFont(family="Microsoft YaHei", size=14, weight="bold"), text_color="#FFFFFF")
        log_head.pack(anchor="w", padx=20, pady=(5, 4))

        self.log_textbox = ctk.CTkTextbox(
            right_panel,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color="#0D1117",
            text_color="#E6EDF3",
            corner_radius=8
        )
        self.log_textbox.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        # Result Action Bar
        self.result_frame = ctk.CTkFrame(right_panel, fg_color="#1F242C", corner_radius=8, height=54)
        self.result_frame.pack(fill="x", padx=20, pady=(0, 15))
        self.result_frame.pack_propagate(False)

        self.btn_play = ctk.CTkButton(
            self.result_frame,
            text="🎬 打开已生成视频",
            font=ctk.CTkFont(family="Microsoft YaHei", size=12, weight="bold"),
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            width=140,
            height=34,
            state="disabled",
            command=self._open_video
        )
        self.btn_play.pack(side="left", padx=12, pady=10)

        self.btn_open_folder = ctk.CTkButton(
            self.result_frame,
            text="📂 打开输出目录",
            font=ctk.CTkFont(family="Microsoft YaHei", size=12),
            fg_color="#374151",
            hover_color="#4B5563",
            width=120,
            height=34,
            command=self._open_output_folder
        )
        self.btn_open_folder.pack(side="left", padx=(0, 10), pady=10)

        self.btn_ppt = ctk.CTkButton(
            self.result_frame,
            text="📊 浏览PPT讲稿",
            font=ctk.CTkFont(family="Microsoft YaHei", size=12),
            fg_color="#374151",
            hover_color="#4B5563",
            width=120,
            height=34,
            command=self._open_ppt
        )
        self.btn_ppt.pack(side="left", padx=(0, 10), pady=10)

        self.btn_srt = ctk.CTkButton(
            self.result_frame,
            text="📝 查看中文字幕",
            font=ctk.CTkFont(family="Microsoft YaHei", size=12),
            fg_color="#374151",
            hover_color="#4B5563",
            width=120,
            height=34,
            state="disabled",
            command=self._open_srt
        )
        self.btn_srt.pack(side="left", padx=(0, 10), pady=10)

    def _initial_check(self):
        """Enable playback buttons when a freshly produced final video exists."""
        videos = sorted(
            (config.OUTPUT_DIR / "videos").glob("*_final.mp4"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not videos:
            return
        latest = videos[0]
        srt = latest.with_name(latest.name.replace("_final.mp4", "_subtitles.srt"))
        self.last_produced_video = latest
        self.last_produced_srt = srt if srt.exists() else None
        self.btn_play.configure(state="normal")
        if self.last_produced_srt:
            self.btn_srt.configure(state="normal")
        self._log(f"[系统提示] 检测到历史成片：{latest.name}，可直接打开播放。")

    def _clear_saved_key(self):
        if not messagebox.askyesno(
            "清除已保存的 Key",
            "将从 .env 删除已保存的 DeepSeek Key，并清空输入框。\n其他设置会保留，确定继续？",
            parent=self,
        ):
            return
        path = config.BASE_DIR / ".env"
        try:
            path = config.clear_api_key()
        except Exception as exc:
            messagebox.showerror("清除失败", f"无法清除 {path}：{exc}", parent=self)
            return
        self.api_key_entry.delete(0, "end")
        self._last_saved_key = ""
        self._log(f"[*] 已清除保存的 Key（{path}）。请填入新 Key 后点“测试连接”。")

    def _on_key_focus_out(self, event=None):
        self._save_api_key(silent=False)

    def _save_api_key(self, silent: bool = False) -> bool:
        if not self.remember_key_var.get():
            return False
        key = self.api_key_entry.get().strip()
        if not key:
            return False
        if key == self._last_saved_key:
            return True
        try:
            path = config.save_api_key(key)
        except Exception as exc:
            if not silent:
                self._log(f"[!] Key 保存失败（仍可本次使用）: {exc}")
            return False
        self._last_saved_key = key
        if not silent:
            self._log(f"[*] Key 已保存到 {path}，下次启动会自动填入。")
        return True

    def _test_api_key(self):
        key = self.api_key_entry.get().strip()
        if not key:
            messagebox.showwarning("提示", "请先填写 DeepSeek API Key。")
            return
        config.set_api_key(key)
        remember = bool(self.remember_key_var.get())
        self._log("\n[*] 正在验证 DeepSeek API Key（真实请求 /chat/completions）...")

        def _bg_test():
            from pipeline.deepseek_client import DeepSeekClient, diagnose

            result = diagnose(DeepSeekClient(api_key=key))
            self.log_queue.put(("log", f"[{result['status']}] {result['detail']}"))
            if result.get("advice"):
                self.log_queue.put(("log", f"         └─ {result['advice']}"))
            if "401" in f"{result.get('detail', '')} {result.get('advice', '')}":
                self.log_queue.put(
                    ("log", "[*] 服务端拒绝了该 Key；可点“清除已保存 Key”后填入新 Key，避免下次继续自动填入失效 Key。")
                )
            if remember and result.get("status") == "PASS":
                try:
                    path = config.save_api_key(key)
                    self.log_queue.put(("log", f"[*] Key 已验证并保存到 {path}，下次启动自动填入。"))
                except Exception as exc:
                    self.log_queue.put(("log", f"[!] Key 验证通过，但保存失败: {exc}"))

        threading.Thread(target=_bg_test, daemon=True).start()

    def _browse_pdf(self):
        filename = filedialog.askopenfilename(
            title="选择技术手册 PDF 文件",
            filetypes=[("PDF Documents", "*.pdf"), ("All Files", "*.*")]
        )
        if not filename:
            return
        self.pdf_entry.delete(0, "end")
        self.pdf_entry.insert(0, filename)
        self._load_curriculum_from_pdf(Path(filename))
        values = list(self.chunk_options.values()) or ["暂无可用章节"]
        self.chunk_combo.configure(values=values)
        self.chunk_combo.set(values[0])
        if self.curriculum_sections:
            self._log(f"[*] 已重载 PDF 目录：{len(self.curriculum_sections)} 个章节。")
        else:
            self._log("[!] 该 PDF 未解析到目录大纲，请检查文件。")

    def _load_curriculum_from_pdf(self, pdf_path: Path):
        """Dynamically parses all chapters & sections from the given PDF outline and DeepSeek Director."""
        self.chunk_options = {}

        # 1. First add the 30 System Curated Episodes (from CUDA原理与实现教学视频项目实施文档.docx)
        try:
            from pipeline.deepseek_director import CURRICULUM_30_EPISODES
            for ep in CURRICULUM_30_EPISODES:
                self.chunk_options[f"ep_{ep['ep_id']}"] = f"🌟 [实例文档第{ep['ep_id']}讲] {ep['title']} ({ep['duration']}, {ep['guide_pages']})"
        except Exception as e:
            print(f"[Warning] Loading 30-episode curriculum: {e}")

        # 2. Add dynamic sections from PDF outline
        try:
            parser = FullBookPdfParser(pdf_path)
            curriculum = parser.extract_full_curriculum(min_level=1, max_level=1)
            self.curriculum_sections = curriculum

            for s in curriculum[:30]:  # Load major PDF sections
                label = f"📄 [手册原生] {s['index']:02d} · {s['title']} (P{s['start_page']}-P{s['end_page']}, {s['page_count']}页)"
                self.chunk_options[s["sec_id"]] = label

            self.chunk_options["all"] = "⚡ 顺序生产全部章节并拼接为长篇大课 (Batch & Stitch Master Course)"
        except Exception as e:
            print(f"[Warning] PDF outline parsing fallback: {e}")
            if not self.chunk_options:
                self.chunk_options = {
                    "sec_001_intro": "01 · Programming Model (P20-P30)",
                    "sec_002_simt": "02 · Writing SIMT Kernels (P61-P87)",
                    "all": "⚡ 全部章节一键生产"
                }

    def _log(self, text: str):
        self.log_textbox.insert("end", text + "\n")
        self.log_textbox.see("end")

    def _update_stage(self, stage, text: str):
        if isinstance(stage, float):
            ratio = max(0.0, min(1.0, stage))
            stage_idx = min(4, int(ratio * 5))
        else:
            stage_idx = int(stage)
            ratio = (stage_idx + 1) / 5.0
        self.progress_bar.set(ratio)
        self.detail_status.configure(text=text)
        for i, lbl in enumerate(self.stage_labels):
            if i < stage_idx:
                lbl.configure(text_color="#10B981")
            elif i == stage_idx:
                lbl.configure(text_color=COLOR_ACCENT)
            else:
                lbl.configure(text_color=COLOR_TEXT_MUTED)

    def _on_progress(self, stage: str, message: str, pct: float):
        """Called from the pipeline thread - only touches the queue."""
        self.log_queue.put(("stage", (float(pct), message)))

    def _poll_log_queue(self):
        try:
            while True:
                msg_type, content = self.log_queue.get_nowait()
                if msg_type == "log":
                    self._log(content)
                elif msg_type == "stage":
                    s_idx, s_text = content
                    self._update_stage(s_idx, s_text)
                elif msg_type == "finish":
                    self._handle_finish(content)
        except queue.Empty:
            pass
        self.after(80, self._poll_log_queue)

    def _run_env_check(self):
        key = self.api_key_entry.get().strip()
        config.set_api_key(key)
        self.log_textbox.delete("1.0", "end")
        self._log("=" * 75)
        self._log("🚀 系统与依赖自检（FFmpeg / Manim / Edge-TTS / DeepSeek / PDF）")
        self._log("=" * 75)

        def _worker():
            try:
                from pipeline.deepseek_client import DeepSeekClient, diagnose

                checks = check_env.run_all_checks()
                # Replace the generic DeepSeek probe with one that uses the GUI key.
                checks = [c for c in checks if "DeepSeek" not in c.get("name", "")]
                probe = diagnose(DeepSeekClient(api_key=key))
                checks.append(
                    {
                        "name": "DeepSeek API（当前输入框 Key）",
                        "status": probe["status"],
                        "detail": probe["detail"],
                        "advice": probe.get("advice", ""),
                    }
                )

                icons = {"PASS": "✅ [通过]", "WARN": "⚠️ [注意]", "FAIL": "❌ [缺失]", "INFO": "💡 [提示]"}
                failed = False
                for item in checks:
                    icon = icons.get(item["status"], "[ ]")
                    self.log_queue.put(("log", f"{icon} {item['name']}: {item['detail']}"))
                    if item.get("advice"):
                        self.log_queue.put(("log", f"         └─ 建议: {item['advice']}"))
                    failed = failed or item["status"] == "FAIL"
                self.log_queue.put(("log", "=" * 75))
                self.log_queue.put(
                    ("log", "⚠️ 存在缺失依赖，请按提示配置。" if failed else "🎉 核心依赖就绪，可以开始生成。")
                )
            except Exception:
                self.log_queue.put(("log", "[!] 体检异常:\n" + traceback.format_exc()))

        threading.Thread(target=_worker, daemon=True).start()

    def _start_pipeline(self):
        if self.is_running:
            return

        pdf_path = Path(self.pdf_entry.get().strip())
        if not pdf_path.exists() or not pdf_path.is_file():
            messagebox.showerror("PDF 不存在", f"找不到 PDF 文件：\n{pdf_path}\n\n请先选择有效的 PDF。")
            return

        selected_chunk_text = self.chunk_combo.get()
        chunk_key = next((k for k, v in self.chunk_options.items() if v == selected_chunk_text), None)
        if chunk_key is None:
            messagebox.showwarning("未选择章节", "请在下拉框中选择要生成的章节。")
            return

        api_key = self.api_key_entry.get().strip()
        if not api_key:
            messagebox.showerror(
                "需要 DeepSeek API Key",
                "本版本已移除「无 Key 兜底」模式，必须配置 DEEPSEEK_API_KEY 才能生成讲稿与动画。\n\n"
                "请在输入框填入 Key，或在项目根目录 .env 中配置后重启。",
            )
            return
        self._save_api_key(silent=False)
        config.set_api_key(api_key)
        voice_str = self.voice_combo.get().split()[0]
        quality_str = self.quality_seg.get()
        quality_flag = "-qm"

        # Reset per-run output state so a stale file can never look like success.
        self.last_produced_video = None
        self.last_produced_srt = None
        self.last_produced_ppt = None
        self._run_produced = []
        self._run_error = ""

        self.is_running = True
        self.btn_run.configure(state="disabled", text="⏳ 正在全自动渲染中...")
        self.status_badge.configure(text="● 正在生成", text_color=COLOR_ACCENT)
        self.btn_play.configure(state="disabled")
        self.btn_srt.configure(state="disabled")
        self.log_textbox.delete("1.0", "end")

        self._log(f"[*] 任务: {selected_chunk_text}")
        self._log(
            f"[*] DeepSeek: {'已启用 (' + api_key[:4] + '***)' if api_key else '未配置（生成会直接失败）'} "
            f"| 音色: {voice_str} | 输出: 1280x720 + 88px 字幕条带"
        )

        resume_mode = self.resume_var.get()
        self.worker_thread = threading.Thread(
            target=self._run_worker,
            args=(pdf_path, chunk_key, api_key, voice_str, quality_flag, resume_mode),
            daemon=True,
        )
        self.worker_thread.start()

    def _run_worker(self, pdf_path: Path, chunk_key: str, api_key: str, voice: str, quality: str, resume: bool = True):
        emitter = LogEmitter(self.log_queue)
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout = emitter
        sys.stderr = emitter

        try:
            config.set_api_key(api_key)
            self.log_queue.put(("stage", (0.0, "Layer 1: 解析 PDF 目录树与章节内容...")))
            full_orch = FullBookOrchestrator(
                pdf_path=pdf_path,
                api_key=api_key,
                voice=voice,
                progress=self._on_progress,
            )
            curriculum = full_orch.parser.extract_full_curriculum(min_level=1, max_level=1)
            if not curriculum:
                raise RuntimeError("PDF 中没有解析到任何章节，请确认文件包含目录大纲。")

            target_sections = []
            if chunk_key.startswith("ep_"):
                ep_num = chunk_key.replace("ep_", "")
                from pipeline.deepseek_director import DeepSeekDirector
                from pipeline.episode_router import describe_match, resolve_episode_section

                director = DeepSeekDirector(api_key=api_key)
                ep_spec = director.find_episode_by_id_or_title(ep_num) or {
                    "ep_id": ep_num,
                    "title": self.chunk_options.get(chunk_key, f"第{ep_num}讲"),
                }
                resolved = resolve_episode_section(
                    curriculum, ep_spec, int(ep_num) if str(ep_num).isdigit() else 1
                )
                if resolved:
                    target_sections = [resolved]
                    self.log_queue.put(("log", f"[*] 剧集章节路由: {describe_match(resolved)}"))
            elif chunk_key == "all":
                target_sections = curriculum[:10]
            else:
                target_sections = [s for s in curriculum if s["sec_id"] == chunk_key]
                if not target_sections:
                    target_sections = [curriculum[0]]

            produced = []
            for idx, section in enumerate(target_sections, start=1):
                self.log_queue.put(
                    ("stage", (0.05 + 0.85 * (idx - 1) / max(1, len(target_sections)),
                               f"[{idx}/{len(target_sections)}] {section['title']}"))
                )
                result = full_orch.produce_section_video(section, quality=quality, resume=resume)
                video = result.get("final_video")
                if video and Path(video).exists():
                    produced.append(Path(video))
                    self._run_produced = list(produced)
                    self.last_produced_video = Path(video)
                    self.last_produced_srt = Path(str(video).replace("_final.mp4", "_subtitles.srt"))
                    self.last_produced_ppt = result.get("deck_html")
                else:
                    self.log_queue.put(
                        ("log", f"[!] 章节失败: {section['title']} — {result.get('error', '未知错误')}")
                    )

            if chunk_key == "all" and len(produced) > 1:
                self.log_queue.put(("stage", (0.95, "拼接整书大课（不再二次烧字幕）...")))
                master = full_orch.composer.concatenate_course_videos(
                    produced,
                    output_filename="00_cuda_master_course.mp4",
                    burn_subtitles=False,
                )
                if master and master.exists():
                    self.last_produced_video = master
                    produced = [master]

            if not produced:
                raise RuntimeError(self._run_error or "所有章节均未产出视频，请查看上方日志。")
            self.log_queue.put(("finish", True))

        except Exception:
            details = traceback.format_exc()
            self._run_error = details
            self.log_queue.put(("log", "[!] 执行异常：\n" + details))
            self.log_queue.put(("finish", False))
        finally:
            sys.stdout, sys.stderr = old_stdout, old_stderr

    def _handle_finish(self, success: bool):
        self.is_running = False
        self.btn_run.configure(state="normal", text="🚀 一键全自动生成微视频")

        ok = bool(success and self.last_produced_video and self.last_produced_video.exists())
        if ok:
            self.status_badge.configure(text="● 生成完成", text_color="#10B981")
            self.progress_bar.set(1.0)
            self.detail_status.configure(text=f"成片完成：{self.last_produced_video.name}")
            self.btn_play.configure(state="normal")
            if self.last_produced_srt and self.last_produced_srt.exists():
                self.btn_srt.configure(state="normal")
            self._log(f"\n🎉 [成功] 视频: {self.last_produced_video}\n")
            messagebox.showinfo("生成完成", f"视频已生成：\n{self.last_produced_video}")
        else:
            self.status_badge.configure(text="● 异常中断", text_color="#EF4444")
            self.detail_status.configure(text="生成中断，请查看日志中的异常堆栈。")
            messagebox.showerror("生成失败", "本次没有产出视频，请查看日志中的异常堆栈。")

    def _open_video(self):
        if self.last_produced_video and self.last_produced_video.exists():
            os.startfile(str(self.last_produced_video))
        else:
            messagebox.showwarning("提示", "未找到已生成的视频文件。")

    def _open_output_folder(self):
        folder = config.OUTPUT_DIR / "videos"
        folder.mkdir(parents=True, exist_ok=True)
        os.startfile(str(folder))

    def _open_srt(self):
        if self.last_produced_srt and self.last_produced_srt.exists():
            os.startfile(str(self.last_produced_srt))
        else:
            messagebox.showwarning("提示", "未找到字幕文件。")

    def _open_ppt(self):
        if self.last_produced_ppt and Path(self.last_produced_ppt).exists():
            os.startfile(str(self.last_produced_ppt))
        else:
            # Check default decks folder
            decks_dir = config.OUTPUT_DIR / "decks"
            htmls = list(decks_dir.glob("*.html"))
            if htmls:
                os.startfile(str(htmls[0]))
            else:
                messagebox.showwarning("提示", "未找到已生成的 PPT 讲稿文件。")


def main():
    # PyInstaller --windowed gives us no console: sys.stdout/stderr are None.
    # Install harmless targets before anything can print.
    if sys.stdout is None:
        sys.stdout = io.StringIO()
    if sys.stderr is None:
        sys.stderr = io.StringIO()

    if "--selftest" in sys.argv:
        # Headless smoke test used by build_exe.py: writes a report and exits.
        lines = []
        try:
            lines.append(f"frozen={getattr(sys, 'frozen', False)}")
            lines.append(f"base_dir={config.BASE_DIR}")
            lines.append(f"output_dir={config.OUTPUT_DIR}")
            lines.append(f"api_key_configured={config.has_api_key()}")
            lines.append(f"pdf_exists={config.DEFAULT_PDF_PATH.exists()}")
            lines.append(f"assets_storyboard={(config.BASE_DIR / 'assets' / 'storyboard_scene.py').exists()}")
            lines.append(f"ffmpeg={config.ffmpeg_binary()}")
            from pipeline.manim_renderer import find_manim_python

            found = find_manim_python()
            lines.append(f"manim_python={found[0] if found else None}")
            lines.append(f"manim_version={found[1] if found else None}")
            import customtkinter  # noqa: F401
            import av  # noqa: F401
            import pypdf  # noqa: F401
            import edge_tts  # noqa: F401

            lines.append("gui_deps=ok")
            if config.has_api_key():
                lines.append("RESULT=PASS")
            else:
                lines.append("RESULT=FAIL: DEEPSEEK_API_KEY missing (fallback mode removed)")
        except Exception as exc:
            lines.append(f"RESULT=FAIL: {exc}")
        try:
            (config.OUTPUT_DIR / "_selftest.txt").write_text("\n".join(lines), encoding="utf-8")
        except OSError:
            pass
        return

    app = CudaStudioApp()
    app.mainloop()


if __name__ == "__main__":
    main()
