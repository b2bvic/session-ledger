#!/usr/bin/env python3
"""Offline regression tests for session-ledger. Synthetic fixtures only."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "ledger"

CLAUDE_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
CLAUDE_B = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
SHARED = "cccccccc-cccc-cccc-cccc-cccccccccccc"
CODEX_ID = "dddddddd-dddd-dddd-dddd-dddddddddddd"
WRONG_ROLLOUT = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"


def write_jsonl(path: Path, records) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for rec in records:
        if isinstance(rec, str):
            lines.append(rec)
        else:
            lines.append(json.dumps(rec))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def claude_user(text, uuid="u1", ts="2026-01-15T12:00:00.000Z", **extra):
    rec = {
        "type": "user",
        "uuid": uuid,
        "parentUuid": extra.pop("parentUuid", None),
        "timestamp": ts,
        "message": {"role": "user", "content": text},
    }
    rec.update(extra)
    return rec


def claude_assistant(text, uuid="a1", parent="u1", ts="2026-01-15T12:00:01.000Z", tools=None):
    content = [{"type": "text", "text": text}]
    if tools:
        content.extend(tools)
    return {
        "type": "assistant",
        "uuid": uuid,
        "parentUuid": parent,
        "timestamp": ts,
        "message": {
            "role": "assistant",
            "model": "claude-sonnet-4-5-20250929",
            "content": content,
            "usage": {
                "input_tokens": 10,
                "output_tokens": 12,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
            },
        },
    }


def claude_tool_result(tool_use_id, text, uuid="u2", parent="a1", ts="2026-01-15T12:00:02.000Z"):
    return {
        "type": "user",
        "uuid": uuid,
        "parentUuid": parent,
        "timestamp": ts,
        "message": {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": tool_use_id, "content": text}
            ],
        },
    }


def codex_session(session_id, extra_meta=None):
    payload = {
        "id": session_id,
        "timestamp": "2026-01-15T12:00:00.000Z",
        "cwd": "/tmp/synth-app",
        "originator": "codex_cli_rs",
        "cli_version": "0.42.0",
    }
    if extra_meta:
        payload.update(extra_meta)
    return {
        "timestamp": "2026-01-15T12:00:00.000Z",
        "type": "session_meta",
        "payload": payload,
    }


def codex_user(text):
    return {
        "timestamp": "2026-01-15T12:00:01.000Z",
        "type": "response_item",
        "payload": {
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": text}],
        },
    }


def codex_assistant(text):
    return {
        "timestamp": "2026-01-15T12:00:04.000Z",
        "type": "response_item",
        "payload": {
            "type": "message",
            "role": "assistant",
            "content": [{"type": "output_text", "text": text}],
        },
    }


def codex_function_call(call_id, name, arguments):
    return {
        "timestamp": "2026-01-15T12:00:02.000Z",
        "type": "response_item",
        "payload": {
            "type": "function_call",
            "name": name,
            "arguments": arguments,
            "call_id": call_id,
        },
    }


def codex_function_output(call_id, output):
    return {
        "timestamp": "2026-01-15T12:00:03.000Z",
        "type": "response_item",
        "payload": {
            "type": "function_call_output",
            "call_id": call_id,
            "output": output,
        },
    }


def codex_agent_message(text):
    return {
        "timestamp": "2026-01-15T12:00:04.000Z",
        "type": "event_msg",
        "payload": {"type": "agent_message", "message": text},
    }


def codex_tokens(inp=111, out=33, cached=2):
    return {
        "timestamp": "2026-01-15T12:00:05.000Z",
        "type": "event_msg",
        "payload": {
            "type": "token_count",
            "info": {
                "total_token_usage": {
                    "input_tokens": inp,
                    "cached_input_tokens": cached,
                    "output_tokens": out,
                    "reasoning_output_tokens": 0,
                    "total_tokens": inp + out,
                }
            },
        },
    }


class LedgerHarness(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.claude = self.home / "claude"
        self.codex = self.home / "codex"
        self.db = self.home / "ledger.db"
        self.projects = self.claude / "projects"
        self.projects.mkdir(parents=True)
        (self.codex / "sessions").mkdir(parents=True)
        (self.codex / "archived_sessions").mkdir(parents=True)
        self.env = os.environ.copy()
        self.env["HOME"] = str(self.home)
        self.env["LEDGER_DB"] = str(self.db)
        self.env["LEDGER_CLAUDE"] = str(self.claude)
        self.env["LEDGER_CODEX"] = str(self.codex)
        self.env.pop("LEDGER_PROJECT", None)
        self.env.pop("LEDGER_VAULT", None)
        self.env["LEDGER_TZ"] = "UTC"

    def tearDown(self):
        self.tmp.cleanup()

    def run_ledger(self, *args, check=True):
        result = subprocess.run(
            [sys.executable, str(LEDGER), *args],
            cwd=str(ROOT),
            env=self.env,
            capture_output=True,
            text=True,
        )
        if check and result.returncode != 0:
            raise AssertionError(
                f"ledger {' '.join(args)} failed ({result.returncode})\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
            )
        return result

    def connect(self):
        conn = sqlite3.connect(str(self.db))
        conn.row_factory = sqlite3.Row
        return conn

    def add_project(self, name: str) -> Path:
        path = self.projects / name
        path.mkdir(parents=True, exist_ok=True)
        return path

    def load_module(self):
        loader = importlib.machinery.SourceFileLoader(
            "session_ledger_under_test", str(LEDGER)
        )
        spec = importlib.util.spec_from_loader(loader.name, loader)
        mod = importlib.util.module_from_spec(spec)
        saved = {
            k: os.environ.get(k)
            for k in ("LEDGER_DB", "LEDGER_CLAUDE", "LEDGER_CODEX", "LEDGER_PROJECT", "LEDGER_VAULT")
        }
        os.environ.update(
            {
                "LEDGER_DB": str(self.db),
                "LEDGER_CLAUDE": str(self.claude),
                "LEDGER_CODEX": str(self.codex),
            }
        )
        os.environ.pop("LEDGER_PROJECT", None)
        os.environ.pop("LEDGER_VAULT", None)
        try:
            loader.exec_module(mod)
        finally:
            for key, value in saved.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
        return mod


class DiscoveryAndHarvestTests(LedgerHarness):
    def test_multi_project_default_discovery(self):
        proj_a = self.add_project("proj-a")
        proj_b = self.add_project("proj-b")
        write_jsonl(
            proj_a / f"{CLAUDE_A}.jsonl",
            [claude_user("project alpha unique-token-alpha")],
        )
        write_jsonl(
            proj_b / f"{CLAUDE_B}.jsonl",
            [claude_user("project beta unique-token-beta")],
        )
        out = self.run_ledger("harvest").stdout
        conn = self.connect()
        rows = conn.execute("SELECT session_uuid, source_path FROM sessions ORDER BY session_uuid").fetchall()
        self.assertEqual([r["session_uuid"] for r in rows], [CLAUDE_A, CLAUDE_B])
        texts = [r[0] for r in conn.execute("SELECT content_text FROM messages").fetchall()]
        self.assertTrue(any("unique-token-alpha" in (t or "") for t in texts))
        self.assertTrue(any("unique-token-beta" in (t or "") for t in texts))
        conn.close()
        self.assertIn("Discovered: 2", out)

    def test_ledger_project_override(self):
        proj_a = self.add_project("proj-a")
        proj_b = self.add_project("proj-b")
        write_jsonl(proj_a / f"{CLAUDE_A}.jsonl", [claude_user("keep-me")])
        write_jsonl(proj_b / f"{CLAUDE_B}.jsonl", [claude_user("skip-me")])
        self.env["LEDGER_PROJECT"] = str(proj_a)
        self.run_ledger("harvest")
        conn = self.connect()
        uuids = [r[0] for r in conn.execute("SELECT session_uuid FROM sessions").fetchall()]
        conn.close()
        self.assertEqual(uuids, [CLAUDE_A])

    def test_nested_subagents(self):
        proj = self.add_project("proj-nested")
        session_path = proj / f"{CLAUDE_A}.jsonl"
        write_jsonl(
            session_path,
            [
                claude_user("parent session prompt"),
                claude_assistant("parent reply"),
            ],
        )
        child = proj / CLAUDE_A / "subagents" / "agent-child.jsonl"
        write_jsonl(
            child,
            [
                claude_user("nested subagent unique-child-token", uuid="cu1"),
                claude_assistant("child reply unique-child-answer", uuid="ca1", parent="cu1"),
            ],
        )
        grandchild = proj / CLAUDE_A / "subagents" / "child" / "subagents" / "agent-grandchild.jsonl"
        write_jsonl(
            grandchild,
            [
                claude_user("deeper unique-grandchild-token", uuid="gu1"),
                claude_assistant("grandchild reply", uuid="ga1", parent="gu1"),
            ],
        )
        self.run_ledger("harvest")
        conn = self.connect()
        agents = [r[0] for r in conn.execute("SELECT agent_id FROM subagents ORDER BY agent_id").fetchall()]
        self.assertEqual(agents, ["child", "grandchild"])
        side = conn.execute(
            "SELECT content_text, agent_id, is_sidechain FROM messages WHERE is_sidechain = 1 ORDER BY agent_id"
        ).fetchall()
        self.assertGreaterEqual(len(side), 4)
        blob = " ".join((r["content_text"] or "") for r in side)
        self.assertIn("unique-child-token", blob)
        self.assertIn("unique-grandchild-token", blob)
        conn.close()

    def test_resumed_and_unchanged_files(self):
        proj = self.add_project("proj-resume")
        path = proj / f"{CLAUDE_A}.jsonl"
        write_jsonl(path, [claude_user("first prompt")])
        first = self.run_ledger("harvest").stdout
        self.assertIn("Harvested:  1", first)
        conn = self.connect()
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0], 1)
        conn.close()

        unchanged = self.run_ledger("harvest").stdout
        self.assertIn("Skipped:    1", unchanged)
        conn = self.connect()
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0], 1)
        conn.close()

        write_jsonl(
            path,
            [
                claude_user("first prompt"),
                claude_assistant("follow-up after resume unique-resume-token"),
            ],
        )
        resumed = self.run_ledger("harvest").stdout
        self.assertIn("Harvested:  1", resumed)
        conn = self.connect()
        count = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        texts = [r[0] for r in conn.execute("SELECT content_text FROM messages").fetchall()]
        conn.close()
        self.assertEqual(count, 2)
        self.assertEqual(sum(1 for t in texts if t == "first prompt"), 1)
        self.assertTrue(any("unique-resume-token" in (t or "") for t in texts))

    def test_resume_replaces_unified_search_snapshot(self):
        path = self.add_project("search-resume") / f"{CLAUDE_A}.jsonl"
        retained = "retainedsearchterm appears in a sufficiently long message"
        removed = "removedsearchterm appears in an obsolete message"
        write_jsonl(path, [claude_user(retained), claude_assistant(removed)])
        self.run_ledger("harvest")
        with self.connect() as conn:
            conn.execute("INSERT INTO fts_unified VALUES (?, ?, ?, ?, ?)",
                         ("vault_file", CLAUDE_A, "Work", "", "vaultsearchterm stays indexed"))
        write_jsonl(path, [claude_user(retained), claude_assistant("replacement message exceeds twenty characters")])
        self.run_ledger("harvest")
        with self.connect() as conn:
            for term, expected in (("retainedsearchterm", 1), ("removedsearchterm", 0),
                                   ("vaultsearchterm", 1)):
                count = conn.execute("SELECT COUNT(*) FROM fts_unified WHERE fts_unified MATCH ?",
                                     (term,)).fetchone()[0]
                self.assertEqual(count, expected, term)

    def test_missing_roots_are_explicit(self):
        self.env["LEDGER_CODEX"] = str(self.home / "missing-codex")
        self.env["LEDGER_CLAUDE"] = str(self.home / "missing-claude")
        out = self.run_ledger("harvest", "--source", "all").stdout
        self.assertIn("unavailable", out)
        self.assertIn("missing", out)
        self.assertIn("0 discovered files is not evidence of complete coverage", out)
        self.assertIn("not configured", out)

    def test_malformed_rows_and_prior_state(self):
        proj = self.add_project("proj-malformed")
        path = proj / f"{CLAUDE_A}.jsonl"
        write_jsonl(path, [claude_user("good prompt unique-good-row"), claude_assistant("good response")])
        self.run_ledger("harvest")
        write_jsonl(path, [claude_user("changed partial row"), "{this is not json"])
        result = self.run_ledger("harvest", check=False)
        self.assertEqual(result.returncode, 1)
        conn = self.connect()
        texts = [r[0] for r in conn.execute("SELECT content_text FROM messages")]
        conn.close()
        self.assertEqual(texts, ["good prompt unique-good-row", "good response"])

    def test_duplicate_identity_rejected(self):
        proj_a = self.add_project("proj-a")
        proj_b = self.add_project("proj-b")
        write_jsonl(proj_a / f"{SHARED}.jsonl", [claude_user("first owner")])
        write_jsonl(proj_b / f"{SHARED}.jsonl", [claude_user("second owner should conflict")])
        out = self.run_ledger("harvest", check=False).stdout
        self.assertIn("Conflicts:  1", out)
        conn = self.connect()
        rows = conn.execute("SELECT source_path, first_prompt FROM sessions").fetchall()
        self.assertEqual(len(rows), 1)
        self.assertIn("proj-a", rows[0]["source_path"])
        self.assertEqual(rows[0]["first_prompt"], "first owner")
        conn.close()

    def test_vendor_uuid_collision(self):
        proj = self.add_project("proj-collision")
        write_jsonl(proj / f"{SHARED}.jsonl", [claude_user("claude owner of shared uuid")])
        rollout = (
            self.codex
            / "sessions"
            / "2026"
            / "01"
            / "15"
            / f"rollout-2026-01-15T12-00-00-{WRONG_ROLLOUT}.jsonl"
        )
        write_jsonl(
            rollout,
            [
                codex_session(SHARED),
                codex_user("codex owner of shared uuid unique-codex-collision"),
                codex_assistant("codex reply"),
            ],
        )
        self.run_ledger("harvest", "--source", "all")
        conn = self.connect()
        rows = conn.execute(
            "SELECT session_uuid, provider, native_session_id FROM sessions ORDER BY provider"
        ).fetchall()
        self.assertEqual(len(rows), 2)
        by_provider = {r["provider"]: r for r in rows}
        self.assertEqual(by_provider["claude-code"]["session_uuid"], SHARED)
        self.assertEqual(by_provider["codex"]["session_uuid"], f"codex:{SHARED}")
        self.assertEqual(by_provider["codex"]["native_session_id"], SHARED)
        conn.close()

    def test_child_resume_reharvests_unchanged_parent(self):
        proj = self.add_project("child-resume")
        parent = proj / f"{CLAUDE_A}.jsonl"
        child = proj / CLAUDE_A / "subagents/agent-child.jsonl"
        write_jsonl(parent, [claude_user("parent")])
        write_jsonl(child, [claude_user("child before", uuid="child-u")])
        self.run_ledger("harvest")
        write_jsonl(child, [claude_user("child before", uuid="child-u"), claude_assistant("child after", uuid="child-a")])
        self.run_ledger("harvest")
        conn = self.connect()
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM messages WHERE content_text='child after'").fetchone()[0], 1)
        conn.close()
        self.assertIn("Skipped:    1", self.run_ledger("harvest").stdout)

    def test_malformed_child_preserves_parent_snapshot(self):
        proj = self.add_project("child-error")
        parent = proj / f"{CLAUDE_A}.jsonl"
        child = proj / CLAUDE_A / "subagents/agent-child.jsonl"
        write_jsonl(parent, [claude_user("parent good")])
        write_jsonl(child, [claude_user("child good", uuid="child-u")])
        self.run_ledger("harvest")
        write_jsonl(child, [claude_user("child partial", uuid="child-u"), "{broken"])
        result = self.run_ledger("harvest", check=False)
        self.assertEqual(result.returncode, 1)
        conn = self.connect()
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM messages WHERE content_text='child good'").fetchone()[0], 1)
        conn.close()

    def test_dry_run_does_not_create_database(self):
        self.run_ledger("harvest", "--dry-run")
        self.assertFalse(self.db.exists())

    def test_claude_export_filename_does_not_replace_source_id(self):
        proj = self.add_project("renamed")
        write_jsonl(proj / "renamed.jsonl", [claude_user("exported", sessionId=CLAUDE_A)])
        self.run_ledger("harvest")
        conn = self.connect()
        self.assertEqual(conn.execute("SELECT native_session_id FROM sessions").fetchone()[0], CLAUDE_A)
        conn.close()

    def test_codex_move_to_archive_and_event_order(self):
        source = self.codex / "sessions/renamed.jsonl"
        write_jsonl(source, [codex_session(CODEX_ID), codex_agent_message("one answer"), codex_assistant("one answer")])
        self.run_ledger("harvest", "--source", "codex", "--session", CODEX_ID)
        source.rename(self.codex / "archived_sessions/renamed.jsonl")
        self.run_ledger("harvest", "--source", "codex")
        conn = self.connect()
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0], 1)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM messages WHERE content_text='one answer'").fetchone()[0], 1)
        conn.close()

    def test_missing_timestamps_are_not_harvest_time(self):
        proj = self.add_project("untimed")
        row = claude_user("no source time")
        row.pop("timestamp")
        write_jsonl(proj / f"{CLAUDE_A}.jsonl", [row])
        self.run_ledger("harvest")
        conn = self.connect()
        self.assertEqual(conn.execute("SELECT timestamp FROM messages").fetchone()[0], "")
        self.assertEqual(conn.execute("SELECT started_at FROM sessions").fetchone()[0], "")
        conn.close()

    def test_version_one_database_migrates_additively(self):
        conn = self.connect()
        conn.executescript((ROOT / "tests/fixtures/schema-v1.sql").read_text())
        conn.execute("INSERT INTO sessions(session_uuid, source, started_at) VALUES ('preserved', 'claude-code', '2026-01-01')")
        conn.commit();conn.close()
        self.run_ledger("init")
        conn = self.connect()
        self.assertEqual(conn.execute("SELECT session_uuid FROM sessions").fetchone()[0], "preserved")
        self.assertIn("native_session_id", [r[1] for r in conn.execute("PRAGMA table_info(sessions)")])
        conn.close()

    def test_codex_tools_search_and_native_id(self):
        rollout = (
            self.codex
            / "archived_sessions"
            / "2025"
            / "12"
            / "01"
            / f"rollout-2025-12-01T09-00-00-{WRONG_ROLLOUT}.jsonl"
        )
        write_jsonl(
            rollout,
            [
                codex_session(CODEX_ID, extra_meta={"model": "gpt-5.2-codex"}),
                codex_user("codexsearchtoken please list files"),
                codex_function_call(
                    "call_shell_1",
                    "shell",
                    json.dumps({"command": ["ls", "-la"], "workdir": "/tmp/synth-app"}),
                ),
                codex_function_output("call_shell_1", "file.txt\nreadme.md\n"),
                codex_assistant("Listed the directory."),
                codex_agent_message("Listed the directory."),
                codex_tokens(),
            ],
        )
        self.run_ledger("harvest", "--source", "codex")
        conn = self.connect()
        session = conn.execute("SELECT * FROM sessions").fetchone()
        self.assertEqual(session["session_uuid"], f"codex:{CODEX_ID}")
        self.assertEqual(session["native_session_id"], CODEX_ID)
        self.assertEqual(session["provider"], "codex")
        self.assertNotIn(WRONG_ROLLOUT, session["session_uuid"])
        self.assertEqual(session["total_input_tokens"], 111)
        self.assertEqual(session["total_output_tokens"], 33)
        self.assertEqual(session["total_cache_read"], 2)
        assistants = conn.execute(
            "SELECT content_text FROM messages WHERE role = 'assistant' AND content_text IS NOT NULL"
        ).fetchall()
        listed = [r[0] for r in assistants if r[0] and "Listed the directory" in r[0]]
        self.assertEqual(len(listed), 1)
        tool = conn.execute("SELECT * FROM tool_uses").fetchone()
        self.assertEqual(tool["tool_use_id"], "codex:call_shell_1")
        self.assertEqual(tool["native_id"], "call_shell_1")
        self.assertEqual(tool["tool_name"], "shell")
        self.assertIn("ls", tool["command"])
        self.assertIn("file.txt", tool["result_text"])
        self.assertIn("workdir", tool["input_json"])
        conn.close()
        search = self.run_ledger("search", "codexsearchtoken")
        self.assertNotIn("No results for", search.stdout)
        self.assertIn("codexsearchtoken", search.stdout)

    def test_zero_files_is_not_complete_coverage(self):
        out = self.run_ledger("harvest", "--source", "all").stdout
        self.assertIn("Discovered: 0", out)
        self.assertIn("0 discovered files is not evidence of complete coverage", out)
        self.assertIn("available", out)

    def test_export_shared_record(self):
        proj = self.add_project("proj-export")
        write_jsonl(
            proj / f"{CLAUDE_A}.jsonl",
            [
                claude_user("export prompt"),
                claude_assistant(
                    "export reply",
                    tools=[
                        {
                            "type": "tool_use",
                            "id": "toolu_read_1",
                            "name": "Read",
                            "input": {"file_path": "/tmp/export.py"},
                        }
                    ],
                ),
                claude_tool_result("toolu_read_1", "print('hi')"),
            ],
        )
        self.run_ledger("harvest")
        exported = self.run_ledger("export", "--session", CLAUDE_A, "--pretty")
        records = json.loads(exported.stdout)
        self.assertEqual(len(records), 1)
        rec = records[0]
        self.assertEqual(rec["provider"], "claude-code")
        self.assertEqual(rec["session_id"], CLAUDE_A)
        self.assertEqual(rec["native_session_id"], CLAUDE_A)
        self.assertTrue(rec["source_path"].endswith(f"{CLAUDE_A}.jsonl"))
        self.assertTrue(any(m.get("text") == "export prompt" for m in rec["messages"]))
        tool_calls = []
        for msg in rec["messages"]:
            tool_calls.extend(msg.get("tool_calls") or [])
        self.assertEqual(tool_calls[0]["id"], "toolu_read_1")
        self.assertEqual(tool_calls[0]["input"]["file_path"], "/tmp/export.py")
        self.assertIn("print('hi')", tool_calls[0]["output"])

    def test_source_cli_choices_preserved(self):
        help_out = self.run_ledger("harvest", "--help").stdout
        self.assertIn("claude-code", help_out)
        self.assertIn("codex", help_out)
        self.assertIn("vault", help_out)
        self.assertIn("all", help_out)
        self.run_ledger("init")
        self.run_ledger("status")
        self.run_ledger("sessions")
        self.run_ledger("stats")
        self.run_ledger("files")


class ParserUnitTests(LedgerHarness):
    def test_detect_and_qualify(self):
        mod = self.load_module()
        claude_records = [claude_user("hi")]
        codex_records = [codex_session(CODEX_ID), codex_user("hi")]
        self.assertEqual(mod.detect_transcript_format(claude_records), "claude-code")
        self.assertEqual(mod.detect_transcript_format(codex_records), "codex")
        self.assertEqual(mod.detect_transcript_format([{"foo": 1}]), "unknown")
        self.assertEqual(mod.qualify_id("claude-code", SHARED), SHARED)
        self.assertEqual(mod.qualify_id("codex", SHARED), f"codex:{SHARED}")
        self.assertEqual(mod.qualify_id("codex", f"codex:{SHARED}"), f"codex:{SHARED}")
        self.assertEqual(mod.extract_codex_session_id(codex_records), CODEX_ID)
        self.assertIsNone(mod.extract_codex_session_id([{"type": "response_item", "payload": {}}]))


if __name__ == "__main__":
    unittest.main()
