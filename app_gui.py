"""
CUDA Educational Video Generator GUI (CudaVideoStudio)
Modern CustomTkinter Desktop Interface for 5-Layer Cognitive Animation Pipeline.
"""

import os
import sys
import time
import queue
import threading
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

import config
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
    def __init__(self, log_queue: queue.Queue):
        self.log_queue = log_queue

    def write(self, msg: str):
        if msg.strip():
            self.log_queue.put(("log", msg.strip()))

    def flush(self):
        pass


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

        ctk.CTkLabel(left_panel, text="DeepSeek API Key (可选，留空使用内置金标分镜):", font=ctk.CTkFont(size=12), text_color=COLOR_TEXT_MUTED).pack(anchor="w", padx=15)
        self.api_key_entry = ctk.CTkEntry(left_panel, height=32, show="•", placeholder_text="sk-...", font=ctk.CTkFont(size=12))
        if config.DEEPSEEK_API_KEY:
            self.api_key_entry.insert(0, config.DEEPSEEK_API_KEY)
        self.api_key_entry.pack(fill="x", padx=15, pady=(2, 8))

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
        sec4_lbl = ctk.CTkLabel(left_panel, text="🎬 动画渲染画质", font=ctk.CTkFont(family="Microsoft YaHei", size=15, weight="bold"), text_color="#FFFFFF")
        sec4_lbl.pack(anchor="w", padx=15, pady=(10, 8))

        self.quality_seg = ctk.CTkSegmentedButton(
            left_panel,
            values=["480P 预览 (-ql)", "720P 高清 (-qm)", "1080P 交付 (-qh)"],
            selected_color=COLOR_ACCENT,
            selected_hover_color=COLOR_ACCENT_HOVER,
            height=34
        )
        self.quality_seg.set("480P 预览 (-ql)")
        self.quality_seg.pack(fill="x", padx=15, pady=(2, 20))

        # 5. Big Action Button
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
        self.btn_run.pack(fill="x", padx=15, pady=(5, 15))

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
        """Checks for existing generated video to enable buttons if present."""
        sample_video = config.OUTPUT_DIR / "videos" / "01_global_thread_indexing_final.mp4"
        sample_srt = config.OUTPUT_DIR / "videos" / "01_global_thread_indexing_subtitles.srt"
        if sample_video.exists():
            self.last_produced_video = sample_video
            self.last_produced_srt = sample_srt
            self.btn_play.configure(state="normal")
            self.btn_srt.configure(state="normal")
            self._log("[系统提示] 检测到已存在历史成片，可随时点击'打开已生成视频'播放。\n")

    def _browse_pdf(self):
        filename = filedialog.askopenfilename(
            title="选择技术手册 PDF 文件",
            filetypes=[("PDF Documents", "*.pdf"), ("All Files", "*.*")]
        )
        if filename:
            self.pdf_entry.delete(0, "end")
            self.pdf_entry.insert(0, filename)
            self._load_curriculum_from_pdf(Path(filename))
            self.chunk_combo.configure(values=list(self.chunk_options.values()))
            first_val = list(self.chunk_options.values())[0]
            self.chunk_combo.set(first_val)
            self._log(f"[*] 成功重载 PDF 目录树: 共发现 {len(self.curriculum_sections)} 个章节小节。\n")

    def _load_curriculum_from_pdf(self, pdf_path: Path):
        """Dynamically parses all chapters & sections from the given PDF outline."""
        try:
            parser = FullBookPdfParser(pdf_path)
            curriculum = parser.extract_full_curriculum(min_level=1, max_level=1)
            self.curriculum_sections = curriculum
            self.chunk_options = {}

            # Add all dynamic sections from PDF
            for s in curriculum[:35]:  # Load up to 35 major sections
                label = f"[{s['index']:02d}] {s['title']} (P{s['start_page']}-P{s['end_page']}, {s['page_count']}页)"
                self.chunk_options[s["sec_id"]] = label

            self.chunk_options["all"] = "⚡ 顺序生产全部章节并拼接为长篇大课 (Batch & Stitch Master Course)"
        except Exception as e:
            self.chunk_options = {
                "sec_001_intro": "01 · Programming Model (P20-P30)",
                "sec_002_simt": "02 · Writing SIMT Kernels (P61-P87)",
                "all": "⚡ 全部章节一键生产"
            }

    def _log(self, text: str):
        self.log_textbox.insert("end", text + "\n")
        self.log_textbox.see("end")

    def _update_stage(self, stage_idx: int, text: str):
        self.progress_bar.set((stage_idx + 1) / 5.0)
        self.detail_status.configure(text=text)
        for i, lbl in enumerate(self.stage_labels):
            if i < stage_idx:
                lbl.configure(text_color="#10B981")  # Completed green
            elif i == stage_idx:
                lbl.configure(text_color=COLOR_ACCENT) # Current highlight
            else:
                lbl.configure(text_color=COLOR_TEXT_MUTED)

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

    def _start_pipeline(self):
        if self.is_running:
            return

        # Read config from UI
        pdf_path = Path(self.pdf_entry.get().strip())
        selected_chunk_text = self.chunk_combo.get()
        chunk_key = next((k for k, v in self.chunk_options.items() if v == selected_chunk_text), "01_global_thread_indexing")

        api_key = self.api_key_entry.get().strip()
        voice_str = self.voice_combo.get().split()[0]
        quality_str = self.quality_seg.get()
        quality_map = {
            "480P 预览 (-ql)": "-ql",
            "720P 高清 (-qm)": "-qm",
            "1080P 交付 (-qh)": "-qh"
        }
        quality_flag = quality_map.get(quality_str, "-ql")

        self.is_running = True
        self.btn_run.configure(state="disabled", text="⏳ 正在全自动渲染中...")
        self.status_badge.configure(text="● 正在生成", text_color=COLOR_ACCENT)
        self.btn_play.configure(state="disabled")
        self.btn_srt.configure(state="disabled")
        self.log_textbox.delete("1.0", "end")

        self._log(f"[*] 启动生成任务: {selected_chunk_text}")
        self._log(f"[*] 渲染画质: {quality_str} | 旁白音色: {voice_str}")

        # Start worker thread
        self.worker_thread = threading.Thread(
            target=self._run_worker,
            args=(pdf_path, chunk_key, api_key, voice_str, quality_flag),
            daemon=True
        )
        self.worker_thread.start()

    def _run_worker(self, pdf_path: Path, chunk_key: str, api_key: str, voice: str, quality: str):
        emitter = LogEmitter(self.log_queue)
        old_stdout = sys.stdout
        sys.stdout = emitter

        try:
            # Stage 0: L1 Dynamic Full Book Parser
            self.log_queue.put(("stage", (0, "Layer 1: 正在深度解析 PDF 目录树与章节真实内容...")))
            full_orch = FullBookOrchestrator(pdf_path=pdf_path, api_key=api_key, voice=voice)
            curriculum = full_orch.parser.extract_full_curriculum(min_level=1, max_level=1)

            target_sections = []
            if chunk_key == "all":
                target_sections = curriculum[:10]  # Batch top 10 core chapters
            else:
                matched = [s for s in curriculum if s["sec_id"] == chunk_key]
                if matched:
                    target_sections = matched
                else:
                    # Fallback to curriculum[0] or default
                    target_sections = [curriculum[1] if len(curriculum) > 1 else curriculum[0]]

            produced_videos = []
            total_sections = len(target_sections)

            for idx, sec in enumerate(target_sections, 1):
                sec_id = sec["sec_id"]
                sec_title = sec["title"]
                page_info = f"P{sec.get('start_page')}-P{sec.get('end_page')}"

                self.log_queue.put(("log", f"\n======================================================\n🎬 [{idx}/{total_sections}] 深度全真章节制作: {sec_title} ({page_info})\n======================================================"))

                # Stage 1: Generate Deep PPT Deck
                self.log_queue.put(("stage", (1, f"[{idx}/{total_sections}] Layer 2: 正在根据 PDF 原文提炼高信息密度 PPT 讲稿 ({sec_title})...")))

                # Stage 2 & 3: Dual-Track Production
                self.log_queue.put(("stage", (2, f"[{idx}/{total_sections}] Layer 3 & 4: 正在进行图文幻灯片与 Manim 物理微架构推演渲染 ({quality})...")))
                sec_result = full_orch.produce_section_video(sec, quality=quality)

                final_video = sec_result.get("final_video")
                if final_video and final_video.exists():
                    produced_videos.append(final_video)
                    self.last_produced_video = final_video
                    self.last_produced_srt = config.OUTPUT_DIR / "videos" / f"{sec_id}_subtitles.srt"
                    self.last_produced_ppt = sec_result.get("deck_html")
                    self.log_queue.put(("log", f"[+] 章节深度视频制作完成: {final_video.name}"))
                else:
                    self.log_queue.put(("log", f"[!] 章节渲染异常: {sec_id}"))

            # If batching all, concatenate into a seamless full course
            if chunk_key == "all" and len(produced_videos) > 1:
                self.log_queue.put(("stage", (4, "Layer 5: 正在将全部真实章节视频无损拼接为整书大课 (Full Course Master)...")))
                master_video = full_orch.composer.concatenate_course_videos(produced_videos, output_filename="00_cuda_full_book_master_course.mp4")
                if master_video and master_video.exists():
                    self.last_produced_video = master_video
                    self.log_queue.put(("log", f"\n🏆 [整书系统大课制作完毕] 已成功保存至: {master_video}\n"))

            self.log_queue.put(("finish", True))

        except Exception as e:
            self.log_queue.put(("log", f"[!] 执行过程异常: {str(e)}"))
            self.log_queue.put(("finish", False))
        finally:
            sys.stdout = old_stdout

    def _handle_finish(self, success: bool):
        self.is_running = False
        self.btn_run.configure(state="normal", text="🚀 一键全自动生成微视频")

        if success and self.last_produced_video and self.last_produced_video.exists():
            self.status_badge.configure(text="● 生成完成", text_color="#10B981")
            self.progress_bar.set(1.0)
            self.detail_status.configure(text=f"成片渲染完毕! 位于: {self.last_produced_video.name}")
            self.btn_play.configure(state="normal")
            self.btn_srt.configure(state="normal")
            self._log(f"\n🎉 [成功] 视频已保存至: {self.last_produced_video}\n")
            messagebox.showinfo("生成完成", f"视频已成功生成！\n文件: {self.last_produced_video.name}")
        else:
            self.status_badge.configure(text="● 异常中断", text_color="#EF4444")
            self.detail_status.configure(text="生成中断，请查看日志排查。")

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
    app = CudaStudioApp()
    app.mainloop()


if __name__ == "__main__":
    main()
