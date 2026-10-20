#!/usr/bin/env python3
"""Partition: project-scoped Codex setup and inspectable personal context. Python 3.11+."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import uuid

VERSION = "1.1.0"
BEGIN = "<!-- partition:begin -->"
END = "<!-- partition:end -->"
BLOCK = f"{BEGIN}\nRead `.partition/INSTRUCTIONS.md` for Partition workflows and context loading.\n{END}"
IGNORE = "# partition:begin\n.partition/private/\n.partition/state.json\n.partition/backups/\n# partition:end"
DEFAULTS = {
    "fast": {"model": "gpt-6-luna", "effort": "high"},
    "balanced": {"model": "gpt-6.1-sol", "effort": "low"},
    "deep": {"model": "gpt-6.1-sol", "effort": "high"},
    "frontier": {"model": "gpt-6-astra", "effort": "low"},
}


class PartitionError(Exception):
    pass


def safe_path(root: Path, relative: str) -> Path:
    """Reject traversal and symlinked paths before reading or modifying managed data."""
    rel = Path(relative)
    if rel.is_absolute() or not rel.parts or any(p in ("..", ".git") for p in rel.parts):
        raise PartitionError(f"Unsafe path: {relative}")
    current = root
    for part in rel.parts:
        current = current / part
        if current.is_symlink():
            raise PartitionError(f"Symlink is not supported here: {current}")
    if not current.resolve().is_relative_to(root.resolve()):
        raise PartitionError(f"Path escapes project: {relative}")
    return current


def write(path: Path, content: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = content.encode() if isinstance(content, str) else content
    fd, temp = tempfile.mkstemp(prefix=".partition-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(path: Path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise PartitionError(f"Cannot read valid JSON from {path}: {exc}") from exc


def dump(value) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def project(value: str) -> Path:
    root = Path(value).expanduser().resolve()
    if not root.is_dir():
        raise PartitionError(f"Project directory does not exist: {root}")
    return root


def state(root: Path) -> dict:
    path = safe_path(root, ".partition/state.json")
    if not path.exists():
        raise PartitionError("Partition is not installed here. Run init first.")
    data = read_json(path)
    if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("files"), dict):
        raise PartitionError("Unsupported or invalid installation manifest.")
    for rel, entry in data["files"].items():
        safe_path(root, rel)
        if not isinstance(entry, dict) or not isinstance(entry.get("sha256"), str):
            raise PartitionError("Invalid managed file entry.")
        if entry.get("backup"):
            if not isinstance(entry["backup"], str) or not entry["backup"].startswith(".partition/backups/"):
                raise PartitionError("Invalid backup location.")
            safe_path(root, entry["backup"])
    return data


def templates() -> dict[str, bytes]:
    base = Path(__file__).resolve().parent / "assets"
    if not base.is_dir():
        raise PartitionError("Install/update from the cloned repository's partition.py.")
    result = {}
    for file in sorted(base.rglob("*")):
        if file.is_file():
            rel = file.relative_to(base).as_posix()
            result[rel] = file.read_bytes()
    result[".partition/partition.py"] = Path(__file__).read_bytes()
    return result


def ensure_marker(text: str, begin: str, end: str, block: str) -> str:
    if text.count(begin) != text.count(end) or text.count(begin) > 1:
        raise PartitionError("Malformed managed markers; repair before installing.")
    if begin in text:
        start, stop = text.index(begin), text.index(end)
        if stop < start:
            raise PartitionError("Managed markers are out of order.")
        if text[start:stop + len(end)] != block:
            raise PartitionError("Managed instruction block was edited; preserve or repair it first.")
        return text
    return text + ("\n\n" if text and not text.endswith("\n\n") else "") + block + "\n"


def init(root: Path) -> dict:
    override = safe_path(root, "AGENTS.override.md")
    if override.exists() and override.read_text().strip():
        raise PartitionError("AGENTS.override.md takes precedence over AGENTS.md. Integrate Partition manually or move the override before installing.")
    manifest_path = safe_path(root, ".partition/state.json")
    manifest = state(root) if manifest_path.exists() else {"version": 1, "files": {}}
    desired = templates()
    # Preflight all destinations and blocks before any changes.
    planned = []
    for rel, content in desired.items():
        dest = safe_path(root, rel)
        old = manifest["files"].get(rel)
        if old and dest.exists() and digest(dest.read_bytes()) != old["sha256"]:
            if dest.read_bytes() == content:
                continue
            raise PartitionError(f"Locally edited managed file preserved: {rel}. Reconcile before updating.")
        if not old and dest.exists() and dest.read_bytes() != content:
            raise PartitionError(f"Existing file preserved: {rel}. Move it aside before installing.")
        planned.append((rel, dest, content))
    for rel, begin, end, block in (("AGENTS.md", BEGIN, END, BLOCK),
                                  (".gitignore", "# partition:begin", "# partition:end", IGNORE)):
        dest = safe_path(root, rel)
        content = dest.read_text() if dest.exists() else ""
        new = ensure_marker(content, begin, end, block)
        planned.append((rel, dest, new.encode()))
    private = safe_path(root, ".partition/private")
    for rel in ("preferences.md", "instructions.md", "index.md", "references", "projects", "memories"):
        safe_path(root, ".partition/private/" + rel)
    changed = []
    for rel, dest, content in planned:
        old = manifest["files"].get(rel)
        if dest.exists() and dest.read_bytes() == content:
            if old is None:
                # Preexisting identical files are not owned and will not be removed.
                continue
            continue
        entry = dict(old or {})
        if old is None and dest.exists():
            backup_rel = ".partition/backups/" + uuid.uuid4().hex
            write(safe_path(root, backup_rel), dest.read_bytes())
            entry["backup"] = backup_rel
        write(dest, content)
        entry["sha256"] = digest(content)
        manifest["files"][rel] = entry
        changed.append(rel)
    private.mkdir(parents=True, exist_ok=True)
    for folder in ("references", "projects", "memories"):
        (private / folder).mkdir(exist_ok=True)
    starters = {
        "preferences.md": "# My preferences\n\nAdd your preferred tone, detail level, working style, and accessibility needs here. This file contains preferences, not facts to invent.\n",
        "instructions.md": "# My instructions\n\nAdd your personal working instructions here. Keep source documents and examples in references/.\n",
        "index.md": "# My context index\n\nList relevant reference and project files with a short description of when to read them. Paths are relative to this private directory.\n\nExample: references/voice.md — writing samples; use only when matching my voice.\n",
    }
    for rel, content in starters.items():
        dest = private / rel
        if not dest.exists():
            write(dest, content)
    write(manifest_path, dump(manifest))
    return {"installed": str(root), "changed": changed, "private_context": str(private)}


def uninstall(root: Path) -> dict:
    manifest = state(root)
    preserved, removed = [], []
    for rel, entry in manifest["files"].items():
        dest = safe_path(root, rel)
        if rel == ".gitignore":
            # Private data survives uninstall; its exclusion must survive too.
            continue
        if not dest.exists():
            continue
        raw = dest.read_bytes()
        if digest(raw) == entry["sha256"]:
            if entry.get("backup"):
                write(dest, safe_path(root, entry["backup"]).read_bytes())
            else:
                dest.unlink()
            removed.append(rel)
        elif rel in ("AGENTS.md", ".gitignore"):
            block = BLOCK if rel == "AGENTS.md" else IGNORE
            text = raw.decode()
            if text.count(block) == 1:
                write(dest, text.replace(block, "", 1))
                removed.append(rel + " (managed block only)")
            else:
                preserved.append(rel)
        else:
            preserved.append(rel)
    # Retain the manifest when edited package files remain: a future update must not adopt them.
    if not preserved:
        safe_path(root, ".partition/state.json").unlink()
    return {"removed": removed, "preserved": preserved, "retained": [".gitignore privacy exclusions"],
            "note": "Private context and backups are retained. No global Codex settings were changed."}


def policies(root: Path) -> dict:
    data = read_json(safe_path(root, ".partition/models.json"))
    if not isinstance(data, dict) or set(data) != set(DEFAULTS):
        raise PartitionError("models.json must contain fast, balanced, deep, and frontier policies.")
    for key, value in data.items():
        if not isinstance(value, dict) or not isinstance(value.get("model"), str) or not re.fullmatch(r"[\w./:-]+", value["model"]):
            raise PartitionError(f"Invalid model policy: {key}")
        if value.get("effort") not in {"low", "medium", "high", "xhigh", "max", "ultra"}:
            raise PartitionError(f"Invalid reasoning effort: {key}")
    return data


def route(prompt: str, mode: str = "auto") -> dict:
    """Explainable preview hints, not an LLM classifier or a permission boundary."""
    software = bool(re.search(r"\b(code|coding|debug|bug|function|python|javascript|typescript|repository|repo|sql|api|compiler|unit tests?|git|software)\b", prompt, re.I))
    general = bool(re.search(r"\b(essay|poem|story|letter|email|schedule|trip|meal|learn|research|spreadsheet|presentation|user guide)\b", prompt, re.I))
    area = mode if mode != "auto" else ("mixed" if software and general else "software" if software else "general")
    return {"work_area_hint": area, "execution": "current agent; workers only when justified",
            "note": "Keyword hint only. Codex decides the actual workflow from the complete request."}


def catalog() -> dict:
    if not shutil.which("codex"):
        raise PartitionError("Codex CLI is missing. Install it and sign in with ChatGPT first.")
    try:
        result = subprocess.run(["codex", "debug", "models"], capture_output=True, text=True, timeout=30)
        if result.returncode:
            raise PartitionError("Codex model catalog failed. Run codex debug models directly for details.")
        data = json.loads(result.stdout)
        models = data.get("models", []) if isinstance(data, dict) else data
        return {m.get("slug", m.get("id")): m for m in models}
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        raise PartitionError(f"Could not inspect Codex model catalog: {exc}") from exc


def check_model(models: dict, model: str, effort: str) -> None:
    if model not in models:
        raise PartitionError(f"Model {model} is absent from the Codex catalog. Edit .partition/models.json or choose --model.")
    levels = models[model].get("supported_reasoning_levels", [])
    allowed = {level.get("effort") if isinstance(level, dict) else level for level in levels}
    if allowed and effort not in allowed:
        raise PartitionError(f"{model} does not list reasoning effort {effort}; supported: {sorted(allowed)}")


def doctor(root: Path, online: bool = False) -> dict:
    manifest = state(root)
    changed = [rel for rel, entry in manifest["files"].items()
               if not safe_path(root, rel).is_file() or digest(safe_path(root, rel).read_bytes()) != entry["sha256"]]
    for rel, block in (("AGENTS.md", BLOCK), (".gitignore", IGNORE)):
        if rel in changed and safe_path(root, rel).is_file() and block in safe_path(root, rel).read_text():
            changed.remove(rel)  # User-owned text outside the managed block is expected.
    errors = []
    worker_policies = []
    role_files = sorted((root / ".codex/agents").glob("partition_*.toml"))
    for rel in role_files:
        safe_path(root, rel.relative_to(root).as_posix())
        agent = tomllib.loads(rel.read_text())
        if not all(isinstance(agent.get(k), str) and agent[k].strip() for k in ("name", "description", "developer_instructions")):
            errors.append(f"Invalid custom agent: {rel.name}")
        if any(k in agent for k in ("sandbox_mode", "approval_policy", "model_provider", "mcp_servers")):
            errors.append(f"Unsupported agent permission/provider override: {rel.name}")
        if not re.fullmatch(r"partition_[a-z0-9_]+", agent.get("name", "")):
            errors.append(f"Invalid tool-compatible agent name: {rel.name}")
        if "model" in agent:
            worker_policies.append({"model": agent["model"], "effort": agent.get("model_reasoning_effort", "low")})
    config = policies(root)
    if BLOCK not in safe_path(root, "AGENTS.md").read_text():
        errors.append("AGENTS.md is missing the Partition instruction block.")
    if IGNORE not in safe_path(root, ".gitignore").read_text():
        errors.append(".gitignore is missing the private-context exclusions.")
    tracked_private = []
    git = subprocess.run(["git", "-C", str(root), "ls-files", "--", ".partition/private"], capture_output=True, text=True) if shutil.which("git") else None
    if git and git.returncode == 0:
        tracked_private = git.stdout.splitlines()
    if tracked_private:
        errors.append("Private context is already tracked by Git; ignore rules do not untrack existing files.")
    info = {"version": VERSION, "project": str(root), "errors": errors,
            "locally_changed_managed_files": changed, "policies": config,
            "codex_cli": bool(shutil.which("codex")),
            "note": "Local edits are preserved. Catalog presence is not proof of account entitlement."}
    if online:
        models = catalog()
        for policy in list(config.values()) + worker_policies:
            try:
                check_model(models, policy["model"], policy["effort"])
            except PartitionError as exc:
                errors.append(str(exc))
        info["catalog_checked"] = True
    return info


def memory_dir(root: Path) -> Path:
    state(root)
    return safe_path(root, ".partition/private/memories")


def memory_records(root: Path) -> list[dict]:
    folder = memory_dir(root)
    records = []
    for file in sorted(folder.glob("*.json")):
        safe_path(root, file.relative_to(root).as_posix())
        record = read_json(file)
        if not isinstance(record, dict) or record.get("id") != file.stem or not isinstance(record.get("text"), str):
            raise PartitionError(f"Invalid memory record: {file.name}")
        records.append(record)
    return records


def memory_add(root: Path, text: str, scope: str, source: str, kind: str) -> dict:
    folder = memory_dir(root)
    if not text.strip():
        raise PartitionError("Memory text cannot be empty.")
    record = {"id": uuid.uuid4().hex, "text": text.strip(), "scope": scope,
              "source": source, "kind": kind, "created_at": datetime.now(timezone.utc).isoformat()}
    write(folder / (record["id"] + ".json"), dump(record))
    return record


def memory_delete(root: Path, ident: str) -> dict:
    if not re.fullmatch(r"[a-f0-9]{32}", ident):
        raise PartitionError("Use the full memory ID from memory list/search.")
    dest = memory_dir(root) / (ident + ".json")
    safe_path(root, dest.relative_to(root).as_posix())
    if not dest.is_file():
        raise PartitionError("Memory ID not found.")
    dest.unlink()
    return {"deleted": ident}


def context_search(root: Path, query: str, scope: str | None = None, limit: int = 5) -> list[dict]:
    terms = set(re.findall(r"\w+", query.casefold()))
    if not terms:
        return []
    candidates = []
    for record in memory_records(root):
        if record.get("scope", "global") not in ("global", scope):
            continue
        candidates.append({"source": f"memory:{record['id']}", "text": record["text"],
                           "scope": record.get("scope"), "kind": record.get("kind")})
    private = safe_path(root, ".partition/private")
    # Match snippets, not whole libraries. Do not follow symlinks or parse executable formats.
    for file in sorted(private.rglob("*.md")):
        rel = file.relative_to(root).as_posix()
        relative = file.relative_to(private)
        if relative.parts[0] in {"onboarding", "onboarding-runtime"}:
            continue  # Draft uploads, unchecked imports, backups, and the setup environment are not active context.
        if file.is_symlink() or any((private / parent).is_symlink() for parent in relative.parents):
            continue
        safe_path(root, rel)
        if file.stat().st_size > 256_000:
            continue
        file_scope = None
        parts = file.relative_to(private).parts
        if parts[0] == "projects" and len(parts) > 2:
            file_scope = parts[1]
            if scope != file_scope:
                continue
        for number, line in enumerate(file.read_text().splitlines(), 1):
            if line.strip():
                candidates.append({"source": f"{rel}:{number}", "text": line[:1200], "scope": file_scope})
    scored = []
    for item in candidates:
        words = set(re.findall(r"\w+", item["text"].casefold()))
        score = len(words & terms)
        if score:
            scored.append((score, item))
    scored.sort(key=lambda pair: -pair[0])
    return [{"score": score, **item} for score, item in scored[:limit]]


def launch_command(root: Path, args) -> tuple[list[str], dict]:
    config = policies(root)
    policy = config[args.quality]
    model, effort = args.model or policy["model"], args.effort or policy["effort"]
    hint = route(args.prompt or "", args.mode)
    command = ["codex", "--ask-for-approval", "on-request", "--enable", "multi_agent_v2"]
    if args.exec:
        command += ["exec", "--skip-git-repo-check"]
    command += ["--cd", str(root), "--model", model, "-c", f'model_reasoning_effort={json.dumps(effort)}',
                "--sandbox", "read-only" if args.read_only else "workspace-write",
                "-c", "agents.max_concurrent_threads_per_session=2"]
    # Explicit per-invocation role declarations work even before a project's
    # .codex/config.toml is trusted. Never edit the user's global trust settings.
    for file in sorted((root / ".codex/agents").glob("partition_*.toml")):
        safe_path(root, file.relative_to(root).as_posix())
        role = tomllib.loads(file.read_text())
        name = role.get("name", "")
        if not re.fullmatch(r"partition_[a-z0-9_]+", name):
            raise PartitionError(f"Invalid role name: {name}")
        command += ["-c", f'agents.{name}.description={json.dumps(role["description"])}',
                    "-c", f'agents.{name}.config_file={json.dumps(str(file))}']
    if args.search:
        # exec does not expose --search; use the documented config key for both clients.
        command += ["-c", 'web_search="live"']
    prompt = (f"Use Partition from .partition/INSTRUCTIONS.md. Work area preference: {args.mode}. "
              "Handle simple work directly. Read .partition/private/preferences.md and instructions.md; "
              "consult the private index and search context only when relevant. "
              "Do not claim a reference or memory was read unless you actually read it.")
    if args.read_only:
        prompt += " Analysis-only session: do not edit files or perform external mutations."
    if args.prompt:
        prompt += "\n\nUser request:\n" + args.prompt
    command.append(prompt)
    return command, {**hint, "model": model, "effort": effort,
                     "sandbox": "read-only" if args.read_only else "workspace-write"}


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--version", action="version", version=VERSION)
    sub = p.add_subparsers(dest="command", required=True)
    for name in ("init", "uninstall", "doctor", "context", "run", "memory"):
        command = sub.add_parser(name)
        command.add_argument("--project", default=".", help="Existing project directory (default: current directory)")
        if name == "doctor":
            command.add_argument("--check-models", action="store_true", help="Inspect the Codex model catalog; does not generate tokens")
        elif name == "context":
            command.add_argument("query")
            command.add_argument("--scope")
            command.add_argument("--limit", type=int, choices=range(1, 21), default=5)
        elif name == "run":
            command.add_argument("prompt", nargs="?")
            command.add_argument("--mode", choices=("auto", "general", "software"), default="auto")
            command.add_argument("--quality", choices=tuple(DEFAULTS), default="balanced")
            command.add_argument("--model")
            command.add_argument("--effort", choices=("low", "medium", "high", "xhigh", "max", "ultra"))
            command.add_argument("--read-only", action="store_true")
            command.add_argument("--search", action="store_true")
            command.add_argument("--exec", action="store_true", help="One non-interactive run instead of an interactive session")
            command.add_argument("--dry-run", action="store_true", help="Preview without launching Codex or checking its model catalog")
        elif name == "memory":
            actions = command.add_subparsers(dest="action", required=True)
            add = actions.add_parser("add")
            add.add_argument("text")
            add.add_argument("--scope", default="global")
            add.add_argument("--source", default="user")
            add.add_argument("--kind", choices=("user-stated", "inferred"), default="user-stated")
            actions.add_parser("list")
            delete = actions.add_parser("delete")
            delete.add_argument("id")
    return p


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    try:
        root = project(args.project)
        if args.command == "init":
            result = init(root)
        elif args.command == "uninstall":
            result = uninstall(root)
        elif args.command == "doctor":
            result = doctor(root, args.check_models)
            print(dump(result), end="")
            return 1 if result["errors"] else 0
        elif args.command == "context":
            result = context_search(root, args.query, args.scope, args.limit)
        elif args.command == "memory":
            if args.action == "add":
                result = memory_add(root, args.text, args.scope, args.source, args.kind)
            elif args.action == "delete":
                result = memory_delete(root, args.id)
            else:
                result = memory_records(root)
        else:
            state(root)
            command, preview = launch_command(root, args)
            if args.dry_run:
                result = {**preview, "argv": command}
            else:
                check_model(catalog(), preview["model"], preview["effort"])
                print(dump(preview), file=sys.stderr, end="")
                return subprocess.run(command).returncode
        print(dump(result), end="")
        return 0
    except (PartitionError, OSError, ValueError, tomllib.TOMLDecodeError) as exc:
        print(f"partition: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
