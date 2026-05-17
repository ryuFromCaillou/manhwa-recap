from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

from .schemas import Transcript


ALLOWED_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


_NS_RE = re.compile(r"(\d+)")


def natural_sort_key(path: Path) -> list[object]:
    """
    Build a natural-sort key for filenames.

    This sorts `10.png` after `2.png` by splitting numeric spans.
    """
    parts: list[object] = []
    for chunk in _NS_RE.split(path.name):
        if chunk.isdigit():
            parts.append(int(chunk))
        else:
            parts.append(chunk.lower())
    return parts


def discover_input_images(input_dir: Path) -> list[Path]:
    """
    Discover and return supported images in an input folder, in filename order.

    Args:
        input_dir: Folder containing ordered chapter screenshots.

    Returns:
        List of image paths sorted in natural filename order.

    Raises:
        FileNotFoundError: If `input_dir` does not exist.
        NotADirectoryError: If `input_dir` is not a directory.
        ValueError: If no valid images are found.
    """
    if not input_dir.exists():
        raise FileNotFoundError(f"Input folder does not exist: {input_dir}")
    if not input_dir.is_dir():
        raise NotADirectoryError(f"Input path is not a folder: {input_dir}")

    images = [
        p
        for p in input_dir.iterdir()
        if p.is_file() and p.suffix.lower() in ALLOWED_EXTS
    ]
    images.sort(key=natural_sort_key)
    if not images:
        raise ValueError(
            f"No valid images found in {input_dir} (allowed: {sorted(ALLOWED_EXTS)})"
        )
    return images


def ensure_dir(path: Path) -> None:
    """Create `path` (and parents) if it does not exist."""
    path.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, obj: Any) -> None:
    """Write a JSON file (UTF-8) with stable formatting."""
    ensure_dir(path.parent)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    """Read a JSON file (UTF-8)."""
    return json.loads(path.read_text(encoding="utf-8"))


def load_optional_cast_context(input_dir: Path, out_dir: Path) -> dict | None:
    """Load optional cast context from input or output folder."""
    candidates = [
        input_dir / "cast_context.json",
        out_dir / "cast_context.json",
    ]
    for path in candidates:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    return None


def write_text(path: Path, text: str) -> None:
    """Write a UTF-8 text file, ensuring it ends with a newline."""
    ensure_dir(path.parent)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def to_jsonable(obj: Any) -> Any:
    """
    Convert common objects to JSON-serializable structures.

    Supports Pydantic models via `model_dump()` and `Path` objects.
    """
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, dict):
        return {k: to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(v) for v in obj]
    return obj


def render_summary_text(
    title: str,
    overall_summary: str,
    major_events: Iterable[str],
    characters_mentioned: Iterable[str],
    unresolved_or_uncertain: Iterable[str],
) -> str:
    """
    Render a human-readable chapter summary text block.

    Returns:
        A single string suitable for writing to `summary.txt`.
    """
    lines: list[str] = []
    lines.append(f"Title: {title}")
    lines.append("")
    lines.append("Overall summary:")
    lines.append(overall_summary.strip())
    lines.append("")
    lines.append("Major events:")
    for item in major_events:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("Characters mentioned:")
    for item in characters_mentioned:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("Unresolved or uncertain:")
    for item in unresolved_or_uncertain:
        lines.append(f"- {item}")
    return "\n".join(lines).strip() + "\n"


def render_transcript_text(title: str, transcript: Transcript) -> str:
    lines: list[str] = []
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
        lines.append((line.text or "").strip())

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
        lines.append("")

    return "\n".join(lines).strip() + "\n"
