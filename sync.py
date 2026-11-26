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
import re
import sys
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parent

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


def repository_of(kit: Path, vendor: dict) -> Path:
    return (kit / vendor["repository"]).resolve()


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


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Write the kit into each plugin repository, or check them.")
    parser.add_argument("--check", action="store_true", help="write nothing; exit 1 when a plugin differs")
    parser.add_argument("--vendor", action="append", help="only this vendor (repeatable)")
    parser.add_argument("--kit", type=Path, default=KIT_ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    kit = args.kit.resolve()
    try:
        names = args.vendor or vendor_names(kit)
        drift = False
        for name in names:
            vendor = load_vendor(kit, name)
            repo = repository_of(kit, vendor)
            if not repo.is_dir():
                raise SyncError(f"{name}: no plugin repository at {repo}")
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
