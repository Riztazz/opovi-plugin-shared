---
description: Serve every open Opowi issue of this world, oldest first, one proposal each
tools: list_issues claim read_project submit_proposal
---
# Opowi: serve every open issue

Serve every open issue of this folder's world, oldest first, with one proposal each, then end the turn.

{{include:rules}}

{{include:preflight}}

## The run

1. Call {{tool:list_issues}} once, with `projectId` set to `worldId`, `status` set to `"open"` and `kitVersion` set to
   `"{{kit_version}}"`. A refusal: follow "When a call is refused". Number the issues oldest first, by `createdAt`.
   That list is the whole run: an issue sent while it runs waits for the next run.
2. With no open issue, say "No open issues in this world." and end the turn.
3. Take the issues one at a time, in that order. Claim one, serve it, and only then claim the next.
   - A refusal that ends the whole command stops the run there. Claim nothing more.
   - A refusal of that one issue: note its code, and go on with the next issue.
   - A skill missing from this folder stops the run there, as "Serving a claimed issue" says.
4. At the end, show one table, oldest first: the number, the label, and what came of it (the proposal id and its
   status, "cards only" with the card ids, or the refusal's code). Name the issues the run did not reach when it
   stopped early. Then end the turn.

{{include:claim}}

{{include:serve}}

{{include:refusals}}
