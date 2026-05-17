from __future__ import annotations

import base64
import json
import time
from pathlib import Path
from typing import Any

from openai import OpenAI

from . import prompts
from .schemas import (
    BeatSummary,
    ChapterSummary,
    ContextualPanelInterpretation,
    JsonObject,
    PanelManifest,
    PanelSummary,
    Transcript,
)


def _guess_mime(path: Path) -> str:
    """Return a best-effort MIME type for a local image path."""
    ext = path.suffix.lower()
    if ext in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if ext == ".webp":
        return "image/webp"
    return "image/png"


def _image_to_data_url(path: Path) -> str:
    """Load a local image and encode it as a `data:` URL suitable for `input_image`."""
    mime = _guess_mime(path)
    b64 = base64.b64encode(path.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{b64}"


def _find_json_bounds(text: str) -> tuple[int, int] | None:
    """Find the first balanced JSON object in a text blob."""
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape = False

    for idx in range(start, len(text)):
        char = text[idx]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
        else:
            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return start, idx + 1
    return None


def _extract_json_object(text: str) -> JsonObject:
    """
    Extract the first JSON object found in `text`.

    The model may wrap JSON in prose or a code fence; this tries to be forgiving.
    """
    s = text.strip()
    if s.startswith("```"):
        s = s.strip("`")
    bounds = _find_json_bounds(s)
    if bounds is None:
        raise ValueError("Model did not return a JSON object.")
    payload = s[bounds[0] : bounds[1]]
    return json.loads(payload)


def _normalize_int_field(value: Any, fallback: int | None = None) -> int | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        clean = value.strip()
        if clean.isdigit():
            return int(clean)
        try:
            return int(float(clean))
        except (ValueError, TypeError):
            return fallback
    if isinstance(value, list) and len(value) == 1:
        return _normalize_int_field(value[0], fallback=fallback)
    return fallback


def _normalize_str(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return " ".join(str(item).strip() for item in value if item is not None).strip()
    if value is None:
        return ""
    return str(value).strip()


def _normalize_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        items: list[str] = []
        for item in value:
            if item is None:
                continue
            if isinstance(item, list):
                items.append(" ".join(str(part).strip() for part in item if part is not None))
            elif isinstance(item, dict):
                items.append(json.dumps(item, ensure_ascii=False))
            else:
                items.append(str(item).strip())
        return [item for item in items if item]
    return [str(value).strip()]


def _normalize_transcript_line_payload(value: Any, index: int) -> dict[str, Any]:
    data: dict[str, Any] = {}
    if isinstance(value, dict):
        data = dict(value)
    elif isinstance(value, str):
        data = {"text": value}
    elif value is None:
        data = {}
    else:
        data = {"text": _normalize_str(value)}

    line_id = _normalize_str(data.get("line_id")) or f"line_{index:04d}"
    beat_id = _normalize_str(data.get("beat_id")) or None

    panel_ids = _normalize_str_list(data.get("panel_ids"))
    panel_ids = [p.strip() for p in panel_ids if p and str(p).strip()]

    speaker = _normalize_str(data.get("speaker")) or "Narrator"
    line_type = _normalize_str(data.get("line_type")) or "narration"
    text = _normalize_str(data.get("text"))

    visual_anchor = _normalize_str(data.get("visual_anchor")) or None
    emotional_tone = _normalize_str(data.get("emotional_tone")) or None
    pacing = _normalize_str(data.get("pacing")) or None

    uncertainty_notes = _normalize_str_list(data.get("uncertainty_notes"))

    if not text and line_type not in {"pause"}:
        line_type = "pause"
        uncertainty_notes.append("Empty text line; converted to pause.")

    return {
        "line_id": line_id,
        "beat_id": beat_id,
        "panel_ids": panel_ids,
        "speaker": speaker,
        "line_type": line_type,
        "text": text,
        "visual_anchor": visual_anchor,
        "emotional_tone": emotional_tone,
        "pacing": pacing,
        "uncertainty_notes": uncertainty_notes,
    }


def _normalize_transcript_payload(data: JsonObject, title: str) -> JsonObject:
    if not isinstance(data, dict):
        data = {}

    data["title"] = title
    raw_lines = data.get("lines")
    if not isinstance(raw_lines, list):
        raw_lines = []
    data["lines"] = [
        _normalize_transcript_line_payload(item, idx) for idx, item in enumerate(raw_lines, start=1)
    ]

    data["unresolved_or_uncertain"] = _normalize_str_list(data.get("unresolved_or_uncertain"))
    return data


def _normalize_panel_summary_payload(data: JsonObject, panel: PanelManifest) -> JsonObject:
    data["reading_order"] = _normalize_int_field(
        data.get("reading_order"), fallback=panel.reading_order
    )
    data["dialogue_notes"] = _normalize_str_list(data.get("dialogue_notes"))
    data["uncertainty_notes"] = _normalize_str_list(data.get("uncertainty_notes"))

    for key in ("visual_description", "action", "concise_summary"):
        if key in data:
            data[key] = _normalize_str(data[key])

    return data


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


def _responses_json_call(
        *,
        client: OpenAI,
        model: str,
        prompt_text: str,
        image_paths: list[Path],
        retry_once: bool = True,
        raw_output_file: Path | None = None,
        print_raw: bool = False,
    ) -> JsonObject:
    """
    Call the OpenAI Responses API with text + optional images and parse JSON output.

    Args:
        client: `OpenAI()` client instance.
        model: Model name (e.g. `gpt-4.1`).
        prompt_text: User prompt content.
        image_paths: Local images to attach as `input_image` items.
        retry_once: If true, retries once after a short sleep on failure.
    """
    content: list[dict[str, Any]] = [{"type": "input_text", "text": prompt_text}]
    for p in image_paths:
        content.append({"type": "input_image", "image_url": _image_to_data_url(p)})

    attempt = 0
    last_err: Exception | None = None
    while True:
        attempt += 1
        try:
            resp = client.responses.create(
                model=model,
                input=[{"role": "user", "content": content}],
            )
            text = getattr(resp, "output_text", None)
            if not text:
                raise ValueError("Empty model response text.")

            # Optionally persist the raw model response for debugging/inspection
            if raw_output_file is not None:
                try:
                    raw_output_file.parent.mkdir(parents=True, exist_ok=True)
                    raw_output_file.write_text(text, encoding="utf-8")
                except Exception:
                    # best-effort only; do not fail the call because of logging
                    pass

            if print_raw:
                print("--- RAW MODEL OUTPUT START ---")
                print(text)
                print("--- RAW MODEL OUTPUT END ---")

            try:
                return _extract_json_object(text)
            except Exception as e:  # pragma: no cover - surface model output for debugging
                snippet = text.strip()[:1000]
                raise RuntimeError(
                    f"Model did not return a JSON object. Raw response (truncated):\n{snippet}"
                ) from e
        except Exception as e:
            last_err = e
            if not retry_once or attempt >= 2:
                raise
            time.sleep(1.0)


def summarize_panel(
    panel: PanelManifest,
    ocr_text: str | None,
    model: str,
    *,
    raw_output_dir: Path | None = None,
    print_raw: bool = False,
) -> PanelSummary:
    """Summarize one individual panel image."""
    client = OpenAI()

    prompt_text = prompts.PANEL_PROMPT.strip()
    prompt_text += f"\n\nPanel id: {panel.panel_id}\n"
    if ocr_text:
        prompt_text += "\nOCR (may be noisy; prefer what you can directly read in the image):\n"
        prompt_text += ocr_text.strip()[:12000]

    raw_output_file = None
    if raw_output_dir is not None:
        raw_output_file = Path(raw_output_dir) / f"{panel.panel_id}.raw.txt"

    data = _responses_json_call(
        client=client,
        model=model,
        prompt_text=prompt_text,
        image_paths=[Path(panel.cropped_image_path)],
        raw_output_file=raw_output_file,
        print_raw=print_raw,
    )

    data["panel_id"] = panel.panel_id
    data = _normalize_panel_summary_payload(data, panel)
    return PanelSummary.model_validate(data)


def _normalize_resolved_characters(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, list):
        characters: list[dict[str, Any]] = []
        for item in value:
            if isinstance(item, dict):
                characters.append(
                    {
                        "name": _normalize_str(item.get("name")) or None,
                        "visual_label": _normalize_str(item.get("visual_label")),
                        "confidence": _normalize_str(item.get("confidence")) or "uncertain",
                        "evidence": _normalize_str_list(item.get("evidence")),
                    }
                )
            else:
                characters.append(
                    {
                        "name": None,
                        "visual_label": _normalize_str(item),
                        "confidence": "uncertain",
                        "evidence": [],
                    }
                )
        return characters
    return [{"name": None, "visual_label": _normalize_str(value), "confidence": "uncertain", "evidence": []}]


def _normalize_contextual_panel_payload(
    data: JsonObject,
    panel_summary: PanelSummary,
) -> JsonObject:
    data["panel_id"] = panel_summary.panel_id
    data["reading_order"] = _normalize_int_field(
        data.get("reading_order"), fallback=panel_summary.reading_order
    )
    data["resolved_characters"] = _normalize_resolved_characters(
        data.get("resolved_characters")
    )
    data["continuity_links"] = _normalize_str_list(data.get("continuity_links"))
    data["panel_role"] = _normalize_str(data.get("panel_role")) or "other"
    data["setup_payoff_relation"] = data.get("setup_payoff_relation")
    data["joke_or_dramatic_mechanism"] = _normalize_str(
        data.get("joke_or_dramatic_mechanism")
    )
    data["corrected_story_function"] = _normalize_str(
        data.get("corrected_story_function")
    )
    data["adaptation_notes"] = _normalize_str_list(data.get("adaptation_notes"))
    data["uncertainty_notes"] = _normalize_str_list(data.get("uncertainty_notes"))
    data["concise_contextual_summary"] = _normalize_str(
        data.get("concise_contextual_summary")
    )
    return data


def summarize_contextual_panel(
    panel_summary: PanelSummary,
    previous_panel_summaries: list[PanelSummary],
    cast_context: dict | None,
    model: str,
) -> ContextualPanelInterpretation:
    client = OpenAI()
    prompt_text = prompts.CONTEXTUAL_PANEL_INTERPRETATION_PROMPT.strip()
    if cast_context:
        prompt_text += "\n\nKnown cast context (JSON):\n"
        prompt_text += json.dumps(cast_context, ensure_ascii=False)
    if previous_panel_summaries:
        prompt_text += "\n\nPrevious local panel context (compact JSON array):\n"
        prompt_text += json.dumps(
            [_compact_panel_context(ps) for ps in previous_panel_summaries],
            ensure_ascii=False,
        )
    prompt_text += "\n\nCurrent panel summary (JSON object):\n"
    prompt_text += json.dumps(panel_summary.model_dump(), ensure_ascii=False)
    if panel_summary.dialogue_notes:
        prompt_text += "\n\nOCR/dialogue notes (if available):\n"
        prompt_text += json.dumps(panel_summary.dialogue_notes, ensure_ascii=False)

    data = _responses_json_call(
        client=client,
        model=model,
        prompt_text=prompt_text,
        image_paths=[],
    )

    data = _normalize_contextual_panel_payload(data, panel_summary)
    return ContextualPanelInterpretation.model_validate(data)


def summarize_contextual_panels(
    panel_summaries: list[PanelSummary],
    cast_context: dict | None,
    model: str,
    *,
    context_window: int = 3,
) -> list[ContextualPanelInterpretation]:
    """Interpret panels with bounded local history.

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


def summarize_beats_from_contextual_panel_interpretations(
    contextual_interpretations: list[ContextualPanelInterpretation],
    model: str,
) -> BeatSummary:
    """Group contextual panel interpretations into coherent narrative beats."""
    client = OpenAI()
    serialized = [ci.model_dump() for ci in contextual_interpretations]

    prompt_text = prompts.BEAT_SUMMARY_PROMPT.strip()
    prompt_text += "\n\nPanel summaries (JSON array):\n"
    prompt_text += json.dumps(serialized, ensure_ascii=False)

    data = _responses_json_call(
        client=client,
        model=model,
        prompt_text=prompt_text,
        image_paths=[],
    )

    return BeatSummary.model_validate(data)


def summarize_beats(
    panel_summaries: list[PanelSummary],
    model: str,
) -> BeatSummary:
    """Group panel summaries into coherent narrative beats."""
    client = OpenAI()
    serialized = [ps.model_dump() for ps in panel_summaries]

    prompt_text = prompts.BEAT_SUMMARY_PROMPT.strip()
    prompt_text += "\n\nPanel summaries (JSON array):\n"
    prompt_text += json.dumps(serialized, ensure_ascii=False)

    data = _responses_json_call(
        client=client,
        model=model,
        prompt_text=prompt_text,
        image_paths=[],
    )

    return BeatSummary.model_validate(data)


def summarize_chapter_from_beats(
    title: str,
    beat_summary: BeatSummary,
    model: str,
) -> ChapterSummary:
    """Synthesize a chapter summary from narrative beats."""
    client = OpenAI()
    serialized = beat_summary.model_dump()

    prompt_text = prompts.BEAT_CHAPTER_SYNTHESIS_PROMPT.strip()
    prompt_text += "\n\nChapter title:\n" + title.strip() + "\n"
    prompt_text += "\nBeat summary (JSON object):\n"
    prompt_text += json.dumps(serialized, ensure_ascii=False)

    data = _responses_json_call(
        client=client,
        model=model,
        prompt_text=prompt_text,
        image_paths=[],
    )

    data["title"] = title
    return ChapterSummary.model_validate(data)


def validate_transcript_alignment(
    transcript: Transcript,
    contextual_interpretations: list[ContextualPanelInterpretation],
    *,
    beat_summary: BeatSummary | None = None,
) -> list[str]:
    warnings: list[str] = []

    contextual_ordered = sorted(contextual_interpretations, key=lambda x: x.reading_order)
    contextual_panel_ids = [ci.panel_id for ci in contextual_ordered]
    contextual_panel_id_set = set(contextual_panel_ids)

    transcript_panel_ids: list[str] = []
    for line in transcript.lines:
        if not line.panel_ids and line.line_type not in {"transition", "pause"}:
            warnings.append(f"Line {line.line_id} has empty panel_ids (type={line.line_type}).")
        for pid in line.panel_ids:
            transcript_panel_ids.append(pid)
            if pid not in contextual_panel_id_set:
                warnings.append(f"Unknown panel_id in transcript: {pid} (line {line.line_id}).")

    covered = set(transcript_panel_ids)
    missing = [pid for pid in contextual_panel_ids if pid not in covered]
    if missing:
        warnings.append(f"Missing panels in transcript coverage: {', '.join(missing[:50])}")
        if len(missing) > 50:
            warnings.append(f"Missing panels list truncated ({len(missing)} total).")

    if beat_summary is not None:
        beat_ids = {b.beat_id for b in beat_summary.beats if b.beat_id}
        for line in transcript.lines:
            if line.beat_id and line.beat_id not in beat_ids:
                warnings.append(f"Unknown beat_id in transcript: {line.beat_id} (line {line.line_id}).")

    # Panel ordering sanity: do not go backward unless the line has no panels.
    index_by_panel = {pid: idx for idx, pid in enumerate(contextual_panel_ids)}
    last_idx = -1
    for line in transcript.lines:
        if not line.panel_ids:
            continue
        resolved = [index_by_panel.get(pid) for pid in line.panel_ids if pid in index_by_panel]
        if not resolved:
            continue
        current_min = min(resolved)
        if current_min < last_idx:
            warnings.append(
                f"Transcript panel ordering goes backward at line {line.line_id}."
            )
        last_idx = max(last_idx, max(resolved))

    return warnings


def generate_transcript_from_beats(
    title: str,
    beat_summary: BeatSummary,
    contextual_interpretations: list[ContextualPanelInterpretation],
    model: str,
) -> Transcript:
    client = OpenAI()

    payload = {
        "title": title,
        "beats": beat_summary.model_dump(),
        "contextual_panel_interpretations": [
            ci.model_dump()
            for ci in sorted(contextual_interpretations, key=lambda x: x.reading_order)
        ],
    }

    prompt_text = prompts.TRANSCRIPT_GENERATION_PROMPT.strip()
    prompt_text += "\n\nInput JSON:\n"
    prompt_text += json.dumps(payload, ensure_ascii=False)

    data = _responses_json_call(
        client=client,
        model=model,
        prompt_text=prompt_text,
        image_paths=[],
    )

    data = _normalize_transcript_payload(data, title=title)
    transcript = Transcript.model_validate(data)

    warnings = validate_transcript_alignment(
        transcript,
        contextual_interpretations=contextual_interpretations,
        beat_summary=beat_summary,
    )
    if warnings:
        transcript.unresolved_or_uncertain = list(
            dict.fromkeys([*transcript.unresolved_or_uncertain, *warnings])
        )

    return transcript


def repair_transcript_alignment(
    transcript: Transcript,
    contextual_interpretations: list[ContextualPanelInterpretation],
    warnings: list[str],
    model: str,
) -> Transcript:
    client = OpenAI()

    payload = {
        "title": transcript.title,
        "transcript": transcript.model_dump(),
        "contextual_panel_interpretations": [
            ci.model_dump()
            for ci in sorted(contextual_interpretations, key=lambda x: x.reading_order)
        ],
        "alignment_warnings": warnings,
    }

    prompt_text = prompts.TRANSCRIPT_ALIGNMENT_REPAIR_PROMPT.strip()
    prompt_text += "\n\nInput JSON:\n"
    prompt_text += json.dumps(payload, ensure_ascii=False)

    data = _responses_json_call(
        client=client,
        model=model,
        prompt_text=prompt_text,
        image_paths=[],
    )

    data = _normalize_transcript_payload(data, title=transcript.title)
    repaired = Transcript.model_validate(data)
    repaired_warnings = validate_transcript_alignment(
        repaired,
        contextual_interpretations=contextual_interpretations,
    )
    if repaired_warnings:
        repaired.unresolved_or_uncertain = list(
            dict.fromkeys([*repaired.unresolved_or_uncertain, *repaired_warnings])
        )
    return repaired



