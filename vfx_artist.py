#!/usr/bin/env python3
"""
VFX Artist — 短视频视觉特效模块

功能:
  1. 特效分类库 (文字/画面/转场/强调)
  2. 特效触发器 (脚本关键词 -> 特效标记)
  3. 剪映(CapCut)特效映射
  4. 视觉风格方案 (体育热血/悬疑揭秘/轻松生活)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import json
import re

# ============================================================
# 1. 特效分类库
# ============================================================

class VFXCategory(Enum):
    TEXT = "文字特效"
    VISUAL = "画面特效"
    TRANSITION = "转场特效"
    EMPHASIS = "强调特效"


class VFXIntensity(Enum):
    SUBTLE = "subtle"
    MODERATE = "moderate"
    STRONG = "strong"
    EXTREME = "extreme"


@dataclass
class EffectDef:
    """单个特效定义"""
    name: str               # 特效名称
    category: VFXCategory   # 分类
    description: str        # 描述
    params: dict = field(default_factory=dict)  # 可调参数
    intensity: VFXIntensity = VFXIntensity.MODERATE


# ---------- 文字特效 ----------
TEXT_EFFECTS = {
    "glow": EffectDef(
        name="glow",
        category=VFXCategory.TEXT,
        description="发光效果 — 文字边缘扩散光晕",
        params={
            "color": "#FFD700",        # 光晕颜色
            "blur_radius": 12,         # 模糊半径 px
            "opacity": 0.8,            # 透明度
            "spread": 0.3,             # 扩散比例
            "animate": "pulse",        # 动画: pulse / steady / flicker
        },
        intensity=VFXIntensity.MODERATE,
    ),
    "shadow": EffectDef(
        name="shadow",
        category=VFXCategory.TEXT,
        description="阴影效果 — 立体投影",
        params={
            "offset_x": 4,
            "offset_y": 4,
            "blur": 8,
            "color": "#000000",
            "opacity": 0.5,
        },
        intensity=VFXIntensity.SUBTLE,
    ),
    "stroke": EffectDef(
        name="stroke",
        category=VFXCategory.TEXT,
        description="描边效果 — 文字轮廓线",
        params={
            "width": 3,
            "color": "#FFFFFF",
            "join": "round",
        },
        intensity=VFXIntensity.MODERATE,
    ),
    "gradient_text": EffectDef(
        name="gradient_text",
        category=VFXCategory.TEXT,
        description="渐变文字 — 从color_start到color_end的色彩过渡",
        params={
            "color_start": "#FF6B35",
            "color_end": "#F7C948",
            "angle": 90,
            "animate": "flow",         # flow / static
        },
        intensity=VFXIntensity.MODERATE,
    ),
    "frosted_bg": EffectDef(
        name="frosted_bg",
        category=VFXCategory.TEXT,
        description="毛玻璃背景 — 文字背后的模糊遮罩",
        params={
            "blur_amount": 20,
            "bg_opacity": 0.3,
            "bg_color": "#FFFFFF",
            "corner_radius": 12,
        },
        intensity=VFXIntensity.SUBTLE,
    ),
}

# ---------- 画面特效 ----------
VISUAL_EFFECTS = {
    "shake": EffectDef(
        name="shake",
        category=VFXCategory.VISUAL,
        description="画面震动 — 水平和垂直快速抖动",
        params={
            "amplitude_x": 8,
            "amplitude_y": 6,
            "frequency": 15,           # Hz
            "duration_ms": 300,
            "decay": "ease_out",       # ease_out / linear / bounce
        },
        intensity=VFXIntensity.STRONG,
    ),
    "flash_white": EffectDef(
        name="flash_white",
        category=VFXCategory.VISUAL,
        description="闪白 — 瞬间全白画面再恢复",
        params={
            "duration_ms": 150,
            "peak_opacity": 1.0,
            "easing": "ease_out",
        },
        intensity=VFXIntensity.STRONG,
    ),
    "slow_motion": EffectDef(
        name="slow_motion",
        category=VFXCategory.VISUAL,
        description="慢动作 — 变速播放",
        params={
            "speed_ratio": 0.25,       # 原始速度的25%
            "smooth": "optical_flow",  # optical_flow / frame_blend
            "ramp_in_ms": 200,         # 缓入
            "ramp_out_ms": 300,        # 缓出
        },
        intensity=VFXIntensity.MODERATE,
    ),
    "speed_lines": EffectDef(
        name="speed_lines",
        category=VFXCategory.VISUAL,
        description="速度线 — 水平/放射状动态线条",
        params={
            "direction": "radial",     # radial / horizontal / vertical
            "line_count": 12,
            "line_width": 2,
            "color": "#FFFFFF",
            "opacity": 0.6,
            "animate": True,
            "speed": 1.2,
        },
        intensity=VFXIntensity.MODERATE,
    ),
    "chromatic_aberration": EffectDef(
        name="chromatic_aberration",
        category=VFXCategory.VISUAL,
        description="色差/色散 — RGB通道分离偏移",
        params={
            "r_offset": (3, 0),
            "b_offset": (-3, 0),
            "intensity": 0.5,
        },
        intensity=VFXIntensity.MODERATE,
    ),
    "bokeh": EffectDef(
        name="bokeh",
        category=VFXCategory.VISUAL,
        description="背景虚化 — 模拟浅景深散景",
        params={
            "blur_radius": 15,
            "bokeh_shape": "hexagon",  # circle / hexagon / star
            "threshold": 0.5,
        },
        intensity=VFXIntensity.SUBTLE,
    ),
    "vignette": EffectDef(
        name="vignette",
        category=VFXCategory.VISUAL,
        description="暗角 — 四周变暗聚焦中心",
        params={
            "intensity": 0.6,
            "roundness": 0.8,
            "feather": 0.5,
            "color": "#000000",
        },
        intensity=VFXIntensity.SUBTLE,
    ),
}

# ---------- 转场特效 ----------
TRANSITION_EFFECTS = {
    "glitch": EffectDef(
        name="glitch",
        category=VFXCategory.TRANSITION,
        description="故障风转场 — RGB分离+画面撕裂+噪波",
        params={
            "phase": [
                {"type": "rgb_split", "duration_ms": 100},
                {"type": "scan_line", "duration_ms": 80, "line_height": 4},
                {"type": "block_displace", "duration_ms": 120, "block_size": 16},
                {"type": "noise", "duration_ms": 100},
            ],
            "total_duration_ms": 400,
        },
        intensity=VFXIntensity.EXTREME,
    ),
    "light_transition": EffectDef(
        name="light_transition",
        category=VFXCategory.TRANSITION,
        description="光效过渡 — 高亮闪光衔接两个镜头",
        params={
            "light_type": "radial_wipe",  # radial_wipe / linear_flash / center_burst
            "color": "#FFFFFF",
            "duration_ms": 300,
            "bloom": 0.7,
        },
        intensity=VFXIntensity.STRONG,
    ),
    "particle_dissolve": EffectDef(
        name="particle_dissolve",
        category=VFXCategory.TRANSITION,
        description="粒子消散 — 画面碎成粒子飘散",
        params={
            "particle_size": (2, 8),
            "direction": "random",        # random / left / right / up
            "duration_ms": 500,
            "particle_color": "auto",     # auto 从画面采样
            "turbulence": 0.4,
        },
        intensity=VFXIntensity.EXTREME,
    ),
    "zoom_transition": EffectDef(
        name="zoom_transition",
        category=VFXCategory.TRANSITION,
        description="缩放转场 — 推拉镜切换",
        params={
            "direction": "zoom_in",       # zoom_in / zoom_out
            "scale_to": 3.0,
            "motion_blur": 0.5,
            "duration_ms": 250,
        },
        intensity=VFXIntensity.MODERATE,
    ),
    "slide_wipe": EffectDef(
        name="slide_wipe",
        category=VFXCategory.TRANSITION,
        description="滑动擦除 — 新画面滑入覆盖",
        params={
            "direction": "left_to_right",
            "feather": 0.1,
            "duration_ms": 300,
        },
        intensity=VFXIntensity.SUBTLE,
    ),
}

# ---------- 强调特效 ----------
EMPHASIS_EFFECTS = {
    "keyframe_zoom": EffectDef(
        name="keyframe_zoom",
        category=VFXCategory.EMPHASIS,
        description="关键帧放大 — 画面突发放大强调",
        params={
            "scale_from": 1.0,
            "scale_to": 1.3,
            "duration_ms": 400,
            "anchor": "center",          # center / top / bottom / custom(x,y)
            "motion_blur": True,
            "bounce_back": True,         # 放大后回弹
        },
        intensity=VFXIntensity.STRONG,
    ),
    "color_flicker": EffectDef(
        name="color_flicker",
        category=VFXCategory.EMPHASIS,
        description="颜色闪烁 — 画面闪烁特定颜色",
        params={
            "color": "#FFD700",          # 金色
            "flicker_count": 3,
            "interval_ms": 80,
            "blend_mode": "overlay",
            "opacity_peak": 0.5,
        },
        intensity=VFXIntensity.STRONG,
    ),
    "ring_highlight": EffectDef(
        name="ring_highlight",
        category=VFXCategory.EMPHASIS,
        description="环形高亮 — 围绕目标区域的发光环",
        params={
            "radius": 60,
            "ring_width": 4,
            "color": "#FFD700",
            "animate": "expand",         # expand / pulse / rotate
            "duration_ms": 600,
        },
        intensity=VFXIntensity.MODERATE,
    ),
    "text_bounce": EffectDef(
        name="text_bounce",
        category=VFXCategory.EMPHASIS,
        description="文字弹跳 — 弹性动画入场",
        params={
            "from_scale": 0.3,
            "to_scale": 1.0,
            "bounce_count": 3,
            "direction": "up",           # up / down / left / right / center
            "duration_ms": 500,
            "easing": "elastic_out",
        },
        intensity=VFXIntensity.MODERATE,
    ),
    "pulse": EffectDef(
        name="pulse",
        category=VFXCategory.EMPHASIS,
        description="脉冲 — 缩放+透明度循环波动",
        params={
            "scale_range": (1.0, 1.1),
            "opacity_range": (0.8, 1.0),
            "period_ms": 600,
            "cycles": 3,
        },
        intensity=VFXIntensity.SUBTLE,
    ),
}


# 特效全库（扁平化索引）
ALL_EFFECTS = {
    **TEXT_EFFECTS,
    **VISUAL_EFFECTS,
    **TRANSITION_EFFECTS,
    **EMPHASIS_EFFECTS,
}


# ============================================================
# 2. 特效触发器 — 根据脚本内容自动标记特效插入点
# ============================================================

@dataclass
class VFXTrigger:
    """触发规则：匹配关键词/模式 -> 推荐特效组合"""
    pattern: str                 # 正则模式
    pattern_type: str            # regex / keyword / semantic
    effects: list                # 推荐特效名列表
    description: str             # 触发说明
    priority: int = 5            # 优先级 1-10


TRIGGER_RULES = [
    # --- 数字出现 → 放大+金色闪烁 ---
    VFXTrigger(
        pattern=r"\d{1,3}(?:\.\d)?[万亿千百]|\d{1,3}(?:,\d{3})*(?:\.\d+)?[亿万千百]?",
        pattern_type="regex",
        effects=["keyframe_zoom", "color_flicker", "glow"],
        description="关键数据出现时放大+金色闪烁+发光",
        priority=9,
    ),
    VFXTrigger(
        pattern=r"\d+:\d+|\d+比\d+|\d+\s*[—–-]\s*\d+",
        pattern_type="regex",
        effects=["keyframe_zoom", "shadow"],
        description="比分出现时放大强调",
        priority=9,
    ),
    VFXTrigger(
        pattern=r"\d+\s*[秒分时天年月日]",
        pattern_type="regex",
        effects=["keyframe_zoom", "flash_white"],
        description="时间数字强调",
        priority=8,
    ),

    # --- 反转/惊讶 → 画面震动+闪白 ---
    VFXTrigger(
        pattern=r"反转|逆袭|翻盘|绝杀|万万没想到|居然|竟然|惊人|震惊|不可思议",
        pattern_type="regex",
        effects=["shake", "flash_white", "chromatic_aberration"],
        description="剧情反转/意外时刻",
        priority=10,
    ),

    # --- 提问 → 文字弹跳+高亮 ---
    VFXTrigger(
        pattern=r"\?|你知道吗|有没有想过|什么是|为什么|如何|怎么",
        pattern_type="regex",
        effects=["text_bounce", "ring_highlight", "frosted_bg"],
        description="设问/互动提问",
        priority=7,
    ),

    # --- 情绪高点 → 慢动作+背景虚化 ---
    VFXTrigger(
        pattern=r"泪目|激动|热血|燃爆|感动|破防|最[^\s]{1,4}(时刻|瞬间)",
        pattern_type="regex",
        effects=["slow_motion", "bokeh", "vignette"],
        description="情绪高潮时刻（体育/感动类）",
        priority=10,
    ),
    VFXTrigger(
        pattern=r"赢了|输了|冠军|胜利|失败|金牌|夺冠|捧杯|举起",
        pattern_type="regex",
        effects=["slow_motion", "flash_white", "particle_dissolve"],
        description="胜负/夺冠时刻",
        priority=10,
    ),

    # --- 对比/变化 ---
    VFXTrigger(
        pattern=r"从.*到|曾经.*如今|过去.*现在|变成|变成|逆转",
        pattern_type="regex",
        effects=["glitch", "gradient_text"],
        description="前后对比/变化转折",
        priority=7,
    ),

    # --- 强调断言 ---
    VFXTrigger(
        pattern=r"(但[是]?|然而|不过|关键[的是])[^，。；,\.;]*?[！!]",
        pattern_type="regex",
        effects=["keyframe_zoom", "color_flicker"],
        description="关键转折/强调",
        priority=8,
    ),

    # --- 口号/金句 ---
    VFXTrigger(
        pattern=r"[""「『].+[""」』]|——.+——",
        pattern_type="regex",
        effects=["glow", "text_bounce", "gradient_text"],
        description="金句/引用/口号",
        priority=8,
    ),

    # --- 动作/发力 ---
    VFXTrigger(
        pattern=r"射门|投篮|冲刺|挥拍|上篮|得分|扣篮|进球|拳击|击倒",
        pattern_type="regex",
        effects=["speed_lines", "shake", "keyframe_zoom"],
        description="体育动作高潮",
        priority=8,
    ),

    # --- 开场/导入 ---
    VFXTrigger(
        pattern=r"^(大家好|欢迎|今天[我们]?[来看]|这一期)",
        pattern_type="regex",
        effects=["light_transition", "zoom_transition", "glow"],
        description="开场白",
        priority=6,
    ),
]


@dataclass
class VFXMarker:
    """特效插入标记点"""
    time_estimate_sec: float     # 预估时间点（秒）
    trigger_rule: str            # 匹配到的触发规则描述
    matched_text: str            # 匹配到的原文片段
    effects: list                # 推荐特效列表
    keyframe_params: dict        # 关键帧参数建议
    filter_recommendation: str   # 滤镜推荐


def analyze_script_for_triggers(script: str, words_per_sec: float = 3.5) -> list[VFXMarker]:
    """
    分析脚本内容，自动标记特效插入点。

    Args:
        script: 口播脚本全文
        words_per_sec: 语速（字/秒），用于估算时间点

    Returns:
        VFXMarker列表，按时间排序
    """
    markers = []

    for rule in sorted(TRIGGER_RULES, key=lambda r: r.priority, reverse=True):
        for match in re.finditer(rule.pattern, script):
            char_pos = match.start()
            # 粗略估算时间点：字符位置 / 语速
            time_sec = char_pos / words_per_sec

            # 关键帧参数（根据特效类型生成）
            kf_params = _generate_keyframe_params(rule.effects, time_sec)

            # 滤镜推荐
            filter_rec = _recommend_filter(rule.effects, rule.description)

            marker = VFXMarker(
                time_estimate_sec=round(time_sec, 1),
                trigger_rule=rule.description,
                matched_text=match.group().strip(),
                effects=rule.effects,
                keyframe_params=kf_params,
                filter_recommendation=filter_rec,
            )
            markers.append(marker)

    # 去重（相近时间点的合并）
    markers = _deduplicate_markers(markers)

    # 按时间排序
    markers.sort(key=lambda m: m.time_estimate_sec)

    return markers


def _generate_keyframe_params(effect_names: list, time_sec: float) -> dict:
    """根据特效名生成关键帧参数建议"""
    params = {"time_sec": time_sec, "keyframes": []}

    for name in effect_names:
        effect = ALL_EFFECTS.get(name)
        if effect is None:
            continue

        if name == "keyframe_zoom":
            params["keyframes"].append({
                "property": "scale",
                "keyframes": [
                    {"t": time_sec - 0.1, "value": 1.0, "easing": "ease_in"},
                    {"t": time_sec + 0.05, "value": 1.3, "easing": "ease_out"},
                    {"t": time_sec + 0.4, "value": 1.0, "easing": "elastic_out"},
                ]
            })
        elif name == "text_bounce":
            params["keyframes"].append({
                "property": "position_y",
                "keyframes": [
                    {"t": time_sec, "value": -30, "easing": "ease_out"},
                    {"t": time_sec + 0.15, "value": 0, "easing": "bounce_out"},
                    {"t": time_sec + 0.3, "value": -8, "easing": "ease_in_out"},
                    {"t": time_sec + 0.45, "value": 0, "easing": "ease_out"},
                ]
            })
        elif name == "shake":
            params["keyframes"].append({
                "property": "position",
                "keyframes": [
                    {"t": time_sec, "value": 0, "easing": "linear"},
                    {"t": time_sec + 0.3, "value": 8, "easing": "ease_out"},
                    {"t": time_sec + 0.35, "value": 0, "easing": "linear"},
                ],
                "note": "amplitude decays over keyframes via expression"
            })
        elif name == "color_flicker":
            params["keyframes"].append({
                "property": "effect_opacity",
                "keyframes": [
                    {"t": time_sec, "value": 0},
                    {"t": time_sec + 0.08, "value": 0.5},
                    {"t": time_sec + 0.16, "value": 0},
                    {"t": time_sec + 0.24, "value": 0.5},
                    {"t": time_sec + 0.32, "value": 0},
                ]
            })
        elif name == "slow_motion":
            params["keyframes"].append({
                "property": "speed",
                "keyframes": [
                    {"t": time_sec - 0.2, "value": 1.0, "easing": "ease_in"},
                    {"t": time_sec, "value": 0.25, "easing": "linear"},
                    {"t": time_sec + 1.5, "value": 0.25, "easing": "linear"},
                    {"t": time_sec + 1.8, "value": 1.0, "easing": "ease_out"},
                ]
            })

    return params


def _recommend_filter(effect_names: list, description: str) -> str:
    """推荐配套滤镜"""
    flash_effects = {"flash_white", "light_transition"}
    dark_effects = {"vignette", "bokeh", "chromatic_aberration", "glitch"}
    warm_effects = {"glow", "golden_flicker", "color_flicker"}

    effect_set = set(effect_names)
    if effect_set & flash_effects:
        return "LUT: 高光提升 + 轻微过曝"
    elif effect_set & dark_effects:
        return "LUT: 暗部加深 + 冷色调"
    elif effect_set & warm_effects:
        return "LUT: 暖金质感 + 饱和度+10"
    elif "slow_motion" in effect_set:
        return "Filter: 电影感 + 柔焦"
    else:
        return "LUT: 自然通透"


def _deduplicate_markers(markers: list, merge_window_sec: float = 0.8) -> list:
    """合并时间窗口内重复的特效标记"""
    if not markers:
        return markers

    markers.sort(key=lambda m: m.time_estimate_sec)
    merged = []
    current = markers[0]

    for next_m in markers[1:]:
        if next_m.time_estimate_sec - current.time_estimate_sec < merge_window_sec:
            # 合并：取并集特效、保留高优先级
            current.effects = list(set(current.effects + next_m.effects))
            if next_m.trigger_rule not in current.trigger_rule:
                current.trigger_rule += " + " + next_m.trigger_rule
        else:
            merged.append(current)
            current = next_m

    merged.append(current)
    return merged


# ============================================================
# 3. 剪映(CapCut)特效映射
# ============================================================

class CapCutEffectMapper:
    """
    将本模块的特效名映射到剪映 capcut-mcp 可用的 effect_id 和参数。

    剪映 effect 类型说明:
      - effect_effect_id: 内置特效ID (例如 "glitch_01", "shake_02")
      - keyframe transform: 关键帧变换 (scale/position/rotation/opacity)
      - Lut/Filter: 滤镜/调色
    """

    # 特效名 -> capcut effect_id 映射表
    EFFECT_ID_MAP = {
        # 画面特效
        "shake":            "effect_shake_01",
        "flash_white":      "effect_flash_white",
        "slow_motion":      None,  # 变速通过 timeline speed 实现，非effect
        "speed_lines":      "effect_speed_lines_01",
        "chromatic_aberration": "effect_chromatic_aberration",
        "bokeh":            "effect_bokeh",
        "vignette":         "effect_vignette",

        # 转场特效
        "glitch":           "transition_glitch_01",
        "light_transition": "transition_light_01",
        "particle_dissolve":"transition_particle_dissolve",
        "zoom_transition":  "transition_zoom_01",
        "slide_wipe":       "transition_slide",

        # 文字特效
        "glow":             "text_effect_glow",
        "shadow":           "text_effect_shadow",
        "stroke":           "text_effect_stroke",
        "gradient_text":    "text_effect_gradient",
        "frosted_bg":       "text_effect_frosted",

        # 强调
        "keyframe_zoom":    None,  # 通过关键帧实现
        "color_flicker":    "effect_color_flicker",
        "ring_highlight":   "effect_ring_highlight",
        "text_bounce":      None,  # 通过关键帧动画实现
        "pulse":            None,  # 通过关键帧实现
    }

    # 滤镜映射
    FILTER_ID_MAP = {
        "高对比+暖色调":  "filter_warm_contrast",
        "暗角+冷色":      "filter_cool_vignette",
        "明亮+柔和":      "filter_bright_soft",
        "电影感+柔焦":    "filter_cinematic_soft",
        "暖金质感":        "filter_golden_warm",
        "自然通透":         "filter_natural",
        "高光提升":         "filter_highlight_boost",
        "暗部加深":         "filter_shadow_deep",
    }

    @classmethod
    def get_effect_id(cls, effect_name: str) -> Optional[str]:
        """获取剪映内置特效ID"""
        return cls.EFFECT_ID_MAP.get(effect_name)

    @classmethod
    def get_filter_id(cls, filter_desc: str) -> Optional[str]:
        """根据描述获取剪映滤镜ID"""
        for key, fid in cls.FILTER_ID_MAP.items():
            if key in filter_desc:
                return fid
        return cls.FILTER_ID_MAP.get("自然通透")

    @classmethod
    def build_capcut_keyframe(cls, property_name: str, keyframes: list) -> dict:
        """
        构建剪映关键帧JSON格式。

        CapCut keyframe 格式:
        {
            "property": "scale" | "position" | "rotation" | "opacity",
            "keyframes": [
                {"time": 0.0, "value": 1.0, "easing": "linear"},
                ...
            ]
        }
        """
        return {
            "property": property_name,
            "keyframes": [
                {
                    "time": kf["t"],
                    "value": kf["value"],
                    "easing": kf.get("easing", "linear"),
                }
                for kf in keyframes
            ]
        }

    @classmethod
    def marker_to_capcut_actions(cls, marker: VFXMarker) -> dict:
        """
        将VFXMarker转换为capcut-mcp可执行的操作列表。

        Returns:
            {
                "time_sec": float,
                "effects": [{"type": "effect", "effect_id": "xxx", "params": {...}}, ...],
                "keyframes": [...],
                "filter": "filter_xxx",
                "speed_change": {...} or None,
            }
        """
        actions = {
            "time_sec": marker.time_estimate_sec,
            "effects": [],
            "keyframes": [],
            "filter": cls.get_filter_id(marker.filter_recommendation),
            "speed_change": None,
        }

        for effect_name in marker.effects:
            effect_id = cls.get_effect_id(effect_name)
            if effect_id:
                actions["effects"].append({
                    "type": "effect",
                    "effect_id": effect_id,
                    "name": effect_name,
                    "params": ALL_EFFECTS.get(effect_name, EffectDef(name="", category=VFXCategory.VISUAL, description="")).params,
                })
            elif effect_name == "slow_motion":
                actions["speed_change"] = {
                    "type": "speed",
                    "ratio": 0.25,
                    "method": "optical_flow",
                    "ramp": True,
                }
            elif effect_name == "keyframe_zoom":
                actions["keyframes"].append(
                    cls.build_capcut_keyframe("scale", [
                        {"t": marker.time_estimate_sec - 0.1, "value": 1.0, "easing": "ease_in"},
                        {"t": marker.time_estimate_sec + 0.05, "value": 1.3, "easing": "ease_out"},
                        {"t": marker.time_estimate_sec + 0.4, "value": 1.0, "easing": "elastic_out"},
                    ])
                )
            elif effect_name == "text_bounce":
                actions["keyframes"].append(
                    cls.build_capcut_keyframe("position_y", [
                        {"t": marker.time_estimate_sec, "value": -30, "easing": "ease_out"},
                        {"t": marker.time_estimate_sec + 0.15, "value": 0, "easing": "bounce_out"},
                        {"t": marker.time_estimate_sec + 0.3, "value": -8, "easing": "ease_in_out"},
                        {"t": marker.time_estimate_sec + 0.45, "value": 0, "easing": "ease_out"},
                    ])
                )

        return actions


# ============================================================
# 4. 视觉风格方案
# ============================================================

@dataclass
class VisualStyleScheme:
    """完整视觉风格方案"""
    style_name: str                          # 风格名
    description: str                         # 适用场景
    color_palette: dict                      # 配色方案
    typography: dict                         # 字体方案
    default_effects: list                    # 默认特效列表
    transitions: list                        # 转场风格
    filter_lut: str                          # 调色LUT
    overlays: list                           # 叠加层
    pacing: dict                             # 节奏控制
    example_markers: list = field(default_factory=list)  # 示例标记


# ---------- 预置视觉风格 ----------

SPORTS_HOT_BLOOD = VisualStyleScheme(
    style_name="体育热血风",
    description="适合体育赛事、竞技对抗、燃向混剪",
    color_palette={
        "primary": "#FF4D2E",      # 热血红
        "secondary": "#FFD700",    # 金色/高光
        "accent": "#FF8C00",       # 橙
        "bg_dark": "#0D0D0D",      # 深黑底
        "text_light": "#FFFFFF",
        "text_accent": "#FFD700",
        "gradient_hot": ["#FF4D2E", "#FFD700"],
    },
    typography={
        "title_font": "锐字真言体 / 思源黑体 Heavy",
        "subtitle_font": "思源黑体 Bold",
        "body_font": "思源黑体 Regular",
        "number_font": "DIN Pro / 思源黑体 Heavy",  # 数字专用
        "size_title": 48,
        "size_subtitle": 32,
        "size_body": 24,
        "size_number": 72,         # 比分数字大号
    },
    default_effects=[
        "speed_lines",
        "shake",
        "keyframe_zoom",
        "color_flicker",
        "glow",
    ],
    transitions=[
        {"type": "zoom_transition", "usage": "节奏加速时"},
        {"type": "light_transition", "usage": "关键进球/得分"},
        {"type": "glitch", "usage": "快速混剪段落"},
        {"type": "particle_dissolve", "usage": "转场到慢动作回放"},
    ],
    filter_lut="高对比+暖色调",
    overlays=[
        "dust_particles.mp4 (屏幕粒子浮动)",
        "film_grain.png (轻微胶片颗粒)",
        "light_leak.mp4 (光效漏光)",
    ],
    pacing={
        "cut_frequency": "快节奏 (平均2-3秒/镜)",
        "speed_ramp": "加速→正常→慢动作",
        "beat_sync": True,          # 踩点剪辑
        "bpm_range": (120, 150),
    },
)

MYSTERY_THRILLER = VisualStyleScheme(
    style_name="悬疑揭秘风",
    description="适合悬疑、推理、知识揭秘、奇闻类",
    color_palette={
        "primary": "#1A4067",       # 深海蓝
        "secondary": "#00D2FF",     # 冷青
        "accent": "#7B2FBE",        # 紫
        "bg_dark": "#0A0A0F",
        "text_light": "#E0E0E0",
        "text_accent": "#00D2FF",
        "gradient_cold": ["#1A4067", "#00D2FF"],
    },
    typography={
        "title_font": "思源宋体 Heavy / 造字工房力黑",
        "subtitle_font": "思源黑体 Bold",
        "body_font": "思源黑体 Regular",
        "number_font": "思源黑体 Medium",
        "size_title": 44,
        "size_subtitle": 28,
        "size_body": 22,
        "size_number": 56,
    },
    default_effects=[
        "vignette",
        "chromatic_aberration",
        "glitch",
        "frosted_bg",
        "ring_highlight",
    ],
    transitions=[
        {"type": "glitch", "usage": "揭示线索/反转"},
        {"type": "slide_wipe", "usage": "对比画面"},
        {"type": "light_transition", "usage": "发现答案"},
    ],
    filter_lut="暗角+冷色",
    overlays=[
        "scan_lines.png (扫描线)",
        "dust_scratches.mp4 (划痕/噪点)",
        "vignette_dark.png (加深暗角)",
    ],
    pacing={
        "cut_frequency": "中慢节奏 (平均4-6秒/镜)",
        "speed_ramp": "正常→暂停特写→回放",
        "beat_sync": False,         # 氛围型不在踩点
        "bpm_range": (70, 100),
    },
)

EASY_LIFE = VisualStyleScheme(
    style_name="轻松生活风",
    description="适合生活vlog、美食、旅行、日常分享",
    color_palette={
        "primary": "#FF9A76",       # 暖杏
        "secondary": "#FCF6F0",     # 奶白
        "accent": "#6ECB63",        # 清新绿
        "bg_light": "#FFFAF5",
        "text_dark": "#3D3D3D",
        "text_accent": "#FF9A76",
        "gradient_soft": ["#FF9A76", "#FCF6F0"],
    },
    typography={
        "title_font": "站酷快乐体 / 沐瑶软笔手写体",
        "subtitle_font": "思源黑体 Medium",
        "body_font": "思源黑体 Regular",
        "number_font": "思源黑体 Regular",
        "size_title": 40,
        "size_subtitle": 28,
        "size_body": 22,
        "size_number": 48,
    },
    default_effects=[
        "frosted_bg",
        "shadow",
        "slide_wipe",
        "bokeh",
        "pulse",
    ],
    transitions=[
        {"type": "slide_wipe", "usage": "场景切换"},
        {"type": "zoom_transition", "usage": "食物/物件特写"},
        {"type": "light_transition", "usage": "日落到夜景过渡"},
    ],
    filter_lut="明亮+柔和",
    overlays=[
        "border_rounded.png (圆角边框遮罩)",
        "light_dust.mp4 (柔光粒子)",
    ],
    pacing={
        "cut_frequency": "轻松慢节奏 (平均5-8秒/镜)",
        "speed_ramp": "淡入淡出过渡",
        "beat_sync": False,
        "bpm_range": (80, 110),
    },
)

# 风格库
STYLE_LIBRARY: dict[str, VisualStyleScheme] = {
    "sports_hot_blood": SPORTS_HOT_BLOOD,
    "mystery_thriller": MYSTERY_THRILLER,
    "easy_life": EASY_LIFE,
}


def get_style(style_key: str) -> VisualStyleScheme:
    """按key获取视觉风格方案"""
    return STYLE_LIBRARY.get(style_key, SPORTS_HOT_BLOOD)


def detect_style_from_script(script: str) -> str:
    """
    根据脚本关键词自动判定视频风格。

    Returns:
        风格key: "sports_hot_blood" | "mystery_thriller" | "easy_life"
    """
    sports_kw = ["比赛", "决赛", "进球", "得分", "冠军", "战队", "体育",
                  "足球", "篮球", "乒乓", "田径", "游泳", "拳击", "格斗",
                  "击败", "夺冠", "捧杯", "金牌", "速度", "力量"]
    mystery_kw = ["揭秘", "真相", "秘密", "背后", "隐藏", "诡异", "悬疑",
                   "未解之谜", "细思极恐", "冷知识", "奇闻", "因果"]
    life_kw = ["美食", "旅行", "日常", "生活", "家里", "周末", "做饭",
               "探店", "穿搭", "亲子", "宠物", "猫", "狗", "花"]

    scores = {"sports_hot_blood": 0, "mystery_thriller": 0, "easy_life": 0}
    for kw in sports_kw:
        scores["sports_hot_blood"] += len(re.findall(kw, script))
    for kw in mystery_kw:
        scores["mystery_thriller"] += len(re.findall(kw, script))
    for kw in life_kw:
        scores["easy_life"] += len(re.findall(kw, script))

    return max(scores, key=scores.get)


# ============================================================
# 5. 完整特效方案生成器
# ============================================================

@dataclass
class VFXPlan:
    """完整特效方案"""
    style: VisualStyleScheme
    style_key: str
    markers: list[VFXMarker]
    capcut_timeline: list           # 剪映时间线操作
    global_filter: str
    opening: dict                   # 开场特效
    closing: dict                   # 结尾特效
    music_recommendation: dict      # 配乐建议


def generate_vfx_plan(
    script: str,
    style_key: Optional[str] = None,
    words_per_sec: float = 3.5,
    duration_hint_sec: Optional[float] = None,
) -> VFXPlan:
    """
    生成完整特效方案。

    Args:
        script: 口播脚本全文
        style_key: 风格key，None则自动检测
        words_per_sec: 语速（字/秒）
        duration_hint_sec: 预估总时长（秒），None则按字数估算

    Returns:
        VFXPlan 完整方案
    """
    # 风格判定
    if style_key is None:
        style_key = detect_style_from_script(script)
    style = get_style(style_key)

    # 分析触发点
    markers = analyze_script_for_triggers(script, words_per_sec)

    # 估算时长
    if duration_hint_sec:
        total_duration = duration_hint_sec
    else:
        total_duration = len(script) / words_per_sec

    # 转换为 capcut 时间线操作
    mapper = CapCutEffectMapper()
    capcut_timeline = []
    for m in markers:
        capcut_timeline.append(mapper.marker_to_capcut_actions(m))

    # 全局滤镜
    global_filter = CapCutEffectMapper.FILTER_ID_MAP.get(
        style.filter_lut, "filter_natural"
    )

    # 开场特效
    opening = _build_opening(style_key, total_duration)

    # 结尾特效
    closing = _build_closing(style_key, total_duration)

    # 配乐建议
    music_rec = _build_music_recommendation(style_key)

    return VFXPlan(
        style=style,
        style_key=style_key,
        markers=markers,
        capcut_timeline=capcut_timeline,
        global_filter=global_filter,
        opening=opening,
        closing=closing,
        music_recommendation=music_rec,
    )


def _build_opening(style_key: str, total_duration: float) -> dict:
    """构建开场特效"""
    if style_key == "sports_hot_blood":
        return {
            "duration": 2.0,
            "effects": [
                {"type": "speed_lines", "direction": "radial", "duration": 1.5},
                {"type": "text_bounce", "target": "title", "duration": 0.8},
            ],
            "transition": "light_transition",
            "filter_in": "暗到亮渐变",
            "sound": "重低音撞击 + 呼啸风声",
        }
    elif style_key == "mystery_thriller":
        return {
            "duration": 2.5,
            "effects": [
                {"type": "vignette", "intensity": 0.8},
                {"type": "chromatic_aberration", "duration": 1.0},
            ],
            "transition": "glitch",
            "filter_in": "模糊到清晰",
            "sound": "低频嗡鸣 + 惊悚弦乐",
        }
    else:  # easy_life
        return {
            "duration": 1.5,
            "effects": [
                {"type": "bokeh", "duration": 1.0},
                {"type": "frosted_bg", "target": "title"},
            ],
            "transition": "slide_wipe",
            "filter_in": "淡入",
            "sound": "清脆铃音 + 轻快吉他",
        }


def _build_closing(style_key: str, total_duration: float) -> dict:
    """构建结尾特效"""
    if style_key == "sports_hot_blood":
        return {
            "start_time": total_duration - 2.0,
            "effects": [
                {"type": "slow_motion", "speed": 0.5, "duration": 1.5},
                {"type": "flash_white", "at_end": True},
            ],
            "text_effect": "渐变淡出",
            "sound": "鼓点渐弱 + 全场欢呼回声",
        }
    elif style_key == "mystery_thriller":
        return {
            "start_time": total_duration - 2.5,
            "effects": [
                {"type": "vignette", "intensity": 1.0, "darken_to_black": True},
            ],
            "text_effect": "打字机逐字消失",
            "sound": "低频渐强 → 突然停止",
        }
    else:
        return {
            "start_time": total_duration - 1.5,
            "effects": [
                {"type": "bokeh", "blur_increase": True},
            ],
            "text_effect": "柔和淡出",
            "sound": "吉他泛音渐弱",
        }


def _build_music_recommendation(style_key: str) -> dict:
    """构建配乐建议"""
    if style_key == "sports_hot_blood":
        return {
            "genre": "Epic / Rock / EDM",
            "tempo": "120-150 BPM",
            "mood": "激昂、热血、振奋",
            "reference": "Epic Sport Trailer / 王者荣耀BGM风格",
            "structure": "Intro buildup → Drop高潮 → Bridge回落 → Final爆发",
        }
    elif style_key == "mystery_thriller":
        return {
            "genre": "Ambient / Cinematic / Dark Electronic",
            "tempo": "70-100 BPM",
            "mood": "神秘、紧张、悬念",
            "reference": "Hans Zimmer暗黑系 / 悬疑纪实配乐",
            "structure": "氛围铺垫 → 弦乐渐强 → 真相揭示 → 余韵",
        }
    else:
        return {
            "genre": "Acoustic / Lofi / Indie Pop",
            "tempo": "80-110 BPM",
            "mood": "温暖、轻松、愉悦",
            "reference": "日系生活vlog配乐 / Lofi Study Beats",
            "structure": "轻快进 → 副歌阳光 → 尾声暖意",
        }


# ============================================================
# 6. Demo — U17中日决赛 特效方案
# ============================================================

U17_FINAL_SCRIPT = """
中国U17对阵日本U17的亚洲杯决赛，这场比赛注定载入史册！

开场仅仅3分钟，日本队就率先破门，0:1落后。
但所有人都没想到，这反而点燃了中国队的斗志。

第15分钟，中国队在禁区前沿获得任意球机会，10号球员一脚世界波，
皮球划过一道完美的弧线，直接挂入死角！1:1扳平！

这一刻，全场中国球迷沸腾了！这就是足球最纯粹的热血！

下半场比赛更加激烈。第67分钟，中国队获得角球机会，
7号高高跃起，一记狮子甩头！球进了！2:1逆转！

你知道这意味着什么吗？这是中国U17历史上第一次在亚洲杯决赛逆转日本队！

最后10分钟，全队都在咬牙坚守。后防线每一次解围都让球迷紧张到窒息。

伤停补时，中国队门将贡献了一次神级扑救，将日本队必进之球托出横梁！

终场哨响的那一刻，球员们相拥而泣，2:1！我们是冠军！
中国青少年足球，从此站起来了！
"""


def demo_u17_final():
    """U17中日决赛 体育热血风 完整特效方案演示"""
    print("=" * 72)
    print("  U17中国队vs日本队 亚洲杯决赛 — 完整VFX特效方案")
    print("  视觉风格: 体育热血风 (Sports Hot Blood)")
    print("=" * 72)

    # 生成完整方案
    plan = generate_vfx_plan(U17_FINAL_SCRIPT, style_key="sports_hot_blood")

    # --- Part 1: 风格概览 ---
    print(f"\n{'='*60}")
    print("  PART 1 — 视觉风格方案")
    print("=" * 60)
    style = plan.style
    print(f"\n  风格名称: {style.style_name}")
    print(f"  适用场景: {style.description}")
    print(f"\n  调色方案:")
    for k, v in style.color_palette.items():
        print(f"    {k}: {v}")
    print(f"\n  字体方案:")
    for k, v in style.typography.items():
        print(f"    {k}: {v}")
    print(f"\n  全局滤镜: {style.filter_lut}")
    print(f"  剪辑节奏: {style.pacing['cut_frequency']}")
    print(f"  踩点BPM:  {style.pacing['bpm_range'][0]}-{style.pacing['bpm_range'][1]}")

    # --- Part 2: 配乐建议 ---
    print(f"\n  [配乐建议]")
    for k, v in plan.music_recommendation.items():
        print(f"    {k}: {v}")

    # --- Part 3: 特效触发点 ---
    print(f"\n{'='*60}")
    print("  PART 2 — 特效触发点分析")
    print("=" * 60)
    print(f"\n  共检测到 {len(plan.markers)} 个特效触发点:\n")

    for i, m in enumerate(plan.markers, 1):
        print(f"  [{i:02d}] T={m.time_estimate_sec:5.1f}s | {m.trigger_rule}")
        print(f"       匹配: \"{m.matched_text[:40]}\"")
        print(f"       特效: {', '.join(m.effects)}")
        print(f"       滤镜: {m.filter_recommendation}")
        if m.keyframe_params.get("keyframes"):
            for kf in m.keyframe_params["keyframes"]:
                print(f"       关键帧: {kf['property']} @ {[kk['t'] for kk in kf['keyframes']]}")
        print()

    # --- Part 4: 剪映映射 ---
    print(f"  {'='*60}")
    print("  PART 3 — 剪映(CapCut)特效映射")
    print("  =" + "=" * 59)

    for i, action in enumerate(plan.capcut_timeline):
        m = plan.markers[i]
        print(f"\n  --- Marker {i+1:02d} @ {action['time_sec']:.1f}s ---")
        print(f"  全局滤镜: {action['filter']}")

        if action["effects"]:
            for ef in action["effects"]:
                print(f"  + effect: {ef['effect_id']} ({ef['name']})")
        if action["keyframes"]:
            for kf in action["keyframes"]:
                pts = [(kk['time'], kk['value']) for kk in kf['keyframes']]
                print(f"  + keyframe[{kf['property']}]: {pts}")
        if action["speed_change"]:
            sc = action["speed_change"]
            print(f"  + speed_change: ratio={sc['ratio']} method={sc['method']}")

    # --- Part 5: 时间线总览 ---
    print(f"\n{'='*60}")
    print("  PART 4 — 完整时间线总览 (预估总时长: {:.0f}秒)".format(len(U17_FINAL_SCRIPT) / 3.5))
    print("=" * 60)

    # 分段展示
    segments = [
        ("开场 (0-3s)", [
            "叠层: dust_particles.mp4 粒子浮动",
            "叠加: film_grain.png 胶片颗粒",
            "开场特效: speed_lines(放射) + text_bounce(标题弹跳)",
            "转场: light_transition 光效过渡",
            "配乐: 低频鼓点渐入",
        ]),
        ("第一波高潮 — 落后+世界波扳平 (3-12s)", [
            "【0:1落后】keyframe_zoom 比分放大 + color_flicker 金色闪烁",
            "【世界波】speed_lines(水平) + shake 画面震动",
            "【球迷沸腾】flash_white 闪白 + slow_motion 慢动作回放",
            "转场: particle_dissolve 粒子消散 → 慢镜头",
        ]),
        ("第二波高潮 — 逆转 (12-25s)", [
            "【关键数据2:1】keyframe_zoom(scale:1.0→1.3) + glow 金色发光",
            "【你知道吗】text_bounce 文字弹跳 + ring_highlight 环形高亮",
            "【反转/逆转】shake + chromatic_aberration 色散",
            "【神级扑救】slow_motion(0.25x) + zoom_transition 缩放推入",
            "过滤镜: 高对比+暖色调 全段叠加",
        ]),
        ("结尾 — 夺冠时刻 (25-30s)", [
            "【2:1冠军】keyframe_zoom 最大放大 + color_flicker(3次闪烁)",
            "【相拥而泣】slow_motion(0.25x) + flash_white",
            "【从此站起来】text_bounce(弹跳出场) + glow(金色光晕)",
            "关闭: 慢动作(0.5x) → flash_white(纯白) → 标题定格",
            "音效: 全场欢呼 + 鼓点渐弱",
        ]),
    ]

    total_effects = 0
    for seg_name, actions in segments:
        print(f"\n  ■ {seg_name}")
        for a in actions:
            print(f"    {a}")
            total_effects += 1

    # --- Part 6: 特效统计 ---
    print(f"\n{'='*60}")
    print("  PART 5 — 特效使用统计")
    print("=" * 60)

    effect_counts = {}
    for m in plan.markers:
        for ef in m.effects:
            effect_counts[ef] = effect_counts.get(ef, 0) + 1

    for name, count in sorted(effect_counts.items(), key=lambda x: -x[1]):
        bar = "█" * count
        print(f"  {name:25s} {count}次  {bar}")

    print(f"\n  总计特效触发: {sum(effect_counts.values())} 次")
    print(f"  涉及特效种类: {len(effect_counts)} 种")

    # --- Part 7: 导出JSON ---
    print(f"\n{'='*60}")
    print("  PART 6 — capcut-mcp 可导入JSON (摘要)")
    print("=" * 60)

    export_data = {
        "project": "U17_China_vs_Japan_Final",
        "style": plan.style_key,
        "duration_sec": len(U17_FINAL_SCRIPT) / 3.5,
        "global_filter": plan.global_filter,
        "music": plan.music_recommendation,
        "timeline": plan.capcut_timeline,
    }
    print(json.dumps(export_data, ensure_ascii=False, indent=2)[:2000])
    print("  ... (完整JSON见导出变量)")

    return plan


# ============================================================
# 主入口
# ============================================================

if __name__ == "__main__":
    plan = demo_u17_final()
    print("\n" + "=" * 72)
    print("  VFX特效方案生成完毕！")
    print("  皇上，U17决赛热血方案已就绪，随时可导入剪映执行。")
    print("=" * 72)
