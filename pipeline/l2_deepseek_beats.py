"""
Layer 2: DeepSeek Cognitive Bottleneck Extraction & Visual Beat Generation.
Implements Prompt A (Misconception vs Reality) and Prompt B (Visual Beats Sheet).
Supports online DeepSeek API (with JSON mode) and robust offline pedagogical fallback.
"""

import json
import os
import requests
from pathlib import Path
from typing import Dict, Any, List, Optional

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config


# Gold-standard pedagogical templates for offline/zero-config operation
GOLD_STANDARD_BEATS = {
    "01_global_thread_indexing": {
        "conflict": {
            "misconception": "CPU 程序员习惯将 threadIdx.x 视为全局唯一的自增循环变量 i。",
            "reality": "每个 Block 内部的 threadIdx 都是从 0 开始重新计数的，多个 Block 启动时，会有多个 t0 线程同时写入同一个内存物理地址。",
            "why_confusing": "单 Block 测试时完全正常，网格扩展到多 Block 后出现偶发、随机的数据覆盖，Bug 极其隐蔽。",
            "physical_metaphor": "两个不同车间（Block）里工号相同（t0）的工人，同时往同一个储物柜（Slot 0）投递零件引发撞车。"
        },
        "beats": [
            {
                "beat_id": 1,
                "title": "建立直觉假象：单 Block 的平静",
                "layout_zone": "top",
                "visual_action": "顶部浮现代码 'int idx = threadIdx.x;'。屏幕中央显示 Block 0，内部包含 4 个青色圆点(t0-t3)。底部显示 8 个带刻度内存槽位[0]至[7]。圆点 t0 平稳向下投射绿色光标到[0]号槽位，槽位亮起绿色。",
                "narration": "在单块中，threadIdx 看起来就像唯一的循环变量。",
                "pause_buffer": 0.5
            },
            {
                "beat_id": 2,
                "title": "认知冲突爆发：多 Block 物理撞车",
                "layout_zone": "center",
                "visual_action": "屏幕向右扩展，显现 Block 1，同样包含 t0-t3。此时 Block 0 的 t0 与 Block 1 的 t0 同时向下移动，两条光束在[0]号槽位猛烈交汇碰撞。槽位边框瞬间变红，产生剧烈抖动与闪烁，覆盖红色报警光斑。",
                "narration": "但多块并行时，每一个块都有自己的零号线程。",
                "pause_buffer": 0.8
            },
            {
                "beat_id": 3,
                "title": "顿悟重构：物理坐标的全局升维",
                "layout_zone": "top",
                "visual_action": "红色警告消退。顶部代码淡出，居中浮现金色高光公式 'idx = blockIdx.x * blockDim.x + threadIdx.x'。Block 1 整体被金色虚线框选中标注偏移量 '1 * 4'。Block 1 的 t0 编号实时变为 't4'，光束重新精准指向[4]号槽位，所有槽位呈现有序阵列。",
                "narration": "身份不是天生的，是用块偏移量自己算出来的。",
                "pause_buffer": 2.2  # Deliberate Silence for consolidation
            }
        ]
    },
    "02_warp_divergence": {
        "conflict": {
            "misconception": "以为 GPU 上的 if-else 分支能像 CPU 多核那样互不影响、独立全速执行。",
            "reality": "同一 Warp 内的 32 个线程共享同一个指令发射器，遇到分支时必须串行执行：先跑 Branch A（其他线程挂起），再跑 Branch B，吞吐量减半。",
            "why_confusing": "代码计算结果完全正确，但性能评测时 GPU 算力利用率暴跌 50% 以上。",
            "physical_metaphor": "一列全员系在同一根拉杆上的过山车，遇到岔路口必须先走完左轨再倒车走右轨。"
        },
        "beats": [
            {
                "beat_id": 1,
                "title": "SIMT 齐步走的幻象",
                "layout_zone": "center",
                "visual_action": "中央显示一列 4 线程微型 Warp 并排前进，顶部显示 'if (tid % 2 == 0)'。4 个圆点同时向前匀速滑动，代表硬件锁步（Lockstep）执行。",
                "narration": "线程束像齐步走的方阵，本该共享同一个时钟脉冲。",
                "pause_buffer": 0.5
            },
            {
                "beat_id": 2,
                "title": "分支分化：被动的串行等待",
                "layout_zone": "center",
                "visual_action": "方阵遇上 if-else 分支。奇数线程 t1/t3 瞬间变灰并被虚线遮罩锁定，偶数线程 t0/t2 耗时 1.5 秒执行分支 A；随后 t0/t2 变灰冻结，t1/t3 激活执行分支 B，总耗时变为双倍。",
                "narration": "当分歧发生，没有并行跳过，只有互相等待。",
                "pause_buffer": 0.8
            },
            {
                "beat_id": 3,
                "title": "顿悟：时间维度的折叠",
                "layout_zone": "bottom",
                "visual_action": "时间轴进度条被拉长一倍，显示两条串行红色时间块。文字揭示 '执行时间 = 分支A + 分支B'，随后聚拢合成为消除分支后的紧凑单周期绿色方块。",
                "narration": "消除分歧，才是 GPU 榨干算力的真正秘密。",
                "pause_buffer": 2.0
            }
        ]
    },
    "03_shared_memory_bank_conflict": {
        "conflict": {
            "misconception": "以为共享内存像 CPU 高速缓存一样，任何多线程并发寻址都能同时全速读写。",
            "reality": "共享内存硬件被切分成 32 个独立物理 Bank。如果同一个 Warp 内的不同线程访问命中同一个 Bank，硬件将强制排队串行化。",
            "why_confusing": "单步调试时每个值都正确，但评测内存吞吐量时发现速度骤降为原本的 1/2 或 1/4。",
            "physical_metaphor": "32 个并行窗口的办事大厅，当多名客户拥挤在同一个窗口前，只能依次排队办理。"
        },
        "beats": [
            {
                "beat_id": 1,
                "title": "理想并发：1 对 1 物理映射",
                "layout_zone": "center",
                "visual_action": "上方显示 4 个线程 t0-t3，下方显示 4 个绿色 Bank 模块。4 条绿色光束同时垂直射向各自编号匹配的 Bank，1 个时钟周期内全部瞬间完成。",
                "narration": "当每个线程访问不同的 Bank，数据并发一触即发。",
                "pause_buffer": 0.6
            },
            {
                "beat_id": 2,
                "title": "Bank 冲突：被迫串行排队",
                "layout_zone": "center",
                "visual_action": "步长跨度变为 2。t0 与 t2 的光束同时射向 Bank 0 产生剧烈闪烁撞车。Bank 0 亮起红色警报框，t2 被迫等待 t0 读取完毕后才开始第二轮读取。",
                "narration": "一旦跨步访存撞上同一模块，硬件只能强制串行排队。",
                "pause_buffer": 0.8
            },
            {
                "beat_id": 3,
                "title": "顿悟破局：填充错位消除冲突",
                "layout_zone": "top",
                "visual_action": "顶部代码浮现二维数组填充公式 '__shared__ float s[32][33]'。由于多出 1 列填充偏移，所有线程访问自动错开 Bank，全部恢复为绿色并行直连。",
                "narration": "巧妙增加一个单位的填充，就能让并发高速通道重新畅通。",
                "pause_buffer": 2.2
            }
        ]
    },
    "04_coalesced_memory_access": {
        "conflict": {
            "misconception": "以为只要每个线程各读取一个 4 字节 float，总线就只传输 4 字节，访问开销均等。",
            "reality": "GPU 显存物理传输必须对齐 32 字节或 128 字节扇区(Sector)。连续线程访问连续地址只需 1 次合并总线事务(100% 效率)；跨步离散访问会触发多次总线传输并丢弃大部分数据，带宽跌破 10%。",
            "why_confusing": "循环计算逻辑毫无差别，但非合并访问会导致内核执行时间瞬间膨胀 10 倍以上。",
            "physical_metaphor": "快递货车每次送来一整箱(128B)货物，连续线程一次全拿走，跨步线程每次只拿一个就让货车空跑。"
        },
        "beats": [
            {
                "beat_id": 1,
                "title": "连续访存：单次合并事务 100% 吞吐",
                "layout_zone": "center",
                "visual_action": "顶部显示 4 个并排线程 t0-t3，下方显示一根宽阔的 128 字节显存总线通道。4 根绿色光束紧凑汇聚为一道宽光束，单次脉冲瞬间点亮 4 个连续内存槽位。",
                "narration": "连续的线程抓取连续的内存，总线单次事务全额打满。",
                "pause_buffer": 0.6
            },
            {
                "beat_id": 2,
                "title": "跨步离散：总线反复空载奔波",
                "layout_zone": "center",
                "visual_action": "线程访存地址变为 stride=4 离散分布。宽总线被迫进行多次独立传输，大量的内存槽位未被利用而显示为灰色虚影浪费，总线利用率指示标尺暴跌至 25%。",
                "narration": "一旦发生离散跨步，总线只能反复搬运废弃数据。",
                "pause_buffer": 0.8
            },
            {
                "beat_id": 3,
                "title": "顿悟：内存布局必须契合硬件吞吐粒度",
                "layout_zone": "bottom",
                "visual_action": "金色标语浮现 '结构体数组(AoS) -> 数组结构体(SoA)'。内存条重新规整对齐，绿色高光事务块覆盖所有线程，带宽吞吐恢复 100%。",
                "narration": "顺应硬件扇区对齐，才是吞吐暴涨的底层密码。",
                "pause_buffer": 2.2
            }
        ]
    },
    "05_atomic_operations_race_condition": {
        "conflict": {
            "misconception": "以为代码写了 sum += 1，十万个 GPU 线程跑完后结果就一定是十万。",
            "reality": "自增运算在底层由 Read-Modify-Write 三步组成。高并发下多个线程同时读到旧值，计算后互相覆写，绝大多数增量无声丢失，必须由 atomicAdd 硬件排队互斥锁保护。",
            "why_confusing": "单线程或极少线程测试时结果正确，一旦大规模并发，统计数字随机丢失 80% 以上。",
            "physical_metaphor": "多名裁判同时看了一眼记分牌上的 0，各自在草稿纸上加 1 后同时写上去，记分牌最终只显示 1。"
        },
        "beats": [
            {
                "beat_id": 1,
                "title": "并发写冲突：不可控的旧值覆写",
                "layout_zone": "center",
                "visual_action": "中央显示计数器 [0]。两个线程 t0 与 t1 同时读取数字 0，各自在其本地缓存中计算得出 1，随后同时覆写中央计数器，最终计数器仅显示 1，产生惊叹号警告。",
                "narration": "并发读改写不是原子事务，海量更新在覆写中瞬间蒸发。",
                "pause_buffer": 0.6
            },
            {
                "beat_id": 2,
                "title": "原子操作：硬件级排队独占锁",
                "layout_zone": "center",
                "visual_action": "顶部代码变为 'atomicAdd(&counter, 1)'。中央计数器外围浮现金色硬件盾牌，t0 优先进入使计数器变为 1；随后 t1 依序进入变为 2，所有更新无一遗漏。",
                "narration": "呼叫原子指令，硬件为每个线程拉起安全互斥锁。",
                "pause_buffer": 0.8
            },
            {
                "beat_id": 3,
                "title": "顿悟：安全与吞吐的辩证平衡",
                "layout_zone": "bottom",
                "visual_action": "展示分块局部规约(Warp Shuffle/Shared Memory)再全局 Atomic 的两级架构，计数器飞速跃升至 100000 满额。",
                "narration": "先局部合并再原子累加，安全与极速兼得。",
                "pause_buffer": 2.2
            }
        ]
    },
    "06_syncthreads_barrier": {
        "conflict": {
            "misconception": "以为写完共享内存后别的线程就会自然看到，或者以为可以在 if 里面放同步屏障。",
            "reality": "Warp 之间调度异步且不可控，没有 __syncthreads() 就会读出未写完的脏垃圾。若把屏障放入条件分支，未走该分支的线程永不到达，导致整个硬件块永久死锁挂起！",
            "why_confusing": "死锁发生时没有崩溃堆栈，程序直接永远失去响应挂死，极难排查。",
            "physical_metaphor": "旅行团约定集合拍照，如果只让一部分人进暗室集合，剩下的人在门外走掉，大家将永远等不到全员到齐。"
        },
        "beats": [
            {
                "beat_id": 1,
                "title": "异步步调冲突：脏数据读取陷阱",
                "layout_zone": "center",
                "visual_action": "显示线程快慢不一步调，快线程 t0 试图读取 t3 的共享内存槽位，但 t3 尚未完成写入，读取结果显示为乱码红色问号 'NaN'。",
                "narration": "缺少同步屏障，快线程只会抓取未写完的脏数据。",
                "pause_buffer": 0.6
            },
            {
                "beat_id": 2,
                "title": "致命死锁禁忌：分支内屏障挂死硬件",
                "layout_zone": "center",
                "visual_action": "顶部代码显示 'if (tid % 2 == 0) __syncthreads();'。一道红色栅栏降下，只有 t0/t2 抵达，t1/t3 直接绕过离开。栅栏发出蜂鸣报警并显示 '永久死锁 (Deadlock)' 冰冻标志。",
                "narration": "严禁在分歧条件中安插屏障，那会让硬件陷入永恒等待。",
                "pause_buffer": 0.8
            },
            {
                "beat_id": 3,
                "title": "顿悟：全员集合，步调一致",
                "layout_zone": "bottom",
                "visual_action": "屏障移至分支外部公共区。绿色安全屏障降下，所有 4 个线程全部抵达打卡，栅栏平稳抬起，整齐划一进入下一个计算阶段。",
                "narration": "全员步调一致，是并行大厦稳固不倒的基石。",
                "pause_buffer": 2.2
            }
        ]
    }
}


class DeepSeekBeatGenerator:
    def __init__(self, api_key: str = "", base_url: str = ""):
        self.api_key = api_key or config.DEEPSEEK_API_KEY
        self.base_url = base_url or config.DEEPSEEK_BASE_URL
        self.model = config.DEEPSEEK_MODEL
        self.output_dir = config.OUTPUT_DIR / "beats"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _call_deepseek_json(self, system_prompt: str, user_prompt: str) -> Optional[Dict[str, Any]]:
        """Invokes DeepSeek API with strict JSON mode."""
        if not self.api_key:
            return None

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.3
        }

        try:
            resp = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=payload, timeout=45)
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                return json.loads(content)
            else:
                print(f"[Warning] DeepSeek API returned status {resp.status_code}: {resp.text}")
                return None
        except Exception as e:
            print(f"[Warning] DeepSeek API request failed: {e}")
            return None

    def run_prompt_a_conflict(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """Prompt A: Cognitive Conflict Extraction."""
        sys_prompt = (
            "你是一个顶尖的 CUDA 教学架构师。你的任务不是总结知识点，而是找出学习者从 CPU 串行思维"
            "切换到 GPU 并发思维时，最可能在哪一步产生'我的代码为什么不对'的困惑。\n"
            "输出必须为合法 JSON，键名包含：misconception (错误直觉), reality (GPU实际物理行为), "
            "why_confusing (为何隐蔽让人困惑), physical_metaphor (最贴切的物理几何隐喻)。"
        )
        user_prompt = f"分析以下 CUDA 知识切片：\n标题: {chunk['title']}\n核心关注: {chunk['cognitive_focus']}\n代码: {chunk['minimal_code']}"

        result = self._call_deepseek_json(sys_prompt, user_prompt)
        if result:
            return result
        # Fallback to gold standard
        chunk_id = chunk.get("chunk_id", "")
        if chunk_id in GOLD_STANDARD_BEATS:
            return GOLD_STANDARD_BEATS[chunk_id]["conflict"]
        return {
            "misconception": "以为并发线程拥有天然独立的串行执行序列。",
            "reality": "硬件按多层次空间网格分发，共享物理通道或槽位。",
            "why_confusing": "少量线程并发无法暴露竞争条件。",
            "physical_metaphor": "多辆汽车同时争抢唯一的窄车道入口。"
        }

    def run_prompt_b_beats(self, chunk: Dict[str, Any], conflict: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Prompt B: Visual Beat Sheet Generation."""
        sys_prompt = (
            "你是一位 3Blue1Brown 式的数理动画导演。将输入的 CUDA 认知冲突转化为一段 30~45 秒的 Manim 几何动画节拍列表。\n"
            "必须遵守以下铁律：\n"
            "1. 严禁使用任何主观词汇（如'震撼'、'直观'、'优雅'、'清晰'）。\n"
            "2. visual_action 必须描述具象几何图元、相对空间坐标（三区布局：top, center, bottom）、颜色Hex及运动轨迹。\n"
            "3. narration 为旁白文本，每句严格限制在 25 字以内，通俗有力。\n"
            "4. pause_buffer 为该节拍动作与旁白结束后的刻意静音沉淀时间（秒）。在核心揭示时刻必须预留 1.5~2.5 秒。\n"
            "输出 JSON 格式：{\"beats\": [{\"beat_id\": 1, \"title\": \"...\", \"layout_zone\": \"top|center|bottom\", \"visual_action\": \"...\", \"narration\": \"...\", \"pause_buffer\": 1.8}]}"
        )
        user_prompt = f"概念: {chunk['title']}\n认知冲突: {json.dumps(conflict, ensure_ascii=False)}"

        result = self._call_deepseek_json(sys_prompt, user_prompt)
        if result and "beats" in result:
            return result["beats"]

        chunk_id = chunk.get("chunk_id", "")
        if chunk_id in GOLD_STANDARD_BEATS:
            return GOLD_STANDARD_BEATS[chunk_id]["beats"]
        return []

    def generate_for_chunk(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """Runs the complete Layer 2 pipeline for a single chunk."""
        chunk_id = chunk["chunk_id"]
        print(f"[*] Layer 2: Extracting Cognitive Conflict & Visual Beats for {chunk_id}...")

        conflict = self.run_prompt_a_conflict(chunk)
        beats = self.run_prompt_b_beats(chunk, conflict)

        manifest = {
            "chunk_id": chunk_id,
            "title": chunk["title"],
            "conflict": conflict,
            "beats": beats
        }

        out_path = self.output_dir / f"{chunk_id}_beats.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

        print(f"[+] Layer 2 Success: Saved {len(beats)} visual beats to {out_path.name}")
        return manifest


if __name__ == "__main__":
    from pipeline.l1_chunker import CudaChunker
    chunker = CudaChunker()
    chunks = chunker.process_and_save_chunks()
    
    generator = DeepSeekBeatGenerator()
    for ch in chunks[:2]:
        generator.generate_for_chunk(ch)
