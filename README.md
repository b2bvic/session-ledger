# AI agent session audit trail: session-ledger

Session-ledger archives local Claude Code and Codex CLI transcripts in SQLite for operators who use hosted models.
It keeps an AI agent session audit trail when decisions and tool results span separate sessions.

[Project page](https://scalewithsearch.com/code/session-ledger)

## Install

Use Git and Python 3.11 or newer with SQLite FTS5 support. The runtime needs no pip packages.

```bash
git clone https://github.com/b2bvic/session-ledger.git
cd session-ledger
```

For a source installation after review:

```bash
mkdir -p "$HOME/.local/bin"
install -m 755 ledger "$HOME/.local/bin/ledger"
```

## Quick start

Create an isolated database without reading your session history:

```bash
demo_record=$(mktemp -d)
mkdir -p "$demo_record/claude/projects" "$demo_record/codex/sessions"
export LEDGER_DB="$demo_record/sessions.db"
export LEDGER_CLAUDE="$demo_record/claude"
export LEDGER_CODEX="$demo_record/codex"
unset LEDGER_PROJECT LEDGER_VAULT
python3 ./ledger init
python3 ./ledger harvest --source all
python3 ./ledger search "authentication bug"
python3 ./ledger export --pretty --out "$demo_record/sessions.json"
```

The empty example reports missing coverage and no search matches.
Set the source roots to your own transcript directories before importing session history.
This provides Claude Code session history and a Codex CLI session archive.
Run `harvest --dry-run --source all` to preview ingestion with an in-memory database.

## How it works

The ledger discovers local JSONL files and imports messages, tool records, file operations, and parse errors.
SQLite FTS5 transcript search indexes the stored text.
Provider identifiers keep Claude and Codex records separate when native session identifiers collide.
JSON export includes provider, session identities, source paths, messages, correlated tools, and available parsed source records.
The database and JSON export remain files you control. Changing model tools requires a compatible transcript adapter.
These are recordkeeping patterns a team can adopt; an archived statement remains a statement until you verify its outcome.

| Setting | Purpose |
|---|---|
| `LEDGER_DB` or `--db` | Select the SQLite database. |
| `LEDGER_CLAUDE` | Select the Claude configuration root. |
| `LEDGER_PROJECT` | Restrict Claude discovery to one project. |
| `LEDGER_CODEX` | Select the Codex configuration root. |
| `LEDGER_VAULT` | Select an optional Markdown root for vault ingestion. |

Plain `harvest` defaults to Claude. Use `--source codex` or `--source all` for other sources.
Codex discovery includes `sessions/` and `archived_sessions/` recursively.
Read each coverage receipt even when the command returns zero.

Run the regression suite:

```bash
python3 -m unittest discover -s tests -v
```

## Limits

- Missing roots and zero discovered files leave coverage unknown.
- `--since` filters file modification times. It is an ingestion shortcut, not an event-time usage window.
- Supported transcript schemas cover the implemented parsers. Other record types can remain unindexed.
- Malformed inputs preserve the prior session snapshot. Identity conflicts and unknown formats return a failing harvest status.
- Dry runs do not create or change the configured database.
- The additive schema migration preserves version-one data. Back up the database before an upgrade.
- Legacy model cost tables can return zero for unsupported models. Use provider billing for account charges.
- Source version 0.2.0 includes Codex ingestion. Compare an installed binary’s version with this checkout before an upgrade.

See [Build a macOS release](RELEASING.md) for packaging instructions.

## Related repositories

- [agent-oversight](https://github.com/b2bvic/agent-oversight): orchestration cluster and evaluation guide.
- [agent-monitor](https://github.com/b2bvic/agent-monitor): timestamp-filtered usage observations.
- [skills](https://github.com/b2bvic/skills): session search and local artifact checks.
- [owned-record](https://github.com/b2bvic/owned-record): owned memory cluster.

## How this was built

This README was written with model assistance in 2026. The code and tests in this repository are the evidence; read them to judge the tool.

## License

[MIT](LICENSE).
