PANEL_PROMPT = """You are summarizing one manhwa/comic panel.

Assume Katara is the narrator describing the panel from her perspective.
Read the panel image and produce a structured JSON summary. Use visible dialogue if legible.
Do not invent character names unless explicitly shown.
If something is uncertain, say it is uncertain.

Return EXACTLY one valid JSON object and NOTHING ELSE.
Do not wrap the response in markdown or code fences.
Do not append any explanation, error note, or extra text.

Return JSON with:
- panel_id
- reading_order (integer)
- visual_description (string)
- dialogue_notes (JSON array of strings)
- action (string)
- uncertainty_notes (JSON array of strings)
- concise_summary (string)
Return ONLY a single JSON object and nothing else.
"""


CONTEXTUAL_PANEL_INTERPRETATION_PROMPT = """You are interpreting a comic/manhwa panel sequence for adaptation into a narrated motion-comic episode.

You will receive:
1. Optional known cast context.
2. A compact local window of previous panel summaries.
3. The current panel summary.
4. OCR/dialogue notes if available.

Do not treat the current panel in isolation.
Use the local previous-panel window to identify immediate setup/payoff, joke structure, callbacks, reveals, reactions, emotional turns, or continuity.
Do not assume you have the full chapter history.
Resolve likely character identities only when supported by visual cues, dialogue continuity, or cast context.
Do not invent character names, motives, or unseen events.

Important:
- If a joke is set up in a previous local panel and paid off in the current panel, explain that mechanism.
- If a character trait changes the meaning of the panel, explicitly state it.
- If identity is uncertain, mark confidence as low or uncertain.
- Prefer corrected story function over generic visual description.

Return JSON with:
- panel_id
- reading_order
- resolved_characters: list of objects with name, visual_label, confidence, evidence
- continuity_links: list of links to previous panels or prior dialogue
- panel_role: setup, payoff, reaction, reveal, transition, escalation, atmosphere, action, or other
- setup_payoff_relation: object or null, with setup_panel_ids, payoff_panel_ids, setup, payoff, mechanism, effect
- joke_or_dramatic_mechanism: string or null
- corrected_story_function
- adaptation_notes: list of video/narration-relevant notes
- uncertainty_notes
- concise_contextual_summary
"""


BEAT_SUMMARY_PROMPT = """You are grouping panel summaries into narrative beats.

Use the ordered panel summaries to identify coherent beats of action, reaction, and story progression.
Group consecutive panels that belong in the same beat, but keep beats compact and meaningful.
Return JSON with:
- beats: a list of objects with beat_id, panel_ids, state_before, trigger, state_after, emotional_shift, story_function, recap_sentence, uncertainty_notes
- leftover_panels: panel_ids that do not clearly fit into any narrative beat
"""


BEAT_CHAPTER_SYNTHESIS_PROMPT = """You are synthesizing a chapter summary from narrative beats.

Preserve chronology and avoid inventing unsupported details.
Use the beats to produce an overall chapter-level recap.
Return JSON with:
- overall_summary
- major_events
- characters_mentioned
- unresolved_or_uncertain
"""



