# Speck — Specification-driven Development

**Human-LLM communication is broken: natural language is too ambiguous but code diffs are too noisy.**

Software development requires developers to plan across multiple layers of abstraction — but human-AI interfaces are not well designed for this:
- It's hard to communicate technical ideas with unstructured text.
- Reading walls of text is fatiguing.
- Fixing design mistakes after code generation is costly and frustrating.

What we need is a **shared, structured specification language between humans and AI** which lets developers & LLMs visualise what the final program structure looks like before writing a single line of code.

Introducing **speck**, a specification workflow skill for AI-assisted development which inserts a design step between 'Plan Mode' and 'Code Generation'.

[IMAGE]

## What is speck

When developing a feature, the workflow generates a new `.speck` file for each relevant file in the change (e.g., `main.speck.py`). The `speck` file keeps the original file's structure and behaviour (e.g. classes, function signatures, docstrings) but abstracts out unneeded implementation details. 

This lets you collaborate with the LLM across any level of abstraction — manipulating structures, types, and function behaviour. Once you are satisfied, the LLM can generate code which faithfully matches the specification you set out.

You can visualise and guide the system's design without writing a single line of implementation code! The workflow generates `speck` files 'before' and 'after' your proposed feature, which can be viewed as a code diff in your IDE.

Speck is unopinionated, leaves no trace, and fits into any existing AI workflow.

Give it a go today to explore a better way to communicate with your LLM!

Workflow: `Plan Mode → Speck Diff → Collaborate / Review → Code Gen → Cleanup`

## How does it work

1. **Plan.** Sketch out your feature with 'Plan Mode' as normal, and accept the plan.
2. **Speck.** Before implementing the plan, the new 'speck' workflow kicks in.
3. **Diff.** The workflow generates 'before' and 'after' speck files, leveraging git* to produce diffs.
4. **Review.** Review and refine the speck diff in your IDE alongside the LLM, until you sign off.
5. **Generation.** The AI generates code according to your specification.
6. **Cleanup.** Once you have finished, the speck files are wiped leaving no trace of the workflow.

*Or your VCS of choice.

## Install

Speck is one markdown file. Drop it into your skills directory:

```sh
git clone https://github.com/DylanMoss1/speck.git
mkdir -p ~/.claude/skills/speck
cp speck/SKILL.md ~/.claude/skills/speck/SKILL.md
```

The skill activates automatically when you finish planning a feature, asking if you want to use the speck workflow.

For the best experience:
- Turn off linting on `*.speck` files, but keep the LSP configuration on.
- Use your IDE's 'diff' view to compare 'before' and 'after' specks.
- Use the [grill-me](https://github.com/mattpocock/skills/blob/main/skills/productivity/grill-me/SKILL.md) skill to refine your speck files.
- Use the [superpowers](https://github.com/obra/superpowers) skill (or red-green-refactor TDD) for robust code generation.

## Good to know

- **Any language.** The specification format is generic enough to work across any program file.
- **Unopinionated.** Speck only handles the spec-and-diff workflow. Pair it with whatever planning, questioning, or review tools you already use.
- **Leaves no trace.** Speck files are temporary. They aren't committed long-term and don't touch your project config — your teammates and CI never need to know it exists.
- **Stay in control.** Visualise and guide what the end implementation looks like, don't leave it up to chance!

## License

MIT — see [LICENSE](LICENSE).
