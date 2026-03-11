# GunterAI

A voice-activated AI assistant for 1980–1991 VW Vanagon mechanics, running locally on a Raspberry Pi 5. Say "Hey Gunter" and ask anything about your Vanagon — Gunter answers in a German accent.

## How it works

1. **Wake word** — PvPorcupine listens for "Hey Gunter"
2. **Speech-to-text** — Faster-Whisper transcribes your question
3. **RAG + LLM** — LangChain retrieves relevant context from a Vanagon FAQ vector database, then passes it to a local Llama 3.2 model via Ollama
4. **Text-to-speech** — Piper synthesizes a response using a German voice model
5. **Playback** — Audio is streamed to a Bluetooth speaker via ffplay
6. **Logging** — All Q&A is saved to `service_history.txt`

## Requirements

- Raspberry Pi 5
- [Ollama](https://ollama.com) with `llama3.2:3b` and `mxbai-embed-large` pulled
- Piper TTS binary (place in `piper/`)
- German voice model: `de_DE-thorsten-medium.onnx` (place in project root)
- Picovoice wake word model: `Hey-Gunter_en_raspberry-pi_v4_0_0.ppn`
- Lenovo Camera or compatible USB mic (ALSA device `hw:2,0`)
- Bluetooth speaker

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp sample.env .env
# Fill in your API keys in .env
```

## Running

```bash
# Full voice assistant with RAG (main)
python Mechanic.py

# Simplified voice assistant
python GoldenScript.py

# Text-based chat interface
python vanagon_chat.py

# Refresh the Vanagon FAQ knowledge base
python samba_scrape.py
```

## Configuration

Copy `sample.env` to `.env` and set:

| Variable | Description |
|---|---|
| `PICOVOICE_API_KEY` | Picovoice console access key |
| `OPENAI_API_KEY` | OpenAI key (used by LangChain) |
| `ANTHROPIC_API_KEY` | Anthropic key (optional) |
