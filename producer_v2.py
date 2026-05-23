"""
燧人影视 v2.0 — 真正的AI电影制片厂
升级: AI视频片段(CogVideo) + CapCut深度集成 + 自动导出

用法:
  python producer_v2.py "蜘蛛侠大战章鱼博士"   # 全自动AI电影
  python producer_v2.py                         # 自动抓热点
  python producer_v2.py --export                # 生成后自动导出MP4
"""

import os, sys, json, time, shutil, glob as glob_mod, requests, subprocess, tempfile, hashlib

ROOT = os.path.dirname(os.path.abspath(__file__))
PYTHON = r"D:\py\python.exe"
DESKTOP = os.path.expandvars(r"%USERPROFILE%\Desktop")
ZHIPU_KEY = os.environ.get("ZHIPU_API_KEY", "YOUR_ZHIPU_KEY")
CAPCUT_API = "http://localhost:9000"
LICENSE_KEY = "YOUR_CAPCUT_KEY"
CAPCUT_DRAFTS = os.path.expandvars(
    r"%LOCALAPPDATA%\JianyingPro\User Data\Projects\com.lveditor.draft"
)

sys.path.insert(0, ROOT)
from pipeline_capcut import write_script, humanize_script, parse_script_sections, fetch_hotspots


# ═══════════════════════════════════════════════════════════
#  MODULE 1: AI Video Generator (Wan2.6 + CogVideo)
# ═══════════════════════════════════════════════════════════

DASHSCOPE_KEY = os.environ.get("DASHSCOPE_API_KEY", "YOUR_DASHSCOPE_KEY")


class AIVideoGenerator:
    """AI视频片段生成器 — Wan2.6主引擎(15s/1080P) + CogVideo备选(6s免费)"""

    def __init__(self):
        self.zhipu_headers = {
            "Authorization": f"Bearer {ZHIPU_KEY}",
            "Content-Type": "application/json",
        }
        self.dashscope_headers = {
            "Authorization": f"Bearer {DASHSCOPE_KEY}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable",
        }

    # ── Wan2.6 (Primary: 15s, 1080P, native audio, multi-shot) ──

    def generate_clips_wan(self, scene_prompts, output_dir, duration=10, resolution="1080P"):
        """Wan2.6批量生成 — 15秒1080P，原生音频，多镜头分镜"""
        clips = []
        for i, prompt in enumerate(scene_prompts):
            print(f"\n  [Wan2.6] Scene {i+1}/{len(scene_prompts)}: {prompt[:60]}...")
            clip_path = self._wan_text_to_video(prompt, output_dir, duration, resolution, scene_idx=i+1)
            if clip_path:
                clips.append(clip_path)
                print(f"    -> {os.path.basename(clip_path)}")
            else:
                print(f"    FAILED for scene {i+1}, trying CogVideo fallback...")
                clip_path = self._cogvideo_t2v(prompt, output_dir, scene_idx=i+1)
                if clip_path:
                    clips.append(clip_path)
        return clips

    def _wan_text_to_video(self, prompt, output_dir, duration=10, resolution="1080P", scene_idx=0):
        """Wan2.6 文生视频"""
        resp = requests.post(
            "https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis",
            headers=self.dashscope_headers,
            json={
                "model": "wan2.6-t2v",
                "input": {"prompt": prompt},
                "parameters": {
                    "resolution": resolution,
                    "prompt_extend": True,
                    "duration": duration,
                    "shot_type": "multi",
                    "audio": True,
                },
            },
            timeout=30,
        )
        if resp.status_code != 200:
            print(f"    Wan2.6 API error: {resp.text[:200]}")
            return None

        data = resp.json()
        task_id = data.get("output", {}).get("task_id")
        if not task_id:
            print(f"    No task_id: {json.dumps(data, ensure_ascii=False)[:200]}")
            return None

        return self._poll_dashscope(task_id, output_dir, scene_idx)

    def _wan_image_to_video(self, image_url, prompt, output_dir, duration=10, scene_idx=0):
        """Wan2.6 图生视频"""
        resp = requests.post(
            "https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis",
            headers=self.dashscope_headers,
            json={
                "model": "wan2.6-i2v-flash",
                "input": {"prompt": prompt, "img_url": image_url},
                "parameters": {
                    "resolution": "1080P",
                    "prompt_extend": True,
                    "duration": duration,
                    "shot_type": "multi",
                    "audio": True,
                },
            },
            timeout=30,
        )
        if resp.status_code != 200:
            print(f"    Wan2.6 i2v error: {resp.text[:200]}")
            return None

        data = resp.json()
        task_id = data.get("output", {}).get("task_id")
        if not task_id:
            return None

        return self._poll_dashscope(task_id, output_dir, scene_idx)

    def _wan_reference_to_video(self, prompt, reference_urls, output_dir, duration=10, scene_idx=0):
        """Wan2.6 角色扮演视频 — 保持角色一致性"""
        print(f"    References: {len(reference_urls)} source(s)")
        resp = requests.post(
            "https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis",
            headers=self.dashscope_headers,
            json={
                "model": "wan2.6-r2v-flash",
                "input": {
                    "prompt": prompt,
                    "reference_urls": reference_urls,
                },
                "parameters": {
                    "resolution": "1080P",
                    "duration": duration,
                    "shot_type": "multi",
                    "audio": True,
                },
            },
            timeout=30,
        )
        if resp.status_code != 200:
            print(f"    Wan2.6 r2v error: {resp.text[:200]}")
            return None

        data = resp.json()
        task_id = data.get("output", {}).get("task_id")
        if not task_id:
            return None

        return self._poll_dashscope(task_id, output_dir, scene_idx)

    def _poll_dashscope(self, task_id, output_dir, scene_idx, max_wait=900):
        """轮询DashScope任务 + 下载视频"""
        for attempt in range(max_wait // 5):
            time.sleep(5)
            resp = requests.get(
                f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}",
                headers={"Authorization": f"Bearer {DASHSCOPE_KEY}"},
                timeout=15,
            )
            if resp.status_code != 200:
                continue
            result = resp.json()
            status = result.get("output", {}).get("task_status", "RUNNING")

            if attempt % 6 == 0:
                print(f"    [{attempt * 5}s] {status}")

            if status == "SUCCEEDED":
                video_url = result["output"].get("video_url", "")
                if not video_url:
                    return None
                clip_path = os.path.join(output_dir, f"scene_{scene_idx:02d}.mp4")
                video_data = requests.get(video_url, timeout=120).content
                with open(clip_path, "wb") as f:
                    f.write(video_data)
                return clip_path
            elif status in ("FAILED", "ERROR"):
                return None

        print(f"    Timeout for task {task_id}")
        return None

    # ── CogVideo (Fallback: 6s, 720x720, free) ──

    def generate_clips(self, scene_prompts, output_dir, model="cogvideox-flash"):
        """CogVideo批量生成 — 6秒720p免费"""
        clips = []
        for i, prompt in enumerate(scene_prompts):
            print(f"\n  [CogVideo] Scene {i+1}: {prompt[:60]}...")
            clip_path = self._cogvideo_t2v(prompt, output_dir, scene_idx=i+1)
            if clip_path:
                clips.append(clip_path)
                print(f"    -> {os.path.basename(clip_path)}")
            else:
                print(f"    FAILED for scene {i+1}")
        return clips

    def _cogvideo_t2v(self, prompt, output_dir, scene_idx=0):
        """CogVideo 文生视频"""
        resp = requests.post(
            "https://open.bigmodel.cn/api/paas/v4/videos/generations",
            headers=self.zhipu_headers,
            json={
                "model": "cogvideox-flash",
                "prompt": f"{prompt}, cinematic, high quality, smooth motion",
                "size": "720x720",
            },
            timeout=30,
        )
        if resp.status_code != 200:
            print(f"    CogVideo API error: {resp.text[:200]}")
            return None

        data = resp.json()
        task_id = data.get("id")
        if not task_id:
            return None

        for attempt in range(60):
            time.sleep(5)
            resp = requests.get(
                f"https://open.bigmodel.cn/api/paas/v4/async-result/{task_id}",
                headers=self.zhipu_headers,
                timeout=15,
            )
            if resp.status_code != 200:
                continue
            result = resp.json()
            status = result.get("task_status", "")

            if status in ("SUCCESS", "DONE"):
                video_url = (result.get("video_result", [{}])[0].get("url")
                             or result.get("video_url"))
                if video_url:
                    clip_path = os.path.join(output_dir, f"scene_{scene_idx:02d}.mp4")
                    video_data = requests.get(video_url, timeout=120).content
                    with open(clip_path, "wb") as f:
                        f.write(video_data)
                    return clip_path
                return None
            elif status in ("FAIL", "ERROR"):
                return None

        print(f"    Timeout waiting for task {task_id}")
        return None


# ═══════════════════════════════════════════════════════════
#  MODULE 2: Scene Extractor
# ═══════════════════════════════════════════════════════════

def extract_scene_prompts(script_text, num_scenes=4):
    """从剧本提取视觉场景描述 — 用于AI视频生成"""
    resp = requests.post(
        "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        headers={
            "Authorization": f"Bearer {ZHIPU_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": "glm-4-flash",
            "messages": [
                {"role": "system", "content": f"""从剧本中提取{num_scenes}个视觉场景，每个用英文描述(适合AI视频生成)，30字以内。
包含: 主体、动作、镜头运动、光线氛围。
每行一个场景，不编号。例如:
"A superhero in red suit swinging through destroyed city, dynamic tracking shot, golden hour light"
"A scientist with mechanical tentacles standing in energy core, low angle, purple electric glow"
"Two figures embracing before massive explosion, slow motion, white hot light" """},
                {"role": "user", "content": script_text[:2000]},
            ],
            "max_tokens": 300,
        },
        timeout=30,
    )
    content = resp.json()["choices"][0]["message"]["content"].strip()
    return [p.strip() for p in content.split("\n") if p.strip() and len(p) > 10]


# ═══════════════════════════════════════════════════════════
#  MODULE 3: Voiceover (Edge-TTS)
# ═══════════════════════════════════════════════════════════

def generate_voiceover(script_text, output_dir, voice="zh-CN-YunxiNeural"):
    """Edge-TTS 旁白生成"""
    import asyncio
    import edge_tts

    # Clean script
    import re
    cleaned = []
    for line in script_text.split("\n"):
        line = line.strip()
        if not line or (line.startswith("[") and line.endswith("]") and len(line) < 15):
            continue
        line = re.sub(r'^\[(Hook|Keep|CTA)\]\s*', '', line, flags=re.IGNORECASE)
        line = re.sub(r'^>\s*\S+[：:]\s*', '', line)
        line = re.sub(r'^#{1,4}\s*', '', line)
        line = re.sub(r'\*\*', '', line)
        line = line.strip('"').strip('"')
        if line and len(line) > 2:
            cleaned.append(line)

    clean_text = "。\n".join(cleaned)
    if len(clean_text) < 10:
        clean_text = "精彩内容，即将呈现。"

    output_path = os.path.join(output_dir, "voiceover.mp3")

    async def _speak():
        communicate = edge_tts.Communicate(clean_text, voice, rate="+15%")
        await communicate.save(output_path)

    asyncio.run(_speak())
    print(f"  [Voice] {output_path}")
    return output_path


# ═══════════════════════════════════════════════════════════
#  MODULE 4: CapCut Rich Draft Builder
# ═══════════════════════════════════════════════════════════

class CapCutDraftBuilder:
    """创建富剪映草稿 — 视频+音频+字幕+转场+特效"""

    def __init__(self):
        self.draft_id = None

    def call_api(self, endpoint, data):
        data["license_key"] = LICENSE_KEY
        try:
            resp = requests.post(
                f"{CAPCUT_API}/{endpoint}",
                json=data,
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            return resp.json()
        except Exception as e:
            print(f"    [CapCut API] {endpoint} error: {e}")
            return {"success": False}

    def create_draft(self, draft_name):
        result = self.call_api("create_draft", {"draft_name": draft_name[:20]})
        if result.get("success"):
            self.draft_id = result["output"]["draft_id"]
            print(f"  [CapCut] Draft: {self.draft_id}")
        return self.draft_id

    def add_video_clip(self, video_path, start, end, transition=None,
                       scale_x=1.0, scale_y=1.0, transform_y=0.0):
        """添加视频片段到时间轴 — 支持转场和缩放"""
        # Serve local file via capcut-mcp (it supports local paths)
        # Actually capcut-mcp downloads from URL. For local files, use file:// protocol
        # or host a simple HTTP server. For now, use the file path directly.
        video_url = video_path  # capcut-mcp can handle local paths

        result = self.call_api("add_video", {
            "draft_id": self.draft_id,
            "video_url": video_url,
            "start": "0",
            "end": "999",  # Full duration
            "target_start": str(start),
            "width": 1080,
            "height": 1920,
            "scale_x": scale_x,
            "scale_y": scale_y,
            "transform_y": transform_y,
            "transition": transition,
            "transition_duration": 0.5 if transition else 0,
        })
        return result.get("success")

    def add_audio(self, audio_path, start=0, volume=1.2):
        """添加音频轨道"""
        result = self.call_api("add_audio", {
            "draft_id": self.draft_id,
            "audio_url": audio_path,
            "start": "0",
            "end": "999",
            "target_start": str(start),
            "volume": volume,
        })
        return result.get("success")

    def add_text(self, text, start, end, font_size=5.5, color="#FFFFFF",
                 transform_y=-0.6, intro_anim="Fade_In", intro_dur=0.3):
        """添加字幕文本"""
        result = self.call_api("add_text", {
            "draft_id": self.draft_id,
            "text": text,
            "start": str(start),
            "end": str(end),
            "font": "文轩体",
            "color": color,
            "size": font_size,
            "transform_y": transform_y,
            "transform_x": 0,
            "border_color": "#000000",
            "border_width": 2.0,
            "border_alpha": 0.5,
            "intro_animation": intro_anim,
            "intro_duration": intro_dur,
        })
        return result.get("success")

    def add_hook_text(self, text, start, end):
        """Hook大字 — 金色居中"""
        return self.add_text(text, start, end, font_size=6.5,
                           color="#FFD700", transform_y=0, intro_anim="Bounce_In", intro_dur=0.4)

    def add_cta_text(self, text, start, end):
        """CTA红字 — 底部强调"""
        return self.add_text(text, start, end, font_size=6.0,
                           color="#FF6B6B", transform_y=-0.8, intro_anim="Scale_In", intro_dur=0.3)

    def add_effect(self, effect_type, start, end):
        """添加视频特效"""
        result = self.call_api("add_effect", {
            "draft_id": self.draft_id,
            "effect_type": effect_type,
            "start": str(start),
            "end": str(end),
        })
        return result.get("success")

    def save(self):
        """保存草稿到剪映目录"""
        result = self.call_api("save_draft", {
            "draft_id": self.draft_id,
            "draft_folder": CAPCUT_DRAFTS,
        })
        print(f"  [CapCut] Save: {'OK' if result.get('success') else 'FAIL'}")
        return result.get("success")

    def copy_to_capcut(self):
        """复制草稿文件夹到剪映专业版"""
        capcut_mcp_dir = os.path.join(ROOT, "capcut-mcp")
        dfd_path = os.path.join(capcut_mcp_dir, self.draft_id)
        target_path = os.path.join(CAPCUT_DRAFTS, self.draft_id)

        if os.path.exists(dfd_path):
            if os.path.exists(target_path):
                shutil.rmtree(target_path)
            shutil.copytree(dfd_path, target_path)
            print(f"  [CapCut] Copied to: {target_path}")
            return True
        print(f"  [CapCut] WARN: draft folder not found: {dfd_path}")
        return False


# ═══════════════════════════════════════════════════════════
#  MODULE 5: Auto Export (via UI Automation)
# ═══════════════════════════════════════════════════════════

def auto_export_draft(draft_name, output_path=None):
    """通过UI自动化从剪映导出视频"""
    try:
        from pyJianYingDraft.jianying_controller import Jianying_controller, Export_resolution, Export_framerate

        print(f"\n  [Export] Launching CapCut and exporting '{draft_name}'...")
        controller = Jianying_controller()
        controller.export_draft(
            draft_name=draft_name,
            output_path=output_path,
            resolution=Export_resolution.RES_1080P,
            framerate=Export_framerate.FR_30,
            timeout=600,
        )
        print(f"  [Export] Complete!")
        return True
    except ImportError as e:
        print(f"  [Export] UI automation not available: {e}")
        return False
    except Exception as e:
        print(f"  [Export] Failed: {e}")
        return False


# ═══════════════════════════════════════════════════════════
#  MAIN PRODUCER V2
# ═══════════════════════════════════════════════════════════

def produce_v2(topic=None, num_scenes=4, auto_export=False):
    """V2制片流程: 写稿→AI视频→配音→剪映深度草稿→自动导出"""

    print("""
+======================================================================+
|  Suiren Pictures v2.0 - AI Film Studio                               |
|  Script -> AI Video Clips -> Voice -> CapCut Rich Draft -> Export    |
+======================================================================+
""")

    # ── Step 1: Topic ──
    if not topic:
        print("[Topic] Fetching hot topics...")
        hotspots = fetch_hotspots()
        topic = hotspots[0]["title"] if hotspots else "今日热点"
    print(f"[Topic] {topic}")

    # ── Step 2: Script ──
    print("\n[Writer] Writing script...")
    raw_script, hook_type = write_script(topic)
    humanized = humanize_script(raw_script)
    sections = parse_script_sections(humanized)
    total_dur = sum(s.get("duration", 2.5) for s in sections)
    print(f"  Script: {len(sections)} lines, ~{total_dur:.0f}s, hook={hook_type}")

    # ── Step 3: Setup output ──
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(ROOT, "out", f"v2_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)

    # ── Step 4: Extract scenes + Generate AI video clips ──
    print("\n[AI Cinematographer] Extracting scenes...")
    scene_prompts = extract_scene_prompts(humanized, num_scenes)

    print(f"[AI Video Gen] Generating {len(scene_prompts)} clips via Wan2.6 (15s/1080P/multi-shot/audio)...")
    gen = AIVideoGenerator()
    # Use wan2.6 as primary (duration based on total script length)
    clip_duration = max(8, min(15, int(total_dur / max(len(scene_prompts), 1))))
    video_clips = gen.generate_clips_wan(scene_prompts, output_dir, duration=clip_duration)

    if not video_clips:
        print("[AI Video Gen] Wan2.6 all failed, trying CogVideo fallback...")
        video_clips = gen.generate_clips(scene_prompts, output_dir)

    if not video_clips:
        print("[AI Video Gen] All clips failed! Creating placeholder visuals...")
        for i in range(num_scenes):
            fallback = os.path.join(output_dir, f"fallback_{i}.mp4")
            subprocess.run([
                "ffmpeg", "-y", "-f", "lavfi",
                "-i", f"color=c=0x101018:s=1080x1920:d=3",
                "-c:v", "libx264", "-preset", "ultrafast",
                "-crf", "30", "-pix_fmt", "yuv420p",
                fallback
            ], capture_output=True)
            video_clips.append(fallback)
        print(f"  Created {len(video_clips)} fallback videos")

    # ── Step 5: Voiceover ──
    print("\n[Voice Actor] Generating TTS...")
    voiceover_path = generate_voiceover(humanized, output_dir)

    # ── Step 6: Build Rich CapCut Draft ──
    print("\n[CapCut Builder] Creating rich draft...")
    draft_name = topic[:15]
    builder = CapCutDraftBuilder()
    draft_id = builder.create_draft(draft_name)
    if not draft_id:
        print("FATAL: Cannot create CapCut draft. Is capcut-mcp server running?")
        return None

    # Calculate timing
    clip_duration = max(total_dur / len(video_clips), 2.0) if video_clips else 5.0
    time_offset = 0
    transitions = ["dissolve", "fade", "slide_left", "slide_right", "zoom_in", "rotate_cw"]

    for i, clip_path in enumerate(video_clips):
        # Video clip with transition
        trans = transitions[i % len(transitions)] if i > 0 else None
        builder.add_video_clip(
            clip_path, time_offset, time_offset + clip_duration,
            transition=trans,
            scale_x=1.5,  # Scale up 720x720 to fill 1080x1920
            scale_y=1.5,
            transform_y=0.0,
        )

        # Add scene effect on each clip
        effects = ["cinematic_01", "glow_edge", "film_grain", "vignette"]
        builder.add_effect(effects[i % len(effects)], time_offset, time_offset + clip_duration)

        time_offset += clip_duration - (0.5 if i > 0 else 0)  # Subtract overlap for transition

    # Add audio
    builder.add_audio(voiceover_path, start=0, volume=1.2)

    # Add subtitles with animations
    time_offset = 0
    rhythm = {"hook": 1.8, "keep": 2.5, "cta": 2.0}
    for i, sec in enumerate(sections):
        duration = rhythm.get(sec["section"], 2.5)
        if sec["section"] == "hook":
            builder.add_hook_text(sec["text"], time_offset, time_offset + duration)
        elif sec["section"] == "cta":
            builder.add_cta_text(sec["text"], time_offset, time_offset + duration)
        else:
            builder.add_text(sec["text"], time_offset, time_offset + duration)
        time_offset += duration

    # Save and copy to CapCut
    builder.save()
    builder.copy_to_capcut()

    # ── Step 7: Publish Plan ──
    from publisher import Publisher
    print("\n[Publisher] Creating release strategy...")
    try:
        p = Publisher()
        publish_plan = p.create_publish_plan(script=humanized, context=topic)
        with open(os.path.join(output_dir, "publish_plan.json"), "w", encoding="utf-8") as f:
            json.dump(publish_plan, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"  [Publisher] Skipped: {e}")

    # ── Step 8: Auto Export (optional) ──
    exported_path = None
    if auto_export:
        exported_path = os.path.join(DESKTOP, f"{draft_name}.mp4")
        auto_export_draft(draft_name, exported_path)

    # ── Done ──
    print(f"""
+======================================================================+
|  PRODUCTION COMPLETE                                                 |
+======================================================================+
|  Draft: {draft_name}  (ID: {draft_id})
|  Project: {output_dir}
|  AI Clips: {len(video_clips)} video clips generated
|  Duration: ~{total_dur:.0f}s
+======================================================================+

  [Next] Open CapCut Pro -> Drafts -> '{draft_name}'
    -> Add BGM from CapCut library
    -> Fine-tune effects
    -> Export 1080p

  Or re-run with: python producer_v2.py --export
    -> Auto-export via UI automation
""")

    return {
        "draft_id": draft_id,
        "output_dir": output_dir,
        "video_clips": video_clips,
        "exported": exported_path,
    }


# ═══════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    auto_export = "--export" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    if args:
        topic = args[0]
    else:
        topic = None

    produce_v2(topic=topic, auto_export=auto_export)
