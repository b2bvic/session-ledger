# session-ledger

You can lose earlier decisions and tool results across separate Claude Code and Codex transcripts. Use session-ledger to archive those records in SQLite and search them from your terminal.

Install with Python 3.11+ and curl. You need no pip packages:

```bash
mkdir -p "$HOME/.local/bin" && curl -fsSL https://raw.githubusercontent.com/b2bvic/session-ledger/main/ledger -o "$HOME/.local/bin/ledger" && chmod +x "$HOME/.local/bin/ledger"
```

Sample output from `~/.local/bin/ledger search "authentication bug"` when your initialized database has no matches:

```text
No results for: authentication bug
```

Run `~/.local/bin/ledger init` and `~/.local/bin/ledger harvest --source all` before you search both providers.

## Worked example

```bash
./ledger init
./ledger harvest
./ledger search "authentication bug"
```

## Data boundary

The default database is local SQLite storage under the Claude configuration
directory. `harvest` reads local JSONL transcripts from your selected providers. It records
messages, file operations, errors, and skipped inputs; it does not verify that
the archived statements are correct.

Use `./ledger --help` and each subcommand's help before changing paths or
retention behavior.

## Source selection

Source version 0.2.0 adds Codex ingestion and all-project Claude discovery.
The existing v0.1.0 release binary does not include these changes. The install command follows the source on `main`.

| Setting | Purpose |
|---|---|
| `LEDGER_CLAUDE` | Claude configuration directory. The default is `~/.claude`. |
| `LEDGER_PROJECT` | Limit Claude discovery to one project directory. Otherwise, scan all projects. |
| `LEDGER_CODEX` | Codex configuration directory. The default is `~/.codex`. |
| `LEDGER_DB` or `--db` | Select the local database. |
| `LEDGER_VAULT` | Optional Markdown root for `--source vault` or `--source all`. |

```bash
ledger harvest --source claude-code
ledger harvest --source codex
ledger harvest --source all
ledger harvest --dry-run --source all
```

Plain `harvest` retains its Claude-only default. Codex discovery includes `sessions/` and `archived_sessions/` recursively.
The receipt lists configured roots, unavailable inputs, discovered files, skips, errors, unknown formats, and identity conflicts.
Zero discovered files does not establish complete coverage.
`--since` filters files by modification time. It is an ingestion shortcut, not an event-time usage window.

Dry runs use an in-memory database and do not create or change your configured database.
Malformed transcripts and child files preserve the previous session snapshot. Fix the input before retrying.
A changed child transcript causes a parent-session refresh even when the parent file is unchanged.
Conflicting identities in different existing files are rejected. Moving a source to the archive can refresh its stored path.
Harvest returns exit 1 for reported input errors, unknown formats, or identity conflicts.
Read the coverage receipt even when the command returns zero.

## Shared record export

```bash
ledger export --pretty --out ./sessions.json
ledger export --session codex:YOUR_SESSION_ID --pretty
```

The export contains provider, stored and native session identifiers, parent identifier when available, source paths, messages, and correlated tools.
Each message includes its parsed source record when available. Missing source timestamps stay unknown rather than becoming the harvest time.
Codex session identifiers come from `session_meta`, including renamed exports.
Claude identifiers use `sessionId` when present and retain filename fallback for older files.
Codex stored identifiers have a `codex:` prefix. Interpret message and tool identifiers within their provider and session.

Codex ingestion supports message, function-call, custom-tool-call, tool-output, and native cumulative token records.
Mirrored assistant event messages do not duplicate matching response-item text in search.
Other record types are not guaranteed to be indexed. The source file remains the complete input record.

The additive schema migration preserves version-one tables and existing sessions.
Back up your database before an upgrade. Use a copy to confirm your own transcript coverage first.
Legacy cost estimates retain their historical model table. An unsupported model can show zero; that value does not mean free usage.
Use the monitor for timestamp-filtered observations, and your provider for billing.

## Verify

```bash
python3 -m unittest discover -s tests -v
```

Tests use isolated synthetic transcripts and databases. They cover migration, source discovery, resumed children, malformed-input preservation, provider identities, and export.
See [Build a macOS release](RELEASING.md) for packaging.

## License

MIT.

## How this was built

This 2026 README refit used model assistance.

No claim is made about how the underlying code was authored or reviewed.

## Principles

This repository demonstrates **P02 (own the memory plane)** and **P03 (continuity compounds)** because it harvests JSONL records into indexed storage while tracking messages, file operations, errors, and skipped inputs.

[Read the principles](https://victorvalentineromo.com/principles).
