"""Tests of sync.py: the kit renders whole for each vendor, refuses what a plugin must not hold, and --check sees drift.

Run from the kit's folder: py -3 -m unittest discover -s tests -v
"""

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIT))

import sync  # noqa: E402

FOUR = {"list_issues", "claim", "read_project", "submit_proposal"}


def small_kit(root: Path, command: str, fragment: str = "Fragment text.\n") -> tuple[Path, Path]:
    """A kit with one vendor and one command, and an empty plugin repository beside it."""
    kit = root / "kit"
    repo = root / "plugin"
    (kit / "commands").mkdir(parents=True)
    (kit / "fragments").mkdir()
    (kit / "vendors").mkdir()
    repo.mkdir()
    (kit / "VERSION").write_text("9.8.7\n", encoding="utf-8", newline="\n")
    (kit / "commands" / "do-it.md").write_text(command, encoding="utf-8", newline="\n")
    (kit / "fragments" / "part.md").write_text(fragment, encoding="utf-8", newline="\n")
    vendor = {
        "vendor": "test-agent",
        "agent": "Test Agent",
        "repository": "../plugin",
        "skillsDir": ".test/skills",
        "commandFile": "commands/{name}.md",
        "commandName": "/t:{name}",
        "toolMention": "`t__{tool}`",
        "toolGrant": "t__{tool}",
        "toolSeparator": " ",
        "arguments": "$ARGS",
        "configure": "configure it",
        "update": "update it",
        "frontmatter": [
            {"key": "description", "value": "{description}", "quoted": True},
            {"key": "argument-hint", "value": "{argument-hint}", "quoted": True},
            {"key": "allowed-tools", "value": "{tools}", "quoted": False},
        ],
        "versionFile": "KIT_VERSION",
        "manifest": {"path": "manifest.json", "versionKey": "version"},
    }
    (kit / "vendors" / "test-agent.json").write_text(json.dumps(vendor), encoding="utf-8")
    (repo / "manifest.json").write_text('{\n  "name": "t",\n  "version": "0.0.0"\n}\n', encoding="utf-8")
    return kit, repo


GOOD = "---\ndescription: Do it\ntools: claim\n---\nCall {{tool:claim}} with {{arguments}}.\n{{include:part}}\n"


class TheRealKitRendersWhole(unittest.TestCase):
    def test_every_vendor_renders_every_command_with_no_placeholder_left(self):
        for name in sync.vendor_names(KIT):
            vendor = sync.load_vendor(KIT, name)
            rendered = sync.render(KIT, vendor, sync.repository_of(KIT, vendor))
            commands = [path for path in rendered if path.endswith(".md")]
            self.assertEqual(len(commands), 3, f"{name} gets the three fetch commands, got {sorted(commands)}")
            for path, text in rendered.items():
                self.assertNotIn("{{", text, f"{name}'s {path} holds no placeholder the render left")

    def test_each_command_pre_allows_only_opowi_tools_it_names(self):
        vendor = sync.load_vendor(KIT, "claude-code")
        rendered = sync.render(KIT, vendor, sync.repository_of(KIT, vendor))
        for path, text in rendered.items():
            if not path.startswith("commands/"):
                continue
            line = next(row for row in text.splitlines() if row.startswith("allowed-tools:"))
            granted = line.removeprefix("allowed-tools:").split()
            tools = {grant.removeprefix("mcp__plugin_opovi_opovi__") for grant in granted}
            self.assertTrue(tools <= FOUR, f"{path} pre-allows only the four Opowi tools, got {granted}")
            self.assertTrue(all(g.startswith("mcp__plugin_opovi_opovi__") for g in granted),
                            f"{path} pre-allows only tools of the plugin's own server, got {granted}")

    def test_the_kit_version_reaches_the_claim_the_version_file_and_the_manifest(self):
        version = (KIT / "VERSION").read_text(encoding="utf-8").strip()
        vendor = sync.load_vendor(KIT, "claude-code")
        rendered = sync.render(KIT, vendor, sync.repository_of(KIT, vendor))
        self.assertIn(f'`kitVersion`: `"{version}"`', rendered["commands/fetch-single.md"],
                      "fetch-single claims with the kit's version")
        self.assertEqual(rendered["KIT_VERSION"], f"{version}\n", "KIT_VERSION holds the kit's version")
        manifest = json.loads(rendered[".claude-plugin/plugin.json"])
        self.assertEqual(manifest["version"], version, "plugin.json carries the kit's version")

    def test_the_shipped_claude_code_plugin_is_what_the_kit_makes(self):
        vendor = sync.load_vendor(KIT, "claude-code")
        repo = sync.repository_of(KIT, vendor)
        if not repo.is_dir():
            self.skipTest(f"no plugin repository at {repo}")
        self.assertEqual(sync.differences(KIT, vendor, repo), [],
                         "opovi-claude-code holds exactly what the kit makes; run py -3 sync.py")

    def test_every_rendered_command_sends_kit_version_and_holds_the_update_note_line(self):
        version = (KIT / "VERSION").read_text(encoding="utf-8").strip()
        self.assertEqual(version, "0.3.0", "the kit is bumped to 0.3.0")
        for name in sync.vendor_names(KIT):
            vendor = sync.load_vendor(KIT, name)
            rendered = sync.render(KIT, vendor, sync.repository_of(KIT, vendor))
            for path, text in rendered.items():
                if not path.endswith(".md"):
                    continue
                self.assertIn(
                    "Opovi <latest> is out (you run <running>): <repository>",
                    text,
                    f"{name}'s {path} holds the update note's line",
                )
                self.assertIn(
                    f'`kitVersion` set to `"{version}"`',
                    text,
                    f"{name}'s {path} carries the kit version for tool calls",
                )
                self.assertNotIn(
                    "`vendor` set to",
                    text,
                    f"{name}'s {path} sends no vendor argument on tool calls",
                )


class TheRenderRefuses(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.root)

    def refused(self, command: str, fragment: str = "Fragment text.\n") -> str:
        kit, repo = small_kit(self.root, command, fragment)
        vendor = sync.load_vendor(kit, "test-agent")
        with self.assertRaises(sync.SyncError) as raised:
            sync.render(kit, vendor, repo)
        return str(raised.exception)

    def test_an_unknown_placeholder_refuses_the_render(self):
        message = self.refused(GOOD.replace("{{arguments}}", "{{argumants}}"))
        self.assertIn("argumants", message, "the refusal names the unknown placeholder")

    def test_a_tool_outside_the_four_refuses_the_render(self):
        message = self.refused(GOOD.replace("tools: claim", "tools: claim run_shell"))
        self.assertIn("run_shell", message, "a command may name only the four Opowi tools")

    def test_a_tool_the_tools_line_leaves_out_refuses_the_render(self):
        message = self.refused(GOOD.replace("{{tool:claim}}", "{{tool:submit_proposal}}"))
        self.assertIn("submit_proposal", message, "a command mentions only the tools its tools line allows")

    def test_an_include_of_a_missing_fragment_refuses_the_render(self):
        message = self.refused(GOOD.replace("{{include:part}}", "{{include:gone}}"))
        self.assertIn("gone", message, "the refusal names the missing fragment")

    def test_a_command_with_no_description_refuses_the_render(self):
        message = self.refused(GOOD.replace("description: Do it\n", ""))
        self.assertIn("description", message, "every command carries a description")

    def test_an_include_that_includes_itself_refuses_the_render(self):
        message = self.refused(GOOD, fragment="Again {{include:part}}\n")
        self.assertIn("part", message, "an include cycle is refused, never rendered forever")


class CheckSeesDrift(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.kit, self.repo = small_kit(self.root, GOOD)
        self.vendor = sync.load_vendor(self.kit, "test-agent")

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_check_is_clean_right_after_a_write(self):
        sync.write(self.kit, self.vendor, self.repo)
        self.assertEqual(sync.differences(self.kit, self.vendor, self.repo), [],
                         "a plugin just written holds what the kit makes")

    def test_a_write_renders_the_command_for_the_vendor(self):
        sync.write(self.kit, self.vendor, self.repo)
        text = (self.repo / "commands" / "do-it.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith('---\ndescription: "Do it"\nallowed-tools: t__claim\n---\n'),
                        f"the vendor's frontmatter leads the command, with no argument-hint it lacks:\n{text}")
        self.assertIn("Call `t__claim` with $ARGS.", text, "tools and arguments take the vendor's own form")
        self.assertIn("Fragment text.", text, "an include brings the fragment in")
        self.assertNotIn(b"\r", (self.repo / "commands" / "do-it.md").read_bytes(), "a written file has LF endings")

    def test_check_names_a_plugin_file_that_differs_from_the_kit(self):
        sync.write(self.kit, self.vendor, self.repo)
        (self.repo / "commands" / "do-it.md").write_text("edited by hand\n", encoding="utf-8")
        found = sync.differences(self.kit, self.vendor, self.repo)
        self.assertTrue(any("commands/do-it.md" in line for line in found),
                        f"check names the command edited by hand, got {found}")

    def test_check_names_a_command_file_the_kit_no_longer_makes(self):
        sync.write(self.kit, self.vendor, self.repo)
        (self.repo / "commands" / "old.md").write_text("left over\n", encoding="utf-8")
        found = sync.differences(self.kit, self.vendor, self.repo)
        self.assertTrue(any("commands/old.md" in line for line in found),
                        f"check names a command the kit does not make, got {found}")

    def test_check_names_a_manifest_whose_version_is_not_the_kits(self):
        sync.write(self.kit, self.vendor, self.repo)
        (self.repo / "manifest.json").write_text('{\n  "name": "t",\n  "version": "0.0.1"\n}\n', encoding="utf-8")
        found = sync.differences(self.kit, self.vendor, self.repo)
        self.assertTrue(any("manifest.json" in line for line in found),
                        f"check names a manifest with another version, got {found}")

    def test_main_check_exits_1_on_drift_and_0_when_clean(self):
        sync.write(self.kit, self.vendor, self.repo)
        self.assertEqual(sync.main(["--check", "--kit", str(self.kit)]), 0, "--check passes on a clean plugin")
        (self.repo / "KIT_VERSION").write_text("0.0.0\n", encoding="utf-8")
        self.assertEqual(sync.main(["--check", "--kit", str(self.kit)]), 1, "--check fails on a drifted plugin")

    def test_a_missing_plugin_repository_is_an_error_not_a_skip(self):
        shutil.rmtree(self.repo)
        self.assertEqual(sync.main(["--kit", str(self.kit)]), 2, "a vendor whose repository is absent exits 2")


if __name__ == "__main__":
    unittest.main()
