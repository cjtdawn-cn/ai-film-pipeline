"""
短视频BGM与音效设计模块 — Sound Designer

功能:
  1. BGM情绪分类库 — 按视频情绪匹配BGM风格
  2. 免费BGM来源 — 内置常用免费音效库信息
  3. 音效点设计 — 根据脚本情绪点自动标记音效插入位置
  4. BGM推荐输出 — 给定视频内容/情绪,输出完整音效方案

Author: Claude Code
Date:   2026-05-22
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Optional, Dict


# ══════════════════════════════════════════════════════════════════════════════
# 情绪 / 风格 枚举
# ══════════════════════════════════════════════════════════════════════════════

class Emotion(Enum):
    """视频核心情绪标签"""
    HOT_BLOODED  = "热血"      # 体育 / 竞技 / 战斗
    SUSPENSE     = "悬疑"      # 揭秘 / 推理 / 案件
    RELAXED      = "轻松"      # 生活 / Vlog / 美食
    FINANCE      = "财经"      # 商业 / 财经 / 科技
    INSPIRING    = "励志"      # 燃向 / 逆袭 / 成长
    ROMANTIC     = "浪漫"      # 情感 / 婚礼 / 旅行
    COMEDIC      = "搞笑"      # 幽默 / 段子 / 翻车
    SCARY        = "恐怖"      # 惊悚 / 鬼畜 / 深夜
    NOSTALGIC    = "怀旧"      # 回忆 / 年代感 / 青春
    TECH         = "科技"      # 数码 / 极客 / 评测


class BgmStyle(Enum):
    """BGM 音乐风格"""
    ENERGETIC_ELECTRONIC = "激昂电子"
    DRUM_BEAT            = "鼓点节奏"
    TENSION_AMBIENT      = "紧张氛围"
    RISING_TENSION       = "渐强压迫"
    LIGHT_GUITAR         = "轻快吉他"
    LO_FI                = "Lo-Fi舒缓"
    CALM_PIANO           = "沉稳钢琴"
    RHYTHMIC_PULSE       = "节奏脉冲"
    ORCHESTRAL_EPIC      = "交响史诗"
    SYNTH_POP            = "合成器流行"
    JAZZ_SWING           = "爵士摇摆"
    HIP_HOP_BEAT         = "嘻哈节拍"
    RETRO_WAVE           = "复古浪潮"
    HORROR_DRONE         = "恐怖低吟"
    ACOUSTIC_FOLK        = "原声民谣"
    CHINESE_TRADITIONAL  = "国风民乐"


# ══════════════════════════════════════════════════════════════════════════════
# 数据类
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class FreeMusicSource:
    """免费音效/音乐来源信息"""
    name: str
    url: str
    region: str              # "中国" / "国际"
    attribution: bool        # 是否需要署名
    description: str
    best_for: List[str] = field(default_factory=list)


@dataclass
class SfxPoint:
    """音效插入点"""
    time_seconds: float
    label: str               # "Hook钩子" / "反转" / "高潮" / "CTA结尾" / "转场"
    sfx_type: str            # "提示音" / "重音" / "转折音" / "收束音" / "上升音"
    sfx_suggestion: str      # 具体音效建议
    intensity: str           # "强" / "中" / "弱"


@dataclass
class BgmRecommendation:
    """BGM 推荐结果"""
    primary_style: BgmStyle
    alternative_styles: List[BgmStyle]
    bpm_range: str           # "60-80" / "120-140" 等
    keywords_cn: List[str]   # 剪映/抖音曲库搜索关键词
    keywords_en: List[str]   # YouTube/Pixabay 搜索关键词
    reference_tracks: List[str] = field(default_factory=list)


@dataclass
class SoundDesign:
    """完整的音效设计方案"""
    video_topic: str
    emotions: List[Emotion]
    duration_seconds: float
    bgm_recommendation: BgmRecommendation
    sfx_points: List[SfxPoint] = field(default_factory=list)
    free_sources: List[str] = field(default_factory=list)  # 来源名称列表


# ══════════════════════════════════════════════════════════════════════════════
# 核心引擎
# ══════════════════════════════════════════════════════════════════════════════

class SoundDesigner:
    """音效设计师 — 根据视频内容生成 BGM + 音效方案"""

    # ------------------------------------------------------------------
    # 情绪 → BGM 风格 映射表
    # ------------------------------------------------------------------
    EMOTION_STYLE_MAP: Dict[Emotion, Dict] = {
        Emotion.HOT_BLOODED: {
            "primary": BgmStyle.ENERGETIC_ELECTRONIC,
            "alternatives": [
                BgmStyle.DRUM_BEAT,
                BgmStyle.ORCHESTRAL_EPIC,
                BgmStyle.HIP_HOP_BEAT,
            ],
            "bpm": "120-160",
            "keywords_cn": ["燃向", "热血", "电子", "鼓点", "激烈", "体育", "电竞"],
            "keywords_en": ["epic", "energetic", "electronic", "sport", "hype", "drum"],
            "references": [
                "Alan Walker - Faded (Instrumental)",
                "Imagine Dragons - Believer (Instrumental)",
                "Two Steps From Hell - Heart of Courage",
            ],
        },
        Emotion.SUSPENSE: {
            "primary": BgmStyle.TENSION_AMBIENT,
            "alternatives": [
                BgmStyle.RISING_TENSION,
                BgmStyle.HORROR_DRONE,
                BgmStyle.RHYTHMIC_PULSE,
            ],
            "bpm": "60-100",
            "keywords_cn": ["悬疑", "紧张", "氛围", "渐强", "探案", "揭秘"],
            "keywords_en": ["suspense", "tension", "ambient", "mystery", "cinematic"],
            "references": [
                "Hans Zimmer - Time (Inception OST)",
                "Trent Reznor - Gone Girl OST",
            ],
        },
        Emotion.RELAXED: {
            "primary": BgmStyle.LIGHT_GUITAR,
            "alternatives": [
                BgmStyle.LO_FI,
                BgmStyle.ACOUSTIC_FOLK,
                BgmStyle.JAZZ_SWING,
            ],
            "bpm": "70-100",
            "keywords_cn": ["轻松", "轻快", "Vlog", "日常", "治愈", "吉他"],
            "keywords_en": ["lo-fi", "chill", "acoustic", "vlog", "relaxing"],
            "references": [
                "Lofi Girl streams",
                "Sungha Jung - acoustic covers",
            ],
        },
        Emotion.FINANCE: {
            "primary": BgmStyle.CALM_PIANO,
            "alternatives": [
                BgmStyle.RHYTHMIC_PULSE,
                BgmStyle.RETRO_WAVE,
                BgmStyle.JAZZ_SWING,
            ],
            "bpm": "80-110",
            "keywords_cn": ["财经", "沉稳", "钢琴", "商务", "节奏", "科技感"],
            "keywords_en": ["corporate", "piano", "business", "minimal", "tech"],
            "references": [
                "Epidemic Sound - corporate playlists",
            ],
        },
        Emotion.INSPIRING: {
            "primary": BgmStyle.ORCHESTRAL_EPIC,
            "alternatives": [
                BgmStyle.ENERGETIC_ELECTRONIC,
                BgmStyle.DRUM_BEAT,
                BgmStyle.SYNTH_POP,
            ],
            "bpm": "100-140",
            "keywords_cn": ["励志", "逆袭", "燃", "成长", "奋斗", "梦想"],
            "keywords_en": ["inspirational", "uplifting", "motivational", "epic"],
            "references": [
                "M83 - Outro",
                "Hans Zimmer - Dream is Collapsing",
            ],
        },
        Emotion.ROMANTIC: {
            "primary": BgmStyle.ACOUSTIC_FOLK,
            "alternatives": [
                BgmStyle.CALM_PIANO,
                BgmStyle.SYNTH_POP,
                BgmStyle.LIGHT_GUITAR,
            ],
            "bpm": "60-90",
            "keywords_cn": ["浪漫", "温暖", "甜蜜", "婚礼", "情感", "钢琴"],
            "keywords_en": ["romantic", "wedding", "love", "piano", "warm"],
            "references": [
                "Yiruma - River Flows in You",
                "Ludovico Einaudi - Nuvole Bianche",
            ],
        },
        Emotion.COMEDIC: {
            "primary": BgmStyle.HIP_HOP_BEAT,
            "alternatives": [
                BgmStyle.JAZZ_SWING,
                BgmStyle.SYNTH_POP,
            ],
            "bpm": "90-130",
            "keywords_cn": ["搞笑", "幽默", "鬼畜", "快节奏", "段子"],
            "keywords_en": ["funny", "comedy", "quirky", "upbeat", "fun"],
            "references": [],
        },
        Emotion.SCARY: {
            "primary": BgmStyle.HORROR_DRONE,
            "alternatives": [
                BgmStyle.TENSION_AMBIENT,
                BgmStyle.RISING_TENSION,
            ],
            "bpm": "40-70",
            "keywords_cn": ["恐怖", "惊悚", "诡异", "低音", "氛围"],
            "keywords_en": ["horror", "scary", "dark", "drone", "creepy"],
            "references": [],
        },
        Emotion.NOSTALGIC: {
            "primary": BgmStyle.RETRO_WAVE,
            "alternatives": [
                BgmStyle.CALM_PIANO,
                BgmStyle.ACOUSTIC_FOLK,
                BgmStyle.LIGHT_GUITAR,
            ],
            "bpm": "70-100",
            "keywords_cn": ["怀旧", "回忆", "青春", "年代感", "校园"],
            "keywords_en": ["nostalgic", "retro", "vintage", "memory", "old school"],
            "references": [
                "The Midnight - Sunset",
            ],
        },
        Emotion.TECH: {
            "primary": BgmStyle.RHYTHMIC_PULSE,
            "alternatives": [
                BgmStyle.RETRO_WAVE,
                BgmStyle.SYNTH_POP,
                BgmStyle.ENERGETIC_ELECTRONIC,
            ],
            "bpm": "100-130",
            "keywords_cn": ["科技", "未来感", "数码", "评测", "电子"],
            "keywords_en": ["tech", "futuristic", "digital", "review", "cyberpunk"],
            "references": [],
        },
    }

    # ------------------------------------------------------------------
    # 免费音效库
    # ------------------------------------------------------------------
    FREE_SOURCES: List[FreeMusicSource] = [
        FreeMusicSource(
            name="剪映 / 抖音自带曲库",
            url="https://www.capcut.cn/ (剪映) 或抖音 App 内",
            region="中国",
            attribution=False,
            description="国内最便捷来源,剪映内直接搜索添加,自动适配视频时长,一键智能踩点。抖音内使用无需担心版权。",
            best_for=["全部类型", "国内发布", "零门槛"],
        ),
        FreeMusicSource(
            name="YouTube Audio Library",
            url="https://www.youtube.com/audiolibrary",
            region="国际",
            attribution=False,
            description="YouTube 官方免费曲库,数千首高品质音乐/音效,大部分无需署名。下载后导入剪映即可。",
            best_for=["Vlog", "放松", "背景音乐", "国际发布"],
        ),
        FreeMusicSource(
            name="Pixabay Music",
            url="https://pixabay.com/music/",
            region="国际",
            attribution=False,
            description="完全免费,无需署名,可按情绪/风格/时长筛选。下载 mp3 直接拖入时间线。",
            best_for=["商业项目", "无需署名", "类型全面"],
        ),
        FreeMusicSource(
            name="爱给网",
            url="https://www.aigei.com/",
            region="中国",
            attribution=True,
            description="国内最大的CC协议音效素材站,包含游戏音效、影视配乐、环境音等。大部分需署名,注意看CC版本。",
            best_for=["音效素材", "游戏视频", "中国风音乐"],
        ),
        FreeMusicSource(
            name="Mixkit",
            url="https://mixkit.co/free-stock-music/",
            region="国际",
            attribution=False,
            description="高质量免费素材 (Envato 出品),音乐+SFX都有,无需署名,商用安全。",
            best_for=["高质量BGM", "商业项目", "音效包"],
        ),
        FreeMusicSource(
            name="Freesound.org",
            url="https://freesound.org/",
            region="国际",
            attribution=True,
            description="社区驱动的音效数据库,海量环境音/拟音/合成音效。CC协议,注意具体license。",
            best_for=["环境音", "拟音", "特殊音效"],
        ),
    ]

    # ------------------------------------------------------------------
    # 脚本情绪点 → 音效插入规则
    # ------------------------------------------------------------------
    # 情绪触发关键词 (脚本中出现这些词时自动标记音效点)
    SFX_TRIGGER_RULES = [
        {
            "labels": ["hook", "钩子", "开头", "震惊", "你绝对想不到", "竟然"],
            "sfx_type": "提示音 / 重音",
            "sfx_suggestion": "短促提示音 (类似消息通知/叮咚) 或低频重音 (woosh/bass hit)",
            "intensity": "强",
            "offset_rule": "at_text_start",  # 在该句开头
        },
        {
            "labels": ["反转", "但是", "然而", "没想到", "结果", "突然", "其实"],
            "sfx_type": "转折音",
            "sfx_suggestion": "悬念上升音 (riser) 或 戛然而止 (brake/stutter) 后接转折",
            "intensity": "中",
            "offset_rule": "before_text",  # 该句之前
        },
        {
            "labels": ["高潮", "巅峰", "决战", "最后", "冲刺", "决胜", "关键"],
            "sfx_type": "重音 / 渐强",
            "sfx_suggestion": "低频渐强鼓点 (build-up drum) + 重音 hit 搭配",
            "intensity": "强",
            "offset_rule": "at_text_start",
        },
        {
            "labels": ["转发", "关注", "点赞", "订阅", "评论", "一键三连", "下载"],
            "sfx_type": "收束音 / CTA音",
            "sfx_suggestion": "清脆收束 (click/chime) 或 品牌标识音 (logo sonic)",
            "intensity": "中",
            "offset_rule": "at_text_start",
        },
        {
            "labels": ["中国", "冠军", "胜利", "赢了", "夺金", "加冕", "登顶"],
            "sfx_type": "庆典音 / 重音",
            "sfx_suggestion": "烟花/礼炮 (firework) 或 管弦重音 (orchestral hit)",
            "intensity": "强",
            "offset_rule": "at_text_start",
        },
        {
            "labels": ["遗憾", "落败", "泪目", "可惜", "告别", "再见"],
            "sfx_type": "柔和收束",
            "sfx_suggestion": "钢琴单音 或 环境衰减 (ambient fade)",
            "intensity": "弱",
            "offset_rule": "at_text_start",
        },
        {
            "labels": ["让我们", "一起来", "回顾", "见证", "请看"],
            "sfx_type": "上升音 / 转场音",
            "sfx_suggestion": "短上升音 (riser) 或 swoosh 转场",
            "intensity": "中",
            "offset_rule": "before_text",
        },
    ]

    def __init__(self) -> None:
        self._designs: List[SoundDesign] = []

    # ------------------------------------------------------------------
    # 公开 API
    # ------------------------------------------------------------------

    def classify_emotion(self, text: str) -> List[Emotion]:
        """从文本内容自动识别情绪标签"""
        emotion_keywords = {
            Emotion.HOT_BLOODED:  ["热血", "燃", "决赛", "冠军", "击败", "进球", "得分", "对抗", "绝杀"],
            Emotion.SUSPENSE:     ["悬疑", "秘密", "揭秘", "真相", "背后", "阴谋", "反转", "你绝对"],
            Emotion.RELAXED:      ["日常", "Vlog", "美食", "旅行", "周末", "打卡", "探店", "治愈"],
            Emotion.FINANCE:      ["股票", "基金", "商业", "财经", "投资", "市值", "营收", "财报"],
            Emotion.INSPIRING:    ["励志", "逆袭", "努力", "坚持", "梦想", "从零开始", "改变"],
            Emotion.ROMANTIC:     ["浪漫", "爱情", "婚礼", "甜蜜", "表白", "牵手"],
            Emotion.COMEDIC:      ["搞笑", "段子", "翻车", "笑死", "离谱", "迷惑行为"],
            Emotion.SCARY:        ["恐怖", "惊悚", "鬼", "吓人", "细思极恐"],
            Emotion.NOSTALGIC:    ["回忆", "小时候", "那个年代", "青春", "从前", "十年前"],
            Emotion.TECH:         ["科技", "AI", "芯片", "评测", "数码", "代码", "算法"],
        }
        found = []
        for emotion, keywords in emotion_keywords.items():
            score = sum(1 for kw in keywords if kw in text)
            if score >= 2:
                found.append(emotion)
        if not found:
            found.append(Emotion.RELAXED)  # 默认轻松
        return found

    def recommend_bgm(self, emotions: List[Emotion]) -> BgmRecommendation:
        """根据情绪列表推荐 BGM (取第一个情绪为主,其余为辅助)"""
        primary_emotion = emotions[0]
        mapping = self.EMOTION_STYLE_MAP.get(primary_emotion)
        if mapping is None:
            mapping = self.EMOTION_STYLE_MAP[Emotion.RELAXED]

        # 合并辅助情绪的关键词
        extra_cn = []
        extra_en = []
        for e in emotions[1:]:
            m = self.EMOTION_STYLE_MAP.get(e)
            if m:
                extra_cn.extend(m["keywords_cn"][:2])
                extra_en.extend(m["keywords_en"][:2])

        return BgmRecommendation(
            primary_style=mapping["primary"],
            alternative_styles=mapping["alternatives"],
            bpm_range=mapping["bpm"],
            keywords_cn=list(dict.fromkeys(mapping["keywords_cn"] + extra_cn)),
            keywords_en=list(dict.fromkeys(mapping["keywords_en"] + extra_en)),
            reference_tracks=mapping["references"],
        )

    def detect_sfx_points(
        self,
        script: str,
        estimated_duration: float,
        script_segments: Optional[List[Dict[str, object]]] = None,
    ) -> List[SfxPoint]:
        """
        从脚本中检测音效插入点。

        script_segments 格式:
          [{"text": "台词", "start_ratio": 0.0, "end_ratio": 0.3}, ...]

        如果没有提供 segments,则按句号/换行粗略分割。
        """
        if script_segments is None:
            # 按句号/换行/感叹号自动分割
            import re
            sentences = re.split(r"[。！？\n！!？?]", script)
            sentences = [s.strip() for s in sentences if s.strip()]
            n = len(sentences)
            script_segments = []
            for i, sent in enumerate(sentences):
                script_segments.append({
                    "text": sent,
                    "start_ratio": i / max(n, 1),
                    "end_ratio": (i + 1) / max(n, 1),
                })

        sfx_points: List[SfxPoint] = []

        for seg in script_segments:
            text = str(seg.get("text", ""))
            start_ratio = float(seg.get("start_ratio", 0))
            time_at = start_ratio * estimated_duration

            for rule in self.SFX_TRIGGER_RULES:
                for lbl in rule["labels"]:
                    if lbl in text:
                        # 根据 offset_rule 微调时间
                        if rule["offset_rule"] == "before_text":
                            t = max(time_at - 0.3, 0.0)  # 文本前0.3秒
                        else:
                            t = time_at  # 文本开始处

                        sfx_points.append(SfxPoint(
                            time_seconds=round(t, 1),
                            label=text[:20],
                            sfx_type=rule["sfx_type"],
                            sfx_suggestion=rule["sfx_suggestion"],
                            intensity=rule["intensity"],
                        ))
                        break  # 每个 segment 只匹配一条规则

        # 按时间排序并去重 (同一时间点只保留 intensity 最高的)
        sfx_points.sort(key=lambda p: p.time_seconds)
        deduped: List[SfxPoint] = []
        for p in sfx_points:
            if deduped and abs(p.time_seconds - deduped[-1].time_seconds) < 0.5:
                # 时间过近,保留 intensity 更强的
                intensity_order = {"强": 3, "中": 2, "弱": 1}
                if intensity_order.get(p.intensity, 1) > intensity_order.get(deduped[-1].intensity, 1):
                    deduped[-1] = p
            else:
                deduped.append(p)

        return deduped

    def get_free_sources(self, emotions: List[Emotion]) -> List[FreeMusicSource]:
        """根据情绪推荐最适合的免费音效来源"""
        primary = emotions[0]
        # 需要中国风或有中国关键词的情绪,优先推荐爱给网
        if primary in (Emotion.NOSTALGIC, Emotion.INSPIRING):
            order = [0, 3, 1, 2, 4, 5]  # 剪映第一, 爱给网第二
        else:
            order = [0, 1, 2, 3, 4, 5]  # 默认: 剪映 > YouTube > Pixabay > 爱给网
        return [self.FREE_SOURCES[i] for i in order]

    def design(
        self,
        video_topic: str,
        script: str,
        estimated_duration: float,
        emotions: Optional[List[Emotion]] = None,
        script_segments: Optional[List[Dict[str, object]]] = None,
    ) -> SoundDesign:
        """
        一键生成完整音效设计方案。

        参数:
          video_topic:       视频主题/标题
          script:            完整脚本文本
          estimated_duration: 预估视频时长 (秒)
          emotions:          手动指定情绪 (可选,不传则自动识别)
          script_segments:   脚本分段 (可选,用于精确时间定位)

        返回:
          SoundDesign 对象
        """
        if emotions is None:
            emotions = self.classify_emotion(script)

        bgm = self.recommend_bgm(emotions)
        sfx = self.detect_sfx_points(script, estimated_duration, script_segments)
        sources = [s.name for s in self.get_free_sources(emotions)]

        design = SoundDesign(
            video_topic=video_topic,
            emotions=emotions,
            duration_seconds=estimated_duration,
            bgm_recommendation=bgm,
            sfx_points=sfx,
            free_sources=sources,
        )
        self._designs.append(design)
        return design

    # ------------------------------------------------------------------
    # 输出格式化
    # ------------------------------------------------------------------

    def format_report(self, design: SoundDesign) -> str:
        """将设计方案格式化为可读报告"""
        emo_str = " + ".join(e.value for e in design.emotions)
        bgm = design.bgm_recommendation

        lines = [
            "=" * 64,
            f"  音效设计方案: {design.video_topic}",
            "=" * 64,
            "",
            f"  视频时长: {design.duration_seconds}s",
            f"  情绪标签: {emo_str}",
            "",
            "-" * 48,
            "  [1] BGM 推荐",
            "-" * 48,
            f"  主风格:   {bgm.primary_style.value}",
            f"  备选风格: {', '.join(s.value for s in bgm.alternative_styles)}",
            f"  BPM 范围: {bgm.bpm_range}",
            "",
            f"  剪映/抖音搜索关键词:",
            f"    {', '.join(bgm.keywords_cn)}",
            f"  YouTube/Pixabay搜索关键词:",
            f"    {', '.join(bgm.keywords_en)}",
        ]

        if bgm.reference_tracks:
            lines.append("")
            lines.append("  参考曲目:")
            for t in bgm.reference_tracks:
                lines.append(f"    - {t}")

        lines.extend([
            "",
            "-" * 48,
            "  [2] 音效插入时间线",
            "-" * 48,
        ])

        if not design.sfx_points:
            lines.append("  (未检测到明显音效点)")
        else:
            lines.append(f"  {'时间':>6s}  {'强度':<4s} {'类型':<14s} 触发文本")
            lines.append(f"  {'-'*6}  {'-'*4} {'-'*14}  {'-'*20}")
            for p in design.sfx_points:
                time_str = f"{p.time_seconds:.1f}s"
                lines.append(
                    f"  {time_str:>6s}  {p.intensity:<4s} {p.sfx_type:<14s} {p.label}"
                )

        lines.extend([
            "",
            "-" * 48,
            "  [3] 免费音源推荐 (按推荐优先级)",
            "-" * 48,
        ])
        for i, name in enumerate(design.free_sources, 1):
            src = next((s for s in self.FREE_SOURCES if s.name == name), None)
            if src:
                lines.append(f"  {i}. {src.name}")
                lines.append(f"     {src.url}")
                lines.append(f"     署名要求: {'需要' if src.attribution else '不需要'}")
                lines.append(f"     备注: {src.description[:60]}...")
                lines.append("")

        # 音效素材补充
        lines.append("-" * 48)
        lines.append("  [4] 推荐音效素材 (下载关键词)")
        lines.append("-" * 48)
        sfx_keywords = self._collect_sfx_keywords(design)
        lines.append(f"  Pixabay:   {', '.join(sfx_keywords['pixabay'][:6])}")
        lines.append(f"  爱给网:    {', '.join(sfx_keywords['aigei'][:6])}")
        lines.append(f"  Mixkit:    {', '.join(sfx_keywords['mixkit'][:6])}")
        lines.append("")
        lines.append("=" * 64)

        return "\n".join(lines)

    def _collect_sfx_keywords(self, design: SoundDesign) -> Dict[str, List[str]]:
        """收集音效素材下载关键词"""
        all_kw = set()
        for p in design.sfx_points:
            if "提示音" in p.sfx_type:
                all_kw.update(["notification sound", "bell ding", "chime"])
            if "重音" in p.sfx_type:
                all_kw.update(["bass hit", "impact", "boom", "heavy hit"])
            if "转折" in p.sfx_type:
                all_kw.update(["riser", "transition", "swoosh", "whoosh"])
            if "收束" in p.sfx_type:
                all_kw.update(["click", "end chime", "logo sound"])
            if "庆典" in p.sfx_type:
                all_kw.update(["firework", "crowd cheer", "victory"])
            if "上升" in p.sfx_type:
                all_kw.update(["riser", "build up", "sweep"])

        # 按平台分类关键词
        return {
            "pixabay": sorted(all_kw),
            "aigei": sorted(["提示音", "转场", "重击", "胜利", "鼓点", "上升"]),
            "mixkit": sorted(all_kw),
        }

    def to_json(self, design: SoundDesign) -> str:
        """将设计方案导出为 JSON 字符串"""
        output = {
            "video_topic": design.video_topic,
            "emotions": [e.value for e in design.emotions],
            "duration_seconds": design.duration_seconds,
            "bgm": {
                "primary_style": design.bgm_recommendation.primary_style.value,
                "alternative_styles": [s.value for s in design.bgm_recommendation.alternative_styles],
                "bpm_range": design.bgm_recommendation.bpm_range,
                "keywords_cn": design.bgm_recommendation.keywords_cn,
                "keywords_en": design.bgm_recommendation.keywords_en,
                "reference_tracks": design.bgm_recommendation.reference_tracks,
            },
            "sfx_points": [
                {
                    "time": p.time_seconds,
                    "label": p.label,
                    "type": p.sfx_type,
                    "suggestion": p.sfx_suggestion,
                    "intensity": p.intensity,
                }
                for p in design.sfx_points
            ],
            "recommended_sources": design.free_sources,
        }
        return json.dumps(output, ensure_ascii=False, indent=2)


# ══════════════════════════════════════════════════════════════════════════════
# 测试 & 演示
# ══════════════════════════════════════════════════════════════════════════════

def _demo_u17_final():
    """
    U17 中日决赛短视频脚本 — 音效设计方案演示
    视频主题: 中国 U17 亚洲杯决赛绝杀日本,历史首冠!
    """

    # 模拟脚本 (已分段,带时间比例)
    script_segments = [
        {"text": "这一刻,中国足球等了18年。", "start_ratio": 0.00, "end_ratio": 0.08},
        {"text": "U17亚洲杯决赛——中国 vs 日本", "start_ratio": 0.08, "end_ratio": 0.15},
        {"text": "开场仅仅8分钟,中国队前场逼抢得手!", "start_ratio": 0.15, "end_ratio": 0.22},
        {"text": "张洪福一脚远射击中横梁!", "start_ratio": 0.22, "end_ratio": 0.28},
        {"text": "可惜!差一点!!", "start_ratio": 0.28, "end_ratio": 0.32},
        {"text": "上半场第35分钟,日本队率先破门...", "start_ratio": 0.32, "end_ratio": 0.38},
        {"text": "1:0,中国落后。", "start_ratio": 0.38, "end_ratio": 0.42},
        {"text": "但没想到——下半场风云突变!", "start_ratio": 0.42, "end_ratio": 0.48},
        {"text": "第60分钟,中国队角球开出!", "start_ratio": 0.48, "end_ratio": 0.53},
        {"text": "王钰栋头球!!进了!!1:1!!", "start_ratio": 0.53, "end_ratio": 0.60},
        {"text": "全场沸腾!中国队扳平比分!", "start_ratio": 0.60, "end_ratio": 0.66},
        {"text": "比赛来到伤停补时,第92分钟...", "start_ratio": 0.66, "end_ratio": 0.72},
        {"text": "禁区前沿混乱!球到了蒯纪闻脚下——", "start_ratio": 0.72, "end_ratio": 0.78},
        {"text": "他起脚了!!!", "start_ratio": 0.78, "end_ratio": 0.82},
        {"text": "球进了!!!!!2:1!!!!!", "start_ratio": 0.82, "end_ratio": 0.88},
        {"text": "绝杀!中国队绝杀了日本队!!", "start_ratio": 0.88, "end_ratio": 0.93},
        {"text": "U17亚洲杯冠军!中国队!", "start_ratio": 0.93, "end_ratio": 0.97},
        {"text": "关注我,不错过每一个历史时刻!", "start_ratio": 0.97, "end_ratio": 1.00},
    ]

    full_script = " ".join(str(s["text"]) for s in script_segments)

    # 创建音效设计师
    designer = SoundDesigner()

    # 一键生成方案
    design = designer.design(
        video_topic="U17亚洲杯决赛 中国2:1绝杀日本 首夺冠军",
        script=full_script,
        estimated_duration=90.0,  # 90秒短视频
        emotions=[Emotion.HOT_BLOODED, Emotion.INSPIRING],  # 热血 + 励志
        script_segments=script_segments,
    )

    # 输出报告
    report = designer.format_report(design)
    print(report)
    print()

    # 也输出 JSON 版本
    print("─" * 64)
    print("  JSON 导出:")
    print("─" * 64)
    print(designer.to_json(design))


# ══════════════════════════════════════════════════════════════════════════════
# 入口
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    _demo_u17_final()
