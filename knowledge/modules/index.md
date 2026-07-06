# Modules

Python package: `infinity_audiobook/`

* [Entry point](entry-point.md) - `main.py` wiring and shutdown
* [Text producer](text-producer.md) - LLM segment generation
* [Audio producer](audio-producer.md) - TTS synthesis thread
* [Player](player.md) - Feeder thread and OutputStream callback
* [Story state](story-state-module.md) - `story.md` parse/read/write
* [TTS](tts.md) - OmniVoice voice cloning
* [LLM clients](llm-clients.md) - Gemini tiered client

Supporting modules: `context.py`, `models.py`, `settings_paths.py`, `settings.py`, `story_config.py`, `story_compact.py`, `story_arc.py`, `reference_sources.py`, `llm_prompts.py`, `llm_debug.py`, `gemini_errors.py`, `playback_config.py`, `env.py`, `ui/` (`snapshot.py` transcript ring + cold-start seed, `app.py` Textual TUI).
