"""
🎬 热点→剪映草稿 全自动管线 (2026版)
1. 抓热点 + 智谱写稿（7种钩子模板）
2. Humanizer 去AI痕迹
3. capcut-mcp 生成剪映草稿（动态字幕+节奏时间轴）
4. 复制到剪映草稿目录 → 打开剪映加BGM/特效 → 导出

用法:
  python pipeline_capcut.py                    # 自动抓热点
  python pipeline_capcut.py "你的主题"          # 指定主题
"""
import requests, json, os, sys, time, shutil, random

ROOT = os.path.dirname(os.path.abspath(__file__))
ZHIPU_KEY = os.environ.get("ZHIPU_API_KEY", "YOUR_ZHIPU_KEY")
CAPCUT_API = "http://localhost:9000"
LICENSE_KEY = "YOUR_CAPCUT_KEY"

CAPCUT_DRAFTS = os.path.expandvars(
    r"%LOCALAPPDATA%\JianyingPro\User Data\Projects\com.lveditor.draft"
)

# ═══════════════════════════════════
#  2026爆款钩子模板库
# ═══════════════════════════════════

HOOK_TEMPLATES = {
    "反常识": {
        "formula": "先给一个颠覆认知的结论，制造好奇心缺口",
        "opener": "你以为X，其实Y / 99%的人都搞反了 / 这件事完全被误解了",
        "best_for": "科普、财经、社会热点",
        "rhythm": "快-慢-快",
    },
    "承诺型": {
        "formula": "明确告诉观众看完能得到什么具体价值",
        "opener": "看完这个视频，你就知道... / 一分钟教会你... / 以后别再...",
        "best_for": "教程、工具、技能分享",
        "rhythm": "慢-快-慢",
    },
    "数据冲击": {
        "formula": "用一个惊人的具体数字开头，制造信任感",
        "opener": "90%的人不知道... / 只花3块钱就... / 1200万人都在犯这个错",
        "best_for": "冷知识、省钱、健康",
        "rhythm": "快-快-快",
    },
    "痛点前置": {
        "formula": "直接戳中高频痛点，让观众产生「这不就是我吗」",
        "opener": "你是不是也... / 每次...都想死 / 最烦的就是...",
        "best_for": "生活、职场、情感、育儿",
        "rhythm": "慢-快-慢",
    },
    "悬念开局": {
        "formula": "讲一半藏一半，逼观众看完才知道结局",
        "opener": "今天说个真事... / 我差点就...直到... / 结局你绝对想不到",
        "best_for": "故事、娱乐、奇闻",
        "rhythm": "慢-慢-快",
    },
    "秘密揭露": {
        "formula": "制造「内幕感」，让观众觉得赚到了独家信息",
        "opener": "行内人不会告诉你... / 商家最怕你知道... / 内部员工透露...",
        "best_for": "消费、避坑、职场内幕",
        "rhythm": "快-慢-快",
    },
    "身份代入": {
        "formula": "3个具象细节让观众对号入座，触发「这就是我」",
        "opener": "如果你也有这种习惯... / 这种人的通病就是... / XX星座的都懂",
        "best_for": "情感、星座、性格、生活方式",
        "rhythm": "慢-慢-快",
    },
}

# 2026年脚本结构模板
SCRIPT_STRUCTURE = """
【结构要求 — 严格遵循】
输出格式用标记分隔，每行一句，按口语断句换行：

[Hook: 0-3秒]
1句。短促有力，3秒内触发好奇/惊讶/共鸣。

[Keep: 4-18秒]
4-5句，每句一行。长短句交替，有具体细节和态度。
- 第1行：具体案例/细节
- 第2行：展开说
- 第3-4行：反转/意外点/数据冲击
- 加入具体数字、人名、场景

[CTA: 最后5秒]
1-2句。用提问/投票/挑战结尾。
"""

# ═══════════════════════════════════
#  Step 1: 抓热点 + 写稿
# ═══════════════════════════════════

def fetch_hotspots():
    import hotspot_hunter
    hotspots = hotspot_hunter.collect_all_hotspots()
    print(f"📊 抓到 {len(hotspots)} 条热点")
    return hotspots[:10]

def pick_best_hook(topic):
    """根据话题自动选最佳钩子类型"""
    keywords_map = {
        "反常识": ["骗", "假", "真相", "谣言", "反转", "误区", "错", "竟然", "居然", "不是", "其实"],
        "承诺型": ["怎么", "如何", "方法", "技巧", "教程", "学会", "秘诀", "攻略"],
        "数据冲击": ["钱", "元", "万", "亿", "%", "排名", "第一", "最", "多少"],
        "痛点前置": ["上班", "工资", "结婚", "孩子", "焦虑", "失眠", "胖", "穷", "累", "烦"],
        "悬念开局": ["事件", "事故", "案件", "去世", "突发", "震惊", "曝光","爆出"],
        "秘密揭露": ["内幕", "潜规则", "商家", "行业", "公司", "员工", "内部", "禁"],
        "身份代入": ["你", "我", "星座", "性格", "习惯", "90后", "00后"],
    }
    for hook_type, keywords in keywords_map.items():
        for kw in keywords:
            if kw in topic:
                return hook_type
    return random.choice(["反常识", "悬念开局", "痛点前置"])

def write_script(topic):
    """智谱GLM按2026钩子模板写稿"""
    hook_type = pick_best_hook(topic)
    hook_info = HOOK_TEMPLATES[hook_type]

    print(f"✍️  写稿: {topic}")
    print(f"  🪝 选中钩子: 【{hook_type}】— {hook_info['formula']}")

    system_prompt = f"""你是抖音百万粉口播博主。写20秒爆款短视频脚本，总共6-8句。

当前热点: {topic}
选定钩子: 【{hook_type}】— {hook_info['formula']}
开头示例: {hook_info['opener']}
节奏要求: {hook_info['rhythm']}

{SCRIPT_STRUCTURE}

核心规则:
- 总共输出6-8句（Hook 1句 + Keep 4-5句 + CTA 1-2句）
- [Hook]必须3秒内触发好奇/惊讶/共鸣，不准说"大家好"
- [Keep]每行单独一句，不超过20字，长短句交替
- 必须加入1个具体数字/金额/百分比
- [CTA]用提问或投票结尾，不说"点赞关注"
- 口语化像跟朋友聊天，加口癖和语气词
- 禁止: "此外""至关重要""深入探讨""总而言之""值得注意的是"
- 禁止: 排比句、破折号、表情符号

只输出脚本，用[Hook][Keep][CTA]标记分段。"""

    resp = requests.post(
        "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        headers={"Authorization": f"Bearer {ZHIPU_KEY}", "Content-Type": "application/json"},
        json={
            "model": "glm-4-flash",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"主题: {topic}"},
            ],
            "max_tokens": 600,
        },
        timeout=30,
    )
    content = resp.json()["choices"][0]["message"]["content"].strip()
    return content, hook_type

# ═══════════════════════════════════
#  Step 2: 去AI痕迹
# ═══════════════════════════════════

def humanize_script(script):
    """用Humanizer-zh原则去AI痕迹"""
    print("🔍 去AI痕迹...")

    resp = requests.post(
        "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        headers={"Authorization": f"Bearer {ZHIPU_KEY}", "Content-Type": "application/json"},
        json={
            "model": "glm-4-flash",
            "messages": [
                {"role": "system", "content": """你是文字编辑，专门去AI写作痕迹。重写成更像真人说的话。

核心规则:
1. 删除所有AI填充词: "此外""至关重要""深入探讨""总而言之""值得注意的是""在当今时代"
2. 打破工整结构 — 长短句交替，不要排比句
3. 注入人味 — 加1-2个口语小毛病/犹豫/即兴插入语
4. 具体>抽象 — "省了30块"不说"显著节省开支"
5. 有态度 — 对事实做出反应，不只是报告
6. 允许混乱 — 完美结构 = AI
7. 保留[Hook][Keep][CTA]分段标记

只输出改写后的脚本。"""},
                {"role": "user", "content": f"原稿:\n{script}"},
            ],
            "max_tokens": 600,
        },
        timeout=30,
    )
    return resp.json()["choices"][0]["message"]["content"].strip()

# ═══════════════════════════════════
#  Step 3: capcut-mcp 生成草稿
# ═══════════════════════════════════

def call_api(endpoint, data):
    data["license_key"] = LICENSE_KEY
    resp = requests.post(f"{CAPCUT_API}/{endpoint}", json=data,
        headers={"Content-Type": "application/json"})
    return resp.json()

def parse_script_sections(script):
    """解析[Hook][Keep][CTA]分段，返回带时间分配的行列表"""
    lines = []
    current_section = "keep"
    for line in script.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("[Hook") or line.startswith("[HOOK"):
            current_section = "hook"
            content = line.split("]", 1)[-1].strip()
            if content:
                lines.append({"text": content, "section": "hook", "duration": 2.0})
        elif line.startswith("[Keep") or line.startswith("[KEEP"):
            current_section = "keep"
            content = line.split("]", 1)[-1].strip()
            if content:
                lines.append({"text": content, "section": "keep", "duration": 2.5})
        elif line.startswith("[CTA") or line.startswith("[cta"):
            current_section = "cta"
            content = line.split("]", 1)[-1].strip()
            if content:
                lines.append({"text": content, "section": "cta", "duration": 2.0})
        else:
            # 普通行，根据当前段分配时长
            dur = 1.5 if current_section == "hook" else (2.0 if current_section == "cta" else 2.5)
            lines.append({"text": line, "section": current_section, "duration": dur})

    # 如果没有分段标记，把所有行当keep处理
    if not any(l["section"] in ("hook", "cta") for l in lines):
        for i, l in enumerate(lines):
            if i == 0:
                l["section"] = "hook"
                l["duration"] = 2.0
            elif i == len(lines) - 1:
                l["section"] = "cta"
                l["duration"] = 2.0

    return lines

def create_capcut_draft(script_text, topic="今日热点", hook_type=""):
    """把脚本转成剪映草稿 — 带2026节奏时间轴"""
    print(f"\n🎬 生成剪映草稿: {topic}")
    print(f"  🪝 钩子类型: {hook_type}")

    # 1. 创建草稿
    result = call_api("create_draft", {"draft_name": topic[:20]})
    if not result.get("success"):
        print(f"❌ 创建草稿失败: {result}")
        return None
    draft_id = result["output"]["draft_id"]
    print(f"  ✅ 草稿ID: {draft_id}")

    # 2. 添加黑色背景
    call_api("add_video", {
        "draft_id": draft_id,
        "video_url": "https://upload.wikimedia.org/wikipedia/commons/8/87/Black_colour.jpg",
        "width": 1080, "height": 1920,
        "start": 0, "end": 60,
        "track_name": "bg",
    })

    # 3. 解析脚本结构，计算时间轴
    sections = parse_script_sections(script_text)

    # 2026节奏法则: Hook快(1.5s/句) → Keep中(2.5s/句) → CTA快(2s/句)
    time_offset = 0
    rhythm_by_section = {"hook": 1.8, "keep": 2.5, "cta": 2.0}
    sub_lines = []

    for i, sec in enumerate(sections):
        duration = rhythm_by_section.get(sec["section"], 2.5)
        start_time = time_offset
        end_time = start_time + duration

        sub_lines.append({
            "text": sec["text"],
            "start": start_time,
            "end": end_time,
            "section": sec["section"],
        })

        # Hook段加停顿（制造张力）
        if sec["section"] == "hook":
            time_offset = end_time + 0.3  # Hook后多停0.3秒
        elif sec["section"] == "cta" and i == len(sections) - 1:
            end_time += 0.5  # 最后一句多留半秒
            sub_lines[-1]["end"] = end_time
            time_offset = end_time
        else:
            time_offset = end_time

    # 4. 逐行添加字幕（带2026风格）
    for i, sl in enumerate(sub_lines):
        # Hook用大号字+黄色，Keep用白色，CTA用强调色
        if sl["section"] == "hook":
            font_color = "#FFD700"  # 金色钩子
            font_size = 6.5
            pos_y = 0  # 居中
        elif sl["section"] == "cta":
            font_color = "#FF6B6B"  # 红色CTA
            font_size = 6.0
            pos_y = 0
        else:
            font_color = "#FFFFFF"
            font_size = 5.5
            pos_y = -0.6  # 下方

        call_api("add_text", {
            "draft_id": draft_id,
            "text": sl["text"],
            "start": sl["start"],
            "end": sl["end"],
            "font": "文轩体",
            "color": font_color,
            "size": font_size,
            "track_name": f"sub_{i}",
            "transform_y": pos_y,
            "transform_x": 0,
            "border_color": "#000000",
            "border_width": 2.0,
            "border_alpha": 0.5,
            # Hook加淡入动画
            "intro_animation": "Fade_In" if sl["section"] == "hook" else None,
            "intro_duration": 0.3 if sl["section"] == "hook" else 0,
        })

        section_emoji = {"hook": "🪝", "keep": "📝", "cta": "🎯"}
        print(f"  {section_emoji.get(sl['section'], '  ')} [{sl['start']:.1f}s] {sl['text'][:35]}...")

    total_duration = time_offset
    print(f"\n  ⏱️  总时长: {total_duration:.1f}秒 | 字幕: {len(sub_lines)}条")

    # 5. 保存草稿
    result = call_api("save_draft", {
        "draft_id": draft_id,
        "draft_folder": CAPCUT_DRAFTS,
    })
    print(f"  💾 保存: {'✅' if result.get('success') else '❌'}")

    # 6. 复制草稿到剪映专业版草稿目录
    capcut_mcp_dir = os.path.join(ROOT, "capcut-mcp")
    dfd_path = os.path.join(capcut_mcp_dir, draft_id)
    target_path = os.path.join(CAPCUT_DRAFTS, draft_id)

    if os.path.exists(dfd_path):
        if os.path.exists(target_path):
            shutil.rmtree(target_path)
        shutil.copytree(dfd_path, target_path)
        print(f"  📂 复制到剪映: ✅ ({target_path})")
    else:
        print(f"  ⚠️ 草稿文件夹未找到: {dfd_path}")

    return draft_id, total_duration

# ═══════════════════════════════════
#  主流程
# ═══════════════════════════════════

def main():
    topic_arg = sys.argv[1] if len(sys.argv) > 1 else None

    print("""
╔══════════════════════════════════════╗
║   🎬 热点→剪映 2026钩子管线         ║
║   7种钩子 x 去AI味 x 剪映精修       ║
╚══════════════════════════════════════╝
""")

    # 1. 确定主题
    if topic_arg:
        topic = topic_arg
        print(f"📌 指定主题: {topic}")
    else:
        print("🔍 抓取今日热点...")
        hotspots = fetch_hotspots()
        if not hotspots:
            print("❌ 没有抓到热点")
            return
        topic = hotspots[0]["title"]
        print(f"📌 自动选择: {topic}")

    # 2. 写稿（自动选钩子）
    raw_script, hook_type = write_script(topic)
    print(f"\n── 初稿 [{hook_type}] ──\n{raw_script}\n")

    # 3. 去AI痕迹
    humanized = humanize_script(raw_script)
    print(f"\n── 去AI味后 ──\n{humanized}\n")

    # 4. 生成剪映草稿
    draft_id, duration = create_capcut_draft(humanized, topic, hook_type)

    if draft_id:
        print(f"""
╔══════════════════════════════════════╗
║ ✅ 剪映草稿已生成！                  ║
╠══════════════════════════════════════╣
║ 📂 打开剪映 → 「草稿」→「{topic[:16]}」║
║                                      ║
║ 🎤 1. 文本朗读 → 选个自然音色       ║
║ 🎵 2. 音频 → 曲库 → 搜热门BGM      ║
║ 🎨 3. 调节 → 套个滤镜               ║
║ 📤 4. 导出 → 1080p → 发抖音         ║
║                                      ║
║ ⏱️  视频时长: {duration:.0f}秒                    ║
║ 🪝 钩子类型: {hook_type}                      ║
╚══════════════════════════════════════╝
""")

    # 保存文案
    os.makedirs(os.path.join(ROOT, "out"), exist_ok=True)
    output_path = os.path.join(ROOT, "out", "capcut_script.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"主题: {topic}\n钩子: {hook_type}\n时长: {duration:.0f}秒\n\n── 去AI味版本 ──\n{humanized}\n\n── 原始版本 ──\n{raw_script}")
    print(f"📝 文案保存: {output_path}")


if __name__ == "__main__":
    main()
