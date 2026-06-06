# Speck

## Overview

speck is a specification workflow for AI-assisted development. It inserts a design step between planning and code generation.

Speck files (e.g. `main.speck.py`) live alongside their source counterparts. They capture structure and behaviour — class/function definitions, type signatures, imports, decorators, constants, docstrings — without implementation. They provide a shared technical language between humans and AI: more structured than natural language, less complex than full code diffs.

### Rules

1. No code before sign-off. Do NOT edit non-`.speck` files until the user explicitly signs off on the speck. Never simultaneously edit `.speck` files and their corresponding source files.
2. No skipping. The speck workflow applies to all code changes. The only valid skip is an explicit user instruction (e.g. "skip speck", "just make the change directly").
3. No mention in Plan Mode. Do not reference speck files during planning — they are irrelevant until the plan is approved.
4. The speck diff is the contract. The speck diff is the sole, canonical specification of what changes get made. If a change is not in the speck diff, it does not get implemented — no matter what the plan, conversation, or prior discussion says. If a change is in the speck diff, it must be implemented — no exceptions. During implementation, treat the speck diff the way a builder treats blueprints: follow it exactly.
5. No overriding signed-off changes. Once the user signs off on a speck, every change in it is final. Do not skip, weaken, or reinterpret any signed-off change based on your own judgment — even if you believe a comment is stale, a rename is unnecessary, or a change was "just a discussion annotation." The user reviewed and approved it; implement it. If you have concerns (e.g. a comment contradicts the new code), implement the speck as-is and raise the concern with the user afterward.
6. Annotations are directives. Comments and annotations added to speck files (e.g. `# Change this to X`, `# Instead do Y`, `# Add a TODO here`) are implementation instructions, not discussion notes. They carry the same weight as structural changes like renamed functions or modified signatures. During implementation, treat every annotation in the signed-off speck diff as something that must be acted on.
7. No project config changes. Do not modify project configuration files (e.g. `pyproject.toml`, `.gitignore`, `Makefile`, `tsconfig.json`) to accommodate speck files unless the user explicitly asks. Speck is a workflow tool used alongside other developers and tools that should not be aware of its existence. Speck files are temporary artifacts — they must not leave traces in the project's configuration.

Common rationalizations that do NOT justify skipping:
- "The change is trivial / just a rename / only touches one file"
- "The user said 'implement' so they want code directly"
- "The plan is specific enough that a speck is redundant"
- "This is a mechanical change with no design decisions"
- "These are code review fixes, not new design work"
- "The plan already contains exact code snippets"

Common rationalizations that do NOT justify omitting a signed-off speck change:
- "This comment is stale / misleading after the other changes"
- "This was just a discussion annotation, not a real change"
- "This is an annotation/comment, not a structural change"
- "A code reviewer flagged this as unnecessary"
- "This rename doesn't affect behavior"
- "I'll mention it to the user instead of implementing it"

## Generating Speck Files

To generate a speck file from a source file, copy the source but remove all concrete implementation. Preserve:
- Class and function definitions (signatures only)
- Type signatures, import statements, decorators, constants
- All docstrings

Copy all relevant parts — do not leave sections omitted. Replace method bodies with `...`.

The speck diff is the canonical representation of the feature changes. It is the single source of truth for what will change. Only what appears in the speck diff gets implemented — nothing more, nothing less. Do not omit changes under the assumption that they will be inferred from conversation context, the plan, or prior discussion. If a change is not visible in the speck diff, it does not exist and must not be implemented. Conversely, every change in the speck diff must be implemented. This includes new files, modified signatures, removed definitions, added imports, and changed constants.

The diff should also contain a list of all references / calls to user-defined constants and functions in relevant functions (listed in the docstring under headings `CONSTANTS` and `CALLS`). Include these for any function that is new, modified, or whose call graph changes. For modified functions, include both the "before" and "after" states (ensure the full list is provided for both so the diff is clear as to what has changed); for new functions, include the "after" state only.

If the function's behaviour is not clear from a docstring alone, if the docstring would become long and hard to read, or if there are implementation-specific changes (rather than behavioural changes), you can include basic pseudocode in the docstring to describe the function's behavior / implementation.

For example this might look like:

```python
def add_row_to_db(row: Row) -> None:
    """Insert a row into the database, retrying on failure.

    PSEUDOCODE:  # Only include if needed
    1) parse and validate the row
    2) send row to db
        2.1) attempt to update db with row
        2.2) if this fails, backoff and retry at most 3 times

    CONSTANTS:
      - DB_URL: str

    CALLS:
      - parse_row(...)                           # Use '...' for args if this
                                                 #   function is not important
                                                 #   to this speck change
      - send_to_db(db_url: str, row: Row)        # Otherwise include argument
                                                 #   names and types
      - send_to_db_with_backoff(                 # If the function is too long,
            db_url: str,                         #   split it across multiple lines
            row: Row,  # Parsed + validated row  # Optionally comment
                                                 #   constants / functions / args
                                                 #   if they are important to this
                                                 #   speck (only do this if relevant)
            backoff_time: int
        )
    """
    ...
```

If the project has a code formatter, run it on both the before and after speck files so formatting differences don't pollute the diff. Ensure empty statements (`...`) are on matching lines in both versions.

## Creating a Speck Diff

1. **Base Commit:** For each affected source file, create a corresponding `.speck` file representing the current ("before") state. Commit these files with the message `speck [before state]: <very short description of changes>`.
2. Working directory: Modify the speck files (without committing) to represent the "after" state.

`git diff` now shows exactly what changes the feature requires at the specification level.

If `.git` cannot be found, check if the user is using other VCS tools such as `jj`. If so, use this instead and adapt the commands accordingly.

For changes that are implementation specific (rather than behavioural changes), you must make explicit mention of these in the module / function's docstrings. This ensures every change is visible in the diff — even implementation ones. Keep these concise — avoid long lists or blocks of text. These comments/docstring hints should not be carried into the final code. The speck file should be treated as the source of truth for all changes to be made, do not rely on previous conversations for context.

## Example

Given `main.py` with functions `fun1` and `fun2`, to implement a feature that removes `fun1` and adds `fun3`:

- Base Commit: `main.speck.py` contains `fun1` and `fun2` (run formatter if it exists).
- Working directory: `main.speck.py` modified to remove `fun1` and add `fun3` (run formatter if it exists).

`git diff` shows: `fun1` removed, `fun3` added, `fun2` preserved.

Keep the speck diff current — update speck files as your understanding of the feature evolves. If the "before" state of a speck file is empty, leave the file completely blank.

## Iterating on the Design

Speck files are a shared language. Use them to communicate technical details with the user. Users may also modify speck files to communicate ideas back — check for changes before answering questions.

To modify the Base Commit (e.g. to add new before-state files):

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

- Test specks before code generation. After the feature speck files are signed off, create speck files for all relevant tests (new and modified test files) following the same before/after workflow. Present the test speck diff to the user and obtain explicit sign-off before proceeding to code generation. This ensures test coverage and design are agreed upon alongside the feature design.
- Before generating code, review all speck files (feature and test) for errors, inconsistencies, or contradictions between files. Fix any issues found before proceeding.
- Generate code by following the speck diff line by line. The speck diff is the implementation checklist — every addition, removal, and modification it contains must be reflected in the generated code, and no other changes should be made. After generating code, re-read the speck diff and confirm nothing was missed. Do not create a new commit — this lets speck and code changes be viewed together.
- Once you have finished generating code, double check that the implementation is completely consistent with the speck files. The code generation may edit files / functions not included in the `.speck` description. Make sure to edit and add new `.speck` files accordingly whenever code is changed or generated.
- Keep `.speck` files until the user has verified the generated code. After the user has verified the generated code, remove all `.speck` files and check that no `.speck` files remain.
