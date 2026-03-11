# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

"Gunter" is a voice-activated AI assistant specialized in 1980–1991 VW Vanagon mechanics, running on a Raspberry Pi 5. It uses a fully local LLM pipeline (Ollama) with RAG over scraped Vanagon documentation, and speaks with a German TTS voice.

## Running the Project

```bash
# Activate the virtual environment first
source .venv/bin/activate

# Main voice assistant (requires Ollama running locally)
python Mechanic.py

# Simplified voice assistant (alternative implementation)
python GoldenScript.py

# Text-based conversational interface
python vanagon_chat.py

# Scrape/refresh Vanagon FAQ from TheSamba.com (rebuilds FAQ_md.md)
python samba_scrape.py
```

Ollama must be running with the `llama3.2:3b` model and `mxbai-embed-large` embeddings loaded before starting Mechanic.py or vanagon_chat.py.

## Dependencies

```bash
pip install -r requirements.txt
```

Python 3.11 is the target interpreter. No test suite exists — validation is done by running the application.

## Architecture

The pipeline flows: **Wake Word → Audio Capture → STT → LLM+RAG → TTS → Playback → Log**

### Key Components

| Component | Technology | Details |
|---|---|---|
| Wake word | PvPorcupine (Picovoice) | Custom `.ppn` model for "Hey Gunter" |
| Audio input | PvRecorder + `arecord` | Mic at hw:2,0 (Lenovo Camera, device index 2) |
| Speech-to-Text | Faster-Whisper | `base.en` model, `int8` compute, local files only |
| LLM | Ollama (`llama3.2:3b`) | Local inference, `num_ctx=2048–4096` |
| Embeddings | `mxbai-embed-large` via Ollama | Used to query the Chroma vector store |
| Vector DB | Chroma (persisted) | Stored at `vanagon_local_db/`, indexes `FAQ_md.md` |
| RAG chain | LangChain | `create_retrieval_chain` + `create_stuff_documents_chain` |
| TTS | Piper (`./piper/piper`) | German voice model `de_DE-thorsten-medium.onnx` |
| Audio output | `ffplay` | Piped from Piper, played via Bluetooth speaker |
| Logging | `service_history.txt` | Timestamped Q&A log of all interactions |

### Hardware Assumptions

- **Device**: Raspberry Pi 5
- **Microphone**: Lenovo Camera (ALSA device `hw:2,0`, PvRecorder index 2)
- **Speaker**: Bluetooth speaker (output via `ffplay`)
- All models run on CPU with int8 quantization for RAM efficiency.

### German TTS Pronunciation

Piper uses a German voice, so English VW terms are phonetically mapped before synthesis (e.g., `"Vanagon"` → `"Wannagohn"`, `"idle"` → `"eidel"`). This mapping lives in `Mechanic.py`.

### Chroma Vector Store

The RAG knowledge base is built from `FAQ_md.md` (scraped Vanagon FAQ). Run `samba_scrape.py` to refresh it. The Chroma DB is persisted at `vanagon_local_db/` and loaded at startup.

## Configuration

Copy `sample.env` to `.env` and fill in keys:
- `OPENAI_API_KEY` — not actively used but imported by LangChain
- `ANTHROPIC_API_KEY` — not actively used in main scripts
- `PICOVOICE_API_KEY` — used by Mechanic.py and GoldenScript.py for wake-word detection

The `.env` file exists but the main scripts rely on `python-dotenv` to load it.
