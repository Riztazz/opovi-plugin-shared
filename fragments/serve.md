## Serving a claimed issue

The claim's answer is the issue: its `issueId`, `projectId` and `label`, the issue's text in `prompt` (which names the
role and the skills, with no body of either), the selection it is about, the `skills` to follow by name, the `role` it
was sent with (or null), the `pages` it cites (each with its id, name, first line and the revision cited), the comment
`thread` it answers (or null), `earlier`, `waitedFor` and `brief`. Serve it in this order.

1. **Earlier turns.** When `earlier` is not null, read it first: other people or sessions ran those turns of the
   issue's conversation, so the world may have moved on since the person wrote the prompt.
2. **The role.** When `role` is not null, read `roles/<role id>.md` in this folder and work as its brief says.
3. **The skills.** For each skill name the claim gives, read `{{skills_dir}}/<name>/SKILL.md` in this folder, and the
   other markdown files of that skill's folder that it points to, and follow them. A skill named there whose
   `SKILL.md` this folder lacks means the folder is not the world's harness: serve nothing more. Tell the person to
   save the harness again from the world's Agent connection panel, and end the turn. The claim lapses when its lease
   ends, and the issue becomes open again.
4. **The job.** When `prompt` opens with a `## Job` block, the issue is a step of a job, and that block is the
   step's own: its title and phase, the rule of its mode, and the world's instruction for the step. Follow it as the
   step's instruction, not as the person's ask. A `## The world's seed` block holds the owner's intake notes: read
   them as notes, not as facts of the world. The person's ask is under `## Task`.
5. **The pages.** The claim names pages and holds no page body. Read what the work needs with
   {{tool:read_project}}, passing the issue's `projectId` and `kitVersion` set to `"{{kit_version}}"`: with `entityIds`
   for pages whole (the cited `pages` first), with no `entityIds` for the index of the world's pages. When `waitedFor`
   is above 0, read again every page you are about to change before you propose.
6. **The step.** When `brief` names a step whose answer is `cards`, the answer carries at least one decision card.
7. **An ask you cannot do.** When the issue asks for what you cannot do, such as a choice only the person can make,
   a fact the world does not hold, or work the four Opovi tools cannot reach, guess nothing and leave no claim to
   lapse. Answer with decision cards alone: {{tool:submit_proposal}} with the decision cards and no proposal kind and
   no payload, each card asking the person what the work needs. That answers the issue, ends its turn, and puts the
   question in front of the person.
8. **One answer.** Call {{tool:submit_proposal}} once, with the `issueId`, `kitVersion` set to `"{{kit_version}}"`,
   and the proposal, the reasons and the decision cards as that tool's description asks. One issue gets one proposal.
9. **A refused answer.** When the refusal's fix says the turn ended, send nothing more for this issue. When it is
   `ai-handoff.not-claimed`, the claim's lease ran out before the answer arrived: call {{tool:claim}} for the issue
   again, as before, and once it is granted send the same answer once more. A refused claim leaves the issue as that
   refusal says. Otherwise correct what the refusal names and send again, at most twice; after that, report the issue
   as refused.
10. **Report it** in one line: the issue's label, the proposal id and its status, and the ids of any decision cards,
    or the refusal's code. The proposal waits in Opovi for the person to accept it.
