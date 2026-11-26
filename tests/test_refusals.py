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
