# opovi-agent-kit

The shared source of the Opovi agent plugins. Each plugin repository holds a copy of what this kit makes, because an
installed plugin must stand alone: Claude Code, Codex and Antigravity install a plugin's own folder and nothing beside
it.

Status: built for Claude Code, Codex and Antigravity (`vendors/claude-code.json`, `vendors/codex.json`,
`vendors/antigravity.json`), at the version `VERSION` names. Not yet tried against a live Opovi server.

| Repository | Holds |
|---|---|
| https://github.com/Riztazz/opovi-plugin-shared | this kit |
| https://github.com/Riztazz/opovi-claude | the Claude Code plugin |
| https://github.com/Riztazz/opovi-codex | the Codex plugin |
| https://github.com/Riztazz/opovi-antigravity | the Antigravity plugin |

Each vendor file names its GitHub repository (`Riztazz/opovi-claude`, `Riztazz/opovi-codex`, `Riztazz/opovi-antigravity`),
and a local, git-ignored `plugins.local.json` maps each vendor to where its clone lives on this PC.

## What the plugins do

A person sends AI issues from their Opovi world, then types a fetch command in their own agent. The agent serves
that person's open issues and ends its turn. Nothing waits and nothing wakes, so nothing spends tokens while idle.

| Command | What the agent does |
|---|---|
| `fetch-list` | Shows this world's open issues of the person, numbered oldest first, with id, label, when sent and size. Serves none. |
| `fetch-single <id or number>` | Serves the one issue named by id or by its number in the last list. With none, the oldest open one. |
| `fetch-all` | Serves every open issue of this world, oldest first, one proposal each, then ends the turn. |

Every command first reads the folder's `opovi.json`. With none, it tells the person to save the world's harness from
the Agent connection panel and calls nothing. When `claim` answers `ai-handoff.harness-stale`, it shows the panel's
address and stops.

## What the kit holds

```
commands/<name>.md          one procedure per command, the same words for every vendor
fragments/<name>.md         the parts several commands share: rules, preflight, claim, serve, refusals
schema/opovi.schema.json    the world folder's opovi.json
contract.md                 the endpoint, the four MCP tools, the sign-in header and every refusal a command handles
vendors/<vendor>.json       how one vendor names a command, a tool and an argument, and its GitHub repository
plugins.local.json          git-ignored map of vendor to local clone path (absolute or kit-relative)
sync.py                     writes the kit into each vendor's clone, checking its git origin URL
tests/test_sync.py          the tests of sync.py
VERSION                     the kit's version, stamped into each plugin as KIT_VERSION and sent to claim as kitVersion
```

## A command's source

A command file starts with a header and holds placeholders that `sync.py` fills in for each vendor:

```
---
description: Serve one open Opovi issue of this world, ...
argument-hint: [id or number]
tools: list_issues claim read_project submit_proposal
---
The person typed this after the command: `{{arguments}}`
{{include:preflight}}
Call {{tool:claim}} with ...
```

| Placeholder | Becomes |
|---|---|
| `{{include:<fragment>}}` | the text of `fragments/<fragment>.md`, placeholders filled |
| `{{tool:<tool>}}` | the vendor's name of that Opovi tool (`toolMention`). Only a tool the header's `tools` line names |
| `{{command:<command>}}` | how the person types that command (`commandName`) |
| `{{arguments}}` | the vendor's argument form (`arguments`) |
| `{{skills_dir}}`, `{{vendor}}`, `{{agent}}` | the vendor's skills folder in a world folder, its `opovi.json` vendor value, its display name |
| `{{configure}}`, `{{update}}` | the vendor's words for setting a new token and updating the plugin |
| `{{kit_version}}` | `VERSION` |

The header's `tools` line may name only the four Opovi tools, and it is what the vendor pre-allows (`toolGrant`).
`sync.py` refuses an unknown placeholder, a tool outside the four, a tool the `tools` line leaves out, a missing
fragment and an include cycle.

## A vendor file

`vendors/<vendor>.json` holds `vendor` (the `opovi.json` value), `agent` (its display name), `repository` (the GitHub
repository as `owner/name`), `skillsDir` (as Opovi's `harness-files.ts` writes it), `commandFile` and
`commandName` (with `{name}`), `toolMention` and `toolGrant` (with `{tool}`), `toolSeparator`, `arguments`,
`configure`, `update`, `frontmatter` (the header each command file gets: `key`, a `value` with `{description}`,
`{argument-hint}` or `{tools}`, and `quoted`; an entry whose field a command lacks is left out), `versionFile`, and
`manifest` (the plugin manifest whose `versionKey` takes `VERSION`; the manifest itself is the plugin's own file).

A new vendor is one vendor file and its plugin repository beside this one. No procedure is copied by hand.

### How a person sets the token, per vendor

`configure` is the words a refusal gives for a new token, so each one is a way that was tried. The plugin's README
holds the full steps and says which were run and which only read (checked 2026-11-26).

| Vendor | Steps | Checked |
|---|---|---|
| Claude Code | The desktop app: the plugin page, the Opovi plugin, its Settings tab. A terminal: `echo '{"token":"<new token>"}' \| claude plugin configure opovi@opovi --values-stdin`. A first install in one line: `claude plugin install opovi@opovi --config server_url=... --config token=...`. Then start Claude Code again. Not `/plugin configure opovi@opovi`: it did not open the settings in the desktop app | The two terminal lines run in `claude` 2.1.332 against a throwaway `CLAUDE_CONFIG_DIR`. The desktop app's page is the lead's report, not run |
| Codex | `OPOVI_TOKEN` in the environment and `[mcp_servers.opovi]` in `~/.codex/config.toml` | Read from the plugin's README, not run |
| Antigravity | Customizations, Installed, the plugin's setup dialog. `agy plugin` has no configure command (`agy` 1.5.16 `plugin --help`) | Not run |

## Running it

From this folder, with Python 3.10 or later and nothing else installed:

```
py -3 sync.py                     write every vendor's plugin
py -3 sync.py --check             write nothing; exit 1 when a plugin differs from what the kit makes
py -3 sync.py --vendor claude-code
py -3 sync.py --plugin claude-code=/path/to/clone
py -3 -B -m unittest discover -s tests -v
```

`sync.py` finds each vendor's clone in `plugins.local.json` (`{ "<vendor>": "<path>" }`). When a vendor has no entry,
an interactive run asks once (offering a sibling folder named like the repository as its default) and saves the answer;
`--check` and non-terminal runs ask nothing, exit 2, and print the line to add. Every run checks each folder's git
`origin` URL against the vendor's `repository` field and refuses a mismatch with exit 2. Use `--plugin <vendor>=<path>`
to override one vendor for a single run without saving.

`sync.py` writes LF only and leaves a command file the kit no longer makes in place, naming it as stale, for a person
to remove. Exit codes: 0 done or clean, 1 drift or a stale file, 2 a kit or setup error such as a missing or mismatched
plugin repository.

## The world folder

Each world gets a folder of its own on the person's PC, saved from the world's Agent connection panel in Opovi.

```
opovi.json                        serverUrl, worldId, vendor, harnessVersion, skills (schema/opovi.schema.json)
<skills folder>/<name>/SKILL.md   the world's skills, in the folder the vendor reads
roles/<role id>.md                each role's brief and the skills it names
README.md                         what the folder is, and the three commands
```

The folder holds markdown and JSON only. Nothing in it runs.

## The contract with the server

`contract.md` holds it whole. In short:

- **Four tools, all on the server:** `list_issues`, `claim`, `read_project`, `submit_proposal`, at
  `<server>/api/plugins/ai-handoff/mcp`. A plugin allows these four and no other. None of them can touch the PC.
- **Sign-in:** `Authorization: Bearer <agent token>` on every MCP call. The person makes one token per agent in
  Opovi, under Settings, You, Agent connection. OAuth replaces the pasted token later.
- **Own issues only.** A token reads and serves only its own person's issues.
- **The harness check.** `claim` takes the folder's `harnessVersion` and refuses a missing or old one with
  `ai-handoff.harness-stale`, whose text names the Agent connection panel. The command shows it and stops.
- **The plugin check.** `claim` takes `kitVersion`, and the server refuses a plugin under its floor with
  `ai-handoff.kit-outdated`, whose text names the repository to update from. A call with no `kitVersion`, or a string
  that is not a version number, is refused `ai-handoff.kit-missing`, and the command sends its version once and a second refusal ends it.
- **A refusal is text.** The agent reads `<code>: <message> <fix>` and no details object, so every link a command
  shows is in that text.

## Releasing a version

The four repositories share one version, `VERSION` here, and each release is a tag `v<version>` in all four. Opovi's
server tells a person once per version that a newer plugin is out, so a change that reaches no plugin's files needs no
release.

1. Change the kit, run `py -3 sync.py` (using `plugins.local.json` to reach each clone), then `py -3 sync.py --check` and the tests. Both clean.
2. Raise `VERSION` (semver, below 1.0): the patch for wording an agent reads, the minor for a change in what a command
   sends or reads, a new field or tool among them. Run `py -3 sync.py` again: it writes `KIT_VERSION` and each
   manifest's version.
3. Commit in each of the four repositories, one commit per change, a short subject and no body.
4. Tag `v<version>` in all four and push the commits and the tag: `git push origin main --tags`.
5. In Opovi, in the same wave: `DEFAULT_KIT_CONFIG.latest` in `packages/plugins/ai-handoff/src/policy/inbox-policy.ts`
   moves to the new version, and so does `latest` in the hosted server's `<STUDIO_DATA>/plugins/ai-handoff/opovi-kit.json`,
   which the server reads again within 5 s, with no restart. A release an older plugin cannot work with also moves
   `KIT_VERSION_FLOOR`, which refuses the older plugins with `ai-handoff.kit-outdated`.

## Rules

- The kit and the plugins hold no secret and no part of the Opovi server.
- No hook and no script in any plugin. A command is instructions to the agent and nothing else.
- A command changes nothing on the PC: it reads the world folder and sends one proposal per issue.
- A change to a command's procedure lands here first, then `sync.py` copies it into every plugin.
