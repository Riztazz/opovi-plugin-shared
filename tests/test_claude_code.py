"""Tests of the Claude Code vendor's configure words: the steps a refusal and the README give for setting a token.

Run from the kit's folder: py -3 -m unittest discover -s tests -v
"""

import json
import sys
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIT))

import sync  # noqa: E402

COMMANDS = ("fetch-all", "fetch-list", "fetch-single")
STDIN_LINE = "claude plugin configure opovi@opovi --values-stdin"


def vendor_and_repo():
    vendor = sync.load_vendor(KIT, "claude-code")
    return vendor, sync.repository_of(KIT, vendor)


class TheRefusalsNameAWayThatWorks(unittest.TestCase):
    def setUp(self):
        self.vendor, self.repo = vendor_and_repo()
        self.made = sync.render(KIT, self.vendor, self.repo)

    def test_no_command_tells_a_person_to_type_slash_plugin_configure(self):
        for name in COMMANDS:
            text = self.made[f"commands/{name}.md"]
            self.assertNotIn("/plugin configure", text, f"{name} sends a person to a command the desktop app does not run")

    def test_each_command_names_the_stdin_line_for_a_new_token_in_both_refusals(self):
        for name in COMMANDS:
            text = self.made[f"commands/{name}.md"]
            self.assertEqual(text.count(STDIN_LINE), 2, f"{name} gives the terminal line in the token and the address refusal")

    def test_each_command_names_the_desktop_apps_settings_tab(self):
        for name in COMMANDS:
            self.assertIn("Settings tab in the desktop app", self.made[f"commands/{name}.md"], f"{name} says where the desktop app keeps the settings")

    def test_the_address_refusal_hands_over_the_configure_words_after_a_colon_with_no_nested_parentheses(self):
        refusals = (KIT / "fragments" / "refusals.md").read_text(encoding="utf-8")
        self.assertIn("same Opovi install: {{configure}}.", refusals)


class TheShippedPluginHoldsTheSameWords(unittest.TestCase):
    def setUp(self):
        self.vendor, self.repo = vendor_and_repo()

    def test_the_shipped_commands_equal_what_the_kit_makes(self):
        made = sync.render(KIT, self.vendor, self.repo)
        for name in COMMANDS:
            shipped = (self.repo / "commands" / f"{name}.md").read_text(encoding="utf-8")
            self.assertEqual(shipped, made[f"commands/{name}.md"], f"{name} in opovi-claude-code is what sync.py writes")

    def test_the_readme_gives_the_install_line_with_both_config_flags(self):
        readme = (self.repo / "README.md").read_text(encoding="utf-8")
        self.assertIn("claude plugin install opovi@opovi --config server_url=", readme)
        self.assertIn("--config token=", readme)

    def test_the_readme_gives_the_same_stdin_line_the_refusals_give(self):
        readme = (self.repo / "README.md").read_text(encoding="utf-8")
        self.assertIn(STDIN_LINE, readme, "the README and the refusals agree on the terminal line")

    def test_the_readme_says_which_steps_were_run_and_which_only_read(self):
        readme = (self.repo / "README.md").read_text(encoding="utf-8")
        self.assertIn("**Run**", readme)
        self.assertIn("**Read, not run:**", readme)

    def test_the_settings_the_lines_name_are_the_manifests_user_config_keys(self):
        manifest = json.loads((self.repo / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(set(manifest["userConfig"]), {"server_url", "token"}, "the README and the refusals name these two keys")
        self.assertIn("`server_url`", self.vendor["configure"])
        self.assertIn('{"token":"<new token>"}', self.vendor["configure"])


if __name__ == "__main__":
    unittest.main()
