---
description: Serve one open Opowi issue of this world, named by id or list number, or else the oldest
argument-hint: [id or number]
tools: list_issues claim read_project submit_proposal
---
# Opowi: serve one issue

Serve one open issue of this folder's world with one proposal, then end the turn.

The person typed this after the command: `{{arguments}}`

{{include:rules}}

{{include:preflight}}

## Which issue

1. **Nothing typed:** call {{tool:list_issues}} with `projectId` set to `worldId`, `status` set to `"open"` and
   `kitVersion` set to `"{{kit_version}}"`, and take the oldest issue, the one with the smallest `createdAt`.
2. **A whole number N:** when this conversation already shows the table of a `{{command:fetch-list}}` run, take the
   id in its row N. Otherwise call {{tool:list_issues}} as above, number the issues oldest first, and take number
   N. A number past the last one: say how many issues are open, and end the turn.
3. **An id** (a lowercase UUID, 36 characters with dashes): take it as it is.
4. **Anything else:** say that the command takes a list number or an issue id, or nothing for the oldest, and end
   the turn.
5. **No open issue:** say "No open issues in this world." and end the turn.

A refusal of the list: follow "When a call is refused".

{{include:claim}}

{{include:serve}}

When the issue is served or refused, end the turn. Serve no other issue.

{{include:refusals}}
