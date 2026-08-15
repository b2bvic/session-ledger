# session-ledger

A zero-dependency SQLite archive and search tool for local session records.

## Principle cluster

This repository demonstrates **P02 (own the memory plane)** and **P03 (continuity compounds)** because it harvests JSONL records into indexed storage while tracking messages, file operations, errors, and skipped inputs.

[Read the principles](https://victorvalentineromo.com/principles).

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
