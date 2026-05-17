Codex implementation target: reduce contextual panel API cost by replacing full-history context with bounded local context plus compact serialization. Current expensive line is in `summarize_contextual_panels()`: each panel receives `ordered[:index]`, so later panels carry all previous panel summaries into the prompt. That creates quadratic context growth across a 60-panel chapter. 

Use these implementation orders.

````md
# Codex Task: Optimize Contextual Panel Summarization Context Cost

## Objective

Modify the contextual panel interpretation pipeline so each panel call receives only a bounded local context window instead of all previous panels.

Current behavior:
- `summarize_contextual_panels()` sorts panels.
- For panel at index `i`, it passes `ordered[:index]` into `summarize_contextual_panel()`.
- This causes the prompt to grow larger for every later panel.
- For 60 panels, this becomes unnecessarily expensive.

Desired behavior:
- Only pass the previous `N` panels, default `N = 3`.
- Serialize previous panels using a compact form instead of full `PanelSummary.model_dump()`.
- Keep the current panel as the full `PanelSummary`.
- Preserve existing output schemas and avoid breaking the beat/chapter pipeline.

Relevant files:
- `summarize.py`
- `schemas.py`
- `prompts.py`
- `app.py`

## Step 1: Add compact serialization helper in `summarize.py`

Add this function near the other normalization/helper functions:

```python
def _compact_panel_context(panel_summary: PanelSummary) -> JsonObject:
    """
    Return a compact representation of a previous panel for contextual interpretation.

    This prevents repeated full PanelSummary payloads from inflating prompts.
    Keep only fields useful for continuity, setup/payoff, identity, dialogue, and action.
    """
    return {
        "panel_id": panel_summary.panel_id,
        "reading_order": panel_summary.reading_order,
        "dialogue_notes": panel_summary.dialogue_notes,
        "action": panel_summary.action,
        "concise_summary": panel_summary.concise_summary,
        "uncertainty_notes": panel_summary.uncertainty_notes,
    }
````

`PanelSummary` currently contains fields such as `visual_description`, `dialogue_notes`, `uncertainty_notes`, `action`, and `concise_summary`, so compacting previous panels avoids repeatedly sending the full visual description for older panels. 

## Step 2: Change previous-panel serialization in `summarize_contextual_panel()`

Find this block:

```python
if previous_panel_summaries:
    prompt_text += "\n\nPrevious panel summaries (JSON array):\n"
    prompt_text += json.dumps(
        [ps.model_dump() for ps in previous_panel_summaries],
        ensure_ascii=False,
    )
```

Replace it with:

```python
if previous_panel_summaries:
    prompt_text += "\n\nPrevious local panel context (compact JSON array):\n"
    prompt_text += json.dumps(
        [_compact_panel_context(ps) for ps in previous_panel_summaries],
        ensure_ascii=False,
    )
```

Do not compact the current panel yet. Keep this line unchanged:

```python
prompt_text += json.dumps(panel_summary.model_dump(), ensure_ascii=False)
```

The current panel is the object being interpreted, so full detail is still useful.

## Step 3: Add `context_window` parameter to `summarize_contextual_panels()`

Current function:

```python
def summarize_contextual_panels(
    panel_summaries: list[PanelSummary],
    cast_context: dict | None,
    model: str,
) -> list[ContextualPanelInterpretation]:
    ordered = sorted(panel_summaries, key=lambda ps: ps.reading_order)
    contextual: list[ContextualPanelInterpretation] = []
    for index, panel_summary in enumerate(ordered):
        contextual.append(
            summarize_contextual_panel(
                panel_summary=panel_summary,
                previous_panel_summaries=ordered[:index],
                cast_context=cast_context,
                model=model,
            )
        )
    return contextual
```

Replace with:

```python
def summarize_contextual_panels(
    panel_summaries: list[PanelSummary],
    cast_context: dict | None,
    model: str,
    *,
    context_window: int = 3,
) -> list[ContextualPanelInterpretation]:
    """
    Interpret panels with bounded local history.

    context_window controls how many immediately previous panels are passed into
    each contextual interpretation call. This avoids quadratic prompt growth.
    """
    if context_window < 0:
        raise ValueError("context_window must be >= 0")

    ordered = sorted(panel_summaries, key=lambda ps: ps.reading_order)
    contextual: list[ContextualPanelInterpretation] = []

    for index, panel_summary in enumerate(ordered):
        start = max(0, index - context_window)
        previous_window = ordered[start:index]

        contextual.append(
            summarize_contextual_panel(
                panel_summary=panel_summary,
                previous_panel_summaries=previous_window,
                cast_context=cast_context,
                model=model,
            )
        )

    return contextual
```

This is the main cost fix. It converts the contextual pass from “panel 60 receives panels 1–59” into “panel 60 receives panels 57–59.”

## Step 4: Update contextual prompt wording in `prompts.py`

Current prompt says the model receives “Previous panel summaries.” 

Change that section to make the new bounded-context behavior explicit:

```python
CONTEXTUAL_PANEL_INTERPRETATION_PROMPT = """You are interpreting a comic/manhwa panel sequence for adaptation into a narrated motion-comic episode.

You will receive:
1. Optional known cast context.
2. A compact local window of previous panel summaries.
3. The current panel summary.
4. OCR/dialogue notes if available.

Do not treat the current panel in isolation.
Use the local previous-panel window to identify immediate setup/payoff, joke structure, callbacks, reveals, reactions, emotional turns, or continuity.
Do not assume you have the full chapter history.
Resolve likely character identities only when supported by visual cues, dialogue continuity, or cast context.
Do not invent character names, motives, or unseen events.

Important:
- If a joke is set up in a previous local panel and paid off in the current panel, explain that mechanism.
- If a character trait changes the meaning of the panel, explicitly state it.
- If identity is uncertain, mark confidence as low or uncertain.
- Prefer corrected story function over generic visual description.

Return JSON with:
- panel_id
- reading_order
- resolved_characters: list of objects with name, visual_label, confidence, evidence
- continuity_links: list of links to previous panels or prior dialogue
- panel_role: setup, payoff, reaction, reveal, transition, escalation, atmosphere, action, or other
- setup_payoff_relation: object or null, with setup_panel_ids, payoff_panel_ids, setup, payoff, mechanism, effect
- joke_or_dramatic_mechanism: string or null
- corrected_story_function
- adaptation_notes: list of video/narration-relevant notes
- uncertainty_notes
- concise_contextual_summary
"""
```

## Step 5: Add CLI argument in `app.py`

The current CLI already accepts arguments like `--model`, `--use-ocr`, and `--output-root`. Add a new argument for contextual window size in the relevant summarize command parser. 

Add:

```python
s.add_argument(
    "--context-window",
    type=int,
    default=3,
    help="Number of previous panels to include during contextual panel interpretation.",
)
```

Where this gets used depends on the current panel-based pipeline command. In the uploaded `app.py`, the visible command still uses the older chunk pipeline: chunk → OCR → chunk summaries → chapter synthesis.  If the panel pipeline command exists elsewhere or has been added locally, pass `args.context_window` into `summarize_contextual_panels()`.

Expected call:

```python
contextual_interpretations = summarize_contextual_panels(
    panel_summaries=panel_summaries,
    cast_context=cast_context,
    model=args.model,
    context_window=args.context_window,
)
```

## Step 6: Save debugging outputs

Wherever contextual interpretations are generated, write both the panel summaries and contextual interpretations to disk.

Add or preserve:

```python
io_utils.write_json(
    out_dir / "panel_summaries.json",
    io_utils.to_jsonable(panel_summaries),
)

io_utils.write_json(
    out_dir / "contextual_interpretations.json",
    io_utils.to_jsonable(contextual_interpretations),
)
```

`io_utils.write_json()` and `io_utils.to_jsonable()` already exist and support Pydantic models through `model_dump()`. 

## Step 7: Keep beat synthesis global

Do not remove the beat-level global pass.

The correct division is:

```text
PanelSummary: visual/local extraction
ContextualPanelInterpretation: local sequence correction with bounded context
BeatSummary: global narrative grouping
ChapterSummary: final recap
```

The beat synthesis function already consumes all contextual panel interpretations at once, which is the right place for broader sequence-level reasoning. 

## Step 8: Acceptance criteria

The implementation is successful if:

1. `summarize_contextual_panels(..., context_window=3)` passes at most 3 previous panels to each contextual call.
2. Previous panels are serialized with `_compact_panel_context()`, not full `model_dump()`.
3. `context_window=0` works and passes no previous panels.
4. Negative `context_window` raises `ValueError`.
5. Existing schemas remain compatible.
6. Beat and chapter synthesis still work without modification.
7. CLI exposes `--context-window` where the panel pipeline is invoked.
8. Output files still include `contextual_interpretations.json`.

## Optional next step, not required in this patch

After this patch works, add a `RollingStoryState` schema for compressed long-range memory. Do not implement it yet unless needed. The bounded-window fix is lower-risk and should be merged first.

```

Core diagnosis: the bug is architectural, not just model selection. The contextual layer is currently doing too much chapter-memory work. Bound it. Let beat synthesis handle global structure.
```
