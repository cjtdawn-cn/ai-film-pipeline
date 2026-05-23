"""
燧人影视 · 制片人总控台
一条指令 → 全公司10个AI Agent自动协同 → 成片放桌面

用法:
  python producer.py "蜘蛛侠大战章鱼博士"          # 新项目
  python producer.py                                # 自动抓热点
  python producer.py --project spiderman            # 用已有项目素材出片
"""

import os, sys, json, time, shutil, tempfile, glob as glob_mod

ROOT = os.path.dirname(os.path.abspath(__file__))
PYTHON = r"D:\py\python.exe"
DESKTOP = os.path.expandvars(r"%USERPROFILE%\Desktop")
ZHIPU_KEY = os.environ.get("ZHIPU_API_KEY", "YOUR_ZHIPU_KEY")

# 导入各模块
sys.path.insert(0, ROOT)
from pipeline_capcut import write_script, humanize_script, parse_script_sections, fetch_hotspots
from subtitle_engine import script_to_ass
from video_compositor import VideoCompositor


# ═══════════════════════════════════
#  Step 4: 美术指导 — 生成概念图
# ═══════════════════════════════════

def generate_images(script_text, topic, num_images=4):
    """用智谱CogView生成关键场景图"""
    import requests

    print(f"\n[Art Director] Generating {num_images} concept images...")

    # 从剧本提取关键场景描述
    scene_prompts = _extract_scene_prompts(script_text, num_images)

    images = []
    for i, prompt in enumerate(scene_prompts):
        print(f"  Scene {i+1}: {prompt[:50]}...")

        resp = requests.post(
            "https://open.bigmodel.cn/api/paas/v4/images/generations",
            headers={
                "Authorization": f"Bearer {ZHIPU_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "cogview-3-flash",
                "prompt": f"{prompt}, cinematic lighting, high contrast, vertical composition, 9:16 aspect ratio, dramatic atmosphere, 8K, ultra detailed, Marvel comic style",
                "size": "768x1344",  # 9:16竖屏
            },
            timeout=60,
        )

        if resp.status_code == 200:
            data = resp.json()
            img_url = data["data"][0]["url"]
            # Download image
            img_resp = requests.get(img_url, timeout=30)
            img_path = os.path.join(ROOT, "out", "temp", f"scene_{i+1:02d}.png")
            os.makedirs(os.path.dirname(img_path), exist_ok=True)
            with open(img_path, "wb") as f:
                f.write(img_resp.content)
            images.append(img_path)
            print(f"    OK: {img_path}")
        else:
            print(f"    FAIL: {resp.text[:200]}")

    return images


def _extract_scene_prompts(script_text, num_images):
    """从剧本提取关键场景的视觉描述"""
    import requests

    resp = requests.post(
        "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        headers={
            "Authorization": f"Bearer {ZHIPU_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": "glm-4-flash",
            "messages": [
                {"role": "system", "content": f"""从以下剧本提取{num_images}个关键场景的视觉描述，每段30字以内。
只输出场景描述，每行一个。用英文，适合AI图片生成。
描述要包含: 主体、动作、光线、氛围。
例如: "A young man in damaged red suit crouching on steel beam, city burning behind, dramatic sunset lighting" """},
                {"role": "user", "content": script_text},
            ],
            "max_tokens": 300,
        },
        timeout=30,
    )
    content = resp.json()["choices"][0]["message"]["content"].strip()
    prompts = [p.strip() for p in content.split("\n") if p.strip()]
    return prompts[:num_images]


# ═══════════════════════════════════
#  Step 3: 配音师 — TTS语音
# ═══════════════════════════════════

def generate_voiceover(script_text, output_dir, voice=None):
    """用edge-tts生成旁白/解说音轨"""
    import asyncio
    import edge_tts

    print(f"\n[Voice Actor] Generating TTS voiceover...")

    clean_text = _clean_script_for_tts(script_text)
    if not clean_text.strip():
        clean_text = "这是一个短视频。"

    if voice is None:
        voice = "zh-CN-YunxiNeural"  # 云希=男声 温暖有力

    output_path = os.path.join(output_dir, "voiceover.mp3")

    async def _speak():
        communicate = edge_tts.Communicate(clean_text, voice, rate="+15%")
        await communicate.save(output_path)

    # 直接使用asyncio.run — producer.py作为独立脚本运行，不会有已运行的事件循环
    asyncio.run(_speak())

    print(f"  OK: {output_path}")
    return output_path


def _clean_script_for_tts(script_text):
    """清洗脚本，移除标记和角色名，保留纯叙述文本"""
    import re
    # 移除标记行如 [Hook] [Keep] [CTA] ###
    cleaned = []
    for line in script_text.split("\n"):
        line = line.strip()
        if not line:
            continue
        # 跳过纯标记行
        if line.startswith("[") and line.endswith("]") and len(line) < 15:
            continue
        # 移除行首标记
        line = re.sub(r'^\[(Hook|Keep|CTA|HOOK|KEEP|cta)\]\s*', '', line)
        # 移除角色标记如 > 蜘蛛侠：
        line = re.sub(r'^>\s*\S+[：:]\s*', '', line)
        # 移除Markdown标记
        line = re.sub(r'^#{1,4}\s*', '', line)
        line = re.sub(r'\*\*', '', line)
        if line and len(line) > 2:
            cleaned.append(line)

    return "。\n".join(cleaned)


# ═══════════════════════════════════
#  Step 5: 动画字幕师
# ═══════════════════════════════════

def generate_subtitles(sections, output_dir):
    """生成ASS动画字幕"""
    print(f"\n[Subtitle Animator] Generating karaoke ASS subtitles...")
    ass_path = os.path.join(output_dir, "subtitles.ass")
    script_to_ass(sections, ass_path)
    return ass_path


# ═══════════════════════════════════
#  Step 6: 剪辑师 — FFmpeg合成
# ═══════════════════════════════════

def composite_video(images, audio_path, ass_path, output_path):
    """视频合成: 图片+音频+字幕 → MP4"""
    print(f"\n[Editor] Compositing final video with FFmpeg...")

    compositor = VideoCompositor()

    # 探测音频时长
    total_dur = compositor.probe_duration(audio_path)
    if total_dur == 0:
        total_dur = 20
    print(f"  Audio duration: {total_dur:.1f}s")

    # 均匀分配图片时长
    crossfade = 0.5
    num_images = len(images)
    per_image = (total_dur + crossfade * (num_images - 1)) / num_images
    durations = [per_image] * num_images

    # 调整最后一张填满总时长
    total_with_crossfade = sum(durations) - crossfade * (num_images - 1)
    durations[-1] += total_dur - total_with_crossfade

    print(f"  {num_images} images, {per_image:.1f}s each")

    compositor.render(
        images, durations, audio_path, ass_path, output_path,
        crossfade=crossfade, volume=1.2
    )
    return output_path


# ═══════════════════════════════════
#  蜘蛛侠项目专用: 利用已有素材
# ═══════════════════════════════════

def produce_spiderman():
    """用蜘蛛侠已有素材合成成片"""
    print("""
╔══════════════════════════════════════════╗
║   Spider-Man vs Doc Ock: Final Render   ║
║   Earth's Last Defense                  ║
╚══════════════════════════════════════════╝
""")

    project_dir = os.path.join(ROOT, "out", "spiderman")
    output_dir = os.path.join(ROOT, "out", "spiderman")
    os.makedirs(output_dir, exist_ok=True)

    # 1. 读取剧本
    script_path = os.path.join(project_dir, "script_full.md")
    with open(script_path, "r", encoding="utf-8") as f:
        script_text = f.read()

    # 2. 找到已有图片 (jpg/png都找)
    images = []
    for ext in ["*.jpg", "*.jpeg", "*.png"]:
        images.extend(sorted(glob_mod.glob(os.path.join(project_dir, ext))))
    images = sorted(set(images))

    if not images:
        print("[Art] No existing images, generating with CogView...")
        images = generate_images(script_text, "Spider-Man vs Doc Ock", 6)
    else:
        print(f"[Art] Found {len(images)} existing concept images")

    # 3. 检查是否有已有音频
    audio_dir = os.path.join(project_dir, "audio")
    existing_audio = []
    if os.path.exists(audio_dir):
        existing_audio = sorted(glob_mod.glob(os.path.join(audio_dir, "*.mp3")))

    # 4. 生成旁白 — 先从剧本提取浓缩故事叙述
    print("\n[Writer] Condensing script for narration...")
    narration_script = _condense_spiderman_for_narration(script_text)
    if not narration_script.strip():
        narration_script = _clean_script_for_tts(script_text)

    print("\n[Voice Actor] Generating story narration...")
    voiceover_path = generate_voiceover(narration_script, output_dir, voice="zh-CN-YunxiNeural")

    # 探测真实时长
    compositor_temp = VideoCompositor()
    real_duration = compositor_temp.probe_duration(voiceover_path)
    print(f"  Narration duration: {real_duration:.1f}s")

    # 5. 生成ASS字幕 — 用浓缩旁白的时间轴
    sections = _parse_narration_to_sections(narration_script, real_duration)
    ass_path = os.path.join(output_dir, "subtitles.ass")
    script_to_ass(sections, ass_path)

    # 6. 合成成片
    output_mp4 = os.path.join(DESKTOP, "蜘蛛侠大战章鱼博士_地球最后防线.mp4")
    composite_video(images, voiceover_path, ass_path, output_mp4)

    return output_mp4


def _condense_spiderman_for_narration(script_text):
    """将完整剧本浓缩为2-3分钟的叙事旁白"""
    import requests

    # 只取故事大纲+关键场景对话给AI浓缩
    # 取前3000字（去掉视觉规范等元数据）
    lines = script_text.split("\n")
    story_lines = []
    for line in lines:
        line = line.strip()
        if line.startswith("#") or line.startswith(">") or line.startswith("###"):
            story_lines.append(line)
        elif line and not line.startswith("-") and not line.startswith("```"):
            story_lines.append(line)

    story_text = "\n".join(story_lines[:80])  # 前80行

    resp = requests.post(
        "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        headers={
            "Authorization": f"Bearer {ZHIPU_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": "glm-4-flash",
            "messages": [
                {"role": "system", "content": """你是有声书旁白编剧。将蜘蛛侠动画短片剧本浓缩为一段2-3分钟的故事旁白。
要求:
- 用第三人称叙述
- 包含关键剧情转折点（发现真相→低谷→逆袭→牺牲→重生）
- 每句不超过25字，共15-20句
- 每句一行，口语化，适合朗读
- 不输出标记，只输出旁白文本"""},
                {"role": "user", "content": story_text},
            ],
            "max_tokens": 500,
        },
        timeout=30,
    )
    content = resp.json()["choices"][0]["message"]["content"].strip()
    print(f"  Condensed narration: {len(content)} chars")
    return content


def _parse_narration_to_sections(narration_text, total_duration):
    """将浓缩旁白文本解析为字幕时间轴"""
    lines = []
    for line in narration_text.split("\n"):
        line = line.strip()
        if not line:
            continue
        # 跳过可能的标记
        if line.startswith("#") or line.startswith("```"):
            continue
        # 清理引号和标记
        line = line.strip('"').strip('"').strip()
        if len(line) > 2:
            lines.append(line)

    if not lines:
        return [{"text": "蜘蛛侠大战章鱼博士", "section": "hook", "duration": 3}]

    # 按句数均匀分配时长
    per_line = total_duration / len(lines) if total_duration > 0 else 3
    sections = []
    for i, line in enumerate(lines):
        section = "keep"
        if i == 0:
            section = "hook"
        elif i >= len(lines) - 2:
            section = "cta"
        sections.append({
            "text": line,
            "section": section,
            "duration": min(per_line, 4.5),
        })
    return sections


# ═══════════════════════════════════
#  主入口: 全流程自动制片
# ═══════════════════════════════════

def produce(topic=None, num_images=4):
    """一条指令出片: 写稿→配音→美术→字幕→剪辑→成片"""

    print(f"""
+------------------------------------------------------+
|  Suiren Pictures · Fully Automated Production        |
|  Script -> Art -> Voice -> Subs -> Edit -> Publish   |
+------------------------------------------------------+
""")

    # ── Step 1 ──
    if not topic:
        print("[Topic] Fetching hot topics...")
        hotspots = fetch_hotspots()
        if hotspots:
            topic = hotspots[0]["title"]
        else:
            topic = "今日热点新闻"
    print(f"[Topic] {topic}")

    # ── Step 2: 编剧 ──
    print(f"\n[Writer] Writing script...")
    raw_script, hook_type = write_script(topic)
    print(f"  Hook: {hook_type}")

    # ── Step 3: 去AI痕迹 ──
    print(f"\n[Editor] Humanizing...")
    humanized = humanize_script(raw_script)

    # ── Step 4: 解析为时间轴 ──
    sections = parse_script_sections(humanized)
    total_duration = sum(
        s.get("duration", 1.8 if s["section"] == "hook" else (2.0 if s["section"] == "cta" else 2.5))
        for s in sections
    )
    print(f"  Duration: {total_duration:.0f}s | {len(sections)} lines")

    # 创建输出目录
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(ROOT, "out", f"production_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)

    # 保存文案
    script_file = os.path.join(output_dir, "script.txt")
    with open(script_file, "w", encoding="utf-8") as f:
        f.write(f"主题: {topic}\n钩子: {hook_type}\n\n{humanized}")

    # ── Step 5: 美术 — 生成概念图 ──
    images = generate_images(humanized, topic, num_images)

    if not images:
        print("[Art] Image gen failed, using black background...")
        from PIL import Image
        black_img = os.path.join(output_dir, "black_bg.png")
        Image.new("RGB", (1080, 1920), (20, 20, 30)).save(black_img)
        images = [black_img]

    # ── Step 6: 配音 — TTS ──
    voiceover_path = generate_voiceover(humanized, output_dir)

    # ── Step 7: 字幕 — ASS动画 ──
    ass_path = generate_subtitles(sections, output_dir)

    # ── Step 8: 剪辑 — FFmpeg合成 ──
    safe_topic = topic.replace(" ", "_").replace("/", "_")[:30]
    output_mp4 = os.path.join(DESKTOP, f"{safe_topic}.mp4")
    composite_video(images, voiceover_path, ass_path, output_mp4)

    # ── Step 9: 发行 — 发布计划 ──
    from publisher import Publisher
    print(f"\n[Publisher] Creating release strategy...")
    publisher = Publisher()
    publish_plan = publisher.create_publish_plan(
        script=humanized,
        context=topic,
    )
    publish_path = os.path.join(output_dir, "publish_plan.json")
    with open(publish_path, "w", encoding="utf-8") as f:
        json.dump(publish_plan, f, ensure_ascii=False, indent=2)

    # ── Step 10: 剪映草稿 ──
    print(f"\n[CapCut] Generating draft...")
    try:
        from pipeline_capcut import create_capcut_draft
        create_capcut_draft(humanized, topic, hook_type)
    except Exception as e:
        print(f"  CapCut draft skipped: {e}")

    # ── 收尾 ──
    print(f"""
+======================================================================+
|  DELIVERY COMPLETE                                                   |
+======================================================================+
|  Video: {output_mp4}
|  Project: {output_dir}
|  Duration: {total_duration:.0f}s
|  Hook: {hook_type}
|  Agents: Writer + Art + Voice + Subs + Edit + Publisher = 6 agents
+======================================================================+
""")

    # 打开桌面文件夹
    os.startfile(DESKTOP)
    return output_mp4


# ═══════════════════════════════════
#  CLI
# ═══════════════════════════════════

if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "--project" and len(sys.argv) > 2:
            project_name = sys.argv[2]
            if project_name == "spiderman":
                produce_spiderman()
            else:
                print(f"未知项目: {project_name}")
        elif arg == "--help" or arg == "-h":
            print("""
燧人影视 · 制片人总控台
用法:
  python producer.py                      # 自动抓热点出片
  python producer.py "你的主题"            # 指定主题出片
  python producer.py --project spiderman  # 用已有素材合成
            """)
        else:
            produce(arg)
    else:
        produce()
