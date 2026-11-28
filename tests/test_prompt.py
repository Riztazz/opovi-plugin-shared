"""Tests that the kit says what a claim's prompt holds: the job block, the seed and the person's task.

The headings are the Opovi server's (PROMPT_LAYOUT in packages/plugins/ai-handoff/src/policy/prompt-layout.ts).
Run from the kit's folder: py -3 -m unittest discover -s tests -v
"""

import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent

HEADINGS = ("## Job", "## The world's seed", "## Task")


class TheClaimPromptIsDescribedAsTheServerWritesIt(unittest.TestCase):
    def test_the_contract_names_each_heading_of_the_claim_prompt(self):
        contract = (KIT / "contract.md").read_text(encoding="utf-8")
        for heading in HEADINGS:
            self.assertIn(f"`{heading}`", contract, f"contract.md's claim row names the prompt's {heading} block")

    def test_the_serving_order_names_each_heading_of_the_claim_prompt(self):
        serve = (KIT / "fragments" / "serve.md").read_text(encoding="utf-8")
        for heading in HEADINGS:
            self.assertIn(f"`{heading}`", serve, f"serve.md names the prompt's {heading} block")

    def test_the_serving_order_has_a_job_step_before_the_pages(self):
        serve = (KIT / "fragments" / "serve.md").read_text(encoding="utf-8")
        self.assertIn("**The job.**", serve, "serve.md's serving order has a step for the job block")
        self.assertLess(
            serve.index("**The job.**"),
            serve.index("**The pages.**"),
            "the job step comes before the agent reads the pages",
        )


if __name__ == "__main__":
    unittest.main()
