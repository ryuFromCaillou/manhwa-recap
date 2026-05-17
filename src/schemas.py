from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class OCRResult(BaseModel):
    """OCR output for an image."""

    model_config = ConfigDict(extra="ignore")

    chunk_id: str
    text: str
    confidence: float | None = None


class ChapterSummary(BaseModel):
    """Structured chapter-level summary synthesized from chunk summaries."""

    model_config = ConfigDict(extra="ignore")

    title: str
    overall_summary: str
    major_events: list[str] = Field(default_factory=list)
    characters_mentioned: list[str] = Field(default_factory=list)
    unresolved_or_uncertain: list[str] = Field(default_factory=list)
    """Structured chapter-level summary synthesized from chunk summaries."""

    model_config = ConfigDict(extra="ignore")

    title: str
    overall_summary: str
    major_events: list[str] = Field(default_factory=list)
    characters_mentioned: list[str] = Field(default_factory=list)
    unresolved_or_uncertain: list[str] = Field(default_factory=list)


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


class ResolvedCharacter(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str | None = None
    visual_label: str
    confidence: str = "uncertain"
    evidence: list[str] = Field(default_factory=list)


class SetupPayoffRelation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    setup_panel_ids: list[str] = Field(default_factory=list)
    payoff_panel_ids: list[str] = Field(default_factory=list)
    setup: str | None = None
    payoff: str | None = None
    mechanism: str | None = None
    effect: str | None = None


class ContextualPanelInterpretation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    panel_id: str
    reading_order: int
    resolved_characters: list[ResolvedCharacter] = Field(default_factory=list)
    continuity_links: list[str] = Field(default_factory=list)
    panel_role: str
    setup_payoff_relation: SetupPayoffRelation | None = None
    joke_or_dramatic_mechanism: str | None = None
    corrected_story_function: str
    adaptation_notes: list[str] = Field(default_factory=list)
    uncertainty_notes: list[str] = Field(default_factory=list)
    concise_contextual_summary: str


class TranscriptLine(BaseModel):
    model_config = ConfigDict(extra="ignore")

    line_id: str
    beat_id: str | None = None
    panel_ids: list[str] = Field(default_factory=list)

    speaker: str = "Recap Narrator"
    line_type: str = "recap"
    text: str

    visual_anchor: str | None = None
    beat_function: str | None = None
    pacing: str | None = None

    uncertainty_notes: list[str] = Field(default_factory=list)


class Transcript(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str
    lines: list[TranscriptLine] = Field(default_factory=list)
    unresolved_or_uncertain: list[str] = Field(default_factory=list)


JsonObject = dict[str, Any]
