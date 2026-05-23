"""
ASS动画字幕引擎 — 卡拉OK逐字高亮 + 分段色彩 + 入场动画
输入: 字幕行列表(文本+时间) → 输出: .ass字幕文件
"""
import os


class ASSSubtitleEngine:
    """ASS字幕生成器，支持卡拉OK特效和分段色彩"""

    # 样式预设
    PRESETS = {
        "douyin": {
            "playResX": 1080,
            "playResY": 1920,
            "font": "思源黑体 Heavy",
            "font_size_hook": 72,
            "font_size_keep": 52,
            "font_size_cta": 56,
            "color_hook": "&H00D7FF&",       # 金色 BGR → 实际上是 cyan? No, let me recalculate
            # In ASS, colors are BBGGRR (reversed)
            # Gold = #FFD700 → &H00D7FF&
            "color_keep": "&HFFFFFF&",       # 白色
            "color_cta": "&H6B6BFF&",        # 红色 #FF6B6B → &H6B6BFF&
            "color_highlight": "&H00D7FF&",  # 高亮色=金色
            "border_color": "&H000000&",
            "shadow_color": "&H80000000&",
            "margin_l": 60,
            "margin_r": 60,
            "margin_v": 40,
        }
    }

    def __init__(self, preset="douyin", width=1080, height=1920):
        self.preset = self.PRESETS[preset]
        self.width = width
        self.height = height
        self.events = []
        self.styles = []
        self._event_id = 0

    def _time_ass(self, seconds):
        """秒 → ASS时间格式 H:MM:SS.cc"""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        cs = int((seconds - int(seconds)) * 100)
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    def _distribute_karaoke(self, text, duration_s):
        """将一句文本的时间均匀分配给每个字符，生成卡拉OK时序"""
        chars = list(text.replace(" ", ""))
        if not chars:
            return [], []

        total_cs = int(duration_s * 100)  # 总时间(百分秒)
        per_char = max(1, total_cs // len(chars))

        # 生成 {\kXX} 序列（XX = 百分秒）
        timing = []
        remaining = total_cs
        for i, ch in enumerate(chars):
            if i == len(chars) - 1:
                k_time = remaining  # 最后一个字吃掉剩余全部时间
            else:
                k_time = min(per_char, remaining - (len(chars) - i - 1))
            timing.append(k_time)
            remaining -= k_time

        return chars, timing

    def add_line(self, text, start_time, end_time, section="keep",
                 position="bottom", animation="karaoke"):
        """添加一条字幕行"""
        duration = end_time - start_time
        chars, timing = self._distribute_karaoke(text, duration)

        # 构建卡拉OK文本: {\kXX}字{\kXX}字...
        if animation == "karaoke" and chars:
            parts = []
            for ch, t in zip(chars, timing):
                parts.append(f"{{\\k{t}}}{ch}")
            karaoke_text = "".join(parts)
        else:
            karaoke_text = text

        # 分段样式
        if section == "hook":
            font_size = self.preset["font_size_hook"]
            color = self.preset["color_hook"]
            # Hook居中对齐，更大更醒目
            align = 2  # 底部居中 (ASS: 1左下,2中下,3右下, 4左中,5中中,6右中...)
            # Actually for vertical video bottom center: an=2 (bottom center)
            pos_y = 120  # 距离底部120px (给CTA留空间)
            anim_in = "{\\fade(300,0,300,0)}"  # 淡入300ms

        elif section == "cta":
            font_size = self.preset["font_size_cta"]
            color = self.preset["color_cta"]
            align = 2
            pos_y = 80  # CTA在底部
            anim_in = "{\\fade(200,0,200,0)}"

        else:  # keep
            font_size = self.preset["font_size_keep"]
            color = self.preset["color_keep"]
            align = 2
            pos_y = 100
            anim_in = "{\\fade(200,0,200,0)}"

        # ASS alignment: 1左下 2中下 3右下 5居中 8中上
        # For bottom-center safe area: an=2
        # Use margin_v for vertical positioning
        margin_v = pos_y

        # 构建ASS Dialogue行
        # Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
        style = "Default"

        # ASS Text with positioning override
        ass_text = (
            f"{anim_in}"
            f"{{\\an{ align }}}"
            f"{{\\fs{ font_size }}}"
            f"{{\\c{ color }}}"
            f"{{\\3c{ self.preset['border_color'] }}}"
            f"{{\\bord3}}"
            f"{{\\shad0}}"
            f"{{\\4c{ self.preset['shadow_color'] }}}"
            f"{{\\4a&H80&}}"
            f"{karaoke_text}"
        )

        self.events.append({
            "Layer": 0,
            "Start": self._time_ass(start_time),
            "End": self._time_ass(end_time),
            "Style": style,
            "Name": "",
            "MarginL": self.preset["margin_l"],
            "MarginR": self.preset["margin_r"],
            "MarginV": margin_v,
            "Effect": "karaoke",
            "Text": ass_text,
        })
        self._event_id += 1

    def add_title_card(self, text, start_time, end_time):
        """居中大字标题卡 — 用于片头/转折点"""
        ass_text = (
            f"{{\\fade(400,0,400,0)}}"
            f"{{\\an5}}"  # 居中
            f"{{\\fs80}}"
            f"{{\\c&H00D7FF&}}"
            f"{{\\bord4}}"
            f"{{\\3c&H000000&}}"
            f"{{\\b1}}"
            f"{text}"
        )
        self.events.append({
            "Layer": 1,
            "Start": self._time_ass(start_time),
            "End": self._time_ass(end_time),
            "Style": "Default",
            "Name": "Title",
            "MarginL": 0, "MarginR": 0, "MarginV": 0,
            "Effect": "",
            "Text": ass_text,
        })

    def generate(self, output_path, audio_duration=0):
        """生成.ass字幕文件"""
        # 构建ASS文件内容
        header = f"""[Script Info]
; 燧人影视 — AI动画字幕引擎
Title: AI Generated Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: None
PlayResX: {self.width}
PlayResY: {self.height}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{self.preset['font']},52,&HFFFFFF&,&H000000&,&H000000&,&H80000000&,1,0,0,0,100,100,0,0,1,3,1,2,{self.preset['margin_l']},{self.preset['margin_r']},{self.preset['margin_v']},1
Style: Hook,{self.preset['font']},{self.preset['font_size_hook']},{self.preset['color_hook']},&H000000&,&H000000&,&H80000000&,1,0,0,0,100,100,0,0,1,3,1,2,60,60,120,1
Style: CTA,{self.preset['font']},{self.preset['font_size_cta']},{self.preset['color_cta']},&H000000&,&H000000&,&H80000000&,1,0,0,0,100,100,0,0,1,3,1,2,60,60,80,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

        lines = [header.rstrip()]
        for evt in sorted(self.events, key=lambda e: e["Start"]):
            line = (
                f"Dialogue: {evt['Layer']},"
                f"{evt['Start']},{evt['End']},"
                f"{evt['Style']},{evt['Name']},"
                f"{evt['MarginL']},{evt['MarginR']},{evt['MarginV']},"
                f"{evt['Effect']},{evt['Text']}"
            )
            lines.append(line)

        content = "\n".join(lines)

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"  [ASS] Subtitles: {output_path} ({len(self.events)} events)")
        return output_path


# ═══════════════════════════════════
#  剧本 → ASS字幕 快捷转换
# ═══════════════════════════════════

def script_to_ass(sections, output_path, preset="douyin"):
    """
    将pipeline_capcut.parse_script_sections()的输出直接转为ASS字幕
    sections: [{"text": "...", "section": "hook/keep/cta", "duration": 2.5}, ...]
    """
    engine = ASSSubtitleEngine(preset=preset)
    time_offset = 0

    # 节奏参数
    rhythm = {"hook": 1.8, "keep": 2.5, "cta": 2.0}

    for i, sec in enumerate(sections):
        duration = sec.get("duration", rhythm.get(sec["section"], 2.5))
        # Hook后加0.3秒停顿
        if sec["section"] == "hook":
            gap = 0.3
        elif sec["section"] == "cta" and i == len(sections) - 1:
            gap = 0.5
        else:
            gap = 0

        start = time_offset
        end = start + duration

        # Hook用标题卡+常规字幕双显
        if sec["section"] == "hook":
            engine.add_title_card(sec["text"], start, end)

        engine.add_line(
            sec["text"], start, end,
            section=sec["section"],
            position="bottom",
            animation="karaoke"
        )

        time_offset = end + gap

    engine.generate(output_path)
    return output_path
