## First: the world folder

Do this before any call.

1. Read `opovi.json` at the root of the folder this session was opened in. Look for it nowhere else.
2. **No `opovi.json`:** say this, call no tool, and end the turn:
   "This folder holds no Opovi world. In Opovi, open the world and its Agent connection panel, save the world's
   harness for {{agent}} into a folder of its own, then open {{agent}} in that folder and run this command again."
3. **Check its fields.** It holds `serverUrl` (an http or https address), `worldId` (a lowercase UUID, 36
   characters with dashes), `vendor`, `harnessVersion` (a whole number, 0 or more) and `skills` (a list of names).
   A field that is missing or has another shape: say that `opovi.json` is damaged, name the field, tell the person to
   save the harness again from the world's Agent connection panel, and end the turn. Ignore a field not named here.
4. **`vendor` is not `{{vendor}}`:** the folder was saved for another agent (say which one `vendor` names), and its
   skills sit where {{agent}} does not read them. Tell the person to save the harness again from the Agent connection
   panel, choosing {{agent}}, and end the turn.
5. Keep `worldId` and `harnessVersion` for the calls below. Every call that takes a project passes `worldId`.
