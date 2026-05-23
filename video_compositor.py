"""
视频合成引擎 — FFmpeg Ken Burns + 转场 + 字幕烧录 + 音轨合成
输入: 图片列表 + 音频 + ASS字幕 → 输出: 成品MP4
"""
import subprocess, os, tempfile, shutil, json


class VideoCompositor:
    """FFmpeg视频合成器 — 图片+音频+字幕 → MP4"""

    def __init__(self, width=1080, height=1920, fps=30):
        self.width = width
        self.height = height
        self.fps = fps

    def _run(self, cmd, description="", cwd=None):
        """运行FFmpeg，实时输出进度"""
        print(f"  [FFmpeg] {description}...")
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
        if result.returncode != 0:
            print(f"  [WARN] FFmpeg:\n{result.stderr[-500:]}")
        return result

    def image_to_segment(self, image_path, duration, output_path,
                         zoom_start=1.0, zoom_end=1.08,
                         pan_x_start=0, pan_x_end=-0.02,
                         pan_y_start=0, pan_y_end=-0.01):
        """单张图片 → Ken Burns动画片段（慢速推拉+微移）"""
        total_frames = int(duration * self.fps)
        # zoompan: z='min(max(zoom,pzoom)+0.0015,1.3)' means smooth zoom
        # x/y expressions for smooth pan
        z_expr = f"min(max(zoom,pzoom)+0.0015,1.15)"

        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", image_path,
            "-filter_complex",
            f"[0:v]scale={self.width}:{self.height}:force_original_aspect_ratio=increase,"
            f"crop={self.width}:{self.height},"
            f"zoompan=z='{z_expr}':d={total_frames}:fps={self.fps}:"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={self.width}x{self.height},"
            f"format=yuv420p[v]",
            "-map", "[v]", "-c:v", "libx264", "-preset", "fast",
            "-crf", "18", "-pix_fmt", "yuv420p",
            "-t", str(duration), output_path
        ]
        self._run(cmd, f"Ken Burns {duration}s → {os.path.basename(output_path)}")
        return output_path

    def concat_with_crossfade(self, segment_paths, durations, output_path,
                              crossfade_dur=0.5):
        """多段视频 → 交叉淡入淡出拼接"""
        if len(segment_paths) == 1:
            shutil.copy2(segment_paths[0], output_path)
            return output_path

        # Build complex filter: [0][1]xfade=... -> [x]; [x][2]xfade=... -> [y]; ...
        inputs = []
        filter_parts = []
        for i, (path, dur) in enumerate(zip(segment_paths, durations)):
            inputs.extend(["-i", path])
        inputs = ["-i", segment_paths[0]]

        # xfade approach: chain xfade transitions
        # offset = previous total duration - crossfade_dur
        last_label = "0:v"
        total_offset = 0

        for i in range(1, len(segment_paths)):
            inputs.extend(["-i", segment_paths[i]])
            offset = total_offset + durations[i-1] - crossfade_dur
            next_label = f"x{i-1}" if i == len(segment_paths) - 1 else f"x{i-1}"
            if i < len(segment_paths) - 1:
                filter_parts.append(
                    f"[{last_label}][{i}:v]xfade=transition=fade:duration={crossfade_dur}:"
                    f"offset={offset}[{next_label}]"
                )
                last_label = next_label
            else:
                # Last one - map as final
                filter_parts.append(
                    f"[{last_label}][{i}:v]xfade=transition=fade:duration={crossfade_dur}:"
                    f"offset={offset}[outv]"
                )
            total_offset += durations[i-1] - crossfade_dur

        filter_str = ";".join(filter_parts)

        cmd = [
            "ffmpeg", "-y",
            *inputs,
            "-filter_complex", filter_str,
            "-map", "[outv]", "-c:v", "libx264", "-preset", "fast",
            "-crf", "18", "-pix_fmt", "yuv420p",
            output_path
        ]
        self._run(cmd, f"拼接{len(segment_paths)}段 (xfade)")
        return output_path

    def burn_subtitles(self, video_path, ass_path, output_path):
        """烧录ASS字幕到视频 — 在ass_path所在目录执行以避免路径解析问题"""
        work_dir = os.path.dirname(ass_path) or "."
        ass_fn = os.path.basename(ass_path)
        video_fn = os.path.basename(video_path)

        cmd = [
            "ffmpeg", "-y",
            "-i", video_fn,
            "-vf", f"subtitles='{ass_fn}'",
            "-c:v", "libx264", "-preset", "fast",
            "-crf", "18", "-pix_fmt", "yuv420p",
            output_path
        ]
        self._run(cmd, f"Burning subtitles", cwd=work_dir)
        return output_path

    def add_audio(self, video_path, audio_path, output_path, volume=1.0):
        """添加/替换音轨"""
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-filter_complex", f"[1:a]volume={volume}[a]",
            "-map", "0:v", "-map", "[a]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            output_path
        ]
        self._run(cmd, f"合成音轨 volume={volume}")
        return output_path

    def render(self, images, durations, audio_path, ass_path, output_path,
               crossfade=0.5, volume=1.0):
        """一键渲染: 图片+时长+音频+字幕 → 成品MP4"""
        tmpdir = tempfile.mkdtemp(prefix="vc_")

        try:
            # Step 1: 每张图 → Ken Burns片段
            segments = []
            for i, (img, dur) in enumerate(zip(images, durations)):
                seg_path = os.path.join(tmpdir, f"seg_{i:03d}.mp4")
                self.image_to_segment(img, dur, seg_path)
                segments.append(seg_path)

            # Step 2: 交叉淡入淡出拼接
            concat_path = os.path.join(tmpdir, "concat.mp4")
            self.concat_with_crossfade(segments, durations, concat_path, crossfade)

            # Step 3: 烧录字幕 — copy ASS to tmpdir to avoid path escaping hell
            tmp_ass = os.path.join(tmpdir, "subs.ass")
            shutil.copy2(ass_path, tmp_ass)
            subbed_path = os.path.join(tmpdir, "subbed.mp4")
            self.burn_subtitles(concat_path, tmp_ass, subbed_path)

            # Step 4: 合成音频
            self.add_audio(subbed_path, audio_path, output_path, volume)

            print(f"  [OK] Output: {output_path}")
            return output_path

        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def _has_audio(self, video_path):
        """检查视频是否已有音轨"""
        cmd = ["ffmpeg", "-v", "quiet", "-print_format", "json", "-show_streams", video_path]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                for stream in data.get("streams", []):
                    if stream.get("codec_type") == "audio":
                        return True
        except Exception:
            pass
        return False

    def probe_duration(self, file_path):
        """探测媒体时长（秒）"""
        import re
        cmd = ["ffmpeg", "-i", file_path, "-f", "null", "NUL"]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            # Parse "Duration: HH:MM:SS.ms" from stderr
            m = re.search(r"Duration:\s*(\d+):(\d+):(\d+)\.(\d+)", result.stderr)
            if m:
                h, mi, s, ms = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
                return h * 3600 + mi * 60 + s + ms / 100.0
        except Exception:
            pass
        return 0

    # ── 高级功能 ──

    def image_grid_collage(self, image_paths, output_path, cols=3, rows=2,
                           cell_w=360, cell_h=640, duration=3.0):
        """多图拼贴画 → 单帧视频（用作开场/转场）"""
        # xstack filter for grid layout
        inputs = []
        for p in image_paths:
            inputs.extend(["-loop", "1", "-i", p])

        # Build xstack layout
        layouts = []
        for r in range(rows):
            for c in range(cols):
                idx = r * cols + c
                if idx < len(image_paths):
                    layouts.append(f"{c*cell_w}_{r*cell_h}")

        filter_str = (
            f"{';'.join(f'[{i}:v]scale={cell_w}:{cell_h}[s{i}]' for i in range(len(image_paths)))};"
            f"{' '.join(f'[s{i}]' for i in range(len(image_paths)))}"
            f"xstack=inputs={len(image_paths)}:layout={'|'.join(layouts)}[v]"
        )

        cmd = [
            "ffmpeg", "-y",
            *inputs,
            "-filter_complex", filter_str,
            "-map", "[v]", "-c:v", "libx264", "-preset", "fast",
            "-crf", "18", "-pix_fmt", "yuv420p",
            "-t", str(duration), output_path
        ]
        self._run(cmd, f"拼贴{len(image_paths)}图")
        return output_path


# ═══════════════════════════════════
#  快速函数
# ═══════════════════════════════════

def quick_composite(images, audio_path, ass_path, output_path, durations=None):
    """一行合成: 图片+音频+字幕 → MP4"""
    c = VideoCompositor()
    if durations is None:
        total_dur = c.probe_duration(audio_path)
        dur_per_img = total_dur / len(images)
        durations = [dur_per_img + 0.5] * len(images)
        # Adjust last to match audio exactly
        durations[-1] = total_dur - sum(durations[:-1]) + durations[-1]
    return c.render(images, durations, audio_path, ass_path, output_path)
