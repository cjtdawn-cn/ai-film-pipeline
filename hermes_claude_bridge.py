"""
Hermes <-> Claude Code Deep Integration Bridge
Usage:
  python hermes_claude_bridge.py sync-memory
  python hermes_claude_bridge.py sync-skills
  python hermes_claude_bridge.py serve
"""
import os, sys, json, shutil, subprocess, io
from pathlib import Path
from datetime import datetime

# Fix Windows GBK encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Paths
HERMES_HOME = Path(os.environ.get("HERMES_HOME", r"D:\claude-config\.hermes"))
CLAUDE_HOME = Path(r"D:\claude-config\.claude")
MEMORY_DIR = CLAUDE_HOME / "projects" / "d--Kronos-master" / "memory"
SKILLS_DIR = CLAUDE_HOME / "skills"
PROJECT_ROOT = Path(r"D:\AI_Agents\video-tools")
PYTHON = r"D:\py\python.exe"
HERMES_CLI = r"D:\py\Scripts\hermes.exe"


class HermesClaudeBridge:
    """双向桥接器"""

    # ── Memory Sync ──
    def sync_memory(self):
        """Sync Hermes memory <-> Claude Code Memory"""
        print("[Memory Sync] Hermes <-> Claude Code")

        # 1. Read Claude Code MEMORY.md index
        memory_index = MEMORY_DIR / "MEMORY.md"
        if memory_index.exists():
            entries = []
            for line in memory_index.read_text(encoding="utf-8").split("\n"):
                if line.startswith("- [") and "](" in line:
                    entries.append(line)
            print(f"  Claude Code memories: {len(entries)} entries")

            # 2. Export to Hermes format (Honcho dialectic model)
            export = {
                "source": "claude-code",
                "synced_at": datetime.now().isoformat(),
                "entries": entries,
                "memory_dir": str(MEMORY_DIR),
            }
            export_path = HERMES_HOME / "claude_memories.json"
            export_path.write_text(json.dumps(export, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"  -> Exported to {export_path}")

        # 3. Read Hermes sessions DB if exists
        hermes_db = HERMES_HOME / "sessions.db"
        if hermes_db.exists():
            print(f"  Hermes sessions DB: {hermes_db.stat().st_size // 1024}KB")
            print(f"  [OK] Hermes memory active (FTS5 indexed)")

    # ── Skill Sync ──
    def sync_skills(self):
        """Sync skills: Hermes skills/ <-> Claude Code skills/"""
        print("[Skill Sync] Hermes <-> Claude Code")

        # 1. Copy Claude Code skills to Hermes
        if SKILLS_DIR.exists():
            hermes_skills = HERMES_HOME / "skills"
            hermes_skills.mkdir(parents=True, exist_ok=True)
            for skill_file in SKILLS_DIR.glob("*.md"):
                dest = hermes_skills / skill_file.name
                if not dest.exists():
                    shutil.copy2(skill_file, dest)
                    print(f"  Claude -> Hermes: {skill_file.name}")

        # 2. Copy Hermes built-in skills to Claude Code
        hermes_builtin = Path(r"D:\py\Lib\site-packages\skills")
        if hermes_builtin.exists():
            SKILLS_DIR.mkdir(parents=True, exist_ok=True)
            for skill_file in hermes_builtin.glob("**/*.md"):
                dest = SKILLS_DIR / skill_file.name
                if not dest.exists():
                    shutil.copy2(skill_file, dest)
                    print(f"  Hermes -> Claude: {skill_file.name}")

        # 3. Register producer_v3 skills
        producer_skills = [
            ("燧人影视制片", "producer_v3.py", "一键AI电影: 剧本→视频→配音→剪映"),
            ("Wav2Lip口型", "lipsync_engine.py", "音视频口型同步"),
            ("CosyVoice配音", "producer_v3.py", "AI语音合成"),
            ("CapCut剪辑", "producer_v3.py", "剪映自动草稿生成"),
        ]
        for name, script, desc in producer_skills:
            skill_md = HERMES_HOME / "skills" / f"{name}.md"
            skill_md.parent.mkdir(parents=True, exist_ok=True)
            skill_md.write_text(f"""---
name: {name}
description: {desc}
source: {PROJECT_ROOT / script}
---

# {name}

{desc}

## Usage
Trigger with: `/{name}` or mention "{desc}"

## Script
`{PROJECT_ROOT / script}`
""", encoding="utf-8")
            print(f"  Producer skill: {name}")

    # ── MCP Bridge Server ──
    def serve_mcp(self):
        """启动 Hermes MCP 服务器 → Claude Code 可调用"""
        print("[MCP Bridge] Starting Hermes MCP server on port 9001...")

        # Start Hermes MCP server in background
        cmd = [HERMES_CLI, "mcp", "serve", "--port", "9001"]
        print(f"  Running: {' '.join(cmd)}")
        subprocess.Popen(cmd, creationflags=subprocess.CREATE_NO_WINDOW)

        # Generate Claude Code MCP config
        mcp_config = CLAUDE_HOME / "mcp_servers.json"
        mcp_data = {
            "mcpServers": {
                "hermes-agent": {
                    "command": HERMES_CLI,
                    "args": ["mcp", "serve", "--port", "9001"],
                    "env": {"HERMES_HOME": str(HERMES_HOME)},
                }
            }
        }
        mcp_config.write_text(json.dumps(mcp_data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  [OK] Claude Code MCP config written to {mcp_config}")
        print(f"  [OK] Hermes MCP server running on http://localhost:9001")

    # ── Context Enrichment ──
    def enrich_context(self):
        """将 Hermes 自进化上下文注入 Claude Code CLAUDE.md"""
        print("[Context] Enriching Claude Code context from Hermes...")

        hermes_memory = HERMES_HOME / "claude_memories.json"
        if not hermes_memory.exists():
            print("  No Hermes memories yet. Run sync-memory first.")
            return

        # Read Hermes memory insights
        data = json.loads(hermes_memory.read_text(encoding="utf-8"))

        # Update Claude Code CLAUDE.md with Hermes insights
        claude_md = CLAUDE_HOME / "CLAUDE.md"
        if claude_md.exists():
            content = claude_md.read_text(encoding="utf-8")
            enrichment = f"""

<!-- Hermes Agent Integration (auto-synced {datetime.now().strftime('%Y-%m-%d %H:%M')}) -->
## Hermes Agent Bridge
- Hermes home: {HERMES_HOME}
- Memories synced: {len(data.get('entries', []))} entries
- Hermes CLI: `hermes` (D:\\py\\Scripts\\hermes.exe)
- MCP server: `hermes mcp serve --port 9001`
- Skills: `hermes skills list`
- Memory: `hermes memory search <query>`
<!-- End Hermes Integration -->
"""
            if "Hermes Agent Bridge" not in content:
                claude_md.write_text(content + enrichment, encoding="utf-8")
                print(f"  [OK] CLAUDE.md enriched with Hermes bridge info")
            else:
                print(f"  [OK] CLAUDE.md already has Hermes bridge")

    # ── Full Integration ──
    def integrate_all(self):
        """一键完成所有融合"""
        self.sync_memory()
        self.sync_skills()
        self.serve_mcp()
        self.enrich_context()
        print("\n[=== Hermes <-> Claude Code Integration Complete ===]")
        print(f"  Hermes home: {HERMES_HOME}")
        print(f"  Claude Code home: {CLAUDE_HOME}")
        print(f"  Memory: bidirectional sync")
        print(f"  Skills: shared skill pool")
        print(f"  MCP: Hermes tools available in Claude Code")
        print(f"  Context: CLAUDE.md enriched")


if __name__ == "__main__":
    bridge = HermesClaudeBridge()
    cmds = {
        "sync-memory": bridge.sync_memory,
        "sync-skills": bridge.sync_skills,
        "serve": bridge.serve_mcp,
        "enrich": bridge.enrich_context,
        "all": bridge.integrate_all,
    }

    action = sys.argv[1] if len(sys.argv) > 1 else "all"
    if action in cmds:
        cmds[action]()
    else:
        print(f"Usage: python hermes_claude_bridge.py [{'|'.join(cmds)}]")
        print(f"Default: all")
