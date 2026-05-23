"""
抖音短视频动画引擎 — 字幕动画 · 节奏表 · 转场 · 剪映指令

用法:
  python animator.py                             # U17中日决赛完整演示
  python animator.py --text "你的脚本内容"        # 自定义脚本
  python animator.py --output capcut_anim.json    # 输出剪映动画参数JSON
"""

import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple

# Windows GBK encoding fix
if sys.platform == "win32":
    import io
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass  # not a standard console, use as-is

ROOT = os.path.dirname(os.path.abspath(__file__))

# ============================================================================
#  缓动曲线库 — 标准CSS easing + 剪映对应曲线
# ============================================================================

EASING_LIBRARY = {
    "ease_out":         {"css": "cubic-bezier(0.25, 0.46, 0.45, 0.94)", "jianying": "OutCubic"},
    "ease_in":          {"css": "cubic-bezier(0.42, 0.0, 1.0, 1.0)",    "jianying": "InCubic"},
    "ease_in_out":      {"css": "cubic-bezier(0.42, 0.0, 0.58, 1.0)",  "jianying": "InOutCubic"},
    "bounce_out":       {"css": "cubic-bezier(0.34, 1.56, 0.64, 1.0)", "jianying": "OutBounce"},
    "elastic_out":      {"css": "cubic-bezier(0.68, -0.55, 0.27, 1.55)", "jianying": "OutElastic"},
    "back_out":         {"css": "cubic-bezier(0.34, 1.56, 0.64, 1.0)", "jianying": "OutBack"},
    "linear":           {"css": "linear",                               "jianying": "Linear"},
    "anticipate":       {"css": "cubic-bezier(0.68, -0.2, 0.27, 1.0)", "jianying": "OutBack"},
    "sharp_in":         {"css": "cubic-bezier(0.86, 0.0, 0.07, 1.0)",  "jianying": "InQuint"},
    "smooth_in_out":    {"css": "cubic-bezier(0.65, 0.0, 0.35, 1.0)",  "jianying": "InOutSine"},
}


# ============================================================================
#  1. 字幕动画引擎
# ============================================================================

@dataclass
class AnimationConfig:
    """单条字幕的动画配置"""
    name: str           # 动画名称
    type: str           # intro / outro / loop
    duration_ms: int    # 时长(毫秒)
    easing: str         # 缓动曲线
    staggered: bool     # 是否逐字错帧
    stagger_delay_ms: int = 50  # 逐字间隔
    params: Dict = field(default_factory=dict)


class SubtitleAnimator:
    """字幕动画引擎 — 为抖音口播字幕设计入场/出场/循环动画"""

    # ── 引擎内置动画预设 ──
    PRESETS = {
        # ─── 入场动画 (intro) ───
        "karaoke": AnimationConfig(
            name="卡拉OK逐字弹出",
            type="intro",
            duration_ms=600,
            easing="ease_out",
            staggered=True,
            stagger_delay_ms=60,
            params={
                "capcut_name": "卡拉OK",
                "capcut_resource_id": "6771294855785091588",
                "capcut_effect_id": "6771294855785091588",
                "description": "逐字高亮变色，跟随语速弹出，抖音最火字幕效果",
                "best_for": "口播全段，音乐类，歌唱字幕",
                "color_flow": ["#FF3B30", "#FF9500", "#FFCC00", "#34C759"],
            }
        ),

        "bounce_in": AnimationConfig(
            name="弹跳入场",
            type="intro",
            duration_ms=500,
            easing="bounce_out",
            staggered=False,
            params={
                "capcut_name": "Bounce In",
                "capcut_resource_id": "6887766069587481090",
                "capcut_effect_id": "6887766069587481090",
                "description": "文字从下方弹跳入场，弹性回弹，有冲击力",
                "best_for": "Hook句首句，强调词，数据冲击",
            }
        ),

        "slide_reveal": AnimationConfig(
            name="滑动揭示",
            type="intro",
            duration_ms=500,
            easing="ease_in_out",
            staggered=True,
            stagger_delay_ms=40,
            params={
                "capcut_name": "Slide Right",
                "capcut_resource_id": "6724920136056181256",
                "capcut_effect_id": "6724920136056181256",
                "description": "从左到右逐字滑入揭示，适合信息递进",
                "best_for": "Keep段叙述，故事展开，层层递进",
            }
        ),

        "typewriter": AnimationConfig(
            name="打字机效果",
            type="intro",
            duration_ms=700,
            easing="linear",
            staggered=True,
            stagger_delay_ms=45,
            params={
                "capcut_name": "Typewriter",
                "capcut_resource_id": "7210980292243231233",
                "capcut_effect_id": "7210980292243231233",
                "description": "光标式逐字打印，复古机械感，信息密度高的段落",
                "best_for": "揭秘内容，数据播报，严肃叙述",
            }
        ),

        "scale_pulse": AnimationConfig(
            name="缩放脉冲",
            type="loop",
            duration_ms=400,
            easing="elastic_out",
            staggered=False,
            params={
                "capcut_name": "Pulse",
                "capcut_resource_id": "6724919955654971918",
                "capcut_effect_id": "6724919955654971918",
                "description": "文字周期性放大缩小，强调关键词语，抓住眼球",
                "best_for": "CTA关键词，金额/数字，品牌名，行动指令",
                "pulse_count": 3,
                "scale_range": "100% → 120% → 100%",
            }
        ),

        "pop_up": AnimationConfig(
            name="弹出强调",
            type="intro",
            duration_ms=400,
            easing="back_out",
            staggered=False,
            params={
                "capcut_name": "Pop Up",
                "capcut_resource_id": "7145435451946439170",
                "capcut_effect_id": "7145435451946439170",
                "description": "快速弹出放大，适合情绪爆发点",
                "best_for": "高潮句，绝杀时刻，逆转宣布",
            }
        ),

        "glitch_in": AnimationConfig(
            name="故障风入场",
            type="intro",
            duration_ms=500,
            easing="sharp_in",
            staggered=False,
            params={
                "capcut_name": "Glitch",
                "capcut_resource_id": "7077812383946641921",
                "capcut_effect_id": "7077812383946641921",
                "description": "RGB分离故障风，赛博朋克感，年轻化",
                "best_for": "电竞/科技内容，年轻向开场",
            }
        ),

        "fade_in": AnimationConfig(
            name="渐显淡入",
            type="intro",
            duration_ms=400,
            easing="ease_in_out",
            staggered=False,
            params={
                "capcut_name": "Fade In",
                "capcut_resource_id": "6724916044072227332",
                "capcut_effect_id": "6724916044072227332",
                "description": "最基础的透明度渐变，干净不抢戏",
                "best_for": "叙述段，情感段，转场过渡",
            }
        ),

        # ─── 出场动画 (outro) ───
        "fade_out": AnimationConfig(
            name="渐隐淡出",
            type="outro",
            duration_ms=300,
            easing="ease_in",
            staggered=False,
            params={
                "capcut_name": "Fade Out",
                "capcut_resource_id": "6724919382104871427",
                "capcut_effect_id": "6724919382104871427",
                "description": "字幕淡出消失",
                "best_for": "所有段落的标准退场",
            }
        ),

        "bounce_out": AnimationConfig(
            name="弹跳退场",
            type="outro",
            duration_ms=500,
            easing="ease_in",
            staggered=False,
            params={
                "capcut_name": "Bounce Out",
                "capcut_resource_id": "6887765964515971585",
                "capcut_effect_id": "6887765964515971585",
                "description": "文字弹跳出画，活力收尾",
                "best_for": "CTA段，互动引导，欢快结尾",
            }
        ),

        "throw_back": AnimationConfig(
            name="甩出退场",
            type="outro",
            duration_ms=500,
            easing="sharp_in",
            staggered=False,
            params={
                "capcut_name": "Throw Back",
                "capcut_resource_id": "7233110388701663745",
                "capcut_effect_id": "7233110388701663745",
                "description": "文字快速甩出画面，有力量感",
                "best_for": "体育/动作类，高潮段收尾",
            }
        ),

        "slide_out": AnimationConfig(
            name="滑出退场",
            type="outro",
            duration_ms=400,
            easing="ease_in",
            staggered=False,
            params={
                "capcut_name": "Slide Down",
                "capcut_resource_id": "7403256664498901520",
                "capcut_effect_id": "7403256664498901520",
                "description": "文字向下滑出，干净利落",
                "best_for": "信息段，无缝衔接下一句",
            }
        ),

        # ─── 循环强调动画 (loop) ───
        "shake_emphasis": AnimationConfig(
            name="震动强调",
            type="loop",
            duration_ms=300,
            easing="linear",
            staggered=False,
            params={
                "capcut_name": "Shake",
                "capcut_resource_id": "7161320851327947265",
                "capcut_effect_id": "7161320851327947265",
                "description": "快速抖动，最大限度吸引注意",
                "best_for": "顶级Hook，数据爆炸，冲突爆发",
            }
        ),

        "wave_flow": AnimationConfig(
            name="波浪流动",
            type="loop",
            duration_ms=600,
            easing="smooth_in_out",
            staggered=False,
            params={
                "capcut_name": "Wave",
                "capcut_resource_id": "6724927688047333891",
                "capcut_effect_id": "6724927688047333891",
                "description": "文字波浪形起伏，流畅有韵律",
                "best_for": "Keep段持续字幕，故事叙述",
            }
        ),
    }

    def get(self, preset_name: str) -> AnimationConfig:
        """获取预设动画配置"""
        if preset_name not in self.PRESETS:
            available = ", ".join(self.PRESETS.keys())
            raise KeyError(f"未知动画 '{preset_name}'。可用: {available}")
        return self.PRESETS[preset_name]

    def generate_staggered_timeline(
        self,
        text: str,
        intro_name: str,
        outro_name: str = "fade_out",
        char_duration_ms: int = 80,
    ) -> List[Dict]:
        """
        生成逐字动画时间线

        返回每个字的 [start_ms, end_ms, char, animation_in, animation_out]
        用于驱动剪映的分段字幕动画
        """
        intro = self.get(intro_name)
        outro = self.get(outro_name)
        chars = list(text)
        timeline = []

        for i, ch in enumerate(chars):
            delay = i * intro.stagger_delay_ms
            entry = {
                "char": ch,
                "index": i,
                "start_ms": delay,
                "anim_in": {
                    "name": intro.params["capcut_name"],
                    "resource_id": intro.params["capcut_resource_id"],
                    "effect_id": intro.params["capcut_effect_id"],
                    "duration_ms": intro.duration_ms,
                    "easing": EASING_LIBRARY[intro.easing]["jianying"],
                },
                "anim_out": {
                    "name": outro.params["capcut_name"],
                    "resource_id": outro.params["capcut_resource_id"],
                    "effect_id": outro.params["capcut_effect_id"],
                    "duration_ms": outro.duration_ms,
                    "easing": EASING_LIBRARY[outro.easing]["jianying"],
                },
            }
            timeline.append(entry)

        return timeline

    def generate_keyword_animation(
        self,
        text: str,
        keywords: List[str],
        emphasis_anim: str = "scale_pulse",
    ) -> Dict[str, AnimationConfig]:
        """识别关键词并分配强调动画"""
        anim = self.get(emphasis_anim)
        highlighted = {}
        for kw in keywords:
            if kw in text:
                highlighted[kw] = anim
        return highlighted


# ============================================================================
#  2. 动画节奏表 — 脚本分段 + 动画匹配
# ============================================================================

@dataclass
class Segment:
    """脚本段落"""
    text: str
    type: str          # hook / keep / cta / climax
    index: int         # 段落序号
    estimated_duration_ms: int = 2000  # 预估显示时长


@dataclass
class SegmentAnimation:
    """段落动画方案"""
    segment: Segment
    intro_anim: str           # 入场动画预设名
    outro_anim: str           # 出场动画预设名
    loop_anim: Optional[str]  # 循环动画(可选)
    transition: str           # 段前转场
    emphasis_words: List[str] # 需要强调的关键词
    rationale: str            # 选型理由


class RhythmTable:
    """动画节奏表 — 根据脚本类型/情绪自动匹配动画风格"""

    # ── 段落类型 → 动画策略 ──
    TYPE_STRATEGY = {
        "hook": {
            "goal": "0.3秒抓住注意力，最大化视觉冲击",
            "intro": "bounce_in",
            "outro": "throw_back",
            "loop": "shake_emphasis",
            "transition": "hard_cut",
            "speed": "快",
            "font_style": "粗体/大号/高对比色",
            "description": "快节奏大幅动画，制造好奇心缺口",
        },
        "keep": {
            "goal": "流畅的信息传递，观众舒适阅读",
            "intro": "slide_reveal",
            "outro": "slide_out",
            "loop": "wave_flow",
            "transition": "dissolve",
            "speed": "中",
            "font_style": "常规/易读/次要色",
            "description": "舒适阅读节奏，维持观看留存",
        },
        "cta": {
            "goal": "引导互动，让观众产生操作冲动",
            "intro": "pop_up",
            "outro": "bounce_out",
            "loop": "scale_pulse",
            "transition": "push",
            "speed": "快→慢",
            "font_style": "彩色/动感/引导手势",
            "description": "强调互动指令，推动点赞评论关注",
        },
        "climax": {
            "goal": "情绪爆发点，让观众感受到冲击",
            "intro": "pop_up",
            "outro": "fade_out",
            "loop": "scale_pulse",
            "transition": "push",
            "speed": "极快",
            "font_style": "超粗/金色/震动",
            "description": "高潮瞬间，全屏冲击，最大化情绪渲染",
        },
        "data": {
            "goal": "让数字入脑，强化可信度",
            "intro": "typewriter",
            "outro": "fade_out",
            "loop": "scale_pulse",
            "transition": "push",
            "speed": "慢",
            "font_style": "数字放大/跳变/对比色",
            "description": "数据冲击，增强说服力与记忆度",
        },
    }

    def __init__(self):
        self.animator = SubtitleAnimator()

    def segment_script(self, script_lines: List[str]) -> List[Segment]:
        """自动分段脚本"""
        segments = []
        hook_indicators = ["?", "？", "!", "！", "你猜", "震惊", "天啊", "原来",
                           "99%", "千万", "注意", "别划走", "你敢信"]
        cta_indicators = ["点赞", "关注", "评论", "转发", "收藏", "点个赞",
                          "你怎么看", "你觉得", "告诉我", "说说"]

        for i, line in enumerate(script_lines):
            line = line.strip()
            if not line:
                continue

            # 自动判定类型
            if i == 0 and any(ind in line for ind in hook_indicators):
                seg_type = "hook"
            elif any(ind in line for ind in cta_indicators):
                seg_type = "cta"
            elif "逆转" in line or "绝杀" in line or "夺冠" in line or \
                 "冠军" in line or "沸腾" in line or "惊天" in line:
                seg_type = "climax"
            elif re.search(r'[0-9]+[:：][0-9]+|[0-9]+个|[0-9]+次|[0-9]+年', line):
                seg_type = "data"
            else:
                seg_type = "keep"

            # 预估时长：中文朗读约4字/秒
            char_count = len(line)
            est_duration = max(int(char_count / 4 * 1000), 1500)

            segments.append(Segment(
                text=line,
                type=seg_type,
                index=i,
                estimated_duration_ms=est_duration,
            ))

        return segments

    def assign_animations(self, segments: List[Segment]) -> List[SegmentAnimation]:
        """为每个段落分配动画方案"""
        plans = []

        for seg in segments:
            strategy = self.TYPE_STRATEGY.get(seg.type, self.TYPE_STRATEGY["keep"])
            emphasis = self._extract_emphasis_words(seg.text, seg.type)

            plan = SegmentAnimation(
                segment=seg,
                intro_anim=strategy["intro"],
                outro_anim=strategy["outro"],
                loop_anim=strategy.get("loop"),
                transition=strategy["transition"],
                emphasis_words=emphasis,
                rationale=f"[{seg.type.upper()}] {strategy['description']} — {strategy['goal']}",
            )
            plans.append(plan)

        return plans

    def _extract_emphasis_words(self, text: str, seg_type: str) -> List[str]:
        """提取需要强调的关键词"""
        emphasis = []

        # 数字
        numbers = re.findall(r'[0-9]+(?:\.[0-9]+)?[：:][0-9]+|[0-9]+个|[0-9]+%|[0-9]+万|[0-9]+岁|[0-9]+年|第[0-9]+', text)
        emphasis.extend(numbers)

        # 感叹/情绪词
        emotion_words = ["绝杀", "逆转", "冠军", "沸腾", "惊天", "逆袭", "震撼",
                         "历史", "第一次", "征服", "血性", "奇迹", "从未"]
        for w in emotion_words:
            if w in text and w not in emphasis:
                emphasis.append(w)

        # CTA动词
        cta_words = ["点赞", "点个赞", "点个关注", "评论", "转发", "收藏"]
        if seg_type == "cta":
            for w in cta_words:
                if w in text and w not in emphasis:
                    emphasis.append(w)

        # 队名/人名
        entities = re.findall(r'[中国队|日本队|中国|日本|U17|亚洲杯]+', text)
        for e in entities:
            if len(e) >= 2 and e not in emphasis:
                emphasis.append(e)

        return emphasis[:5]  # 最多5个关键词

    def print_rhythm_table(self, plans: List[SegmentAnimation]):
        """打印动画节奏表"""
        print()
        print("=" * 90)
        print("  动画节奏表 · Animation Rhythm Table")
        print("=" * 90)

        total_ms = 0
        for i, plan in enumerate(plans):
            seg = plan.segment
            total_ms += seg.estimated_duration_ms
            total_s = total_ms / 1000
            bar = "█" * min(int(seg.estimated_duration_ms / 200), 10)

            print(f"""
  [{plan.segment.type.upper():6s}] {bar} {seg.estimated_duration_ms/1000:.1f}s  (累计 {total_s:.1f}s)
  ┌ 文本: {seg.text[:60]}{'...' if len(seg.text) > 60 else ''}
  ├ 入场: {plan.intro_anim:16s} | 出场: {plan.outro_anim:16s}
  ├ 循环: {(plan.loop_anim or '—'):16s} | 转场: {plan.transition}
  ├ 强调: {', '.join(plan.emphasis_words) if plan.emphasis_words else '—'}
  └ 理由: {plan.rationale}""")

        print()
        print(f"  总时长预估: {total_ms/1000:.1f}s ({total_ms//1000//60}:{total_ms//1000%60:02d})")
        print("=" * 90)
        print()


# ============================================================================
#  3. 转场设计
# ============================================================================

@dataclass
class Transition:
    """转场定义"""
    name: str
    style: str                # hard_cut / dissolve / push / rotate
    capcut_name: str
    capcut_resource_id: str
    capcut_effect_id: str
    duration_ms: int
    description: str
    best_for: List[str]


class TransitionLibrary:
    """转场库 — 场景切换动画"""

    TRANSITIONS = {
        "hard_cut": Transition(
            name="硬切",
            style="hard_cut",
            capcut_name="Hard Cut (直接切)",
            capcut_resource_id="",
            capcut_effect_id="",
            duration_ms=0,
            description="无过渡直接切换，节奏最快，力量感强",
            best_for=["体育赛事", "快节奏口播", "战斗/冲突场景", "Hook→Keep"],
        ),

        "dissolve": Transition(
            name="溶解过渡",
            style="dissolve",
            capcut_name="Dissolve",
            capcut_resource_id="6724846004274729480",
            capcut_effect_id="392FD26E-A514-4d0f-8950-EA4A20CB407C",
            duration_ms=467,
            description="画面柔和交叉淡入淡出，情绪连贯",
            best_for=["情感故事", "叙事段落", "Keep→Keep", "回忆画面"],
        ),

        "push_pull": Transition(
            name="推拉过渡",
            style="push",
            capcut_name="Pull in + Pull Out",
            capcut_resource_id="6724226861666144779",
            capcut_effect_id="E27206B3-FFA0-4ea4-B6E7-44350CED4574",
            duration_ms=467,
            description="镜头推进/拉远，空间感变化，适合揭秘",
            best_for=["数据揭示", "真相揭露", "层层递进", "Keep→Climax"],
        ),

        "push_out": Transition(
            name="推出过渡",
            style="push",
            capcut_name="Pull Out",
            capcut_resource_id="6724226338418332167",
            capcut_effect_id="39411271-04D8-40f1-9DF9-1E0A7DA5CF64",
            duration_ms=467,
            description="画面推出，拉开距离感",
            best_for=["总结段落", "Hook→Keep", "反转揭露"],
        ),

        "rotate_cw": Transition(
            name="顺时针旋转",
            style="rotate",
            capcut_name="Rotate CW II",
            capcut_resource_id="7252989706198061569",
            capcut_effect_id="7FDC0CB7-1EF6-4625-95E0-115626185F87",
            duration_ms=800,
            description="顺时针翻转画面，活力动感",
            best_for=["年轻向内容", "活力场景", "胜利/庆祝", "CTA段"],
        ),

        "rotate_ccw": Transition(
            name="逆时针旋转",
            style="rotate",
            capcut_name="Rotate CCW II",
            capcut_resource_id="7252989957319430658",
            capcut_effect_id="B64D4180-9B0E-4b25-8602-4397D00557D6",
            duration_ms=800,
            description="逆时针翻转，倒叙感/回顾感",
            best_for=["倒叙", "回顾", "失误/反转"],
        ),

        "flash": Transition(
            name="闪光爆炸",
            style="dissolve",
            capcut_name="Flash",
            capcut_resource_id="6987208055511323137",
            capcut_effect_id="15F94905-7A39-4789-8285-92188260756B",
            duration_ms=467,
            description="快速白光闪过，冲击力强",
            best_for=["高潮瞬间", "进球后", "比分揭晓", "Climax→Keep"],
        ),

        "white_flash": Transition(
            name="白闪过渡",
            style="dissolve",
            capcut_name="White Flash",
            capcut_resource_id="6724845376098013708",
            capcut_effect_id="B5F63066-4B98-4c8a-B4AD-1398E1D313F2",
            duration_ms=467,
            description="干净白色闪烁过渡",
            best_for=["干净利落的段落切换", "广告感"],
        ),

        "shake": Transition(
            name="震动切场",
            style="hard_cut",
            capcut_name="Shake 3",
            capcut_resource_id="7252670515926536705",
            capcut_effect_id="33EED074-6860-488a-9C94-D5B8F07C1CA6",
            duration_ms=800,
            description="画面震动后切场，模拟地震/爆炸感",
            best_for=["绝杀/逆转", "惊天大新闻", "情绪爆发点"],
        ),

        "glitch": Transition(
            name="故障转场",
            style="hard_cut",
            capcut_name="RGB Glitch",
            capcut_resource_id="7480389949041200390",
            capcut_effect_id="7C44F868-52C9-4b15-9F96-E7316A9A3DE9",
            duration_ms=1000,
            description="RGB分离故障效果，科技/电竞感",
            best_for=["电竞", "科技", "年轻人内容"],
        ),
    }

    def get(self, name: str) -> Transition:
        if name not in self.TRANSITIONS:
            available = ", ".join(self.TRANSITIONS.keys())
            raise KeyError(f"未知转场 '{name}'。可用: {available}")
        return self.TRANSITIONS[name]

    def recommend(self, seg_type: str, next_seg_type: Optional[str] = None) -> Transition:
        """根据段落类型和下一段类型推荐转场"""
        pair = (seg_type, next_seg_type or "")

        recommendations = {
            ("hook", "keep"):        self.TRANSITIONS["dissolve"],
            ("keep", "keep"):        self.TRANSITIONS["dissolve"],
            ("keep", "climax"):      self.TRANSITIONS["push_pull"],
            ("climax", "keep"):      self.TRANSITIONS["flash"],
            ("climax", "cta"):       self.TRANSITIONS["rotate_cw"],
            ("data", "keep"):        self.TRANSITIONS["push_out"],
            ("data", "climax"):      self.TRANSITIONS["flash"],
            ("keep", "cta"):         self.TRANSITIONS["rotate_cw"],
            ("cta", "cta"):          self.TRANSITIONS["dissolve"],
            ("hook", "data"):        self.TRANSITIONS["push_out"],
            ("hook", "climax"):      self.TRANSITIONS["shake"],
        }

        return recommendations.get(pair, self.TRANSITIONS["dissolve"])

    def all_styles(self) -> Dict[str, List[Transition]]:
        """按风格分组返回所有转场"""
        groups = {}
        for t in self.TRANSITIONS.values():
            groups.setdefault(t.style, []).append(t)
        return groups


# ============================================================================
#  4. 剪映动画指令生成器
# ============================================================================

class CapcutAnimationBuilder:
    """生成 capcut-mcp 兼容的动画参数 JSON"""

    def __init__(self):
        self.rhythm = RhythmTable()
        self.transitions_lib = TransitionLibrary()

    def build_full_plan(
        self,
        script_lines: List[str],
        bgm_style: str = "sports_epic",
    ) -> Dict:
        """
        构建完整动画方案

        返回包含所有动画参数的大字典，可直接导入剪映
        """
        # 1. 分段
        segments = self.rhythm.segment_script(script_lines)

        # 2. 分配动画
        anim_plans = self.rhythm.assign_animations(segments)

        # 3. 构建时间轴
        timeline = []
        cursor_ms = 0

        for i, plan in enumerate(anim_plans):
            seg = plan.segment
            next_type = anim_plans[i + 1].segment.type if i + 1 < len(anim_plans) else None
            transition = self.transitions_lib.recommend(seg.type, next_type)

            # 字幕轨道
            subtitle_track = {
                "segment_index": i,
                "segment_type": seg.type,
                "text": seg.text,
                "start_ms": cursor_ms,
                "duration_ms": seg.estimated_duration_ms,
                "intro_animation": {
                    "type": plan.intro_anim,
                    "capcut_name": SubtitleAnimator.PRESETS[plan.intro_anim].params["capcut_name"],
                    "resource_id": SubtitleAnimator.PRESETS[plan.intro_anim].params["capcut_resource_id"],
                    "effect_id": SubtitleAnimator.PRESETS[plan.intro_anim].params["capcut_effect_id"],
                    "duration_ms": SubtitleAnimator.PRESETS[plan.intro_anim].duration_ms,
                    "easing": EASING_LIBRARY[SubtitleAnimator.PRESETS[plan.intro_anim].easing]["jianying"],
                },
                "outro_animation": {
                    "type": plan.outro_anim,
                    "capcut_name": SubtitleAnimator.PRESETS[plan.outro_anim].params["capcut_name"],
                    "resource_id": SubtitleAnimator.PRESETS[plan.outro_anim].params["capcut_resource_id"],
                    "effect_id": SubtitleAnimator.PRESETS[plan.outro_anim].params["capcut_effect_id"],
                    "duration_ms": SubtitleAnimator.PRESETS[plan.outro_anim].duration_ms,
                    "easing": EASING_LIBRARY[SubtitleAnimator.PRESETS[plan.outro_anim].easing]["jianying"],
                },
                "emphasis_words": [
                    {
                        "word": w,
                        "animation": plan.loop_anim or "scale_pulse",
                        "capcut_name": SubtitleAnimator.PRESETS[plan.loop_anim or "scale_pulse"].params["capcut_name"],
                    }
                    for w in plan.emphasis_words
                ],
                "font_style": self.TYPE_STRATEGY[seg.type]["font_style"],
            }

            # 转场轨道 (段间)
            transition_track = {
                "before_segment": i,
                "at_ms": cursor_ms,
                "transition": {
                    "style": transition.style,
                    "name": transition.capcut_name,
                    "resource_id": transition.capcut_resource_id,
                    "effect_id": transition.capcut_effect_id,
                    "duration_ms": transition.duration_ms,
                    "description": transition.description,
                },
            }

            timeline.append({
                "subtitle": subtitle_track,
                "transition": transition_track if transition.duration_ms > 0 else "硬切 (0ms)",
            })

            cursor_ms += seg.estimated_duration_ms

        # 4. 全局节奏分析
        total_duration_ms = sum(s.estimated_duration_ms for s in segments)
        type_distribution = {}
        for s in segments:
            type_distribution[s.type] = type_distribution.get(s.type, 0) + 1

        # BGM节奏点匹配
        bpm_map = {
            "sports_epic": 120,   # 体育史诗
            "fast_beats": 140,    # 快节奏
            "story_telling": 80,  # 故事叙述
            "emotional": 70,      # 情感
        }

        return {
            "meta": {
                "version": "1.0",
                "generator": "animator.py — 抖音短视频动画引擎",
                "total_segments": len(segments),
                "total_duration_ms": total_duration_ms,
                "total_duration_human": f"{total_duration_ms//1000}s ({total_duration_ms//1000//60}:{total_duration_ms//1000%60:02d})",
                "type_distribution": type_distribution,
                "bgm_recommendation": {
                    "style": bgm_style,
                    "bpm": bpm_map.get(bgm_style, 100),
                    "beat_interval_ms": int(60000 / bpm_map.get(bgm_style, 100)),
                },
            },
            "segments": timeline,
            "rhythm_summary": self._generate_rhythm_summary(anim_plans),
        }

    def _generate_rhythm_summary(self, plans: List[SegmentAnimation]) -> Dict:
        """生成节奏摘要"""
        entries = []
        for plan in plans:
            entries.append({
                "type": plan.segment.type,
                "text_preview": plan.segment.text[:50],
                "intro": plan.intro_anim,
                "outro": plan.outro_anim,
                "transition": plan.transition,
                "emphasis": plan.emphasis_words,
            })
        return {
            "structure": "Hook → Keep → Climax → Keep → CTA (抖音黄金结构)",
            "pattern": "快入 → 流畅递进 → 情绪爆发 → 收束引导互动",
            "entries": entries,
        }

    def export_json(self, plan: Dict, output_path: str):
        """导出JSON供capcut-mcp使用"""
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(plan, f, ensure_ascii=False, indent=2)
        print(f"  动画方案已导出 → {output_path}")
        return output_path

    # 暴露 TYPE_STRATEGY 方便外部引用
    TYPE_STRATEGY = RhythmTable.TYPE_STRATEGY


# ============================================================================
#  U17 中日决赛 演示方案
# ============================================================================

U17_SCRIPT = [
    "中国U17在亚洲杯决赛中对阵日本队！",
    "上半场0:2落后，所有人都觉得没希望了。",
    "但下半场中国队像换了一支队伍，",
    "连进三球，完成惊天逆转！",
    "第89分钟绝杀进球，全场沸腾！",
    "中国队3:2战胜日本，夺得U17亚洲杯冠军！",
    "这是中国足球历史上第一次在这个年龄段夺得亚洲冠军！",
    "小将们在场上拼到抽筋，用血性和技术征服了所有人！",
    "",
    "如果你也被这群少年感动了，点个赞",
    "评论区说出你最想对国足小将说的话",
]


def demo():
    """U17中日决赛完整动画方案演示"""
    print("""
  ╔══════════════════════════════════════════════════════════════╗
  ║                                                              ║
  ║    [Anim] 动画引擎 · U17亚洲杯决赛 完整动画方案                   ║
  ║    [ 中国 3:2 日本 ]  惊天逆转夺冠                               ║
  ║                                                              ║
  ╚══════════════════════════════════════════════════════════════╝
  """)

    builder = CapcutAnimationBuilder()
    rhythm = RhythmTable()

    # ── 分段 ──
    segments = rhythm.segment_script(U17_SCRIPT)
    plans = rhythm.assign_animations(segments)

    # ── 打印节奏表 ──
    rhythm.print_rhythm_table(plans)

    # ── 转场方案 ──
    trans_lib = TransitionLibrary()
    print()
    print("=" * 90)
    print("  转场方案 · Transition Design")
    print("=" * 90)

    for i, plan in enumerate(plans):
        next_type = plans[i + 1].segment.type if i + 1 < len(plans) else None
        t = trans_lib.recommend(plan.segment.type, next_type)
        arrow = " → " + next_type if next_type else " (结尾)"
        print(f"  [{plan.segment.type:6s} {arrow:16s}] {t.name:12s} | "
              f"{t.style:12s} | {t.duration_ms}ms | {t.description}")

    # ── 转场风格一览 ──
    print()
    print("─" * 90)
    print("  转场风格适用场景对照")
    print("─" * 90)
    for style_name, trans_list in trans_lib.all_styles().items():
        names = ", ".join(t.name for t in trans_list)
        print(f"  {style_name:12s} : {names}")

    # ── 动画类型速查 ──
    print()
    print("=" * 90)
    print("  字幕动画速查 · Subtitle Animation Quick Reference")
    print("=" * 90)
    animator = SubtitleAnimator()
    for name, cfg in animator.PRESETS.items():
        print(f"  {cfg.type:6s} | {name:16s} | {cfg.duration_ms:4d}ms | "
              f"{cfg.easing:14s} | 逐字:{cfg.staggered} | {cfg.params.get('best_for', '')}")

    # ── 构建完整JSON方案 ──
    print()
    print("=" * 90)
    print("  生成中: capcut-mcp 动画参数 JSON...")
    print("=" * 90)

    plan_json = builder.build_full_plan(U17_SCRIPT)

    # ── 逐段展示动画指令 ──
    for i, seg_data in enumerate(plan_json["segments"]):
        sub = seg_data["subtitle"]
        print(f"""
  ┌── 第{i+1}段 [{sub['segment_type'].upper()}] {sub['text'][:45]}...
  │
  │  入场动画:
  │    · 类型:      {sub['intro_animation']['type']}
  │    · 剪映名称:  {sub['intro_animation']['capcut_name']}
  │    · resource_id: {sub['intro_animation']['resource_id']}
  │    · 时长:      {sub['intro_animation']['duration_ms']}ms
  │    · 缓动:      {sub['intro_animation']['easing']}
  │
  │  出场动画:
  │    · 类型:      {sub['outro_animation']['type']}
  │    · 剪映名称:  {sub['outro_animation']['capcut_name']}
  │    · resource_id: {sub['outro_animation']['resource_id']}
  │    · 时长:      {sub['outro_animation']['duration_ms']}ms
  │    · 缓动:      {sub['outro_animation']['easing']}
  │
  │  强调词: {', '.join(f"{e['word']}({e['animation']})" for e in sub['emphasis_words']) if sub['emphasis_words'] else '—'}
  │""")

    # ── 全局参数 ──
    meta = plan_json["meta"]
    print(f"""
  ╔══════════════════════════════════════════════════════════════╗
  ║  全局参数                                                    ║
  ╠══════════════════════════════════════════════════════════════╣
  ║  总段数: {meta['total_segments']:<49d}║
  ║  总时长: {meta['total_duration_human']:<49s}║
  ║  BGM建议: {meta['bgm_recommendation']['style'] + ' (' + str(meta['bgm_recommendation']['bpm']) + 'BPM)':<46s}║
  ║  节拍间隔: {meta['bgm_recommendation']['beat_interval_ms']}ms{'':<40s}║
  ║                                                              ║
  ║  段落分布:                                                    ║""")
    for typ, cnt in meta["type_distribution"].items():
        print(f"  ║    {typ}: {cnt}段{'':<44s}║")
    print("""  ║                                                              ║
  ╚══════════════════════════════════════════════════════════════╝
  """)

    # ── 逐字卡拉OK 演示 ──
    print()
    print("=" * 90)
    print("  逐字卡拉OK时间线演示 (Hook句)")
    print("=" * 90)
    hook_text = U17_SCRIPT[0]
    timeline = animator.generate_staggered_timeline(
        hook_text, intro_name="karaoke", outro_name="fade_out"
    )
    for char_data in timeline[:12]:  # 只展示前12个字
        print(f"  [{char_data['start_ms']:4d}ms] "
              f"'{char_data['char']}' "
              f"→ {char_data['anim_in']['name']} "
              f"({char_data['anim_in']['duration_ms']}ms, {char_data['anim_in']['easing']})")
    print(f"  ... (共 {len(timeline)} 个字)")

    return plan_json


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="抖音短视频动画引擎 — 字幕动画 · 节奏表 · 转场 · 剪映指令")
    parser.add_argument("--text", type=str, help="脚本内容 (一行一句)")
    parser.add_argument("--output", type=str, default="capcut_anim.json",
                        help="输出JSON路径 (默认 capcut_anim.json)")
    parser.add_argument("--bgm", type=str, default="sports_epic",
                        choices=["sports_epic", "fast_beats", "story_telling", "emotional"],
                        help="BGM风格 (默认 sports_epic)")
    args = parser.parse_args()

    if args.text:
        lines = [l.strip() for l in args.text.replace("\\n", "\n").split("\n") if l.strip()]
    else:
        lines = U17_SCRIPT
        print("未指定 --text，使用U17中日决赛演示脚本\n")

    builder = CapcutAnimationBuilder()
    plan = builder.build_full_plan(lines, bgm_style=args.bgm)
    builder.export_json(plan, args.output)

    # 简短输出
    rhythm = RhythmTable()
    segments = rhythm.segment_script(lines)
    plans = rhythm.assign_animations(segments)

    print()
    for i, p in enumerate(plans):
        print(f"  [{p.segment.type:6s}] {p.segment.text[:55]}...")
        print(f"        入场:{p.intro_anim:16s} 出场:{p.outro_anim:16s} "
              f"转场:{p.transition:12s} 强调:{','.join(p.emphasis_words) if p.emphasis_words else '—'}")

    total = sum(s.estimated_duration_ms for s in segments)
    print(f"\n总时长: {total/1000:.1f}s | 段数: {len(segments)}")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        demo()
    else:
        main()
