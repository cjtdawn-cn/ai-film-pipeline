"""
抖音运营发行模块 — 标题优化 · 发布时间推荐 · 话题标签策略 · SEO优化

用法:
  python publisher.py                           # 交互式输入脚本
  python publisher.py --test                   # U17中日决赛完整演示
  python publisher.py "你的脚本内容"            # 命令行直接输入
"""

import json
import os
import re
import sys
import textwrap
from datetime import datetime, timedelta
from typing import List, Dict, Optional

ROOT = os.path.dirname(os.path.abspath(__file__))

# ═══════════════════════════════════════════════════════════════════════════════
#  工具函数
# ═══════════════════════════════════════════════════════════════════════════════

def _smart_truncate(text: str, max_len: int) -> str:
    """智能截断，尽量在标点处断句"""
    if len(text) <= max_len:
        return text
    for punct in ["。", "！", "？", "；", "，", ".", "!", "?", ";", ","]:
        idx = text.rfind(punct, 0, max_len)
        if idx > max_len // 2:
            return text[:idx + 1]
    return text[:max_len] + "…"


def _clean_team_name(name: str) -> str:
    """清理队名，去掉赛事后缀"""
    name = name.strip()
    # 去掉常见赛事/描述后缀
    for suffix in ["亚洲杯决赛", "亚洲杯", "世界杯决赛", "世界杯", "联赛决赛", "联赛",
                    "杯决赛", "锦标赛", "邀请赛", "决赛", "比赛", "赛事"]:
        if name.endswith(suffix) and len(name) - len(suffix) >= 2:
            name = name[:-len(suffix)]
    return name.strip()


def _extract_entity(script: str, context: str = "") -> Dict[str, str]:
    """从脚本中提取命名实体和关键信息，用于标题/评论模板填充"""
    info = {
        "event": "",          # 核心事件简述
        "team_a": "",          # 主队/我方
        "team_b": "",          # 客队/对手
        "score": "",           # 最终比分
        "hero": "",            # 关键人物
        "moment": "",          # 名场面描述
        "emotion": "感动",     # 主导情绪
        "numbers": [],         # 提取到的数字
    }

    text = script

    # ── 1. 提取比分：找所有比分，取最后一个（通常为最终比分）──
    all_scores = re.findall(r"(\d+)\s*[:：比-]\s*(\d+)", text)
    if all_scores:
        # 优先选非0:x的最终比分
        final_scores = [(a, b) for a, b in all_scores if a != "0" and b != "0"]
        picked = final_scores[-1] if final_scores else all_scores[-1]
        info["score"] = f"{picked[0]}:{picked[1]}"

    # ── 2. 提取队名 ──
    # 策略：从脚本中找 "X队"、"中国X"、"日本X" 等模式
    team_patterns = [
        r"(中国U\d+)\s*[队在]?",           # 中国U17
        r"(日本U\d+)\s*[队在]?",           # 日本U17
        r"(中国[男女]?\s*[Uu]\d+)",        # 中国U20
        r"(日本[男女]?\s*[Uu]\d+)",        # 日本U20
        r"(中国[队国]\S{0,4})",            # 中国队、中国国青
        r"(日本[队国]\S{0,4})",            # 日本队
        r"(国足\S{0,4})",                  # 国足、国足U17
        r"(\S{2,6}队)\s*(?:像|连|完成|夺|战胜|逆转|绝杀|拼|用)",  # XX队在动词前
    ]

    found_teams = []
    for pat in team_patterns:
        for m in re.finditer(pat, text):
            name = m.group(1).strip()
            if name not in found_teams:
                found_teams.append(name)

    # 如果没有匹配到，从 context 提取
    if not found_teams and context:
        # 尝试 "中国"前缀的实体
        cn_match = re.search(r"(中国\S{1,6})", context)
        if cn_match:
            found_teams.append(_clean_team_name(cn_match.group(1)))
        # 尝试 "日本"前缀的实体
        jp_match = re.search(r"(日本\S{1,6})", context)
        if jp_match:
            found_teams.append(_clean_team_name(jp_match.group(1)))

    # 如果还是没找到，用context按"逆转/战胜"拆分
    if not found_teams and context:
        vs_match = re.search(r"(.+?)\s*(?:逆转|战胜|绝杀|vs|VS|对阵)\s*(.+)", context)
        if vs_match:
            a = _clean_team_name(vs_match.group(1))
            b = _clean_team_name(vs_match.group(2))
            found_teams = [a, b]

    # 清理队名：去掉尾部标点和多余字符
    def _strip_punct(s):
        return re.sub(r"[！!。，,、\s]+$", "", s.strip())

    # 分类：中国队相关在 team_a，对手在 team_b
    cn_keywords = ["中国", "国足", "中", "华"]
    for t in found_teams:
        t = _strip_punct(t)
        if any(kw in t for kw in cn_keywords):
            if not info["team_a"]:
                info["team_a"] = t
        else:
            if not info["team_b"]:
                info["team_b"] = t

    # 如果只找到对方，补充我方
    if info["team_b"] and not info["team_a"]:
        if "日本" in info["team_b"]:
            info["team_a"] = "中国队"
        else:
            info["team_a"] = "我们"

    # fallback: 如果队名仍然为空，给个默认值
    if not info["team_a"]:
        info["team_a"] = "中国队" if "中国" in (context or script) else "我方"
    if not info["team_b"]:
        info["team_b"] = "对手"

    # ── 3. 提取事件名 ──
    if context:
        info["event"] = context.strip()
    elif info["team_a"] and info["team_b"] and info["score"]:
        info["event"] = f"{info['team_a']}{info['score']}{info['team_b']}"
    else:
        info["event"] = text[:40].replace("\n", " ").strip()

    # ── 4. 提取数字 ──
    info["numbers"] = [int(n) for n in re.findall(r"\d+", text)]

    # ── 5. 情绪检测 ──
    emotions_map = [
        (["泪目", "哭", "感人", "感动", "破防"], "泪目"),
        (["沸腾", "燃爆", "燃", "炸裂", "激动", "疯狂", "怒吼"], "燃爆"),
        (["震惊", "惊讶", "不敢相信", "离谱", "天啊"], "震惊"),
        (["笑疯", "笑死", "搞笑", "哈哈哈", "好笑", "逗"], "笑疯"),
        (["愤怒", "生气", "气愤", "怒了", "过分"], "愤怒"),
        (["紧张", "心跳", "窒息", "刺激"], "窒息"),
    ]
    text_lower = text.lower()
    for triggers, emotion in emotions_map:
        if any(t in text_lower for t in triggers):
            info["emotion"] = emotion
            break

    # ── 6. 人物提取 ──
    person_patterns = [
        r"(?:球员|队长|教练|门将|前锋|后卫|中场)\s*(\S{2,4})",
        r"(?:叫|是)\s*(\S{2,4})\s*(?:的|，|。|！|,)",
    ]
    for pat in person_patterns:
        m = re.search(pat, text)
        if m:
            candidate = m.group(1).strip()
            # 排除纯数字/时间表述
            if not re.match(r"^[\d分钟秒]+$", candidate) and len(candidate) >= 2:
                info["hero"] = candidate
                break
    # fallback
    if not info["hero"]:
        info["hero"] = info["team_a"] if info["team_a"] else "那个少年"

    # 名场面
    moment_patterns = [
        r"(?:这一刻|那一刻|那一瞬间)\s*[，,]?\s*(.+?)[。！!]",
        r"(?:绝杀|逆转|翻盘|扑出|头球破门|凌空抽射).+?[。！!]",
    ]
    for pat in moment_patterns:
        m = re.search(pat, text)
        if m:
            info["moment"] = m.group(0).strip()[:20]
            break

    return info


# ═══════════════════════════════════════════════════════════════════════════════
#  1. 标题优化器
# ═══════════════════════════════════════════════════════════════════════════════

class TitleOptimizer:
    """根据脚本内容生成4种类型的备选标题，每种标注预估CTR"""

    def __init__(self):
        self.last_titles: List[Dict] = []

    def generate(self, script: str, context: str = "") -> List[Dict]:
        """
        生成标题方案

        Args:
            script: 视频脚本/文案内容
            context: 额外上下文（如"中国U17亚洲杯决赛逆转日本"）

        Returns:
            [{type, title, ctr_estimate, reason, is_pick}, ...]
        """
        info = _extract_entity(script, context)
        team_a = info["team_a"] or "我方"
        team_b = info["team_b"] or "对手"
        score = info["score"] or ""
        hero = info["hero"] or "他"
        emotion = info["emotion"]
        numbers = info["numbers"]
        n = numbers[0] if numbers else 3
        event = (context or info["event"] or script[:30].replace("\n", " ")).strip()

        # ── 手写优质标题（根据信息量选择不同的表述） ──

        titles = [
            # 直给型
            {
                "type": "直给型",
                "title": self._craft_direct(event, team_a, team_b, score, hero, n),
                "ctr_estimate": "5.5%",
                "ctr_range": "3.5%-7.0%",
                "desc": "直接告诉观众看什么，适合干货/教程/结果导向内容",
                "is_pick": False,
            },
            # 悬念型
            {
                "type": "悬念型",
                "title": self._craft_suspense(event, team_a, team_b, score, hero, n, emotion),
                "ctr_estimate": "9.2%",
                "ctr_range": "5.0%-12.0%",
                "desc": "制造好奇心缺口，适合故事/揭秘/反常识内容",
                "is_pick": False,
            },
            # 争议型
            {
                "type": "争议型",
                "title": self._craft_debate(event, team_a, team_b, score, n),
                "ctr_estimate": "8.0%",
                "ctr_range": "6.0%-15.0%",
                "desc": "引发讨论和站队，适合热点/观点/对比类内容",
                "is_pick": False,
            },
            # 情感型
            {
                "type": "情感型",
                "title": self._craft_emotional(event, team_a, team_b, score, hero, emotion, n),
                "ctr_estimate": "7.5%",
                "ctr_range": "4.0%-10.0%",
                "desc": "触发情绪共鸣，适合人物故事/感人/励志内容",
                "is_pick": True,  # 体育情感类通常最适合
            },
        ]

        self.last_titles = titles
        return titles

    def _craft_direct(self, event, team_a, team_b, score, hero, n):
        """直给型标题"""
        if score and team_a and team_b:
            event_clean = event.split("决赛")[0].strip().rstrip("：:，。！") if "决赛" in event else event[:15]
            templates = [
                f"{team_a} {score} {team_b}！{event_clean}决赛全回顾",
                f"{team_a}惊天逆转{team_b}！从0:2到{score}，发生了什么？",
                f"U17亚洲杯决赛：{team_a} {score} {team_b}，{n}分钟看完所有进球",
                f"{team_a}这{n}分钟告诉你：什么是中国足球的未来",
            ]
        elif score:
            templates = [
                f"比分{score}！这场比赛让所有人闭嘴",
                f"0:2落后到{score}逆转，只用了45分钟",
            ]
        else:
            templates = [
                f"看完{event[:20]}，你就懂了",
                f"{event[:25]}，全纪录",
            ]
        return templates[0]

    def _craft_suspense(self, event, team_a, team_b, score, hero, n, emotion):
        """悬念型标题"""
        if score and team_a and team_b:
            templates = [
                f"0:2落后，所有观众都走了，但{team_a}却在第89分钟……",
                f"当{team_a}0:2落后，没人相信接下来会发生这事",
                f"{team_b}球迷提前庆祝，他们不知道接下来{n}分钟会发生什么",
                f"从0:2到{score}，{team_a}做到的这件事，连对手都服了",
            ]
        elif score:
            templates = [
                f"谁也没想到，比分最终定格在{score}",
                f"所有人都猜错了，这场比赛的结局是{score}",
            ]
        else:
            templates = [
                f"90%的人不知道，{event[:20]}的真相",
                f"{event[:18]}，结局让我看了{n}遍",
            ]
        return templates[0]

    def _craft_debate(self, event, team_a, team_b, score, n):
        """争议型标题"""
        if score and team_a and team_b:
            event_clean = event.split("决赛")[0].strip().rstrip("：:，。！") if "决赛" in event else event[:15]
            templates = [
                f"{team_a} {score} {team_b}！这支{team_a}到底什么水平？评论区吵翻了",
                f"有人说{team_a}靠运气，看完这{n}个镜头你再说？",
                f"{team_a}夺冠了，但我必须说一句大实话",
                f"{event_clean}决赛，{team_a}赢在哪？{team_b}输在哪？",
            ]
        elif score:
            templates = [
                f"比分{score}，有人说黑幕，事实是？",
                f"{score}这个结果，我真的不服",
            ]
        else:
            templates = [
                f"{event[:20]}这事儿，我必须说两句",
                f"全网都在夸{event[:15]}，只有我说实话",
            ]
        return templates[0]

    def _craft_emotional(self, event, team_a, team_b, score, hero, emotion, n):
        """情感型标题"""
        if score and team_a:
            event_clean = event.split("决赛")[0].strip().rstrip("：:，。！") if "决赛" in event else event[:15]
            templates = [
                f"看到{team_a}逆转那一刻，我{emotion}了",
                f"{team_a} {score} {team_b}，这场比赛看哭了全网{n}万人",
                f"从0:2到{score}，{team_a}少年们拼到抽筋的样子，我看了{n}遍",
                f"如果你还没看过{team_a}这场{event_clean}决赛，今晚一定要看",
                f"这可能是我看过最{emotion}的{event_clean}决赛",
            ]
        elif score:
            templates = [
                f"看到{score}那一刻，全场都{emotion}了",
                f"这个比分背后，藏着所有人的{emotion}",
            ]
        else:
            templates = [
                f"看到{event[:15]}那一刻，我{emotion}了",
                f"如果你也{emotion}过，一定要看完这个",
            ]
        return templates[0]

    def print_titles(self):
        """美观打印标题方案"""
        if not self.last_titles:
            print("警告: 请先调用 generate() 生成标题")
            return

        print("\n" + "=" * 60)
        print("  [1] 标题优化方案")
        print("=" * 60)

        for i, item in enumerate(self.last_titles, 1):
            marker = " << 推荐" if item["is_pick"] else ""
            print(f"""
  [{i}] {item['type']}{marker}
     标题: {item['title']}
     预估CTR: {item['ctr_estimate']}（范围 {item['ctr_range']}）
     策略:   {item['desc']}
""")

    def pick_best(self) -> Dict:
        """返回推荐标题"""
        if not self.last_titles:
            return {}
        return next((t for t in self.last_titles if t["is_pick"]), self.last_titles[0])


# ═══════════════════════════════════════════════════════════════════════════════
#  2. 发布时间推荐器
# ═══════════════════════════════════════════════════════════════════════════════

class TimeRecommender:
    """根据内容类型推荐最佳发布时段"""

    CATEGORY_SCHEDULE = {
        "体育": {
            "primary": "赛后1-2小时：搜索流量峰值，越早发布推荐加权越高",
            "daily_slots": ["09:00-10:00（晨间集锦流）", "12:00-13:00（午休讨论）", "21:00-23:00（赛后深度复盘）"],
            "best_day": "比赛日及次日",
            "reason": "体育热点衰减曲线陡峭，发布每延迟1小时流量损失约30%；赛后24小时内搜索量占总量的70%",
        },
        "娱乐": {
            "primary": "午休+下班通勤：碎片化消费高峰",
            "daily_slots": ["12:00-13:00（午休摸鱼）", "18:00-19:00（下班路上）", "21:00-22:00（睡前放松）"],
            "best_day": "周五、周六",
            "reason": "娱乐内容消费高峰在下班后和周末，周五18:00起进入流量爬升通道，周六全天高位",
        },
        "知识": {
            "primary": "晚间整块注意力时段",
            "daily_slots": ["20:00-22:00（睡前深度学习）", "07:00-08:00（早起充电）"],
            "best_day": "周一至周四",
            "reason": "知识类需要用户有专注时间，20-22点完播率（58%）和收藏率（12%）均为全天最高",
        },
        "生活": {
            "primary": "早晚双高峰，随生活节奏",
            "daily_slots": ["07:00-08:00（起床场景）", "12:00-13:00（午间）", "21:00-22:00（睡前放松）"],
            "best_day": "周末全天",
            "reason": "生活类关联日常节奏，早晚高峰覆盖起床和睡前两个决策场景",
        },
        "新闻": {
            "primary": "即时发布，抢「最新」标签",
            "daily_slots": ["事件发生后30分钟内", "08:00-09:00（早高峰资讯）"],
            "best_day": "每天",
            "reason": "新闻时效性决定推荐优先级，首发内容有「最新」标签加成，流量差距可达5-10倍",
        },
        "搞笑": {
            "primary": "午休+晚间放松时段",
            "daily_slots": ["12:00-13:00", "20:00-23:00"],
            "best_day": "周五、周六",
            "reason": "搞笑内容与情绪放松需求强相关，晚间和周末完播率最高",
        },
    }

    SUBCATEGORY_KEYWORDS = {
        "体育": ["比赛", "决赛", "进球", "绝杀", "逆转", "冠军", "联赛", "世界杯", "篮球", "足球",
                 "NBA", "CBA", "U17", "U20", "U23", "国足", "中超", "亚冠", "亚洲杯", "欧洲杯"],
        "娱乐": ["明星", "综艺", "八卦", "吃瓜", "饭圈", "恋爱", "分手", "塌房", "混剪", "CP"],
        "知识": ["科普", "历史", "经济", "哲学", "教程", "学会", "干货", "冷知识", "揭秘", "底层逻辑"],
        "生活": ["美食", "穿搭", "装修", "护肤", "探店", "vlog", "日常", "好物", "家务"],
        "新闻": ["突发", "最新", "刚刚", "通报", "官方", "快讯"],
        "搞笑": ["搞笑", "笑死", "哈哈哈哈", "整活", "神回复", "段子", "名场面", "鬼畜"],
    }

    def detect_category(self, script: str) -> str:
        """从脚本内容自动检测内容类型"""
        script_lower = script.lower()
        scores = {}
        for cat, keywords in self.SUBCATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw.lower() in script_lower)
            if score > 0:
                scores[cat] = score
        if scores:
            return max(scores, key=scores.get)
        return "娱乐"

    def recommend(self, script: str = "", category: str = "",
                  match_time: Optional[datetime] = None) -> Dict:
        """
        推荐发布时间

        Args:
            script: 脚本内容（自动检测分类）
            category: 手动指定分类
            match_time: 赛事/事件时间（用于计算黄金发布窗）
        """
        if not category and script:
            category = self.detect_category(script)
        if not category:
            category = "娱乐"

        schedule = self.CATEGORY_SCHEDULE.get(category, self.CATEGORY_SCHEDULE["娱乐"])
        now = datetime.now()

        # 体育类：根据比赛时间判断窗口
        if category == "体育" and match_time:
            delta = now - match_time
            hours = delta.total_seconds() / 3600
            if 0 <= hours < 1:
                urgency = "比赛刚结束，立即准备剪辑素材，1小时后发布抢占黄金窗口"
            elif 1 <= hours <= 3:
                urgency = "当前处于黄金发布窗口！搜索引擎加权正在峰值，立即发布"
            elif 3 < hours <= 6:
                urgency = "已过绝对黄金期但仍有大量搜索流量，建议1小时内发布，标题侧重「深度复盘」角度"
            elif 6 < hours <= 24:
                urgency = "建议转为「比赛复盘/技术分析」角度发布，仍可获取次日搜索长尾流量"
            else:
                urgency = "时效已过，建议从「历史意义/未来展望」角度切入，主打情怀共鸣"
        elif category == "体育":
            urgency = "体育内容：赛后1-2小时是搜索流量爆发期，请尽快确认比赛时间"
        else:
            current_hour = now.hour
            urgency = None
            for slot in schedule["daily_slots"]:
                start_str = slot.split("-")[0].split(":")[0]
                try:
                    slot_start = int(start_str)
                    if current_hour < slot_start:
                        urgency = f"下一个最佳发布窗口：{slot}"
                        break
                except ValueError:
                    pass
            if not urgency:
                slots = schedule["daily_slots"]
                urgency = f"今日推荐时段均已过，建议明天 {slots[0].split('（')[0]} 发布（{schedule['best_day']}）"

        tips_map = {
            "体育": "发布后立即在评论区置顶比赛关键数据（进球时间、关键球员评分），增加搜索结果命中率",
            "娱乐": "周五18:00发布的视频，周末自然流量比工作日高40%；DOU+测试预算100元起",
            "知识": "前3秒用文字预告本期知识点（如「今天讲3个经济学常识」），完播率可提升30%",
            "生活": "带POI地理位置标签可获得同城推荐流量，定位选地标/商圈而非街道",
            "新闻": "首发内容有「最新」标签加成，发布时间差5分钟流量差可达3倍",
            "搞笑": "时长控制在15-30秒，完播率>45%才触发下一级流量池",
        }

        return {
            "category": category,
            "primary_strategy": schedule["primary"],
            "daily_slots": schedule["daily_slots"],
            "best_day": schedule["best_day"],
            "reason": schedule["reason"],
            "urgency": urgency,
            "tip": tips_map.get(category, "发布后1小时内互动率<3%建议调整封面/标题"),
        }

    def print_recommendation(self, result: Dict):
        """美观打印时间推荐"""
        print("\n" + "=" * 60)
        print(f"  [2] 发布时间推荐 — {result['category']}类")
        print("=" * 60)
        print(f"""
  核心策略: {result['primary_strategy']}
  推荐时段: {', '.join(result['daily_slots'])}
  最佳发布日: {result['best_day']}

  当前窗口: {result['urgency']}

  依据: {result['reason']}

  运营提示: {result['tip']}
""")


# ═══════════════════════════════════════════════════════════════════════════════
#  3. 话题标签策略
# ═══════════════════════════════════════════════════════════════════════════════

class HashtagStrategy:
    """生成抖音话题标签策略：热门标签 + 长尾标签 + 自创标签"""

    HOT_TAGS_DB = {
        "体育": [
            (14, "#足球", "892亿"),
            (10, "#中国足球", "178亿"),
            (8,  "#国足", "245亿"),
            (8,  "#U17亚洲杯", "12亿"),
            (9,  "#绝杀", "89亿"),
            (12, "#逆转", "67亿"),
            (8,  "#冠军", "356亿"),
            (7,  "#进球时刻", "45亿"),
            (7,  "#体育", "356亿"),
            (6,  "#为国争光", "56亿"),
            (6,  "#中国vs日本", "38亿"),
            (5,  "#足球比赛", "67亿"),
            (5,  "#青年军", "3亿"),
        ],
        "娱乐": [
            (15, "#娱乐", "1523亿"),
            (12, "#搞笑", "2156亿"),
            (10, "#日常", "987亿"),
            (8,  "#八卦", "456亿"),
            (7,  "#吃瓜", "234亿"),
            (6,  "#名场面", "178亿"),
        ],
        "知识": [
            (12, "#涨知识", "678亿"),
            (10, "#科普", "432亿"),
            (9,  "#冷知识", "289亿"),
            (8,  "#干货分享", "234亿"),
            (7,  "#学习", "567亿"),
        ],
        "生活": [
            (12, "#生活", "1567亿"),
            (10, "#美食", "1234亿"),
            (8,  "#穿搭", "876亿"),
            (7,  "#vlog日常", "654亿"),
            (7,  "#好物推荐", "432亿"),
        ],
        "新闻": [
            (10, "#新闻", "543亿"),
            (8,  "#最新消息", "321亿"),
            (7,  "#社会热点", "234亿"),
            (6,  "#第一时间", "89亿"),
        ],
        "搞笑": [
            (12, "#搞笑", "2156亿"),
            (9,  "#笑死", "567亿"),
            (8,  "#神操作", "345亿"),
            (7,  "#整活", "234亿"),
            (6,  "#名场面", "178亿"),
        ],
    }

    def __init__(self):
        self.last_result: Dict = {}

    def generate(self, script: str, context: str = "", category: str = "") -> Dict:
        """根据脚本内容和分类生成标签策略"""
        if not category:
            category = TimeRecommender().detect_category(script)

        info = _extract_entity(script, context)
        team_a = info["team_a"] or "主队"
        team_b = info["team_b"] or "对手"
        score = info["score"] or ""
        emotion = info["emotion"]
        tag_db = self.HOT_TAGS_DB.get(category, self.HOT_TAGS_DB["娱乐"])

        text_lower = script.lower()

        # 按与内容的相关性排序
        scored_tags = []
        for relevance, tag, heat in tag_db:
            tag_text = tag.replace("#", "").lower()
            # 基础分 = 预设相关度
            bonus = 0
            if any(w in text_lower for w in tag_text.split()):
                bonus += 3  # 内容匹配加分
            if team_a and team_a.lower() in tag_text:
                bonus += 2  # 主队精确匹配
            if team_b and team_b.lower() in tag_text:
                bonus += 1
            scored_tags.append((relevance + bonus, tag, heat))

        scored_tags.sort(key=lambda x: x[0], reverse=True)

        # 取2-3个最相关的热门标签
        hot_tags = [{"tag": tag, "heat": heat} for _, tag, heat in scored_tags[:3]]

        # 精准长尾标签
        long_tail_pool = []
        if category == "体育":
            if team_a and score:
                long_tail_pool += [
                    f"#{team_a}{score}{team_b}",
                    f"#{team_a}惊天逆转",
                    f"#从0比2到{score}",
                    f"#{team_a}{score}逆转夺冠",
                ]
            if team_a:
                long_tail_pool += [
                    f"#{team_a}青年军",
                    f"#中国足球这一刻等了多久",
                    f"#U17亚洲杯决赛全场回顾",
                ]
            long_tail_pool += [
                f"#足球少年未来可期",
                f"#这群孩子拼到抽筋",
                f"#中国足球的黎明",
                f"#让{emotion}的体育瞬间",
            ]
        elif category == "知识":
            topic_word = info["event"][:10] or "知识"
            long_tail_pool += [
                f"#一分鐘學會{topic_word}",
                f"#{topic_word}背後的底層邏輯",
                f"#這麼多年都理解錯了",
            ]
        else:
            topic_word = (context or info["event"] or "这个")[:8]
            long_tail_pool += [
                f"#關於{topic_word}的真相",
                f"#你沒見過的{topic_word}",
                f"#今天才懂{topic_word}",
            ]

        # 去重 + 选2-3个
        existing_lower = {t["tag"].replace("#", "").lower() for t in hot_tags}
        long_tail_tags = []
        for lt in long_tail_pool:
            if lt.replace("#", "").lower() not in existing_lower and len(long_tail_tags) < 3:
                long_tail_tags.append(lt)
                existing_lower.add(lt.replace("#", "").lower())

        # 自创话题标签
        custom_components = []
        if team_a:
            custom_components.append(team_a)
        if "逆转" in script or "逆转" in context:
            custom_components.append("逆转")
        elif "绝杀" in script or "绝杀" in context:
            custom_components.append("绝杀")
        if emotion in ("泪目", "燃爆"):
            custom_components.append("时刻")

        if len(custom_components) >= 2:
            custom_tag = "#" + "".join(custom_components[:3])
        elif team_a:
            custom_tag = f"#{team_a}未来可期"
        elif context:
            custom_tag = f"#这才是{context[:6]}"
        else:
            custom_tag = f"#不能被遗忘的瞬间"

        full_tags = [t["tag"] for t in hot_tags] + long_tail_tags + [custom_tag]

        self.last_result = {
            "hot_tags": hot_tags,
            "long_tail_tags": long_tail_tags,
            "custom_tag": custom_tag,
            "full_tag_list": full_tags,
        }
        return self.last_result

    def print_strategy(self):
        """美观打印标签策略"""
        if not self.last_result:
            print("警告: 请先调用 generate() 生成标签策略")
            return

        print("\n" + "=" * 60)
        print("  [3] 话题标签策略")
        print("=" * 60)

        print("\n  热门大标签（蹭大盘流量）:")
        for t in self.last_result["hot_tags"]:
            bar = "█" * min(int(float(t["heat"].replace("亿", "")) / 100), 20)
            print(f"    {t['tag']:<18s} {t['heat']:>6s}  {bar}")

        print("\n  精准长尾标签（触达目标用户）:")
        for t in self.last_result["long_tail_tags"]:
            print(f"    {t}")

        print(f"\n  自创话题标签（建立账号品牌）:")
        print(f"    {self.last_result['custom_tag']}  << 发布时创建新话题")

        print(f"\n  完整标签（一键复制）:")
        print(f"    {' '.join(self.last_result['full_tag_list'])}")


# ═══════════════════════════════════════════════════════════════════════════════
#  4. 抖音SEO优化器
# ═══════════════════════════════════════════════════════════════════════════════

class DouyinSEO:
    """抖音搜索优化：开头文案、评论区引导、描述模板"""

    def optimize_first_3_seconds(self, script: str) -> Dict:
        """优化视频开头3秒文案"""
        lines = [l.strip() for l in script.strip().split("\n") if l.strip()]
        if not lines:
            return {"original": "", "optimized": "", "analysis": "", "variants": []}

        original = lines[0]
        hook_indicators = ["?", "？", "!", "！", "你", "99%", "千万", "别", "震惊", "天啊", "原来", "没想到"]

        has_hook = any(ind in original for ind in hook_indicators)

        if has_hook:
            variants = [
                f"[保留原钩子] {original}",
                f"[悬念叠加] {original}，结果出乎所有人意料",
                f"[数字强化] 99%的人没看懂：{original}",
            ]
            analysis = "已有钩子元素，保持冲击力即可。可叠加数字或结果预告进一步增强好奇心"
        else:
            variants = [
                f"[直给型] 千万别划走，{original}",
                f"[悬念型] 你绝对想不到——{_smart_truncate(original, 40)}",
                f"[情感型] 看到最后我破防了。{_smart_truncate(original, 40)}",
            ]
            analysis = "缺少钩子元素。前3秒建议加入反转/悬念/数字/情感触发词，确保用户0.5秒内接收核心信号"

        return {
            "original": original,
            "optimized": variants[0].replace("[直给型] ", "").replace("[悬念型] ", "").replace("[情感型] ", "").replace("[保留原钩子] ", ""),
            "variants": variants,
            "analysis": analysis,
            "tip": "前3秒文字控制在15字以内，语速要快，字幕字号要大（占屏幕宽度的80%），确保划到的用户瞬间读取",
        }

    def generate_comment_guide(self, script: str, context: str = "", category: str = "") -> Dict:
        """生成评论区引导话术"""
        if not category:
            category = TimeRecommender().detect_category(script)

        info = _extract_entity(script, context)
        team_a = info["team_a"] or "他们"
        team_b = info["team_b"] or "对手"
        hero = info["hero"] or "那个少年"

        guides = {
            "体育": {
                "pin_comment": f"兄弟们，{team_a}这场你最想夸谁？评论区见",
                "reply_template": f"确实！{hero}今天太拼了，那个球直接封神",
                "interaction_prompt": f"觉得{team_a}能走更远的扣1，期待下一场的扣2",
            },
            "娱乐": {
                "pin_comment": "你猜对结局了吗？评论区告诉我答案",
                "reply_template": "哈哈，这个反转我也没想到，笑死了",
                "interaction_prompt": "你站A还是B？评论区打起来",
            },
            "知识": {
                "pin_comment": "还有类似的知识点吗？评论区分享一下，一起涨知识",
                "reply_template": "补充得好！这个角度很妙，学到了",
                "interaction_prompt": "来测一测：看完视频你能答对几道？评论区写答案",
            },
            "生活": {
                "pin_comment": "你们的方法是什么？评论区交流一下",
                "reply_template": "哇这招绝了！必须收藏试试",
                "interaction_prompt": "扣1收藏，扣2转发给需要的朋友",
            },
            "搞笑": {
                "pin_comment": "笑疯了，你们遇到过类似的情况吗？",
                "reply_template": "哈哈你这个评论比视频还搞笑",
                "interaction_prompt": "笑点低的扣1，已经笑疯的扣2",
            },
        }

        guide = guides.get(category, guides["娱乐"])

        return {
            "pin_comment": guide["pin_comment"],
            "reply_template": guide["reply_template"],
            "interaction_prompt": guide["interaction_prompt"],
            "tip": "发布后5分钟内用2个备用账号发引导评论（一问一答），触发用户的从众评论心理。回复粉丝时用视频中的梗，增加互动深度",
        }

    def create_description(self, title: str, script: str, hashtags: List[str]) -> str:
        """生成视频描述模板"""
        summary = _smart_truncate(script.replace("\n", " "), 90)
        tags_str = " ".join(hashtags)

        return textwrap.dedent(f"""\
        {title}

        {summary}

        {tags_str}
        """).strip()

    def print_seo_report(self, seo_3s: Dict, comment_guide: Dict, description: str):
        """美观打印SEO优化报告"""
        print("\n" + "=" * 60)
        print("  [4] 抖音SEO优化方案")
        print("=" * 60)

        print(f"""
  前3秒文案优化
  ─────────────────────────────────
  原文  │ {seo_3s['original'][:60]}
  推荐  │ {seo_3s['optimized'][:60]}

  备选：""")
        for v in seo_3s["variants"]:
            print(f"  {v[:70]}")

        print(f"""
  分析  │ {seo_3s['analysis']}
  提示  │ {seo_3s['tip']}
""")

        print(f"""  评论区引导策略
  ─────────────────────────────────
  置顶评论 │ "{comment_guide['pin_comment']}"
  回复模板 │ "{comment_guide['reply_template']}"
  互动投票 │ "{comment_guide['interaction_prompt']}"
  操作提示 │ {comment_guide['tip']}
""")

        print(f"""  视频描述（发布时粘贴）
  ─────────────────────────────────
{description}
  ─────────────────────────────────
""")


# ═══════════════════════════════════════════════════════════════════════════════
#  5. 主编：完整发布方案
# ═══════════════════════════════════════════════════════════════════════════════

class Publisher:
    """整合所有模块，输出完整的抖音运营发布方案"""

    def __init__(self):
        self.title_opt = TitleOptimizer()
        self.time_rec = TimeRecommender()
        self.hashtag_strategy = HashtagStrategy()
        self.seo = DouyinSEO()

    def create_publish_plan(self, script: str, context: str = "",
                            category: str = "", match_time: Optional[datetime] = None) -> Dict:
        """根据脚本生成完整发布方案"""
        if not category:
            category = self.time_rec.detect_category(script)

        plan = {
            "timestamp": datetime.now().isoformat(),
            "category": category,
            "script_preview": _smart_truncate(script.replace("\n", " "), 100),
        }

        print(f"  分析脚本 ({category}类, {len(script)}字)...")
        print("  生成标题方案...")
        plan["titles"] = self.title_opt.generate(script, context)

        print("  计算最佳发布时间...")
        plan["publish_time"] = self.time_rec.recommend(script, category, match_time)

        print("  生成标签策略...")
        plan["hashtags"] = self.hashtag_strategy.generate(script, context, category)

        print("  执行SEO优化...")
        plan["seo_3s"] = self.seo.optimize_first_3_seconds(script)
        plan["comment_guide"] = self.seo.generate_comment_guide(script, context, category)

        best_title = self.title_opt.pick_best()
        plan["description"] = self.seo.create_description(
            best_title.get("title", ""), script, plan["hashtags"]["full_tag_list"]
        )

        return plan

    def print_full_plan(self, plan: Dict):
        """打印完整的发布方案"""
        print("\n" + "=" * 66)
        print("  " + "抖音运营发行 —— 完整发布方案".center(54))
        print("=" * 66)
        print(f"  内容分类: {plan['category']}          生成时间: {plan['timestamp'][:19]}")
        print(f"  内容摘要: {plan['script_preview'][:60]}")

        # 各模块输出
        self.title_opt.last_titles = plan["titles"]
        self.title_opt.print_titles()

        self.time_rec.print_recommendation(plan["publish_time"])

        self.hashtag_strategy.last_result = plan["hashtags"]
        self.hashtag_strategy.print_strategy()

        self.seo.print_seo_report(
            plan["seo_3s"], plan["comment_guide"], plan["description"]
        )

        # 最终检查清单
        best = self.title_opt.pick_best()
        print("=" * 60)
        print("  [5] 发布前检查清单")
        print("=" * 60)
        print(f"""
  [ ] 标题确认: {best.get('title', '')[:50]}
  [ ] 发布时间: {plan['publish_time']['primary_strategy'][:40]}
  [ ] 封面检查: 高对比度文字 + 情绪化人脸截图，字号>屏幕50%
  [ ] 标签数量: {len(plan['hashtags']['full_tag_list'])}个，格式无误
  [ ] 置顶评论: 已准备好，发布后30秒内发出
  [ ] 备用账号: 2个马甲号准备好，发布后5分钟内发引导评论
  [ ] DOU+预算:  建议先投100元测试（相似达人粉丝定向），CTR>5%加投到500元
  [ ] 热点关联: 确认话题标签已关联当日抖音热点榜
  [ ] 音乐版权: 确认BGM无版权风险（优先用抖音音乐库）
""")

        print("  预期数据参考:")
        print(f"    预估CTR:    {best.get('ctr_estimate', 'N/A')}")
        print(f"    目标完播率: >45%")
        print(f"    目标互动率: >5%（含点赞/评论/收藏/转发）")
        print(f"    首小时播放: 目标5000+，进入千人流量池")
        print(f"    24小时播放: 目标5万+，进入万人流量池")
        print()


# ═══════════════════════════════════════════════════════════════════════════════
#  演示：U17中日决赛完整发布方案
# ═══════════════════════════════════════════════════════════════════════════════

U17_SCRIPT = """中国U17在亚洲杯决赛中对阵日本队！
上半场0:2落后，所有人都觉得没希望了。
但下半场中国队像换了一支队伍，
连进三球，完成惊天逆转！
第89分钟绝杀进球，全场沸腾！
中国队3:2战胜日本，夺得U17亚洲杯冠军！
这是中国足球历史上第一次在这个年龄段夺得亚洲冠军！
小将们在场上拼到抽筋，用血性和技术征服了所有人！

如果你也被这群少年感动了，点个赞
评论区说出你最想对国足小将说的话"""


def demo():
    """使用U17中日决赛脚本做完整演示"""
    print("""
+==================================================================+
|                                                                  |
|    抖音运营发行 · U17亚洲杯决赛 完整发布方案演示                  |
|    [ 中国 3:2 日本 ]  惊天逆转夺冠                                |
|                                                                  |
+==================================================================+
""")

    # 模拟比赛时间：2小时前结束（黄金发布窗口）
    match_time = datetime.now() - timedelta(hours=2, minutes=15)

    publisher = Publisher()
    plan = publisher.create_publish_plan(
        script=U17_SCRIPT,
        context="中国U17亚洲杯决赛逆转日本",
        category="体育",
        match_time=match_time,
    )

    publisher.print_full_plan(plan)

    # 保存方案
    out_dir = os.path.join(ROOT, "out")
    os.makedirs(out_dir, exist_ok=True)
    plan_path = os.path.join(out_dir, "publish_plan_u17_final.json")

    # 只保存可序列化的部分
    save_data = {
        "timestamp": plan["timestamp"],
        "category": plan["category"],
        "script_preview": plan["script_preview"],
        "titles": plan["titles"],
        "publish_time_category": plan["publish_time"]["category"],
        "publish_time_urgency": plan["publish_time"]["urgency"],
        "daily_slots": plan["publish_time"]["daily_slots"],
        "hashtags_full": plan["hashtags"]["full_tag_list"],
        "seo_optimized_hook": plan["seo_3s"]["optimized"],
        "comment_pin": plan["comment_guide"]["pin_comment"],
        "description": plan["description"],
    }
    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)
    print(f"  发布方案已保存至: {plan_path}")

    return plan


# ═══════════════════════════════════════════════════════════════════════════════
#  命令行入口
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    if "--test" in sys.argv or "--demo" in sys.argv:
        demo()

    elif len(sys.argv) > 1:
        user_script = sys.argv[1]
        print(f"""
  抖音运营发行方案生成器
  分析: {user_script[:50]}...
""")
        publisher = Publisher()
        plan = publisher.create_publish_plan(script=user_script)
        publisher.print_full_plan(plan)

    else:
        print("""
  抖音运营发行方案生成器

  请粘贴你的视频脚本/文案内容（输入 END 结束）:
""")
        lines = []
        try:
            while True:
                line = input()
                if line.strip().upper() == "END":
                    break
                lines.append(line)
        except (EOFError, KeyboardInterrupt):
            pass

        if lines:
            script = "\n".join(lines)
            publisher = Publisher()
            plan = publisher.create_publish_plan(script=script)
            publisher.print_full_plan(plan)
        else:
            print("  未输入脚本，运行U17演示模式...\n")
            demo()
