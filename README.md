# CudaStudy: Technical PDF to High-Density Video Studio

> **Transform System Technical Documentation (e.g., CUDA C++ Programming Guide) into Structured Lecture Slide Decks & 3Blue1Brown-style Manim Microarchitecture Simulations.**

---

## 🌟 Key Features

1. **Full-Book PDF Outline Parser**: Recursively extracts the complete Table of Contents, section hierarchy, page ranges, and verbatim C++/CUDA code blocks from any technical document.
2. **Deep Pedagogical Deck Generator**: Dynamically synthesizes high-density PPT slide decks (Markdown & interactive HTML), complete with bullet points and comprehensive spoken lecture scripts (150~280 words per slide).
3. **Dual-Track Video Engine**:
   - **Slide Track**: High-resolution dark-themed technical slides with deliberate 3.5s cognitive digestion buffers.
   - **Manim Physics Simulation Track**: 3Blue1Brown-style mathematical/geometric animations for hardware race conditions, Warp divergence, Bank conflicts, memory coalescing, and barriers.
4. **Standalone Windows Desktop UI**: Packaged zero-dependency desktop application (`CudaVideoStudio.exe`) with real-time log streaming and one-click lecture generation.

---

## 🚀 Quick Start

### 1. Environment Setup
```bash
# Clone the repository
git clone https://github.com/maleRjc/CudaStudy.git
cd CudaStudy

# Install dependencies using Python 3.11+
python -m venv .venv
.venv\Scripts\activate
pip install manim edge-tts customtkinter pypdf av pillow requests
```

### 2. Launch GUI Studio
```bash
python app_gui.py
```

### 3. Pipeline Architecture
```text
PDF Document
    │
    ▼
Layer 1: FullBookPdfParser (Table of Contents & Page Ranges)
    │
    ▼
Layer 2: DeepPedagogicalDeckGenerator (Structured PPT & Script)
    │
    ▼
Layer 3: AudioTimingEngine (Edge-TTS Speech & Microsecond Clock)
    │
    ▼
Layer 4: Dual-Track Visual Engine (PPT Slide Cards + Manim Scenes)
    │
    ▼
Layer 5: VideoComposer (FFmpeg Muxing, Subtitles & Master Course Stitching)
```

---

## 📄 License
MIT License.
