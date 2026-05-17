Yes. The transcript target is slightly wrong right now.

What you want is not “Katara narrates the comic as if she is inside the scene.” That creates dramatic retelling and bubble-by-bubble paraphrase.

You want “recap narration anchored to the current panel.” The voice should describe what the viewer is seeing, but interpret it using the beat context. The beat recap sentence is already closer because it compresses story function instead of roleplaying the moment.

So the transcript line should be more like:

```text
Toph turns the fireworks into a joke about sound, setting up the group’s sudden reaction.
```

Not:

```text
I watched as Toph asked us what fireworks sounded like to her, and then we all jumped when the sound exploded.
```

And not:

```text
Toph says, “You wanna know what fireworks sound like for me?”
```

unless you explicitly want dialogue preservation.

The correction is to rename the task mentally:

```text
Transcript generation
→ Panel-aligned recap narration
```

Each line should answer:

```text
What is this panel doing in the beat?
What should the recap narrator say while this panel is on screen?
```

Not:

```text
What would Katara say if she were recounting this scene?
What exact comic dialogue happens here?
```

I would change the transcript prompt like this:

```python
PANEL_ALIGNED_RECAP_TRANSCRIPT_PROMPT = """You are generating panel-aligned recap narration for a motion-comic/manhwa recap video.

You will receive:
1. Reviewed contextual panel interpretations.
2. Beat summaries.

The output is not character dialogue and not first-person roleplay.
Do not speak as Katara or any character.
Do not merely restate speech bubbles.
Do not write dramatic prose as if adapting the scene into a novel.

Instead, write concise recap-style narration anchored to each panel or small panel group.

Each transcript line should describe what the panel is doing within the current beat:
- setup
- payoff
- reaction
- reveal
- transition
- escalation
- atmosphere
- action

Use the beat recap_sentence and story_function as the main guide for tone and compression.
Use panel interpretations to keep the narration visually aligned.

Rules:
- Every line must include panel_ids.
- Every important panel should be represented.
- Prefer third-person recap narration.
- Use dialogue only when it is essential to the joke, reveal, or plot point.
- If dialogue is used, summarize it unless the exact wording matters.
- Keep lines short enough for voiceover.
- Avoid invented motives, emotions, or unsupported details.
- Avoid overly cinematic or dramatic wording.
- Avoid first-person narration.

Return JSON with:
- title
- lines: list of objects with line_id, beat_id, panel_ids, speaker, line_type, text, visual_anchor, beat_function, pacing, uncertainty_notes
- unresolved_or_uncertain

Return ONLY a single JSON object and nothing else.
"""
```

I would also adjust the schema slightly. Replace `emotional_tone` with `beat_function`, because “emotional tone” encourages dramatic writing.

```python
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
```

Valid `line_type` values should become:

```text
recap
dialogue_quote
sfx
transition
pause
```

That forces the normal path to be recap, not character narration.

The key prompt sentence is this:

```text
Each transcript line should describe what the panel is doing within the current beat.
```

That is the actual target.

For Codex, give this implementation correction:

````md
# Transcript Prompt Correction

The transcript generator is currently too dramatic and too close to character retelling. Change the target from “character narration” to “panel-aligned recap narration.”

## Required behavior

The transcript should:

- use third-person recap voice
- stay aligned to panel IDs
- describe the panel’s function inside the current beat
- use `beat.recap_sentence` and `beat.story_function` as the compression guide
- avoid first-person narration
- avoid speaking as Katara or any character
- avoid merely paraphrasing speech bubbles
- quote dialogue only when the exact line is essential

## Replace transcript prompt with panel-aligned recap prompt

Add or replace with:

```python
PANEL_ALIGNED_RECAP_TRANSCRIPT_PROMPT = """You are generating panel-aligned recap narration for a motion-comic/manhwa recap video.

You will receive:
1. Reviewed contextual panel interpretations.
2. Beat summaries.

The output is not character dialogue and not first-person roleplay.
Do not speak as Katara or any character.
Do not merely restate speech bubbles.
Do not write dramatic prose as if adapting the scene into a novel.

Instead, write concise recap-style narration anchored to each panel or small panel group.

Each transcript line should describe what the panel is doing within the current beat:
- setup
- payoff
- reaction
- reveal
- transition
- escalation
- atmosphere
- action

Use the beat recap_sentence and story_function as the main guide for tone and compression.
Use panel interpretations to keep the narration visually aligned.

Rules:
- Every line must include panel_ids.
- Every important panel should be represented.
- Prefer third-person recap narration.
- Use dialogue only when it is essential to the joke, reveal, or plot point.
- If dialogue is used, summarize it unless the exact wording matters.
- Keep lines short enough for voiceover.
- Avoid invented motives, emotions, or unsupported details.
- Avoid overly cinematic or dramatic wording.
- Avoid first-person narration.

Return JSON with:
- title
- lines: list of objects with line_id, beat_id, panel_ids, speaker, line_type, text, visual_anchor, beat_function, pacing, uncertainty_notes
- unresolved_or_uncertain

Return ONLY a single JSON object and nothing else.
"""
````

## Schema adjustment

Change transcript line defaults:

```python
speaker: str = "Recap Narrator"
line_type: str = "recap"
```

Replace:

```python
emotional_tone
```

with:

```python
beat_function
```

## Validation rule

Add a validation warning if generated text contains first-person narration patterns such as:

```text
I saw
I watched
we saw
I realized
from my perspective
```

Also warn if too many lines are `dialogue` or direct quote style.

## Desired output style

Bad:

```text
I watched as Toph asked us what fireworks sounded like to her.
```

Bad:

```text
Toph says she wants to show them what fireworks sound like for her.
```

Better:

```text
Toph sets up a joke by reframing the fireworks around sound instead of sight.
```

Better:

```text
The payoff hits when the loud blast makes the group jump in panic.
```

Better:

```text
The panel holds on the group’s shocked reaction, selling the joke before the scene moves on.
```

```

The important shift: the transcript should be “recap voiceover with panel anchors,” not “in-universe narration.” Your beat summaries are the voice model. Your contextual panel interpretations are the alignment model.
```
