"""阿里云 CosyVoice — AI 配音/语音克隆，免费额度可用"""
import requests
import time
import os
import sys

API_KEY = os.environ.get("DASHSCOPE_API_KEY", "YOUR_DASHSCOPE_KEY")
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


def text_to_speech(
    text,
    voice="longxiaochun",  # 龙小春 — 温柔女声
    model="cosyvoice-v1",
    save_dir="out",
    speed=1.0,
    volume=50,
):
    """
    AI 配音 — 文本转语音

    可选音色:
      童声: longxiaochun, longcheng, longyuxiang
      女声: longwanwan, longxiaoxia, loongbella, longyuning
      男声: longbo, longshao, loongbrian, longshu
      方言: longyu (粤语), longshu (四川话), longhua (东北话)
    """
    print(f"🔊 CosyVoice 配音: [{voice}] {text[:30]}...")
    os.makedirs(save_dir, exist_ok=True)

    resp = requests.post(
        "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-to-speech/synthesis",
        json={
            "model": model,
            "input": {"text": text},
            "parameters": {"voice": voice, "format": "mp3", "speed": speed, "volume": volume},
        },
        headers=HEADERS,
    )

    data = resp.json()
    task_id = data.get("output", {}).get("task_id", "")
    print(f"  → 任务ID: {task_id}")
    return task_id if task_id else data


def wait_and_download(task_id, save_dir="out", poll_interval=2, max_wait=120):
    """等待合成完成并下载音频"""
    print(f"⏳ 合成中...")
    os.makedirs(save_dir, exist_ok=True)

    elapsed = 0
    while elapsed < max_wait:
        time.sleep(poll_interval)
        elapsed += poll_interval

        resp = requests.get(
            f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}",
            headers=HEADERS,
        )
        result = resp.json()
        status = result.get("output", {}).get("task_status", "RUNNING")
        print(f"  [{elapsed}s] 状态: {status}")

        if status == "SUCCEEDED":
            audio_url = result["output"]["audio_url"]
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filepath = os.path.join(save_dir, f"cosyvoice_{timestamp}.mp3")

            with open(filepath, "wb") as f:
                f.write(requests.get(audio_url).content)
            print(f"✅ 配音已保存: {filepath}")
            return filepath

        elif status == "FAILED":
            print(f"❌ 合成失败")
            return None

    return None


def generate_voiceover(text, voice="longxiaochun", save_dir="out"):
    """一键生成配音"""
    task_id = text_to_speech(text, voice, save_dir=save_dir)
    if isinstance(task_id, dict):
        print(f"❌ 请求失败: {task_id}")
        return None
    return wait_and_download(task_id, save_dir)


# ─── 批量配音 ───
def batch_voiceover(scripts, voice="longxiaochun", save_dir="out"):
    """批量配音 — scripts: [(文件名前缀, 文案), ...]"""
    results = []
    for name, text in scripts:
        print(f"\n📝 [{name}]")
        path = generate_voiceover(text, voice, save_dir)
        results.append((name, path))
        time.sleep(1)  # 避免限流
    return results


if __name__ == "__main__":
    text = sys.argv[1] if len(sys.argv) > 1 else "大家好，欢迎来到我的频道，今天分享一个超实用的AI工具"
    voice = sys.argv[2] if len(sys.argv) > 2 else "longxiaochun"
    generate_voiceover(text, voice)
