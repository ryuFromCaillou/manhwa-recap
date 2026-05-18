# Root CONTEXT.md

## Workspace Purpose

This workspace organizes the `manhwa-recap` pipeline using Interpretable Context Methodology.

The root context is a routing and orientation file. It should not contain every prompt, rule, example, or output. Stage folders own stage-specific instructions.

Use this file to determine where to work, what context to load, and what kind of artifact to produce.

## Current Pipeline Model

The project is a sequential, human-reviewed production pipeline:

```text
01_panel_extraction
02_panel_summary
03_contextual_interpretation
04_beat_summary
05_transcript_generation
06_transcript_review
07_final_script
```

Each stage receives artifacts from the previous stage, applies a narrow transformation or review pass, then writes a stable output for the next stage.

## Context Loading Rule

Load context in this order:

1. Root `CLAUDE.md` for global project identity and behavioral rules.
2. Root `CONTEXT.md` for routing.
3. The current stage's `CONTEXT.md` for the active contract.
4. Only the reference files named by the current stage.
5. Only the input artifacts named by the current stage.

Do not load all project files by default.

## Stage Routing

### `01_panel_extraction/`

Use this stage when the task involves page images, crop boxes, reading order, panel manifests, panel IDs, or panel QA.

Expected outputs include panel images, manifests, crop review notes, and reading-order corrections.

### `02_panel_summary/`

Use this stage when the task is to describe individual panels as visible evidence.

This stage should answer: what is visibly present, what action is happening, what dialogue is legible, and what is uncertain?

This stage should not decide full story meaning unless it is directly visible.

### `03_contextual_interpretation/`

Use this stage when the task is to interpret panels in sequence.

This stage should answer: how does this panel connect to previous panels, what role does it play, who is likely present, and what setup/payoff or emotional turn is occurring?

### `04_beat_summary/`

Use this stage when the task is to group contextual panels into compact narrative beats.

This stage should answer: what changed from before to after, what triggered the change, and what recap sentence captures the beat?

### `05_transcript_generation/`

Use this stage when the task is to create narration lines from reviewed beats and contextual panel interpretations.

This stage should produce recap-style narration, not character roleplay, not speech-bubble paraphrase, and not unsupported dramatization.

### `06_transcript_review/`

Use this stage when the task is to critique transcript lines.

This stage should flag tone drift, unsupported claims, missed setup/payoff, missing character context, weak panel alignment, and narration that sounds too much like direct dialogue.

### `07_final_script/`

Use this stage when the transcript has passed review and needs to be assembled into final delivery format.

This stage may include pacing notes, scene transitions, voiceover formatting, and production-ready script export.

## Root Reference Folders

Use `_references/` for stable project knowledge that can be reused across chapters.

Examples:

```text
_references/
  cast_context.md
  recap_voice.md
  transcript_anti_patterns.md
  style_examples.md
  known_failure_modes.md
```

Use `_schemas/` for stable input/output contracts.

Examples:

```text
_schemas/
  panel_manifest.schema.json
  panel_summary.schema.json
  contextual_panel.schema.json
  beat_summary.schema.json
  transcript.schema.json
  review_notes.schema.json
```

Use `_runs/` for chapter-specific artifacts.

Examples:

```text
_runs/
  chapter_001/
    inputs/
    01_panel_extraction/
    02_panel_summary/
    03_contextual_interpretation/
    04_beat_summary/
    05_transcript_generation/
    06_transcript_review/
    07_final_script/
```

## Artifact Rule

Stable instructions belong in root or stage context files.

Reusable facts belong in `_references/`.

Formal machine-readable structures belong in `_schemas/`.

Chapter-specific outputs belong in `_runs/<chapter_id>/`.

Temporary scratch work belongs in `_scratch/` and should not be treated as canonical.

## Handoff Rule

Every stage should produce an artifact that the next stage can consume without requiring conversation memory.

A good handoff includes:

- source artifact names
- output file path
- schema or format used
- unresolved uncertainty
- review status
- known issues

## Review Status Labels

Use these status labels in stage outputs when needed:

```text
unchecked
needs_review
approved
rejected
superseded
```

Do not delete superseded artifacts unless explicitly instructed. Mark them as superseded so the reasoning trail remains inspectable.

## Naming Conventions

Use stable numeric prefixes for stages.

Use lowercase filenames with underscores.

Use explicit chapter or run IDs.

Use panel IDs that preserve page and reading order when possible:

```text
page_003_panel_001
page_003_panel_002
```

Use beat IDs that preserve order:

```text
beat_001
beat_002
```

## Default Output Style

For planning or review files, use markdown.

For machine-consumed stage outputs, use JSON.

For prompt contracts, use markdown with clear sections.

For examples, prefer paired good/bad examples.

## Immediate Project Concern

The current known issue is transcript voice drift.

Earlier panel-level prompting encouraged character-perspective narration. That is useful only if the stage explicitly asks for that voice. Transcript generation should instead use reviewed beat summaries as the primary source and produce neutral recap narration.

Therefore, transcript generation should be downstream of beat summaries, not raw panel summaries alone.
