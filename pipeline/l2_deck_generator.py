"""
Layer 2 (Enhanced): Dynamic PDF-Driven Lecture Slide Deck Generator.
Parses raw sections of technical documentation (PDF/Markdown), analyzes complexity,
and dynamically generates a multi-slide pedagogical lecture deck (Markdown/JSON).
Each slide contains:
1. slide_id, title, slide_type (title/concept/code/animation/benchmark/summary)
2. key_points (bullet points for visual slide rendering)
3. narration_script (in-depth spoken lecture script, 100-250 words per slide)
4. visual_action (exact Manim or UI layout instructions)
5. est_duration_seconds
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
import requests

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config


# Comprehensive deep-dive slide decks for standard sections
# Demonstrates how a concept naturally expands into 4 to 8 slides (3-6 minutes)
GOLD_STANDARD_DECKS = {
    "01_global_thread_indexing": {
        "concept_id": "01_global_thread_indexing",
        "topic": "CUDA 线程层级模型与全局物理寻址",
        "target_duration_range": "3~5分钟",
        "slides": [
            {
                "slide_id": 1,
                "title": "课程引言：并行硬件的坐标系与心智冲突",
                "slide_type": "title_overview",
                "key_points": [
                    "CPU 循环思维：单个计数器 i 遍历整个数据空间",
                    "GPU 硬件现实：数万物理线程以 Grid/Block 空间网格排布",
                    "核心困惑：为什么单 Block 代码搬到多 Block 会产生静默数据损毁？"
                ],
                "narration_script": (
                    "欢迎来到 CUDA 底层架构深度精讲。在传统的 CPU 编程世界里，我们要处理一段数组，最自然的思维就是写一个 for 循环，"
                    "用一个全局唯一的变量 i，从 0 一直遍历到 N。然而当我们迈入 GPU 的超大规模并行体系时，这种一维线性的思维习惯会成为最致命的陷阱。"
                    "GPU 并不会为你维护一个自动递增的全局索引。相反，硬件将成千上万的物理线程切分成了网格 Grid 和线程块 Block。"
                    "如果对这一空间层级缺乏透彻理解，你的代码往往会在单块测试时完美运行，而一旦增加数据规模、启动多块网格，就会陷入随机覆写的深渊。"
                ),
                "visual_spec": {
                    "layout": "header_and_bullets",
                    "header_title": "CUDA 线程层级模型与全局寻址",
                    "header_subtitle": "从 CPU 串行循环到 GPU 空间升维",
                    "code_badge": "d_out[i] = data[i];  // CPU 模式 vs GPU 空间映射",
                    "active_elements": ["Grid", "Block", "Thread"]
                }
            },
            {
                "slide_id": 2,
                "title": "直觉陷阱：单 Block 假象与局部坐标覆盖",
                "slide_type": "code_misconception",
                "key_points": [
                    "初学者直觉：误以为 threadIdx.x 是全局唯一的",
                    "单 Block 启动 (<<<1, 4>>>)：代码运行毫无瑕疵",
                    "多 Block 启动 (<<<2, 4>>>)：每个 Block 内部各自拥有独立的 t0~t3"
                ],
                "narration_script": (
                    "我们来看这段看似无害的核函数代码。许多初学者写下了 int idx = threadIdx.x，并直接用它去访问显存数组。"
                    "如果你的启动配置是 1 个 Block 包含 4 个线程，那么 threadIdx.x 确实是从 0 到 3，与显存槽位一一对应，测试结果完全正确。"
                    "但请注意，threadIdx 只是线程在所属 Block 内部的'局部工号'！当我们将配置扩展为 2 个 Block 时，Block 0 拥有自己的 0 号到 3 号线程，"
                    "而 Block 1 同样拥有自己的 0 号到 3 号线程。硬件并不会因为有两个车间就自动给第二个车间的工人编上 4 号工号。"
                ),
                "visual_spec": {
                    "layout": "code_and_hardware_demo",
                    "code_badge": "int idx = threadIdx.x; // 致命局部坐标误用",
                    "show_blocks": 1,
                    "highlight": "threadIdx_local"
                }
            },
            {
                "slide_id": 3,
                "title": "硬件物理机理：多线程块并发覆写碰撞",
                "slide_type": "manim_physics_demo",
                "key_points": [
                    "Block 0 的 t0 与 Block 1 的 t0 同时发射访存请求",
                    "两条内存总线事务同时锁定显存 [0] 号物理槽位",
                    "非原子写冲突：后到达者覆盖先到达者，前序计算成果完全丢失"
                ],
                "narration_script": (
                    "现在，让我们将目光投向 GPU 的物理微架构。当两个 Block 同时并发运行时，Block 0 的 0 号线程和 Block 1 的 0 号线程，"
                    "它们计算出来的 idx 都是 0。这意味着它们会在同一个时间窗口内，向显存物理地址 0 发起写入请求！"
                    "屏幕中央我们可以看到，两条光束同时激射向同一个内存单元。由于没有互斥保护，硬件总线产生了严重的写冲突。"
                    "先到达的线程写入的数据，瞬间被后到达的线程强行冲刷抹去。这就是为什么许多并行程序的 Bug 具有随机性和不可重现性——它完全取决于硬件执行单元的微观调度先手。"
                ),
                "visual_spec": {
                    "layout": "collision_animation",
                    "show_blocks": 2,
                    "animate_collision": True,
                    "target_slot": 0
                }
            },
            {
                "slide_id": 4,
                "title": "坐标升维：块偏移与线性基底计算",
                "slide_type": "math_architecture_resolution",
                "key_points": [
                    "工号独立，车间独立：引入 blockIdx.x 与 blockDim.x",
                    "全局寻址公式：全局ID = 所在块编号 × 块尺寸 + 块内局部偏移",
                    "严格一维连续映射：确保每个物理线程获得全宇宙唯一的身份证"
                ],
                "narration_script": (
                    "要彻底瓦解这种物理碰撞，核心在于完成从'局部相对坐标'到'全局绝对物理坐标'的数学升维。"
                    "在 CUDA 硬件体系中，每一个线程的全局身份，不是硬件直接赐予的，而是通过空间基底公式自己计算出来的。"
                    "公式非常优美而直观：全局索引等于 blockIdx.x 乘以 blockDim.x，再加上 threadIdx.x。"
                    "其中，blockIdx.x 是车间编号，blockDim.x 是每个车间的定员规模。两者的乘积，就是当前车间在整个显存流水线中的全局起始偏移量。"
                    "再加上本车间内的相对工号 threadIdx，即可获得在整个显存大空间中独一无二、绝不撞车的物理指针。"
                ),
                "visual_spec": {
                    "layout": "math_formula_and_resolved_grid",
                    "code_badge": "int idx = blockIdx.x * blockDim.x + threadIdx.x;",
                    "show_blocks": 2,
                    "show_resolved_mapping": True
                }
            },
            {
                "slide_id": 5,
                "title": "总结沉淀：多维扩展与工程边界检查",
                "slide_type": "summary_best_practice",
                "key_points": [
                    "黄金定律：全局 ID 是 GPU 空间寻址的基石",
                    "维度延伸：二维 (blockIdx.y * gridDim.x) 与三维体积展开",
                    "边界防线：if (idx < N) 永远是内存越界访问的第一道保命盾牌"
                ],
                "narration_script": (
                    "通过本小节的透彻推演，我们建立起了一个不可动摇的 GPU 并行心智模型。"
                    "第一，永远不要假定局部变量具有全局意义；第二，当我们将网格推广到二维图像或者三维流体仿真时，同样的基底累加逻辑依然适用，"
                    "只需将每行的块偏移量与线程行偏移量依次折算。最后永远不要忘记，在核函数的第一行加上 if (idx < N) 的越界拦截守卫。"
                    "这不仅保护了显存安全，更是构建大型鲁棒 CUDA 系统必备的工程肌肉记忆。"
                ),
                "visual_spec": {
                    "layout": "summary_and_checklist",
                    "code_badge": "if (idx < N) { d_out[idx] = ...; }",
                    "checklist": [
                        "确认 Block 规模是否被整除",
                        "确认全局索引是否已加上块偏移",
                        "核函数头部强制添加越界安全检查"
                    ]
                }
            }
        ]
    }
}


class LectureDeckGenerator:
    """Generates structured PPT-style lecture decks from technical documentation chunks."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or config.DEEPSEEK_API_KEY
        self.output_dir = config.OUTPUT_DIR / "decks"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_deck_for_chunk(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """Generates dynamic multi-slide lecture deck based on section depth and content."""
        chunk_id = chunk["chunk_id"]
        deck_file = self.output_dir / f"{chunk_id}_deck.json"

        # Check local cache first
        if deck_file.exists():
            try:
                with open(deck_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

        # If online DeepSeek is available, prompt it to create custom dynamic-length deck
        if self.api_key:
            online_deck = self._call_deepseek_deck_builder(chunk)
            if online_deck and len(online_deck.get("slides", [])) >= 3:
                self._save_deck(online_deck, deck_file)
                return online_deck

        # Fallback to high-density gold standard deck or dynamic algorithmic synthesizer
        deck = self._synthesize_pedagogical_deck(chunk)
        self._save_deck(deck, deck_file)
        return deck

    def _save_deck(self, deck: Dict[str, Any], deck_file: Path):
        with open(deck_file, "w", encoding="utf-8") as f:
            json.dump(deck, f, ensure_ascii=False, indent=2)
        print(f"[+] LectureDeckGenerator: Saved {len(deck.get('slides', []))}-slide deck in {deck_file.name}")

    def _synthesize_pedagogical_deck(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """Algorithmic multi-slide pedagogical deck synthesis tailored to chunk complexity."""
        chunk_id = chunk["chunk_id"]
        if chunk_id in GOLD_STANDARD_DECKS:
            return GOLD_STANDARD_DECKS[chunk_id]

        title = chunk.get("title", chunk_id)
        cognitive_focus = chunk.get("cognitive_focus", "")
        code = chunk.get("minimal_code", "")
        pdf_context = chunk.get("pdf_context_snippet", "")

        slides = [
            {
                "slide_id": 1,
                "title": f"专题解析：{title}",
                "slide_type": "title_overview",
                "key_points": [
                    f"核心探究：{chunk.get('section_ref', 'CUDA Programming Guide')}",
                    "心智模型转变：突破传统 CPU 串行直觉",
                    "本讲目标：从微架构机理彻底吃透底层运行规律"
                ],
                "narration_script": (
                    f"各位开发者大家好，本节我们将深入探讨《CUDA 编程指南》中的关键架构主题：{title}。"
                    f"在许多初学者的认知中，往往会将这部分机理简单化处理，从而埋下严重的性能或逻辑缺陷。"
                    f"今天我们将拆解其物理原貌，帮助大家建立起稳固的底层认知直觉。"
                ),
                "visual_spec": {
                    "layout": "header_and_bullets",
                    "header_title": title,
                    "code_badge": chunk.get("keywords", ["CUDA"])[0] if chunk.get("keywords") else "CUDA"
                }
            },
            {
                "slide_id": 2,
                "title": "直觉陷阱与认知断层剖析",
                "slide_type": "code_misconception",
                "key_points": [
                    "典型直觉误区：容易按照传统串行范式理解硬件行为",
                    "微观缺陷：在多线程并发时引发未定义状态",
                    "隐蔽表现：数据随机损坏或执行时间异常膨胀"
                ],
                "narration_script": (
                    f"首先看这个概念在实践中最容易引发的误解。{cognitive_focus}"
                    f"这种认知与 GPU 的实际物理运作存在巨大鸿沟。如果直接套用普通思维编写内核，"
                    f"程序往往表面上能跑通，但在高并发或者压力测试下就会暴露严重缺陷。"
                ),
                "visual_spec": {
                    "layout": "code_and_hardware_demo",
                    "code_badge": code[:100].replace("\n", " ") if code else "kernel<<<grid, block>>>()"
                }
            },
            {
                "slide_id": 3,
                "title": "GPU 物理机理与硬件微架构演变",
                "slide_type": "manim_physics_demo",
                "key_points": [
                    "硬件实体交互：线程束、指令单元与物理显存",
                    "底层排队与冲突：硬件强制串行化或总线空载",
                    "性能代价：算力利用率或显存吞吐断崖式下跌"
                ],
                "narration_script": (
                    "让我们通过动态可视化镜头，深入观察芯片内部究竟发生了什么。"
                    "当成千上万个线程同时被调度到流式多处理器（SM）时，每一个时钟脉冲都在严格受制于硬件的物理布线与逻辑规则。"
                    "如果访存或指令分支违背了硬件规则，执行管线就会被迫暂停，等待周期急剧拉长。"
                ),
                "visual_spec": {
                    "layout": "collision_animation",
                    "code_badge": code if code else ""
                }
            },
            {
                "slide_id": 4,
                "title": "架构破局：工程最佳实践与优化范式",
                "slide_type": "math_architecture_resolution",
                "key_points": [
                    "重构心智模型：顺应 GPU 硬件物理偏好",
                    "标准工程解法：使用对齐、填充或原子排队",
                    "极速释放：恢复 100% 满额硬件吞吐"
                ],
                "narration_script": (
                    "要彻底解决这一痛点，我们必须遵循 NVIDIA 官方推荐的架构范式进行重构。"
                    "通过重组数据排布、或者调整线程分发逻辑，我们可以让所有并发动作完全契合芯片的设计初衷，"
                    "既保证了算法的绝对正确性，又能彻底榨干每一个计算单元的澎湃算力。"
                ),
                "visual_spec": {
                    "layout": "math_formula_and_resolved_grid",
                    "code_badge": code.split("\n\n")[-1] if "\n\n" in code else code
                }
            },
            {
                "slide_id": 5,
                "title": "全景沉淀：规约总结与避坑检查表",
                "slide_type": "summary_best_practice",
                "key_points": [
                    "核心记忆要点：建立三维立体硬件图式",
                    "代码走查规则：检查内存、指令与同步依赖",
                    "通向高性能：写出符合工业级标准的高性能内核"
                ],
                "narration_script": (
                    f"总结这一讲的内容。掌握了{title}的本质，你就掌握了写出工业级稳健 CUDA 代码的关键一把钥匙。"
                    f"在日后的实际工程开发中，请随时回溯今天所推演的几何模型，"
                    f"让代码始终运行在最快、最平稳的高速公路上。"
                ),
                "visual_spec": {
                    "layout": "summary_and_checklist"
                }
            }
        ]

        return {
            "concept_id": chunk_id,
            "topic": title,
            "target_duration_range": "3~5分钟",
            "slides": slides
        }

    def _call_deepseek_deck_builder(self, chunk: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Invokes DeepSeek API to generate dynamic-length multi-slide lecture deck based on section text."""
        url = f"{config.DEEPSEEK_BASE_URL.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        prompt = f"""你是一名资深高性能计算教学专家与技术演讲大师。
请根据以下来自《CUDA Programming Guide》的技术片段，不要写空泛的短视频脚本，而是生成一套用于深入讲透该概念的【专业教学 PPT 幻灯片讲稿 (Slide Deck)】。
每套讲稿必须根据内容的技术深度，动态拆分为 4 到 7 张幻灯片（总讲授时长 3 到 5 分钟）。

【概念标题】: {chunk.get('title')}
【参考章节】: {chunk.get('section_ref')}
【核心认知冲突】: {chunk.get('cognitive_focus')}
【代码示例】:
{chunk.get('minimal_code')}

【PDF原文摘要】:
{chunk.get('pdf_context_snippet', '')[:1200]}

【严格输出 JSON 格式要求】:
{{
  "concept_id": "{chunk.get('chunk_id')}",
  "topic": "{chunk.get('title')}",
  "target_duration_range": "3~5分钟",
  "slides": [
    {{
      "slide_id": 1,
      "title": "幻灯片标题",
      "slide_type": "title_overview | code_misconception | manim_physics_demo | math_architecture_resolution | summary_best_practice",
      "key_points": ["核心要点1", "核心要点2", "核心要点3"],
      "narration_script": "本页幻灯片的讲师口播讲稿，字数在150字到250字之间，深入浅出、条理清晰地讲透本页内容，坚决杜绝一句话概括。",
      "visual_spec": {{
        "layout": "header_and_bullets | code_and_hardware_demo | collision_animation | math_formula_and_resolved_grid | summary_and_checklist",
        "code_badge": "代码关键行"
      }}
    }}
  ]
}}
"""
        payload = {
            "model": config.DEEPSEEK_MODEL,
            "messages": [
                {"role": "system", "content": "You are a world-class parallel computing educator and slide deck architect. Always respond with pure JSON."},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.4
        }

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=45)
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                return json.loads(content)
        except Exception as e:
            print(f"[Warning] DeepSeek Deck builder error: {e}")
        return None


if __name__ == "__main__":
    from pipeline.l1_chunker import CudaChunker
    c = CudaChunker()
    chunks = c.process_and_save_chunks()
    gen = LectureDeckGenerator()
    deck = gen.generate_deck_for_chunk(chunks[0])
    print(f"\n[Success] Generated {len(deck['slides'])} slides for {deck['topic']}")
