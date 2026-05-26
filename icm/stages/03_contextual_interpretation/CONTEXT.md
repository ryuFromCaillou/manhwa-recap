# Stage 03: Contextual Interpretation

## Role

You are the continuity and story-function interpreter.

Your job is to interpret each panel in sequence using previous panel summaries, cast context, and dialogue continuity.

## Inputs

Read:

- `_runs/<chapter_id>/02_panel_summary/panel_summaries.json`
- `_references/cast_context.md`
- `_references/known_failure_modes.md`
- `_schemas/contextual_panel.schema.json`
- Root `CLAUDE.md` and root `CONTEXT.md`

Optional if needed:

- `_runs/<chapter_id>/01_panel_extraction/crop_review.md`
- `_runs/<chapter_id>/02_panel_summary/panel_summary_review.md`

## Outputs

Write outputs to:

```text
_runs/<chapter_id>/03_contextual_interpretation/
```

Expected artifacts:

```text
contextual_panel_interpretations.json
contextual_review.md
```

## Output Contract

Each contextual interpretation should include:

- `panel_id`
- `reading_order`
- `resolved_characters`
- `continuity_links`
- `panel_role`
- `setup_payoff_relation`
- `joke_or_dramatic_mechanism`
- `corrected_story_function`
- `adaptation_notes`
- `uncertainty_notes`
- `concise_contextual_summary`

## Work Rules

Do not treat the current panel in isolation.

Use previous panels to identify setup/payoff, callbacks, reveals, reactions, emotional turns, and continuity.

Resolve character identities only when supported by evidence.

If a character trait changes the meaning of a panel, explicitly say so.

Preserve uncertainty from Stage 02 unless this stage has enough evidence to resolve it.

Do not generate final transcript lines here. Produce interpretation, not narration.

## Special Rule: Toph / Fireworks Type Cases

If a character is blind or otherwise experiences the event differently, do not describe the moment as though visual perception is the default.

For example, a fireworks scene involving Toph may be about sound, vibration, or joke payoff, not visual appreciation.

## Failure Checks

Before handoff, check:

- Did every interpretation use sequence context?
- Are setup/payoff relations identified when present?
- Are character identities supported by evidence?
- Are uncertainty notes still visible?
- Are panel roles compact and useful for beat grouping?

## Handoff

The next stage consumes `contextual_panel_interpretations.json` and groups consecutive panels into beats.

Contextual panels should make beat grouping easier by stating each panel's story function clearly.
