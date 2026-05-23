"""智谱 CogVideo — 文生视频/图生视频，免费额度可用"""
import requests
import time
import os
import sys

API_KEY = os.environ.get("ZHIPU_API_KEY", "YOUR_ZHIPU_KEY")
BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


def text_to_video(prompt, model="cogvideox-flash", save_dir="out"):
    """文生视频 — cogvideox-flash 免费，cogvideox 付费"""
    print(f"🎬 文生视频: {prompt}")
    os.makedirs(save_dir, exist_ok=True)

    resp = requests.post(
        f"{BASE_URL}/videos/generations",
        json={"model": model, "prompt": prompt, "size": "720x720"},
        headers=HEADERS,
    )
    data = resp.json()
    print(f"  → 任务ID: {data.get('id', data)}")
    return data.get("id")


def image_to_video(image_url_or_path, prompt="", model="cogvideox-flash", save_dir="out"):
    """图生视频 — 传图片URL或本地路径"""
    print(f"🎬 图生视频: {prompt or '(无提示词)'}")
    os.makedirs(save_dir, exist_ok=True)

    payload = {"model": model, "image_url": image_url_or_path, "size": "720x720"}
    if prompt:
        payload["prompt"] = prompt

    resp = requests.post(f"{BASE_URL}/videos/generations", json=payload, headers=HEADERS)
    data = resp.json()
    print(f"  → 任务ID: {data.get('id', data)}")
    return data.get("id")


def wait_and_download(task_id, save_dir="out", poll_interval=5, max_wait=600):
    """轮询任务状态，完成后下载视频"""
    print(f"⏳ 等待生成... (任务ID: {task_id})")
    os.makedirs(save_dir, exist_ok=True)

    elapsed = 0
    while elapsed < max_wait:
        time.sleep(poll_interval)
        elapsed += poll_interval

        resp = requests.get(f"{BASE_URL}/async-result/{task_id}", headers=HEADERS)
        result = resp.json()
        status = result.get("task_status", result.get("status", "unknown"))
        print(f"  [{elapsed}s] 状态: {status}")

        if status in ("SUCCESS", "success", "DONE"):
            video_url = result.get("video_result", [{}])[0].get("url", result.get("video_url"))
            if not video_url:
                print(f"  ⚠️ 无法获取视频URL，完整响应: {result}")
                return None

            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filepath = os.path.join(save_dir, f"cogvideo_{timestamp}.mp4")

            with open(filepath, "wb") as f:
                f.write(requests.get(video_url).content)
            print(f"✅ 视频已保存: {filepath}")
            return filepath

        elif status in ("FAIL", "fail", "ERROR"):
            print(f"❌ 生成失败: {result}")
            return None

    print(f"❌ 超时 ({max_wait}s)")
    return None


# ─── 一键生成 ───
def generate_video(prompt, from_image=None, model="cogvideox-flash", save_dir="out"):
    task_id = (
        image_to_video(from_image, prompt, model, save_dir)
        if from_image
        else text_to_video(prompt, model, save_dir)
    )
    if not task_id:
        return None
    return wait_and_download(task_id, save_dir)


if __name__ == "__main__":
    prompt = sys.argv[1] if len(sys.argv) > 1 else "一只橘猫在阳光下打哈欠，温暖治愈"
    generate_video(prompt)
