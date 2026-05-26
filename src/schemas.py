from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class OCRResult(BaseModel):
    """OCR output for an image."""

    model_config = ConfigDict(extra="ignore")

    chunk_id: str
    text: str
    confidence: Optional[float] = None


class ChapterSummary(BaseModel):
    """Structured chapter-level summary synthesized from chunk summaries."""

    model_config = ConfigDict(extra="ignore")

    title: str
    overall_summary: str
    major_events: List[str] = Field(default_factory=list)
    characters_mentioned: List[str] = Field(default_factory=list)
    unresolved_or_uncertain: List[str] = Field(default_factory=list)
    """Structured chapter-level summary synthesized from chunk summaries."""

    model_config = ConfigDict(extra="ignore")

    title: str
    overall_summary: str
    major_events: List[str] = Field(default_factory=list)
    characters_mentioned: List[str] = Field(default_factory=list)
    unresolved_or_uncertain: List[str] = Field(default_factory=list)


class PanelManifest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    panel_id: str
    source_image_path: str
    cropped_image_path: str
    page_index: int
    panel_index: int
    reading_order: int
    bbox: List[int]


class PanelOCRResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    panel_id: str
    text: str
    confidence: Optional[float] = None


class PanelSummary(BaseModel):
    model_config = ConfigDict(extra="ignore")

    panel_id: str
    reading_order: int
    visual_description: str
    dialogue_notes: List[str] = Field(default_factory=list)
    action: str
    uncertainty_notes: List[str] = Field(default_factory=list)
    concise_summary: str


class NarrativeBeat(BaseModel):
    model_config = ConfigDict(extra="ignore")

    beat_id: str
    panel_ids: List[str] = Field(default_factory=list)
    state_before: str
    trigger: str
    state_after: str
    emotional_shift: Optional[str] = None
    story_function: str
    recap_sentence: str
    uncertainty_notes: List[str] = Field(default_factory=list)

    @staticmethod
    def _coerce_str_list(value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, list):
            out: List[str] = []
            for item in value:
                if item is None:
                    continue
                if isinstance(item, str):
                    s = item.strip()
                    if s:
                        out.append(s)
                else:
                    s = str(item).strip()
                    if s:
                        out.append(s)
            return out
        if isinstance(value, str):
            s = value.strip()
            return [s] if s else []
        return [str(value).strip()] if str(value).strip() else []

    @field_validator("beat_id", mode="before")
    @classmethod
    def _coerce_beat_id(cls, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, (int, float, bool)):
            return str(int(value)) if isinstance(value, bool) else str(value)
        return str(value).strip()

    @field_validator("panel_ids", mode="before")
    @classmethod
    def _coerce_panel_ids(cls, value: Any) -> List[str]:
        return cls._coerce_str_list(value)

    @field_validator("uncertainty_notes", mode="before")
    @classmethod
    def _coerce_uncertainty_notes(cls, value: Any) -> List[str]:
        return cls._coerce_str_list(value)


class BeatSummary(BaseModel):
    model_config = ConfigDict(extra="ignore")

    beats: List[NarrativeBeat] = Field(default_factory=list)
    leftover_panels: List[str] = Field(default_factory=list)

    @field_validator("leftover_panels", mode="before")
    @classmethod
    def _coerce_leftover_panels(cls, value: Any) -> List[str]:
        return NarrativeBeat._coerce_str_list(value)


class ResolvedCharacter(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: Optional[str] = None
    visual_label: str
    confidence: str = "uncertain"
    evidence: List[str] = Field(default_factory=list)


class SetupPayoffRelation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    setup_panel_ids: List[str] = Field(default_factory=list)
    payoff_panel_ids: List[str] = Field(default_factory=list)
    setup: Optional[str] = None
    payoff: Optional[str] = None
    mechanism: Optional[str] = None
    effect: Optional[str] = None


class ContextualPanelInterpretation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    panel_id: str
    reading_order: int
    resolved_characters: List[ResolvedCharacter] = Field(default_factory=list)
    continuity_links: List[str] = Field(default_factory=list)
    panel_role: str
    setup_payoff_relation: Optional[SetupPayoffRelation] = None
    joke_or_dramatic_mechanism: Optional[str] = None
    corrected_story_function: str
    adaptation_notes: List[str] = Field(default_factory=list)
    uncertainty_notes: List[str] = Field(default_factory=list)
    concise_contextual_summary: str


class TranscriptLine(BaseModel):
    model_config = ConfigDict(extra="ignore")

    line_id: str
    beat_id: Optional[str] = None
    panel_ids: List[str] = Field(default_factory=list)

    speaker: str = "Recap Narrator"
    line_type: str = "recap"
    text: str

    visual_anchor: Optional[str] = None
    beat_function: Optional[str] = None
    pacing: Optional[str] = None

    uncertainty_notes: List[str] = Field(default_factory=list)


class Transcript(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str
    lines: List[TranscriptLine] = Field(default_factory=list)
    unresolved_or_uncertain: List[str] = Field(default_factory=list)


JsonObject = Dict[str, Any]
