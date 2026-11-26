---
description: List this world's open Opovi issues, numbered, and serve none
tools: list_issues
---
# Opovi: list the open issues

Show the person's open issues of this folder's world, numbered, and serve none of them.

{{include:rules}}

{{include:preflight}}

## The list

1. Call {{tool:list_issues}} with `projectId` set to `worldId`, `status` set to `"open"` and `kitVersion` set to
   `"{{kit_version}}"`, and no other argument. A refusal: follow "When a call is refused".
2. The answer's `issues` come newest first. Number them oldest first: number 1 is the issue that has waited
   longest, the one with the smallest `createdAt`.
3. Show one table, oldest first, with these columns: the number, the `id` whole, the `label` (write "(closed to your
   role)" when it is null), when it was sent (`createdAt` is milliseconds since 1970-01-01 UTC, written as a UTC date
   and time) and its size (`promptChars` characters).
4. With no open issue, say "No open issues in this world." instead of the table.
5. End with one line: `{{command:fetch-single}} <number or id>` serves one, and `{{command:fetch-all}}` serves them
   all. When `list_issues` carried `update`, print `Opovi <latest> is out (you run <running>): <repository>` after that
   line as the last line. Claim nothing, and end the turn.

{{include:refusals}}
