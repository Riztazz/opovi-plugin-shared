"""Writes the kit into each plugin repository beside it, or checks that each one holds what the kit makes.

    py -3 sync.py                     write every vendor's plugin
    py -3 sync.py --check             write nothing; exit 1 when a plugin differs from what the kit makes
    py -3 sync.py --vendor codex      only that vendor (repeatable)

A vendor is one file in vendors/. Each command in commands/ becomes one file in the vendor's plugin, with the
vendor's own frontmatter, tool names and argument form. Exit codes: 0 done or clean, 1 drift, 2 a kit or setup error.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parent
LOCAL_CONFIG = "plugins.local.json"
GITHUB_HTTPS_RE = re.compile(r"^https?://(?:[^/@]+@)?github\.com/([^/]+/[^/]+?)(?:\.git)?/?$", re.IGNORECASE)
GITHUB_SSH_RE = re.compile(r"^(?:git@github\.com:|ssh://git@github\.com/)([^/]+/[^/]+?)(?:\.git)?/?$", re.IGNORECASE)

# The only tools a command may name or pre-allow, all on the Opowi server (contract.md).
OPOWI_TOOLS = ("list_issues", "claim", "read_project", "submit_proposal")

PLACEHOLDER = re.compile(r"\{\{([a-z_]+)(?::([a-z0-9_-]+))?\}\}")
MAX_INCLUDE_DEPTH = 4


class SyncError(Exception):
    """The kit cannot be rendered as it stands, or a plugin repository cannot be reached."""


def vendor_names(kit: Path) -> list[str]:
    return sorted(path.stem for path in (kit / "vendors").glob("*.json"))


def load_vendor(kit: Path, name: str) -> dict:
    path = kit / "vendors" / f"{name}.json"
    if not path.is_file():
        raise SyncError(f"no vendor file {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def github_slug(url: str) -> str | None:
    """Return 'owner/name' from a GitHub https or ssh remote URL, or None."""
    cleaned = url.strip()
    for pattern in (GITHUB_HTTPS_RE, GITHUB_SSH_RE):
        match = pattern.match(cleaned)
        if match is not None:
            return match.group(1)
    return None


def origin_url(repo: Path) -> str | None:
    """Return the git origin URL of repo, or None when unavailable."""
    result = subprocess.run(
        ["git", "-c", "core.quotepath=false", "-C", str(repo), "remote", "get-url", "origin"],
        capture_output=True,
        timeout=10,
        check=False,
    )
    if result.returncode != 0:
        return None
    url = result.stdout.decode("utf-8", errors="replace").strip()
    return url or None


def verify_clone(name: str, repo: Path, expected: str) -> None:
    """Ensure repo exists and its git origin matches the expected GitHub owner/name."""
    if not repo.is_dir():
        raise SyncError(f"{name}: no plugin repository at {repo}")
    found = origin_url(repo)
    if found is None:
        raise SyncError(f"{name}: {repo} has no git origin, expected {expected}")
    slug = github_slug(found)
    if slug is None or slug.lower() != expected.lower():
        raise SyncError(f"{name}: {repo} has origin {found}, expected {expected}")


def load_local_plugins(kit: Path) -> dict[str, str]:
    """Load the git-ignored plugins.local.json mapping vendor names to clone paths."""
    path = kit / LOCAL_CONFIG
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SyncError(f"cannot read {LOCAL_CONFIG}: {error}") from error
    if not isinstance(data, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in data.items()):
        raise SyncError(f"{LOCAL_CONFIG} must be a JSON object mapping vendor names to paths")
    return data


def save_local_plugin(kit: Path, name: str, raw_path: str) -> None:
    """Persist one vendor's clone path to plugins.local.json atomically."""
    data = load_local_plugins(kit)
    data[name] = raw_path
    payload = (json.dumps(data, indent=2) + "\n").encode("utf-8")
    target = kit / LOCAL_CONFIG
    fd, tmp_name = tempfile.mkstemp(prefix=".plugins.local.", suffix=".tmp", dir=kit)
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
        os.replace(tmp_path, target)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


def resolve_clone_path(kit: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    return path.resolve() if path.is_absolute() else (kit / path).resolve()


def repository_of(
    kit: Path,
    vendor: dict,
    overrides: dict[str, str] | None = None,
    *,
    interactive: bool = False,
    check: bool = False,
) -> Path:
    """Resolve and verify the local clone for a vendor."""
    name = vendor["vendor"]
    expected = vendor["repository"]
    if overrides and name in overrides:
        repo = resolve_clone_path(kit, overrides[name])
        verify_clone(name, repo, expected)
        return repo

    local = load_local_plugins(kit)
    if name in local:
        repo = resolve_clone_path(kit, local[name])
        verify_clone(name, repo, expected)
        return repo

    repo_leaf = expected.split("/")[-1]
    sibling = kit.parent / repo_leaf
    default = f"../{repo_leaf}" if sibling.is_dir() else None
    if check or not interactive:
        suggestion = default if default is not None else "<path>"
        raise SyncError(f'{name}: no entry in {LOCAL_CONFIG} for {expected}; add:\n  "{name}": "{suggestion}"')

    print(f"Where is the clone of {expected} ({name})?")
    prompt = f"  [{default}]: " if default is not None else "  path: "
    answer = input(prompt).strip()
    if not answer:
        if default is None:
            raise SyncError(f"{name}: no path given for {expected}")
        answer = default
    repo = resolve_clone_path(kit, answer)
    verify_clone(name, repo, expected)
    save_local_plugin(kit, name, answer)
    print(f"Saved to {LOCAL_CONFIG}.")
    return repo


def kit_version(kit: Path) -> str:
    version = (kit / "VERSION").read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise SyncError(f"VERSION holds '{version}', not a semver such as 0.1.0")
    return version


def read_command(path: Path) -> tuple[dict[str, str], str]:
    """A kit command's header fields and its body. The header is `key: value` lines between two `---` lines."""
    text = path.read_text(encoding="utf-8")
    match = re.match(r"---\n(.*?)\n---\n", text, re.DOTALL)
    if match is None:
        raise SyncError(f"{path.name} starts with no --- header")
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        key, colon, value = line.partition(":")
        if not colon:
            raise SyncError(f"{path.name}: header line '{line}' is not 'key: value'")
        fields[key.strip()] = value.strip()
    if not fields.get("description"):
        raise SyncError(f"{path.name} has no description")
    tools = fields.get("tools", "").split()
    unknown = [tool for tool in tools if tool not in OPOWI_TOOLS]
    if unknown:
        raise SyncError(f"{path.name} names tools outside the four Opowi tools: {', '.join(unknown)}")
    return fields, text[match.end():]


def expand(kit: Path, vendor: dict, version: str, body: str, tools: list[str], where: str, seen: tuple) -> str:
    """The body with every placeholder replaced in the vendor's form, includes expanded."""

    def replace(match: re.Match) -> str:
        name, argument = match.group(1), match.group(2)
        if name == "include":
            if argument in seen or len(seen) >= MAX_INCLUDE_DEPTH:
                raise SyncError(f"{where}: include of '{argument}' runs in a cycle ({' > '.join(seen)})")
            fragment = kit / "fragments" / f"{argument}.md"
            if not fragment.is_file():
                raise SyncError(f"{where}: no fragment '{argument}' in fragments/")
            text = fragment.read_text(encoding="utf-8").rstrip("\n")
            return expand(kit, vendor, version, text, tools, f"fragments/{argument}.md", (*seen, argument))
        if name == "tool":
            if argument not in tools:
                raise SyncError(f"{where} names the tool '{argument}', which its command's tools line leaves out")
            return vendor["toolMention"].format(tool=argument)
        if name == "command":
            return vendor["commandName"].format(name=argument)
        simple = {
            "arguments": vendor["arguments"],
            "skills_dir": vendor["skillsDir"],
            "vendor": vendor["vendor"],
            "agent": vendor["agent"],
            "kit_version": version,
            "configure": vendor["configure"],
            "update": vendor["update"],
        }
        if name not in simple or argument is not None:
            raise SyncError(f"{where}: unknown placeholder '{match.group(0)}'")
        return simple[name]

    expanded = PLACEHOLDER.sub(replace, body)
    if "{{" in expanded:
        raise SyncError(f"{where}: a placeholder the render does not read is left: {expanded[expanded.index('{{'):][:40]}")
    return expanded


def frontmatter(vendor: dict, fields: dict[str, str], tools: list[str]) -> str:
    values = {**fields, "tools": vendor["toolSeparator"].join(vendor["toolGrant"].format(tool=t) for t in tools)}
    lines = ["---"]
    for entry in vendor["frontmatter"]:
        names = re.findall(r"\{([a-z-]+)\}", entry["value"])
        if any(not values.get(name) for name in names):
            continue
        value = re.sub(r"\{([a-z-]+)\}", lambda m: values[m.group(1)], entry["value"])
        lines.append(f"{entry['key']}: {json.dumps(value) if entry['quoted'] else value}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def render(kit: Path, vendor: dict, repo: Path) -> dict[str, str]:
    """Every file the kit makes in the vendor's plugin, by path relative to the plugin's root."""
    version = kit_version(kit)
    files: dict[str, str] = {}
    for path in sorted((kit / "commands").glob("*.md")):
        fields, body = read_command(path)
        tools = fields.get("tools", "").split()
        expanded = expand(kit, vendor, version, body, tools, f"commands/{path.name}", ())
        note = (
            f"<!-- Written by opovi-agent-kit's sync.py from commands/{path.name}, kit {version}. "
            "Change it there, never here. -->\n\n"
        )
        files[vendor["commandFile"].format(name=path.stem)] = frontmatter(vendor, {**fields, "name": path.stem}, tools) + note + expanded
    files[vendor["versionFile"]] = f"{version}\n"
    manifest = vendor.get("manifest")
    if manifest is not None:
        held = repo / manifest["path"]
        if not held.is_file():
            raise SyncError(f"no manifest at {held}; the plugin repository holds its own")
        data = json.loads(held.read_text(encoding="utf-8"))
        data[manifest["versionKey"]] = version
        files[manifest["path"]] = json.dumps(data, indent=2) + "\n"
    return files


def stale_commands(vendor: dict, repo: Path, made: dict[str, str]) -> list[str]:
    """Command files in the plugin's command folder that the kit no longer makes."""
    pattern = vendor["commandFile"]
    folder, _, leaf = pattern.rpartition("/")
    suffix = leaf.split("{name}")[-1]
    held = repo / folder if folder else repo
    if not held.is_dir():
        return []
    found = [f"{folder}/{p.name}" if folder else p.name for p in held.iterdir() if p.name.endswith(suffix)]
    return sorted(path for path in found if path not in made)


def differences(kit: Path, vendor: dict, repo: Path) -> list[str]:
    """One line per plugin file that is not what the kit makes, missing, or no longer made."""
    made = render(kit, vendor, repo)
    lines = []
    for path, text in made.items():
        held = repo / path
        if not held.is_file():
            lines.append(f"missing  {path}")
        elif held.read_bytes() != text.encode("utf-8"):
            lines.append(f"differs  {path}")
    lines += [f"stale    {path}" for path in stale_commands(vendor, repo, made)]
    return lines


def write(kit: Path, vendor: dict, repo: Path) -> list[str]:
    """Writes every file the kit makes, LF only, and answers the paths that changed. A stale file is left for a person."""
    changed = []
    for path, text in render(kit, vendor, repo).items():
        target = repo / path
        data = text.encode("utf-8")
        if target.is_file() and target.read_bytes() == data:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        changed.append(path)
    return changed


def parse_plugin_overrides(items: list[str], available: list[str]) -> dict[str, str]:
    overrides: dict[str, str] = {}
    for item in items:
        name, sep, raw_path = item.partition("=")
        if not sep or not name or not raw_path:
            raise SyncError(f"--plugin expects <vendor>=<path>, got {item!r}")
        if name not in available:
            raise SyncError(f"unknown vendor {name!r} in --plugin")
        overrides[name] = raw_path
    return overrides


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Write the kit into each plugin repository, or check them.")
    parser.add_argument("--check", action="store_true", help="write nothing; exit 1 when a plugin differs")
    parser.add_argument("--vendor", action="append", help="only this vendor (repeatable)")
    parser.add_argument(
        "--plugin",
        action="append",
        default=[],
        metavar="VENDOR=PATH",
        help="override one vendor's clone path for this run without saving",
    )
    parser.add_argument("--kit", type=Path, default=KIT_ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    kit = args.kit.resolve()
    try:
        available = vendor_names(kit)
        overrides = parse_plugin_overrides(args.plugin, available)
        names = args.vendor or available
        interactive = sys.stdin.isatty()
        drift = False
        for name in names:
            vendor = load_vendor(kit, name)
            repo = repository_of(kit, vendor, overrides, interactive=interactive, check=args.check)
            if args.check:
                found = differences(kit, vendor, repo)
                for line in found:
                    print(f"{name}: {line}")
                drift = drift or bool(found)
                print(f"{name}: {'differs from the kit' if found else 'clean'}")
            else:
                changed = write(kit, vendor, repo)
                for path in changed:
                    print(f"{name}: wrote {path}")
                for path in stale_commands(vendor, repo, render(kit, vendor, repo)):
                    print(f"{name}: stale {path}, which the kit no longer makes; remove it by hand")
                    drift = True
                print(f"{name}: {len(changed)} files written")
        return 1 if drift else 0
    except SyncError as error:
        print(f"sync: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
