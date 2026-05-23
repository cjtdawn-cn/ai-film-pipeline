# 燧人影视制片 — AI 电影全流程管线

一键 AI 电影制作：**剧本 → 视频 → 配音 → 剪映**，从创意到成片全自动。

## 简介

燧人影视制片是一套全自动 AI 电影制作工具链。你只需要输入一个主题或一句话，系统自动完成：抓取热点选题 → 大模型写剧本 → AI 生成视频画面 → 语音合成配音 → Wav2Lip 口型同步 → 字幕生成 → 剪映自动剪辑输出。整个过程无需人工干预，从创意到成片一步到位。

**核心能力：**
- 多模型支持：智谱 GLM-4、阿里通义万相、CosyVoice v3、CogVideo
- 口型同步：Wav2Lip 高精度音视频口型对齐
- 专业剪辑：剪映 MCP 协议操控，自动转场/特效/字幕
- Hermes 融合：与 Hermes Agent 双向记忆同步、技能共享、MCP 互通
- 全流程自动化：热点发现 → 剧本 → 视频 → 配音 → 剪辑 → 发布

## 快速开始

```bash
# 安装依赖
pip install requests edge-tts

# 设置 API Key（环境变量）
set ZHIPU_API_KEY=你的智谱key
set DASHSCOPE_API_KEY=你的阿里云key

# 一键生成电影
python producer_v3.py "蜘蛛侠大战章鱼博士"

# 自动抓热点生成
python producer_v3.py

# 纯本地模式（不用API）
python producer_v3.py --local
```

## 整体流程

```
热点/选题 → GLM-4写剧本 → wan2.6生成视频 → CosyVoice配音 → Wav2Lip口型同步 → CapCut自动剪辑 → 输出成片
```

## 模块说明

### 核心管线

| 文件 | 功能 |
|------|------|
| `producer_v3.py` | 主制片管线，串联全部模块 |
| `producer_v2.py` | 上一版本管线（参考） |
| `producer.py` | 最早版本（参考） |

### 剧本 & 选题

| 文件 | 功能 |
|------|------|
| `hotspot_hunter.py` | 全网热点抓取，自动选题 |
| `pipeline_capcut.py` | 剧本→剪映直通管线 |
| `pipeline_douyin.py` | 抖音适配管线 |

### AI 视频生成

| 文件 | 功能 |
|------|------|
| `dashscope_wanxiang.py` | 阿里通义万相视频生成 |
| `zhipu_cogvideo.py` | 智谱 CogVideo 视频生成 |
| `colab_wan22_video_gen.ipynb` | Colab wan2.2 视频生成 |

### AI 配音 & 语音

| 文件 | 功能 |
|------|------|
| `voice_actor.py` | 配音模块（多引擎） |
| `dashscope_cosyvoice.py` | 阿里云 CosyVoice v3 语音合成 |
| `sound_designer.py` | 音效设计 |

### 口型同步

| 文件 | 功能 |
|------|------|
| `lipsync_engine.py` | Wav2Lip 口型同步引擎 |

### 字幕 & 剪辑

| 文件 | 功能 |
|------|------|
| `subtitle_engine.py` | 字幕生成引擎 |
| `video_compositor.py` | 视频合成 |
| `animator.py` | 动画特效 |
| `vfx_artist.py` | 视觉特效 |
| `publisher.py` | 一键发布多平台 |

### 剪映 MCP 服务

| 目录 | 功能 |
|------|------|
| `capcut-mcp/` | 剪映 MCP HTTP API 服务（端口 9000），Python 操控剪映草稿 |

```bash
# 启动剪映 MCP 服务
cd capcut-mcp
pip install -r requirements.txt
python main.py
```

### 集成 & 桥接

| 文件 | 功能 |
|------|------|
| `hermes_claude_bridge.py` | Hermes Agent ↔ Claude Code 双向融合桥 |

```bash
# Hermes 融合
python hermes_claude_bridge.py sync-memory   # 记忆同步
python hermes_claude_bridge.py sync-skills   # 技能同步
python hermes_claude_bridge.py serve         # 启动 MCP 服务
python hermes_claude_bridge.py all           # 一键全部
```

### 配套工具

| 目录 | 功能 |
|------|------|
| `AI-Content-Studio/` | AI 内容工作室，多媒体内容生成 |
| `Humanizer-zh/` | 中文人性化处理 |
| `coze_digital_human_guide.md` | 扣子数字人部署指南 |

## 环境要求

- Python 3.10+
- FFmpeg
- 智谱 GLM API Key（剧本生成）
- 阿里云 DashScope API Key（视频 + 语音）
- 剪映专业版（CapCut 剪辑）
- Wav2Lip 环境（可选，口型同步）

## API Key 配置

创建 `.env` 文件或设置环境变量：

```bash
ZHIPU_API_KEY=your_zhipu_key
DASHSCOPE_API_KEY=your_dashscope_key
```

代码中默认值已替换为 `YOUR_ZHIPU_KEY` / `YOUR_DASHSCOPE_KEY` 占位符，使用前请替换为真实 Key。

## 特别说明

- 剪映 MCP 服务需先启动（`capcut-mcp/main.py`），默认监听 `localhost:9000`
- Wav2Lip 需要独立 conda 环境和模型权重文件
- 视频生成依赖云端 API，需稳定网络连接
