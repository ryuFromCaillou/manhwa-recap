from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import io_utils, panelize
from .config import (
    DEFAULT_MODEL,
    DEFAULT_OUTPUT_FORMAT,
    AppConfig,
)
from .ocr import run_ocr
from .schemas import BeatSummary, ChapterSummary, PanelManifest, PanelSummary
from .summarize import (
    summarize_beats_from_contextual_panel_interpretations,
    summarize_chapter_from_beats,
    summarize_contextual_panels,
    summarize_panel,
)


def _build_parser() -> argparse.ArgumentParser:
    """Create the top-level CLI parser and subcommands."""
    p = argparse.ArgumentParser(prog="manhwa-recap")
    sub = p.add_subparsers(dest="cmd", required=True)

    ps = sub.add_parser("panel-summarize", help="Summarize a chapter using panelized images")
    ps.add_argument("input_dir", type=Path, help="Folder of ordered images (e.g. input/chapter_001)")
    ps.add_argument("--title", required=True, help="Chapter title for the output")
    ps.add_argument("--model", default=DEFAULT_MODEL)
    ps.add_argument(
        "--output-format",
        default=DEFAULT_OUTPUT_FORMAT,
        choices=["text", "json", "both"],
        help="Controls what is printed to stdout (files are still written).",
    )
    ps.add_argument("--use-ocr", action="store_true")
    ps.add_argument(
        "--context-window",
        type=int,
        default=3,
        help="Number of previous panels to include during contextual panel interpretation.",
    )
    ps.add_argument("--output-root", type=Path, default=Path("output"))
    ps.add_argument(
        "--raw-responses-dir",
        type=Path,
        default=None,
        help="Directory to write raw model responses (one file per call)",
    )
    ps.add_argument(
        "--stream-raw",
        action="store_true",
        help="Print raw model outputs to stdout as they are received",
    )

    p_panel = sub.add_parser("panelize", help="Detect and crop panels from a chapter folder")
    p_panel.add_argument("input_dir", type=Path, help="Folder of ordered images (e.g. input/chapter_001)")
    p_panel.add_argument("--output-root", type=Path, default=Path("output"))
    p_panel.add_argument("--debug", action="store_true", help="Write debug images with detected panel boxes")
    p_panel.add_argument(
        "--detector",
        default="builtin",
        choices=["builtin", "external"],
        help="Which panel detector to use.",
    )
    p_panel.add_argument("--gutter-mode", default="auto", choices=["auto", "white", "black"])
    p_panel.add_argument("--white-threshold", type=int, default=245)
    p_panel.add_argument("--black-threshold", type=int, default=15)
    p_panel.add_argument("--min-area", type=int, default=20_000)
    p_panel.add_argument("--padding", type=int, default=8)
    return p


def _chapter_output_dir(input_dir: Path, output_root: Path) -> Path:
    """Map an input folder name to an output folder under `output_root`."""
    return output_root / input_dir.name


def _write_outputs(out_dir: Path, chapter: ChapterSummary) -> tuple[Path, Path]:
    """Write `summary.json` and `summary.txt` and return their paths."""
    summary_json_path = out_dir / "summary.json"
    summary_txt_path = out_dir / "summary.txt"
    io_utils.write_json(summary_json_path, io_utils.to_jsonable(chapter))
    io_utils.write_text(
        summary_txt_path,
        io_utils.render_summary_text(
            title=chapter.title,
            overall_summary=chapter.overall_summary,
            major_events=chapter.major_events,
            characters_mentioned=chapter.characters_mentioned,
            unresolved_or_uncertain=chapter.unresolved_or_uncertain,
        ),
    )
    return summary_txt_path, summary_json_path


def _cmd_panel_summarize(args: argparse.Namespace) -> int:
    """Run the panel summarization pipeline: OCR panels → summarize panels → group beats → chapter synthesis."""
    try:
        AppConfig.load()
    except Exception as e:
        print(str(e), file=sys.stderr)
        return 2

    out_dir = _chapter_output_dir(args.input_dir, args.output_root)
    panels_dir = out_dir / "panels"
    manifest_path = panels_dir / "manifest.json"

    if not manifest_path.exists():
        print(f"Panel manifest not found: {manifest_path}. Run 'panelize' first.", file=sys.stderr)
        return 2

    try:
        manifest_data = io_utils.read_json(manifest_path)
        manifests = [PanelManifest.model_validate(m) for m in manifest_data]
    except Exception as e:
        print(f"Failed to load panel manifest: {e}", file=sys.stderr)
        return 2

    ocr_map: dict[str, str] = {}
    if args.use_ocr:
        ocr_results = []
        for m in manifests:
            try:
                r = run_ocr(Path(m.cropped_image_path))
                ocr_map[m.panel_id] = r.text
                ocr_results.append({
                    "panel_id": m.panel_id,
                    "text": r.text,
                    "confidence": r.confidence,
                    "source_image_path": m.source_image_path,
                    "cropped_image_path": m.cropped_image_path,
                })
            except Exception as e:
                print(f"OCR failed for {m.panel_id}: {e}", file=sys.stderr)
                return 2
        io_utils.write_json(out_dir / "panel_ocr.json", ocr_results)

    panel_summaries: list[PanelSummary] = []
    failed_panels: list[str] = []
    for m in manifests:
        try:
                ps = summarize_panel(
                    m,
                    ocr_text=ocr_map.get(m.panel_id),
                    model=args.model,
                    raw_output_dir=args.raw_responses_dir,
                    print_raw=args.stream_raw,
                )
                panel_summaries.append(ps)
        except Exception as e:
            failed_panels.append(m.panel_id)
            print(f"Panel summarization failed for {m.panel_id}: {e}", file=sys.stderr)

    io_utils.write_json(out_dir / "panel_summaries.json", io_utils.to_jsonable(panel_summaries))

    if not panel_summaries:
        print("No panel summaries succeeded; cannot proceed.", file=sys.stderr)
        if failed_panels:
            print("Failed panels: " + ", ".join(failed_panels), file=sys.stderr)
        return 3

    cast_context = io_utils.load_optional_cast_context(args.input_dir, out_dir)
    try:
        contextual_interpretations = summarize_contextual_panels(
            panel_summaries=panel_summaries,
            cast_context=cast_context,
            model=args.model,
            context_window=args.context_window,
        )
    except Exception as e:
        print(f"Contextual interpretation failed: {e}", file=sys.stderr)
        return 3

    io_utils.write_json(
        out_dir / "contextual_panel_interpretations.json",
        io_utils.to_jsonable(contextual_interpretations),
    )

    try:
        beat_summary = summarize_beats_from_contextual_panel_interpretations(
            contextual_interpretations=contextual_interpretations,
            model=args.model,
        )
    except Exception as e:
        print(f"Beat grouping failed: {e}", file=sys.stderr)
        return 3

    io_utils.write_json(out_dir / "beat_summary.json", io_utils.to_jsonable(beat_summary))

    try:
        chapter = summarize_chapter_from_beats(args.title, beat_summary=beat_summary, model=args.model)
    except Exception as e:
        print(f"Chapter synthesis failed: {e}", file=sys.stderr)
        return 3

    summary_txt_path, summary_json_path = _write_outputs(out_dir, chapter)

    if failed_panels:
        print("Warning: some panels failed: " + ", ".join(failed_panels), file=sys.stderr)

    if args.output_format == "json":
        print(str(summary_json_path))
    elif args.output_format == "text":
        print(str(summary_txt_path))
    else:
        print(str(summary_txt_path))
        print(str(summary_json_path))
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point; returns a process exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.cmd == "panelize":
        return _cmd_panelize(args)
    if args.cmd == "panel-summarize":
        return _cmd_panel_summarize(args)
    print(f"Unknown command: {args.cmd}", file=sys.stderr)
    return 2


def _cmd_panelize(args: argparse.Namespace) -> int:
    """Run the panelization pipeline for a chapter folder."""
    try:
        AppConfig.load()
    except Exception as e:
        print(str(e), file=sys.stderr)
        return 2

    try:
        manifest_path = panelize.panelize_chapter(
            input_dir=args.input_dir,
            output_root=args.output_root,
            detector=args.detector,
            gutter_mode=args.gutter_mode,
            white_threshold=args.white_threshold,
            black_threshold=args.black_threshold,
            min_area=args.min_area,
            padding=args.padding,
            debug=args.debug,
        )
    except Exception as e:
        print(f"Panelization failed: {e}", file=sys.stderr)
        return 2

    print(str(manifest_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
