from __future__ import annotations

import argparse
from pathlib import Path
from PIL import Image


def crop_grid(image_path: Path, output_dir: Path, rows: int, cols: int) -> list[Path]:
    """Crop an image into a regular grid and save each tile."""
    output_dir.mkdir(parents=True, exist_ok=True)
    img = Image.open(image_path)
    img.load()
    width, height = img.size
    tile_width = width // cols
    tile_height = height // rows

    cropped_paths: list[Path] = []
    idx = 1
    for row in range(rows):
        for col in range(cols):
            left = col * tile_width
            top = row * tile_height
            right = width if col == cols - 1 else left + tile_width
            bottom = height if row == rows - 1 else top + tile_height
            crop = img.crop((left, top, right, bottom))
            out_path = output_dir / f"panel_{idx:03d}.png"
            crop.save(out_path, format="PNG", optimize=True)
            cropped_paths.append(out_path)
            idx += 1
    return cropped_paths


def crop_list(image_path: Path, output_dir: Path, boxes: list[tuple[int, int, int, int]]) -> list[Path]:
    """Crop an image using explicit bounding boxes."""
    output_dir.mkdir(parents=True, exist_ok=True)
    img = Image.open(image_path)
    img.load()

    cropped_paths: list[Path] = []
    for idx, (left, top, right, bottom) in enumerate(boxes, start=1):
        crop = img.crop((left, top, right, bottom))
        out_path = output_dir / f"panel_{idx:03d}.png"
        crop.save(out_path, format="PNG", optimize=True)
        cropped_paths.append(out_path)
    return cropped_paths


def _parse_box(value: str) -> tuple[int, int, int, int]:
    parts = [int(x.strip()) for x in value.split(",") if x.strip()]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("Crop box must be 4 comma-separated integers: left,top,right,bottom")
    return tuple(parts)  # type: ignore[return-value]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Crop a page image into clipped panel images for testing."
    )
    parser.add_argument("image", type=Path, help="Source page image file")
    parser.add_argument("output_dir", type=Path, help="Target folder for cropped images")
    parser.add_argument("--rows", type=int, default=1, help="Number of vertical slices")
    parser.add_argument("--cols", type=int, default=1, help="Number of horizontal slices")
    parser.add_argument(
        "--box",
        type=_parse_box,
        action="append",
        help="Explicit crop box in left,top,right,bottom format. Can be repeated.",
    )
    args = parser.parse_args()

    if args.box and (args.rows != 1 or args.cols != 1):
        parser.error("Use either --box or --rows/--cols, not both.")

    if args.box:
        cropped = crop_list(args.image, args.output_dir, args.box)
    else:
        if args.rows <= 0 or args.cols <= 0:
            parser.error("--rows and --cols must be positive integers")
        cropped = crop_grid(args.image, args.output_dir, rows=args.rows, cols=args.cols)

    print(f"Saved {len(cropped)} cropped images to {args.output_dir}")
    for path in cropped:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
