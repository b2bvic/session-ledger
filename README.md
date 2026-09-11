# session-ledger

You can lose earlier decisions and tool results across separate Claude Code transcripts. Use session-ledger to archive those records in SQLite and search them from your terminal.

Install with Python 3.11+ and curl. You need no pip packages:

```bash
mkdir -p "$HOME/.local/bin" && curl -fsSL https://raw.githubusercontent.com/b2bvic/session-ledger/main/ledger -o "$HOME/.local/bin/ledger" && chmod +x "$HOME/.local/bin/ledger"
```

Sample output from `~/.local/bin/ledger search "authentication bug"` when your initialized database has no matches:

```text
No results for: authentication bug
```

Run `~/.local/bin/ledger init` and `~/.local/bin/ledger harvest` before you search your transcripts.

## Worked example

```bash
./ledger init
./ledger harvest
./ledger search "authentication bug"
```

## Data boundary

The default database is local SQLite storage under the Claude configuration
directory. `harvest` reads local Claude Code JSONL transcripts. It records
messages, file operations, errors, and skipped inputs; it does not verify that
the archived statements are correct.

Use `./ledger --help` and each subcommand's help before changing paths or
retention behavior.

## License

MIT.

## How this was built

This 2026 README refit used model assistance.

No claim is made about how the underlying code was authored or reviewed.

## Principles

This repository demonstrates **P02 (own the memory plane)** and **P03 (continuity compounds)** because it harvests JSONL records into indexed storage while tracking messages, file operations, errors, and skipped inputs.

[Read the principles](https://victorvalentineromo.com/principles).
