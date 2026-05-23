"""
🔥 热点猎手 — 自动抓热点 → AI写爆款稿 → 一键出片

从微博/今日头条/抖音 抓当日热点，挑最适合做视频的，
自动生成抖音爆款脚本，配合视频管线直接出片。

用法:
  python hotspot_hunter.py           # 抓热点+写稿
  python hotspot_hunter.py --make    # 抓热点+写稿+配音+出片
"""
import requests
import json
import os
import sys
import subprocess
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
ZHIPU_KEY = os.environ.get("ZHIPU_API_KEY", "YOUR_ZHIPU_KEY")

# ═══════════════════════════════════
#  Step 1: 多渠道抓热点
# ═══════════════════════════════════

def fetch_weibo_hot():
    """微博热搜 — 需要带Cookie"""
    try:
        resp = requests.get("https://weibo.com/ajax/side/hotSearch", timeout=10,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json",
                "Referer": "https://weibo.com/",
                "Cookie": "SUB=_2AkMR;",
            })
        items = resp.json().get("data", {}).get("realtime", [])
        results = []
        for i in items:
            num = i.get("num", 0)
            if isinstance(num, str):
                try: num = int(num)
                except: num = 0
            results.append({"title": i["word"], "hot": num, "source": "微博"})
        return results[:20]
    except Exception as e:
        print(f"  ⚠️ 微博抓取失败: {e}")
        return []


def fetch_toutiao_hot():
    """今日头条热榜"""
    try:
        resp = requests.get("https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc", timeout=10,
            headers={"User-Agent": "Mozilla/5.0"})
        items = resp.json().get("data", [])
        results = []
        for i in items:
            hv = i.get("HotValue", 0)
            if isinstance(hv, str):
                try: hv = int(hv)
                except: hv = 0
            results.append({"title": i["Title"], "hot": hv, "source": "头条"})
        return results[:20]
    except Exception as e:
        print(f"  ⚠️ 头条抓取失败: {e}")
        return []


def fetch_douyin_hot():
    """抖音热点榜"""
    try:
        resp = requests.get("https://www.douyin.com/aweme/v1/web/hot/search/list/", timeout=10,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://www.douyin.com/",
            })
        items = resp.json().get("data", {}).get("word_list", [])
        results = []
        for i in items:
            hot_val = i.get("hot_value", i.get("sentence_count", 0))
            if isinstance(hot_val, str):
                try: hot_val = int(hot_val)
                except: hot_val = 0
            title = i.get("word", i.get("sentence", ""))
            if title:
                results.append({"title": title, "hot": hot_val, "source": "抖音"})
        return results[:20]
    except Exception as e:
        print(f"  ⚠️ 抖音抓取失败: {e}")
        return []


def collect_all_hotspots():
    """汇总所有平台热点"""
    print("🔍 抓取热点中...")
    all_hot = []
    all_hot.extend(fetch_weibo_hot())
    all_hot.extend(fetch_toutiao_hot())
    all_hot.extend(fetch_douyin_hot())
    # 按热度排序
    return sorted(all_hot, key=lambda x: x.get("hot", 0) if isinstance(x.get("hot"), (int, float)) else 0, reverse=True)


# ═══════════════════════════════════
#  Step 2: AI 判断哪些热点适合做视频
# ═══════════════════════════════════

VIRAL_TEMPLATES = """你是抖音千万粉博主，擅长把任何热点变成爆款短视频。
以下是抖音爆款视频模板库：

1. 【三秒反转】"你以为X，其实Y" — 开头颠覆认知
2. 【数字清单】"99%的人不知道的3个X" — 制造好奇心
3. 【冷知识】"今天才知道..." — 分享感+惊讶
4. 【避坑指南】"千万别做X" — 恐惧驱动
5. 【极简教程】"一分钟学会X" — 实用收藏
6. 【故事叙述】"说个真事..." — 第一人称代入
7. 【对比冲击】"X vs Y，差距这么大" — 视觉化对比
8. 【情感共鸣】"如果你也觉得累..." — 情绪共鸣

对每个热点，判断：热度分(1-10)、适合哪个模板、爆款潜力(1-10)
"""


def pick_best_topics(hotspots):
    """用智谱GLM选最适合做视频的热点"""
    if not hotspots:
        return "（无热点数据）"

    top20 = hotspots[:20]
    summary = "\n".join([f"{i+1}. [{h['source']}] {h['title']}" for i, h in enumerate(top20)])

    print(f"🤖 智谱GLM分析 {len(top20)} 条热点...")

    resp = requests.post(
        "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        headers={"Authorization": f"Bearer {ZHIPU_KEY}", "Content-Type": "application/json"},
        json={
            "model": "glm-4-flash",
            "messages": [
                {"role": "system", "content": VIRAL_TEMPLATES},
                {"role": "user", "content": f"今日热点：\n{summary}\n\n挑5个最适合做抖音视频的，给每一条：热度分、推荐模板、一句话爆款标题"},
            ],
            "max_tokens": 800,
        },
        timeout=30,
    )
    return resp.json()["choices"][0]["message"]["content"]


# ═══════════════════════════════════
#  Step 3: 生成爆款脚本
# ═══════════════════════════════════

def write_viral_script(topic, template_hint=""):
    """针对单个热点写爆款脚本"""
    print(f"✍️  写稿: {topic}")

    resp = requests.post(
        "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        headers={"Authorization": f"Bearer {ZHIPU_KEY}", "Content-Type": "application/json"},
        json={
            "model": "glm-4-flash",
            "messages": [
                {
                    "role": "system",
                    "content": f"""你是抖音千万粉口播博主。写15秒爆款短视频脚本。
要求：
- 开头3秒必须有钩子（反转/惊讶/好奇）
- 口语化，带网感，像跟朋友聊天
- 每句不超过20字，适合做字幕
- 结尾引导互动（点赞/评论/关注）
{template_hint}
只输出脚本，每条一行。""",
                },
                {"role": "user", "content": f"主题: {topic}"},
            ],
            "max_tokens": 400,
        },
        timeout=30,
    )
    return resp.json()["choices"][0]["message"]["content"].strip()


# ═══════════════════════════════════
#  Step 4: 批量出片
# ═══════════════════════════════════

def make_video(title, script_lines, voice="longxiaochun"):
    """调管线出片"""
    print(f"\n🎬 制作视频: {title}")

    props = {
        "title": title,
        "lines": [s.strip() for s in script_lines.split("\n") if s.strip()],
        "bgColor": "#0c0c1d",
        "accentColor": "#ff2d55",
    }

    props_path = os.path.join(ROOT, "remotion-studio", "props.json")
    with open(props_path, "w", encoding="utf-8") as f:
        json.dump(props, f, ensure_ascii=False)

    safe_name = title.replace("/", "").replace(" ", "_")[:20]
    out_path = os.path.join(ROOT, "out", f"{safe_name}.mp4")

    subprocess.run(
        ["npx", "remotion", "render", "CaptionedShort", out_path, f"--props={props_path}"],
        cwd=os.path.join(ROOT, "remotion-studio"),
        capture_output=True,
        timeout=600,
    )

    return out_path if os.path.exists(out_path) else None


# ═══════════════════════════════════
#  主流程
# ═══════════════════════════════════

def main(make_videos=False):
    print("""
╔══════════════════════════════════════╗
║   🔥 热点猎手 · 抖音爆款生产线       ║
╚══════════════════════════════════════╝
""")

    # 1. 抓热点
    hotspots = collect_all_hotspots()
    print(f"\n📊 抓到 {len(hotspots)} 条热点\n")
    for i, h in enumerate(hotspots[:10]):
        hot_str = f"{h['hot']/10000:.0f}万" if isinstance(h.get('hot'), (int, float)) and h['hot'] > 10000 else str(h.get('hot', ''))
        print(f"  {i+1}. [{h['source']}] {h['title']} ({hot_str})")

    # 2. AI 分析选最佳
    analysis = pick_best_topics(hotspots)
    print(f"\n🎯 AI 推荐话题:\n{analysis}\n")

    # 3. 写稿
    top5 = hotspots[:5]
    scripts = []
    for h in top5:
        script = write_viral_script(h["title"])
        scripts.append({"topic": h["title"], "script": script, "source": h["source"]})
        print(f"  ✓ [{h['source']}] {h['title'][:30]}...")
        time.sleep(1)

    # 4. 保存稿件
    os.makedirs(os.path.join(ROOT, "out"), exist_ok=True)
    drafts_path = os.path.join(ROOT, "out", "hotspot_scripts.json")
    with open(drafts_path, "w", encoding="utf-8") as f:
        json.dump(scripts, f, ensure_ascii=False, indent=2)

    print(f"\n📝 稿件已保存: {drafts_path}")
    for i, s in enumerate(scripts, 1):
        print(f"\n── {i}. [{s['source']}] {s['topic']} ──")
        print(s["script"][:200])

    # 5. 出片（可选）
    if make_videos:
        print(f"\n🎬 批量出片中...")
        for s in scripts:
            result = make_video(s["topic"], s["script"])
            if result:
                print(f"  ✅ {result}")
            time.sleep(2)


if __name__ == "__main__":
    make = "--make" in sys.argv
    main(make_videos=make)
