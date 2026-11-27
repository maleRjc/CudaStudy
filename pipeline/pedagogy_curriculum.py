# -*- coding: utf-8 -*-
"""
Pedagogical Curriculum for Zero-Foundation Learners (面向零基础小白的教学重构库).

严格依据《CUDA原理与实现教学视频项目实施文档.docx》与《CUDA C++ Programming Guide 13.3》编写。
核心准则：
1. 【说人话、小学生都能懂】：拒绝一切未经解释的高深学术黑话与概念堆砌。
2. 【六步教学法闭环】：
   - 提出直观问题（小白疑问）
   - 生活通俗大比方（老教授vs小学生、大巴车、班级教室、讲台黑板、顺丰快递）
   - 概念精准映射（硬件真实机制）
   - 白话逐行拆解代码（解释每个关键字的由来）
   - 动态推演分镜（让不可见的过程可视化）
   - 一句话心法与小白避坑自测
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


PEDAGOGICAL_MASTER_DECKS: Dict[str, Dict[str, Any]] = {
    # =========================================================================
    # 01. Introduction: 为什么需要 GPU？CPU 和 GPU 的本质区别
    # =========================================================================
    "sec_001_introduction": {
        "sec_id": "sec_001_introduction",
        "topic": "为什么需要 GPU？CPU 与 GPU 的本质区别",
        "page_range": "P19-P19",
        "page_count": 1,
        "source": "pedagogy_zero_foundation",
        "slides": [
            {
                "slide_id": 1,
                "title": "小白之问：有了顶级 CPU，为什么还要买显卡？",
                "slide_type": "title_overview",
                "key_points": [
                    "疑问：我的 CPU 已经有 8 核 4.5GHz，为什么算 AI 和图像时它慢得像乌龟？",
                    "本质：CPU 追求单任务极致极速（低延迟），GPU 追求海量任务一起算（高吞吐）。",
                    "芯片晶体管取舍：CPU 把面积留给大脑袋（缓存与控制），GPU 铺满了算术手（ALU）。"
                ],
                "narration_script": "很多初学者刚接触高性能计算时，心里都会有一个巨大的疑问：我的电脑已经配了最新款的顶级 CPU，主频高达四点几吉赫兹，平时玩系统极其流畅，为什么一跑大模型或者渲染视频，CPU 就卡得动弹不得，非要我们额外掏几千块钱去买一张独立显卡呢？显卡到底有什么神奇的超能力？今天这一节，我们不背枯燥的教科书，用三分钟彻底搞懂 CPU 与 GPU 的本质区别，打开异构并行计算的大门！",
                "visual_spec": {
                    "layout": "collision_animation",
                    "code_badge": "",
                    "scene_plan": {
                        "schema": "plan-v2",
                        "kind": "boxes",
                        "slide_id": 1,
                        "title": "小白之问：CPU 与 GPU 的核心使命不同",
                        "subtitle": "低延迟（单人飞奔） vs 高吞吐（万人齐步走）",
                        "figure": {
                            "nodes": [
                                {"id": "cpu", "label": "CPU 核心 (低延迟超级专家)"},
                                {"id": "cache", "label": "超大缓存 L3 Cache (防断货)"},
                                {"id": "gpu", "label": "GPU 核心阵列 (海量微型计算器)"},
                                {"id": "vram", "label": "高带宽显存 VRAM (高速输送带)"}
                            ],
                            "edges": [
                                ["cpu", "cache", "极快读取"],
                                ["gpu", "vram", "极宽总线吞吐"]
                            ]
                        },
                        "steps": [
                            {
                                "heading": "CPU：追求单任务极致低延迟",
                                "bullets": ["单核极其强大，擅长复杂的逻辑判断和操作系统调度。"],
                                "focus": [0, 1],
                                "narration": "CPU 就像一位顶级的全能数学教授，他的个人能力强悍到极点，擅长做复杂的分支判断和操作系统调度，核心目标是尽可能快地搞定手头这一个任务。"
                            },
                            {
                                "heading": "GPU：追求海量数据同时吞吐",
                                "bullets": ["数千个小核心同时动笔，擅长几百万像素或矩阵的简单乘加。"],
                                "focus": [2, 3],
                                "narration": "而 GPU 的目标截然不同，它不追求单个任务几纳秒跑完，它追求的是同时指挥成千上万个小核心一起开工，靠庞大的队伍瞬间吞吐海量数据。"
                            },
                            {
                                "heading": "硬件取舍：谁动了我的晶体管？",
                                "bullets": ["CPU 晶体管大量做成缓存和分支预测，GPU 全做成了绿色计算单元。"],
                                "focus": [0, 2],
                                "narration": "这就决定了芯片底层的晶体管分配：CPU 把大量面积都让给了超大缓存和分支预测器，而 GPU 则把几乎所有的硅片空间，全部铺满了密密麻麻的绿色计算单元！"
                            }
                        ]
                    }
                }
            },
            {
                "slide_id": 2,
                "title": "生活大比方：老教授 vs 5000 个小学生",
                "slide_type": "metaphor_sketch",
                "key_points": [
                    "CPU 是大学老教授：精通微积分和奥数，但他只有一个人，做题只能一道道来。",
                    "GPU 是 5000 个小学生：只会最简单的加减乘除，但 5000 个人同时坐在大礼堂里动笔。",
                    "算一千万道加减法：老教授做完要累趴下，5000 个小学生一人一道，几秒钟全班交卷！"
                ],
                "narration_script": "为了让大家彻底拥有物理直觉，我们打一个经典的生活大比方。你可以把 CPU 想象成一位顶级大学的老教授，他精通微积分、高等代数，逻辑推导滴水不漏。但老教授只有一个人，如果你让他去解一道复杂的逻辑大题，他两秒钟就能解开。可如果你现在交给他一千万道小学一年级的加法题，老教授就算手速再快，一道一道做下来，也得累得晕过去。那 GPU 是什么呢？GPU 相当于大礼堂里坐着的 5000 个小学生！小学生不会高深的微积分，他们每个人手里拿着一根铅笔，只会做加减乘除。面对这一千万道加法题，老教授发号施令，5000 个小学生每人认领一道，同时动笔！一秒钟做完 5000 道，几秒钟时间，一千万道题全部交卷！这就是为什么在 AI、图形渲染这些纯粹由简单加减乘除组成的数据密集型任务面前，GPU 能够形成对 CPU 几百倍的碾压！",
                "visual_spec": {
                    "layout": "collision_animation",
                    "code_badge": "",
                    "scene_plan": {
                        "schema": "plan-v2",
                        "kind": "compare",
                        "slide_id": 2,
                        "title": "生动类比：算力哲学的根本分野",
                        "subtitle": "老教授串行单打独斗 vs 小学生海量并发军团",
                        "figure": {
                            "left": {
                                "title": "CPU 模型：1 位顶级数学老教授",
                                "lines": [
                                    "智商极高：精通微积分与分支逻辑",
                                    "串行解题：一道接着一道算",
                                    "面对 1000 万道加法：需要耗时数小时",
                                    "瓶颈：双拳难敌四手"
                                ]
                            },
                            "right": {
                                "title": "GPU 模型：5000 位勤劳的小学生",
                                "lines": [
                                    "单兵简单：只会基础加减乘除",
                                    "海量并发：5000 人同时落笔",
                                    "面对 1000 万道加法：几秒钟交卷",
                                    "优势：极致的大规模数据吞吐"
                                ]
                            }
                        },
                        "steps": [
                            {
                                "heading": "第一步：审视任务特性",
                                "bullets": ["如果任务是复杂逻辑决策，CPU 是绝对王者。"],
                                "focus": [0],
                                "narration": "在编程世界里，先看你的任务是什么。如果任务是操作系统调度、复杂数据库事务，需要极高智商的老教授也就是 CPU 出马。"
                            },
                            {
                                "heading": "第二步：面对海量独立计算",
                                "bullets": ["当任务由数百万个独立加减法组成，GPU 完胜。"],
                                "focus": [1],
                                "narration": "但图像的几百万个像素、AI 模型的千亿参数乘法，全是彼此互不干扰的加减乘除。这时候派 5000 个小学生同时动笔，效率就会瞬间起飞！"
                            },
                            {
                                "heading": "第三步：确立异构协同心智",
                                "bullets": ["老教授当总指挥，小学生干苦力活，这就是异构计算！"],
                                "focus": [0, 1],
                                "narration": "所以现代计算机的最佳拍档诞生了：老教授 CPU 在办公室负责统筹大局发号施令，小学生 GPU 在工厂里负责批量干体力活，这就是异构协同！"
                            }
                        ]
                    }
                }
            },
            {
                "slide_id": 3,
                "title": "从图形到通用计算：CUDA 到底革了什么命？",
                "slide_type": "concept_breakdown",
                "key_points": [
                    "过去：GPU 只是用来给显示器画 3D 游戏的（固定渲染管线）。",
                    "痛点：早年想用显卡算数学，必须把数据伪装成三角形和像素颜色，极其痛苦。",
                    "2006 年 CUDA 诞生：NVIDIA 彻底打通壁垒，让程序员用 C/C++ 就能直接指挥小学生！"
                ],
                "narration_script": "既然显卡算数这么厉害，为什么直到 2006 年大家才大规模用它来算科学计算和人工智能呢？因为在早期，GPU 只是个纯粹的画图工人，硬件被死死固定在画三角形和给像素涂颜色的流程里。那时候聪明的科学家们如果想用显卡算一个矩阵乘法，简直像在演特务电影：他们必须把数字伪装成像素的红绿蓝颜色值，把加减乘除伪装成图形渲染着色器，代码写得极其痛苦，还容易出错。2006 年，NVIDIA 掌门人黄仁勋做出了一个价值百亿美元的豪赌，正式推出了 CUDA 架构！CUDA 的出现彻底砸碎了图形画图的铁笼子，它直接给开发者提供了熟悉的 C/C++ 编程接口，让我们终于能够像写普通程序一样，直接用代码指挥显卡里成千上万个核心进行通用数学计算！这一场革命，直接奠定了今天深度学习和大模型繁荣的基石。",
                "visual_spec": {
                    "layout": "collision_animation",
                    "code_badge": "",
                    "scene_plan": {
                        "schema": "plan-v2",
                        "kind": "timeline",
                        "slide_id": 3,
                        "title": "GPU 演进之路：从专用画图器到通用算力霸主",
                        "subtitle": "固定图形渲染 → 可编程着色器 → 2006 CUDA 通用革命",
                        "figure": {
                            "rows": [
                                {
                                    "label": "1999 以前：固定画图",
                                    "segments": [{"start": 0.0, "end": 3.0, "label": "纯硬件固定管线，只能画三角形"}]
                                },
                                {
                                    "label": "2003 时代：伪装渲染",
                                    "segments": [{"start": 2.5, "end": 6.5, "label": "GPGPU 极客时代：数字伪装成像素颜色"}]
                                },
                                {
                                    "label": "2006 至今：CUDA 时代",
                                    "segments": [{"start": 5.5, "end": 10.0, "label": "CUDA 诞生：原生 C/C++ 通用并行计算"}]
                                }
                            ]
                        },
                        "steps": [
                            {
                                "heading": "第一阶段：固定画图工具人",
                                "bullets": ["显卡只懂顶点变换和像素光照，无法做通用数学。"],
                                "focus": [0],
                                "narration": "早期的显卡硬件电路是焊死的，只认三维坐标和光照公式，外界根本无法指挥它做其他任何数学运算。"
                            },
                            {
                                "heading": "第二阶段：披着画图马甲的极客运算",
                                "bullets": ["极客把数据伪装成纹理颜色，用像素着色器算数学。"],
                                "focus": [1],
                                "narration": "到了千禧年初期，图形管线有了可编程着色器，极客们把数据伪装成图像纹理偷偷算数学，但开发极其晦涩艰难。"
                            },
                            {
                                "heading": "第三阶段：CUDA 让显卡成为通用超级计算机",
                                "bullets": ["通用计算独立于图形接口，点燃全球 AI 与深度学习革命。"],
                                "focus": [2],
                                "narration": "直到 2006 年 CUDA 横空出世，显卡脱胎换骨成为通用并行加速器，正式拉开了全球 AI 计算大航海时代的序幕！"
                            }
                        ]
                    }
                }
            },
            {
                "slide_id": 4,
                "title": "一句话记住本质与小白课后自测",
                "slide_type": "summary_best_practice",
                "key_points": [
                    "极简口诀：复杂串行找老教授(CPU)，海量简单活找小学生(GPU)！",
                    "核心指标：CPU 专攻低延迟（单任务极快），GPU 专攻高吞吐（总数据量极大）。",
                    "小白自测：如果一个任务只有 5 行代码但包含 10 个层层嵌套的 if-else，该用 CPU 还是 GPU？"
                ],
                "narration_script": "学完这一节，大家在脑海中只需要牢牢印刻两句话。第一句心智口诀：复杂串行找老教授 CPU，海量并发简单活找小学生 GPU！第二句微架构真相：CPU 把晶体管用来做大缓存和复杂预测以降低延迟，GPU 把晶体管全部铺成绿色计算核心以拉满吞吐。最后留给大家一个 5 秒钟就能想出答案的小自测题：如果你的程序只有区区 5 行代码，但是里面包含 10 个层层嵌套的 if-else 复杂条件跳转，后一步完全依赖前一步的结果，你觉得这时候应该派 CPU 上场，还是派 GPU 上场呢？答案显而易见：这种需要高超逻辑推导和快速反应的任务，老教授 CPU 两秒钟就能搞定，派小学生 GPU 只能在原地打架！带着这种清醒的认知，下节课我们将带大家认识 CPU 和 GPU 是如何在物理总线上配合干活的！",
                "visual_spec": {
                    "layout": "collision_animation",
                    "code_badge": "",
                    "scene_plan": {
                        "schema": "plan-v2",
                        "kind": "boxes",
                        "slide_id": 4,
                        "title": "本讲心智清单与小白速记口诀",
                        "subtitle": "认清任务本质，合理分工协同",
                        "figure": {
                            "nodes": [
                                {"id": "n1", "label": "CPU 核心领域：复杂逻辑 / 低延迟 / 操作系统"},
                                {"id": "n2", "label": "GPU 核心领域：矩阵运算 / 高吞吐 / 图像与AI"},
                                {"id": "n3", "label": "黄金口诀：教授主控指方向，万人工人齐落笔"}
                            ],
                            "edges": [
                                ["n1", "n3", "发令"],
                                ["n2", "n3", "执行"]
                            ]
                        },
                        "steps": [
                            {
                                "heading": "复盘 1：延迟导向 vs 吞吐导向",
                                "bullets": ["不再把核多当做唯一指标，看清芯片解决的核心矛盾。"],
                                "focus": [0],
                                "narration": "永远记住：CPU 是延迟导向，为单线程极速而生；GPU 是吞吐导向，为海量并行数据而生。"
                            },
                            {
                                "heading": "复盘 2：自测题揭晓",
                                "bullets": ["复杂嵌套分支：CPU 完胜！因为小学生最怕各走各的分岔路。"],
                                "focus": [1],
                                "narration": "刚才的小白自测题答案就是 CPU！小学生最怕遇到分支分岔，下一节我们将用大巴车的比喻揭开这个惊天秘密。"
                            },
                            {
                                "heading": "复盘 3：异构计算初识完毕",
                                "bullets": ["恭喜你迈出了 CUDA 体系结构的第一步，轻松建立第一层心智！"],
                                "focus": [2],
                                "narration": "恭喜你！不用看任何天书公式，你已经完全吃透了 GPU 计算最底层的存在哲学。下节课我们继续进阶！"
                            }
                        ]
                    }
                }
            }
        ]
    },

    # =========================================================================
    # 02. Programming Model: Thread、Block、Grid 三者关系与全局索引推导
    # =========================================================================
    "sec_002_programming_model": {
        "sec_id": "sec_002_programming_model",
        "topic": "Thread、Block、Grid 组织模型与全局索引计算",
        "page_range": "P20-P30",
        "page_count": 11,
        "source": "pedagogy_zero_foundation",
        "slides": [
            {
                "slide_id": 1,
                "title": "小白之惑：既然有几千个核心，为什么不直接启动线程？",
                "slide_type": "title_overview",
                "key_points": [
                    "疑问：GPU 既然有几万个线程，为什么不能简单写'启动一万个线程'？",
                    "困扰：手册里的 Thread、Block、Grid 到底是什么关系？",
                    "核心揭秘：GPU 硬件芯片是由一个个独立的工厂车间（SM）组成的，必须分班组管理。"
                ],
                "narration_script": "大家在翻看任何一本 CUDA 教程时，最先迎面砸来的往往是三个词：Thread、Block、Grid，以及一个让人头晕脑胀的坐标乘法公式。很多初学者一头雾水：既然 GPU 里有几千个核心，我想算一千万个数据，为什么不能直接在代码里写‘启动一千万个线程’呢？为什么要大费周折地把线程先打包成 Block，再把 Block 拼成 Grid？这不是脱裤子放屁多此一举吗？今天这一节，我们用学校班级的生活案例，三分钟彻底搞懂这三层组织结构，顺便把那个号称初学者第一大噩梦的索引公式彻底拆解得明明白白！",
                "visual_spec": {
                    "layout": "collision_animation",
                    "code_badge": "",
                    "scene_plan": {
                        "schema": "plan-v2",
                        "kind": "grid",
                        "slide_id": 1,
                        "title": "软件层级抽象：Grid → Block → Thread",
                        "subtitle": "年级（整个任务） → 班级车间（协同单元） → 学生个人（计算线程）",
                        "figure": {
                            "rows": 4,
                            "cols": 8,
                            "labels": [f"T{i}" for i in range(32)]
                        },
                        "steps": [
                            {
                                "heading": "第 1 层：Thread 线程（具体的工人）",
                                "bullets": ["每一个线程负责拿起笔，计算一个具体的数据元素。"],
                                "focus": [0],
                                "narration": "最小的单元是 Thread，也就是具体的某一个工人。他负责拿出草稿纸，算一个具体的加法或者像素点。"
                            },
                            {
                                "heading": "第 2 层：Block 线程块（协同的班级）",
                                "bullets": ["几十个工人坐进同一个教室，共享一块讲台黑板，能吹哨同步。"],
                                "focus": [0, 1, 2, 3, 4, 5, 6, 7],
                                "narration": "中间层是 Block，也就是一个班级车间。同班的 32 或 64 个工人坐在同一个房间里，可以共用黑板，互通有无。"
                            },
                            {
                                "heading": "第 3 层：Grid 网格（整个年级集团）",
                                "bullets": ["把所有班级集中起来，构成完整的计算任务总网格。"],
                                "focus": list(range(32)),
                                "narration": "最外层是 Grid，也就是整个年级或者制造集团。整个大任务被切分成成百上千个班级，各司其职同时开工！"
                            }
                        ]
                    }
                }
            },
            {
                "slide_id": 2,
                "title": "生活大比方：年级、班级与座位号",
                "slide_type": "metaphor_sketch",
                "key_points": [
                    "Thread（线程） = 教室里的一个学生，负责算一道题。",
                    "Block（线程块） = 一个班级（比如初一 3 班），全班共用讲台黑板，下课一起吹哨集合。",
                    "Grid（网格） = 整个初一年级，包含了所有的班级。",
                    "为什么必须有班级？因为校长管不了两万人，硬件调度器一次性把整个班级分发给一个独立车间（SM）！"
                ],
                "narration_script": "我们把这套抽象模型直接搬到现实学校里。想象有一所超级中学，初一年级一共有 1000 个学生，校长接到了批改 1000 份试卷的任务。校长能一个人直接对着 1000 个学生扯着嗓子挨个点名吗？根本管不过来！所以学校把这 1000 个学生分成了若干个班级。比如每 32 个学生组成一个班级，这就是 Block；而由所有班级组成的初一年级，就是 Grid；坐在座位上的每一个小学生，就是 Thread！为什么要分班级呢？因为班级里的同学坐在同一个物理教室里，大家抬头就能看到讲台上的大黑板，这在 GPU 里叫共享内存（Shared Memory）；老师喊一声‘全班起立对答案’，大家可以一起停下手里的笔，这在 GPU 里叫线程同步（__syncthreads()）。而不同班级之间隔着走廊，互不干扰，爱谁先做完谁先做完。这样硬件芯片就可以一个班一个班地把任务分发给不同的微型工厂 SM，既井井有条，又能无限横向扩展！",
                "visual_spec": {
                    "layout": "collision_animation",
                    "code_badge": "",
                    "scene_plan": {
                        "schema": "plan-v2",
                        "kind": "boxes",
                        "slide_id": 2,
                        "title": "学校生活类比：为什么必须层级分工？",
                        "subtitle": "大年级 Grid ──拆分成──> 独立班级 Block ──包含──> 小学生 Thread",
                        "figure": {
                            "nodes": [
                                {"id": "grid", "label": "初一年级 Grid (整个大任务 1024 人)"},
                                {"id": "b0", "label": "1 班 Block 0 (教室 1, 32 人)"},
                                {"id": "b1", "label": "2 班 Block 1 (教室 2, 32 人)"},
                                {"id": "b2", "label": "3 班 Block 2 (教室 3, 32 人)"},
                                {"id": "sm", "label": "硬件车间 SM (空闲教室，谁来接谁)"}
                            ],
                            "edges": [
                                ["grid", "b0", "分发"],
                                ["grid", "b1", "分发"],
                                ["grid", "b2", "分发"],
                                ["b0", "sm", "调度入驻"]
                            ]
                        },
                        "steps": [
                            {
                                "heading": "年级拆班：化整为零",
                                "bullets": ["把海量数据任务切分成独立的不依赖块，保证极强的扩展性。"],
                                "focus": [0],
                                "narration": "第一步是化整为零：年级把庞大的千万级任务切成成千上万个独立班级，没有任何班级依赖另一个班。"
                            },
                            {
                                "heading": "班内协作：高内聚低耦合",
                                "bullets": ["同一个班的同学才能看到同一个黑板，不同班级完全解耦。"],
                                "focus": [1, 2, 3],
                                "narration": "第二步是班内高度协作：班级内部的工人能高速共享数据，而班级之间完全解耦，随时可以被硬件任意打散并发调度。"
                            },
                            {
                                "heading": "弹性入驻：硬件无关性",
                                "bullets": ["不管你买 1000 块还是 2 万块的显卡，班级一个一个进教室跑就行！"],
                                "focus": [4],
                                "narration": "第三步是神奇的弹性硬件兼容：好显卡有 100 个教室，可以同时进 100 个班；差显卡只有 10 个教室，就 10 个班 10 个班轮着来，代码一行都不用改！"
                            }
                        ]
                    }
                }
            },
            {
                "slide_id": 3,
                "title": "秒懂天书公式：如何算自己的全局学号？",
                "slide_type": "manim_physics_demo",
                "key_points": [
                    "天书公式：int i = blockIdx.x * blockDim.x + threadIdx.x;",
                    "生活翻译：全局学号 = 你的班级号 × 每班人数 + 你的座位号。",
                    "真实演算：2 班 5 号（每班 32 人）的前面有整整 2 个班（64 人），全局学号就是 64 + 5 = 69！"
                ],
                "narration_script": "有了班级的直觉，我们再来看所有 CUDA 教程里最让新手发怵的公式：int i = blockIdx.x 乘以 blockDim.x 加上 threadIdx.x。其实把它翻译成人话，就是小学生算学号的乘法题！我们来拆解三个变量名：blockIdx.x 就是你的‘班级号’；blockDim.x 就是‘每个班有多少人’；threadIdx.x 就是你在这个班里的‘座位号’。假设你是 2 班的同学，你的班级号 blockIdx.x 就是 2；每个班固定有 32 个人，blockDim.x 就是 32；你的座位号 threadIdx.x 是 5。现在校长在广播里要问你的全校唯一全局学号是多少，你怎么算？你肯定心算：我前面有两个完整的班级，0 班和 1 班，他们一共占去了 2 乘以 32，也就是 64 个人；再加上我在当前班级坐第 5 号，我的全局学号不就是 64 加 5 等于 69 吗？你看，这就是 blockIdx.x 乘以 blockDim.x 加上 threadIdx.x 的全部秘密！就这么一条小学生都会算的加乘公式，只要在核函数里一跑，每个线程就能瞬间认领属于自己的那个数组位置，绝不多算，绝不错算！",
                "visual_spec": {
                    "layout": "collision_animation",
                    "code_badge": "int i = blockIdx.x * blockDim.x + threadIdx.x;",
                    "scene_plan": {
                        "schema": "plan-v2",
                        "kind": "grid",
                        "slide_id": 3,
                        "title": "全局索引物理推导：二维坐标折算为一维工号",
                        "subtitle": "全局工号 i = 班级号(blockIdx) × 班容(blockDim) + 班内座号(threadIdx)",
                        "figure": {
                            "rows": 4,
                            "cols": 8,
                            "labels": [f"Idx {i}" for i in range(32)]
                        },
                        "steps": [
                            {
                                "heading": "步骤 1：定位你的班级 (blockIdx.x)",
                                "bullets": ["确定当前线程坐落在第几个 Block 中，前面跳过了几个整块。"],
                                "focus": [0, 8, 16, 24],
                                "narration": "第一步看自己在第几班。前面的每一个整班，都会打包跳过整整 blockDim.x 个数字位置。"
                            },
                            {
                                "heading": "步骤 2：整块平铺相乘 (blockIdx.x * blockDim.x)",
                                "bullets": ["班级号乘以每班人数，瞬间定位到本班首个元素的物理起点。"],
                                "focus": [16, 17, 18, 19, 20, 21, 22, 23],
                                "narration": "第二步用班级号乘以每班容量，指针瞬间从全校大操场直接瞬移到本班教室门口的第一个座位！"
                            },
                            {
                                "heading": "步骤 3：加上座号精确定位 (+ threadIdx.x)",
                                "bullets": ["加上自己的班内座位号，精准点亮唯一对应的数据方格！"],
                                "focus": [21],
                                "narration": "第三步再加上自己的座位号，啪的一声！你属于全校独一无二的全局工号就诞生了，直接精准操盘对应的内存数据！"
                            }
                        ]
                    }
                }
            },
            {
                "slide_id": 4,
                "title": "白话看代码：越界保护为什么必须写？",
                "slide_type": "code_diff",
                "key_points": [
                    "防翻车铁律：算完学号必须紧跟 if (i < N) 防越界判断！",
                    "原因：班级人数是固定的（比如 32 的倍数），但任务总数往往不是整除的（比如 1000 个数据）。",
                    "后果：如果不加保护，多出来的 24 个学生就会写到别人的试卷上，导致内存非法覆写甚至程序崩溃！"
                ],
                "narration_script": "学会了算学号，初学者最容易踩的生死大坑就来了！在几乎所有工业级 CUDA 代码里，算完学号紧接着的下一行，必定死死跟着一句：if (i 小于 N)。这行代码是干什么的？这叫‘保命安全气囊’！我们还是用小学的例子：假设全校要批改 1000 份试卷，而我们规定每个班必须坐 32 个人。1000 除以 32 等于 31.25，学校只能派出 32 个完整的班级，总共出动了 1024 个学生！大家注意，试卷只有 1000 份，但到场的学生有 1024 个。那坐在最后几个座位的第 1000 号到第 1023 号学生，桌上根本没有试卷给他改。如果代码里不写这句 if (i 小于 N)，这多出来的 24 个学生就会提着笔往邻居家的桌子上乱涂乱画，这在计算机里就叫显存越界访问，轻则计算结果全错，重则引发非法内存访问，直接让程序瞬间暴毙！所以牢记：算完全局工号，第一件事就是关门放哨：if (i 小于 N)，超员的小朋友请把笔放下休息！",
                "visual_spec": {
                    "layout": "collision_animation",
                    "code_badge": "__global__ void add(int *c, int n) {\n    int i = blockIdx.x * blockDim.x + threadIdx.x;\n    if (i < n) { c[i] = 1; } // 安全气囊！\n}",
                    "scene_plan": {
                        "schema": "plan-v2",
                        "kind": "code",
                        "slide_id": 4,
                        "title": "小白代码拆解：必须添加的越界护栏",
                        "subtitle": "算完全局学号后，多余的工人必须放下笔！",
                        "figure": {
                            "lines": [
                                "__global__ void vectorAdd(int *c, int n) {",
                                "    int i = blockIdx.x * blockDim.x + threadIdx.x;",
                                "    if (i < n) {",
                                "        c[i] = 1; // 仅在有效范围内安全执行",
                                "    }",
                                "}"
                            ],
                            "language": "CUDA C++"
                        },
                        "steps": [
                            {
                                "heading": "声明：__global__ 跨界出征令",
                                "bullets": ["告诉编译器这个函数由 CPU 启动，在 GPU 显卡里执行。"],
                                "focus": [0],
                                "narration": "函数头上的下划线 global 是跨界出征令，通知编译器这是由 CPU 发号施令、由 GPU 工人们跑的核函数。"
                            },
                            {
                                "heading": "算号：每个工人认领自己的位置",
                                "bullets": ["根据班级和座号，计算出全局唯一的数据下标。"],
                                "focus": [1],
                                "narration": "第二行算号，通过班级乘班容加座号，每一个工人瞬间拿到了自己在全校数据大操场上的唯一定位。"
                            },
                            {
                                "heading": "护栏：if (i < n) 阻止越界破坏",
                                "bullets": ["整除分配带来的富余线程必须停工，严禁越界覆写。"],
                                "focus": [2, 3],
                                "narration": "第三行是保命护栏！判断学号是否小于总任务量 N，多出来的富余工人乖乖放下笔，确保显存百分之百安全！"
                            }
                        ]
                    }
                }
            },
            {
                "slide_id": 5,
                "title": "一句话口诀与小白课后自测",
                "slide_type": "summary_best_practice",
                "key_points": [
                    "核心口诀：Grid 是年级，Block 是班级，Thread 是学生；班号乘班容加座号，算出全局唯一号！",
                    "安全口诀：只要开班有富余，if (i < N) 保平安！",
                    "小白自测：如果 blockIdx.x=4，blockDim.x=64，threadIdx.x=10，当前工号是多少？"
                ],
                "narration_script": "学到这里，CUDA 编程模型最核心的骨架你已经彻底降伏了！我们用两句顺口溜把今天的内容刻进脑海：第一句：Grid 是年级，Block 是班级，Thread 是学生；班号乘班容加座号，算出全局唯一号！第二句：总数不能被整除，if 小于 N 保平安！最后还是留给大家一道 5 秒钟的口算自测题：假设你的核函数里，当前线程的班级号 blockIdx.x 是 4，每个班有 64 个人，你的班内座号 threadIdx.x 是 10，请问你在全校唯一的全局工号是多少？心算一下：4 乘以 64 等于 256，再加上 10，答案就是 266！只要你脱口而出 266，就说明你已经彻底吃透了 CUDA 最核心的软件执行图景！下节课，我们将带大家走进 CPU 与 GPU 之间那条繁忙的货运公路！",
                "visual_spec": {
                    "layout": "collision_animation",
                    "code_badge": "",
                    "scene_plan": {
                        "schema": "plan-v2",
                        "kind": "boxes",
                        "slide_id": 5,
                        "title": "本讲核心心法：三层空间与工号换算",
                        "subtitle": "牢记组织关系，牢记安全护栏",
                        "figure": {
                            "nodes": [
                                {"id": "c1", "label": "年级 Grid (总体任务规划)"},
                                {"id": "c2", "label": "班级 Block (片上 SM 调度执行)"},
                                {"id": "c3", "label": "学生 Thread (单个流水线落笔)"},
                                {"id": "c4", "label": "自测答案：4*64+10 = 266 号工人"}
                            ],
                            "edges": [
                                ["c1", "c2", "划分"],
                                ["c2", "c3", "组织"],
                                ["c3", "c4", "算出"]
                            ]
                        },
                        "steps": [
                            {
                                "heading": "心智模型完全建立",
                                "bullets": ["从此再看到 blockIdx 和 threadIdx，脑海里就是班级和座位号！"],
                                "focus": [0, 1, 2],
                                "narration": "从此以后你在任何地方看到三层维度坐标，脑子里都能瞬间浮现出年级、班级和座位号的生动画面。"
                            },
                            {
                                "heading": "自测题口算达成",
                                "bullets": ["266 号工人！就是这么简单自然，没有任何玄虚。"],
                                "focus": [3],
                                "narration": "刚才的自测题答案 266，证明你已经彻底征服了初学者最害怕的索引关卡，为编写实战代码打下了坚实地基！"
                            }
                        ]
                    }
                }
            }
        ]
    },

    # =========================================================================
    # 03. The CUDA Platform: CPU 与 GPU 异构协同与 Host/Device 货运
    # =========================================================================
    "sec_003_the_cuda_platform": {
        "sec_id": "sec_003_the_cuda_platform",
        "topic": "CPU 与 GPU 协同：Host 与 Device 货运流水线",
        "page_range": "P31-P34",
        "page_count": 4,
        "source": "pedagogy_zero_foundation",
        "slides": [
            {
                "slide_id": 1,
                "title": "小白之惑：为什么 GPU 读不到我在 CPU 定义的变量？",
                "slide_type": "title_overview",
                "key_points": [
                    "初学者最常见报错：在 main 函数里写了 a=10，GPU 核函数里去读直接报非法内存！",
                    "原因：CPU 和 GPU 是两块物理独立的芯片，内存也是两块互不相通的硬件！",
                    "术语澄清：CPU 与主板内存叫 Host（主机），GPU 与显存叫 Device（设备）。"
                ],
                "narration_script": "很多刚写 CUDA 代码的同学都犯过一个极其经典的错误：在 C++ 程序的 main 函数里明明定义了一个变量 int a = 10，然后兴冲冲地在 GPU 核函数里直接去读这个 a，结果一运行，程序瞬间崩溃，报出刺眼的段错误非法访问。大家非常纳闷：明明都是我这台电脑里的代码，为什么显卡就看不见我的变量呢？今天这一节，我们要搞懂异构系统的第一物理定律：CPU 和 GPU 是物理上完全隔离的两个世界！CPU 和它插在主板上的内存条，在 CUDA 里统一被称为 Host，也就是主机；而 GPU 和焊在显卡上的独立显存，被称为 Device，也就是设备。今天我们就来看看，数据到底是怎么在这两座互不相通的孤岛之间来回搬运的！",
                "visual_spec": {
                    "layout": "collision_animation",
                    "code_badge": "",
                    "scene_plan": {
                        "schema": "plan-v2",
                        "kind": "boxes",
                        "slide_id": 1,
                        "title": "物理隔离：主机 Host 与设备 Device",
                        "subtitle": "主板 CPU 内存条 (Host) ──隔着 PCIe 峡谷──> 显卡 GPU 显存 (Device)",
                        "figure": {
                            "nodes": [
                                {"id": "host_cpu", "label": "CPU 核心 (发号施令的董事长)"},
                                {"id": "host_ram", "label": "主机内存 RAM (公司总部的文档柜)"},
                                {"id": "pcie", "label": "PCIe 高速通道 (跨峡谷过江大桥)"},
                                {"id": "dev_vram", "label": "显卡显存 VRAM (远郊代工厂大仓库)"},
                                {"id": "dev_gpu", "label": "GPU 核心群 (成千上万代工流水线)"}
                            ],
                            "edges": [
                                ["host_cpu", "host_ram", "直连毫秒访问"],
                                ["host_ram", "pcie", "雇卡车装载"],
                                ["pcie", "dev_vram", "过江运达"],
                                ["dev_gpu", "dev_vram", "厂内超高速读取"]
                            ]
                        },
                        "steps": [
                            {
                                "heading": "左岛：总部办公室 Host",
                                "bullets": ["CPU 控制整个程序的生老病死，操作系统的所有文件和内存都在这里。"],
                                "focus": [0, 1],
                                "narration": "左边是公司总部的 Host：CPU 是发号施令的董事长，内存条是总部的文档柜，程序刚启动时所有数据都在这儿。"
                            },
                            {
                                "heading": "过江：PCIe 跨海大桥",
                                "bullets": ["两块芯片隔着主板插槽总线，必须通过数据传输通道搬家。"],
                                "focus": [2],
                                "narration": "中间隔着主板上的 PCIe 插槽大桥，两个物理世界之间不能隔空取物，所有包裹都得通过货车运过去。"
                            },
                            {
                                "heading": "右岛：远郊代工厂 Device",
                                "bullets": ["GPU 工厂只认自己厂房里的大仓库（显存 VRAM），读不到总部的纸。"],
                                "focus": [3, 4],
                                "narration": "右边是远郊工厂 Device：GPU 工人们只认自己厂房里焊好的大仓库 VRAM，这就是为什么必须先把数据拉进显存！"
                            }
                        ]
                    }
                }
            },
            {
                "slide_id": 2,
                "title": "生活大比方：总部办公室与远郊外包大工厂",
                "slide_type": "metaphor_sketch",
                "key_points": [
                    "Host（CPU） = 市中心的总部写字楼：领导在这里制定战略，存放合同原始文件。",
                    "Device（GPU） = 远郊的外包制造代工厂：厂里有上万名熟练技术工人，干活极其神速。",
                    "痛点：工人们在远郊厂房里，根本不可能伸手够到你总部的办公桌！",
                    "解决方案：必须用厢式货车走高速公路（PCIe），把图纸和原材料整批运到厂区大仓库！"
                ],
                "narration_script": "我们用外包大工厂的例子把这个过程具象化。想象你在市中心高档写字楼里开了一家设计公司，这是 Host；你在电脑硬盘里准备好了 1000 万张待处理的照片，存放在你身边的文件柜里，也就是主机内存。现在你想处理这 1000 万张照片，你在城郊 50 公里外找了一家拥有 5000 名工人的外包代工厂，这就是 Device。工厂里的工人们手脚极其利索，给他们图纸，一秒钟就能裁好一万张。但是工人们远在城郊，他们哪怕想看你桌上的一张草稿纸，也绝对不可能把手伸过 50 公里抓过去！那正常的工业流程该怎么做？显而易见：第一步，你必须先打电话给外包工厂：‘喂，厂长吗？先在你们厂区划一块空仓库出来！’这叫在显卡里分配空间；第二步，你雇一辆厢式大货车，把文件柜里的 1000 万张照片打包，开上高速公路，拉到外包工厂的仓库里！第三步，厂长一声令下，几千名工人从厂区仓库搬走照片，疯狂开工！第四步，等大家裁好了，再雇卡车把成品沿高速公路拉回总部的写字楼，最后把厂里的空仓库退租。这一套合情合理的商业外包流程，就是每一个 CUDA 程序员每天必须写烂的经典四步曲！",
                "visual_spec": {
                    "layout": "collision_animation",
                    "code_badge": "",
                    "scene_plan": {
                        "schema": "plan-v2",
                        "kind": "compare",
                        "slide_id": 2,
                        "title": "商业外包流水线：经典四步曲",
                        "subtitle": "租厂房仓库 → 卡车运货上岛 → 工厂批量赶工 → 运回成品退租",
                        "figure": {
                            "left": {
                                "title": "真实世界：总部外包流程",
                                "lines": [
                                    "1. 电话联系厂区：预留一块大仓库",
                                    "2. 雇佣顺丰货车：把图纸运送至厂区",
                                    "3. 广播喇叭喊话：全体工人同时动工",
                                    "4. 货车拉回成果：腾退注销厂区仓库"
                                ]
                            },
                            "right": {
                                "title": "CUDA 代码：对应标准 API",
                                "lines": [
                                    "1. cudaMalloc(租用显存物理空间)",
                                    "2. cudaMemcpy(HostToDevice 跨总线)",
                                    "3. kernel<<<Grid, Block>>>(启动计算)",
                                    "4. cudaMemcpy(DeviceToHost) & cudaFree"
                                ]
                            }
                        },
                        "steps": [
                            {
                                "heading": "第一步：在显存里开辟仓库 (cudaMalloc)",
                                "bullets": ["申请一块显存指针，告诉显卡准备接收多少字节的数据。"],
                                "focus": [0],
                                "narration": "第一步是向显卡申请一块干净的显存空间，拿到了一个显存专用的指针，相当于在远郊厂区拿到了仓库钥匙。"
                            },
                            {
                                "heading": "第二步：卡车装货跨越 PCIe (cudaMemcpy H2D)",
                                "bullets": ["把主机内存的数据，顺着 PCIe 通道搬运到显卡大仓库。"],
                                "focus": [1],
                                "narration": "第二步是用卡车运货，把内存条里的原始数组，顺着 PCIe 总线高速公路倾泻进刚刚申请好的显存大仓库。"
                            },
                            {
                                "heading": "第三步：点火开工与拉回成品 (Launch & D2H)",
                                "bullets": ["尖括号点火开工，算完后再用卡车拉回主机内存。"],
                                "focus": [2, 3],
                                "narration": "第三步尖括号发号施令让工人开工，算完后再用卡车把结果从显存运回电脑内存，最后释放显存，大功告成！"
                            }
                        ]
                    }
                }
            },
            {
                "slide_id": 3,
                "title": "白话看代码：经典四步曲的标准写法",
                "slide_type": "code_diff",
                "key_points": [
                    "cudaMalloc：在远郊显存里租仓库（参数是指针的地址与字节数）。",
                    "cudaMemcpy(..., cudaMemcpyHostToDevice)：雇卡车把数据拉去工厂仓库。",
                    "kernel<<<blocks, threads>>>(...)：吹号角让工厂所有人动笔开工！",
                    "cudaMemcpy(..., cudaMemcpyDeviceToHost) + cudaFree：拉回成果并退房。"
                ],
                "narration_script": "我们直接来看屏幕上的标准 CUDA C++ 代码，有了刚才的外包比喻，每一行看起来都无比亲切！第一行：cudaMalloc(&d_data, size)。注意那个 d 前缀，工业界通常用 h 表示 Host 内存，用 d 表示 Device 显存。这行代码就是在显卡里租下 size 个字节的仓库空间。第二行：cudaMemcpy(d_data, h_data, size, cudaMemcpyHostToDevice)。最后一个参数叫 HostToDevice，顾名思义：把总部文件柜 h_data 里的图纸，运给外包工厂 d_data！第三行：add<<<grids, blocks>>>(d_data)。三个尖括号一响，黄金万两！厂长按下总电闸，显卡里上千名工人同时从 d_data 里抄数据开工！第四行：再调用一次 cudaMemcpy，最后一个参数变成 DeviceToHost，把算完的成品运回总部的 h_data 柜子里；最后紧跟一个 cudaFree(d_data)，退租显存仓库，防止内存泄漏！这就是所有 CUDA 程序的标准心法骨架，无论以后写多么高深的模型，万变不离其宗！",
                "visual_spec": {
                    "layout": "collision_animation",
                    "code_badge": "cudaMalloc(&d_a, bytes);\ncudaMemcpy(d_a, h_a, bytes, cudaMemcpyHostToDevice);\nadd<<<grids, blocks>>>(d_a);\ncudaMemcpy(h_a, d_a, bytes, cudaMemcpyDeviceToHost);\ncudaFree(d_a);",
                    "scene_plan": {
                        "schema": "plan-v2",
                        "kind": "code",
                        "slide_id": 3,
                        "title": "白话代码拆解：异构协同标准样板",
                        "subtitle": "租显存 → 运数据(H2D) → 点火计算 → 拉回数据(D2H) → 释放",
                        "figure": {
                            "lines": [
                                "cudaMalloc(&d_a, bytes); // 1. 远郊厂区租仓库",
                                "cudaMemcpy(d_a, h_a, bytes, cudaMemcpyHostToDevice); // 2. 货车运去工厂",
                                "addKernel<<<grids, blocks>>>(d_a); // 3. 厂长吹哨全员开工",
                                "cudaMemcpy(h_a, d_a, bytes, cudaMemcpyDeviceToHost); // 4. 货车拉回成果",
                                "cudaFree(d_a); // 5. 厂区仓库退租退房"
                            ],
                            "language": "CUDA C++"
                        },
                        "steps": [
                            {
                                "heading": "第 1 步：显存开辟 (cudaMalloc)",
                                "bullets": ["为 GPU 准备独立的物理接收缓冲区。"],
                                "focus": [0],
                                "narration": "第一行 cudaMalloc，在显卡自己的高带宽显存里圈出一块地盘，拿到专属于 GPU 的设备指针。"
                            },
                            {
                                "heading": "第 2 步：过江运货 (HostToDevice)",
                                "bullets": ["PCIe 总线大卡车把内存数据倾泻到显存。"],
                                "focus": [1],
                                "narration": "第二行跨桥搬运，数据从主机内存沿着 PCIe 总线快速倾泻到刚刚开辟好的显存缓冲区。"
                            },
                            {
                                "heading": "第 3-5 步：尖括号开工与收尾回传",
                                "bullets": ["启动并发 Kernel，运算完毕拉回结果并退租显存。"],
                                "focus": [2, 3, 4],
                                "narration": "第三行三个尖括号点火开工，算完后第四行把结果原路运回主机内存，第五行退租显存防止内存泄漏！"
                            }
                        ]
                    }
                }
            },
            {
                "slide_id": 4,
                "title": "一句话口诀与小白课后自测",
                "slide_type": "summary_best_practice",
                "key_points": [
                    "核心口诀：主控在主机，苦力在设备；显存先开房，数据卡车运，算完运回家！",
                    "性能警示：高速公路运货（PCIe）很慢，尽量少在两边来回倒腾数据！",
                    "小白自测：如果我在 GPU 函数里直接写 printf 打印 h_data，会发生什么？"
                ],
                "narration_script": "学完本节，我们用一句朗朗上口的口诀总结核心心智：主控在主机，苦力在设备；显存先开房，数据卡车运，算完运回家！同时千万记住一个顶级的性能法则：虽然显卡内部算数据快如闪电，但是中间那条连接两座岛屿的 PCIe 高速公路，跟内存和显存本身的带宽比起来，慢得像蜗牛爬！所以优秀的工程师都会尽量把数据在显卡里多算几遍，千万不要算一步就雇卡车运回主机，再运去显卡，那所有的加速比就全被运货的时间吃光了！最后留给大家一个 5 秒自测题：如果一个新手在 GPU 核函数里直接去读主机内存里的 h_data 变量，会发生什么？答案正如我们开篇所讲：GPU 工人根本拿不到总部的纸，它会因为指针悬空和非法越界访问，直接引发硬件异常崩溃！下一节，我们将亲自动手，从零写出我们人生的第一个完整可运行的 CUDA 程序！",
                "visual_spec": {
                    "layout": "collision_animation",
                    "code_badge": "",
                    "scene_plan": {
                        "schema": "plan-v2",
                        "kind": "boxes",
                        "slide_id": 4,
                        "title": "本讲核心心智图与避坑黄金律",
                        "subtitle": "两岛隔离原则与数据驻留法则",
                        "figure": {
                            "nodes": [
                                {"id": "k1", "label": "主机端 Host (控制流与业务逻辑)"},
                                {"id": "k2", "label": "PCIe 瓶颈 (尽量批量合并，减少来回折腾)"},
                                {"id": "k3", "label": "设备端 Device (数据驻留，连续高能计算)"}
                            ],
                            "edges": [
                                ["k1", "k2", "一次性倾泻"],
                                ["k2", "k3", "常驻显卡"]
                            ]
                        },
                        "steps": [
                            {
                                "heading": "黄金律：减少 PCIe 搬家开销",
                                "bullets": ["能常驻在显存的数据，绝不无故搬回主机。"],
                                "focus": [1],
                                "narration": "永远记住：PCIe 货运是整套架构中最窄的瓶颈，一次性把数据拉进显卡，在里面常驻算透，才是高性能的真谛！"
                            },
                            {
                                "heading": "自测题答疑总结",
                                "bullets": ["主机与设备物理隔离，严禁交叉跨岛无序裸指针访问。"],
                                "focus": [0, 2],
                                "narration": "恭喜你！搞懂了 Host 与 Device 的分工，你已经彻底避开了 90% CUDA 初学者都会踩的内存非法访问天坑！"
                            }
                        ]
                    }
                }
            }
        ]
    },

    # =========================================================================
    # 04. Intro to CUDA C: 从零编写第一个 CUDA 程序 (Vector Add)
    # =========================================================================
    "sec_004_intro_to_cuda_c": {
        "sec_id": "sec_004_intro_to_cuda_c",
        "topic": "从零编写第一个 CUDA 程序：Vector Add 全流程落地",
        "page_range": "P35-P44",
        "page_count": 10,
        "source": "pedagogy_zero_foundation",
        "slides": [
            {
                "slide_id": 1,
                "title": "小白之问：看懂了理论，怎样亲手写出第一个加法？",
                "slide_type": "title_overview",
                "key_points": [
                    "新手门槛：理论听着热闹，一打开代码编辑器看着指针和括号就犯怵！",
                    "破局：从全天下最经典的入门实验——向量加法（Vector Add）起步。",
                    "核心逻辑：让 1000 万个小学生，每个人同时把两个数字加在一起，生成第三个数字！"
                ],
                "narration_script": "很多初学者在学完前面的理论之后，一面对黑乎乎的代码编辑器，手放在键盘上就完全不知道该往哪敲了。今天这一节，我们彻底抛开所有心理恐惧，亲手带大家从零写出你人生中第一个真正能在显卡上狂奔的 CUDA 程序——向量加法 Vector Add！所谓的向量加法，名字听起来高大上，其实就是小学一年级的加法：你有两个装满了数字的超大数组 A 和 B，现在要把它们对应位置的数字相加，存进数组 C 里面。在 CPU 上你得写一个巨大的 for 循环从头跑到尾，而在 CUDA 里，我们要派出一万个小学生，每个人同时下笔算一道！今天我们就把每一个标点符号都掰开了揉碎了讲清楚！",
                "visual_spec": {
                    "layout": "collision_animation",
                    "code_badge": "",
                    "scene_plan": {
                        "schema": "plan-v2",
                        "kind": "boxes",
                        "slide_id": 1,
                        "title": "向量加法计算逻辑：千万人同时落笔",
                        "subtitle": "数组 A[i] ＋ 数组 B[i] ──由第 i 号线程并发计算──> 输出 C[i]",
                        "figure": {
                            "nodes": [
                                {"id": "arr_a", "label": "输入数组 A (A[0], A[1] ... A[N])"},
                                {"id": "arr_b", "label": "输入数组 B (B[0], B[1] ... B[N])"},
                                {"id": "threads", "label": "海量并发工人 (Thread 0, 1 ... N)"},
                                {"id": "arr_c", "label": "输出数组 C (C[i] = A[i] + B[i])"}
                            ],
                            "edges": [
                                ["arr_a", "threads", "读取"],
                                ["arr_b", "threads", "读取"],
                                ["threads", "arr_c", "写入"]
                            ]
                        },
                        "steps": [
                            {
                                "heading": "传统 CPU 思维：1 人干 1000 万次",
                                "bullets": ["一个单线程指针从 0 循环到 1000 万，耗时数百毫秒。"],
                                "focus": [0, 1],
                                "narration": "在传统 CPU 里，是一个工人拿着笔，从第 0 个加到第 1000 万个，循环千万次，时间长得令人窒息。"
                            },
                            {
                                "heading": "现代 GPU 思维：1000 万人 1 秒干完",
                                "bullets": ["每个工人拿到自己的专属学号 i，只动笔算自己的这一道题。"],
                                "focus": [2, 3],
                                "narration": "在 GPU 世界里，是一千万个工人同时动笔，每个人只算自己名下的这一道加法，瞬间交卷！"
                            }
                        ]
                    }
                }
            },
            {
                "slide_id": 2,
                "title": "白话看代码：核函数里的每一句真言",
                "slide_type": "code_diff",
                "key_points": [
                    "__global__：跨界出征令，通知编译器由 CPU 吹号启动、在 GPU 执行！",
                    "指针传参：float *a, float *b, float *c，把显存里的三个大数组钥匙递进核函数。",
                    "核函数极简：总共就两行代码，第一行算自己的工号，第二行相加写入！"
                ],
                "narration_script": "大家看屏幕上这段名扬天下的核函数代码。其实刨去函数头，真正的核心代码居然只有区区两行！我们一行一行看。第一行：__global__ void vecAdd(float *a, float *b, float *c, int n)。__global__ 是贴在函数头上的跨界出征令，告诉编译器：‘这个函数要在显卡里成千上万个核心上同时跑！’函数返回值永远是 void，因为 GPU 是通过指针直接在显存里改数据的，不需要 return 任何值。传进来的 a、b、c 是显存数组的地址钥匙，n 是数组的总长度。再看第二行：int i = blockIdx.x 乘以 blockDim.x 加上 threadIdx.x。这是我们在第二节课学过的算学号公式，让当前这个工人立刻算出自己的唯一全局编号。最后第三行：if (i 小于 n) c[i] = a[i] 加上 b[i]。如果学号在有效范围内，直接拿起 A 数组的第 i 个数，加上 B 数组的第 i 个数，一把填进 C 数组的第 i 个格子里！你看，就这么简简单单两行字，没有任何复杂的逻辑，人人都能看得懂！",
                "visual_spec": {
                    "layout": "collision_animation",
                    "code_badge": "__global__ void vecAdd(float *a, float *b, float *c, int n) {\n    int i = blockIdx.x * blockDim.x + threadIdx.x;\n    if (i < n) c[i] = a[i] + b[i];\n}",
                    "scene_plan": {
                        "schema": "plan-v2",
                        "kind": "code",
                        "slide_id": 2,
                        "title": "白话代码拆解：核函数逐行大揭秘",
                        "subtitle": "出征令 ──算学号 ──安全越界保护 ──极简相加",
                        "figure": {
                            "lines": [
                                "__global__ void vecAdd(float *a, float *b, float *c, int n) {",
                                "    int i = blockIdx.x * blockDim.x + threadIdx.x; // 算全局工号",
                                "    if (i < n) { // 保命安全气囊",
                                "        c[i] = a[i] + b[i]; // 核心加法计算",
                                "    }",
                                "}"
                            ],
                            "language": "CUDA C++"
                        },
                        "steps": [
                            {
                                "heading": "出征令与参数传递",
                                "bullets": ["__global__ 告诉编译器核函数将在设备端执行。"],
                                "focus": [0],
                                "narration": "第一行贴上跨界出征令，传入显存指针，告诉显卡工人们原材料在哪里、成品放在哪里。"
                            },
                            {
                                "heading": "认领工号与越界拦截",
                                "bullets": ["算号公式让每个工人各归其位，if (i < n) 拦截富余线程。"],
                                "focus": [1, 2],
                                "narration": "第二行和第三行让工人认领自己的学号，并系好安全带，多余的工人放下笔休息。"
                            },
                            {
                                "heading": "单兵落笔：极简赋值",
                                "bullets": ["一人加一道题，整个千万级数组在几微秒内瞬间完成！"],
                                "focus": [3],
                                "narration": "第四行一人动笔算一道题，没有循环，没有跳转，数万核心一击必杀！"
                            }
                        ]
                    }
                }
            },
            {
                "slide_id": 3,
                "title": "主函数里的排兵布阵：三个尖括号怎么配？",
                "slide_type": "concept_breakdown",
                "key_points": [
                    "调用方式：vecAdd<<<blocksPerGrid, threadsPerBlock>>>(d_a, d_b, d_c, n);",
                    "每班人数（threadsPerBlock）：通常固定为 256（32 的 8 倍，满载满员）。",
                    "需要几班（blocksPerGrid）：用总数向上取整：(n + 256 - 1) / 256！"
                ],
                "narration_script": "写完了显卡里的核函数，回到 CPU 的 main 主函数里，最让新手纠结的就是那三个尖括号里的神秘数字到底该怎么填。比如我们要算 1000 万个数字，尖括号里该写几乘几呢？我们教大家一套工业界通用的配方！第一步：确定每个班坐多少人，也就是 threadsPerBlock。根据我们前面学的大巴车规则，每班人数必须是 32 的整数倍，最推荐的标准配置是 256 个人！第二步：既然每班坐 256 人，面对 n 个数据，我们一共需要派出几个班级呢？很多新手直接写 n 除以 256，结果万一除不尽，最后剩下的几个数据就漏掉了！在计算机里，有一个极度精妙的向上取整经典公式：(n 加 256 减 1) 除以 256！只要用这个公式算出来的班级数，哪怕只多出来 1 个数据，它也会多开一个完整的班级去包容它，确保所有的数字一个不漏地全部被算完！配好这两个参数，三个尖括号往中间一塞，整个 GPU 工厂瞬间就被点燃了！",
                "visual_spec": {
                    "layout": "collision_animation",
                    "code_badge": "int threads = 256;\nint blocks = (n + threads - 1) / threads; // 向上取整神公式！\nvecAdd<<<blocks, threads>>>(d_a, d_b, d_c, n);",
                    "scene_plan": {
                        "schema": "plan-v2",
                        "kind": "boxes",
                        "slide_id": 3,
                        "title": "尖括号排兵布阵公式：向上取整的数学美感",
                        "subtitle": "每班定员 256 人 ──向上取整算出班级总数──> 尖括号启动",
                        "figure": {
                            "nodes": [
                                {"id": "n_val", "label": "总数据量 N (比如 1000 万)"},
                                {"id": "tp_val", "label": "每班人数 Threads (标准定员 256)"},
                                {"id": "bp_val", "label": "派出班数 Blocks = (N + 255) / 256"},
                                {"id": "launch", "label": "点兵发号 vecAdd<<<Blocks, Threads>>>"}
                            ],
                            "edges": [
                                ["n_val", "bp_val", "输入任务"],
                                ["tp_val", "bp_val", "班内容量"],
                                ["bp_val", "launch", "组装参数"]
                            ]
                        },
                        "steps": [
                            {
                                "heading": "确定班容：256 黄金定员",
                                "bullets": ["256 是 32 的 8 倍，刚好让 8 个 Warp 满负荷打满 SM。"],
                                "focus": [1],
                                "narration": "第一步确定黄金班容：256 个人刚好等于 8 辆满载的大巴车，硬件资源利用最均衡。"
                            },
                            {
                                "heading": "向上取整防漏算",
                                "bullets": ["(n + threads - 1) / threads 保证即使余 1 个元素也不会漏掉。"],
                                "focus": [0, 2],
                                "narration": "第二步用经典向上取整公式计算班级总数，保证即使多出一个尾数也能被完全覆盖。"
                            },
                            {
                                "heading": "尖括号点兵开工",
                                "bullets": ["两项参数填入尖括号，核函数瞬间以千万人之势爆发！"],
                                "focus": [3],
                                "narration": "第三步尖括号点将启动，整个程序以千军万马之势在显卡里爆发，这就是并行计算的纯粹魅力！"
                            }
                        ]
                    }
                }
            },
            {
                "slide_id": 4,
                "title": "一句话口诀与小白课后自测",
                "slide_type": "summary_best_practice",
                "key_points": [
                    "核心口诀：global 跨界出征令，尖括号点兵点将；每班定员二百五，一人加一道交卷！",
                    "流程记忆：租房(cudaMalloc) → 运料(H2D) → 点兵(<<<>>>) → 回传(D2H) → 退租(Free)。",
                    "小白自测：如果 N=1000，每班 256 人，(1000 + 255) / 256 算出来一共派出几个班？"
                ],
                "narration_script": "学完从零编写第一个程序，我们用一句口诀封存所有的操作细节：global 跨界出征令，尖括号点兵点将；每班定员二百五，一人加一道交卷！整个程序的生命周期依然是牢不可破的五步曲：显存租房、货车运料、尖括号点兵、货车拉回成果、退房释放显存！最后给大家留一道极简的口算自测题：如果你的任务量 N 是 1000 个数字，每班人数是 256 人，套用刚才的向上取整公式 (1000 加 255) 除以 256，算出来一共要派出几个班级呢？1255 除以 256 整数相除等于 4！派出整整 4 个班，总共 1024 个学生，前 1000 个人改卷子，最后 24 个人休息，一个不漏，完美完工！下节课，我们将带大家认识如何用全世界最流行的 Python 语言来写出同样强悍的 GPU 代码！",
                "visual_spec": {
                    "layout": "collision_animation",
                    "code_badge": "",
                    "scene_plan": {
                        "schema": "plan-v2",
                        "kind": "boxes",
                        "slide_id": 4,
                        "title": "本讲核心心智图与自测答案",
                        "subtitle": "五步曲全生命周期 ──向上取整算出 4 个班",
                        "figure": {
                            "nodes": [
                                {"id": "a1", "label": "五步生命周期：Malloc → H2D → Launch → D2H → Free"},
                                {"id": "a2", "label": "自测答案：(1000 + 255)/256 = 派出 4 个班级 (1024人)"},
                                {"id": "a3", "label": "成功迈出第一步：你已经是合格的 CUDA 实战开发者！"}
                            ],
                            "edges": [
                                ["a1", "a2", "验证"],
                                ["a2", "a3", "进阶"]
                            ]
                        },
                        "steps": [
                            {
                                "heading": "五步曲闭环",
                                "bullets": ["牢记从申请显存到释放的完整链条，杜绝一切内存泄漏。"],
                                "focus": [0],
                                "narration": "五步曲闭环深深刻进 DNA，从此无论写什么高难度项目，底层的骨架永远是这套标准规范。"
                            },
                            {
                                "heading": "恭喜迈入实战大门",
                                "bullets": ["你已经能够独立编写并读懂真实的 GPU 核函数代码！"],
                                "focus": [1, 2],
                                "narration": "自测题答案 4 个班！恭喜你，你已经亲手击穿了 GPU 编程的实战门槛，彻底摆脱了纸上谈兵！"
                            }
                        ]
                    }
                }
            }
        ]
    },

    # =========================================================================
    # 05. Intro to CUDA Python: Python 也能写 GPU？Numba 与 CuPy
    # =========================================================================
    "sec_005_intro_to_cuda_python": {
        "sec_id": "sec_005_intro_to_cuda_python",
        "topic": "Python 玩转 GPU 计算：Numba JIT 与 CuPy 即时加速",
        "page_range": "P45-P60",
        "page_count": 16,
        "source": "pedagogy_zero_foundation",
        "slides": [
            {
                "slide_id": 1,
                "title": "小白之问：C++ 门槛太高，能用熟悉的 Python 跑显卡吗？",
                "slide_type": "title_overview",
                "key_points": [
                    "心声：C++ 的指针、Makefile、头文件让人头大，我平时只用 Python！",
                    "疑问：Python 出了名的运行慢，能在显卡上跑出原生性能吗？",
                    "答案：完全可以！借由 Numba JIT 即时编译与 CuPy，直接享受 C 语言级别的 GPU 速度！"
                ],
                "narration_script": "很多做数据分析、机器学习和人工智能的同学，平时最熟悉的编程语言是 Python。一听说要学 CUDA，必须去啃 C++ 的裸指针、内存对齐和头文件链接，瞬间就打起了退堂鼓。大家心里难免有一个巨大的期盼：我就不能用我最熟悉的 Python 来写显卡代码吗？可是马上又有人跳出来质疑：Python 出了名的运行速度慢，平时单核跑个循环都要卡半天，把它搬到显卡上，难道不会把显卡也拖成老牛拉破车吗？今天这一节，我们将打破这个偏见！告诉你如何用 Python 极其优雅地写出和 C++ 性能几乎一模一样的 GPU 原生程序！",
                "visual_spec": {
                    "layout": "collision_animation",
                    "code_badge": "",
                    "scene_plan": {
                        "schema": "plan-v2",
                        "kind": "boxes",
                        "slide_id": 1,
                        "title": "Python 异构加速架构：Numba 与 CuPy 双雄",
                        "subtitle": "Python 极简语法开发 ──JIT 实时同传──> 显卡原生 PTX/SASS 机器码狂奔",
                        "figure": {
                            "nodes": [
                                {"id": "py_code", "label": "原生 Python 代码 (简单易读，开发敏捷)"},
                                {"id": "jit_eng", "label": "Numba JIT 即时编译器 (同声传译官)"},
                                {"id": "ptx_sass", "label": "纯硬件 GPU 机器码 (绕过所有 Python 解释器)"},
                                {"id": "gpu_hw", "label": "GPU 物理芯片 (以 C++ 原生极速狂飙)"}
                            ],
                            "edges": [
                                ["py_code", "jit_eng", "即时拦截"],
                                ["jit_eng", "ptx_sass", "直接生成汇编"],
                                ["ptx_sass", "gpu_hw", "硬件满速执行"]
                            ]
                        },
                        "steps": [
                            {
                                "heading": "痛点：Python 虚拟机解释慢",
                                "bullets": ["原生 Python 逐行解释字节码，单线程开销巨大。"],
                                "focus": [0],
                                "narration": "平时 Python 之所以慢，是因为每一行都在虚拟机里逐字解释，拖泥带水。"
                            },
                            {
                                "heading": "魔法：JIT 实时同声传译",
                                "bullets": ["Numba 把函数在运行前直接翻译成 LLVM 中间码并烧制成机器码。"],
                                "focus": [1, 2],
                                "narration": "但 Numba 像一位神仙同传翻译官，把你的 Python 函数在被调用的瞬间，直接翻译成了纯硬件机器码！"
                            },
                            {
                                "heading": "结果：零性能损耗狂奔",
                                "bullets": ["完全绕开 Python 虚拟机，速度与 C++ 编写的核函数毫无二致！"],
                                "focus": [3],
                                "narration": "一旦送进显卡，Python 虚拟机早就退场了，显卡跑的完全是纯净的硬件指令，速度与 C++ 毫无差别！"
                            }
                        ]
                    }
                }
            },
            {
                "slide_id": 2,
                "title": "生活大比方：自带翻译官的国际商务谈判",
                "slide_type": "metaphor_sketch",
                "key_points": [
                    "普通 Python 运行 = 一个不懂外语的人拿着字典，逐个查单词跟外商说话，慢得像蜗牛。",
                    "Numba JIT = 聘请了国家级同声传译大翻译家：你在台上一张嘴说中文，他立刻用流利纯正的当地外语翻译完毕！",
                    "GPU 拿到的是翻译好的原生说明书：外商根本不知道你最初讲的是中文，交流效率达到最高峰！"
                ],
                "narration_script": "我们用商务谈判的比喻把 Python 的 GPU 加速一秒讲透。平时大家写 Python，就像一个完全不懂外语的小白去参加跨国商务谈判。他手里拿了一本厚厚的英文字典，别人说一句话，他翻一下字典，查到一个单词才读一句，慢得让人抓狂，这就是 Python 虚拟机的运行模式。而当你给函数头上贴上 @cuda.jit 装饰器的那一刻，相当于你直接雇佣了一位国家级的顶级同传大翻译官！你在台上潇洒自如地讲着最简单顺口的中文（也就是 Python 代码），大翻译官在幕后运笔如飞，一眨眼的功夫，就把你的全篇发言直接翻译成了一份语法毫无破绽、极其专业严谨的纯外文书面合同（也就是 GPU 机器码）！合同直接交到显卡手里，显卡照单全收，满负荷开工！显卡从头到尾根本不需要知道这份代码最初是用 Python 还是 C++ 写的，它执行的完全就是原汁原味的高性能硬件指令！",
                "visual_spec": {
                    "layout": "collision_animation",
                    "code_badge": "from numba import cuda\n\n@cuda.jit\ndef vecAdd_py(a, b, c):\n    i = cuda.grid(1) # 一句话自动搞定二维三维工号换算！\n    if i < c.size:\n        c[i] = a[i] + b[i]",
                    "scene_plan": {
                        "schema": "plan-v2",
                        "kind": "code",
                        "slide_id": 2,
                        "title": "Numba CUDA 白话语法：比 C++ 更加优雅精妙",
                        "subtitle": "@cuda.jit 出征令 ──cuda.grid(1) 自动算工号",
                        "figure": {
                            "lines": [
                                "from numba import cuda",
                                "@cuda.jit // 贴上 JIT 跨界出征令",
                                "def vector_add_python(a, b, c):",
                                "    i = cuda.grid(1) # 一行搞定所有 blockIdx 坐标相乘！",
                                "    if i < c.size:",
                                "        c[i] = a[i] + b[i]"
                            ],
                            "language": "Python"
                        },
                        "steps": [
                            {
                                "heading": "贴上 @cuda.jit 装饰器",
                                "bullets": ["通知 Numba 这是一个要由显卡执行的并行核函数。"],
                                "focus": [1],
                                "narration": "函数头顶的 @cuda.jit 就是 Python 世界的跨界出征令，唤醒同声传译官进入战斗状态。"
                            },
                            {
                                "heading": "一行 cuda.grid(1) 降维打击",
                                "bullets": ["省去繁琐的手写乘加，Numba 自动为你折算出全局一维绝对工号！"],
                                "focus": [3],
                                "narration": "看第四行极其震撼的 cuda.grid(1)！再也不用手写坐标乘法了，Numba 一行代码自动帮你算出全局学号！"
                            },
                            {
                                "heading": "原生 Python 数组操作",
                                "bullets": ["普通赋值语法，底层直接映射到显卡硬件高带宽读写。"],
                                "focus": [4, 5],
                                "narration": "最后像普通 Python 一样直接写相加，语法极简，底层的算力却狂飙突进，优雅至极！"
                            }
                        ]
                    }
                }
            },
            {
                "slide_id": 3,
                "title": "懒人终极神器：一行搞定的 CuPy",
                "slide_type": "concept_breakdown",
                "key_points": [
                    "如果连 Numba 的核函数都懒得写怎么办？",
                    "终极魔法 CuPy：把 import numpy as np 替换成 import cupy as cp！",
                    "全套矩阵乘法、奇异值分解、傅里叶变换，代码一行不改，速度立刻暴增 50 到 100 倍！"
                ],
                "narration_script": "如果你甚至觉得写 Numba 的核函数都有点费劲，还有没有更无脑、更暴力的加速方式？有！这就是在 AI 与数据科学界被奉为神明的终极懒人库——CuPy！大家平时在 Python 里做科学计算，最离不开的库必定是 NumPy。我们用 np.dot 算矩阵，用 np.sum 算求和。在过去，这些操作全是在 CPU 上慢吞吞单核跑的。而 CuPy 做了一件惊天动地的事：它把 NumPy 的几乎所有 API，在 GPU 底层全部用纯 C++ CUDA 重新写了一遍，并且把函数名做到了一模一样！这意味着什么？这意味着你过去辛辛苦苦写好的上千行数据处理脚本，只需要把最开头那句 import numpy as np，改成 import cupy as cp，其他所有代码一个标点符号都不用动，你的整个程序瞬间从 CPU 切换到了显卡显存里狂飙，矩阵乘法速度原地暴增 100 倍！这种近乎作弊般的生产力提升，就是现代 GPU 软件生态送给每一位开发者最丰厚的礼物！",
                "visual_spec": {
                    "layout": "collision_animation",
                    "code_badge": "# 仅需替换一行导入！\n# import numpy as np\nimport cupy as cp\n\nx = cp.ones((10000, 10000))\ny = cp.dot(x, x) # 显卡全速运转，百倍加速！",
                    "scene_plan": {
                        "schema": "plan-v2",
                        "kind": "compare",
                        "slide_id": 3,
                        "title": "NumPy vs CuPy：一行代码偷天换日",
                        "subtitle": "CPU 慢速单打独斗 ──替换一行导入──> GPU 原地百倍爆发",
                        "figure": {
                            "left": {
                                "title": "经典 NumPy (跑在 CPU 内存)",
                                "lines": [
                                    "import numpy as np",
                                    "x = np.random.randn(8000, 8000)",
                                    "y = np.dot(x, x)",
                                    "耗时：约 8.5 秒 (CPU 风扇轰鸣)"
                                ]
                            },
                            "right": {
                                "title": "神级 CuPy (原生跑在显卡显存)",
                                "lines": [
                                    "import cupy as cp",
                                    "x = cp.random.randn(8000, 8000)",
                                    "y = cp.dot(x, x)",
                                    "耗时：仅需 0.08 秒 (百倍加速秒杀！)"
                                ]
                            }
                        },
                        "steps": [
                            {
                                "heading": "左边：熟悉的 NumPy 传统单核",
                                "bullets": ["大矩阵乘法严重受制于 CPU 核心数，耗时达数秒之久。"],
                                "focus": [0],
                                "narration": "在 CPU 上跑大矩阵乘法，CPU 核心占满，耗时数秒，成了整个数据分析流水线的瓶颈。"
                            },
                            {
                                "heading": "右边：CuPy 一键无缝接管",
                                "bullets": ["零学习成本，直接替换导入包名，显卡瞬间爆发百倍威力！"],
                                "focus": [1],
                                "narration": "换上 CuPy 后，数据直接在显存生成，算力瞬间打满，耗时骤降几十到上百倍，爽快淋漓！"
                            }
                        ]
                    }
                }
            },
            {
                "slide_id": 4,
                "title": "一句话口诀与小白课后自测",
                "slide_type": "summary_best_practice",
                "key_points": [
                    "核心口诀：表面潇洒写 Python，底层飞奔纯机器；Numba 同传免损耗，CuPy 替换爽如飞！",
                    "技术选型：写自定义底层算法用 Numba @cuda.jit，写通用矩阵数组分析用 CuPy！",
                    "小白自测：使用 CuPy 算完数据后，如果要把结果画在 matplotlib 折线图上，该怎么办？"
                ],
                "narration_script": "学完 Python 的 CUDA 生态，我们用一句口诀封存今天的轻松愉悦：表面潇洒写 Python，底层飞奔纯机器；Numba 同传免损耗，CuPy 替换爽如飞！在未来的技术选型中，如果你需要写高度定制化的底层线程调度算法，请拿出 Numba 的 @cuda.jit；如果你只是想给你的大矩阵乘法、图像滤波和数据统计加速，直接无脑换上 CuPy！最后留给大家一个现实中天天会遇到的实战测试题：CuPy 算出来的矩阵保存在显卡显存里，而我们常用的画图库 matplotlib 只能读 CPU 内存里的数据，这时候你想把 CuPy 数组画成图表，该怎么办呢？答案非常简单：CuPy 提供了一个极度贴心的函数——x.get()，或者 cp.asnumpy(x)！只要调用一下 get()，它就会自动雇佣一辆后台卡车，把显存里的数据安安全全拉回电脑内存，然后你就能开开心心地用 matplotlib 绘图啦！下节课，我们将正式杀入 GPU 硬件底层最具杀伤力的机制——Warp 线程束与分支分化！",
                "visual_spec": {
                    "layout": "collision_animation",
                    "code_badge": "",
                    "scene_plan": {
                        "schema": "plan-v2",
                        "kind": "boxes",
                        "slide_id": 4,
                        "title": "本讲核心心智图与生态选择指南",
                        "subtitle": "定制算法选 Numba ──标准计算选 CuPy ──回传用 get()",
                        "figure": {
                            "nodes": [
                                {"id": "numba_box", "label": "Numba @cuda.jit：细粒度控制线程与共享内存"},
                                {"id": "cupy_box", "label": "CuPy：NumPy 无缝替代，零学习成本百倍加速"},
                                {"id": "interop", "label": "自测解法：调用 x.get() 自动回传主机内存"}
                            ],
                            "edges": [
                                ["numba_box", "interop", "协同"],
                                ["cupy_box", "interop", "回传"]
                            ]
                        },
                        "steps": [
                            {
                                "heading": "Python 生态双剑合璧",
                                "bullets": ["告别 C++ 编译环境的繁琐，Python 开发者也能尽享 GPU 算力红利。"],
                                "focus": [0, 1],
                                "narration": "Numba 与 CuPy 双剑合璧，让每一位 Python 开发者都能以最低的门槛，坐拥世界顶级的 GPU 算力！"
                            },
                            {
                                "heading": "数据回传自测解答",
                                "bullets": ["调用 .get() 随时拉回主机，与现有 Python 数据科学生态无缝融合。"],
                                "focus": [2],
                                "narration": "自测题答疑完毕：一个 get 函数随时打通显存与内存，与整个开源 Python 生态浑然一体！"
                            }
                        ]
                    }
                }
            }
        ]
    },

    # =========================================================================
    # 06. Writing SIMT Kernels: Warp 线程束与分支分化灾难
    # =========================================================================
    "sec_006_writing_simt_kernels": {
        "sec_id": "sec_006_writing_simt_kernels",
        "topic": "Warp 线程束与 SIMT 锁步执行机制",
        "page_range": "P61-P87",
        "page_count": 27,
        "source": "pedagogy_zero_foundation",
        "slides": [
            {
                "slide_id": 1,
                "title": "小白之惑：为什么大家总念叨 32？什么叫 Warp 线程束？",
                "slide_type": "title_overview",
                "key_points": [
                    "迷思：明明启动了 1024 个线程，为什么硬件手册里到处都是神秘数字 32？",
                    "本质：硬件发射指令时，从来不单个点名，而是把 32 个线程捆绑成一个 Warp 发射。",
                    "SIMT（单指令多线程）：一个喇叭喊口令，车上 32 个人同时动笔做相同的动作！"
                ],
                "narration_script": "只要你跟任何一个写 GPU 代码的老程序员聊天，你一定会发现他们嘴里动不动就念叨一个神秘的数字：32。不仅如此，他们还会一脸严肃地警告你：写代码时千万小心分支分化，小心性能砍半！很多初学者彻底懵了：我们上一节不是刚学了 Thread、Block 和 Grid 吗？怎么又冒出来一个 Warp 线程束？这个 32 到底是从哪里钻出来的？今天这一节，我们将揭开 GPU 硬件底层最核心的秘密——Warp 线程束与单指令多线程 SIMT。搞懂了它，你就能一眼看穿为什么别人的显卡跑得飞起，而你的代码却在显卡里疯狂‘堵车’！",
                "visual_spec": {
                    "layout": "collision_animation",
                    "code_badge": "",
                    "scene_plan": {
                        "schema": "plan-v2",
                        "kind": "warp",
                        "slide_id": 1,
                        "title": "硬件真实调度单位：32 个物理线程固定一组",
                        "subtitle": "指令发射器并不是一个一个喊，而是对 32 个人同时广播命令！",
                        "figure": {
                            "threads": 32
                        },
                        "steps": [
                            {
                                "heading": "捆绑打包：固定 32 线程一束",
                                "bullets": ["SM 内部的调度器以 32 为基本粒子进行物理派发。"],
                                "focus": list(range(32)),
                                "narration": "在硬件物理层面上，SM 从来不管理单个线程，而是把连续的 32 个线程焊死在一起，组成一个 Warp 线程束。"
                            },
                            {
                                "heading": "单指令广播 (Single Instruction)",
                                "bullets": ["一个发射时钟周期，给 32 个核心下达完全相同的指令。"],
                                "focus": list(range(16)),
                                "narration": "指令发射器只配一个广播喇叭，喊一句‘加法’，这 32 个工人就必须在同一节拍下整齐划一地同时落笔！"
                            },
                            {
                                "heading": "多数据独立 (Multiple Threads)",
                                "bullets": ["虽然动作完全相同，但每个人操盘自己名下的独立数据。"],
                                "focus": list(range(16, 32)),
                                "narration": "虽然大家的动作完全一样，但每个人手里握着的数字和内存地址不同，这就是单指令多线程 SIMT 的精髓！"
                            }
                        ]
                    }
                }
            },
            {
                "slide_id": 2,
                "title": "生活大比方：32 座大巴车与广播喇叭",
                "slide_type": "metaphor_sketch",
                "key_points": [
                    "Warp（线程束） = 一辆固定坐 32 个人的旅游大巴车。",
                    "SIMT 执行 = 导游拿着车载扩音器广播：‘所有人把矿泉水瓶盖拧开！’",
                    "整齐划一：车上 32 个人在同一个秒数整齐划一地拧开盖子，效率无与伦比！",
                    "为什么是 32？因为硬件如果给每个人配一个导游，芯片面积全被广播系统占满了！"
                ],
                "narration_script": "我们来打一个绝妙的生活大比方。你可以把一个 Warp 想象成一辆满载 32 个人的中巴车。车上坐了 32 名工人，车头只有一个广播喇叭。导游不可能走到每个座位的耳朵边挨个说悄悄话，那太浪费时间了。导游站在车头拿起麦克风大喊一声：‘所有人拿出铅笔，在第一道题上写个 1！’话音刚落，车上 32 个人低头同时下笔写 1。这就是 SIMT 单指令多线程。为什么硬件非要规定 32 个人一辆车呢？大家想想：如果给 32 个人每个人都配一个独立的导游和对讲机，芯片上的控制器面积就会暴增 32 倍，那就根本没有地方留给算数核心了！正是因为 32 个人共用一套指令解码系统，GPU 才能把体积压缩到极致，塞进去几万个计算核心。在风平浪静的时候，这辆大巴车就像开在德国高速公路上一样，一路狂飙，所向披靡！",
                "visual_spec": {
                    "layout": "collision_animation",
                    "code_badge": "",
                    "scene_plan": {
                        "schema": "plan-v2",
                        "kind": "compare",
                        "slide_id": 2,
                        "title": "生活大比方：大巴车载客与广播广播机制",
                        "subtitle": "1 个喇叭广播指令 ──锁步同步──> 32 名乘客齐刷刷动作",
                        "figure": {
                            "left": {
                                "title": "硬件哲学：极致精简控制流",
                                "lines": [
                                    "1 个指令解码器 (Instruction Cache)",
                                    "1 个 Warp 调度发射器",
                                    "节约高达 95% 的控制流芯片面积",
                                    "把省下来的空间全部做成绿色算力 ALU"
                                ]
                            },
                            "right": {
                                "title": "执行特征：锁步推进 (Lockstep)",
                                "lines": [
                                    "车上 32 个人必须走同一条物理路线",
                                    "时钟周期完全对齐，齐步走",
                                    "一旦步调一致，算力打满 100%",
                                    "但最怕有人想中途下车去不同地方！"
                                ]
                            }
                        },
                        "steps": [
                            {
                                "heading": "极简硬件设计：共用扩音喇叭",
                                "bullets": ["用一个指挥官管 32 个人，把晶体管效率发挥到极限。"],
                                "focus": [0],
                                "narration": "大巴车哲学的核心是极简：只配一个扩音喇叭，省下海量的控制逻辑晶体管，全部换成密密麻麻的算力核心。"
                            },
                            {
                                "heading": "锁步齐走：步调高度一致",
                                "bullets": ["只要大家没有分歧，32 个人每一纳秒都满负荷高速运转。"],
                                "focus": [1],
                                "narration": "只要全车 32 个人的动作步调一致，没有人在路上唱反调，这辆中巴车的算力输出就是百分之百的满分表现！"
                            }
                        ]
                    }
                }
            },
            {
                "slide_id": 3,
                "title": "分支分化灾难：大巴车遇到岔路口",
                "slide_type": "manim_physics_demo",
                "key_points": [
                    "灾难代码：if (threadIdx.x % 2 == 0) { 干路线A; } else { 干路线B; }",
                    "大巴车的困境：车只有一辆，既不能一分为二，也不能横跨两条路！",
                    "硬件惩罚：车先开去路线 A，奇数 16 人闭眼发呆挂起；干完后掉头去路线 B，换偶数人闭眼发呆！",
                    "恶果：本来 1 秒跑完的循环，硬生生花了 2 秒，单卡算力利用率暴跌到 50%！"
                ],
                "narration_script": "但是！如果代码里写了一个条件分支，噩梦瞬间就降临了！比如大家看这段代码：if (线程号是偶数) 走路线 A；else 走路线 B。车上一共有 32 个人，16 个偶数同学想去麦当劳，16 个奇数同学想去肯德基。中巴车只有一辆，它又不能在高速路上把自己劈成两半！那司机怎么处理呢？司机拿起喇叭大喊：‘偶数的 16 个人听令，低头去麦当劳点餐；奇数的 16 个人闭上眼睛、双手抱头，在座位上发呆挂起！’这时候只有一半的人在干活，另一半人白白坐着看戏。等偶数同学吃完了，司机再把车掉头开到肯德基，喊道：‘奇数的 16 个人起来干活，刚才吃过的偶数同学闭眼发呆！’大家看明白了吗？本来一脚油门大家一起干完的事情，因为这一句 if-else，硬生生被拆成了两个串行的阶段，全车人的总时间多花了一整倍，显卡算力直接腰斩 50%！在工业界，这种现象叫 Warp 分支分化（Warp Divergence），它是所有新手写出低性能代码的头号杀手！",
                "visual_spec": {
                    "layout": "collision_animation",
                    "code_badge": "if (threadIdx.x % 2 == 0) {\n    path_A(); // 偶数执行，奇数挂起发呆\n} else {\n    path_B(); // 奇数执行，偶数挂起发呆\n}",
                    "scene_plan": {
                        "schema": "plan-v2",
                        "kind": "warp",
                        "slide_id": 3,
                        "title": "Warp 分支分化动态推演：执行掩码与串行回退",
                        "subtitle": "路线 A 执行时奇数被 Mask 禁用 ──掉头──> 路线 B 执行时偶数被 Mask 禁用",
                        "figure": {
                            "threads": 32
                        },
                        "steps": [
                            {
                                "heading": "第 1 阶段：齐步走进入分岔路口",
                                "bullets": ["代码遇到 if (tid % 2 == 0)，Warp 内产生截然不同的执行意图。"],
                                "focus": list(range(32)),
                                "narration": "大巴车开进岔路口，遇到 if 条件判断，车内 32 名乘客瞬间分裂成两派不同的走向。"
                            },
                            {
                                "heading": "第 2 阶段：串行跑分支 A（禁用奇数）",
                                "bullets": ["硬件打上执行掩码，奇数核心断电发呆，算力瞬间暴跌 50%。"],
                                "focus": [i for i in range(32) if i % 2 == 0],
                                "narration": "硬件只能先串行跑分支 A，给奇数核心打上禁用掩码，这 16 个人只能在座位上白白发呆干等。"
                            },
                            {
                                "heading": "第 3 阶段：掉头跑分支 B（禁用偶数）",
                                "bullets": ["反转执行掩码，换奇数核心干活，偶数发呆，总用时翻倍！"],
                                "focus": [i for i in range(32) if i % 2 != 0],
                                "narration": "跑完分支 A 后，大巴车再掉头跑分支 B，换奇数干活偶数发呆，整个核函数耗时直接白白翻倍！"
                            }
                        ]
                    }
                }
            },
            {
                "slide_id": 4,
                "title": "避坑指南：怎样写代码才不会让大巴车堵车？",
                "slide_type": "code_diff",
                "key_points": [
                    "避坑心法：并不是不能写 if，而是要让同车 32 个人同心协力！",
                    "错误反例：按线程号对 2 取模（tid % 2 == 0），整车人在座位里犬牙交错分歧。",
                    "正确写法：以 32 的整数倍为分界线（tid / 32），整车 32 人要么全去 A，要么全去 B！"
                ],
                "narration_script": "那既然分支分化这么可怕，我们在 CUDA 里就完全不能写 if 语句了吗？当然不是！关键在于：你要确保坐在同一辆中巴车上的 32 个人，步调高度一致！大家看屏幕上的对比。左边的反例代码：if (threadIdx.x % 2 == 0)，座位号是 0、2、4 的偶数同学去 A，1、3、5 的奇数同学去 B，这 32 个人在同一辆车里犬牙交错，大巴车只能无可奈何地跑两趟，性能直接崩溃。再看右边的正解写法：假设我们按 32 个人为单位分工，前 32 个人也就是第 1 辆大巴车的整车人全部走路线 A，后 32 个人的第 2 辆大巴车整车人全部走路线 B。这时候奇迹发生了：第 1 辆大巴车一踩油门直接开向麦当劳，车上没有任何人唱反调；第 2 辆大巴车一踩油门直接开向肯德基，两辆车在各自的物理车道上并驾齐驱，分支分歧瞬间归零，算力依然打满 100%！所以工业界有一句金句：同一辆车里的 32 个人必须走同一条路；不同的车爱去哪去哪，互不相干！",
                "visual_spec": {
                    "layout": "collision_animation",
                    "code_badge": "// 规范正解：以 Warp 边界 (32) 组织分支！\nint warp_id = threadIdx.x / 32;\nif (warp_id == 0) { whole_warp_A(); }\nelse { whole_warp_B(); }",
                    "scene_plan": {
                        "schema": "plan-v2",
                        "kind": "compare",
                        "slide_id": 4,
                        "title": "分支避坑代码对比：犬牙交错 vs 整车对齐",
                        "subtitle": "车内内耗（性能腰斩） vs 整车统领（性能打满）",
                        "figure": {
                            "left": {
                                "title": "致命反例：车内犬牙交错",
                                "lines": [
                                    "if (threadIdx.x % 2 == 0) {",
                                    "    path_A(); // 0,2,4,6... 偶数",
                                    "} else {",
                                    "    path_B(); // 1,3,5,7... 奇数",
                                    "}",
                                    "// 结果：整车内部分化，串行两遍！"
                                ]
                            },
                            "right": {
                                "title": "工业规范：以 32 整数倍对齐",
                                "lines": [
                                    "int warp_id = threadIdx.x / 32;",
                                    "if (warp_id == 0) {",
                                    "    path_A(); // 整个 Warp 0 全去 A",
                                    "} else {",
                                    "    path_B(); // 整个 Warp 1 全去 B",
                                    "}",
                                    "// 结果：车内零分歧，并发无损！"
                                ]
                            }
                        },
                        "steps": [
                            {
                                "heading": "左边反例：同一辆车内部打架",
                                "bullets": ["相邻线程走不同分支，硬件只能串行执行两遍。"],
                                "focus": [0],
                                "narration": "左边反例把分支切在相邻线程之间，同车乘客各怀鬼胎，大巴车只能硬生生拆成两趟跑。"
                            },
                            {
                                "heading": "右边正解：以 32 为边界整车统筹",
                                "bullets": ["同一个 Warp 走同一个分支，各车并驾齐驱零损耗。"],
                                "focus": [1],
                                "narration": "右边正解以 32 的整数倍为分界线，整车人一条心，两辆车各自狂奔，完美避开所有性能惩罚！"
                            }
                        ]
                    }
                }
            },
            {
                "slide_id": 5,
                "title": "一句话口诀与小白课后自测",
                "slide_type": "summary_best_practice",
                "key_points": [
                    "核心口诀：三十二人一辆车，喇叭一响齐步走；同车最忌分歧路，整车对齐性能牛！",
                    "微架构真理：Warp 是硬件指令调度的不可分割原子单位。",
                    "小白自测：如果一个 Block 只有 33 个线程，硬件在物理上会启动几辆大巴车（几个 Warp）？"
                ],
                "narration_script": "学完这一节，大家是不是觉得深奥的 SIMT 和分支分化一下变得触手可及了？我们用一句顺口溜把今天的心法焊死在脑海里：三十二人一辆车，喇叭一响齐步走；同车最忌分歧路，整车对齐性能牛！最后留给大家一个极度考验直觉的小白测试题：假设你在代码里启动了一个 Block，里面的线程数设置为 33 个，请问显卡硬件在底层会为你派出几辆中巴车（也就是几个 Warp）呢？想一想：大巴车是固定 32 座的，前 32 个人坐满了第 1 辆大巴车，剩下的第 33 号同学孤零零一个人，硬件也必须为了他额外专门派出一整辆 32 座的大巴车！只不过那辆车上只有他一个人在干活，剩下 31 个座位全空着！答案就是：启动整整 2 个 Warp！这就是为什么工业界在设置线程块大小时，永远必须是 32 的整数倍！下节课，我们将带大家去探索 GPU 芯片上的高速小黑板——共享内存与分块乘法！",
                "visual_spec": {
                    "layout": "collision_animation",
                    "code_badge": "",
                    "scene_plan": {
                        "schema": "plan-v2",
                        "kind": "boxes",
                        "slide_id": 5,
                        "title": "本讲核心心智图与 32 整数倍原则",
                        "subtitle": "Warp 粒度与硬件分配底线",
                        "figure": {
                            "nodes": [
                                {"id": "w1", "label": "Warp 0: 线程 0~31 (满员 32 人高速开跑)"},
                                {"id": "w2", "label": "Warp 1: 线程 32 (只有 1 人，空置率 31/32)"},
                                {"id": "w3", "label": "黄金规则：线程块 Block 大小永远设为 32 的整数倍！"}
                            ],
                            "edges": [
                                ["w1", "w3", "对齐"],
                                ["w2", "w3", "警示"]
                            ]
                        },
                        "steps": [
                            {
                                "heading": "自测题答疑：33 线程派出 2 辆大巴",
                                "bullets": ["向上取整分配：33 个人必须消耗 2 个 Warp 的硬件调度资源。"],
                                "focus": [0, 1],
                                "narration": "自测题答案揭晓：33 个线程硬件必须派 2 辆大巴车！第二辆大巴车只有 1 个人，空载浪费极其严重。"
                            },
                            {
                                "heading": "工业规范：永远设为 32 的倍数 (128, 256)",
                                "bullets": ["Block 规模通常建议为 128、256 或 512，杜绝任何硬件空置。"],
                                "focus": [2],
                                "narration": "所以工业界写代码，BlockDim 永远写 128、256 或 512，保证每一辆大巴车都坐得满满当当，彻底榨干显卡硬件潜能！"
                            }
                        ]
                    }
                }
            }
        ]
    },

    # =========================================================================
    # 07. Writing TILE Kernels: 共享内存与分块矩阵乘法
    # =========================================================================
    "sec_007_writing_tile_kernels": {
        "sec_id": "sec_007_writing_tile_kernels",
        "topic": "共享内存与分块矩阵乘法 (Tiled GEMM)",
        "page_range": "P88-P105",
        "page_count": 18,
        "source": "pedagogy_zero_foundation",
        "slides": [
            {
                "slide_id": 1,
                "title": "小白之惑：GPU 算力这么强，为什么算矩阵乘法慢如蜗牛？",
                "slide_type": "title_overview",
                "key_points": [
                    "困惑：明明用了几千个核心，朴素矩阵乘法一跑，显卡风扇呼呼转，速度却慢得惊人！",
                    "真相：算得飞快，但全是发呆等数据——访存延迟（Memory Latency）成了死穴！",
                    "解药：利用同一个班级专属的片上高速小黑板——Shared Memory 共享内存！"
                ],
                "narration_script": "很多刚进阶 GPU 编程的同学，在写完第一个朴素矩阵乘法时，往往会被现实狠狠泼一盆冷水：明明我用了一万个线程，显卡风扇也转得震天响，为什么跑一个大矩阵乘法，耗时比想象中慢了十倍甚至几十倍？算力到底漏到哪里去了？真相可能会颠覆你的认知：显卡并不是算得慢，而是它大部分时间根本没在算，全在傻傻地等数据！全局显存离核心实在太远了，走一趟要花上百个时钟周期。这就好比一个大厨炒一道菜只要 3 秒钟，但他切好一片肉就得跑去郊区大仓库去拿一根葱，一来一回全浪费在路上了！今天这一节，我们将带大家认识 GPU 芯片上最神奇的加速神器——片上共享内存（Shared Memory），看看工程师们是如何用一块讲台大黑板，把矩阵乘法性能瞬间拉升十倍以上的！",
                "visual_spec": {
                    "layout": "collision_animation",
                    "code_badge": "",
                    "scene_plan": {
                        "schema": "plan-v2",
                        "kind": "matrix",
                        "slide_id": 1,
                        "title": "朴素矩阵乘法的致命死穴：海量重复访存",
                        "subtitle": "算 1 次乘加，跑远郊大仓库取 2 个数，总线被彻底挤爆！",
                        "figure": {
                            "size": 8,
                            "tile": 4
                        },
                        "steps": [
                            {
                                "heading": "乘法原理：行乘以列累加",
                                "bullets": ["计算结果矩阵的一个点，需要把 A 的一整行和 B 的一整列相乘。"],
                                "focus": [0, 1],
                                "narration": "计算矩阵的一个元素，必须把左矩阵的一整行和右矩阵的一整列对应相乘再累加。"
                            },
                            {
                                "heading": "致命重复：相邻工人互不通气",
                                "bullets": ["同一个数据被几千个线程从显存重复搬运了几百遍，极度浪费带宽！"],
                                "focus": [2, 3],
                                "narration": "在朴素写法里，相邻的工人完全不通气，同一个数字被几千个工人各自跑去显存搬了几百遍，总线瞬间被彻底挤瘫痪！"
                            }
                        ]
                    }
                }
            },
            {
                "slide_id": 2,
                "title": "生活大比方：讲台大黑板 vs 校外大仓库",
                "slide_type": "metaphor_sketch",
                "key_points": [
                    "全局显存（Global Memory） = 校外 10 公里的公用大仓库：容量超大（24GB），但走一趟要 400 步！",
                    "共享内存（Shared Memory） = 班级讲台上的大黑板：就挂在教室正前方，抬头看一眼只要 1 步！",
                    "分块乘法（Tiling）：全班派几个代表去校外大仓库整箱搬砖，整块抄在黑板上，大家在黑板前高速乘加！"
                ],
                "narration_script": "我们继续用班级教室的类比彻底讲透这个秘密。你可以把显卡上的全局显存（Global Memory）想象成校外 10 公里远的大仓库。那里地方大得很，能放几十个 G 的数据，但去一趟极慢，要走四百步（400 个时钟周期）。在朴素算法里，一个班 32 个同学，每算一步，32 个人各自跑一趟校外大仓库，搬一个数字回来乘一下，算下一个数又跑一趟校外仓库，整个教室门口全在堵车，大家都在路上跑马拉松，根本没人在桌前动笔！而共享内存（Shared Memory）是什么？它是就挂在你们班教室讲台正前方的一面大黑板！从黑板上抄一个数据，只要抬头看一眼，一步路就搞定（1 到 2 个时钟周期），速度快了整整几十倍！那聪明的班主任会怎么做？分块计算（Tiling）闪亮登场：全班同学分工协作，派代表去校外大仓库，把一个 16 乘以 16 的小数据方块一次性成箱搬回教室，清清楚楚抄在讲台大黑板上！然后全班同学在教室里，就着黑板上的数据高速乘加几十遍！算完了这一批，再一起擦掉黑板，搬下一个方块！这就是分块矩阵乘法 Tiled GEMM 的全部真相！",
                "visual_spec": {
                    "layout": "collision_animation",
                    "code_badge": "__shared__ float s_A[16][16]; // 班级讲台大黑板！",
                    "scene_plan": {
                        "schema": "plan-v2",
                        "kind": "compare",
                        "slide_id": 2,
                        "title": "访存策略大对决：各奔东西 vs 讲台黑板协同",
                        "subtitle": "远郊大仓库取货（慢 400 倍） vs 片上共享内存黑板（快如闪电）",
                        "figure": {
                            "left": {
                                "title": "朴素做法：各自跑郊区大仓库",
                                "lines": [
                                    "每个线程各算各的",
                                    "每次乘加都跨越总线去显存读数",
                                    "访问延迟高达 400+ 时钟周期",
                                    "算力核心 90% 时间处于饥渴停滞"
                                ]
                            },
                            "right": {
                                "title": "分块协同：讲台黑板数据复用",
                                "lines": [
                                    "整班派代表批量搬运一块 (Tile)",
                                    "整齐写入片上黑板 __shared__",
                                    "黑板读取延迟仅需 1~2 时钟周期",
                                    "同一批数据在班内复用数十次！"
                                ]
                            }
                        },
                        "steps": [
                            {
                                "heading": "左边反例：路途遥远带宽挤爆",
                                "bullets": ["显存不是算力不够，而是总线被重复的取水搬砖彻底塞死。"],
                                "focus": [0],
                                "narration": "左边的朴素写法，每个学生反复去几十公里外的仓库取数，芯片绝大部分时间都在干等数据送达。"
                            },
                            {
                                "heading": "右边正解：黑板片上超高复用",
                                "bullets": ["把小方块一次性抄在黑板上，班内全员原地复用计算，速度暴增！"],
                                "focus": [1],
                                "narration": "右边正解把小方块整箱抄在讲台黑板上，全班同学原地高速复用几十次，把访存压力直接骤降数十倍！"
                            }
                        ]
                    }
                }
            },
            {
                "slide_id": 3,
                "title": "动态推演：滑动的方块与同步哨音",
                "slide_type": "manim_physics_demo",
                "key_points": [
                    "Tiling 滑动窗口：把大矩阵切成一个个小方砖（Tile），窗口从左向右一步步推进。",
                    "__syncthreads() 哨音：全班搬完数据后，老师吹哨叫停，确保黑板写满了大家才能动手算！",
                    "双重保障：算完了再吹一次哨，确保所有人都算完了才能擦黑板换下一批，防止写脏数据！"
                ],
                "narration_script": "我们通过动画来看这个过程的物理推进。大家看屏幕：左边的 A 矩阵和右边的 B 矩阵，被切成了一个个发光的小方块（Tile）。每一个 Block 负责产出最终结果的一个小方格。在第 1 个阶段，A 的滑窗停在第一列块，B 的滑窗停在第一行块，Block 里的每个线程协同搬运一个数字，把这两个小方砖装载进片上的共享内存 s_A 和 s_B。装完之后，注意代码里最关键的保护神：__syncthreads()！全班同学必须集体听到这声哨音，停下来互相确认：大家都搬完了吗？确认黑板抄满了，大家再一起开足马力进行乘加运算！算完之后，老师再次吹响 __syncthreads() 哨音：大家都算完了吗？只有等全班最后一个同学算完，才能擦掉黑板，把滑窗向右滑动，把下一批砖搬上讲台！这两个同步屏障，就如同两道防洪堤，既保证了大家不会去读写到一半的空黑板，又保证了大家不会把同班同学还没算完的数据提前擦掉！",
                "visual_spec": {
                    "layout": "collision_animation",
                    "code_badge": "__syncthreads(); // 老师吹哨：全班到齐才能擦写黑板！",
                    "scene_plan": {
                        "schema": "plan-v2",
                        "kind": "matrix",
                        "slide_id": 3,
                        "title": "滑窗分块动态演进与 __syncthreads() 屏障",
                        "subtitle": "协同搬砖到黑板 ──吹哨同步──> 全员黑板乘加 ──吹哨擦黑板",
                        "figure": {
                            "size": 8,
                            "tile": 4
                        },
                        "steps": [
                            {
                                "heading": "阶段 1：协同搬砖至共享内存",
                                "bullets": ["每个线程负责把对应坐标的元素从显存搬入 __shared__。"],
                                "focus": [0],
                                "narration": "第一阶段：全班同学分工协作，每个人只搬一个数字，瞬间合力把小矩阵块写满讲台黑板。"
                            },
                            {
                                "heading": "阶段 2：吹哨栅栏 __syncthreads()",
                                "bullets": ["所有线程必须到达同步点，防止跑得快的同学提前读取残缺黑板。"],
                                "focus": [1],
                                "narration": "第二阶段吹响同步哨音！所有工人必须停在同一道栅栏前，确保黑板已经完完整整写好。"
                            },
                            {
                                "heading": "阶段 3：片上高速乘加并循环滑窗",
                                "bullets": ["在 1 周期极速黑板前乘加，算完再次同步，滑向下一个 Tile。"],
                                "focus": [2, 3],
                                "narration": "第三阶段在黑板前高速乘加，算完再次吹哨确认，然后滑向下一个 Tile 重复迭代，优雅而极致！"
                            }
                        ]
                    }
                }
            },
            {
                "slide_id": 4,
                "title": "一句话口诀与小白课后自测",
                "slide_type": "summary_best_practice",
                "key_points": [
                    "核心口诀：显存太远如郊区，讲台黑板在眼前；分块搬入共享区，复用百遍快如飞！",
                    "同步口诀：黑板抄完先吹哨，算完再吹保平安！",
                    "小白自测：如果一个 Block 里的线程写了 if (tid == 0) { __syncthreads(); } 会怎样？"
                ],
                "narration_script": "学完分块矩阵乘法，你就已经掌握了高性能计算皇冠上的明珠算法！我们用一句顺口溜把这套心法封印进脑海：显存太远如郊区，讲台黑板在眼前；分块搬入共享区，复用百遍快如飞！同步屏障双保险，黑板写完算完都吹哨！最后留给大家一个致命的代码陷阱测试题：如果一个初学者在代码里写了一句：if (threadIdx.x == 0) { __syncthreads(); }，也就是只让 0 号同学去等哨音，其他人不进这个分支，程序会发生什么？千万警惕：__syncthreads() 绝对不能放在任何分支判断里面！因为同步屏障要求全班所有人必须全部到齐才能放行。如果你把它放在 if 里面，其他 31 个同学直接跳过去了，而 0 号同学在门口傻傻等全班同学到齐，结果永远等不来，整块显卡芯片瞬间陷入永久死锁（Deadlock），程序彻底卡死！所以切记：同步哨音，必须放在无条件执行的大路上，所有人一起听！下节课，我们将带大家走进 CPU 与 GPU 之间更高级的秘密武器——异步流与并发重叠！",
                "visual_spec": {
                    "layout": "collision_animation",
                    "code_badge": "",
                    "scene_plan": {
                        "schema": "plan-v2",
                        "kind": "boxes",
                        "slide_id": 4,
                        "title": "本讲核心心法与 __syncthreads 致命死锁禁忌",
                        "subtitle": "分块复用拉满吞吐，公共分支杜绝死锁",
                        "figure": {
                            "nodes": [
                                {"id": "p1", "label": "Shared Memory (讲台大黑板：数据复用神器)"},
                                {"id": "p2", "label": "Tile 滑块机制 (以空间换时间，把大矩阵切小)"},
                                {"id": "p3", "label": "禁忌警告：严禁在条件分支内放置 __syncthreads() 死锁！"}
                            ],
                            "edges": [
                                ["p1", "p2", "赋能"],
                                ["p2", "p3", "护航"]
                            ]
                        },
                        "steps": [
                            {
                                "heading": "共享内存：极致复用的终极法宝",
                                "bullets": ["把访存瓶颈转化为纯粹的计算吞吐，算力提升数十倍。"],
                                "focus": [0, 1],
                                "narration": "共享内存是打破显存带宽墙的终极法宝，分块算法让你的显卡从在路上发呆，真正变成算力猛兽。"
                            },
                            {
                                "heading": "死锁禁忌牢记心中",
                                "bullets": ["同步屏障全员必须可达，永远放在公共无条件控制流中！"],
                                "focus": [2],
                                "narration": "自测题禁忌印在心底：同步栅栏必须全员无条件同时路过，严防死锁，安全高效！"
                            }
                        ]
                    }
                }
            }
        ]
    },

    # =========================================================================
    # 08. Asynchronous Execution: 多流流水线与计算/传输重叠
    # =========================================================================
    "sec_008_asynchronous_execution": {
        "sec_id": "sec_008_asynchronous_execution",
        "topic": "异步执行与 CUDA Stream 多流流水线",
        "page_range": "P106-P130",
        "page_count": 25,
        "source": "pedagogy_zero_foundation",
        "slides": [
            {
                "slide_id": 1,
                "title": "小白之惑：为什么我的显卡在炒菜时，水龙头总在闲着？",
                "slide_type": "title_overview",
                "key_points": [
                    "默认状态的串行悲剧：把数据运去显存 → 发呆等运完 → 启动计算 → 发呆等算完 → 运回数据。",
                    "痛点：货车在 PCIe 跑时计算核心空转；计算核心满负荷时货车在车库发呆！",
                    "解药：CUDA Stream（流）——打造双流水线，让货车运货与厨房炒菜同时发生！"
                ],
                "narration_script": "我们前面讲过，把数据通过 PCIe 高速公路运进显卡，是一件非常消耗时间的事情。在最朴素的默认模式下，几乎所有初学者的代码都在经历这样一段悲剧的循环：先花 5 秒钟把第一批数据拉进显存，在这个漫长的 5 秒钟里，显卡里上万个计算核心全都抱头大睡，无所事事；好不容易数据到了，计算核心开始轰鸣计算，这时候那条昂贵的 PCIe 传输通道又彻底熄火，闲着吃灰。算完了再等运回数据，周而复始。这就好比一个厨房：买菜的时候燃气灶空着，炒菜的时候水龙头空着，洗碗的时候全员站着看戏，整体效率低得令人发指！今天这一节，我们将带大家认识如何利用 CUDA Stream（异步流），构建一条真正的工业级多流水线，把昂贵的传输时间彻底‘隐藏’在计算时间里！",
                "visual_spec": {
                    "layout": "collision_animation",
                    "code_badge": "",
                    "scene_plan": {
                        "schema": "plan-v2",
                        "kind": "timeline",
                        "slide_id": 1,
                        "title": "单流串行执行：巨大的空闲气泡 (Idle Bubble)",
                        "subtitle": "PCIe 传输绿块与 GPU 计算橙块互不重叠，互相傻等",
                        "figure": {
                            "rows": [
                                {
                                    "label": "默认单流 Stream 0",
                                    "segments": [
                                        {"start": 0.0, "end": 2.5, "label": "Memcpy 传输批次 1 (核心闲着)"},
                                        {"start": 2.5, "end": 5.0, "label": "Kernel 运算批次 1 (PCIe 闲着)"},
                                        {"start": 5.0, "end": 7.5, "label": "Memcpy 传输批次 2 (核心闲着)"},
                                        {"start": 7.5, "end": 10.0, "label": "Kernel 运算批次 2 (PCIe 闲着)"}
                                    ]
                                }
                            ]
                        },
                        "steps": [
                            {
                                "heading": "串行交替：轮流吃灰",
                                "bullets": ["一个干活另一个必定发呆，硬件总体利用率永远不足 50%。"],
                                "focus": [0],
                                "narration": "看这条串行时间轴：传输和计算交替进行，你干活时我吃灰，硬件综合利用率连一半都不到！"
                            }
                        ]
                    }
                }
            },
            {
                "slide_id": 2,
                "title": "生活大比方：炒菜同时洗新菜的后厨流水线",
                "slide_type": "metaphor_sketch",
                "key_points": [
                    "单流同步 = 一个笨厨师：洗完第一盘土豆，开火炒；炒熟装盘，再去水槽洗第二盘青菜；青菜炒熟再去洗肉！",
                    "多流异步 = 五星级饭店双人流水线：配菜员正在水槽洗第二盘青菜的同时，主厨锅里正在颠勺炒第一盘土豆！",
                    "核心真理：计算与传输并不冲突！GPU 硬件内部有独立的数据传输引擎（DMA）和独立的计算核心，完全可以两面开花！"
                ],
                "narration_script": "我们用厨房做饭的大比方把异步流水线彻底讲通。默认的单流同步，就像一个单打独斗的笨厨师。他先去水龙头底下洗第一盘土豆，洗完端上灶台点火炒；等第一道菜出锅装盘了，他关掉火，慢悠悠走到水槽开始洗第二盘青菜；青菜洗完了再开火炒第二道，炒完了再去切肉。这样一顿饭做下来要花三个小时，而且灶台有一半时间是凉的，水槽有一半时间是干的！那五星级大饭店是怎么操作的？饭店里配了两个独立的岗位：一个配菜帮工，一个主厨。主厨手里颠着勺疯狂翻炒第一道宫保鸡丁的时候，配菜帮工根本不用等主厨，他在水龙头底下同时麻利地清洗第二道水煮鱼的原材料！等主厨第一道菜出锅的同一秒，第二道菜的原料已经洗好切好递到了手边，主厨立刻下锅翻炒，同时帮工马不停蹄开始切第三道菜！大家看，洗菜也就是数据传输（PCIe），炒菜也就是核心计算（Kernel），两个动作在时间轴上完全重叠（Overlap），洗菜的时间被完全‘藏’在了炒菜的时间里，整顿饭的总耗时直接缩短了一半！",
                "visual_spec": {
                    "layout": "collision_animation",
                    "code_badge": "",
                    "scene_plan": {
                        "schema": "plan-v2",
                        "kind": "compare",
                        "slide_id": 2,
                        "title": "后厨运作模式对比：单人串行 vs 异步多流流水线",
                        "subtitle": "洗菜炒菜轮流等（时间耗光） vs 炒第一道同时洗第二道（延迟隐藏）",
                        "figure": {
                            "left": {
                                "title": "单流同步：笨厨师单人干",
                                "lines": [
                                    "1. 水龙头下洗菜 (总线满，灶台冷)",
                                    "2. 灶台开火炒菜 (灶台热，水龙头关)",
                                    "3. 菜熟出锅装盘",
                                    "4. 重新走回水槽洗第二盘菜"
                                ]
                            },
                            "right": {
                                "title": "多流异步：五星后厨流水线",
                                "lines": [
                                    "Stream 0: 主厨正在颠勺翻炒批次 1",
                                    "Stream 1: 帮工同时在水槽清洗批次 2",
                                    "时间轴上完美重叠 (Overlap)",
                                    "数据传输时间被 100% 免费抹平！"
                                ]
                            }
                        },
                        "steps": [
                            {
                                "heading": "硬件具备双通道独立引擎",
                                "bullets": ["显卡拥有独立的 DMA 传输控制器和独立的 SM 计算阵列。"],
                                "focus": [1],
                                "narration": "在硬件上，显卡专门配备了独立的 DMA 拷贝引擎和计算核心，它们本来就是两个物理硬件，天生支持同时运转！"
                            },
                            {
                                "heading": "延迟隐藏：免费的午餐",
                                "bullets": ["把大任务切分成多批次分片，计算与传输错开并发。"],
                                "focus": [0, 1],
                                "narration": "把原本庞大的数据切成几个小分片，一边算上一个分片，一边运下一个分片，把传输时间彻底藏进计算里！"
                            }
                        ]
                    }
                }
            },
            {
                "slide_id": 3,
                "title": "动态推演：Stream 0 与 Stream 1 的无缝重叠",
                "slide_type": "manim_physics_demo",
                "key_points": [
                    "分片流水线（Chunk Pipeline）：把大任务分成 Chunk 0、Chunk 1、Chunk 2...",
                    "Stream 0 运送 Chunk 0 完毕，立刻启动 Kernel 0 计算；",
                    "与此同时，Stream 1 启动运送 Chunk 1，两条时间轴无缝嵌合，空闲气泡彻底消除！"
                ],
                "narration_script": "我们通过两条时间轴的动画推演，直观透视无缝重叠的奇迹。屏幕上方是 Stream 0，下方是 Stream 1。我们把原本 100MB 的大数组分成前后两个 50MB 的小块。在时刻 0 到时刻 2，Stream 0 率先开跑，把第一块数据运入显存。在时刻 2 的这个瞬间，奇迹开始了：Stream 0 的数据已经到位，它立刻启动 GPU 计算核心开工；与此同时，计算核心在忙碌，但 PCIe 传输通道空下来了，Stream 1 毫不犹豫地接管传输通道，开始把第二块数据拉进显存！大家看屏幕中间时刻 2 到时刻 4 的这个区间：上面是绿色的正在全速计算的 Kernel 0，下面是蓝色的正在全速运货的 Memcpy 1，两个物理引擎同时满载，彼此丝毫不干涉！原本两个阶段需要各花 4 秒总共 8 秒，现在通过错位重叠，总耗时直接被压缩到了 6 秒！只要切的分片足够细腻，所有的传输时间就像蒸发了一样，这就是高性能计算里最经典的‘延迟隐藏’！",
                "visual_spec": {
                    "layout": "collision_animation",
                    "code_badge": "cudaStream_t s0, s1;\ncudaStreamCreate(&s0); cudaStreamCreate(&s1);\n// 分片交错提交到两个独立流中！",
                    "scene_plan": {
                        "schema": "plan-v2",
                        "kind": "timeline",
                        "slide_id": 3,
                        "title": "双流异步流水线：计算与数据传输的完美时间重叠",
                        "subtitle": "Stream 0 计算 Chunk 0 的同时 ──完全重叠──> Stream 1 传输 Chunk 1",
                        "figure": {
                            "rows": [
                                {
                                    "label": "Stream 0 队列",
                                    "segments": [
                                        {"start": 0.0, "end": 2.5, "label": "Memcpy Chunk 0 (拉货)"},
                                        {"start": 2.5, "end": 6.5, "label": "Kernel Chunk 0 (颠勺翻炒)"},
                                        {"start": 6.5, "end": 8.0, "label": "Memcpy 回传 0"}
                                    ]
                                },
                                {
                                    "label": "Stream 1 队列",
                                    "segments": [
                                        {"start": 2.5, "end": 5.0, "label": "Memcpy Chunk 1 (同时洗菜)"},
                                        {"start": 6.5, "end": 9.5, "label": "Kernel Chunk 1 (接力翻炒)"},
                                        {"start": 9.5, "end": 10.0, "label": "Memcpy 回传 1"}
                                    ]
                                }
                            ]
                        },
                        "steps": [
                            {
                                "heading": "阶段 1：首批装载启动流水线",
                                "bullets": ["Stream 0 首先装载 Chunk 0，启动整个流水线的齿轮。"],
                                "focus": [0],
                                "narration": "流水线启动：Stream 0 率先把第 0 块原料送进厨房，点火进入计算状态。"
                            },
                            {
                                "heading": "阶段 2：重叠黄金期（算 0 运 1）",
                                "bullets": ["Kernel 0 与 Memcpy 1 在时间轴上完美并行，互不干扰！"],
                                "focus": [0, 1],
                                "narration": "进入重叠黄金期！Stream 0 算第 0 块，Stream 1 运第 1 块，算力与总线同时跑满，气泡彻底消灭！"
                            }
                        ]
                    }
                }
            },
            {
                "slide_id": 4,
                "title": "一句话口诀与小白课后自测",
                "slide_type": "summary_best_practice",
                "key_points": [
                    "核心口诀：单流傻等串行过，双流并发不闲着；炒菜同时洗新菜，传输计算齐重叠！",
                    "避坑铁律：要想实现真正的异步传输，主机内存必须使用锁页内存（cudaMallocHost）！",
                    "小白自测：在同一个 Stream 里提交的两个 Kernel，它们会同时并发执行吗？"
                ],
                "narration_script": "学完异步执行，我们用一句口诀封印今天的心智模型：单流傻等串行过，双流并发不闲着；炒菜同时洗新菜，传输计算齐重叠！不过在这里一定要送给小白一句价值千金的避坑铁律：如果你想让 cudaMemcpyAsync 真正异步跑起来，你主机端的内存千万不能用普通的 malloc 申请，必须使用 cudaMallocHost 申请所谓的‘锁页内存’（Pinned Memory）！因为普通内存操作系统随时会把它换页到硬盘上，显卡不敢异步偷拿；只有锁定物理页，显卡的 DMA 引擎才能在后台放心地自己去拉货！最后留给大家一个 5 秒自测题：如果在同一个 Stream 0 队列里先后提交了 Kernel A 和 Kernel B，它们俩会在显卡里同时并发跑吗？答案是：绝对不会！因为同一个 Stream 是一个严格先进先出的单向队列，里面的任务必须严格按顺序排队执行；只有把任务扔进不同的 Stream，它们才能在硬件允许的情况下并驾齐驱！下节课，我们将带大家认识一种神奇的懒人内存——统一内存与智能顺丰快递！",
                "visual_spec": {
                    "layout": "collision_animation",
                    "code_badge": "",
                    "scene_plan": {
                        "schema": "plan-v2",
                        "kind": "boxes",
                        "slide_id": 4,
                        "title": "本讲核心心法与 Stream 队列执行真谛",
                        "subtitle": "同流严格排队串行 ──跨流具备并发可能",
                        "figure": {
                            "nodes": [
                                {"id": "s1", "label": "同一个 Stream：内部严格按提交顺序串行排队"},
                                {"id": "s2", "label": "不同的 Stream：彼此独立，硬件有空则并发重叠"},
                                {"id": "s3", "label": "锁页内存 Pinned Memory：异步 DMA 传输的先决基石"}
                            ],
                            "edges": [
                                ["s1", "s2", "对比"],
                                ["s2", "s3", "依赖"]
                            ]
                        },
                        "steps": [
                            {
                                "heading": "同流串行，跨流并发",
                                "bullets": ["Stream 内部是队列，跨 Stream 才是并行的舞台。"],
                                "focus": [0, 1],
                                "narration": "永远记住：同一个 Stream 内部永远严格按顺序排队，只有跨不同的 Stream，并发重叠的大戏才会上演！"
                            },
                            {
                                "heading": "锁页内存基石",
                                "bullets": ["使用 cudaMallocHost 固定物理内存，确保后台 DMA 顺利穿透。"],
                                "focus": [2],
                                "narration": "锁页内存是异步流水线不可或缺的基石，掌握了多流重叠，你就正式迈入了 GPU 性能优化的高手殿堂！"
                            }
                        ]
                    }
                }
            }
        ]
    },

    # =========================================================================
    # 09. Unified and System Memory: 统一内存与智能顺丰快递
    # =========================================================================
    "sec_009_unified_and_system_memory": {
        "sec_id": "sec_009_unified_and_system_memory",
        "topic": "统一内存与智能缺页异常 (Unified Memory)",
        "page_range": "P131-P160",
        "page_count": 30,
        "source": "pedagogy_zero_foundation",
        "slides": [
            {
                "slide_id": 1,
                "title": "小白之惑：每次都要搬运内存烦死了，有没有懒人神器？",
                "slide_type": "title_overview",
                "key_points": [
                    "新手噩梦：malloc、cudaMalloc、cudaMemcpy、cudaFree，指针多到让人抓狂！",
                    "渴望：能不能只申请一个指针，CPU 能直接读写，GPU 也能直接读写？",
                    "终极解药：Unified Memory（统一内存）—— cudaMallocManaged！"
                ],
                "narration_script": "学到这里，很多被指针和内存拷贝折磨得痛不欲生的同学，心里肯定都在疯狂吐槽：写个 CUDA 程序也太繁琐了吧！先要在 CPU 申请一个 h_data 指针，再在 GPU 申请一个 d_data 指针，然后算完这一步运过去，算完下一步运回来，一旦少写一个 cudaFree，显存直接泄露卡死。难道就不能像普通 C 语言那样，我只申请一个公用的指针，CPU 想改就改，GPU 想算就算，中间什么卡车搬运都不用我管吗？答案是：不仅能，而且 NVIDIA 早在十年前就为你准备好了一套超级懒人神器——统一内存 Unified Memory！只要换掉一行 API，繁琐的显存搬运瞬间烟消云散！今天我们就来看看，这个黑科技背后到底藏着怎样的魔法！",
                "visual_spec": {
                    "layout": "collision_animation",
                    "code_badge": "",
                    "scene_plan": {
                        "schema": "plan-v2",
                        "kind": "boxes",
                        "slide_id": 1,
                        "title": "统一虚拟地址空间 (UVA / Unified Memory)",
                        "subtitle": "CPU 与 GPU 共享同一套指针标签，告别双份繁琐维护",
                        "figure": {
                            "nodes": [
                                {"id": "ptr", "label": "单一虚拟指针 ptr (两端可见相同地址)"},
                                {"id": "cpu_side", "label": "CPU 核心 (普通指针解引用 *ptr)"},
                                {"id": "gpu_side", "label": "GPU 核心群 (核函数内直接读写 ptr[i])"},
                                {"id": "page_mgr", "label": "硬件页迁移引擎 (幕后顺丰管家)"}
                            ],
                            "edges": [
                                ["cpu_side", "ptr", "读写"],
                                ["gpu_side", "ptr", "读写"],
                                ["ptr", "page_mgr", "底层按需调度"]
                            ]
                        },
                        "steps": [
                            {
                                "heading": "一个指针两端通用",
                                "bullets": ["用 cudaMallocManaged 申请一块内存，CPU 和 GPU 共享同一把钥匙。"],
                                "focus": [0, 1, 2],
                                "narration": "统一内存的核心魅力在于单一指针：用托管 API 申请一次，CPU 和 GPU 拿到同一把钥匙，两端都能直接读写！"
                            },
                            {
                                "heading": "幕后英雄：硬件页迁移",
                                "bullets": ["程序员不再手动写 cudaMemcpy，全部交由底层硬件引擎按需空投。"],
                                "focus": [3],
                                "narration": "你再也不用手动写复杂的 cudaMemcpy，幕后的硬件页迁移引擎会在底层悄悄为你搞定一切！"
                            }
                        ]
                    }
                }
            },
            {
                "slide_id": 2,
                "title": "生活大比方：智能顺丰按需空投快递",
                "slide_type": "metaphor_sketch",
                "key_points": [
                    "传统显存 = 自己亲自雇大卡车搬家：每次出门前，必须自己计算行李大小，清点上车，到了卸货。",
                    "统一内存 = 全自动顺丰次日达管家：两栋房子共用一套物品清单，东西放在哪里你不用操心。",
                    "缺页异常（Page Fault）：当你在海南房子翻抽屉发现没有衣服时，顺丰管家立刻触发空投，瞬间把衣服从北京送到你海南工位！"
                ],
                "narration_script": "我们用顺丰快递的生活比喻把统一内存的机制一秒讲透。过去传统的 cudaMemcpy，就像你自己亲自雇货车搬家。你人在北京总部，现在要去三亚代工厂度假办公，你必须亲自数清楚有几个箱子，雇卡车装箱，一路颠簸运去三亚；等度假结束，你再亲自把箱子搬上卡车拉回北京。只要有一趟忘装行李，整个工作就彻底瘫痪。而统一内存是什么？统一内存就像你雇了一个全天候智能顺丰管家！你在北京写字楼和三亚海景房共用同一套衣柜清单。你人在北京写字楼工作时，清单上的文件全在你的手边桌上；当你坐飞机瞬间降落到三亚海景房，你手里的钥匙完全不变，你一拉开三亚工位的抽屉，发现里面暂时是空的。这时候神奇的一幕发生了：系统硬件立刻触发一个‘缺页异常’（Page Fault），顺丰管家瞬间警觉：‘报告！老板人在三亚要看第 5 号文件！’顺丰后台用光速把第 5 号文件打包，顺着 PCIe 高速通道瞬间空投进三亚的抽屉里！整个过程全自动按需发生，你甚至感觉不到它的存在！",
                "visual_spec": {
                    "layout": "collision_animation",
                    "code_badge": "",
                    "scene_plan": {
                        "schema": "plan-v2",
                        "kind": "compare",
                        "slide_id": 2,
                        "title": "内存管理哲学演进：手动卡车搬运 vs 顺丰按需空投",
                        "subtitle": "苦哈哈手动算字节对齐 (易错) vs 优雅的硬件按需缺页迁移 (省心)",
                        "figure": {
                            "left": {
                                "title": "传统显式管理：自己搬家",
                                "lines": [
                                    "malloc 申请主机内存",
                                    "cudaMalloc 申请设备显存",
                                    "cudaMemcpy 手动搬运两趟",
                                    "两处释放，稍有不慎内存泄漏"
                                ]
                            },
                            "right": {
                                "title": "统一内存：全自动顺丰管家",
                                "lines": [
                                    "只调用一行 cudaMallocManaged",
                                    "CPU 直接填数据，GPU 直接跑核函数",
                                    "缺页异常 Page Fault 按需换页",
                                    "代码量骤降 60%，开发心智极度轻松"
                                ]
                            }
                        },
                        "steps": [
                            {
                                "heading": "传统模式：维护双份心智负担",
                                "bullets": ["程序员既要管算法，又要当搬家队长，极度心累。"],
                                "focus": [0],
                                "narration": "传统模式下程序员既要研究高深算法，又得当全职搬家队长，精神内耗极其严重。"
                            },
                            {
                                "heading": "统一模式：回归算法本质",
                                "bullets": ["把数据搬运彻底交还给芯片硬件，一行代码解决所有战斗！"],
                                "focus": [1],
                                "narration": "统一内存让一切回归算法本身：只管申请和使用，底层的物理搬家全部交由硬件顺丰按需调度！"
                            }
                        ]
                    }
                }
            },
            {
                "slide_id": 3,
                "title": "白话看代码：一行搞定内存分配与避坑",
                "slide_type": "code_diff",
                "key_points": [
                    "核心代码：cudaMallocManaged(&data, bytes); 替代原有的两套 malloc！",
                    "同步铁律：GPU 算完后，CPU 读之前，必须加上 cudaDeviceSynchronize()！",
                    "原因：内核启动是异步的，不吹哨等 GPU 算完，CPU 就抢着去读，读出来的全是半成品脏数据！"
                ],
                "narration_script": "大家看屏幕上的极简统一内存代码，简直舒服得像诗一样！第一行：cudaMallocManaged(&data, bytes)。就这么简简单单一句话，一个既能在 CPU 跑、又能在 GPU 跑的通用指针 data 就诞生了！第二步：CPU 的 for 循环直接给 data[i] 赋值填数，不需要任何中间卡车搬运；第三步：核函数 add<<<grids, blocks>>>(data) 直接开工，把 data 传进去原地计算；但是请大家睁大双眼，盯紧屏幕上标红的第四行代码：cudaDeviceSynchronize()！这是统一内存唯一的保命警戒线！因为 CPU 把任务扔给 GPU 后，CPU 自己是不会停下来的。如果你不写这句同步吹哨，CPU 紧接着就会去读 data 的数据，而这时候 GPU 工人们可能才算到一半，CPU 就会一头撞在正在施工的工地上，读出残缺不全的脏数据！所以记死这条铁律：统一内存写完核函数，必须吹一声哨 cudaDeviceSynchronize()，等外包工厂把活干利索了，CPU 才能放心地去验收成果！",
                "visual_spec": {
                    "layout": "collision_animation",
                    "code_badge": "cudaMallocManaged(&data, bytes);\n// CPU 直接填数 → GPU 直接计算 → 必须同步！\ncudaDeviceSynchronize();",
                    "scene_plan": {
                        "schema": "plan-v2",
                        "kind": "code",
                        "slide_id": 3,
                        "title": "白话代码拆解：统一内存标准骨架与同步屏障",
                        "subtitle": "极简托管申请 ──直接跨端计算 ──必须设备同步！",
                        "figure": {
                            "lines": [
                                "cudaMallocManaged(&data, bytes); // 1. 懒人托管申请",
                                "for(int i=0; i<N; i++) data[i] = 1; // 2. CPU 直接原地赋值",
                                "addKernel<<<grids, blocks>>>(data); // 3. GPU 原地直接开算",
                                "cudaDeviceSynchronize(); // 4. 必须吹哨！等 GPU 全员收工",
                                "for(int i=0; i<N; i++) check(data[i]); // 5. CPU 放心验收",
                                "cudaFree(data); // 6. 统一释放一块内存"
                            ],
                            "language": "CUDA C++"
                        },
                        "steps": [
                            {
                                "heading": "第 1-3 步：行云流水的极简写法",
                                "bullets": ["申请一次，两边直接用，再也没有任何手动 Memcpy 代码！"],
                                "focus": [0, 1, 2],
                                "narration": "前三行行云流水：申请一块托管内存，CPU 原地填数，GPU 直接点火开算，没有任何多余废话。"
                            },
                            {
                                "heading": "第 4 步：必须添加的同步安全栓",
                                "bullets": ["cudaDeviceSynchronize() 确保 GPU 彻底落笔交卷。"],
                                "focus": [3],
                                "narration": "第四行是绝对不可省略的安全栓：必须吹哨等显卡完全落笔，CPU 才能安全验收，否则必出脏读灾难！"
                            }
                        ]
                    }
                }
            },
            {
                "slide_id": 4,
                "title": "一句话口诀与小白课后自测",
                "slide_type": "summary_best_practice",
                "key_points": [
                    "核心口诀：指针通用省心力，底层顺丰自动送；算完切记先同步，告别繁琐 Memcpy！",
                    "进阶锦囊：如果数据量极庞大，可以提前用 cudaMemPrefetchAsync 预热通知顺丰先送货！",
                    "小白自测：统一内存为什么有时候第一次运行会比手写 Memcpy 稍微慢一丁点？"
                ],
                "narration_script": "学完统一内存，我们用一句口诀封存这个懒人利器：指针通用省心力，底层顺丰自动送；算完切记先同步，告别繁琐 Memcpy！最后留给大家一个触碰体系结构灵魂的小白思考题：很多同学在做基准测试时会发现，统一内存第一次跑的时候，偶尔会比手动写 cudaMemcpy 慢上那么一丢丢，这是为什么呢？答案就是我们刚才讲的顺丰按需空投！手动写 cudaMemcpy，是提前把卡车塞满一次性整车运过去；而统一内存一开始是空的，当 GPU 每一个线程算到某个数据时，硬件发现没有，才临时触发一次缺页中断把这页纸快递送过来。这一个个零散的缺页中断加在一起，就产生了轻微的动态开销。当然，NVIDIA 也早就想到了这一点，它为你提供了一个叫 cudaMemPrefetchAsync 的预取函数，相当于提前给顺丰打个电话：‘明早八点我要用，今晚先把货全车空投过去！’这样一来，便利性与极致性能便实现了完美的双向奔赴！下节课，我们将带大家认识 CUDA 世界的总建造师——NVCC 编译器！",
                "visual_spec": {
                    "layout": "collision_animation",
                    "code_badge": "",
                    "scene_plan": {
                        "schema": "plan-v2",
                        "kind": "boxes",
                        "slide_id": 4,
                        "title": "本讲核心心法：统一内存哲学与预取优化",
                        "subtitle": "零心智负担极速原型 ──进阶预取打满吞吐",
                        "figure": {
                            "nodes": [
                                {"id": "u1", "label": "原型开发首选：cudaMallocManaged (代码精简极致)"},
                                {"id": "u2", "label": "同步底线：cudaDeviceSynchronize (防脏读死穴)"},
                                {"id": "u3", "label": "进阶打满：cudaMemPrefetchAsync (提前预热消灭缺页中断)"}
                            ],
                            "edges": [
                                ["u1", "u2", "必须配套"],
                                ["u2", "u3", "极致进阶"]
                            ]
                        },
                        "steps": [
                            {
                                "heading": "开发敏捷性飞跃",
                                "bullets": ["在写原型和复杂数据结构（如树、链表）时，统一内存是无敌神技。"],
                                "focus": [0, 1],
                                "narration": "在实现复杂图结构和快速算法原型时，统一内存能为你省下成百上千行恶心枯燥的搬家代码。"
                            },
                            {
                                "heading": "预取指令消除抖动",
                                "bullets": ["配合 Prefetch 预取，既能享受统一指针的优雅，又能享受原生吞吐！"],
                                "focus": [2],
                                "narration": "最后配合异步预取指令，把顺丰快递升级为全速专机直达，代码优雅与极致性能两者兼得！"
                            }
                        ]
                    }
                }
            }
        ]
    },

    # =========================================================================
    # 010. NVCC The NVIDIA CUDA Compiler: 编译全链路与胖二进制
    # =========================================================================
    "sec_010_nvcc_the_nvidia_cuda_compiler": {
        "sec_id": "sec_010_nvcc_the_nvidia_cuda_compiler",
        "topic": "NVCC 编译全链路与跨架构 Fatbin 胖二进制",
        "page_range": "P161-P180",
        "page_count": 20,
        "source": "pedagogy_zero_foundation",
        "slides": [
            {
                "slide_id": 1,
                "title": "小白之惑：.cu 文件既有 C++ 又有显卡代码，编译器怎么认？",
                "slide_type": "title_overview",
                "key_points": [
                    "疑问：一个 .cu 源代码里，上面写着普通的 C++ main 函数，下面写着三尖括号的 GPU 核函数，编译器不会精神分裂吗？",
                    "真相：NVCC 根本不是单一编译器，而是一个总指挥交警调度员！",
                    "核心机制：兵分两路——CPU 代码给本地 C++ 编译器，GPU 代码送入微架构汇编流水线！"
                ],
                "narration_script": "大家在刚写 CUDA 代码时，一定会感到非常不可思议：我们写的文件后缀是 .cu，在同一个文件里，上半部分是地地道道的普通 C++ 语法，有 main 函数，有 cout 打印；下半部分却突然画风突变，冒出了三个尖括号、__global__ 和 blockIdx 这种显卡天书。如果直接把这个文件扔给电脑上的 GCC 或者微积分 MSVC 编译器，编译器立刻就会被吓疯，报出一万个语法错误。但是只要敲下 nvcc 命令，它居然顺畅无阻地生成了可执行文件！NVCC 到底施了什么魔法？它到底是一个怎样的编译器？今天这最后一节，我们将带大家透视 CUDA 世界的幕后总工程师——NVCC 编译器，看看它到底是如何把这份中英双语代码完美翻译成能在各种显卡上狂奔的硬件二进制文件的！",
                "visual_spec": {
                    "layout": "collision_animation",
                    "code_badge": "",
                    "scene_plan": {
                        "schema": "plan-v2",
                        "kind": "boxes",
                        "slide_id": 1,
                        "title": "NVCC 异构分离流水线：兵分两路的交警大队长",
                        "subtitle": "输入 .cu 混合源文件 ──中途剥离──> Host 路径与 Device 路径各自开拔",
                        "figure": {
                            "nodes": [
                                {"id": "cu_file", "label": "混合源文件 .cu (中英双语混合菜单)"},
                                {"id": "nvcc", "label": "NVCC 调度总指挥 (分拣交警大队长)"},
                                {"id": "host_cc", "label": "Host 编译器 GCC / MSVC (生成 CPU 机器码)"},
                                {"id": "device_cc", "label": "Device 编译流水线 (生成 PTX 与 SASS)"},
                                {"id": "fatbin", "label": "Fatbin 胖二进制打包融合 (生成最终 .exe)"}
                            ],
                            "edges": [
                                ["cu_file", "nvcc", "提交源码"],
                                ["nvcc", "host_cc", "剥离出普通 C++"],
                                ["nvcc", "device_cc", "剥离出 GPU 核函数"],
                                ["host_cc", "fatbin", "合流封装"],
                                ["device_cc", "fatbin", "合流封装"]
                            ]
                        },
                        "steps": [
                            {
                                "heading": "中英文混合源码提交",
                                "bullets": ["一个文件容纳两种完全不同的执行环境语义。"],
                                "focus": [0],
                                "narration": "混合文件送达，NVCC 面对的是一份既有 CPU 逻辑又有 GPU 执行逻辑的双语剧本。"
                            },
                            {
                                "heading": "兵分两路剥离派发",
                                "bullets": ["属于 CPU 的给本机的 GCC/MSVC，属于显卡的进专属显卡工具链。"],
                                "focus": [1, 2, 3],
                                "narration": "NVCC 充当分拣交警：属于 CPU 的段落直接扔给本机的 GCC 或 MSVC；属于显卡的核函数送进专属设备编译链。"
                            },
                            {
                                "heading": "两路兵马最终合流",
                                "bullets": ["把两边生成的机器码打包成一个整体的可执行程序。"],
                                "focus": [4],
                                "narration": "最后两路产物在一个大熔炉里会师，打包成一个在 Windows 或 Linux 上直接双击就能跑的最终文件！"
                            }
                        ]
                    }
                }
            },
            {
                "slide_id": 2,
                "title": "生活大比方：中英双语菜单与多功能翻译官",
                "slide_type": "metaphor_sketch",
                "key_points": [
                    ".cu 文件 = 一本中英双语混合菜单：上面写着中国大厨（CPU）的指令，下面写着法国西点师（GPU）的配方。",
                    "NVCC = 餐厅大堂经理：它自己不掌勺，而是把中文菜单撕下来送进中餐后厨，把法文菜单撕下来送进西点烘焙房！",
                    "PTX 虚拟汇编 = 联合国的标准英语说明书：不管将来换哪个西点师，大家都能看懂这份通用英语配方。",
                    "Cubin 硬件机器码 = 针对当前具体烤箱型号（比如 4090 芯片）量身定制的机器按键说明！"
                ],
                "narration_script": "我们用国际大餐厅的绝妙比喻把 NVCC 的全链路彻底讲活。想象你在米其林餐厅写了一本中法双语菜单，这就是 .cu 文件。前半部分写着中国大厨的炒菜要求，后半部分写着法国顶级面点师的烘焙秘方。NVCC 是餐厅的帅气大堂经理。大堂经理看到这本菜单，手脚极快地拿剪刀一裁：‘中文炒菜这部分，送去隔壁中餐后厨让老王炒！’老王就是本机的 GCC 或者微软 MSVC 编译器。那后半部分法国面点配方怎么处理呢？法国西点师很挑剔，有的人用老式烤箱，有的人用最新款的 4090 高压烤箱。大堂经理为了让这个配方永远不失传，先把它翻译成一份联合国的通用英语说明书，在 CUDA 里这叫做 PTX 虚拟汇编！不管是哪一年的显卡，大家都看得懂这个 PTX 英语说明书。然后再针对你厨房里当前真正插着的那台具体型号的烤箱，把它烧制成烤箱直接能执行的硬件微指令，这叫做 Cubin！最后，大堂经理把烤箱指令和老王的菜谱打包进同一个精美礼盒，这就是大名鼎鼎的 Fatbin 胖二进制！无论客人把这个礼盒带到哪里，开箱即食，畅通无阻！",
                "visual_spec": {
                    "layout": "collision_animation",
                    "code_badge": "",
                    "scene_plan": {
                        "schema": "plan-v2",
                        "kind": "compare",
                        "slide_id": 2,
                        "title": "从虚拟到物理：PTX 与 Cubin 的双重保障",
                        "subtitle": "PTX 通用虚拟中间码 (向前兼容) ──JIT 烧制──> Cubin 特定显卡机器码 (即开即用)",
                        "figure": {
                            "left": {
                                "title": "PTX (Parallel Thread Execution)",
                                "lines": [
                                    "虚拟通用汇编指令集 (人类可读的中间文本)",
                                    "不绑定任何特定显卡物理型号",
                                    "拥有强大的未来向前兼容性",
                                    "即使未来出了 6090 显卡，老程序也能自动编译运行！"
                                ]
                            },
                            "right": {
                                "title": "Cubin / SASS (真正硬件机器码)",
                                "lines": [
                                    "面向当前具体微架构（如 sm_89, sm_90）",
                                    "纯物理二进制机器码，不可再移植",
                                    "启动零开销，直接送入 SM 执行单元",
                                    "追求极致运行速度的首选产物"
                                ]
                            }
                        },
                        "steps": [
                            {
                                "heading": "PTX：跨越时代的技术保险",
                                "bullets": ["把代码编译成虚拟中间表示，保证程序在十年后的新显卡上依然能跑。"],
                                "focus": [0],
                                "narration": "PTX 是跨越时代的保险：它是不依赖特定显卡的虚拟指令，保证哪怕未来出了全新显卡，老程序也能自动重新编译跑通。"
                            },
                            {
                                "heading": "Cubin：当下物理极致速度",
                                "bullets": ["针对眼前的显卡烧制纯机器码，省去运行时的任何二次开销。"],
                                "focus": [1],
                                "narration": "而 Cubin 是为眼前显卡量身定做的纯硬件机器码，上电就能狂飙，把启动延迟彻底压到最低！"
                            }
                        ]
                    }
                }
            },
            {
                "slide_id": 3,
                "title": "胖二进制 Fatbin：为什么你的软件能跑在别人的各种显卡上？",
                "slide_type": "manim_physics_demo",
                "key_points": [
                    "Fatbin 核心理念：海纳百川，胖得可爱！",
                    "多合一打包：同一个可执行文件里，既塞了 30 系显卡的机器码，又塞了 40 系显卡的机器码，还兜底了一份 PTX 虚拟码！",
                    "智能匹配：程序启动时，驱动自动探测当前插的是什么卡，光速挑选最匹配的机器码运行！"
                ],
                "narration_script": "大家有没有想过一个非常现实的问题：很多商业游戏和 AI 软件，比如 PyTorch 或者大模型推理引擎，我们在官网上只下载了一个安装包，但它既能在别人的 RTX 3060 笔记本上跑，又能在你的 RTX 4090 台式机上跑，甚至在刚发布的最新架构显卡上也能跑。为什么它不需要为每一种显卡单独发一个安装包呢？答案全在一个‘胖’字——Fatbin 胖二进制！在编译阶段，NVCC 就像一个哆啦 A 梦的神奇口袋。你可以在编译参数里告诉它：给我编译一份针对 30 系 Ampere 架构的代码，再编译一份针对 40 系 Ada 架构的代码，最后再塞一份通用的 PTX 虚拟代码保底！NVCC 把这三份产物全部揉在一起，塞进最终的可执行程序里。这个文件体积虽然变大了一点，显得有点‘胖’，但它却拥有了神一般的兼容能力：无论用户插了什么显卡，驱动程序扫一眼硬件，立刻挑出最合适的那一份机器码秒速开跑；哪怕遇到没见过的未来新显卡，也能掏出保底的 PTX 当场烧制！这种极其优雅的工业设计，让 CUDA 生态建立起了全世界最深、最宽的护城河！",
                "visual_spec": {
                    "layout": "collision_animation",
                    "code_badge": "nvcc -gencode arch=compute_80,code=sm_80 \\\n     -gencode arch=compute_89,code=sm_89 \\\n     -gencode arch=compute_89,code=compute_89 app.cu",
                    "scene_plan": {
                        "schema": "plan-v2",
                        "kind": "boxes",
                        "slide_id": 3,
                        "title": "Fatbin 胖二进制结构：千人千面，全架构自适应",
                        "subtitle": "多架构物理机器码 (Cubin) ＋ 兜底虚拟说明书 (PTX) 打包封装",
                        "figure": {
                            "nodes": [
                                {"id": "app", "label": "Fatbin 胖二进制可执行文件"},
                                {"id": "c30", "label": "sm_86 (RTX 30 系列纯机器码)"},
                                {"id": "c40", "label": "sm_89 (RTX 40 系列纯机器码)"},
                                {"id": "c_ptx", "label": "compute_89 (PTX 虚拟汇编，保底未来)"},
                                {"id": "hw_detect", "label": "运行时硬件探测器 (自动挑选最优镜像)"}
                            ],
                            "edges": [
                                ["app", "c30", "内置"],
                                ["app", "c40", "内置"],
                                ["app", "c_ptx", "内置"],
                                ["app", "hw_detect", "启动探测匹配"]
                            ]
                        },
                        "steps": [
                            {
                                "heading": "多镜像打包：一身三用",
                                "bullets": ["把不同代际显卡的硬件机器码打包塞进同一个文件。"],
                                "focus": [0, 1, 2],
                                "narration": "胖二进制把不同代际显卡的硬件机器码全部塞进同一个文件，虽然体积略胖，但极度强悍。"
                            },
                            {
                                "heading": "PTX 保底未来",
                                "bullets": ["留一份虚拟汇编，即使面对未来全新发布的显卡也能自动即时编译。"],
                                "focus": [3],
                                "narration": "同时留一份 PTX 虚拟说明书在里面兜底，保证十年后的新显卡插上去依然能自动 JIT 编译运行！"
                            },
                            {
                                "heading": "运行时秒级自动匹配",
                                "bullets": ["驱动程序自动挑选最贴合当前物理芯片的执行镜像。"],
                                "focus": [4],
                                "narration": "软件一启动，驱动立刻按图索骥秒级挑选出最佳机器码，让普通用户彻底告别任何繁琐的配置噩梦！"
                            }
                        ]
                    }
                }
            },
            {
                "slide_id": 4,
                "title": "全课知识终极大复盘：从代码到硬件的闭环宇宙",
                "slide_type": "summary_best_practice",
                "key_points": [
                    "终极闭环：从老教授与小学生(CPU/GPU)，到年级与班级(Grid/Block)，从32座大巴(Warp)，到讲台黑板(Shared)，从炒菜流水线(Stream)到双语食谱(NVCC)！",
                    "核心真理：GPU 高性能计算从不神秘，一切技术全是对物理客观规律的通俗具象解决！",
                    "结语：恭喜你！你已经完整跨越了从零基础小白到洞悉 GPU 微架构全景的认知飞跃！"
                ],
                "narration_script": "同学们，走到了这里，让我们回过头，深情地看一眼这幅壮丽的 GPU 架构全景图！从第一节课的老教授与 5000 个小学生，到第二节课的年级、班级与座位号；从第三节课总部与远郊代工厂的 PCIe 卡车搬运，到第六节课 32 座大巴车上的广播喇叭与分支分化；从第七节课讲台黑板上的分块矩阵乘法，到第八节课炒菜同时洗新菜的多流流水线，再到统一内存的顺丰按需快递和今天 NVCC 的双语食谱大解密。大家是不是赫然发现：原本冷冰冰、晦涩难懂的体系结构天书，背后每一处设计，本质上全是人类用最朴素、最聪明的生活智慧，在物理硬件的极限边界上所做出的精妙取舍！你不再需要死记硬背任何公式，因为这一套完整立体的心智模型，已经深深烙印在了你的脑海中！恭喜大家，完成了一次从毫无经验的零基础小白，到能够透视芯片微观世界真理的伟大跃迁！愿大家带着这套清晰的心智图谱，在未来的高性能计算与人工智能星辰大海中，乘风破浪，一往无前！",
                "visual_spec": {
                    "layout": "collision_animation",
                    "code_badge": "",
                    "scene_plan": {
                        "schema": "plan-v2",
                        "kind": "boxes",
                        "slide_id": 4,
                        "title": "全书心智总闭环：零基础到微架构宗师",
                        "subtitle": "用生活直觉洞悉软硬件协同的永恒规律",
                        "figure": {
                            "nodes": [
                                {"id": "m1", "label": "任务层：教授 CPU 统筹，海量小学生 GPU 齐步走"},
                                {"id": "m2", "label": "组织层：年级 Grid → 班级 Block → 学生 Thread"},
                                {"id": "m3", "label": "执行层：32 座大巴 Warp 广播，杜绝分歧内耗"},
                                {"id": "m4", "label": "存储层：讲台黑板 Shared 极速复用，顺丰按需空投"},
                                {"id": "m5", "label": "系统层：多流流水线隐藏延迟，NVCC 胖二进制通赢"}
                            ],
                            "edges": [
                                ["m1", "m2", "拆分"],
                                ["m2", "m3", "调度"],
                                ["m3", "m4", "访存"],
                                ["m4", "m5", "闭环"]
                            ]
                        },
                        "steps": [
                            {
                                "heading": "五层心智宇宙完整落成",
                                "bullets": ["任务、组织、执行、存储、系统五大维度无缝贯通。"],
                                "focus": [0, 1, 2, 3, 4],
                                "narration": "五层心智宇宙完整落成：从任务、组织、执行、存储到系统编译，所有底层知识点完全形成闭环！"
                            },
                            {
                                "heading": "恭喜毕业：通往高性能高地",
                                "bullets": ["你已经具备了顶尖 GPU 架构师所必须拥有的物理空间直觉！"],
                                "focus": [0, 1, 2, 3, 4],
                                "narration": "恭喜你！你已经拥有了顶级 GPU 工程师的清晰物理直觉，欢迎真正走进壮丽的高性能计算殿堂！"
                            }
                        ]
                    }
                }
            }
        ]
    }
}


def get_pedagogical_deck_for_section(
    sec_id_or_title: str,
    section_data: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """
    Retrieves the curated, zero-foundation pedagogical deck matching the given sec_id or title.
    Returns a deep copy or normalized structure compliant with DeepPedagogicalDeckGenerator contract.
    """
    target = (sec_id_or_title or "").lower().strip()
    
    # 1. Exact match on known sec_id
    if target in PEDAGOGICAL_MASTER_DECKS:
        return _clone_deck(PEDAGOGICAL_MASTER_DECKS[target], section_data)
        
    # 2. Fuzzy / keyword match
    for key, deck in PEDAGOGICAL_MASTER_DECKS.items():
        if key in target:
            return _clone_deck(deck, section_data)
            
    # Keywords matching across chapters
    if any(k in target for k in ["001", "intro", "why", "difference", "cpu"]):
        return _clone_deck(PEDAGOGICAL_MASTER_DECKS["sec_001_introduction"], section_data)
    elif any(k in target for k in ["002", "model", "index", "grid", "dim", "threadidx", "block"]):
        return _clone_deck(PEDAGOGICAL_MASTER_DECKS["sec_002_programming_model"], section_data)
    elif any(k in target for k in ["003", "platform", "driver", "runtime", "host", "device", "03"]):
        return _clone_deck(PEDAGOGICAL_MASTER_DECKS["sec_003_the_cuda_platform"], section_data)
    elif any(k in target for k in ["004", "cuda_c", "vector", "add", "first", "04", "08"]):
        return _clone_deck(PEDAGOGICAL_MASTER_DECKS["sec_004_intro_to_cuda_c"], section_data)
    elif any(k in target for k in ["005", "python", "numba", "cupy", "05"]):
        return _clone_deck(PEDAGOGICAL_MASTER_DECKS["sec_005_intro_to_cuda_python"], section_data)
    elif any(k in target for k in ["006", "simt", "warp", "diverge", "branch", "lockstep", "06"]):
        return _clone_deck(PEDAGOGICAL_MASTER_DECKS["sec_006_writing_simt_kernels"], section_data)
    elif any(k in target for k in ["007", "tile", "gemm", "matrix", "matmul", "shared", "07", "13", "26"]):
        return _clone_deck(PEDAGOGICAL_MASTER_DECKS["sec_007_writing_tile_kernels"], section_data)
    elif any(k in target for k in ["008", "stream", "async", "overlap", "pipeline", "08", "21"]):
        return _clone_deck(PEDAGOGICAL_MASTER_DECKS["sec_008_asynchronous_execution"], section_data)
    elif any(k in target for k in ["009", "unified", "managed", "page", "fault", "09", "15"]):
        return _clone_deck(PEDAGOGICAL_MASTER_DECKS["sec_009_unified_and_system_memory"], section_data)
    elif any(k in target for k in ["010", "nvcc", "compiler", "ptx", "cubin", "fatbin", "10", "19"]):
        return _clone_deck(PEDAGOGICAL_MASTER_DECKS["sec_010_nvcc_the_nvidia_cuda_compiler"], section_data)

    # Default fallback to intro or model
    return _clone_deck(PEDAGOGICAL_MASTER_DECKS["sec_001_introduction"], section_data)


def _clone_deck(deck: Dict[str, Any], section_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    import copy
    cloned = copy.deepcopy(deck)
    if section_data:
        if "sec_id" in section_data:
            cloned["sec_id"] = section_data["sec_id"]
        if "title" in section_data:
            cloned["original_title"] = section_data["title"]
        if "start_page" in section_data and "end_page" in section_data:
            cloned["page_range"] = f"P{section_data['start_page']}-P{section_data['end_page']}"
            cloned["page_count"] = section_data.get("page_count", 1)
    return cloned
