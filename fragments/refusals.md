## When a call is refused

A refused call answers one line of text: a code such as `ai-handoff.harness-stale:`, then what happened and what to
do. Tell the person both in a sentence or two, and copy every address in it whole, character for character.

These refusals end the whole command. Claim nothing more, and end the turn:

- `ai-handoff.harness-stale`: this folder's harness is not the one the world runs now. The text names the folder's
  version, the world's version, and the address and place of the Agent connection panel in Opovi. Show those, and
  tell the person to save the harness from that panel into this folder again, then run the command again. Nothing was
  claimed, and the issue stays open.
- `ai-handoff.kit-outdated`: this plugin is older than the Opovi server takes. Show the lowest version the text names
  and the repository it names, and tell the person to {{update}}.
- `ai-handoff.kit-missing`: the call sent no `kitVersion`, or a string that is not a version number such as `0.3.2`.
  Send this plugin's version as `kitVersion` and run the call once more. A second `ai-handoff.kit-missing` ends the
  command, and so does a command that cannot name that version: show the text and the repository it names, and tell
  the person to {{update}}.
- `ai-handoff.token-invalid`, `ai-handoff.token-expired`, `ai-handoff.token-banned`, `ai-handoff.route-is-api`: the
  agent's sign-in does not work. Show the text, and tell the person to make a new agent token in Opovi, under
  Settings, You, Agent connection, then {{configure}}.
- `ai-handoff.forbidden`, `ai-handoff.ai-off`: the person may not run AI issues in this world, or its AI is off.
  Show the text.
- A call that fails with no `ai-handoff.` code, or a tool that is not there: the Opovi server did not answer. Say so,
  name the server address in `opovi.json`, and tell the person to check that the plugin's server address names the
  same Opovi install: {{configure}}.

These refusals are about one issue alone. The issue is left as the text says, and a command that serves several
goes on with the next one:

- `ai-handoff.already-claimed`, `ai-handoff.claimed-elsewhere`: another agent or session holds it.
- `ai-handoff.turn-waiting`: an earlier turn of its conversation has not ended. It stays open.
- `ai-handoff.turn-withheld`, `ai-handoff.step-gone`: the issue cannot run any more, and it failed.
- `ai-handoff.issue-missing`, `ai-handoff.issue-closed`: no such issue is open for this person.
- `ai-handoff.not-claimed`, to an answer sent: the claim's lease ran out before the answer arrived. Claim the issue
  again, then send the same answer once more. A refused claim leaves the issue as that refusal says.

Any other code: show the text, and treat it as a refusal of that one issue.
