# 🎭 Coze 蝉镜数字人口播 — 零成本日更方案

## 一、开通账号

1. 打开 https://www.coze.cn 注册登录
2. 左侧菜单 → **插件** → 搜索「**蝉镜**」或「**飞影**」

## 二、创建工作流（核心）

路径：个人空间 → 工作流 → 新建工作流

### 节点结构

```
┌─────────────┐
│  开始节点    │  → 变量: text_input (String) — 你的口播文案
└──────┬──────┘
       ↓
┌─────────────┐
│ 蝉镜-获取形象 │  → 列出你的数字人形象，选一个ID
└──────┬──────┘
       ↓
┌─────────────┐
│ 蝉镜-合成视频 │  → 传入: 文案 + 形象ID + 声音ID
└──────┬──────┘    输出: task_id
       ↓
┌─────────────┐
│ 循环节点     │  → while status != 3:
│ 蝉镜-查进度  │      每5秒查一次进度
└──────┬──────┘
       ↓
┌─────────────┐
│  结束节点    │  → 输出: 视频URL
└─────────────┘
```

### 参数设置

| 节点 | 关键参数 |
|------|---------|
| 开始节点 | `text_input` (String) |
| 蝉镜-获取形象 | 不用参数，直接获取列表 |
| 蝉镜-合成视频 | `text`=开始节点.text_input, `figure_id`=你选的ID, `voice_id`=默认 |
| 循环节点 | 最大循环30次, 每次间隔5秒 |
| 蝉镜-查进度 | `task_id`=合成视频输出的 task_id, 判断 `status==3` 时跳出 |

## 三、创建智能体

1. 新建智能体 → 绑定你的工作流
2. 人设提示词:
   ```
   你是一个专业短视频创作者。用户给你一段文案，你直接用数字人工作流生成口播视频。
   ```
3. 发布 → 复制 Bot ID

## 四、两种使用方式

### 方式A: 网页对话
直接在 Coze 对话框贴文案 → 等视频 → 下载 → 导入剪映

### 方式B: API 调用（可批量）
```python
import requests

COZE_API_KEY = "你的API Key"
BOT_ID = "你的Bot ID"

def generate_avatar_video(text):
    resp = requests.post(
        "https://api.coze.cn/v3/chat",
        headers={
            "Authorization": f"Bearer {COZE_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "bot_id": BOT_ID,
            "user_id": "me",
            "additional_messages": [{"role": "user", "content": text}],
            "stream": False,
        }
    )
    return resp.json()

# 批量生成
if __name__ == "__main__":
    scripts = [
        "今天给大家分享一个省钱小技巧...",
        "AI技术的发展正在改变我们的生活方式...",
        "新手学编程最容易犯的三个错误...",
    ]
    for s in scripts:
        result = generate_avatar_video(s)
        print(f"生成结果: {result}")
```

## 五、视频下载后流程

```
Coze出片(MP4) → 剪映 → 加背景音乐 → 调整字幕样式 → 加片头片尾 → 导出 → 抖音发布
```

## 六、进阶技巧

1. **克隆自己的声音**: 蝉镜支持上传录音→克隆→用自己声音播报
2. **多形象切换**: 不同主题用不同数字人（财经一个、生活一个）
3. **批量模版**: API 脚本一次生成 10 条，集中导入剪映批量剪辑
4. **热点跟进**: 配合 TrendRadar 舆情监控抓热点 → 发给 Coze → 自动出片

## 费用

蝉镜基础功能: **完全免费**
飞影: 基础免费, 高级形象收费
Coze 平台: 免费额度覆盖日常使用
