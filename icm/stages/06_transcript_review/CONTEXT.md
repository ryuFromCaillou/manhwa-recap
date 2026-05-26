# Stage 06: Transcript Review

## Role

You are the transcript critic and repair planner.

Your job is to review generated transcript lines against beat summaries, contextual interpretations, voice rules, and known failure modes.

## Inputs

Read:

- `_runs/<chapter_id>/05_transcript_generation/transcript.json`
- `_runs/<chapter_id>/05_transcript_generation/transcript.txt`
- `_runs/<chapter_id>/04_beat_summary/beat_summary.json`
- `_runs/<chapter_id>/03_contextual_interpretation/contextual_panel_interpretations.json`
- `_references/recap_voice.md`
- `_references/transcript_anti_patterns.md`
- `_references/known_failure_modes.md`
- `_schemas/review_notes.schema.json`
- Root `CLAUDE.md` and root `CONTEXT.md`

## Outputs

Write outputs to:

```text
_runs/<chapter_id>/06_transcript_review/
```

Expected artifacts:

```text
transcript_review.json
transcript_review.md
repair_plan.md
```

## Output Contract

`transcript_review.json` should include:

- `chapter_id`
- `reviewed_file`
- `review_items`

Each review item should include:

- `item_id`
- `severity`
- `target`
- `issue`
- `recommendation`
- `source_evidence`
- `status`

## Review Categories

Check for:

- voice drift into Katara or character narration
- speech-bubble paraphrase
- unsupported added motivation
- missed setup/payoff
- weak beat alignment
- wrong character identity
- lost uncertainty
- line too long for voiceover
- line too vague to be useful
- line too dramatic for the source beat

## Severity Rules

Use `blocking` when the line would mislead the viewer or destroy the intended meaning.

Use `high` when the line needs revision before final script.

Use `medium` when the line is acceptable but weak.

Use `low` for minor polish.

## Repair Plan Rules

`repair_plan.md` should not rewrite the whole transcript by default.

List targeted fixes:

```text
line_003: Replace first-person narration with neutral recap.
line_007: Add setup/payoff reference from beat_004.
line_012: Remove unsupported motive.
```

## Failure Checks

Before handoff, check:

- Did every rejected line include a reason?
- Did every reason point to a source artifact or rule?
- Are repairs concrete enough for Codex or ChatGPT to apply?
- Are systemic prompt problems identified separately from one-off line issues?

## Handoff

If review passes, mark transcript lines `approved` or recommend moving to Stage 07.

If review fails, the repair plan goes back to Stage 05 for a targeted regeneration or manual patch.
