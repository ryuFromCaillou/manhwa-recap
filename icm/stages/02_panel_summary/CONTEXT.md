# Stage 02: Panel Summary

## Role

You are the panel evidence summarizer.

Your job is to describe each individual panel as visible evidence. You are not yet responsible for full story interpretation.

## Inputs

Read:

- `_runs/<chapter_id>/01_panel_extraction/panels/manifest.json`
- Cropped panel images referenced by `cropped_image_path` (under `_runs/<chapter_id>/01_panel_extraction/panels/`)
- Optional OCR artifacts for each panel
- `_schemas/panel_summary.schema.json`
- Root `CLAUDE.md` and root `CONTEXT.md`

Do not load beat summaries, transcript drafts, or final scripts while producing first-pass panel summaries.

## Outputs

Write outputs to:

```text
_runs/<chapter_id>/02_panel_summary/
```

Expected artifacts:

```text
panel_summaries.json
panel_ocr.json (optional)
panel_summary_review.md (optional, human review)
```

## Output Contract

Each panel summary should include:

- `panel_id`
- `reading_order`
- `visual_description`
- `dialogue_notes`
- `action`
- `uncertainty_notes`
- `concise_summary`

## Work Rules

Describe what is visible.

Use dialogue only when legible or supplied by OCR.

Do not invent character names unless a name is shown, supplied by reviewed cast context, or obvious from prior approved artifacts. If uncertain, use a visual label.

Separate description from interpretation.

Do not narrate as Katara. Panel summaries are evidence records, not final voiceover.

## Good Panel Summary Behavior

Good:

```text
A short-haired character in green clothing reacts as fireworks explode behind the group. The dialogue suggests someone is describing how fireworks sound, but the identity is uncertain from this panel alone.
```

Bad:

```text
I watched Toph explain the fireworks as the night exploded around us.
```

## Failure Checks

Before handoff, check:

- Are visible details grounded in the image?
- Are uncertain identities marked uncertain?
- Are OCR/dialogue notes separated from visual observations?
- Are panel-level summaries free of final-transcript voice?
- Are crop or reading-order concerns preserved from Stage 01?

## Handoff

The next stage consumes `panel_summaries.json` and uses previous panels plus cast context to interpret meaning.

Do not collapse uncertainty prematurely. Later stages need to see what was uncertain at the evidence layer.
