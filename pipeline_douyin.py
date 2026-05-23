"""
🎬 一站式抖音视频管线
DeepSeek写稿 → CosyVoice配音 → CogVideo/通义万相生成画面 → Remotion合成

用法:
  python pipeline_douyin.py "今天分享三个省钱妙招"
"""
import subprocess
import sys
import os
import json

# 项目根目录
ROOT = os.path.dirname(os.path.abspath(__file__))

# 从 settings.json 加载 API Key
def load_api_keys():
    settings_path = os.path.join(os.path.dirname(ROOT), "..", "..", "claude-config", ".claude", "settings.json")
    try:
        with open(settings_path) as f:
            cfg = json.load(f)
        return cfg.get("env", {})
    except Exception:
        return {}

ENV = load_api_keys()

# ─── Step 1: DeepSeek 写稿 ───
def write_script(topic):
    """让 DeepSeek 写一段抖音口播文案"""
    print(f"✍️  DeepSeek 写稿: {topic}")
    import requests

    resp = requests.post(
        "https://api.deepseek.com/chat/completions",
        headers={
            "Authorization": f"Bearer {ENV.get('ANTHROPIC_AUTH_TOKEN', '')}",
            "Content-Type": "application/json",
        },
        json={
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "system",
                    "content": "你是抖音爆款文案写手。写15秒口播稿，开头要有钩子，语言口语化有网感。只输出文案，不输出其他。",
                },
                {"role": "user", "content": f"主题: {topic}"},
            ],
            "max_tokens": 300,
        },
    )

    script = resp.json()["choices"][0]["message"]["content"].strip()
    print(f"  → 稿件: {script[:80]}...")

    out_path = os.path.join(ROOT, "out", "script.txt")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(script)
    return script


# ─── Step 2: CosyVoice 配音 ───
def generate_voice(script):
    """AI 配音"""
    print(f"🔊 生成配音...")
    result = subprocess.run(
        [sys.executable, os.path.join(ROOT, "dashscope_cosyvoice.py")],
        input=script,
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    print(result.stdout)
    # 从输出中提取文件路径
    for line in result.stdout.split("\n"):
        if "配音已保存:" in line:
            return line.split(": ")[-1].strip()
    return None


# ─── Step 3: CogVideo 生成画面素材 ───
def generate_footage(prompt):
    """生成 AI 视频素材"""
    print(f"🎬 生成视频素材: {prompt}")
    result = subprocess.run(
        [sys.executable, os.path.join(ROOT, "zhipu_cogvideo.py"), prompt],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    print(result.stdout)
    for line in result.stdout.split("\n"):
        if "视频已保存:" in line:
            return line.split(": ")[-1].strip()
    return None


# ─── Step 4: Remotion 合成 ───
def compose_video(script, voice_path, footage_paths):
    """用 Remotion 合成最终视频"""
    print(f"🎞️  Remotion 合成中...")

    # 写 props
    props = {
        "title": "每日分享",
        "lines": [s.strip() for s in script.replace("\n", "|").split("|") if s.strip()],
        "bgColor": "#1a1a2e",
        "accentColor": "#e94560",
        "voiceover": voice_path,
    }

    props_path = os.path.join(ROOT, "remotion-studio", "props.json")
    with open(props_path, "w", encoding="utf-8") as f:
        json.dump(props, f, ensure_ascii=False)

    result = subprocess.run(
        [
            "npx", "remotion", "render", "CaptionedShort",
            os.path.join(ROOT, "out", "final_video.mp4"),
            f"--props={props_path}",
        ],
        capture_output=True,
        text=True,
        cwd=os.path.join(ROOT, "remotion-studio"),
    )
    print(result.stdout[-500:] if result.stdout else result.stderr[:500])
    return os.path.join(ROOT, "out", "final_video.mp4")


# ─── 主流程 ───
def pipeline(topic, with_footage=False):
    print(f"""
╔══════════════════════════════════╗
║  🎬 抖音视频自动生产线           ║
║  主题: {topic[:20]}
╚══════════════════════════════════╝
""")

    # 1. 写稿
    script = write_script(topic)

    # 2. 配音
    voice = generate_voice(script)

    # 3. AI 画面（可选，免费额度有限制）
    footage = None
    if with_footage:
        footage = generate_footage(topic)

    # 4. Remotion 合成文字动画视频
    video = compose_video(script, voice, [footage] if footage else [])

    print(f"\n✅ 成品视频: {video}")
    print("  → 导入剪映 → 加背景音乐/特效 → 发布抖音")
    return video


if __name__ == "__main__":
    topic = sys.argv[1] if len(sys.argv) > 1 else "一分钟教你用AI省下手机流量费"
    pipeline(topic, with_footage="--footage" in sys.argv)
