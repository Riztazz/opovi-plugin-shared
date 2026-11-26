"""Tests that the kit's refusal table and refusal fragment name every code the Opovi server answers a plugin with.

Run from the kit's folder: py -3 -m unittest discover -s tests -v
"""

import sys
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIT))

import sync  # noqa: E402

# The codes that end a whole command: the plugin sends nothing more after one of these.
COMMAND_ENDING = ("ai-handoff.harness-stale", "ai-handoff.kit-outdated", "ai-handoff.kit-missing")


class EveryCommandEndingRefusalIsNamed(unittest.TestCase):
    def test_the_contract_table_has_a_row_for_each_command_ending_code(self):
        contract = (KIT / "contract.md").read_text(encoding="utf-8")
        for code in COMMAND_ENDING:
            self.assertIn(f"| `{code}` |", contract, f"contract.md's refusal table has a row for {code}")

    def test_the_refusals_fragment_says_what_to_do_for_each_command_ending_code(self):
        fragment = (KIT / "fragments" / "refusals.md").read_text(encoding="utf-8")
        for code in COMMAND_ENDING:
            self.assertIn(f"- `{code}`:", fragment, f"refusals.md tells the agent what to do for {code}")

    def test_kit_missing_tells_the_agent_to_send_the_plugins_version_as_kit_version(self):
        fragment = (KIT / "fragments" / "refusals.md").read_text(encoding="utf-8")
        line = fragment[fragment.index("- `ai-handoff.kit-missing`:") :].split("\n- ")[0]
        self.assertIn("kitVersion", line, "the kit-missing step names the kitVersion argument")
        self.assertIn("{{update}}", line, "the kit-missing step ends on the vendor's update steps")

    def test_kit_missing_is_resent_once_and_a_second_one_ends_the_command(self):
        fragment = (KIT / "fragments" / "refusals.md").read_text(encoding="utf-8")
        line = fragment[fragment.index("- `ai-handoff.kit-missing`:") :].split("\n- ")[0]
        flat = " ".join(line.split())
        self.assertIn("run the call once more", flat, "the kit-missing step allows one resend")
        self.assertIn("A second `ai-handoff.kit-missing` ends the command", flat, "a second one ends the command")

    def test_the_contract_row_for_kit_missing_allows_one_resend_and_a_second_ends_the_command(self):
        contract = (KIT / "contract.md").read_text(encoding="utf-8")
        row = contract[contract.index("| `ai-handoff.kit-missing` |") :].split("\n")[0]
        self.assertIn("once", row, "the contract row sends the version once")
        self.assertIn("a second `ai-handoff.kit-missing` ends the command", row, "the row ends on a second refusal")

    def test_the_readme_says_the_command_sends_its_version_once(self):
        readme = " ".join((KIT / "README.md").read_text(encoding="utf-8").split())
        self.assertIn("sends its version once and a second refusal ends it", readme, "the README states the limit")

    def test_every_vendors_command_carries_the_kit_missing_step_once_rendered(self):
        for name in ("claude-code", "codex", "antigravity"):
            vendor = sync.load_vendor(KIT, name)
            made = sync.render(KIT, vendor, sync.repository_of(KIT, vendor))
            texts = [text for path, text in made.items() if path != "KIT_VERSION" and isinstance(text, str)]
            self.assertTrue(
                any("ai-handoff.kit-missing" in text for text in texts),
                f"{name}'s rendered files say what to do on kit-missing",
            )


if __name__ == "__main__":
    unittest.main()
