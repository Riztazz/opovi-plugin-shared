"""Tests of the Codex vendor in opovi-agent-kit and the shipped opovi-codex plugin.

Run from the kit's folder: py -3 -B -m unittest discover -s tests -v
"""

import json
import sys
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIT))

import sync  # noqa: E402


class TheCodexVendorRendersWhole(unittest.TestCase):
    def test_codex_vendor_renders_three_skills_with_name_description_and_no_placeholders(self):
        vendor = sync.load_vendor(KIT, "codex")
        repo = sync.repository_of(KIT, vendor)
        rendered = sync.render(KIT, vendor, repo)
        expected_skills = {
            "fetch-list": "skills/fetch-list/SKILL.md",
            "fetch-single": "skills/fetch-single/SKILL.md",
            "fetch-all": "skills/fetch-all/SKILL.md",
        }
        for name, rel_path in expected_skills.items():
            self.assertIn(rel_path, rendered, f"codex render includes {rel_path}")
            text = rendered[rel_path]
            self.assertTrue(
                text.startswith(f"---\nname: {name}\ndescription: "),
                f"{rel_path} starts with Codex SKILL.md frontmatter (name and description)",
            )
            self.assertNotIn("{{", text, f"{rel_path} holds no unexpanded placeholder")
            self.assertIn("`vendor` is not `codex`", text, f"{rel_path} checks for vendor codex in opovi.json")
            if name != "fetch-list":
                self.assertIn(".agents/skills", text, f"{rel_path} reads world skills from .agents/skills")

    def test_codex_kit_version_reaches_claim_version_file_and_manifest(self):
        version = (KIT / "VERSION").read_text(encoding="utf-8").strip()
        vendor = sync.load_vendor(KIT, "codex")
        repo = sync.repository_of(KIT, vendor)
        rendered = sync.render(KIT, vendor, repo)
        self.assertIn(
            f'`kitVersion`: `"{version}"`',
            rendered["skills/fetch-single/SKILL.md"],
            "fetch-single claims with the kit's version",
        )
        self.assertEqual(rendered["KIT_VERSION"], f"{version}\n", "KIT_VERSION holds the kit's version")
        manifest = json.loads(rendered[".codex-plugin/plugin.json"])
        self.assertEqual(manifest["version"], version, ".codex-plugin/plugin.json carries the kit's version")

    def test_the_shipped_codex_plugin_is_what_the_kit_makes(self):
        vendor = sync.load_vendor(KIT, "codex")
        repo = sync.repository_of(KIT, vendor)
        if not repo.is_dir():
            self.skipTest(f"no plugin repository at {repo}")
        self.assertEqual(
            sync.differences(KIT, vendor, repo),
            [],
            "opovi-codex holds exactly what the kit makes; run py -3 sync.py --vendor codex",
        )

    def test_codex_config_example_sets_opovi_mcp_with_opovi_token(self):
        vendor = sync.load_vendor(KIT, "codex")
        repo = sync.repository_of(KIT, vendor)
        config_example = repo / "config.toml.example"
        self.assertTrue(config_example.is_file(), "opovi-codex ships config.toml.example")
        text = config_example.read_text(encoding="utf-8")
        self.assertIn("[mcp_servers.opovi]", text, "config.toml.example defines the [mcp_servers.opovi] table")
        self.assertIn("/api/plugins/ai-handoff/mcp", text, "config.toml.example points to /api/plugins/ai-handoff/mcp")
        self.assertIn("OPOVI_TOKEN", text, "config.toml.example reads the agent token from OPOVI_TOKEN")


if __name__ == "__main__":
    unittest.main()
