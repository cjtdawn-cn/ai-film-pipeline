"""
燧人影视 v3.0 — 一键AI电影
wan2.6视频 + Wav2Lip口型同步 + CosyVoice配音 + CapCut剪辑

用法:
  python producer_v3.py "蜘蛛侠大战章鱼博士"
  python producer_v3.py                    # 自动抓热点
  python producer_v3.py --local            # 纯本地模式(不用API)
"""
import os, sys, json, time, shutil, subprocess, requests, re, hashlib

ROOT = os.path.dirname(os.path.abspath(__file__))
DESKTOP = os.path.expandvars(r"%USERPROFILE%\Desktop")
PYTHON = r"D:\py\python.exe"

# API Keys
ZHIPU_KEY = os.environ.get("ZHIPU_API_KEY", "YOUR_ZHIPU_KEY")
DASHSCOPE_KEY = os.environ.get("DASHSCOPE_API_KEY", "YOUR_DASHSCOPE_KEY")
CAPCUT_LICENSE = "YOUR_CAPCUT_KEY"
CAPCUT_API = "http://localhost:9000"

# Paths
FFMPEG = os.path.join(ROOT, "..", "Kronos-master", ".venv", "Scripts", "ffmpeg.exe")
WAV2LIP_PYTHON = r"D:\miniconda3\envs\wav2lip\python.exe"
WAV2LIP_INFER = os.path.join(ROOT, "Wav2Lip-master", "inference.py")
WAV2LIP_MODEL = os.path.join(ROOT, "models", "wav2lip_gan.pth")
WAV2LIP_DIR = os.path.join(ROOT, "Wav2Lip-master")

sys.path.insert(0, ROOT)


# ═══════════════════════════════════════
#  MODULE 1: Script Writer
# ═══════════════════════════════════════

def write_script_v3(topic):
    """用GLM-4写短视频剧本"""
    print(f"\n[Writer] Topic: {topic}")
    resp = requests.post(
        "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        headers={"Authorization": f"Bearer {ZHIPU_KEY}", "Content-Type": "application/json"},
        json={
            "model": "glm-4-flash",
            "messages": [
                {"role": "system", "content": """你是短视频编剧。写15-25秒竖屏短视频剧本。
输出格式:
[Hook] 钩子文案（前2秒抓注意力）
[Scene 1] 视觉场景描述（英文，适合AI视频生成，30字内，含镜头运动+光线+氛围）
[Line 1] 对应配音文案
[Scene 2] ...
[Line 2] ...
[CTA] 结尾引导互动

共4-6个场景。每句文案不超过20字。"""},
                {"role": "user", "content": f"主题: {topic}"},
            ],
            "max_tokens": 500,
        },
        timeout=30,
    )
    return resp.json()["choices"][0]["message"]["content"].strip()


# ═══════════════════════════════════════
#  MODULE 2: AI Video Generator
# ═══════════════════════════════════════

def generate_video_clips(scenes, output_dir):
    """用wan2.6生成视频片段"""
    print(f"\n[Wan2.6] Generating {len(scenes)} video clips...")
    clips = []

    for i, (prompt, line) in enumerate(scenes):
        print(f"  Scene {i+1}: {prompt[:60]}...")

        resp = requests.post(
            "https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis",
            headers={
                "Authorization": f"Bearer {DASHSCOPE_KEY}",
                "Content-Type": "application/json",
                "X-DashScope-Async": "enable",
            },
            json={
                "model": "wan2.6-t2v",
                "input": {"prompt": prompt},
                "parameters": {
                    "resolution": "1080P",
                    "prompt_extend": True,
                    "duration": 5,
                    "shot_type": "single",
                    "audio": False,
                },
            },
            timeout=30,
        )

        data = resp.json()
        task_id = data.get("output", {}).get("task_id")
        if not task_id:
            print(f"    No task_id: {json.dumps(data, ensure_ascii=False)[:150]}")
            clips.append(None)
            continue

        # Poll
        clip_path = None
        for _ in range(120):
            time.sleep(5)
            r = requests.get(
                f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}",
                headers={"Authorization": f"Bearer {DASHSCOPE_KEY}"},
                timeout=15,
            )
            if r.status_code != 200:
                continue
            result = r.json()
            if result.get("output", {}).get("task_status") == "SUCCEEDED":
                video_url = result["output"].get("video_url", "")
                if video_url:
                    clip_path = os.path.join(output_dir, f"scene_{i+1:02d}.mp4")
                    with open(clip_path, "wb") as f:
                        f.write(requests.get(video_url, timeout=120).content)
                break
            elif result.get("output", {}).get("task_status") == "FAILED":
                break

        clips.append(clip_path)
        if clip_path:
            print(f"    -> scene_{i+1:02d}.mp4 ({os.path.getsize(clip_path)//1024}KB)")

    return clips


# ═══════════════════════════════════════
#  MODULE 3: Voiceover (CosyVoice or edge-tts)
# ═══════════════════════════════════════

def generate_voiceover_v3(lines, output_dir):
    """用CosyVoice v3生成配音"""
    full_text = "。".join(lines)
    print(f"\n[CosyVoice] Generating voiceover ({len(full_text)} chars)...")

    resp = requests.post(
        "https://dashscope.aliyuncs.com/api/v1/services/audio/tts/SpeechSynthesizer",
        headers={
            "Authorization": f"Bearer {DASHSCOPE_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": "cosyvoice-v3-flash",
            "input": {
                "text": full_text,
                "voice": "longanyang",
                "format": "mp3",
                "sample_rate": 24000,
                "rate": 1.1,
                "volume": 50,
            },
        },
        timeout=30,
    )

    data = resp.json()
    # v3 API returns output.audio.url or output.audio_url
    audio_url = (data.get("output", {}).get("audio", {}).get("url", "")
                 or data.get("output", {}).get("audio_url", ""))
    if audio_url:
        output_path = os.path.join(output_dir, "voiceover.mp3")
        with open(output_path, "wb") as f:
            f.write(requests.get(audio_url, timeout=60).content)
        print(f"  CosyVoice -> voiceover.mp3 ({os.path.getsize(output_path)//1024}KB)")
        return output_path

    # Task-based async fallback
    task_id = data.get("output", {}).get("task_id", "")
    if task_id:
        for _ in range(30):
            time.sleep(2)
            r = requests.get(
                f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}",
                headers={"Authorization": f"Bearer {DASHSCOPE_KEY}"},
                timeout=10,
            )
            if r.status_code != 200:
                continue
            result = r.json()
            if result.get("output", {}).get("task_status") == "SUCCEEDED":
                audio_url = (result["output"].get("audio", {}).get("url", "")
                             or result["output"].get("audio_url", ""))
                if audio_url:
                    output_path = os.path.join(output_dir, "voiceover.mp3")
                    with open(output_path, "wb") as f:
                        f.write(requests.get(audio_url, timeout=60).content)
                    print(f"  CosyVoice -> voiceover.mp3 ({os.path.getsize(output_path)//1024}KB)")
                    return output_path
            elif result.get("output", {}).get("task_status") == "FAILED":
                break

    print(f"  CosyVoice failed (code={data.get('code','')}), using Edge-TTS fallback...")
    return _edge_tts_fallback(full_text, output_dir)


def _edge_tts_fallback(text, output_dir):
    """Edge-TTS免费备选，失败则生成静音"""
    import asyncio
    output_path = os.path.join(output_dir, "voiceover.mp3")

    voices = ["zh-CN-YunxiNeural", "zh-CN-XiaoxiaoNeural", "zh-CN-YunjianNeural"]
    for voice in voices:
        try:
            import edge_tts
            async def _speak():
                communicate = edge_tts.Communicate(text, voice, rate="+10%")
                await communicate.save(output_path)
            asyncio.run(_speak())
            if os.path.exists(output_path) and os.path.getsize(output_path) > 100:
                print(f"  Edge-TTS ({voice}) -> voiceover.mp3")
                return output_path
        except Exception as e:
            print(f"  Edge-TTS {voice} failed: {e}")
            continue

    return _silent_audio(output_path, 10)


def _silent_audio(output_path, duration_sec=10):
    """生成静音mp3兜底"""
    import struct, wave
    wav_path = output_path.replace(".mp3", ".wav")
    sample_rate, n_channels = 24000, 1
    n_samples = sample_rate * duration_sec
    with wave.open(wav_path, "w") as w:
        w.setnchannels(n_channels)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(b"\x00\x00" * n_samples)
    ffmpeg = os.path.join(ROOT, "..", "Kronos-master", ".venv", "Scripts", "ffmpeg.exe")
    if not os.path.exists(ffmpeg):
        ffmpeg = "ffmpeg"
    subprocess.run([ffmpeg, "-y", "-i", wav_path, "-codec:a", "libmp3lame", "-b:a", "32k", output_path],
                   capture_output=True)
    print(f"  Silent audio fallback -> voiceover.mp3")
    return output_path


# ═══════════════════════════════════════
#  MODULE 4: Lip-Sync
# ═══════════════════════════════════════

def apply_lipsync(video_path, audio_path, output_dir, scene_idx=0):
    """对视频+音频做口型同步"""
    print(f"  [Wav2Lip] Lip-syncing scene {scene_idx+1}...")

    output_path = os.path.join(output_dir, f"lipsync_{scene_idx+1:02d}.mp4")
    temp_dir = os.path.join(WAV2LIP_DIR, "temp")
    os.makedirs(temp_dir, exist_ok=True)

    # Clean temp
    for f in ["temp.wav", "result.avi"]:
        fp = os.path.join(temp_dir, f)
        if os.path.exists(fp):
            os.remove(fp)

    # Run Wav2Lip from its directory
    cmd = [
        WAV2LIP_PYTHON, WAV2LIP_INFER,
        "--checkpoint_path", WAV2LIP_MODEL,
        "--face", video_path,
        "--audio", audio_path,
        "--outfile", output_path,
        "--pads", "0", "10", "0", "0",
        "--resize_factor", "1",
        "--fps", "25",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True,
                               cwd=WAV2LIP_DIR, timeout=600)
        if result.returncode == 0 and os.path.exists(output_path):
            print(f"    -> lipsync_{scene_idx+1:02d}.mp4")
            return output_path
        else:
            # Lip-sync failed - return original video
            print(f"    Lip-sync failed, using original video")
            if "Face not detected" in result.stderr:
                print(f"    (No face detected - concept art limitation)")
            return video_path
    except subprocess.TimeoutExpired:
        print(f"    Timeout, using original video")
        return video_path


# ═══════════════════════════════════════
#  MODULE 5: CapCut Composer
# ═══════════════════════════════════════

def compose_in_capcut(draft_name, video_clips, audio_path, subtitle_lines, output_dir):
    """在剪映中合成最终视频"""
    print(f"\n[CapCut] Building '{draft_name}' draft...")

    capcut_dir = os.path.expandvars(r"%LOCALAPPDATA%\JianyingPro\User Data\Projects\com.lveditor.draft")

    def api(endpoint, data):
        data["license_key"] = CAPCUT_LICENSE
        try:
            r = requests.post(f"{CAPCUT_API}/{endpoint}", json=data, timeout=30)
            return r.json()
        except Exception as e:
            print(f"    API error: {e}")
            return {"success": False}

    # Create draft
    result = api("create_draft", {"draft_name": draft_name[:20]})
    if not result.get("success"):
        print("  CapCut not available - saving as FFmpeg composition instead")
        return _ffmpeg_fallback(video_clips, audio_path, subtitle_lines, output_dir)

    draft_id = result["output"]["draft_id"]
    print(f"  Draft ID: {draft_id}")

    # Add video clips
    transitions = ["Dissolve", "Fade", "Slide_Left", "Slide_Right"]
    for i, clip in enumerate(video_clips):
        if not clip or not os.path.exists(clip):
            continue
        trans = transitions[i % len(transitions)] if i > 0 else None
        api("add_video", {
            "draft_id": draft_id,
            "video_url": clip,
            "width": 1080, "height": 1920,
            "track_name": f"video_{i}",
            "target_start": i * 5,
            "scale_x": 1.0, "scale_y": 1.0,
            "transform_x": 0, "transform_y": 0,
            "transition": trans,
            "transition_duration": 0.5 if trans else 0,
        })

    # Add audio
    if audio_path and os.path.exists(audio_path):
        api("add_audio", {
            "draft_id": draft_id,
            "audio_url": audio_path,
            "target_start": 0,
            "volume": 1.2,
            "track_name": "audio_main",
        })

    # Add subtitles via add_text
    for i, line in enumerate(subtitle_lines):
        api("add_text", {
            "draft_id": draft_id,
            "draft_folder": capcut_dir,
            "text": line,
            "start": i * 5,
            "end": (i + 1) * 5,
            "font": "文轩体",
            "color": "#FFFFFF",
            "size": 5.5,
            "alpha": 1.0,
            "transform_x": 0.5,
            "transform_y": -0.7,
            "track_name": f"sub_{i}",
            "border_color": "#000000",
            "border_width": 2.0,
            "border_alpha": 1.0,
        })

    # Save to CapCut
    api("save_draft", {
        "draft_id": draft_id,
        "draft_folder": capcut_dir,
    })

    print(f"  [OK] Open CapCut Pro -> Drafts -> '{draft_name}'")
    return draft_id


def _ffmpeg_fallback(video_clips, audio_path, subtitle_lines, output_dir):
    """FFmpeg备选合成"""
    output_path = os.path.join(DESKTOP, "suiren_v3_output.mp4")

    # Concat video clips
    concat_list = os.path.join(output_dir, "concat.txt")
    with open(concat_list, "w") as f:
        for clip in video_clips:
            if clip and os.path.exists(clip):
                f.write(f"file '{clip}'\n")

    if os.path.getsize(concat_list) > 0:
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", concat_list, "-i", audio_path,
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-c:a", "aac", "-b:a", "192k", "-shortest",
            "-pix_fmt", "yuv420p", output_path,
        ]
        subprocess.run(cmd, capture_output=True)
        if os.path.exists(output_path):
            print(f"  [OK] FFmpeg output: {output_path}")
            return output_path

    return None


# ═══════════════════════════════════════
#  MAIN PRODUCER
# ═══════════════════════════════════════

def produce_v3(topic=None, use_lipsync=False, local_mode=False):
    """V3一键制片: 剧本→AI视频→配音→口型同步→剪映合成"""

    print(f"""
+======================================================================+
|  Suiren Pictures v3.0 — One-Click AI Film                            |
|  Wan2.6 + Wav2Lip + CosyVoice + CapCut                               |
+======================================================================+
""")

    # Setup
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(ROOT, "out", f"v3_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)

    # Step 1: Topic
    if not topic:
        from pipeline_capcut import fetch_hotspots
        hotspots = fetch_hotspots()
        topic = hotspots[0]["title"] if hotspots else "今日热点"
    print(f"[Topic] {topic}")

    # Step 2: Script
    script = write_script_v3(topic)

    # Parse script - supports two formats:
    # Format A: [Scene X] prompt + [Line X] text
    # Format B: [Scene X] prompt followed by "quoted line" on next line
    scenes = []
    lines = []
    pending_scene = None
    for line in script.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("[Scene") or line.lower().startswith("[scene"):
            prompt = re.sub(r'\[Scene\s*\d*\]\s*', '', line, flags=re.IGNORECASE).strip()
            pending_scene = prompt
        elif line.startswith("[Line") or line.lower().startswith("[line"):
            text = re.sub(r'\[Line\s*\d*\]\s*', '', line, flags=re.IGNORECASE).strip()
            lines.append(text)
            if pending_scene:
                scenes.append([pending_scene, text])
                pending_scene = None
            elif scenes and not scenes[-1][1]:
                scenes[-1][1] = text
        elif line.startswith('"') and line.endswith('"') and pending_scene:
            text = line.strip('"')
            lines.append(text)
            scenes.append([pending_scene, text])
            pending_scene = None
        elif pending_scene and not line.startswith("["):
            if line.startswith('"') and line.endswith('"'):
                text = line.strip('"')
            else:
                text = line
            lines.append(text)
            scenes.append([pending_scene, text])
            pending_scene = None

    if not scenes:
        print("[Script] Parse failed. Using fallback scenes.")
        scenes = [["A young hero standing on rooftop overlooking city at sunset, epic wide shot, golden light", "英雄俯瞰城市，守护最后的希望"]]
        lines = ["英雄俯瞰城市，守护最后的希望"]

    print(f"  Script: {len(scenes)} scenes, {len(lines)} lines")

    # Save script
    with open(os.path.join(output_dir, "script.txt"), "w", encoding="utf-8") as f:
        f.write(script)

    # Step 3: AI Video Generation
    scene_prompts = [s[0] for s in scenes]
    if not local_mode:
        video_clips = generate_video_clips(scenes, output_dir)
    else:
        print("\n[Local Mode] Skipping wan2.6, using test pattern...")
        video_clips = []
        for i in range(len(scenes)):
            clip = os.path.join(output_dir, f"placeholder_{i}.mp4")
            subprocess.run([
                "ffmpeg", "-y", "-f", "lavfi",
                "-i", f"color=c=0x1a1a2e:s=1080x1920:d=5",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
                "-pix_fmt", "yuv420p", clip
            ], capture_output=True)
            video_clips.append(clip)

    valid_clips = [c for c in video_clips if c]
    print(f"  Generated: {len(valid_clips)}/{len(scenes)} clips")

    # Step 4: Voiceover
    if lines:
        voiceover_path = generate_voiceover_v3(lines, output_dir)
    else:
        voiceover_path = _edge_tts_fallback(topic, output_dir)

    # Step 5: Lip-Sync (optional — slow on CPU)
    if use_lipsync and valid_clips:
        print("\n[Wav2Lip] Applying lip-sync to clips...")
        synced = []
        for i, clip in enumerate(valid_clips):
            synced_clip = apply_lipsync(clip, voiceover_path, output_dir, i)
            synced.append(synced_clip)
        valid_clips = synced

    # Step 6: CapCut Composition
    draft_name = topic[:15] if topic else "AI_Film"
    compose_in_capcut(draft_name, valid_clips, voiceover_path, lines, output_dir)

    # Done
    print(f"""
+======================================================================+
|  PRODUCTION COMPLETE                                                 |
+======================================================================+
|  Project: {output_dir}
|  Clips: {len(valid_clips)} AI-generated scenes
|  Voiceover: voiceover.mp3
|  CapCut Draft: '{draft_name}'
|
|  Next: Open CapCut Pro -> Drafts -> '{draft_name}'
|        Fine-tune effects
|        Add BGM from CapCut library
|        Export 1080p to desktop
+======================================================================+
""")

    os.startfile(output_dir)
    return output_dir


if __name__ == "__main__":
    local = "--local" in sys.argv
    lipsync = "--lipsync" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    topic = args[0] if args else None
    produce_v3(topic=topic, use_lipsync=lipsync, local_mode=local)
