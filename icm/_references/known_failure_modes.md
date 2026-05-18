# Known Failure Modes

## Purpose

This file lists recurring failure modes in the manhwa recap pipeline. Stage agents should use this as a review checklist when the current stage references it.

## Panel Extraction Failures

### Cropped panel includes neighboring panel material

The crop boundary captures part of another panel or background texture that changes interpretation.

Review action: flag the crop as `needs_review` and identify the likely correction.

### Reading order is wrong

Panels are processed in an order that does not match the intended comic flow.

Review action: flag affected panel IDs and propose corrected order.

### Decorative background treated as story content

Background effects, speed lines, patterns, or layout decoration are mistaken for objects or actions.

Review action: mark the detail as uncertain or likely decorative.

## Panel Summary Failures

### Character identity invented from weak evidence

The model assigns a name to a character without support from cast context, dialogue, or strong visual evidence.

Review action: use visual labels and confidence instead of names.

### OCR over-trusted

Noisy OCR text is treated as certain dialogue.

Review action: preserve OCR as a note, but prioritize visible evidence when there is conflict.

### Visible uncertainty removed

The summary turns uncertain actions or identities into confident claims.

Review action: add uncertainty notes.

## Contextual Interpretation Failures

### Setup/payoff missed

The model interprets the current panel alone and misses a joke, callback, reveal, or emotional payoff from previous panels.

Review action: identify the setup panel ID and explain the mechanism.

### Character trait ignored

A known trait changes the panel's meaning but is not used. Examples include blindness, bending ability, rank, relationship, disguise, injury, or recurring role.

Review action: add trait evidence and explain how it changes interpretation.

### Generic story function

The model writes a generic visual description instead of explaining what the panel does in the sequence.

Review action: replace with corrected story function.

## Beat Summary Failures

### Beat is too broad

Too many events are grouped into one beat, making the recap sentence vague.

Review action: split the beat into smaller chronological beats.

### Beat is too small

A single reaction panel is isolated even though it belongs to the same action/reaction sequence.

Review action: merge with the surrounding beat.

### Emotional shift unsupported

The beat claims a mood change that is not supported by panel evidence.

Review action: revise or mark uncertain.

## Transcript Failures

### Character narrator drift

The transcript sounds like Katara or another character narrating in first person.

Review action: rewrite as neutral recap narration.

### Speech bubble paraphrase

The transcript merely rewrites dialogue instead of describing the panel or beat function.

Review action: use beat and contextual interpretation as primary sources.

### Overdramatization

The line adds intensity, motives, or stakes not supported by artifacts.

Review action: simplify and return to evidence.

### Beat alignment failure

A transcript line does not clearly correspond to the beat, panel IDs, or story function it claims to cover.

Review action: require source beat ID and panel IDs.
