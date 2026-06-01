# Speck

**Human-LLM communication is broken: natural language is too ambiguous but code diffs are too noisy.**

Software development requires developers to plan across multiple layers of abstraction -- but human-AI interfaces are not well designed for this:
- It's hard to communicate technical ideas using unstructured text.
- Reading walls of text is fatiguing.
- And fixing high-level design mistakes at the code generation stage is costly and frustrating.

What we need is a shared, structured specification language between humans and AI which lets developers visualise what the final program structure will look like before the first line of code is written.

Introducing **speck**, a specification workflow skill for AI-assisted development which inserts a design step between 'Plan Mode' and 'Code Generation'.

When developing a feature, the workflow generates a new `.speck` file for each relevant file in the change (e.g., `main.speck.py`). The `speck` file keeps the original file's structure and behaviour (e.g. classes, function signatures, docstrings) but abstracts out unneeded implementation details. 

This lets you freely collaborate with the LLM across any level of abstraction -- manipulating structures, types, and function behaviour. Once you are satisfied, the LLM can generate code which faithfully matches the specification you set out; you can visualise and guide the system's design without writing a single line of implementation code!

The workflow generates `speck` files 'before' and 'after' your proposed feature, which you can view as a code diff in your IDE.

Speck is unopinionated, leaves no trace, and fits into any existing AI workflow.

Give it a go today to explore a better way to communicate with your LLM!

## How it works

1. **Plan.** Sketch out your feature with 'Plan Mode' as normal, and accept the plan.
2. **Speck.** Before implementing the plan, the workflow kicks in adding a new 'speck' development phase.
3. **Diff.** Speck generates the 

AI generates **speck files** (e.g., `main.speck.py`) — your code with unimportant implementation details removed.
3. **Diff.** Compare the speck files "before" and "after" using `git diff` to see exactly what your feature changes at the design level.
4. **Review.** You review and refine the diff together until you sign off.
5. The AI generates code from the signed-off diff — treating it as the spec.
6. Once you've verified the code, the speck files are deleted. They leave no trace.

## Install

Speck is one markdown file. Drop it into your skills directory:

```sh
git clone https://github.com/DylanMoss1/speck.git
mkdir -p ~/.claude/skills/speck
cp speck/SKILL.md ~/.claude/skills/speck/SKILL.md
```

It activates automatically when you finish planning a feature and asks once whether you'd like to use it (default yes).

Leveraging the power of IDEs and version control, you can easily view and manipulate specification diffs to visualise the changes involved with your proposed feature.

For the best experience:
- Turn off linting on `*.speck` files (but keep the LSP configuration on).
- Use your IDE's 'diff' view to compare "before" and "after" specks.
- Work on `git` subtrees to avoid cluttering your main branch
- Use the [grill-me](https://github.com/mattpocock/skills/blob/main/skills/productivity/grill-me/SKILL.md) skill to refine your speck files.
- Use the [superpowers](https://github.com/obra/superpowers) skill (or red-green-refactor TDD) for code implementation.

## Good to know

- **Any language.** The convention is `name.speck.<extension>` (e.g., `main.speck.py`) with the same transformation — keep signatures, drop bodies. The examples use Python; nothing else assumes it.
- **Unopinionated.** Speck only handles the spec-and-diff workflow. Pair it with whatever planning, questioning, or review tools you already use.
- **Leaves no trace.** Speck files are temporary. They aren't committed long-term and don't touch your project config — your teammates and CI never need to know it exists.
- **You stay in control.** Visualise and guide what the end implementation looks like, don't let LLMs pull your lead!
## License

MIT — see [LICENSE](LICENSE).
