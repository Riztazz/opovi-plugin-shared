# The contract between the plugins and the Opovi server

What every plugin built from this kit sends, what it reads back, and every refusal a command handles. The server side
lives in Opovi's `ai-handoff` plugin (`packages/plugins/ai-handoff/src/server/mechanism/inbox/mcp-tools.ts`). A change
on either side changes this file first.

## The endpoint and the sign-in

- **MCP over streamable HTTP** at `<server>/api/plugins/ai-handoff/mcp`, where `<server>` is the Opovi install's
  address with no trailing slash. `POST` only: the server answers JSON, offers no event stream on `GET` and holds no
  session to end on `DELETE`.
- **`Authorization: Bearer <agent token>`** on every call. A person makes one token per agent in Opovi, under
  Settings, You, Agent connection. A token acts for 90 days, and reads and serves only its own person's issues.
- A plugin keeps the token where its vendor keeps secrets (Claude Code: a `sensitive` user setting). No token is
  ever written into the world folder, a command or this kit.

## The four tools

A plugin allows these four and no other. None of them touches the PC.

| Tool | The commands send | The commands read |
|---|---|---|
| `list_issues` | `projectId` (the folder's `worldId`), `status: "open"`, `kitVersion` (this kit's `VERSION`). Nothing else: the input is strict, so an extra field is refused | `issues`, newest first, each `id`, `projectId`, `label` (null when the person's role no longer reads it), `status`, `createdAt` (ms since the epoch, UTC), `leaseUntil`, `promptChars`, `turn`; optional `update` (`{ running, latest, repository }`) once per version per token |
| `claim` | `issueId`, `harnessVersion` (the folder's `opovi.json`), `kitVersion` (this kit's `VERSION`) | `issueId`, `projectId`, `label`, `leaseUntil`, `prompt` (the instruction; it names the role and the skills, with no body of either), `descriptor`, `skills` (names), `role` (`id`, `name`, `tier`, or null), `pages` (each `id`, `name`, `firstLine`, `revision`), `thread`, `earlier`, `waitedFor`, `brief`; optional `update` once per version per token |
| `read_project` | `projectId`, `kitVersion`, and `entityIds` for pages whole, or `from` for a page of the index | the index, or the pages with their links; optional `update` once per version per token |
| `submit_proposal` | `issueId`, `kitVersion`, and the proposal, reasons and decision cards its own description asks for | `proposalId`, `status`, `decisions`, `findings`; optional `update` once per version per token |

Every tool takes `kitVersion` since Opovi #5878 (`claim` requires it; on the other three it is optional on the wire,
and below the server's floor any call that sends it is refused `ai-handoff.kit-outdated`). The server reads the
plugin's vendor from the agent token row, not from a tool argument. Between the floor and the server's latest version,
the first call on a token carries `update: { running, latest, repository }` once per version, and the command prints
`Opovi <latest> is out (you run <running>): <repository>` as its last line.
`harnessVersion` is optional on the wire, but a claim without it is refused `ai-handoff.harness-stale`, so every command
sends it.

## How a refusal reads

A refused tool call is an MCP error result whose one text is `<code>: <message> <fix>`. The plugin sees no details
object: every value a command shows, a link among them, is written into that text by the server.

| Code | Ends | The text names | The command |
|---|---|---|---|
| `ai-handoff.harness-stale` | the command | the folder's version, the world's version, the address and place of the Agent connection panel | shows them, tells the person to save the harness again, claims nothing more. The issue stays open |
| `ai-handoff.kit-outdated` | the command | the lowest kit version the server takes, the repository to update from | shows them and the vendor's update steps. Checked before the harness version |
| `ai-handoff.kit-missing` | the command | that the call sent no `kitVersion`, or a string that is not a version number, and the repository to update from | sends the plugin's own version as `kitVersion` and runs the call once more; a second `ai-handoff.kit-missing` ends the command, and so does a command that cannot name the version: it shows the text and the vendor's update steps. A `kitVersion` that is not a string, or a string over 64 characters, answers `wire.invalid` before this check |
| `ai-handoff.token-invalid`, `token-expired`, `token-banned`, `route-is-api` | the command | what is wrong with the sign-in | tells the person to make a new token and set it in the plugin |
| `ai-handoff.forbidden`, `ai-handoff.ai-off` | the command | the world it refused | shows the text |
| no `ai-handoff.` code, or no tool | the command | | says the server did not answer and names `opovi.json`'s `serverUrl` |
| `ai-handoff.already-claimed`, `claimed-elsewhere` | that issue | who holds it | goes on with the next |
| `ai-handoff.turn-waiting` | that issue | the turns ahead of it | goes on with the next; the issue stays open |
| `ai-handoff.turn-withheld`, `ai-handoff.step-gone` | that issue | why it cannot run | goes on with the next; the issue failed |
| `ai-handoff.issue-missing`, `issue-closed` | that issue | the id | goes on with the next |
| `ai-handoff.not-claimed` | that answer | that this agent holds no live claim on the issue | the claim's lease ran out: claims the issue again, then sends the same answer once more. A refused claim leaves the issue as that refusal says. The server keeps the turn, so the issue is still open |

A refused `submit_proposal` is corrected and sent again as its fix says, at most twice, unless the fix says the turn
ended.

An agent that cannot do what an issue asks, such as a choice only the person can make or a fact the world does not
hold, answers with decision cards alone: `submit_proposal` with `decisions` and no `kind` and no `payload`. The server
takes that as the issue's answer (`proposalOf` in `mcp-tools.ts`), stores no proposal, ends the turn, and the cards
put the question in front of the person. No claim is left to lapse.

## The world folder

`opovi.json` follows `schema/opovi.schema.json`. Opovi writes it in
`packages/plugins/ai-handoff/src/web/mechanism/harness/harness-files.ts`, with the skills under the vendor's own
directory (`.claude/skills` for Claude Code, `.agents/skills` for Codex and Antigravity) and each role at
`roles/<role id>.md`. The folder holds markdown and JSON only.
