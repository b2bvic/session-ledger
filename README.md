# session-ledger

Searchable archive of your Claude Code sessions. Zero dependencies. SQLite + FTS5 full-text search.

Every conversation you've had with Claude Code is sitting in JSONL files on your disk. This tool harvests them into a single SQLite database with millisecond-fast full-text search across every message, tool use, and file operation.

Built by [Victor Valentine Romo](https://victorvalentineromo.com) at [Scale With Search](https://scalewithsearch.com).

## Install

```bash
curl -o ~/.local/bin/ledger https://raw.githubusercontent.com/b2bvic/session-ledger/main/ledger
chmod +x ~/.local/bin/ledger
```

Requirements: Python 3.11+ (stdlib only, zero pip dependencies).

## Quick Start

```bash
# Initialize the database
ledger init

# Harvest all Claude Code transcripts
ledger harvest

# Search across every session
ledger search "authentication bug"

# Browse recent sessions
ledger sessions list

# See which files you touched most
ledger files hot

# Usage statistics
ledger stats overview
```

## What It Captures

From each Claude Code JSONL transcript:

- Every user message and assistant response
- Tool uses (Bash, Read, Write, Edit, Grep, etc.) with arguments and results
- File operations (which files were read, written, created)
- Session metadata (start/end time, duration, model used)
- Token counts and estimated cost per session
- Domain classification (configurable keyword matching)

## Architecture

- **9 SQLite tables**: sessions, messages, tool_uses, file_operations, compactions, subagents, concurrency_groups, harvest_log, vault_files
- **3 FTS5 virtual tables**: fts_messages, fts_vault_files, fts_unified (cross-corpus search)
- **Porter stemming + Unicode normalization** for search quality
- **WAL mode** for concurrent reads during harvest
- **SHA-256 deduplication** — re-running harvest is safe, never double-counts

## Commands

```
ledger init                         Create/migrate database
ledger harvest [--full] [--dry-run] Ingest new transcripts
ledger search <query> [-n 20]       Full-text search
ledger sessions list [--since 7d]   List recent sessions
ledger sessions show <id>           Show session detail
ledger files hot [--since 30d]      Most-touched files
ledger files trail <path>           History of a specific file
ledger stats overview               Usage summary
ledger stats daily [--since 30d]    Daily activity
ledger stats domains                Domain breakdown
ledger stats tools                  Tool usage frequency
ledger stats models                 Model usage + cost
ledger status                       Database health check
ledger query <sql>                  Raw SQL access
```

## Configuration

All paths are configurable via environment variables:

| Variable | Default | Purpose |
|----------|---------|---------|
| `LEDGER_DB` | `~/.claude/session-ledger.db` | Database location |
| `LEDGER_CLAUDE` | `~/.claude` | Claude config directory |
| `LEDGER_PROJECT` | auto-detected | Project directory for session discovery |
| `LEDGER_TZ` | `America/New_York` | Timezone for display |

### Custom Domain Classification

Create `~/.config/ledger/domains.json` to define your own domains:

```json
{
  "frontend": ["react", "css", "component", "ui", "layout", "responsive"],
  "backend": ["api", "database", "migration", "endpoint", "auth"],
  "infra": ["docker", "deploy", "ci", "kubernetes", "terraform"],
  "docs": ["readme", "documentation", "guide", "tutorial"]
}
```

Sessions are classified by keyword matching against message content. Domains appear in `ledger stats domains` and `ledger sessions list`.

## Examples

```bash
# Find every time you discussed database migrations
ledger search "migration schema alter"

# What did you work on last week?
ledger sessions list --since 7d

# Which files change the most?
ledger files hot --since 30d

# How much have you spent on Claude this month?
ledger stats models --since 30d

# Raw SQL for custom queries
ledger query "SELECT date(started_at) as day, count(*) as sessions FROM sessions GROUP BY day ORDER BY day DESC LIMIT 14"
```

## How It Works

1. Claude Code stores session transcripts as JSONL in `~/.claude/projects/*/`
2. `ledger harvest` reads each JSONL file, parses messages and tool uses
3. Everything goes into SQLite with FTS5 indexes for instant search
4. SHA-256 file hashing prevents duplicate ingestion on re-harvest
5. WAL mode means you can search while a harvest is running

## License

MIT
