---
name: handoff
description: Writes HANDOFF.md at the repository root so the next session can start fresh, and cheaply, where this one stopped, instead of resuming a long conversation (a resume re-reads the whole history uncached). Use when a session has grown long, the task changes, or you are stopping for the day.
disable-model-invocation: true
---

# repo-mode handoff

Write a short handoff file for the next session. Talk to the user in the language they use (default: Greek); the file itself is in English unless the user asks otherwise.

1. Find the repository root (`git rev-parse --show-toplevel`; if this isn't a git repo, use the current folder). The file is `HANDOFF.md` there. If it exists, read it and replace it: it describes the previous stop, not this one.
2. Gather facts, read-only: `git status --short`, `git diff --stat`, `git log --oneline -5`, and what this conversation established (the goal, what was done, what was decided and why, what failed).
3. Write `HANDOFF.md`, at most about 40 lines, with these sections and nothing else:
   - **Goal**: one or two sentences.
   - **State**: done / in progress, with `path:line` for the places that matter. Say what is uncommitted.
   - **Next steps**: ordered and concrete; the first one should be startable without further questions.
   - **Decisions**: what was chosen and why, including approaches that were tried and rejected, so the next session doesn't repeat them.
   - **Commands**: how to build and run the tests for this task, if they aren't obvious.
   - **Open questions / risks**.
   Facts only; no secrets, tokens or credentials; no copied code beyond a line or two.
4. Do not commit, stage or exclude the file. Tell the user the path, and whether `git check-ignore -q HANDOFF.md` shows it as ignored: if it isn't, say they can commit it (shared) or add it to `.git/info/exclude` (private).
5. End with the sentence to use in the next session: **"Read HANDOFF.md and continue from there."** Remind them that a new session (`/clear` or a fresh `claude`) is cheaper than `--continue` or `--resume` for a long conversation, because a resume re-reads the whole history at full price on its first message.
