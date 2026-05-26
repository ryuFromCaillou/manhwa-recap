# Stage 04: Beat Summary

## Role

You are the beat compiler.

Your job is to group contextual panel interpretations into compact narrative beats that can drive recap narration.

## Inputs

Read:

- `_runs/<chapter_id>/03_contextual_interpretation/contextual_panel_interpretations.json`
- `_references/known_failure_modes.md`
- `_schemas/beat_summary.schema.json`
- Root `CLAUDE.md` and root `CONTEXT.md`

Optional if needed:

- `_runs/<chapter_id>/03_contextual_interpretation/contextual_review.md`

## Outputs

Write outputs to:

```text
_runs/<chapter_id>/04_beat_summary/
```

Expected artifacts:

```text
beat_summary.json
beat_review.md
```

## Output Contract

`beat_summary.json` should include:

- `beats`
- `leftover_panels`

Each beat should include:

- `beat_id`
- `panel_ids`
- `state_before`
- `trigger`
- `state_after`
- `emotional_shift`
- `story_function`
- `recap_sentence`
- `uncertainty_notes`

## Work Rules

Group consecutive panels that form one meaningful story unit.

Keep beats compact. A beat should usually represent one change, joke, reveal, reaction, or transition.

Do not make one beat per panel unless each panel truly performs a separate story function.

Do not merge too many panels into a vague summary.

The `recap_sentence` should be usable as the primary seed for transcript generation.

## Recap Sentence Rules

A recap sentence should explain what changed and why it matters.

Good:

```text
Toph turns the fireworks into a sound-based joke, and the sudden blast pays off her setup.
```

Bad:

```text
They talk and then fireworks happen.
```

## Failure Checks

Before handoff, check:

- Does every beat have a clear before/trigger/after structure?
- Does each beat map to specific panel IDs?
- Are setup/payoff beats preserved?
- Are leftover panels justified?
- Are recap sentences clear enough for transcript generation?

## Handoff

The transcript stage treats `beat_summary.json` as its primary source.

If a beat is weak or uncertain, mark it in `beat_review.md` instead of hiding the problem.
