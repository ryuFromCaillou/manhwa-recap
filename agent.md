

The current code already has the right conceptual path: `summarize_panel(...)`, `summarize_contextual_panels(...)`, `summarize_beats_from_contextual_panel_interpretations(...)`, and `summarize_chapter_from_beats(...)` exist in `summarize.py` . The prompts also already define contextual interpretation and beat grouping behavior, including setup/payoff and adaptation notes . So transcript generation should extend this pipeline, not replace it.

Codex implementation order:

````md
# Transcript Generation Implementation Orders

## Goal

Add a transcript generation stage after beat generation.

The transcript must align narration lines to panel IDs. Beats are used for narrative coherence, but panels remain the synchronization unit for video/motion-comic production.

Final output should include:

- `transcript.json`
- `transcript.txt`
- Optional future support for `transcript.srt` or timeline export

The transcript should not be a loose chapter summary. It should be a structured script ledger where each line knows which panel or panels it belongs to.

---

## 1. Extend schemas.py

Add the following Pydantic models.

```python
class TranscriptLine(BaseModel):
    model_config = ConfigDict(extra="ignore")

    line_id: str
    beat_id: str | None = None
    panel_ids: list[str] = Field(default_factory=list)

    speaker: str = "Narrator"
    line_type: str = "narration"
    text: str

    visual_anchor: str | None = None
    emotional_tone: str | None = None
    pacing: str | None = None

    uncertainty_notes: list[str] = Field(default_factory=list)


class Transcript(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str
    lines: list[TranscriptLine] = Field(default_factory=list)
    unresolved_or_uncertain: list[str] = Field(default_factory=list)
````

Line type should support at least:

```text
narration
dialogue
sfx
transition
pause
```

Do not overbuild timing yet. The current priority is stable panel-to-line alignment.

---

## 2. Add transcript prompt to prompts.py

Add:

```python
TRANSCRIPT_GENERATION_PROMPT = \"\"\"You are generating a narrated motion-comic transcript from reviewed panel interpretations and beat summaries.

The transcript must align with the visual panel sequence.

Rules:
- Preserve chronology.
- Every transcript line must include the panel_ids it corresponds to.
- Use beats for narrative coherence, but do not lose panel-level alignment.
- Do not invent unsupported events, dialogue, motives, or identities.
- Use dialogue only when supported by dialogue notes/OCR/context.
- Narration may compress action, but should not skip important visual turns.
- If one narration line covers multiple panels, include all covered panel_ids.
- If a panel is mostly reaction/atmosphere, create a short line or pause/transition line rather than ignoring it.
- If uncertainty exists, include uncertainty_notes.
- Prefer clear, adaptable narration over literary over-writing.

Return JSON with:
- title
- lines: list of objects with line_id, beat_id, panel_ids, speaker, line_type, text, visual_anchor, emotional_tone, pacing, uncertainty_notes
- unresolved_or_uncertain

Return ONLY a single JSON object and nothing else.
\"\"\"
```

This prompt must make alignment non-negotiable. The transcript is allowed to be good prose, but it must remain mechanically useful.

---

## 3. Add transcript generation function to summarize.py

Add:

```python
def generate_transcript_from_beats(
    title: str,
    beat_summary: BeatSummary,
    contextual_interpretations: list[ContextualPanelInterpretation],
    model: str,
) -> Transcript:
    ...
```

Implementation pattern should match the existing OpenAI JSON call helpers already used in `summarize.py` .

The function should serialize:

```python
{
    "title": title,
    "beats": beat_summary.model_dump(),
    "contextual_panel_interpretations": [
        ci.model_dump() for ci in sorted(contextual_interpretations, key=lambda x: x.reading_order)
    ],
}
```

Then call `_responses_json_call(...)` with no images, parse JSON, set `data["title"] = title`, and validate with `Transcript.model_validate(data)`.

---

## 4. Add normalization for transcript payload

Add helper functions:

```python
def _normalize_transcript_line_payload(value: Any, index: int) -> dict[str, Any]:
    ...
```

Normalization should guarantee:

```python
line_id = existing or f"line_{index:04d}"
panel_ids = normalized list[str]
speaker = normalized string fallback "Narrator"
line_type = normalized string fallback "narration"
text = normalized string
uncertainty_notes = normalized list[str]
```

Reject or flag empty text lines unless line_type is `pause`.

Add:

```python
def _normalize_transcript_payload(data: JsonObject, title: str) -> JsonObject:
    ...
```

The function should normalize all lines and ensure `unresolved_or_uncertain` is a list.

---

## 5. Add transcript rendering to io_utils.py

The existing project already renders human-readable summary text through `render_summary_text(...)` . Add a parallel renderer:

```python
def render_transcript_text(title: str, transcript: Transcript) -> str:
    lines = []
    lines.append(f"Title: {title}")
    lines.append("")
    lines.append("Transcript:")
    lines.append("")

    for line in transcript.lines:
        panel_ref = ", ".join(line.panel_ids) if line.panel_ids else "NO_PANEL"
        beat_ref = line.beat_id or "NO_BEAT"
        speaker = line.speaker or "Narrator"
        line_type = line.line_type or "narration"

        lines.append(f"[{line.line_id}] [{beat_ref}] [{panel_ref}] {speaker} ({line_type}):")
        lines.append(line.text.strip())

        if line.visual_anchor:
            lines.append(f"Visual anchor: {line.visual_anchor}")

        if line.uncertainty_notes:
            lines.append("Uncertainty:")
            for note in line.uncertainty_notes:
                lines.append(f"- {note}")

        lines.append("")

    if transcript.unresolved_or_uncertain:
        lines.append("Unresolved or uncertain:")
        for item in transcript.unresolved_or_uncertain:
            lines.append(f"- {item}")

    return "\\n".join(lines).strip() + "\\n"
```

This should produce a readable script while preserving panel linkage.

---

## 6. Add output writer

Add a function either in `app.py` or `io_utils.py`:

```python
def _write_transcript_outputs(out_dir: Path, transcript: Transcript) -> tuple[Path, Path]:
    transcript_json_path = out_dir / "transcript.json"
    transcript_txt_path = out_dir / "transcript.txt"

    io_utils.write_json(transcript_json_path, io_utils.to_jsonable(transcript))
    io_utils.write_text(
        transcript_txt_path,
        io_utils.render_transcript_text(
            title=transcript.title,
            transcript=transcript,
        ),
    )

    return transcript_txt_path, transcript_json_path
```

Use the existing `write_json`, `write_text`, and `to_jsonable` utilities, since those already exist and handle Pydantic models cleanly .

---

## 7. Add CLI command

The current CLI still has a basic `summarize` command that writes `summary.json` and `summary.txt` . Add a new command instead of overloading the old one.

Suggested command:

```bash
manhwa-recap transcript output/chapter_001 --title "Chapter Title"
```

Expected inputs inside the chapter output folder:

```text
panel_summaries.json
contextual_panel_interpretations.json
beat_summary.json
```

Output:

```text
transcript.json
transcript.txt
```

CLI args:

```python
t = sub.add_parser("transcript", help="Generate aligned transcript from reviewed beats and panels")
t.add_argument("chapter_dir", type=Path)
t.add_argument("--title", required=True)
t.add_argument("--model", default=DEFAULT_MODEL)
t.add_argument("--output-format", choices=["text", "json", "both"], default="both")
```

Then implement:

```python
def _cmd_transcript(args: argparse.Namespace) -> int:
    try:
        AppConfig.load()
    except Exception as e:
        print(str(e), file=sys.stderr)
        return 2

    beat_path = args.chapter_dir / "beat_summary.json"
    contextual_path = args.chapter_dir / "contextual_panel_interpretations.json"

    try:
        beat_summary = BeatSummary.model_validate(io_utils.read_json(beat_path))
        contextual = [
            ContextualPanelInterpretation.model_validate(x)
            for x in io_utils.read_json(contextual_path)
        ]
    except Exception as e:
        print(f"Failed to load transcript inputs: {e}", file=sys.stderr)
        return 2

    try:
        transcript = generate_transcript_from_beats(
            title=args.title,
            beat_summary=beat_summary,
            contextual_interpretations=contextual,
            model=args.model,
        )
    except Exception as e:
        print(f"Transcript generation failed: {e}", file=sys.stderr)
        return 3

    txt_path, json_path = _write_transcript_outputs(args.chapter_dir, transcript)

    if args.output_format == "json":
        print(str(json_path))
    elif args.output_format == "text":
        print(str(txt_path))
    else:
        print(str(txt_path))
        print(str(json_path))

    return 0
```

Also add `read_json(path: Path) -> Any` to `io_utils.py`.

---

## 8. Add alignment validation

After transcript generation, validate that panel coverage is sane.

Add:

```python
def validate_transcript_alignment(
    transcript: Transcript,
    contextual_interpretations: list[ContextualPanelInterpretation],
) -> list[str]:
    ...
```

Checks:

```text
- Every transcript panel_id exists in contextual_interpretations.
- Every important panel appears in at least one transcript line.
- No line has an empty panel_ids list unless line_type is transition or pause.
- Beat IDs used by transcript lines exist in beat_summary.
- Panel ordering does not go backward across transcript lines unless explicitly justified.
```

Return warnings, do not fail hard at first. Store warnings in `transcript.unresolved_or_uncertain`.

This is important because the model may generate good narration while silently dropping a reaction panel. For your vision, that is a failure.

---

## 9. Add optional second pass: transcript alignment repair

If validation finds missing panels, run a repair pass.

Add prompt:

```python
TRANSCRIPT_ALIGNMENT_REPAIR_PROMPT = \"\"\"You are repairing an aligned motion-comic transcript.

You will receive:
1. Existing transcript.
2. Ordered contextual panel interpretations.
3. Alignment warnings.

Fix only alignment problems.
Preserve good existing narration when possible.
Add short narration, pause, transition, or reaction lines for missing panels.
Do not invent unsupported story details.

Return the full corrected transcript JSON.
\"\"\"
```

Function:

```python
def repair_transcript_alignment(
    transcript: Transcript,
    contextual_interpretations: list[ContextualPanelInterpretation],
    warnings: list[str],
    model: str,
) -> Transcript:
    ...
```

For now, make this optional with CLI flag:

```bash
--repair-alignment
```

---

## 10. Expected output shape

Example transcript JSON:

```json
{
  "title": "Chapter Title",
  "lines": [
    {
      "line_id": "line_0001",
      "beat_id": "beat_001",
      "panel_ids": ["page_003_panel_001"],
      "speaker": "Katara",
      "line_type": "narration",
      "text": "Toph asked if we wanted to know what fireworks sounded like to her.",
      "visual_anchor": "Toph and the others look up beneath the fireworks.",
      "emotional_tone": "playful setup",
      "pacing": "short setup line",
      "uncertainty_notes": []
    },
    {
      "line_id": "line_0002",
      "beat_id": "beat_001",
      "panel_ids": ["page_003_panel_002"],
      "speaker": "Katara",
      "line_type": "narration",
      "text": "Then she answered herself with a sudden blast of sound that sent everyone jumping.",
      "visual_anchor": "The group reacts in shock to the loud sound effect.",
      "emotional_tone": "comic payoff",
      "pacing": "fast punchline",
      "uncertainty_notes": []
    }
  ],
  "unresolved_or_uncertain": []
}
```

The key property is this: every transcript line is directly tied to one or more panels. That gives you the foundation for later video timing, panel zooms, voiceover generation, subtitle generation, and review UI.

---

## 11. Do not do this yet

Do not jump straight to SRT timestamps.

Do not generate a single chapter narration paragraph.

Do not let beats become the smallest unit.

Do not discard panel IDs after beat grouping.

Do not rely only on OCR dialogue. OCR is useful, but your current OCR wrapper is intentionally basic and may be noisy .

---

## Final architecture

The desired pipeline should become:

```text
images
→ panel crops / manifests
→ OCR
→ panel summaries
→ contextual panel interpretations
→ beat summaries
→ aligned transcript
→ transcript validation
→ optional alignment repair
→ transcript.json + transcript.txt
```


