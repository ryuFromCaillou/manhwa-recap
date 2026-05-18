# Recap Voice Reference

## Purpose

This file defines the default narration voice for transcript generation and final script assembly.

The recap voice is not a character voice. It is a clear external narrator voice that describes what happens, why it matters, and how one beat leads into the next.

## Core Voice

Use neutral third-person recap narration.

The narrator should sound observant, controlled, and story-aware. The narration should help the viewer understand the panel sequence without pretending to be inside the scene.

The voice may be dramatic when the source material is dramatic, but drama must come from the events, not from invented language.

## Primary Sources

Transcript narration should primarily use:

1. `BeatSummary.beats[].recap_sentence`
2. `BeatSummary.beats[].story_function`
3. `ContextualPanelInterpretation.corrected_story_function`
4. `ContextualPanelInterpretation.setup_payoff_relation`
5. `PanelSummary.visual_description` only for necessary visible detail

Do not treat speech bubbles as ready-made transcript lines.

## Good Recap Voice

Good recap narration describes the function of the moment.

Example:

> Toph sets up the joke by asking what fireworks sound like to her, and the next panel pays it off with an overwhelming blast that shocks everyone around her.

Why it works:

- It explains setup and payoff.
- It respects Toph's blindness as relevant context.
- It does not pretend to be Toph.
- It does not simply repeat the dialogue.

## Bad Recap Voice

Bad recap narration roleplays or paraphrases the panel too directly.

Example:

> I looked at the fireworks and realized they sounded like a huge boom to me.

Why it fails:

- It uses first-person character voice.
- It contradicts Toph's blindness if applied to her.
- It misses the joke mechanism.
- It sounds like a rewritten speech bubble.

## Tone Boundaries

Avoid:

- first-person narration from Katara or any other character
- fake internal thoughts
- unsupported motives
- melodrama that is not present in the beat
- direct speech-bubble paraphrase
- explaining too much when the visual action is simple

Prefer:

- compact chronological narration
- cause-and-effect wording
- clear setup/payoff language
- explicit uncertainty when needed
- visual description only when it helps the viewer follow the panel

## Default Sentence Shape

Useful sentence patterns:

- "After [setup], [character/event] [payoff/action]."
- "The moment shifts when [trigger], forcing [reaction/result]."
- "This panel functions as [setup/payoff/reaction/reveal], showing [visible evidence]."
- "The beat moves from [state_before] to [state_after] as [trigger] happens."

Do not overuse these patterns. They are fallback structures, not required templates.
