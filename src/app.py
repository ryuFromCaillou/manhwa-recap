from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import io_utils
from .config import (
    DEFAULT_MODEL,
    DEFAULT_OUTPUT_FORMAT,
    AppConfig,
)


ICM_RUNS_ROOT = Path("icm") / "_runs"
STAGE_01 = "01_panel_extraction"
STAGE_02 = "02_panel_summary"
STAGE_03 = "03_contextual_interpretation"
STAGE_04 = "04_beat_summary"
STAGE_05 = "05_transcript_generation"


def _build_parser() -> argparse.ArgumentParser:
    """Create the top-level CLI parser and subcommands."""
    p = argparse.ArgumentParser(prog="manhwa-recap")
    sub = p.add_subparsers(dest="cmd", required=True)

    ir = sub.add_parser(
        "init-run",
        help="Create/refresh an ICM run folder and copy chapter inputs into it",
    )
    ir.add_argument(
        "source_input_dir",
        type=Path,
        help="Folder of ordered images (e.g. input/chapter_001)",
    )
    ir.add_argument(
        "--chapter-id",
        default=None,
        help="Override run folder name (default: source folder name)",
    )
    ir.add_argument("--output-root", type=Path, default=ICM_RUNS_ROOT)
    ir.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing images in the run inputs folder",
    )

    ps = sub.add_parser("panel-summarize", help="Summarize a chapter using panelized images")
    ps.add_argument(
        "input_dir",
        type=Path,
        help="Folder of ordered images (recommended: icm/_runs/<chapter_id>/inputs)",
    )
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
    ps.add_argument("--output-root", type=Path, default=ICM_RUNS_ROOT)
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
    p_panel.add_argument(
        "input_dir",
        type=Path,
        help="Folder of ordered images (recommended: icm/_runs/<chapter_id>/inputs)",
    )
    p_panel.add_argument("--output-root", type=Path, default=ICM_RUNS_ROOT)
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

    t = sub.add_parser("transcript", help="Generate aligned transcript from reviewed beats and panels")
    t.add_argument("chapter_dir", type=Path)
    t.add_argument("--title", required=True)
    t.add_argument("--model", default=DEFAULT_MODEL)
    t.add_argument(
        "--output-format",
        default=DEFAULT_OUTPUT_FORMAT,
        choices=["text", "json", "both"],
        help="Controls what is printed to stdout (files are still written).",
    )
    t.add_argument("--repair-alignment", action="store_true")
    return p


def _run_dir_for_input(input_dir: Path, output_root: Path) -> Path:
    """
    Map an input folder to its run folder under `output_root`.

    Supports:
    - Canonical ICM layout: `icm/_runs/<chapter_id>/inputs` -> `icm/_runs/<chapter_id>`
    - Legacy/simple layout: `<some_folder_name>` -> `icm/_runs/<some_folder_name>`
    """
    # Canonical ICM layout: output_root/<chapter_id>/inputs
    if input_dir.name == "inputs" and input_dir.parent.parent == output_root:
        return input_dir.parent
    return output_root / input_dir.name


def _stage_dir(run_dir: Path, stage: str) -> Path:
    return run_dir / stage


def _cmd_init_run(args: argparse.Namespace) -> int:
    chapter_id = args.chapter_id or args.source_input_dir.name
    run_dir = args.output_root / chapter_id
    dest_inputs_dir = run_dir / "inputs"

    try:
        copied, skipped = io_utils.copy_input_images_to_dir(
            args.source_input_dir,
            dest_inputs_dir,
            overwrite=bool(args.overwrite),
        )
    except Exception as e:
        print(f"init-run failed: {e}", file=sys.stderr)
        return 2

    print(str(dest_inputs_dir))
    if skipped and not args.overwrite:
        print(
            f"Skipped {skipped} existing file(s); re-run with --overwrite to refresh.",
            file=sys.stderr,
        )
    if copied:
        print(f"Copied {copied} file(s) into {dest_inputs_dir}.", file=sys.stderr)
    return 0


def _resolve_run_dir(chapter_dir: Path) -> Path:
    """
    Resolve a user-provided `chapter_dir` to a run directory.

    Accepts:
    - run root: `.../icm/_runs/chapter_001`
    - stage folder: `.../icm/_runs/chapter_001/04_beat_summary`
    - legacy flat output folder: `.../output/chapter_001`
    """
    if chapter_dir.name == "inputs":
        return chapter_dir.parent
    if (chapter_dir / STAGE_01).exists() or (chapter_dir / STAGE_04).exists():
        return chapter_dir
    if chapter_dir.name.startswith("0") and any(
        (chapter_dir.parent / stage).exists()
        for stage in (STAGE_01, STAGE_02, STAGE_03, STAGE_04, STAGE_05)
    ):
        return chapter_dir.parent
    return chapter_dir


def _write_outputs(out_dir: Path, chapter: object) -> tuple[Path, Path]:
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


def _write_transcript_outputs(out_dir: Path, transcript: object) -> tuple[Path, Path]:
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


def _cmd_panel_summarize(args: argparse.Namespace) -> int:
    """Run the panel summarization pipeline: OCR panels → summarize panels → group beats → chapter synthesis."""
    try:
        AppConfig.load()
    except Exception as e:
        print(str(e), file=sys.stderr)
        return 2

    run_dir = _run_dir_for_input(args.input_dir, args.output_root)
    stage01_dir = _stage_dir(run_dir, STAGE_01)
    stage02_dir = _stage_dir(run_dir, STAGE_02)
    stage03_dir = _stage_dir(run_dir, STAGE_03)
    stage04_dir = _stage_dir(run_dir, STAGE_04)

    panels_dir = stage01_dir / "panels"
    manifest_path = panels_dir / "manifest.json"

    if not manifest_path.exists():
        print(f"Panel manifest not found: {manifest_path}. Run 'panelize' first.", file=sys.stderr)
        return 2

    try:
        from .schemas import PanelManifest
        from .summarize import (
            summarize_beats_from_contextual_panel_interpretations,
            summarize_chapter_from_beats,
            summarize_contextual_panels,
            summarize_panel,
        )

        manifest_data = io_utils.read_json(manifest_path)
        manifests = [PanelManifest.model_validate(m) for m in manifest_data]
    except Exception as e:
        print(f"Failed to load panel manifest: {e}", file=sys.stderr)
        return 2

    ocr_map: dict[str, str] = {}
    if args.use_ocr:
        from .ocr import run_ocr

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
        io_utils.write_json(stage02_dir / "panel_ocr.json", ocr_results)

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

    io_utils.write_json(stage02_dir / "panel_summaries.json", io_utils.to_jsonable(panel_summaries))

    if not panel_summaries:
        print("No panel summaries succeeded; cannot proceed.", file=sys.stderr)
        if failed_panels:
            print("Failed panels: " + ", ".join(failed_panels), file=sys.stderr)
        return 3

    cast_context = io_utils.load_optional_cast_context(args.input_dir, stage02_dir)
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
        stage03_dir / "contextual_panel_interpretations.json",
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

    io_utils.write_json(stage04_dir / "beat_summary.json", io_utils.to_jsonable(beat_summary))

    try:
        chapter = summarize_chapter_from_beats(args.title, beat_summary=beat_summary, model=args.model)
    except Exception as e:
        print(f"Chapter synthesis failed: {e}", file=sys.stderr)
        return 3

    summary_txt_path, summary_json_path = _write_outputs(stage04_dir, chapter)

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


def _cmd_transcript(args: argparse.Namespace) -> int:
    try:
        AppConfig.load()
    except Exception as e:
        print(str(e), file=sys.stderr)
        return 2

    run_dir = _resolve_run_dir(args.chapter_dir)
    beat_path = run_dir / STAGE_04 / "beat_summary.json"
    contextual_path = run_dir / STAGE_03 / "contextual_panel_interpretations.json"

    try:
        from .schemas import BeatSummary, ContextualPanelInterpretation
        from .summarize import (
            generate_transcript_from_beats,
            repair_transcript_alignment,
            validate_transcript_alignment,
        )

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

    if args.repair_alignment:
        warnings = validate_transcript_alignment(
            transcript,
            contextual_interpretations=contextual,
            beat_summary=beat_summary,
        )
        if warnings:
            try:
                transcript = repair_transcript_alignment(
                    transcript=transcript,
                    contextual_interpretations=contextual,
                    warnings=warnings,
                    model=args.model,
                )
            except Exception as e:
                print(f"Transcript alignment repair failed: {e}", file=sys.stderr)
                return 3

    out_dir = run_dir / STAGE_05
    txt_path, json_path = _write_transcript_outputs(out_dir, transcript)

    if args.output_format == "json":
        print(str(json_path))
    elif args.output_format == "text":
        print(str(txt_path))
    else:
        print(str(txt_path))
        print(str(json_path))

    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point; returns a process exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.cmd == "init-run":
        return _cmd_init_run(args)
    if args.cmd == "panelize":
        return _cmd_panelize(args)
    if args.cmd == "panel-summarize":
        return _cmd_panel_summarize(args)
    if args.cmd == "transcript":
        return _cmd_transcript(args)
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
        from . import panelize

        run_dir = _run_dir_for_input(args.input_dir, args.output_root)
        stage01_dir = _stage_dir(run_dir, STAGE_01)
        manifest_path = panelize.panelize_chapter(
            input_dir=args.input_dir,
            output_root=args.output_root,
            chapter_dir=stage01_dir,
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
