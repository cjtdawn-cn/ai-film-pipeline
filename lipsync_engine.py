"""
口型同步引擎 — Wav2Lip本地 + Colab免费GPU双模式
本地: CPU推理 (2GB显存也能跑, 速度慢)
云端: Google Colab免费T4 GPU (快, 需手动上传)

用法:
  engine = LipSyncEngine()
  engine.sync(face_image, audio_path, output_path)  # 本地CPU
  engine.colab_sync(face_image, audio_path)          # 生成Colab笔记本
"""

import os, sys, subprocess, json, tempfile, shutil, base64, time

ROOT = os.path.dirname(os.path.abspath(__file__))
WAV2LIP_DIR = os.path.join(ROOT, "Wav2Lip-master")  # 解压后目录
MODEL_DIR = os.path.join(ROOT, "models")
CONDA_PYTHON = r"D:\miniconda3\envs\wav2lip\python.exe"


class LipSyncEngine:
    """口型同步 — 本地CPU推理 + Colab云端方案"""

    def __init__(self):
        self.ready = self._check_installation()

    def _check_installation(self):
        """检查Wav2Lip是否已安装"""
        if not os.path.exists(WAV2LIP_DIR):
            print("[LipSync] Wav2Lip source not found. Run: git clone --depth 1 https://github.com/Rudrabha/Wav2Lip.git")
            return False
        if not os.path.exists(CONDA_PYTHON):
            print("[LipSync] conda env 'wav2lip' not found")
            return False
        # Check GAN model
        model_path = os.path.join(MODEL_DIR, "wav2lip_gan.pth")
        if not os.path.exists(model_path) or os.path.getsize(model_path) < 400 * 1024 * 1024:
            print("[LipSync] Model not ready. Run download_models() first.")
            return False
        # Check face detection model
        s3fd_path = os.path.join(WAV2LIP_DIR, "face_detection", "detection", "sfd", "s3fd.pth")
        if not os.path.exists(s3fd_path):
            print("[LipSync] Face detection model not found. Run download_models() first.")
            return False
        return True

    def download_models(self):
        """下载Wav2Lip预训练模型"""
        import requests
        os.makedirs(MODEL_DIR, exist_ok=True)

        # Wav2Lip GAN model (~436MB) — try hf-mirror first (China-friendly), then HF, then original
        model_path = os.path.join(MODEL_DIR, "wav2lip_gan.pth")
        gan_urls = [
            "https://hf-mirror.com/camenduru/Wav2Lip/resolve/main/checkpoints/wav2lip_gan.pth",
            "https://huggingface.co/camenduru/Wav2Lip/resolve/main/checkpoints/wav2lip_gan.pth",
        ]

        if os.path.exists(model_path) and os.path.getsize(model_path) > 400 * 1024 * 1024:
            print(f"[LipSync] GAN model OK: {model_path}")
        else:
            print("[LipSync] Downloading Wav2Lip GAN model (~436MB)...")
            for url in gan_urls:
                try:
                    print(f"  Trying: {url}")
                    r = requests.get(url, stream=True, timeout=30)
                    if r.status_code == 200:
                        total = int(r.headers.get("content-length", 0))
                        downloaded = 0
                        with open(model_path, "wb") as f:
                            for chunk in r.iter_content(chunk_size=8192):
                                f.write(chunk)
                                downloaded += len(chunk)
                                if total:
                                    pct = downloaded * 100 // total
                                    if downloaded % (50 * 8192) == 0:
                                        print(f"  {downloaded // (1024*1024)}/{total // (1024*1024)}MB ({pct}%)")
                        break
                except Exception as e:
                    print(f"  Failed: {e}")
                    continue
            if os.path.exists(model_path) and os.path.getsize(model_path) > 400 * 1024 * 1024:
                print(f"[LipSync] GAN model downloaded: {os.path.getsize(model_path) // (1024*1024)}MB")
            else:
                print("[LipSync] Auto-download failed. Please manually download from:")
                print("  https://hf-mirror.com/camenduru/Wav2Lip/resolve/main/checkpoints/wav2lip_gan.pth")
                print(f"  Save to: {model_path}")

        # Face detection model s3fd (~86MB)
        s3fd_dir = os.path.join(WAV2LIP_DIR, "face_detection", "detection", "sfd")
        s3fd_path = os.path.join(s3fd_dir, "s3fd.pth")
        if not os.path.exists(s3fd_path):
            os.makedirs(s3fd_dir, exist_ok=True)
            s3fd_urls = [
                "https://www.adrianbulat.com/downloads/python-fan/s3fd-619a316812.pth",
                "https://huggingface.co/TonyD2046/sadtalker-01/resolve/main/wav2lip/s3fd.pth",
            ]
            print("[LipSync] Downloading face detection model (~86MB)...")
            for url in s3fd_urls:
                try:
                    r = requests.get(url, timeout=120)
                    if r.status_code == 200:
                        with open(s3fd_path, "wb") as f:
                            f.write(r.content)
                        break
                except Exception as e:
                    print(f"  Failed: {e}")
                    continue
            if os.path.exists(s3fd_path):
                print(f"[LipSync] Face model OK: {os.path.getsize(s3fd_path) // (1024*1024)}MB")
            else:
                print("[LipSync] Face model download failed.")
                print(f"  Save s3fd.pth to: {s3fd_path}")

        return model_path if os.path.exists(model_path) else None

    def sync(self, face_video_or_image, audio_path, output_path,
             static=True, pads=(0, 10, 0, 0), resize_factor=1):
        """
        本地CPU口型同步

        Args:
            face_video_or_image: 人脸视频或图片路径
            audio_path: 音频文件路径
            output_path: 输出视频路径
            static: True=静态图片模式(图片→说话视频)
            pads: 裁剪padding (上,下,左,右)
            resize_factor: 缩放因子(降低可提速但降画质)
        """
        if not self.ready:
            print("[LipSync] Not ready. Using Colab fallback.")
            return self.colab_sync(face_video_or_image, audio_path, output_path)

        print(f"[LipSync] Local CPU inference...")
        print(f"  Face: {face_video_or_image}")
        print(f"  Audio: {audio_path}")

        cmd = [
            CONDA_PYTHON, os.path.join(WAV2LIP_DIR, "inference.py"),
            "--checkpoint_path", os.path.join(MODEL_DIR, "wav2lip_gan.pth"),
            "--face", face_video_or_image,
            "--audio", audio_path,
            "--outfile", output_path,
            "--pads", str(pads[0]), str(pads[1]), str(pads[2]), str(pads[3]),
            "--resize_factor", str(resize_factor),
        ]
        cmd = [c for c in cmd if c]  # Remove empty strings

        print(f"  Running Wav2Lip (CPU, may take 5-15 min for 10s clip)...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        if result.returncode != 0:
            print(f"  Error: {result.stderr[-500:]}")
            return None

        print(f"  [OK] {output_path}")
        return output_path

    def colab_sync(self, face_image, audio_path, output_path=None):
        """生成Colab笔记本 — 免费T4 GPU云端推理"""
        notebook = self._generate_colab_notebook(face_image, audio_path)

        colab_path = os.path.join(ROOT, "out", "lipsync_colab.ipynb")
        os.makedirs(os.path.dirname(colab_path), exist_ok=True)

        with open(colab_path, "w", encoding="utf-8") as f:
            json.dump(notebook, f, indent=2)

        print(f"""
[LipSync] Colab notebook generated: {colab_path}
  Steps:
  1. Open https://colab.research.google.com
  2. Upload this notebook
  3. Upload your face image + audio file
  4. Runtime -> Run all (T4 GPU, free)
  5. Download the lip-synced video
""")
        return colab_path

    def _generate_colab_notebook(self, face_image, audio_path):
        """生成Wav2Lip Colab笔记本JSON"""
        cells = [
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    "# Wav2Lip - Free GPU Lip Sync\n",
                    "Generated by 燧人影视 LipSync Engine\n",
                    "Runtime -> Change runtime type -> T4 GPU"
                ]
            },
            {
                "cell_type": "code",
                "metadata": {},
                "source": [
                    "# Clone Wav2Lip and install dependencies\n",
                    "!git clone https://github.com/Rudrabha/Wav2Lip.git\n",
                    "%cd Wav2Lip\n",
                    "!pip install -q librosa opencv-python face-alignment\n",
                    "!pip install -q gdown\n",
                    "\n",
                    "# Download pretrained model\n",
                    "!gdown --id 1l4Yl6G6CqyZQ5xQ6qV6cJ8W8eJ8W8eJ8 -O wav2lip_gan.pth 2>/dev/null || echo 'Please manually download model'\n",
                    "!wget -q 'https://www.adrianbulat.com/downloads/python-fan/s3fd-619a316e.pth' -O face_detection/detection/sfd/s3fd.pth 2>/dev/null"
                ],
                "execution_count": None,
                "outputs": []
            },
            {
                "cell_type": "code",
                "metadata": {},
                "source": [
                    "# Upload your face image\n",
                    "from google.colab import files\n",
                    "uploaded = files.upload()\n",
                    "face_file = list(uploaded.keys())[0]\n",
                    "print(f'Face: {face_file}')"
                ],
                "execution_count": None,
                "outputs": []
            },
            {
                "cell_type": "code",
                "metadata": {},
                "source": [
                    "# Upload your audio\n",
                    "uploaded = files.upload()\n",
                    "audio_file = list(uploaded.keys())[0]\n",
                    "print(f'Audio: {audio_file}')"
                ],
                "execution_count": None,
                "outputs": []
            },
            {
                "cell_type": "code",
                "metadata": {},
                "source": [
                    "# Run Wav2Lip inference\n",
                    "!python inference.py \\\n",
                    "  --checkpoint_path wav2lip_gan.pth \\\n",
                    "  --face {face_file} \\\n",
                    "  --audio {audio_file} \\\n",
                    "  --outfile /content/lipsync_output.mp4 \\\n",
                    "  --pads 0 10 0 0 \\\n",
                    "  --resize_factor 1\n",
                    "\n",
                    "from google.colab import files\n",
                    "files.download('/content/lipsync_output.mp4')\n",
                    "print('Done! Check your downloads folder.')"
                ],
                "execution_count": None,
                "outputs": []
            }
        ]

        return {
            "nbformat": 4,
            "nbformat_minor": 0,
            "metadata": {
                "colab": {"name": "LipSync_燧人影视.ipynb", "provenance": []},
                "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}
            },
            "cells": cells,
        }


# ═══════════════════════════════════
#  快速API
# ═══════════════════════════════════

def sync_lips(face_image, audio_path, output_path=None, use_colab=False):
    """一行口型同步"""
    engine = LipSyncEngine()
    if output_path is None:
        output_path = os.path.join(ROOT, "out", "lipsync_output.mp4")

    if use_colab or not engine.ready:
        return engine.colab_sync(face_image, audio_path, output_path)
    else:
        return engine.sync(face_image, audio_path, output_path)


if __name__ == "__main__":
    print("LipSync Engine - 口型同步模块")
    engine = LipSyncEngine()
    if engine.ready:
        print("Status: READY (local CPU)")
    else:
        print("Status: Colab mode (no local Wav2Lip)")
        print("To install locally:")
        print("  1. Download Wav2Lip-master.zip from GitHub")
        print(f"  2. Extract to: {WAV2LIP_DIR}")
        print(f"  3. Download model to: {MODEL_DIR}/wav2lip_gan.pth")
