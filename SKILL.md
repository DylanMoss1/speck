---
name: speck
description: Speck is a specification workflow for AI-assisted programming — inserting a new design step between 'Plan Mode' and 'Code Generation'.
---

# Speck

## Before anything: confirm speck is wanted

The confirmation is the first thing you do the moment plan mode ends — before creating any speck files and before writing any code. Ask the user once whether they want to use the speck workflow for this piece of work. Frame it as a quick yes/no with yes as the default — e.g. "Use the speck workflow for this? (default yes)".

A "piece of work" means a single feature or change as discussed in planning. A clearly new request starts a fresh piece of work and a fresh confirmation.

- If the user gives any affirmative, or stays silent / gives no response: engage the full workflow below. From this point the workflow is binding for this piece of work — the rules below apply and the confirmation is not revisited.
- If the user says no, or "skip speck", or "just make the change directly": do not use the workflow for this piece of work. Proceed normally.
- Ask only once per piece of work. Do not re-prompt before each file or each change. A single yes engages speck for everything that follows until the work is done.

This confirmation is the *only* sanctioned point at which speck may be skipped. Once the user has opted in, none of the no-skip rules below may be weakened — you may not later decide a change is too small or too mechanical to warrant speck.

## The three rules that override everything (once speck is engaged)

1. **The speck diff is the contract.** Only what is in the signed-off speck diff gets implemented. Everything in it must be implemented. Nothing else.
2. **Never skip the workflow.** Once the user has opted in, it applies to every code change in this work, however small. The opt-in question is asked once, at the start; it is not a recurring escape hatch.
3. **Never write source code before the user signs off on the speck.**

Everything below elaborates these. If the rest of this document and these three rules ever seem to conflict, these three win.

## Workflow at a glance

1. Plan mode ends and the plan is approved.
2. Confirm the user wants speck for this work (default yes).
3. Create the "before" speck files and commit them (the Base Commit).
4. Edit the speck files in the working directory to the "after" state. The `git diff` is the feature.
5. Refine the speck with the user until they sign off.
6. Ask whether they want test specks (default yes); if so, repeat the before/after flow for tests and get sign-off.
7. Review all speck files for inconsistencies, then generate code from the diff.
8. Keep speck and code in sync; clean up the speck files once the user has verified the code.

## Overview

`speck` is a specification workflow for AI-assisted development. It inserts a design step between planning and code generation.

The purpose is communication: speck exists so the human and the AI converge on a precise, reviewable description of a change *before* any code is written, catching misunderstandings while they are still cheap to fix. The speck diff is the medium for that agreement. When a situation arises that the rules below do not directly cover, fall back on this purpose — do whatever best keeps the human and AI working from the same precise, agreed description.

Speck files (e.g. `main.speck.py`) live alongside their source counterparts. They capture structure and behaviour — class/function definitions, type signatures, imports, decorators, constants, docstrings — without implementation. They provide a shared technical language between humans and AI: more structured than natural language, less complex than full code diffs.

This workflow is language-agnostic. A speck file mirrors its source with the same extension (`main.speck.py`, `lib.speck.ts`, `mod.speck.rs`, and so on) and the same transformation: keep structure and signatures, drop implementation. The examples below use Python, but the workflow applies unchanged to any language.

## Rules

These rules serve the purpose above: keeping the human and AI working from one precise, agreed description. When a rule's application is unclear, resolve it in favour of that purpose.

*Sign-off* means an explicit user approval of the speck as a whole, authorising the move from speck to code. A comment on a single change is not sign-off (see rule 10).

1. **No code before sign-off.** Until the user signs off on the speck, do NOT edit non-`.speck` files, and never edit a `.speck` file and its corresponding source file at the same time. (After sign-off, during the code phase, you do keep the two in sync — see "Keep speck and code in sync" below.)
2. **No skipping once opted in.** After the user has confirmed they want speck (see "Before anything"), the workflow applies to all code changes in this work. The only thing that stops it is an explicit user instruction to abandon it (rule 9).
3. **No mention in Plan Mode.** Do not reference speck files during planning — they are irrelevant until the plan is approved.
4. **The speck diff is the contract.** The speck diff is the sole, canonical specification of what changes get made. If a change is not in the speck diff, it does not get implemented — no matter what the plan, conversation, or prior discussion says. If a change is in the speck diff, it must be implemented — no exceptions. During implementation, treat the speck diff the way a builder treats blueprints: follow it exactly.
5. **No overriding signed-off changes.** Once the user signs off on a speck, every change in it is final. Do not skip, weaken, or reinterpret any signed-off change based on your own judgment. If you have concerns (e.g. a comment contradicts the new code), implement the speck as-is and raise the concern with the user afterward.
6. **Annotations are directives.** Comments added to speck files (e.g. `# Change this to X`, `# Instead do Y`) are implementation instructions, not discussion notes. They carry the same weight as structural changes like renamed functions or modified signatures. Act on every annotation in the signed-off speck diff.
7. **No project config changes.** Do not modify project configuration files (e.g. `pyproject.toml`, `.gitignore`, `Makefile`, `tsconfig.json`) to accommodate speck files unless the user explicitly asks. Speck is a workflow tool used alongside other developers and tools that should not be aware of its existence. Speck files are temporary artifacts — they must not leave traces in the project's configuration.
8. **If the source has diverged, stop.** If the working-directory source differs from the base commit in ways that are not reflected in the speck files (e.g. a hotfix, a teammate's commit, an unfinished edit), do not generate a speck diff that silently ignores this. Surface the divergence to the user and agree on how to handle it before proceeding. A speck diff is only trustworthy when the "before" speck genuinely matches the committed source it was derived from.
9. **The user can abandon the workflow at any time.** This is distinct from rules 2 and 5, which forbid *you* from skipping on your own initiative. If the user explicitly says to stop using speck — "skip speck", "just write the code", "drop the speck workflow", or similar clear instruction — honour it immediately and proceed without speck. When the user wants out, do not insist on continuing.
10. **Confirm ambiguous sign-offs.** A user message like "looks good" or "yes" may mean "I approve this one modification" or "I approve the whole speck and you may proceed." If it is unclear which they mean, and you believe they may be signing off the entire speck (i.e. authorising you to move to code), check before proceeding. Do not treat an ambiguous approval of a single change as sign-off on the whole speck.

### Rationalizations that are never valid (once the user has opted in)

For skipping the workflow:
- "The change is trivial / just a rename / only touches one file"
- "The user said 'implement' so they want code directly"
- "The plan is specific enough that a speck is redundant"
- "This is a mechanical change with no design decisions"
- "These are code review fixes, not new design work"
- "The plan already contains exact code snippets"

For omitting a signed-off change:
- "This comment is stale / misleading after the other changes"
- "This was just a discussion annotation, not a real change"
- "This rename doesn't affect behavior"
- "A code reviewer flagged this as unnecessary"
- "I'll mention it to the user instead of implementing it"

## Generating Speck Files

To generate a speck file from a source file, copy the source but remove all concrete implementation. Preserve:
- Class and function definitions (signatures only)
- Type signatures, import statements, decorators, constants
- All docstrings

Copy all relevant parts — do not leave sections omitted. Replace method bodies with an empty body (for example `...` in Python).

The diff should also contain a list of all references / calls to user-defined constants and functions in relevant functions (listed in the docstring under headings `CONSTANTS` and `CALLS`). Include these for any function that is new, modified, or whose call graph changes. For modified functions, include both the "before" and "after" states (provide the full list for both so the diff is clear); for new functions, include the "after" state only.

If a function's behaviour is not clear from a docstring alone, if the docstring would become long and hard to read, or if there are implementation-specific changes, you may include basic pseudocode in the docstring. Mark spec-only pseudocode with a clear delimiter so it is never carried into the generated code:

```python
def add_row_to_db(row: Row) -> None:
    """Insert a row into the database, retrying on failure.

    [SPECK-ONLY — do not carry into generated code]
    PSEUDOCODE:
    1) parse and validate the row
    2) send row to db
        2.1) attempt to update db with row
        2.2) if this fails, backoff and retry at most 3 times
    [/SPECK-ONLY]

    CONSTANTS:
      - DB_URL: str

    CALLS:
      - parse_row(...)                          # Use '...' for args if this function is not important to this speck change
      - send_to_db(db_url: str, row: Row)       # Otherwise include argument names and types (you can split this over multiple
                                                # lines, and comment individual args if relevant)
    """
    ...
```

Keep pseudocode and `CONSTANTS`/`CALLS` hints concise — avoid long lists or blocks of text. Everything inside a `[SPECK-ONLY]` block, and any docstring hint that describes implementation rather than behaviour, must NOT be carried into the final code.

If the project has a code formatter, run it on both the before and after speck files so formatting differences don't pollute the diff. Ensure empty statements (`...`) are on matching lines in both versions.

## Creating a Speck Diff

1. **Base Commit:** For each affected source file, create a corresponding `.speck` file representing the current ("before") state. Commit these files with the message `speck [before state]: <very short description of changes>`.
2. **Working directory:** Modify the speck files (without committing) to represent the "after" state.

`git diff` now shows exactly what changes the feature requires at the specification level.

Before starting, check what VCS the user is using (check for `.git` files, `.jj` files, etc.). Choose the most appropriate option (for example, if both `.jj` and `.git` are present, choose `jj`). Adapt the commands accordingly, such as using separate "before" and "after" changes in `jj`.

## Example (Python and git specific)

Given `main.py` with functions `fun1` and `fun2`, to implement a feature that removes `fun1` and adds `fun3`:

- Base Commit: `main.speck.py` contains `fun1` and `fun2` (run formatter if it exists).
- Working directory: `main.speck.py` modified to remove `fun1` and add `fun3` (run formatter if it exists).

`git diff` shows: `fun1` removed, `fun3` added, `fun2` preserved.

Keep the speck diff current — update speck files as your understanding of the feature evolves. If the "before" state of a speck file is empty, leave the file completely blank.

## Iterating on the Design

Speck files are a shared language. Use them to communicate technical details with the user. Users may also modify speck files to communicate ideas back — check for changes before answering questions.

For `git`, to modify the Base Commit (e.g. to add new before-state files):

```sh
git stash -u
# Edit before-state speck files
# Run formatter if it exists
git add <files>
git commit --amend
git stash pop
```

## After Sign-Off

Once the user signs off on the feature speck:

- **Test specks before code generation (ask first).** Ask the user whether they want test specks for this work, with yes as the default — e.g. "Create test specks too? (default yes)". If yes, create speck files for all relevant tests (new and modified) following the same before/after workflow, present the test speck diff, and obtain explicit sign-off before proceeding to code. This ensures test coverage and design are agreed upon alongside the feature. If the user declines, proceed to code generation without test specks.
- **Review before generating.** Review all speck files (feature and test) for errors, inconsistencies, or contradictions between files. Fix any issues found before proceeding.
- **Generate code from the diff.** Follow the speck diff line by line. The speck diff is the implementation checklist — every addition, removal, and modification it contains must be reflected in the generated code, and no other changes should be made. In long sessions especially, re-read the speck diff immediately before generating and again after, to confirm nothing was missed: the diff, not the conversation, is canonical.
- **Do not create a new commit.** Never create a new commit (git) or change (jj) for the code, the "after" speck and code should be tied together so they can be viewed in tandem.
- **Keep speck and code in sync — actively.** Throughout the code-writing phase, the speck and the code must always match. Code generation may touch files or functions not in the original `.speck` description; edit and add `.speck` files accordingly whenever code changes. If the user writes or edits code directly without updating the speck, do not leave the speck stale — propagate those changes into the speck files yourself so the two never drift apart. The speck reflecting reality is your responsibility, not the user's.
- **Clean up only on permission.** Keep `.speck` files until the user has verified the generated code. After verification, remove all `.speck` files and confirm none remain.
