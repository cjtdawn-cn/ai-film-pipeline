"""通义万相 Wan2.6 — 文生视频/图生视频/角色扮演视频，免费额度可用
升级: 15秒+原生音频+多镜头分镜+角色一致性(Reference-to-Video)
"""
import requests
import time
import os
import sys
import json

API_KEY = os.environ.get("DASHSCOPE_API_KEY", "YOUR_DASHSCOPE_KEY")
BASE_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis"
TASK_URL = "https://dashscope.aliyuncs.com/api/v1/tasks"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "X-DashScope-Async": "enable",
}


# ═══════════════════════════════════
#  Wan2.6 核心API
# ═══════════════════════════════════

def text_to_video(prompt, model="wan2.6-t2v", duration=10, resolution="1080P",
                  audio=True, shot_type="multi", prompt_extend=True,
                  negative_prompt="", seed=None):
    """文生视频 — wan2.6支持15秒+多镜头+原生音频"""
    print(f"[Wan2.6] Text-to-Video: {prompt[:50]}...")

    payload = {
        "model": model,
        "input": {"prompt": prompt},
        "parameters": {
            "resolution": resolution,
            "prompt_extend": prompt_extend,
            "duration": duration,
            "shot_type": shot_type,
        },
    }
    if audio:
        payload["parameters"]["audio"] = True
    if negative_prompt:
        payload["input"]["negative_prompt"] = negative_prompt
    if seed is not None:
        payload["parameters"]["seed"] = seed

    resp = requests.post(BASE_URL, json=payload, headers=HEADERS)
    data = resp.json()
    task_id = data.get("output", {}).get("task_id") or data.get("request_id")
    print(f"  -> task_id: {task_id}")
    return task_id if task_id else data


def image_to_video(image_url, prompt="", model="wan2.6-i2v-flash",
                   duration=10, resolution="1080P", audio=True,
                   shot_type="multi", prompt_extend=True, seed=None):
    """图生视频 — 从图片生成视频，支持首帧/尾帧控制"""
    print(f"[Wan2.6] Image-to-Video: {prompt[:50]}...")

    payload = {
        "model": model,
        "input": {"prompt": prompt, "img_url": image_url},
        "parameters": {
            "resolution": resolution,
            "prompt_extend": prompt_extend,
            "duration": duration,
            "shot_type": shot_type,
        },
    }
    if audio:
        payload["parameters"]["audio"] = True
    if seed is not None:
        payload["parameters"]["seed"] = seed

    resp = requests.post(BASE_URL, json=payload, headers=HEADERS)
    data = resp.json()
    task_id = data.get("output", {}).get("task_id") or data.get("request_id")
    print(f"  -> task_id: {task_id}")
    return task_id if task_id else data


def reference_to_video(prompt, reference_urls, model="wan2.6-r2v-flash",
                       duration=10, resolution="1080P", audio=True,
                       shot_type="multi", seed=None):
    """角色扮演视频 — 上传参考图/视频，AI保持角色一致性"""
    print(f"[Wan2.6] Reference-to-Video: {prompt[:50]}...")
    print(f"  References: {len(reference_urls)} source(s)")

    payload = {
        "model": model,
        "input": {
            "prompt": prompt,
            "reference_urls": reference_urls,
        },
        "parameters": {
            "resolution": resolution,
            "duration": duration,
            "shot_type": shot_type,
        },
    }
    if audio:
        payload["parameters"]["audio"] = True
    if seed is not None:
        payload["parameters"]["seed"] = seed

    resp = requests.post(BASE_URL, json=payload, headers=HEADERS)
    data = resp.json()
    task_id = data.get("output", {}).get("task_id") or data.get("request_id")
    print(f"  -> task_id: {task_id}")
    return task_id if task_id else data


# ═══════════════════════════════════
#  轮询 + 下载
# ═══════════════════════════════════

def wait_and_download(task_id, save_dir="out", poll_interval=5, max_wait=900):
    """轮询任务状态，完成后下载视频"""
    print(f"[Wan2.6] Waiting for task: {task_id}")
    os.makedirs(save_dir, exist_ok=True)

    elapsed = 0
    while elapsed < max_wait:
        time.sleep(poll_interval)
        elapsed += poll_interval

        resp = requests.get(f"{TASK_URL}/{task_id}", headers={
            "Authorization": f"Bearer {API_KEY}"
        })
        result = resp.json()
        status = result.get("output", {}).get("task_status", "RUNNING")
        print(f"  [{elapsed}s] {status}")

        if status == "SUCCEEDED":
            video_url = result["output"].get("video_url", "")
            if not video_url:
                print(f"  No video_url. Full response: {json.dumps(result, ensure_ascii=False)[:500]}")
                return None

            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filepath = os.path.join(save_dir, f"wan26_{timestamp}.mp4")

            print(f"  Downloading video...")
            with open(filepath, "wb") as f:
                f.write(requests.get(video_url).content)
            print(f"  Saved: {filepath}")
            return filepath

        elif status in ("FAILED", "ERROR"):
            print(f"  FAILED: {json.dumps(result, ensure_ascii=False)[:500]}")
            return None

    print(f"  Timeout ({max_wait}s)")
    return None


# ═══════════════════════════════════
#  批量生成：剧本 → 多场景视频
# ═══════════════════════════════════

def batch_generate(scenes, save_dir="out", model="wan2.6-t2v", duration=10):
    """批量生成视频 — scenes: [{"prompt": str, "audio_url": str}, ...]"""
    print(f"\n[Wan2.6] Batch generating {len(scenes)} scenes...")
    os.makedirs(save_dir, exist_ok=True)

    results = []
    for i, scene in enumerate(scenes):
        print(f"\n  Scene {i+1}/{len(scenes)}: {scene['prompt'][:40]}...")

        payload = {
            "model": model,
            "input": {"prompt": scene["prompt"]},
            "parameters": {
                "resolution": "1080P",
                "prompt_extend": True,
                "duration": duration,
                "shot_type": "multi",
                "audio": True,
            },
        }
        if scene.get("audio_url"):
            payload["input"]["audio_url"] = scene["audio_url"]

        resp = requests.post(BASE_URL, json=payload, headers=HEADERS)
        data = resp.json()
        task_id = data.get("output", {}).get("task_id")

        if task_id:
            video_path = wait_and_download(task_id, save_dir)
            results.append({"scene": i, "prompt": scene["prompt"], "video": video_path})
        else:
            print(f"    Failed to create task: {json.dumps(data, ensure_ascii=False)[:200]}")
            results.append({"scene": i, "prompt": scene["prompt"], "video": None})

        time.sleep(2)  # Rate limiting

    return results


# ═══════════════════════════════════
#  快速API
# ═══════════════════════════════════

def generate_video(prompt, from_image=None, from_references=None,
                   model="wan2.6-t2v", duration=10, save_dir="out"):
    """一键生成视频"""
    if from_references:
        task_id = reference_to_video(prompt, from_references, model="wan2.6-r2v-flash",
                                     duration=duration)
    elif from_image:
        task_id = image_to_video(from_image, prompt, duration=duration)
    else:
        task_id = text_to_video(prompt, model=model, duration=duration)

    if isinstance(task_id, dict):
        print(f"  Request failed: {task_id}")
        return None
    if not task_id:
        return None
    return wait_and_download(task_id, save_dir)


# ═══════════════════════════════════
#  旧版兼容 (wanx2.0)
# ═══════════════════════════════════

def generate_video_legacy(prompt, from_image=None, save_dir="out"):
    """旧版wanx2.0-turbo (5秒快速生成，兼容)"""
    model = "wanx2.0-i2v-turbo" if from_image else "wanx2.0-t2v-turbo"
    payload = {
        "model": model,
        "input": {"prompt": prompt},
        "parameters": {"duration": 5, "size": "1280x720"},
    }
    if from_image:
        payload["input"]["img_url"] = from_image

    resp = requests.post(BASE_URL, json=payload, headers=HEADERS)
    data = resp.json()
    task_id = data.get("output", {}).get("task_id") or data.get("request_id")

    if not task_id or isinstance(task_id, dict):
        print(f"  Legacy request failed: {data}")
        return None
    return wait_and_download(task_id, save_dir)


if __name__ == "__main__":
    prompt = sys.argv[1] if len(sys.argv) > 1 else "一只橘猫在阳光下打哈欠，温暖治愈，电影质感，4K"
    generate_video(prompt)
