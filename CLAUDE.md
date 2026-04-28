# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

"Gunter" is a voice-activated AI assistant specialized in 1980–1991 VW Vanagon mechanics, running on a Raspberry Pi 5. It features a fullscreen LCARS-inspired tkinter GUI, supports two LLM backends (local Ollama or Anthropic Claude API), two wake modes (Picovoice wake word or manual button), and RAG over OCR'd Bentley and Digifant service manuals.

## Running the Project

```bash
# Activate the virtual environment first
source .venv/bin/activate

# Main voice assistant GUI
python Mechanic.py

# Build/rebuild the Chroma vector store from PDFs (takes hours on Pi 5)
python ingest.py

# Scrape Vanagon FAQ from TheSamba.com (rebuilds FAQ_md.md — separate from the PDF RAG)
python samba_scrape.py
```

Ollama must be running with `llama3.2:3b` and `mxbai-embed-large` loaded when using `LLM_MODE=local` (the default).

## Dependencies

```bash
pip install -r requirements.txt
```

Python 3.11 is the target interpreter. No test suite exists — validation is done by running the application.

## Architecture

The pipeline flows: **Wake Word (or button) → Audio Capture → STT → LLM+RAG → TTS → Playback → Log**

### Key Components

| Component | Technology | Details |
|---|---|---|
| GUI | tkinter (LCARS theme) | 800×480 fullscreen kiosk, class `GunterGUI` |
| Wake word | PvPorcupine (Picovoice) | `Hey-Gunter_en_raspberry-pi_v4_0_0.ppn` |
| Manual wake | LISTEN button in GUI | Fully offline; set `WAKE_MODE=manual` |
| Audio input | PvRecorder | Mic device index `MIC_INDEX=0` |
| Speech-to-Text | Faster-Whisper | `base.en` model, `int8` compute, local files only |
| LLM (local) | Ollama (`llama3.2:3b`) | `http://localhost:11434/api/generate`, offline |
| LLM (cloud) | Anthropic Claude API | Configurable via `CLAUDE_MODEL` env var |
| Embeddings | `mxbai-embed-large` via Ollama | Used at startup and by `ingest.py` |
| Vector DB | Chroma (persisted) | Stored at `vanagon_local_db/`, built from PDFs |
| RAG source | `Manuals/bentley_ocr.pdf`, `Manuals/digifant_pro_ocr.pdf` | Ingested by `ingest.py` |
| TTS | Piper (`./piper/piper`) | English voice `en_US-l2arctic-medium.onnx`, speaker 16 |
| Audio output | `ffplay` | Raw PCM pipe from Piper |
| Ready sound | `ffplay` | Plays `ding.wav` on wake detection |
| PDF viewer | `evince` | Opens to relevant page via `display_manual()` |
| Logging | `service_history.txt` | Timestamped Q&A log of all interactions |

### Hardware Assumptions

- **Device**: Raspberry Pi 5
- **Microphone**: PvRecorder device index `0`
- **Speaker**: Output via `ffplay` (Bluetooth or default audio)
- All local models run on CPU with int8 quantization for RAM efficiency.

### LLM Modes

Controlled by `LLM_MODE` in `.env`:

- `local` (default) — Ollama `llama3.2:3b`, fully offline, `num_ctx=2048`, `temperature=0.2`
- `claude` — Anthropic API, requires network; model set by `CLAUDE_MODEL` (default: `claude-haiku-4-5-20251001`)

Both modes use the same RAG retriever and Gunter system prompt. The GUI shows the active mode at top-right.

### Wake Modes

Controlled by `WAKE_MODE` in `.env`:

- `picovoice` (default) — say "Hey Gunter"; requires Picovoice API key and network on startup
- `manual` — press the `● LISTEN` button in the GUI sidebar; fully offline

### Conversation History

Both LLM backends receive the last 4 conversation turns as context in the prompt. Call `new_session()` (sidebar button) to clear memory between diagnostic sessions.

### PDF Manual Display

`display_manual(topic)` parses the user's question for keywords and opens `evince` to the relevant page:
- ECU/idle/throttle/AFM/Digifant keywords → `digifant_pro_ocr.pdf` (page varies)
- Wiring/electrical keywords → `bentley_ocr.pdf` (page 474 or 549)
- Brake/oil/coolant/fuse keywords → `bentley_ocr.pdf` (page varies)

### TTS Pronunciation Corrections

Piper's English voice mispronounces some terms; `speak()` remaps before synthesis:
- `"Vanagon"` → `"Vana-gon"`
- `"Aircooled"` → `"Air-koold"`
- `"Bus"` → `"Buss"`
- `"Engine"` → `"En-jin"`
- `"ECU"` → `"E--C--U"`

Markdown is stripped from LLM output before TTS via `_strip_markdown()`.

### Chroma Vector Store

Built by `ingest.py` from the two OCR'd PDFs in `Manuals/`. Persisted at `vanagon_local_db/`. Chunks: 500 chars, 50 overlap, batched in groups of 50. Loaded at startup in `Mechanic.py` via `langchain_chroma` + `langchain_ollama`.

## Key Files

| File | Purpose |
|---|---|
| `Mechanic.py` | Main application — GUI, audio pipeline, LLM routing |
| `ingest.py` | One-time script to embed PDFs into Chroma |
| `samba_scrape.py` | Scrapes TheSamba.com FAQ → `FAQ_md.md` (not used by ingest) |
| `en_US-l2arctic-medium.onnx` | Piper TTS voice model |
| `Hey-Gunter_en_raspberry-pi_v4_0_0.ppn` | Picovoice wake word model |
| `vanagon_local_db/` | Persisted Chroma vector store |
| `Manuals/bentley_ocr.pdf` | OCR'd 1980–1991 Vanagon Bentley manual |
| `Manuals/digifant_pro_ocr.pdf` | OCR'd Digifant training manual |
| `service_history.txt` | Timestamped log of all Q&A sessions |
| `vw_logo.png` | Sidebar logo |
| `ding.wav` | Ready sound played on wake detection |
| `piper/piper` | Piper TTS binary |

## Configuration

Copy `sample.env` to `.env`:

```
LLM_MODE=local           # "local" (Ollama) or "claude" (Anthropic API)
WAKE_MODE=picovoice      # "picovoice" (wake word) or "manual" (button)
PICOVOICE_API_KEY=...    # Required for WAKE_MODE=picovoice
ANTHROPIC_API_KEY=...    # Required for LLM_MODE=claude
CLAUDE_MODEL=claude-haiku-4-5-20251001   # or claude-sonnet-4-6
```
