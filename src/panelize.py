from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw

from . import io_utils
from .schemas import PanelManifest


@dataclass(frozen=True)
class PanelBox:
    left: int
    top: int
    right: int
    bottom: int
    score: float | None = None
    source: str = "builtin"


def _import_cv2() -> object:
    try:
        import cv2

        return cv2
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "Panelization requires OpenCV. Install it with: pip install opencv-python"
        ) from exc


def _clamp_box(box: PanelBox, width: int, height: int) -> PanelBox:
    return PanelBox(
        left=max(0, min(box.left, width)),
        top=max(0, min(box.top, height)),
        right=max(0, min(box.right, width)),
        bottom=max(0, min(box.bottom, height)),
        score=box.score,
        source=box.source,
    )


def _box_area(box: PanelBox) -> int:
    return max(0, box.right - box.left) * max(0, box.bottom - box.top)


def _box_contains(outer: PanelBox, inner: PanelBox) -> bool:
    return (
        outer.left <= inner.left
        and outer.top <= inner.top
        and outer.right >= inner.right
        and outer.bottom >= inner.bottom
    )


def _filter_contained_boxes(boxes: list[PanelBox], max_contained_ratio: float = 0.45) -> list[PanelBox]:
    kept: list[PanelBox] = []
    for box in sorted(boxes, key=lambda b: b.score or 0.0, reverse=True):
        if any(
            _box_contains(outer, box)
            and _box_area(box) / max(1, _box_area(outer)) < max_contained_ratio
            for outer in kept
        ):
            continue
        kept.append(box)
    kept.sort(key=lambda b: (b.top, b.left))
    return kept


def detect_panel_boxes_builtin(
    image_path: Path,
    *,
    gutter_mode: str = "auto",
    white_threshold: int = 245,
    black_threshold: int = 15,
    min_area: int = 20_000,
    padding: int = 8,
) -> list[PanelBox]:
    """Builtin OpenCV panel detection using gutter/background analysis."""
    cv2 = _import_cv2()
    image = cv2.imread(str(image_path))
    if image is None:
        raise FileNotFoundError(f"Unable to load image: {image_path}")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) #greyscaled image for easier processing
    height, width = gray.shape

    if gutter_mode == "auto":
        border = 10
        top_slice = gray[:border, :] #indexing the top 10 rows of pixels to analyze the gutter/background color
        bottom_slice = gray[-border:, :]
        left_slice = gray[:, :border]
        right_slice = gray[:, -border:]
        background_mean = (
            float(cv2.mean(top_slice)[0])
            + float(cv2.mean(bottom_slice)[0])
            + float(cv2.mean(left_slice)[0])
            + float(cv2.mean(right_slice)[0])
        ) / 4.0 #average pixel intensity across the borders to determine if the gutter is more likely black or white
        gutter_mode = "black" if background_mean < 127 else "white"

    if gutter_mode == "black":
        mask = gray > black_threshold
    else:
        mask = gray < white_threshold

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 25)) #structuring element for morphological closing to connect nearby components and fill small gaps in the mask
    closed = cv2.morphologyEx(mask.astype("uint8") * 255, cv2.MORPH_CLOSE, kernel) #apply morphological closing to the binary mask to create more solid regions for contour detection
    contours_result = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = contours_result[0] if len(contours_result) == 2 else contours_result[1]

    candidate_boxes: list[PanelBox] = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if w * h < min_area:
            continue
        padded = PanelBox(
            left=x - padding,
            top=y - padding,
            right=x + w + padding,
            bottom=y + h + padding,
            score=float(w * h),
            source="builtin",
        )
        candidate_boxes.append(_clamp_box(padded, width=width, height=height))

    boxes = _filter_contained_boxes(candidate_boxes)
    boxes = [box for box in boxes if _box_area(box) >= min_area]
    return boxes


def detect_panel_boxes_external(
    image_path: Path,
    *,
    gutter_mode: str = "auto",
    white_threshold: int = 245,
    black_threshold: int = 15,
    min_area: int = 20_000,
    padding: int = 8,
) -> list[PanelBox]:
    raise NotImplementedError(
        "External panel detection is not implemented yet. Use --detector builtin or register an external detector."
    )


def detect_panel_boxes(
    image_path: Path,
    *,
    detector: str = "builtin",
    gutter_mode: str = "auto",
    white_threshold: int = 245,
    black_threshold: int = 15,
    min_area: int = 20_000,
    padding: int = 8,
) -> list[PanelBox]:
    if detector == "builtin":
        return detect_panel_boxes_builtin(
            image_path,
            gutter_mode=gutter_mode,
            white_threshold=white_threshold,
            black_threshold=black_threshold,
            min_area=min_area,
            padding=padding,
        )
    if detector == "external":
        return detect_panel_boxes_external(
            image_path,
            gutter_mode=gutter_mode,
            white_threshold=white_threshold,
            black_threshold=black_threshold,
            min_area=min_area,
            padding=padding,
        )
    raise ValueError(
        f"Unsupported detector '{detector}'. Choose from: builtin, external."
    )


def crop_panels_from_page(
    image_path: Path,
    output_dir: Path,
    *,
    page_index: int,
    reading_order_start: int,
    detector: str = "builtin",
    gutter_mode: str = "auto",
    white_threshold: int = 245,
    black_threshold: int = 15,
    min_area: int = 20_000,
    padding: int = 8,
) -> tuple[list[PanelManifest], int]:
    """Crop detected panels from a single page and return their manifests."""
    boxes = detect_panel_boxes(
        image_path,
        detector=detector,
        gutter_mode=gutter_mode,
        white_threshold=white_threshold,
        black_threshold=black_threshold,
        min_area=min_area,
        padding=padding,
    )
    io_utils.ensure_dir(output_dir)

    source_image_path = str(image_path)
    manifests: list[PanelManifest] = []
    image = Image.open(image_path)
    image.load()

    reading_order = reading_order_start
    for panel_index, box in enumerate(boxes, start=1):
        cropped = image.crop((box.left, box.top, box.right, box.bottom))
        panel_id = f"page_{page_index:03d}_panel_{panel_index:03d}"
        cropped_image_path = output_dir / f"{panel_id}.png"
        cropped.save(cropped_image_path, format="PNG", optimize=True)

        manifests.append(
            PanelManifest(
                panel_id=panel_id,
                source_image_path=source_image_path,
                cropped_image_path=str(cropped_image_path),
                page_index=page_index,
                panel_index=panel_index,
                reading_order=reading_order,
                bbox=[box.left, box.top, box.right, box.bottom],
            )
        )
        reading_order += 1

    return manifests, reading_order


def draw_debug_boxes(
    image_path: Path,
    boxes: list[PanelBox],
    output_path: Path,
) -> None:
    """Save a debug copy of the page with detected panel boxes drawn."""
    image = Image.open(image_path)
    image.load()
    draw = ImageDraw.Draw(image)
    for box in boxes:
        draw.rectangle([box.left, box.top, box.right, box.bottom], outline="red", width=3)
        label = box.source
        if box.score is not None:
            label += f" ({int(box.score)})"
        draw.text((box.left + 4, box.top + 4), label, fill="yellow")
    io_utils.ensure_dir(output_path.parent)
    image.save(output_path, format="PNG")


def panelize_chapter(
    input_dir: Path,
    output_root: Path,
    *,
    detector: str = "builtin",
    gutter_mode: str = "auto",
    white_threshold: int = 245,
    black_threshold: int = 15,
    min_area: int = 20_000,
    padding: int = 8,
    debug: bool = False,
) -> Path:
    """Detect and crop panels for an ordered chapter folder."""
    image_paths = io_utils.discover_input_images(input_dir)
    chapter_dir = output_root / input_dir.name
    panels_dir = chapter_dir / "panels"
    io_utils.ensure_dir(panels_dir)

    debug_dir = chapter_dir / "panel_debug"
    if debug:
        io_utils.ensure_dir(debug_dir)

    all_manifests: list[PanelManifest] = []
    reading_order = 1
    for page_index, image_path in enumerate(image_paths, start=1):
        page_manifests, reading_order = crop_panels_from_page(
            image_path,
            panels_dir,
            page_index=page_index,
            reading_order_start=reading_order,
            detector=detector,
            gutter_mode=gutter_mode,
            white_threshold=white_threshold,
            black_threshold=black_threshold,
            min_area=min_area,
            padding=padding,
        )
        all_manifests.extend(page_manifests)

        if debug:
            boxes = detect_panel_boxes(
                image_path,
                detector=detector,
                gutter_mode=gutter_mode,
                white_threshold=white_threshold,
                black_threshold=black_threshold,
                min_area=min_area,
                padding=padding,
            )
            draw_debug_boxes(
                image_path,
                boxes,
                debug_dir / f"page_{page_index:03d}_boxes.png",
            )

    manifest_path = panels_dir / "manifest.json"
    io_utils.write_json(manifest_path, [io_utils.to_jsonable(m) for m in all_manifests])
    return manifest_path
