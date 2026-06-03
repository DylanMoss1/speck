# Speck — Specification-driven Development

**Speck is a specification workflow for AI-assisted programming, inserting a new design step between 'Plan Mode' and 'Code Generation'.**

**Plan Mode** generates large blocks of text, which are hard to debug and reason about precisely.

**Code Generation** is costly, we want to _fail fast_ rather than fix design flaws at this stage.

Speck introduces a flexible, structured specification language between humans and AI — allowing you to visualise the final structure of the program before writing a single line of code.

Benefits:
- Faster, more precise communication with LLMs.
- Fail fast: questions and design decision are front-loaded.
- Hands-off implementation & greater confidence LLMs understand your design.
- Visualise and guide the structure of the program — stay in control.

[VIDEO]








This improves human-LLM communication, 






What does it solve:
- **Avoid 


Avoid planning features with large, natural-language blocks of text.
- 





For those who AI-programming because: 
- 





Speck 





**Human-LLM communication is broken: natural language is too ambiguous but code diffs are too noisy.**






Software development requires developers to plan across multiple layers of abstraction — but human-AI interfaces are not well designed for this:
- It's hard to communicate technical ideas with unstructured text.
- Reading walls of text is fatiguing.
- Fixing design mistakes after code generation is costly and frustrating.

What we need is a **shared, structured specification language between humans and AI** which lets developers & LLMs visualise what the final program structure looks like before starting code implementation.

Introducing **speck**, a specification workflow skill for AI-assisted development which inserts a design step between 'Plan Mode' and 'Code Generation'.

**Embrace the fail-fast philisophy: front-load answering questions, making design decisions, and clearing up misconceptions before writing a single line of code.**

Now LLMs can efficiently one-shot your implementation with full confidence their design aligns with your expections.

[IMAGE]

## What is speck

When developing a feature, the workflow generates a new `.speck` file for each relevant program file in the change (e.g., `main.speck.py`). The `speck` file keeps the original file's structure and behaviour (e.g., classes, function signatures, docstrings) but abstracts out unneeded implementation details.

You can collaborate with the LLM across any level of abstraction — from system-level types and structures to low-level function behaviour. Once you are satisfied, the LLM will generate code which faithfully matches the specification you set out.

You can visualise and guide the system's design without writing a single line of code! The workflow generates `speck` files 'before' and 'after' your proposed feature, to be viewed as a code diff in your IDE.

Speck is unopinionated, leaves no trace, and fits into any existing AI workflow.

Give it a go today to explore a better way to communicate with your LLM!

Workflow: `Plan Mode → Speck Diff → Collaborate / Review → Code Gen → Cleanup`

## How does it work

1. **Plan.** Sketch out your feature with 'Plan Mode' as normal, and accept the plan.
2. **Speck.** Before implementing the plan, the new 'speck' workflow kicks in.
3. **Diff.** The workflow generates 'before' and 'after' speck files, leveraging git* to produce diffs.
4. **Collaborate.** Review and refine the speck diff in your IDE alongside the LLM, until you sign off.
5. **Code Generation.** The LLM generates code according to your specification.
6. **Cleanup.** Once you have finished, the speck files are wiped leaving no trace of the workflow.

*Or your VCS of choice.

## Install

### Install the skill

```sh
git clone https://github.com/DylanMoss1/speck.git
mkdir -p ~/.claude/skills/speck
cp speck/SKILL.md ~/.claude/skills/speck/SKILL.md
```

### Install the hook

This hook invokes the skill after every planning session: asking you whether you want to invoke the speck workflow.

Copy the `hooks` block from [`speck-hook.json`](speck-hook.json) into `~/.claude/settings.json` (or `.claude/settings.json` for a single project), then restart Claude Code.

## For the best experience

For the best experience:
- Turn off linting on `*.speck` files, but keep the LSP configuration on.
- Use your IDE's 'diff' view to compare 'before' and 'after' specks (`git diff` by default).
- Use the [grill-me](https://github.com/mattpocock/skills/blob/main/skills/productivity/grill-me/SKILL.md) skill to refine your speck files.
- Use the [superpowers](https://github.com/obra/superpowers) skill (or red-green-refactor TDD) for robust code generation.

## Philisophy

- **Any language.** The specification format is generic enough to work across any program file.
- **Unopinionated.** Speck only handles the spec-and-diff workflow. Pair it with whatever planning, questioning, or review tools you already use.
- **Leaves no trace.** Speck files are temporary. They aren't committed long-term and don't touch your project config — your teammates and CI never need to know they exists.
- **Stay in control.** Visualise and guide the end implementation, don't leave it up to chance!

## License

MIT — see [LICENSE](LICENSE).
