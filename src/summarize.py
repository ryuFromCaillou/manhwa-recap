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


def _extract_json_object(text: str) -> JsonObject:
    """
    Extract the first JSON object found in `text`.

    The model may wrap JSON in prose or a code fence; this tries to be forgiving.
    """
    s = text.strip()
    if s.startswith("```"):
        s = s.strip("`")
    start = s.find("{")
    end = s.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Model did not return a JSON object.")
    payload = s[start : end + 1]
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


def _responses_json_call(
    *,
    client: OpenAI,
    model: str,
    prompt_text: str,
    image_paths: list[Path],
    retry_once: bool = True,
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
            return _extract_json_object(text)
        except Exception as e:
            last_err = e
            if not retry_once or attempt >= 2:
                raise
            time.sleep(1.0)


def summarize_panel(
    panel: PanelManifest,
    ocr_text: str | None,
    model: str,
) -> PanelSummary:
    """Summarize one individual panel image."""
    client = OpenAI()

    prompt_text = prompts.PANEL_PROMPT.strip()
    prompt_text += f"\n\nPanel id: {panel.panel_id}\n"
    if ocr_text:
        prompt_text += "\nOCR (may be noisy; prefer what you can directly read in the image):\n"
        prompt_text += ocr_text.strip()[:12000]

    data = _responses_json_call(
        client=client,
        model=model,
        prompt_text=prompt_text,
        image_paths=[Path(panel.cropped_image_path)],
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
        prompt_text += "\n\nPrevious panel summaries (JSON array):\n"
        prompt_text += json.dumps(
            [ps.model_dump() for ps in previous_panel_summaries],
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



