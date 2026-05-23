"""
短视频配音模块 — 基于 Microsoft Edge TTS (edge-tts) 的免费中文配音工具。
不需要 API Key，只需网络连接即可使用。

功能：
  - 列出所有可用中文音色
  - 根据脚本情绪自动选音色（激昂/温和/活泼/沉稳）
  - 生成 MP3 音频文件
  - 支持语速调节（抖音口播推荐 1.1-1.3 倍速）

音色库 (edge-tts 中文推荐):
  男声新闻风: zh-CN-YunjianNeural   (云健，洪亮有力)
  男声温和:   zh-CN-YunxiNeural     (云希，温暖)
  女声活泼:   zh-CN-XiaoxiaoNeural  (晓晓，轻快)
  女声知性:   zh-CN-XiaoyiNeural    (晓伊，知性)
"""

import asyncio
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

# ============================================================
# 音色配置
# ============================================================

@dataclass
class Voice:
    """音色定义"""
    short_name: str
    full_name: str
    gender: str          # Male / Female
    style: str           # 激昂 / 温和 / 活泼 / 沉稳
    description: str     # 中文描述
    tags: list = field(default_factory=list)  # 适用场景标签


# 精选中文音色库（edge-tts 稳定可用）
VOICE_LIBRARY: dict[str, Voice] = {
    "yunjian": Voice(
        short_name="yunjian",
        full_name="zh-CN-YunjianNeural",
        gender="Male",
        style="激昂",
        description="云健 — 洪亮有力，适合新闻播报、赛事解说、热血内容",
        tags=["新闻", "赛事", "热血", "激情", "震撼"]
    ),
    "yunxi": Voice(
        short_name="yunxi",
        full_name="zh-CN-YunxiNeural",
        gender="Male",
        style="温和",
        description="云希 — 温暖柔和，适合情感故事、知识科普、旁白",
        tags=["故事", "科普", "情感", "温暖", "旁白"]
    ),
    "xiaoxiao": Voice(
        short_name="xiaoxiao",
        full_name="zh-CN-XiaoxiaoNeural",
        gender="Female",
        style="活泼",
        description="晓晓 — 轻快活泼，适合脱口秀、吐槽、娱乐内容",
        tags=["搞笑", "吐槽", "娱乐", "口播", "轻快"]
    ),
    "xiaoyi": Voice(
        short_name="xiaoyi",
        full_name="zh-CN-XiaoyiNeural",
        gender="Female",
        style="沉稳",
        description="晓伊 — 沉稳知性，适合财经分析、深度解读、商业内容",
        tags=["财经", "商业", "分析", "深度", "知性"]
    ),
    "yunyang": Voice(
        short_name="yunyang",
        full_name="zh-CN-YunyangNeural",
        gender="Male",
        style="活泼",
        description="云扬 — 年轻活力，适合综艺风格、短视频口播",
        tags=["综艺", "年轻", "活力", "短视频"]
    ),
    "xiaohan": Voice(
        short_name="xiaohan",
        full_name="zh-CN-XiaohanNeural",
        gender="Female",
        style="温和",
        description="晓涵 — 温婉亲切，适合美妆教程、生活记录、Vlog",
        tags=["美妆", "生活", "Vlog", "教程", "亲切"]
    ),
}

# 情绪关键词 → 推荐音色
EMOTION_KEYWORDS: dict[str, list[str]] = {
    "激昂": [
        "绝杀", "逆转", "疯狂", "燃", "炸裂", "暴利", "奇迹",
        "冠军", "决赛", "绝地", "逆袭", "热血", "震撼", "史诗",
        "起飞", "引爆", "冲破", "碾压", "狂飙", "暴涨", "涨停"
    ],
    "温和": [
        "温柔", "温暖", "治愈", "感动", "美好", "幸福", "陪伴",
        "日常", "生活", "记录", "小确幸", "慢生活", "岁月", "情怀"
    ],
    "活泼": [
        "笑死", "哈哈哈哈", "吐槽", "搞笑", "离谱", "绝了", "好家伙",
        "你猜", "你敢信", "没想到", "反转", "神操作", "骚操作", "太顶了",
        "整活", "破防", "麻了", "离谱他妈"
    ],
    "沉稳": [
        "分析", "深度", "揭秘", "底层", "逻辑", "本质", "真相",
        "数据", "研究", "报告", "趋势", "策略", "风险", "博弈",
        "解读", "复盘", "思考", "认知", "格局"
    ],
}


# ============================================================
# 情绪分析
# ============================================================

def analyze_emotion(script: str) -> tuple[str, float]:
    """分析脚本情绪，返回 (风格, 置信度)"""
    scores = {style: 0 for style in EMOTION_KEYWORDS}

    for style, keywords in EMOTION_KEYWORDS.items():
        for kw in keywords:
            if kw in script:
                scores[style] += 1

    # 标点辅助判断
    exclaim_count = script.count("！") + script.count("!")
    question_count = script.count("？") + script.count("?")
    if exclaim_count >= 2:
        scores["激昂"] += 1
    if question_count >= 2:
        scores["活泼"] += 1

    total = sum(scores.values())
    if total == 0:
        return "活泼", 0.0  # 默认活泼（短视频最常用）

    best = max(scores, key=scores.get)
    confidence = scores[best] / total
    return best, round(confidence, 2)


def pick_voice(script: str, preferred_gender: Optional[str] = None) -> Voice:
    """根据脚本自动选择音色"""
    style, confidence = analyze_emotion(script)

    # 选出匹配风格的音色
    candidates = [v for v in VOICE_LIBRARY.values() if v.style == style]

    # 如果指定了性别偏好，则过滤
    if preferred_gender:
        filtered = [v for v in candidates if v.gender == preferred_gender]
        if filtered:
            candidates = filtered

    if not candidates:
        candidates = [VOICE_LIBRARY["xiaoxiao"]]  # fallback

    # 返回第一个匹配的
    return candidates[0]


# ============================================================
# TTS 生成
# ============================================================

async def generate_audio(
    script: str,
    output_path: Optional[str] = None,
    voice: Optional[str] = None,
    rate: float = 1.2,
    auto_select: bool = True,
) -> dict:
    """
    生成配音音频。

    参数:
        script: 配音脚本文本
        output_path: 输出 mp3 路径，不传则自动生成
        voice: 音色 short_name (如 "xiaoxiao")，不传则自动选择
        rate: 语速倍率，抖音口播推荐 1.1-1.3
        auto_select: 是否根据脚本情绪自动选音色

    返回:
        dict: {
            "file": str,           # 音频文件绝对路径
            "voice": str,          # 使用的音色全名
            "voice_desc": str,     # 音色中文描述
            "style": str,          # 情绪风格
            "rate": float,         # 实际语速
            "duration_seconds": float,  # 音频时长
            "script_length": int,  # 脚本字数
        }
    """
    # 自动选音色
    if auto_select and voice is None:
        chosen = pick_voice(script)
        voice = chosen.short_name
    elif voice is None:
        voice = "xiaoxiao"

    voice_info = VOICE_LIBRARY.get(voice)
    if voice_info is None:
        raise ValueError(f"未知音色 '{voice}'，可用: {list(VOICE_LIBRARY.keys())}")

    full_voice_name = voice_info.full_name

    # 输出路径
    if output_path is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "out",
            f"voice_{voice}_{ts}.mp3"
        )

    out_dir = os.path.dirname(output_path)
    os.makedirs(out_dir, exist_ok=True)

    # 计算语速参数 (edge-tts 使用百分比字符串，如 "+20%" 表示 1.2 倍速)
    rate_pct = int((rate - 1.0) * 100)
    rate_str = f"+{rate_pct}%" if rate_pct >= 0 else f"{rate_pct}%"

    # 调用 edge-tts 生成音频
    cmd = [
        sys.executable, "-m", "edge_tts",
        "--voice", full_voice_name,
        "--rate", rate_str,
        "--text", script,
        "--write-media", output_path,
    ]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        err_msg = stderr.decode("utf-8", errors="replace")
        raise RuntimeError(f"edge-tts 生成失败 (code={proc.returncode}): {err_msg}")

    # 获取音频时长（用 ffprobe）
    duration = _get_mp3_duration(output_path)

    # 情绪分析
    style, conf = analyze_emotion(script)

    return {
        "file": os.path.abspath(output_path),
        "voice": full_voice_name,
        "voice_desc": voice_info.description,
        "style": style,
        "style_confidence": conf,
        "rate": rate,
        "duration_seconds": duration,
        "script_length": len(script),
    }


def _get_mp3_duration(filepath: str) -> float:
    """用 ffprobe 获取 MP3 时长（秒）"""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                filepath,
            ],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            info = json.loads(result.stdout)
            return float(info.get("format", {}).get("duration", 0))
    except Exception:
        pass
    return 0.0


# ============================================================
# 同步封装
# ============================================================

def speak(
    script: str,
    output_path: Optional[str] = None,
    voice: Optional[str] = None,
    rate: float = 1.2,
    auto_select: bool = True,
) -> dict:
    """同步版本 — 生成配音音频并返回结果字典"""
    return asyncio.run(
        generate_audio(
            script=script,
            output_path=output_path,
            voice=voice,
            rate=rate,
            auto_select=auto_select,
        )
    )


# ============================================================
# 工具函数
# ============================================================

def list_voices(style: Optional[str] = None, gender: Optional[str] = None):
    """列出可用中文音色，可按风格/性别筛选"""
    voices = list(VOICE_LIBRARY.values())
    if style:
        voices = [v for v in voices if v.style == style]
    if gender:
        voices = [v for v in voices if v.gender == gender]

    print(f"\n{'─' * 60}")
    print(f"  可用中文音色 ({len(voices)} 个)")
    print(f"{'─' * 60}")
    print(f"  {'简称':<12} {'性别':<6} {'风格':<6} 描述")
    print(f"  {'─' * 12} {'─' * 6} {'─' * 6} {'─' * 30}")
    for v in voices:
        print(f"  {v.short_name:<12} {v.gender:<6} {v.style:<6} {v.description}")
    print(f"{'─' * 60}\n")
    return voices


def preview_voices():
    """打印所有音色 + 情绪关键词表"""
    list_voices()
    print("情绪关键词映射:")
    for style, keywords in EMOTION_KEYWORDS.items():
        print(f"  {style}: {', '.join(keywords[:8])}...")
    print()


# ============================================================
# CLI 入口
# ============================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="短视频配音工具 (edge-tts 免费TTS)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python voice_actor.py                           # 用内置测试脚本生成配音
  python voice_actor.py --list                    # 列出所有中文音色
  python voice_actor.py --text "你的脚本内容"      # 自定义脚本
  python voice_actor.py --text "..." --voice xiaoxiao --rate 1.3  # 指定音色和语速
        """
    )

    parser.add_argument("--list", action="store_true", help="列出所有可用中文音色")
    parser.add_argument("--text", type=str, help="配音脚本文本")
    parser.add_argument("--voice", type=str, default=None, help="音色简称 (yunjian/yunxi/xiaoxiao/xiaoyi/yunyang/xiaohan)")
    parser.add_argument("--rate", type=float, default=1.2, help="语速倍率 (默认1.2，抖音推荐1.1-1.3)")
    parser.add_argument("--output", type=str, default=None, help="输出 MP3 文件路径")
    parser.add_argument("--gender", type=str, choices=["Male", "Female"], help="性别偏好")

    args = parser.parse_args()

    if args.list:
        preview_voices()
        sys.exit(0)

    # 脚本内容
    script = args.text
    if not script:
        # 内置测试脚本（U17 足球决赛）
        script = (
            "你猜这届U17决赛，中国队最后5分钟干了啥？"
            "全场被日本压着打，控球率不到三成。"
            "89分钟还落后1个球。"
            "补时最后一分钟，角球。"
            "你信他进了吗？"
        )
        print("未指定 --text，使用内置测试脚本:\n")
        print(f"  {script}\n")

    # 分析情绪
    style, conf = analyze_emotion(script)
    chosen = pick_voice(script, preferred_gender=args.gender)
    if args.voice:
        chosen = VOICE_LIBRARY.get(args.voice, chosen)

    print(f"情绪分析: {style} (置信度 {conf})")
    print(f"自动音色: {chosen.short_name} — {chosen.description}")
    print(f"语速: {args.rate}x")
    print(f"生成中...")

    result = speak(
        script=script,
        output_path=args.output,
        voice=args.voice or chosen.short_name,
        rate=args.rate,
        auto_select=not bool(args.voice),
    )

    print(f"\n{'=' * 50}")
    print(f"  生成完毕!")
    print(f"  {'─' * 30}")
    print(f"  文件: {result['file']}")
    print(f"  音色: {result['voice_desc']}")
    print(f"  风格: {result['style']}")
    print(f"  语速: {result['rate']}x")
    print(f"  时长: {result['duration_seconds']:.1f} 秒")
    print(f"  字数: {result['script_length']} 字")
    print(f"{'=' * 50}")
