"""Tests of the Antigravity vendor: the kit renders the three commands as Antigravity skills, and opovi-antigravity holds them.

Run from the kit's folder: py -3 -m unittest discover -s tests -v
"""

import json
import re
import sys
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIT))

import sync  # noqa: E402

COMMANDS = ("fetch-all", "fetch-list", "fetch-single")
FOUR = {"list_issues", "claim", "read_project", "submit_proposal"}


def vendor_and_repo():
    vendor = sync.load_vendor(KIT, "antigravity")
    return vendor, sync.repository_of(KIT, vendor)


def header_of(text: str) -> dict[str, str]:
    match = re.match(r"---\n(.*?)\n---\n", text, re.DOTALL)
    assert match is not None, "the file starts with a --- header"
    return dict(line.split(": ", 1) for line in match.group(1).splitlines())


class TheKitRendersSkills(unittest.TestCase):
    def setUp(self):
        self.vendor, self.repo = vendor_and_repo()
        self.made = sync.render(KIT, self.vendor, self.repo)

    def test_each_command_becomes_one_skill_in_a_folder_of_its_own_name(self):
        skills = sorted(path for path in self.made if path.startswith("skills/"))
        self.assertEqual(skills, [f"skills/opovi-{name}/SKILL.md" for name in COMMANDS])

    def test_a_skill_name_equals_its_folder_and_only_documented_fields_are_set(self):
        for path, text in self.made.items():
            if not path.startswith("skills/"):
                continue
            header = header_of(text)
            self.assertEqual(header["name"], path.split("/")[1], f"{path}: the name must match the parent directory")
            self.assertEqual(set(header), {"name", "description", "disable-model-invocation"}, path)
            self.assertEqual(header["disable-model-invocation"], "true", f"{path}: a fetch starts only when typed")

    def test_no_skill_holds_another_vendors_words(self):
        for path, text in self.made.items():
            if not path.startswith("skills/"):
                continue
            for word in ("$ARGUMENTS", "mcp__plugin", "Claude Code", "/opovi:", ".claude/skills", "allowed-tools"):
                self.assertNotIn(word, text, f"{path} holds no {word}")
            self.assertNotIn("{{", text, f"{path} holds no placeholder the render left")

    def test_each_skill_names_the_server_and_only_the_four_tools(self):
        for path, text in self.made.items():
            if not path.startswith("skills/"):
                continue
            self.assertIn("`opovi_opovi` MCP server", text, f"{path} says where its tools live")
            named = set(re.findall(r"`([a-z_]+)` on the `opovi_opovi` MCP server", text))
            self.assertTrue(named and named <= FOUR, f"{path} names only the four Opovi tools, got {named}")

    def test_the_skills_read_world_skills_from_the_agents_folder(self):
        text = self.made["skills/opovi-fetch-single/SKILL.md"]
        self.assertIn(".agents/skills/<name>/SKILL.md", text)
        self.assertIn('vendor` is not `antigravity`', text)

    def test_the_argument_reaches_fetch_single_as_the_text_after_its_name(self):
        text = self.made["skills/opovi-fetch-single/SKILL.md"]
        self.assertIn("the text after the command name in the person's message", text)

    def test_fetch_list_points_at_the_commands_as_antigravity_types_them(self):
        text = self.made["skills/opovi-fetch-list/SKILL.md"]
        self.assertIn("`/opovi-fetch-single <number or id>`", text)
        self.assertIn("`/opovi-fetch-all`", text)

    def test_the_manifest_and_the_version_file_carry_the_kits_version(self):
        version = (KIT / "VERSION").read_text(encoding="utf-8").strip()
        self.assertEqual(self.made["KIT_VERSION"], f"{version}\n")
        self.assertEqual(json.loads(self.made["plugin.json"])["version"], version)


class TheShippedPluginIsSound(unittest.TestCase):
    def setUp(self):
        self.vendor, self.repo = vendor_and_repo()
        if not self.repo.is_dir():
            self.skipTest(f"no plugin repository at {self.repo}")

    def read_json(self, name: str) -> dict:
        return json.loads((self.repo / name).read_text(encoding="utf-8"))

    def test_opovi_antigravity_holds_exactly_what_the_kit_makes(self):
        self.assertEqual(sync.differences(KIT, self.vendor, self.repo), [],
                         "opovi-antigravity holds exactly what the kit makes; run py -3 sync.py")

    def test_the_manifest_names_a_kebab_case_plugin(self):
        manifest = self.read_json("plugin.json")
        self.assertRegex(manifest["name"], r"^[a-z0-9]+(-[a-z0-9]+)*$")
        self.assertEqual(manifest["name"], "opovi", "the MCP namespace opovi_opovi in the skills follows from this name")

    def test_the_mcp_server_signs_in_with_the_token_variable_over_the_opovi_endpoint(self):
        server = self.read_json("mcp_config.json")["mcpServers"]["opovi"]
        self.assertEqual(server["serverUrl"], "${OPOVI_SERVER_URL}/api/plugins/ai-handoff/mcp")
        self.assertEqual(server["headers"], {"Authorization": "Bearer ${OPOVI_TOKEN}"})

    def test_the_two_variables_are_declared_and_every_variable_used_is_declared(self):
        config = self.read_json("mcp_config.json")
        server = config["mcpServers"]["opovi"]
        declared = [variable["name"] for variable in server["variables"]]
        self.assertEqual(declared, ["OPOVI_SERVER_URL", "OPOVI_TOKEN"])
        for variable in server["variables"]:
            self.assertTrue(variable.get("title") and variable.get("description"), f"{variable['name']} is explained")
        used = set(re.findall(r"\$\{([A-Z_]+)\}", json.dumps(config)))
        self.assertEqual(used, set(declared), "the config uses exactly the variables it declares")

    def test_only_the_four_tools_are_enabled_and_no_token_is_written_down(self):
        server = self.read_json("mcp_config.json")["mcpServers"]["opovi"]
        self.assertEqual(set(server["enabledTools"]), FOUR)
        for name in ("mcp_config.json", "plugin.json"):
            text = (self.repo / name).read_text(encoding="utf-8")
            self.assertNotRegex(text, r"Bearer (?!\$\{)", f"{name} holds no literal token")

    def test_the_plugin_holds_no_hook_and_no_script(self):
        for name in ("hooks.json", "scripts", "commands", "hooks"):
            self.assertFalse((self.repo / name).exists(), f"{name} stays out of the plugin")


if __name__ == "__main__":
    unittest.main()
