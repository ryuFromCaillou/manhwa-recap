# Stage 05: Transcript Generation

## Role

You are the recap transcript generator.

Your job is to create neutral voiceover narration from reviewed beat summaries and contextual panel interpretations.

This stage is the current priority bottleneck.

## Inputs

Read:

- `_runs/<chapter_id>/04_beat_summary/beat_summary.json`
- `_runs/<chapter_id>/03_contextual_interpretation/contextual_panel_interpretations.json`
- `_references/recap_voice.md`
- `_references/transcript_anti_patterns.md`
- `_references/style_examples.md`
- `_schemas/transcript.schema.json`
- Root `CLAUDE.md` and root `CONTEXT.md`

Optional if needed:

- `_runs/<chapter_id>/04_beat_summary/beat_review.md`
- `_references/cast_context.md`

Do not use raw panel summaries as the primary source unless beat/contextual artifacts are missing or marked unreliable.

## Outputs

Write outputs to:

```text
_runs/<chapter_id>/05_transcript_generation/
```

Expected artifacts:

```text
transcript.json
transcript.txt
```

## Output Contract

`transcript.json` must match `_schemas/transcript.schema.json`.

`transcript.txt` should be human-readable and preserve line IDs, beat IDs, and panel IDs.

## Source Priority

Use this priority order:

1. `BeatSummary.recap_sentence`
2. `BeatSummary.story_function`
3. `ContextualPanelInterpretation.corrected_story_function`
4. `ContextualPanelInterpretation.joke_or_dramatic_mechanism`
5. Panel-level visual details only when they clarify the voiceover

## Voice Rules

Use neutral recap narration.

Do not speak as Katara.

Do not speak as any character unless explicitly directed by a production note.

Do not simply paraphrase dialogue bubbles.

Do not overdramatize.

Do not invent thoughts, motives, or consequences unsupported by the beat.

## Line Construction Rules

One beat may produce one or more transcript lines.

A short beat should usually produce one line.

A complex beat may produce two lines: one for setup, one for payoff or consequence.

Each line must point back to the beat and panel IDs.

If the beat is uncertain, the line may still be written, but uncertainty must remain in `uncertainty_notes`.

## Good Output Example

```json
{
  "line_id": "line_001",
  "beat_id": "beat_001",
  "panel_ids": ["page_003_panel_001", "page_003_panel_002"],
  "speaker": "Recap Narrator",
  "line_type": "recap",
  "text": "Toph turns the fireworks into a sound-based joke, and the sudden blast lands as the payoff.",
  "uncertainty_notes": []
}
```

## Bad Output Example

```text
I watched as Toph showed us what fireworks sounded like to her.
```

Reason: first-person character narration.

```text
Toph says, "You wanna know what fireworks sound like for me?"
```

Reason: speech-bubble paraphrase, not recap narration.

## Failure Checks

Before handoff, check:

- Does each line come from a beat?
- Does each line preserve panel IDs?
- Does the voice sound like a recap narrator?
- Is any line merely dialogue paraphrase?
- Is any line too dramatic compared to the beat?
- Did setup/payoff survive into the transcript?
- Are uncertain claims marked?

## Handoff

The review stage consumes `transcript.json`, `transcript.txt`, and the source beat/contextual artifacts.

If a line was difficult to write, capture the reason as `uncertainty_notes` on the relevant line(s) and/or in a small markdown note stored alongside the transcript.
