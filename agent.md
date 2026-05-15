
````text
Goal: Add a panel-level pipeline to the manhwa-recap project.

Current project state:
- app.py has a `summarize` CLI command that discovers ordered images, builds chunks, optionally runs OCR, summarizes chunks, then synthesizes a chapter summary.
- cropper.py already supports simple grid crops and explicit crop boxes using Pillow.
- ocr.py has `run_ocr(Path)` and can already OCR any image path.
- summarize.py already has reusable API call helpers and `summarize_chunk()` / `summarize_chapter()`.
- schemas.py has `ChunkManifest`, `OCRResult`, `ChunkSummary`, and `ChapterSummary`.

New target pipeline:
chapter images
→ panelize pages
→ save individual panel crops
→ write `panels/manifest.json`
→ OCR each panel
→ summarize each panel
→ group panel summaries into narrative beats
→ synthesize final chapter summary from beats

Implement in small commits.

1. Add panel schemas in `schemas.py`

Add these Pydantic models:

```python
class PanelManifest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    panel_id: str
    source_image_path: str
    cropped_image_path: str
    page_index: int
    panel_index: int
    reading_order: int
    bbox: list[int]


class PanelOCRResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    panel_id: str
    text: str
    confidence: float | None = None


class PanelSummary(BaseModel):
    model_config = ConfigDict(extra="ignore")

    panel_id: str
    reading_order: int
    visual_description: str
    dialogue_notes: list[str] = Field(default_factory=list)
    action: str
    uncertainty_notes: list[str] = Field(default_factory=list)
    concise_summary: str


class NarrativeBeat(BaseModel):
    model_config = ConfigDict(extra="ignore")

    beat_id: str
    panel_ids: list[str] = Field(default_factory=list)
    state_before: str
    trigger: str
    state_after: str
    emotional_shift: str | None = None
    story_function: str
    recap_sentence: str
    uncertainty_notes: list[str] = Field(default_factory=list)


class BeatSummary(BaseModel):
    model_config = ConfigDict(extra="ignore")

    beats: list[NarrativeBeat] = Field(default_factory=list)
    leftover_panels: list[str] = Field(default_factory=list)
````

2. Create `panelize.py`

Create a new module `panelize.py`.

Responsibilities:

* Use OpenCV to detect panel bounding boxes.
* Use Pillow to crop boxes.
* Save cropped panels under `output/<chapter_name>/panels/`.
* Write `output/<chapter_name>/panels/manifest.json`.

Implementation details:

* Use `io_utils.discover_input_images(input_dir)` for natural image ordering.
* Use OpenCV for detection:

  * load image with `cv2.imread`
  * convert to grayscale
  * create content mask with `gray < white_threshold`
  * morphologically close the mask
  * find external contours
  * convert contours to boxes
  * filter tiny boxes
  * pad boxes
  * sort by `(top, left)`
* Use Pillow for cropping.

Add a small dataclass:

```python
@dataclass
class PanelBox:
    left: int
    top: int
    right: int
    bottom: int
```

Functions to implement:

```python
def detect_panel_boxes(
    image_path: Path,
    *,
    white_threshold: int = 245,
    min_area: int = 20_000,
    padding: int = 8,
) -> list[PanelBox]:
    ...
```

```python
def crop_panels_from_page(
    image_path: Path,
    output_dir: Path,
    *,
    page_index: int,
    reading_order_start: int,
    white_threshold: int = 245,
    min_area: int = 20_000,
    padding: int = 8,
) -> tuple[list[PanelManifest], int]:
    ...
```

```python
def panelize_chapter(
    input_dir: Path,
    output_root: Path,
    *,
    white_threshold: int = 245,
    min_area: int = 20_000,
    padding: int = 8,
) -> Path:
    ...
```

The manifest item should look like:

```json
{
  "panel_id": "page_001_panel_003",
  "source_image_path": "input/chapter_001/001.png",
  "cropped_image_path": "output/chapter_001/panels/page_001_panel_003.png",
  "page_index": 1,
  "panel_index": 3,
  "reading_order": 3,
  "bbox": [0, 840, 720, 1220]
}
```

3. Add debug image support

In `panelize.py`, add:

```python
def draw_debug_boxes(
    image_path: Path,
    boxes: list[PanelBox],
    output_path: Path,
) -> None:
    ...
```

This should save a copy of the page with rectangles drawn around detected panels.

Then make `panelize_chapter(..., debug: bool = False)` optionally write:

```text
output/<chapter_name>/panel_debug/page_001_boxes.png
output/<chapter_name>/panel_debug/page_002_boxes.png
```

4. Add panel prompts in `prompts.py`

Add:

```python
PANEL_PROMPT = """You are summarizing one manhwa/comic panel.

Use the image first. Use OCR only as a noisy hint.
Do not invent character names unless visible in dialogue or already provided.
Describe only what is visible or directly stated.

Return JSON with:
- visual_description: what is visually happening in the panel
- dialogue_notes: spoken text or dialogue-based information
- action: the main story action in this panel
- uncertainty_notes: anything unclear, cropped, or hard to read
- concise_summary: 1-2 sentence summary of the panel
"""
```

Add:

```python
BEAT_TRACKING_PROMPT = """You are tracking narrative beats in a manhwa/comic sequence.

Input: ordered panel summaries and OCR notes.

A beat is a transition from one narrative state to another:
state_before → trigger/action/revelation → state_after.

Group consecutive panels into beats. Do not create a new beat unless the narrative state changes.
Preserve panel order. Do not invent character names, motives, or events.
Use uncertainty_notes when panel evidence is unclear.

Return JSON with:
- beats: list of objects with:
  - beat_id
  - panel_ids
  - state_before
  - trigger
  - state_after
  - emotional_shift
  - story_function
  - recap_sentence
  - uncertainty_notes
- leftover_panels: panels that did not clearly form a beat
"""
```

5. Add summarization functions in `summarize.py`

Add imports for the new schemas.

Add:

```python
def summarize_panel(
    panel: PanelManifest,
    ocr_text: str | None,
    model: str,
) -> PanelSummary:
    ...
```

This should be similar to `summarize_chunk()`, but:

* use `prompts.PANEL_PROMPT`
* include panel id and reading order
* attach `[Path(panel.cropped_image_path)]`
* set `data["panel_id"]`
* set `data["reading_order"]`
* return `PanelSummary.model_validate(data)`

Add:

```python
def track_beats(
    panel_summaries: list[PanelSummary],
    model: str,
    *,
    window_size: int = 12,
) -> BeatSummary:
    ...
```

Initial simple version:

* Sort panels by `reading_order`.
* Serialize summaries as JSON.
* Send all panel summaries into one API call using `BEAT_TRACKING_PROMPT`.
* No images needed.
* Validate as `BeatSummary`.

Do not overcomplicate windowing yet. Add `window_size` parameter but leave a TODO for chunked beat tracking.

6. Add CLI command: `panelize`

In `app.py`, import the new module:

```python
from . import chunker, io_utils, panelize
```

Add subcommand:

```python
pz = sub.add_parser("panelize", help="Crop ordered chapter images into individual panels")
pz.add_argument("input_dir", type=Path)
pz.add_argument("--output-root", type=Path, default=Path("output"))
pz.add_argument("--white-threshold", type=int, default=245)
pz.add_argument("--min-area", type=int, default=20_000)
pz.add_argument("--padding", type=int, default=8)
pz.add_argument("--debug", action="store_true")
```

Add command handler:

```python
def _cmd_panelize(args: argparse.Namespace) -> int:
    try:
        manifest_path = panelize.panelize_chapter(
            input_dir=args.input_dir,
            output_root=args.output_root,
            white_threshold=args.white_threshold,
            min_area=args.min_area,
            padding=args.padding,
            debug=args.debug,
        )
    except Exception as e:
        print(f"Panelizing failed: {e}", file=sys.stderr)
        return 2

    print(str(manifest_path))
    return 0
```

Update `main()`:

```python
if args.cmd == "panelize":
    return _cmd_panelize(args)
```

7. Add CLI command: `summarize-panels`

Add subcommand:

```python
sp = sub.add_parser("summarize-panels", help="Summarize panelized chapter and track narrative beats")
sp.add_argument("input_dir", type=Path)
sp.add_argument("--title", required=True)
sp.add_argument("--model", default=DEFAULT_MODEL)
sp.add_argument("--use-ocr", action="store_true")
sp.add_argument("--output-root", type=Path, default=Path("output"))
sp.add_argument("--output-format", default=DEFAULT_OUTPUT_FORMAT, choices=["text", "json", "both"])
```

Handler behavior:

* Compute `out_dir = output_root / input_dir.name`
* Read `out_dir / "panels" / "manifest.json"`
* Validate manifest entries into `PanelManifest`
* If `--use-ocr`, run OCR on each `cropped_image_path`
* Save `panel_ocr.json`
* Summarize each panel with `summarize_panel`
* Save `panel_summaries.json`
* Run `track_beats`
* Save `beats.json`
* For now, synthesize chapter either:

  * Option A: directly from beat recap sentences with a new function, or
  * Option B: write beat recap output only and leave chapter synthesis for a later commit.

Prefer Option B for this commit: stop at `beats.json` and print the path.

8. Add manual fallback later, not now

Do not remove or rewrite `cropper.py`.
Keep it as manual crop fallback.

Later, add support for a manual boxes file:

```text
input/chapter_001/panel_boxes.json
```

But do not implement this in the first pass unless the automatic detector fails badly.

9. Add dependency note

If the project has `pyproject.toml`, add OpenCV as an optional or main dependency:

```text
opencv-python
```

Pillow already appears to be used. If not listed, ensure `pillow` is included.

10. Add basic tests or smoke checks

Add simple smoke tests if a test framework exists. Otherwise, ensure these commands run:

```bash
python -m manhwa_recap.app panelize input/chapter_001 --debug
python -m manhwa_recap.app summarize-panels input/chapter_001 --title "Chapter 1" --use-ocr
```

Expected outputs:

```text
output/chapter_001/panels/manifest.json
output/chapter_001/panels/*.png
output/chapter_001/panel_debug/*_boxes.png
output/chapter_001/panel_ocr.json
output/chapter_001/panel_summaries.json
output/chapter_001/beats.json
```

Acceptance criteria:

* Existing `summarize` command still works.
* `panelize` creates cropped panel files and a manifest.
* Manifest entries preserve reading order.
* Debug images show bounding boxes when `--debug` is passed.
* `summarize-panels` can consume the manifest.
* OCR runs against panel crops, not whole chunks.
* Panel summaries validate against `PanelSummary`.
* Beat tracking validates against `BeatSummary`.
* No panel appears in two beats unless explicitly duplicated by model error; if duplicates occur, leave a TODO for validation cleanup.

Important design rule:
Panelizing is not just cropping. It creates the chronological map for storytelling. The cropped images are useful, but `manifest.json` is the key artifact.


