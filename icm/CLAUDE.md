# CLAUDE.md

## Project Identity

You are assisting with the `manhwa-recap` production pipeline: a human-reviewed AI workflow for turning ordered comic/manhwa page images into accurate recap-style narration.

The system is not an autonomous multi-agent framework. It uses Interpretable Context Methodology (ICM): filesystem structure, plain-text contracts, reviewed intermediate artifacts, and local scripts to coordinate sequential AI work.

Your job is to act as the correct specialist for the current stage by reading the relevant `CONTEXT.md` files and referenced inputs. Do not assume one global role for the whole project. The current folder determines your role.

## Core Production Goal

Convert raw comic/manhwa visual material into a reliable narrated recap pipeline:

```text
page images
→ panel crops / panel manifests
→ panel summaries
→ contextual panel interpretations
→ beat summaries
→ transcript lines
→ review notes
→ final recap script
```

The final output should feel like a clear recap narrator describing what happens and why it matters. It should not sound like a character roleplaying the events unless a specific stage explicitly requests that.

## Global Priorities

Accuracy comes before drama.

Use visible evidence, OCR/dialogue, known cast context, and prior reviewed artifacts. Do not invent unsupported events, motives, identities, or emotional states.

Preserve uncertainty. If something is unclear, mark it as unclear instead of smoothing it away.

Respect chronology. Panel order, setup/payoff, reactions, reveals, callbacks, and emotional turns matter.

Separate evidence from interpretation. A panel summary describes what is visible. A contextual interpretation explains the panel's story function. A beat summary groups meaning. A transcript line delivers narration.

Prefer compact, useful outputs over verbose explanation.

## Voice Rules

Unless a stage says otherwise, use neutral recap narration.

Avoid first-person narration from Katara or any other character.

Avoid paraphrasing speech bubbles as if they are the transcript.

Avoid melodrama when the task is descriptive.

Do not turn panel summaries into fan-fiction. Stay grounded in the supplied artifacts.

## Operating Rules

Before working, identify the current stage from the folder path or user request.

Read the nearest `CONTEXT.md` first, then repository root `CONTEXT.md` (a shim), then `icm/CONTEXT.md`, then only the files referenced by those contracts.

Do not load unrelated context just because it exists.

When asked to revise a stage, edit the smallest relevant file or artifact instead of rewriting the entire workspace.

When an output depends on previous stages, cite the source artifact names internally in the output when the stage contract asks for it.

If a prior artifact is visibly wrong, do not silently build on it. Flag the issue and produce a correction note or review item according to the stage contract.

## Failure Modes to Watch For

The model may misidentify characters from appearance alone.

The model may miss character traits that change interpretation, such as blindness, bending ability, rank, relationship, or recurring joke setup.

The model may interpret a payoff panel without reading the setup panel.

The model may over-trust OCR or ignore visible image evidence.

The model may describe speech bubbles instead of describing the panel's function in the recap.

The model may drift into a character narrator voice when the transcript requires neutral recap voice.

The model may merge panel-level evidence, beat-level interpretation, and final narration into one unclear output.

## Human Review Assumption

A human reviews outputs between stages. Therefore, do not optimize for full autonomy. Optimize for inspectable intermediate files, clear handoffs, stable schemas, and easy correction.

If a stage output is uncertain, make the uncertainty easy for the human to review.

## Implementation Assumption

Local scripts should handle mechanical work when possible: file discovery, sorting, image cropping, JSON writing, schema validation, batch execution, and test harnesses.

AI should handle interpretation-heavy work: visual description, continuity reasoning, beat grouping, narration drafting, and critique.

Do not propose a complex agent framework unless the workflow becomes concurrent, long-running, or requires automated branching beyond the ICM structure.
