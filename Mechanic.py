# Mechanic.py — Gunter AI Vanagon Diagnostic Command
# GUI: pure tkinter, LCARS-inspired theme matching luna_dash.py
# v2.0 — Multi-provider API support (Anthropic, OpenAI, Groq, OpenRouter)
#         Live model fetching from provider APIs
#         19-voice Piper TTS selection with live preview
#         891MB vectorstore (Bentley + Digifant + 1,046 TheSamba threads)
#         Dynamic provider display throughout UI
#         Clean project structure for GitHub release

import gc
import json
import os
import re
import shlex
import struct
import subprocess
import time
import datetime
import wave
import tkinter as tk
from tkinter import simpledialog # noqa
import threading
import pvporcupine
import pyaudio
import requests
import anthropic
from dotenv import load_dotenv
from PIL import Image, ImageTk

load_dotenv()
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from faster_whisper import WhisperModel
from pvrecorder import PvRecorder

# ── Palette (shared with luna_dash.py) ───────────────────────────────────────
BG         = "#000000"
FRAME_BLUE = "#2f5fc0"
FRAME_DIM  = "#1a3570"
GOLD       = "#cfa01f"
GOLD_DIM   = "#8f6f10"
RED_ALERT  = "#700010"
RED_BRIGHT = "#cc0020"
AMBER      = "#ff8c00"
GREEN_LIT  = "#40bf20"
CYAN       = "#00cfcf"
TEXT_SUB   = "#7fa0df"
TEXT_MAIN  = "#c8d8f8"

# ── Mode Configuration ────────────────────────────────────────────────────────
# Set these in your .env file:
#
# LLM_MODE=local          → Ollama (default, fully offline)
# LLM_MODE=cloud          → Use active provider from Settings → API Providers
#
# WAKE_MODE=picovoice     → "Hey Gunter" wake word (set key in Settings)
# WAKE_MODE=manual        → Press LISTEN button, speak into mic
# WAKE_MODE=text          → Type questions via keyboard (no microphone needed)
#
# LOCAL_MODEL=llama3.2:3b  (default local Ollama model)
#
# API keys (Anthropic, OpenAI, Groq, OpenRouter, Picovoice) are managed
# in the Settings panel and stored in providers.json — not in .env

LLM_MODE  = os.getenv("LLM_MODE",  "local")
WAKE_MODE = os.getenv("WAKE_MODE", "picovoice")
LOCAL_MODEL = os.getenv("LOCAL_MODEL", "llama3.2:3b")
MIC_INDEX   = 0
MODEL_SIZE  = "base.en"

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_PATH           = "/home/shogun/PyCharmMiscProject/PythonAIAgent"
BENTLEY_PATH        = f"{BASE_PATH}/Manuals/bentley_ocr.pdf"
DIGIFANT_PATH       = f"{BASE_PATH}/Manuals/digifant_pro_ocr.pdf"
CONFIG_FILE         = f"{BASE_PATH}/vanagon_config.json"
SERVICE_RECORD_FILE = f"{BASE_PATH}/service_records.json"
PROVIDERS_FILE      = f"{BASE_PATH}/providers.json"
VOICES_PATH         = f"{BASE_PATH}/voices"
WAKE_WORD_PATH      = f"{BASE_PATH}/wake_word"
WIKI_PATH           = f"{BASE_PATH}/vanagon_wiki"

# ── Voice options — (onnx_filename, speaker_id or None) ──────────────────────
VOICE_OPTIONS = {
    "Amy (Medium)":        ("en_US-amy-medium.onnx",    None),
    "Joe (Medium)":        ("en_US-joe-medium.onnx",    None),
    "Ryan (High)":         ("en_US-ryan-high.onnx",     None),
    "L2Arctic — Speaker 0":  ("en_US-l2arctic-medium.onnx",  0),
    "L2Arctic — Speaker 1":  ("en_US-l2arctic-medium.onnx",  1),
    "L2Arctic — Speaker 2":  ("en_US-l2arctic-medium.onnx",  2),
    "L2Arctic — Speaker 3":  ("en_US-l2arctic-medium.onnx",  3),
    "L2Arctic — Speaker 4":  ("en_US-l2arctic-medium.onnx",  4),
    "L2Arctic — Speaker 5":  ("en_US-l2arctic-medium.onnx",  5),
    "L2Arctic — Speaker 6":  ("en_US-l2arctic-medium.onnx",  6),
    "L2Arctic — Speaker 7":  ("en_US-l2arctic-medium.onnx",  7),
    "L2Arctic — Speaker 8":  ("en_US-l2arctic-medium.onnx",  8),
    "L2Arctic — Speaker 9":  ("en_US-l2arctic-medium.onnx",  9),
    "L2Arctic — Speaker 10": ("en_US-l2arctic-medium.onnx", 10),
    "L2Arctic — Speaker 11": ("en_US-l2arctic-medium.onnx", 11),
    "L2Arctic — Speaker 12": ("en_US-l2arctic-medium.onnx", 12),
    "L2Arctic — Speaker 13": ("en_US-l2arctic-medium.onnx", 13),
    "L2Arctic — Speaker 14": ("en_US-l2arctic-medium.onnx", 14),
    "L2Arctic — Speaker 15": ("en_US-l2arctic-medium.onnx", 15),
}
VOICE_NAMES = list(VOICE_OPTIONS.keys())  # ordered list for display

# Provider fallback model lists — used when API fetch fails / no key yet
PROVIDER_FALLBACK_MODELS = {
    "anthropic":  ["claude-haiku-4-5-20251001", "claude-sonnet-4-6",
                   "claude-opus-4-6"],
    "openai":     ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
    "groq":       ["llama3-8b-8192", "llama3-70b-8192", "mixtral-8x7b-32768",
                   "gemma2-9b-it"],
    "openrouter": ["mistralai/mistral-7b-instruct", "meta-llama/llama-3-8b-instruct",
                   "google/gemma-2-9b-it", "anthropic/claude-haiku"],
}

# ── Vanagon config defaults ───────────────────────────────────────────────────
CONFIG_DEFAULTS = {
    "year":          "1987",
    "engine":        "Wasserboxer",
    "trans":         "Manual",
    "model":         "2WD",
    "voice_name":    "L2Arctic — Speaker 0",   # display name key into VOICE_OPTIONS
}
YEAR_OPTIONS   = [str(y) for y in range(1980, 1992)]
ENGINE_OPTIONS = ["Air-Cooled", "Wasserboxer", "Diesel"]
TRANS_OPTIONS  = ["Manual", "Automatic"]
MODEL_OPTIONS  = ["2WD", "Syncro"]

# ── Service record items + recommended intervals ──────────────────────────────
# interval_miles: how often this service is typically due (0 = no mileage check)
SERVICE_ITEMS = [
    {"key": "oil_change",      "label": "Oil Change",       "interval_miles": 3000},
    {"key": "oil_filter",      "label": "Oil Filter",       "interval_miles": 3000},
    {"key": "coolant_flush",   "label": "Coolant Flush",    "interval_miles": 30000},
    {"key": "trans_service",   "label": "Trans Service",    "interval_miles": 30000},
    {"key": "brake_pads",      "label": "Brake Pads",       "interval_miles": 20000},
    {"key": "spark_plugs",     "label": "Spark Plugs",      "interval_miles": 15000},
    {"key": "brake_fluid",     "label": "Brake Fluid",      "interval_miles": 24000},
    {"key": "tires",           "label": "Tires",            "interval_miles": 50000},
]

# ── Brain — initialized once at startup ──────────────────────────────────────
embeddings  = OllamaEmbeddings(model="mxbai-embed-large")
time.sleep(1)  # allow Ollama client to settle before ChromaDB Rust init
vectorstore = Chroma(
    persist_directory=f"{BASE_PATH}/vanagon_local_db",
    embedding_function=embeddings
)
# k=4 for any cloud API provider, k=2 for local Ollama (RAM limited)
# Inline check here — get_active_provider() not yet defined at module level
def _check_provider_has_key():
    try:
        with open(PROVIDERS_FILE, "r") as _f:
            _pd = json.load(_f)
        _active = _pd.get("active", "anthropic")
        for _p in _pd.get("providers", []):
            if _p["name"] == _active:
                return bool(_p.get("api_key", "").strip())
    except Exception:
        pass
    return False

k = 2 if (LLM_MODE != "claude" and not _check_provider_has_key()) else 4
retriever = vectorstore.as_retriever(search_kwargs={"k": k})


# ── Vanagon config persistence ────────────────────────────────────────────────
def load_van_config():
    """Load saved Vanagon config from JSON, fall back to defaults."""
    try:
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
            return {k: data.get(k, v) for k, v in CONFIG_DEFAULTS.items()}
    except (FileNotFoundError, json.JSONDecodeError):
        return CONFIG_DEFAULTS.copy()


def save_van_config(config):
    """Persist Vanagon config to JSON."""
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
    except OSError as e:
        print(f"Config save error: {e}")


# ── Providers persistence ─────────────────────────────────────────────────────
PROVIDERS_DEFAULTS = {
    "active": "ollama",
    "picovoice_key": "",
    "providers": [
        {"name": "anthropic",  "label": "Anthropic Claude", "api_key": "",
         "model": "claude-haiku-4-5-20251001"},
        {"name": "openai",     "label": "OpenAI",           "api_key": "",
         "model": "gpt-4o-mini"},
        {"name": "groq",       "label": "Groq",             "api_key": "",
         "model": "llama3-8b-8192"},
        {"name": "openrouter", "label": "OpenRouter",       "api_key": "",
         "model": "mistralai/mistral-7b-instruct"},
        {"name": "ollama",     "label": "Ollama (Local)",   "api_key": "",
         "model": "nemotron-3-nano:4b"},
    ]
}


def load_providers():
    """Load providers config from JSON, fall back to defaults."""
    try:
        with open(PROVIDERS_FILE, "r") as f:
            data = json.load(f)
            existing_names = {p["name"] for p in data.get("providers", [])}
            for default_p in PROVIDERS_DEFAULTS["providers"]:
                if default_p["name"] not in existing_names:
                    data["providers"].append(default_p.copy())
            if "active" not in data:
                data["active"] = PROVIDERS_DEFAULTS["active"]
            if "picovoice_key" not in data:
                data["picovoice_key"] = ""
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        import copy
        return copy.deepcopy(PROVIDERS_DEFAULTS)


def save_providers(data):
    """Persist providers config to JSON."""
    try:
        with open(PROVIDERS_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except OSError as e:
        print(f"Providers save error: {e}")


def get_active_provider():
    """Return the active provider dict, or the anthropic default."""
    data = load_providers()
    active_name = data.get("active", "anthropic")
    for p in data.get("providers", []):
        if p["name"] == active_name:
            return p
    # Fallback: return first provider
    return data["providers"][0] if data["providers"] else PROVIDERS_DEFAULTS["providers"][0]


def fetch_provider_models(provider_name, api_key):
    """
    Fetch live model list from provider API.
    Returns list of model ID strings, or fallback list on failure.
    """
    fallback = PROVIDER_FALLBACK_MODELS.get(provider_name, [])
    if provider_name == "ollama":
        # Ollama — query local API, no key needed
        try:
            resp = requests.get("http://localhost:11434/api/tags", timeout=5)
            resp.raise_for_status()
            models = [m["name"] for m in resp.json().get("models", [])]
            return models if models else ["nemotron-3-nano:4b"]
        except Exception as e:
            print(f"Ollama fetch error: {e}")
            return ["llama3.2:3b", "llama3.1:8b", "mistral:7b", "nemotron-3-nano:4b"]
    if not api_key or not api_key.strip():
        return fallback
    try:
        if provider_name == "anthropic":
            resp = requests.get(
                "https://api.anthropic.com/v1/models",
                headers={"x-api-key": api_key,
                         "anthropic-version": "2023-06-01"},
                timeout=8
            )
            resp.raise_for_status()
            models = [m["id"] for m in resp.json().get("data", [])]
            return models if models else fallback

        elif provider_name in ("openai", "groq", "openrouter"):
            urls = {
                "openai":     "https://api.openai.com/v1/models",
                "groq":       "https://api.groq.com/openai/v1/models",
                "openrouter": "https://openrouter.ai/api/v1/models",
            }
            resp = requests.get(
                urls[provider_name],
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=8
            )
            resp.raise_for_status()
            raw = resp.json().get("data", [])

            if provider_name == "openrouter":
                # Filter to chat-capable models only, sort by id
                models = sorted([
                    m["id"] for m in raw
                    if "chat" in m.get("id", "").lower()
                    or "instruct" in m.get("id", "").lower()
                    or m.get("context_length", 0) >= 4096
                ])
            else:
                # OpenAI / Groq — keep chat/gpt/llama models, skip embeddings etc.
                skip_keywords = ["embed", "tts", "whisper", "dall-e",
                                 "babbage", "davinci", "audio"]
                models = sorted([
                    m["id"] for m in raw
                    if not any(kw in m["id"].lower() for kw in skip_keywords)
                ])
            return models if models else fallback

    except Exception as e:
        print(f"Model fetch error ({provider_name}): {e}")
        return fallback


# ── Service records persistence ───────────────────────────────────────────────
def load_service_records():
    """Load service records from JSON. Returns dict keyed by service item key."""
    defaults = {item["key"]: {"date": "", "miles": ""} for item in SERVICE_ITEMS}
    # Add current status fields
    defaults["current_date"]  = "" # noqa
    defaults["current_miles"] = "" # noqa
    try:
        with open(SERVICE_RECORD_FILE, "r") as f:
            data = json.load(f)
            # Merge saved data with defaults so new items always appear
            for key in defaults:
                if key in data:
                    defaults[key] = data[key]
            return defaults
    except (FileNotFoundError, json.JSONDecodeError):
        return defaults


def save_service_records(records):
    """Persist service records to JSON."""
    try:
        with open(SERVICE_RECORD_FILE, "w") as f:
            json.dump(records, f, indent=2)
    except OSError as e:
        print(f"Service record save error: {e}")


def _build_service_summary():
    """
    Build a compact service history string for injection into prompts.
    Includes current mileage/date and all logged service items.
    Returns empty string if no records exist yet.
    """
    records      = load_service_records()
    today        = datetime.datetime.now().strftime("%m/%d/%Y")
    cur_date     = records.get("current_date",  "") or today
    cur_miles    = records.get("current_miles", "")

    # Always tell Gunter today's actual date
    status_lines = [f"TODAY'S DATE: {today}"]
    if cur_miles:
        status_lines.append(f"CURRENT ODOMETER: {cur_miles} miles")
    if cur_date and cur_date != today:
        status_lines.append(f"LAST STATUS UPDATE: {cur_date}")

    svc_lines = []
    for item in SERVICE_ITEMS:
        rec   = records.get(item["key"], {})
        date  = rec.get("date", "")
        miles = rec.get("miles", "")
        if date or miles:
            svc_lines.append(
                f"  {item['label']}: {date or 'no date'} at {miles or 'unknown'} miles")

    result = "\n".join(status_lines)
    if svc_lines:
        result += "\nSERVICE HISTORY:\n" + "\n".join(svc_lines)
    return result


# ── Logging ───────────────────────────────────────────────────────────────────
def log_service(question, answer):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"\n{'=' * 50}\nDATE: {timestamp}\nISSUE: {question}\nGUNTER: {answer}\n"
    with open("service_history.txt", "a") as f:
        f.write(entry)


# ── Audio helpers ─────────────────────────────────────────────────────────────
def play_ready_sound():
    subprocess.Popen(["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet",
                      f"{BASE_PATH}/ding.wav"])


def speak(text):
    # ── Strip markdown before TTS — removes **, *, ##, #, __ etc. ────────────
    import re as _re
    text = _re.sub(r'\*\*(.+?)\*\*', r'\1', text)   # **bold** → bold
    text = _re.sub(r'\*(.+?)\*',     r'\1', text)   # *italic* → italic
    text = _re.sub(r'__(.+?)__',     r'\1', text)   # __bold__ → bold
    text = _re.sub(r'_(.+?)_',       r'\1', text)   # _italic_ → italic
    text = _re.sub(r'^#{1,6}\s+',    '',    text, flags=_re.MULTILINE)  # headers
    text = _re.sub(r'`(.+?)`',       r'\1', text)   # `code` → code
    text = _re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)  # [link](url) → link
    text = _re.sub(r'^\s*[-*+]\s+',  '',    text, flags=_re.MULTILINE)  # bullets
    text = _re.sub(r'^\s*\d+\.\s+',  '',    text, flags=_re.MULTILINE)  # numbered lists
    text = text.replace('---', '').replace('===', '')  # horizontal rules

    corrections = {
        "Vanagon":   "Vana-gon",
        "Aircooled": "Air-koold",
        "Bus":       "Buss",
        "Engine":    "En-jin",
        "Ollama":    "O-llama",
        "ECU":       "E--C--U"
    }
    for word, replacement in corrections.items():
        text = text.replace(word, replacement)

    # Read active voice from config each call — changes take effect immediately
    cfg        = load_van_config()
    voice_name = cfg.get("voice_name", "L2Arctic — Speaker 0")
    onnx_file, speaker_id = VOICE_OPTIONS.get(
        voice_name, ("en_US-l2arctic-medium.onnx", 0))

    piper_cmd    = f"{BASE_PATH}/piper/piper"
    model_path   = f"{VOICES_PATH}/{onnx_file}"
    safe_text    = shlex.quote(text)
    speaker_flag = f"--speaker {speaker_id} " if speaker_id is not None else ""
    command = (f'echo {safe_text} | {piper_cmd} --model {model_path} '
               f'{speaker_flag}--output_file /tmp/gunter_tts.wav && '
               f'paplay /tmp/gunter_tts.wav')
    print(f"Gunter: {text}")
    subprocess.run(command, shell=True)


# ── Manual display — dynamic page launcher ────────────────────────────────────
def _open_manual_to_page(page_num, source="bentley"):
    """Open Evince directly to a specific page number."""
    manual_path = DIGIFANT_PATH if "digifant" in source.lower() else BENTLEY_PATH
    try:
        subprocess.run(["pkill", "evince"])
        subprocess.Popen(["evince", f"--page-label={page_num}", manual_path])
        print(f"[!] Gunter opening {manual_path} to page {page_num}")
    except Exception as e:
        print(f"Error opening PDF: {e}")


def _extract_page_citation(answer):
    """
    Parse page number and manual source from Gunter's response.
    Matches: 'Bentley page 1135', 'page 247', 'p.16', 'Digifant page 22'
    Returns (page_int, source_str) or (None, None).
    """
    pattern = re.compile(
        r'(bentley|digifant)?\s*p(?:age|\.)\s*(\d+)',
        re.IGNORECASE
    )
    match = pattern.search(answer)
    if match:
        source = match.group(1) or "bentley"
        page   = int(match.group(2))
        max_page = 59 if "digifant" in source.lower() else 1329
        if 1 <= page <= max_page:
            return page, source
    return None, None


def display_manual(topic, answer=""):
    """
    Opens the Bentley or Digifant manual to the page Gunter cited in his answer.
    Only opens if Gunter explicitly cited a page number — no hardcoded fallbacks.
    If Gunter didn't cite a page the manual stays closed rather than opening
    to a potentially wrong page.
    """
    page, source = _extract_page_citation(answer)
    if page:
        _open_manual_to_page(page, source)


# ── Gunter's persona ──────────────────────────────────────────────────────────
GUNTER_SYSTEM = """You are Gunter, a master VW mechanic specialized exclusively in
1980-1991 Vanagons. You have full digital access to the Bentley Manual, the Digifant
Training Manual, and a curated Vanagon Wiki containing verified part numbers, tire
pressures, maintenance procedures, and critical warnings.

NEVER apologize for not having a physical copy of any manual.

KNOWLEDGE SOURCES — use in this priority order:
1. VANAGON WIKI sections (labeled "VANAGON WIKI — VERIFIED REFERENCE") — these contain
   confirmed part numbers, specifications, and critical safety warnings. Treat this
   information as authoritative and cite it directly.
2. CONTEXT from Bentley/Digifant/forum — use for procedures, page citations, and
   community diagnostic experience.
3. Your own expertise — fill gaps, but never invent part numbers or page numbers.

CITATION RULES:
- When CONTEXT includes page references like [Bentley p.247], cite them naturally:
  "According to Bentley page 247..." or "The Bentley covers this on page 247."
- Only cite pages explicitly provided in the CONTEXT — never invent page numbers.
- For part numbers from the Wiki, state them directly without hedging.

BEHAVIOR:
- Never assume engine type, transmission, or drivetrain — always use the VEHICLE
  configuration provided at the top of each message.
- Never assume the owner's location or driving region — do not reference specific
  cities, states, or climates unless the owner explicitly mentions them.
- If SERVICE HISTORY is provided, proactively mention overdue maintenance when
  relevant. Example: if oil change was done 5,000 miles ago and the user asks
  about engine noise, note the oil change may be due.
- If a term seems wrong (like 'oral light'), assume they mean 'oil light' but
  ask for clarification.
- Keep tone professional, direct, and helpful — like a trusted shop mechanic.
- Respond in plain spoken sentences only. No markdown, no bullet points, no asterisks."""


def _build_context(docs):
    """Build context string from RAG results including page number metadata."""
    context_parts = []
    for doc in docs:
        page   = doc.metadata.get('page', None)
        source = doc.metadata.get('source', '')
        if 'bentley' in source.lower():
            manual = 'Bentley'
        elif 'digifant' in source.lower():
            manual = 'Digifant'
        else:
            manual = 'Manual'
        header = f"[{manual} p.{page}]" if page is not None else f"[{manual}]"
        context_parts.append(f"{header}\n{doc.page_content}")
    return "\n\n".join(context_parts)


def _build_history_text(history):
    """Format last 4 conversation turns for prompt injection."""
    if not history:
        return ""
    lines = []
    for turn in history[-4:]:
        lines.append(f"USER: {turn['user']}\nGUNTER: {turn['gunter']}")
    return "\n\n".join(lines) + "\n\n"


def _build_vehicle_header(config):
    """Build vehicle identification string injected into every prompt."""
    return (f"VEHICLE: {config['year']} Vanagon "
            f"{config['engine']} {config['trans']} transmission {config['model']}")


# ── LLM routing ───────────────────────────────────────────────────────────────
def ask_gunter(question, history=None, van_config=None):
    """
    Route to the active provider from providers.json.
    Falls back to .env LLM_MODE if providers.json has no key set.
    """
    provider = get_active_provider()
    name     = provider.get("name", "anthropic")
    api_key  = provider.get("api_key", "").strip()
    model    = provider.get("model", "")

    # If the active provider has no key yet, fall back to legacy .env routing
    if not api_key:
        if LLM_MODE == "claude":
            return _ask_claude(question, history, van_config)
        if name == "ollama":
            return _ask_llama(question, history, van_config, model=model)
        return _ask_llama(question, history, van_config)

    if name == "anthropic":
        return _ask_claude(question, history, van_config,
                           api_key=api_key, model=model)
    elif name == "openai":
        return _ask_openai(question, history, van_config,
                           api_key=api_key, model=model)
    elif name == "groq":
        return _ask_groq(question, history, van_config,
                         api_key=api_key, model=model)
    elif name == "openrouter":
        return _ask_openrouter(question, history, van_config,
                               api_key=api_key, model=model)
    elif name == "ollama":
        return _ask_llama(question, history, van_config, model=model)
    # Unknown provider — fall back to local
    return _ask_llama(question, history, van_config)


def _identify_systems(question):
    """
    Map question keywords to vanagon_wiki system directory names.
    Returns a list of system names relevant to the question.
    Multiple systems can match — e.g. 'overheating head gasket' hits both
    cooling and engine.
    """
    q = question.lower()
    system_keywords = {
        "engine":       ["engine", "oil", "lifter", "head gasket", "compression",
                         "pushrod", "valve", "wasserboxer", "wbx", "rebuild",
                         "timing", "crankshaft", "piston", "rod bearing",
                         "oil pressure", "oil filter", "oil change", "smoke",
                         "misfire", "knock", "tick", "rattle"],
        "cooling":      ["overheat", "coolant", "temperature", "temp", "radiator",
                         "aux pump", "auxiliary pump", "water pump", "thermostat",
                         "fan", "cooling system", "antifreeze", "boil", "steam",
                         "head gasket", "white smoke", "milky oil"],
        "fuel":         ["idle", "surge", "hunt", "digifant", "fuel pump",
                         "fuel filter", "fuel pressure", "rich", "lean", "afm",
                         "throttle", "injector", "ecu", "ecm", "hall sender",
                         "no start", "hard start", "stall", "fuel smell",
                         "oxygen sensor", "o2 sensor", "maf", "map sensor"],
        "transmission": ["transmission", "trans", "gear", "shift", "clutch",
                         "automatic", "manual", "atf", "fluid", "slip",
                         "kickdown", "neutral", "reverse"],
        "brakes":       ["brake", "rotor", "pad", "caliper", "brake fluid",
                         "dot4", "abs", "parking brake", "emergency brake",
                         "squeaking", "grinding brakes", "pedal"],
        "suspension":   ["bearing", "wheel bearing", "tire", "tyre", "pressure",
                         "psi", "alignment", "steering", "suspension",
                         "shock", "spring", "wobble", "vibration", "noise wheel",
                         "front wheel", "rear wheel"],
        "electrical":   ["electrical", "wiring", "fuse", "relay", "battery",
                         "alternator", "voltage", "ground", "short circuit",
                         "gremlin", "intermittent", "light", "charging",
                         "starter", "ignition switch"],
        "body":         ["sliding door", "door roller", "pop top", "poptop",
                         "westfalia", "westy", "camper", "refrigerator",
                         "fridge", "propane", "sink", "water tank", "heater",
                         "canvas", "seal", "window"],
        "parts":        ["part number", "part #", "oem", "replacement",
                         "wix", "mann", "mahle", "ngk", "bosch",
                         "where to buy", "supplier", "cross reference"],
    }
    matched = []
    for system, keywords in system_keywords.items():
        if any(kw in q for kw in keywords):
            matched.append(system)
    return matched


def _load_wiki_context(systems):
    """
    Read relevant vanagon_wiki pages for the identified systems.
    Returns a formatted string ready for prompt injection.
    Silently skips missing files — wiki is optional enhancement.
    """
    if not systems or not os.path.exists(WIKI_PATH):
        return ""

    # Map system name to the most useful wiki pages for that system
    system_pages = {
        "engine":       ["engine/wasserboxer-overview.md",
                         "engine/head-gasket.md",
                         "engine/oil-system.md",
                         "engine/ignition.md",
                         "engine/valve-train.md"],
        "cooling":      ["cooling/overview.md",
                         "cooling/aux-water-pump.md",
                         "cooling/thermostat.md",
                         "cooling/temperature-sensors.md",
                         "cooling/water-pump.md"],
        "fuel":         ["fuel/digifant-overview.md",
                         "fuel/idle-system.md",
                         "fuel/fuel-pump.md",
                         "fuel/fuel-filter.md"],
        "transmission": ["transmission/automatic.md",
                         "transmission/manual.md"],
        "brakes":       ["brakes/front-disc.md",
                         "brakes/rear.md",
                         "brakes/fluid.md"],
        "suspension":   ["suspension/front-bearings.md",
                         "suspension/rear-bearings.md",
                         "suspension/tires.md"],
        "electrical":   ["electrical/overview.md",
                         "electrical/charging.md"],
        "body":         ["body/westfalia.md",
                         "body/sliding-door.md"],
        "parts":        ["parts/cross-reference.md"],
    }

    # Collect unique pages across all matched systems
    pages_to_load = []
    seen = set()
    for system in systems:
        for page in system_pages.get(system, []):
            if page not in seen:
                pages_to_load.append(page)
                seen.add(page)

    # Always include parts cross-reference for part number questions
    if "parts/cross-reference.md" not in seen and any(
            s in systems for s in ["suspension", "engine", "brakes", "cooling"]):
        pages_to_load.append("parts/cross-reference.md")

    # Load and format pages — skip missing files gracefully
    wiki_sections = []
    for page in pages_to_load:
        full_path = os.path.join(WIKI_PATH, page)
        if not os.path.exists(full_path):
            continue
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
            if content:
                wiki_sections.append(f"--- {page} ---\n{content}")
        except OSError:
            pass

    if not wiki_sections:
        return ""

    return "VANAGON WIKI — VERIFIED REFERENCE:\n" + "\n\n".join(wiki_sections)


def _build_user_content(question, history, van_config):
    """Shared prompt assembly for all cloud providers."""
    docs         = retriever.invoke(question)
    context      = _build_context(docs)
    history_text = _build_history_text(history)
    vehicle      = _build_vehicle_header(van_config or CONFIG_DEFAULTS)
    svc_summary  = _build_service_summary()

    # Identify relevant systems and inject wiki pages directly into prompt
    systems      = _identify_systems(question)
    wiki_context = _load_wiki_context(systems)

    # Build prompt — wiki context goes between vehicle header and RAG context
    # so the model sees verified facts before forum/manual fragments
    wiki_section = f"\n{wiki_context}\n" if wiki_context else ""

    return f"""{vehicle}
{svc_summary}
{wiki_section}
CONTEXT FROM BENTLEY/DIGIFANT MANUALS AND FORUM:
{context}

CONVERSATION SO FAR:
{history_text}USER: {question}"""


def _ask_llama(question, history=None, van_config=None, model=None):
    """Local Ollama inference — fully offline. Model set via LOCAL_MODEL in .env."""
    docs         = retriever.invoke(question)
    context      = _build_context(docs)
    history_text = _build_history_text(history)
    vehicle      = _build_vehicle_header(van_config or CONFIG_DEFAULTS)
    svc_summary  = _build_service_summary()
    active_model = model or LOCAL_MODEL

    # Wiki injection — local models read structured markdown well
    systems      = _identify_systems(question)
    wiki_context = _load_wiki_context(systems)
    wiki_section = f"\n{wiki_context}\n" if wiki_context else ""

    full_prompt = f"""SYSTEM: {GUNTER_SYSTEM}

{vehicle}
{svc_summary}
{wiki_section}
CONTEXT FROM BENTLEY/DIGIFANT MANUALS AND FORUM:
{context}

CONVERSATION SO FAR:
{history_text}USER: {question}
GUNTER:"""

    payload = {
        "model": active_model,
        "prompt": full_prompt,
        "stream": False,
        "options": {
            "num_predict": 300,
            "num_ctx":     16384,
            "temperature": 0.2
        }
    }
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json=payload, timeout=600
        )
        return response.json().get(
            "response", "The Bentley is greasy and I cannot read it.")
    except Exception as e:
        return f"Ach! My brain is stalled: {e}"


def _ask_claude(question, history=None, van_config=None,
                api_key=None, model=None):
    """Anthropic Claude API — key and model from providers.json via Settings."""
    key  = api_key or ""
    mdl  = model   or "claude-haiku-4-5-20251001"
    if not key:
        return "Ach! No Anthropic API key set. Add it in Settings → API Providers."
    user_content = _build_user_content(question, history, van_config)
    try:
        client   = anthropic.Anthropic(api_key=key)
        response = client.messages.create(
            model=mdl,
            max_tokens=4096,
            system=GUNTER_SYSTEM,
            messages=[{"role": "user", "content": user_content}]
        )
        return response.content[0].text
    except Exception as e:
        return f"Ach! Claude is unavailable: {e}. Check your key in Settings."


def _ask_openai(question, history=None, van_config=None,
                api_key=None, model="gpt-4o-mini"):
    """OpenAI ChatCompletion API."""
    user_content = _build_user_content(question, history, van_config)
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}",
                     "Content-Type": "application/json"},
            json={
                "model": model,
                "max_tokens": 4096,
                "temperature": 0.2,
                "messages": [
                    {"role": "system", "content": GUNTER_SYSTEM},
                    {"role": "user",   "content": user_content},
                ]
            },
            timeout=60
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.HTTPError as e:
        # Surface the actual OpenAI error message (e.g. model_not_found)
        try:
            detail = e.response.json().get("error", {}).get("message", str(e))
        except Exception:
            detail = str(e)
        return f"Ach! OpenAI error ({e.response.status_code}): {detail}"
    except Exception as e:
        return f"Ach! OpenAI is unavailable: {e}"


def _ask_groq(question, history=None, van_config=None,
              api_key=None, model="llama3-8b-8192"):
    """Groq inference API — OpenAI-compatible endpoint."""
    user_content = _build_user_content(question, history, van_config)
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}",
                     "Content-Type": "application/json"},
            json={
                "model": model,
                "max_tokens": 4096,
                "temperature": 0.2,
                "messages": [
                    {"role": "system", "content": GUNTER_SYSTEM},
                    {"role": "user",   "content": user_content},
                ]
            },
            timeout=60
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.HTTPError as e:
        try:
            detail = e.response.json().get("error", {}).get("message", str(e))
        except Exception:
            detail = str(e)
        return f"Ach! Groq error ({e.response.status_code}): {detail}"
    except Exception as e:
        return f"Ach! Groq is unavailable: {e}"


def _ask_openrouter(question, history=None, van_config=None,
                    api_key=None, model="mistralai/mistral-7b-instruct"):
    """OpenRouter — routes to many providers via single OpenAI-compatible API."""
    user_content = _build_user_content(question, history, van_config)
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}",
                     "Content-Type": "application/json",
                     "HTTP-Referer": "https://github.com/GunterAI",
                     "X-Title": "Gunter AI Vanagon Mechanic"},
            json={
                "model": model,
                "max_tokens": 4096,
                "temperature": 0.2,
                "messages": [
                    {"role": "system", "content": GUNTER_SYSTEM},
                    {"role": "user",   "content": user_content},
                ]
            },
            timeout=60
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.HTTPError as e:
        try:
            detail = e.response.json().get("error", {}).get("message", str(e))
        except Exception:
            detail = str(e)
        return f"Ach! OpenRouter error ({e.response.status_code}): {detail}"
    except Exception as e:
        return f"Ach! OpenRouter is unavailable: {e}"


# ── Whisper — loaded once at module level ─────────────────────────────────────
whisper_model_global = WhisperModel(
    MODEL_SIZE,
    device="cpu",
    compute_type="int8",
    local_files_only=True
)


# ── Button helper ─────────────────────────────────────────────────────────────
def _make_button(parent, text, command,
                 bg=FRAME_BLUE, fg=BG, active_bg=FRAME_DIM):
    return tk.Button(
        parent,
        text=text,
        command=command,
        bg=bg,
        fg=fg,
        activebackground=active_bg,
        activeforeground=GOLD,
        font=("Courier", 10, "bold"),
        relief="flat",
        bd=0,
        cursor="hand2",
        padx=8,
        pady=6,
    )


def _make_dropdown(parent, label_text, variable, options):
    """Themed label + OptionMenu pair."""
    tk.Label(parent, text=label_text, fg=GOLD_DIM, bg=BG,
             font=("Courier", 8), anchor="w").pack(fill="x", padx=12)
    menu = tk.OptionMenu(parent, variable, *options)
    menu.config(
        bg=FRAME_DIM, fg=TEXT_MAIN,
        activebackground=FRAME_BLUE, activeforeground=GOLD,
        font=("Courier", 9), relief="flat",
        highlightthickness=0, bd=0,
        indicatoron=True, width=12,
    )
    menu["menu"].config(
        bg=FRAME_DIM, fg=TEXT_MAIN,
        activebackground=FRAME_BLUE, activeforeground=GOLD,
        font=("Courier", 9)
    )
    menu.pack(fill="x", padx=12, pady=(0, 4))
    return menu


# ── Main GUI ──────────────────────────────────────────────────────────────────
class GunterGUI(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Gunter AI v2.0 - Vanagon Diagnostic Command")
        self.geometry("1024x600")
        self.configure(bg=BG)
        self.resizable(True, True)

        # Conversation memory
        self.conversation_history = []

        # Load persisted configs
        self._van_config      = load_van_config()
        self._service_records = load_service_records()

        # tkinter vars for vehicle config modal
        self.var_year   = tk.StringVar(value=self._van_config["year"])
        self.var_engine = tk.StringVar(value=self._van_config["engine"])
        self.var_trans  = tk.StringVar(value=self._van_config["trans"])
        self.var_model  = tk.StringVar(value=self._van_config["model"])

        # Event used by LISTEN button in manual wake mode
        self._manual_listen_event = threading.Event()

        self._build_layout()
        self._start_clock()

        self.logic_thread = threading.Thread(target=self.run_logic, daemon=True)
        self.logic_thread.start()

        # Kiosk / fullscreen — uncomment for CrowPi touchscreen deployment
        self.update_idletasks()
        # self.attributes("-fullscreen", True)
        # self.lift()
        # self.attributes("-topmost", True)
        # self.focus_force()
        self.bind("<Escape>", lambda event: self.attributes("-fullscreen", False))

    # ── Layout ────────────────────────────────────────────────────────────────
    def _build_layout(self):
        tk.Frame(self, bg=RED_ALERT, height=4).pack(fill="x", side="top")

        title_bar = tk.Frame(self, bg=BG)
        title_bar.pack(fill="x", side="top", pady=(4, 0))

        tk.Label(title_bar, text="GUNTER", fg=GOLD, bg=BG,
                 font=("Courier", 28, "bold")).pack(side="left", padx=(16, 4))
        tk.Label(title_bar, text="VANAGON DIAGNOSTIC COMMAND",
                 fg=TEXT_SUB, bg=BG,
                 font=("Courier", 12)).pack(side="left", padx=4, pady=8)

        # EXIT SHOP — title bar far right
        tk.Button(title_bar, text="EXIT SHOP",
                  command=self.quit_gunter,
                  bg=RED_ALERT, fg=RED_BRIGHT,
                  activebackground=RED_BRIGHT, activeforeground=GOLD,
                  font=("Courier", 10, "bold"),
                  relief="flat", bd=0, cursor="hand2",
                  padx=10, pady=4).pack(side="right", padx=(0, 8))

        self.stardate_lbl = tk.Label(title_bar, text="", fg=GOLD_DIM, bg=BG,
                                     font=("Courier", 11))
        self.stardate_lbl.pack(side="right", padx=16)

        tk.Frame(self, bg=FRAME_BLUE, height=3).pack(fill="x")
        tk.Frame(self, bg=FRAME_DIM,  height=1).pack(fill="x")

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True)

        sidebar = tk.Frame(body, bg=BG, width=160)
        sidebar.pack(side="left", fill="y", padx=(10, 0), pady=8)
        sidebar.pack_propagate(False)
        self._build_sidebar(sidebar)

        tk.Frame(body, bg=FRAME_BLUE, width=3).pack(
            side="left", fill="y", padx=(6, 6), pady=8)

        chat_area = tk.Frame(body, bg=BG)
        chat_area.pack(side="right", fill="both", expand=True,
                       padx=(0, 10), pady=8)
        self._build_chat(chat_area)

    def _build_sidebar(self, parent):
        # ── Bottom section anchored first ─────────────────────────────────────
        bottom = tk.Frame(parent, bg=BG)
        bottom.pack(side="bottom", fill="x")

        self.temp_label = tk.Label(bottom, text="CPU TEMP: --°C",
                                   fg=TEXT_SUB, bg=BG,
                                   font=("Courier", 10))
        self.temp_label.pack(pady=(0, 8))
        self.update_temp()

        # ── Top section ───────────────────────────────────────────────────────
        top = tk.Frame(parent, bg=BG)
        top.pack(side="top", fill="both", expand=True)

        # VW Logo — 50x50
        image_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "vw_logo.png")
        try:
            pil_img = Image.open(image_path).resize(
                (50, 50), Image.Resampling.LANCZOS)
            self._logo_photo = ImageTk.PhotoImage(pil_img)
            tk.Label(top, image=self._logo_photo, bg=BG).pack(pady=(10, 2))
        except (FileNotFoundError, OSError, AttributeError):
            tk.Label(top, text="[VW]", fg=GOLD_DIM, bg=BG,
                     font=("Courier", 14)).pack(pady=(10, 2))

        tk.Label(top, text="GUNTER v2.0", fg=GOLD, bg=BG,
                 font=("Courier", 14, "bold")).pack(pady=(2, 6))

        tk.Frame(top, bg=FRAME_BLUE, height=2).pack(fill="x", pady=(0, 6))

        # ── Action buttons ────────────────────────────────────────────────────
        _make_button(top, "OPEN BENTLEY",
                     self.open_bentley_manual,
                     bg=FRAME_BLUE, fg=BG,
                     active_bg=FRAME_DIM).pack(fill="x", padx=12, pady=2)

        _make_button(top, "CHAT HISTORY",
                     self.show_chat_history,
                     bg=FRAME_DIM, fg=GOLD,
                     active_bg=FRAME_BLUE).pack(fill="x", padx=12, pady=2)

        _make_button(top, "SERVICE HISTORY",
                     self.show_service_history,
                     bg=FRAME_DIM, fg=AMBER,
                     active_bg=FRAME_BLUE).pack(fill="x", padx=12, pady=2)

        _make_button(top, "NEW SESSION",
                     self.new_session,
                     bg=GOLD_DIM, fg=BG,
                     active_bg=GOLD).pack(fill="x", padx=12, pady=2)

        if WAKE_MODE == "manual":
            _make_button(top, "● LISTEN",
                         self._trigger_manual_listen,
                         bg=FRAME_BLUE, fg=CYAN,
                         active_bg=FRAME_DIM).pack(fill="x", padx=12, pady=2)

        # ── MY VANAGON — single button opens config modal ─────────────────────
        tk.Frame(top, bg=FRAME_DIM, height=1).pack(fill="x", pady=(8, 4))

        _make_button(top, "MY VANAGON",
                     self.show_vehicle_config,
                     bg=FRAME_DIM, fg=CYAN,
                     active_bg=FRAME_BLUE).pack(fill="x", padx=12, pady=2)

        # Summary label — shows current config at a glance
        self.van_summary_lbl = tk.Label(
            top,
            text=self._van_summary_text(),
            fg=TEXT_SUB, bg=BG,
            font=("Courier", 8),
            justify="center"
        )
        self.van_summary_lbl.pack(padx=4, pady=(2, 4))

        tk.Frame(top, bg=FRAME_DIM, height=1).pack(fill="x", pady=(4, 4))

        _make_button(top, "⚙ SETTINGS",
                     self.show_settings,
                     bg=FRAME_DIM, fg=AMBER,
                     active_bg=FRAME_BLUE).pack(fill="x", padx=12, pady=2)

    def _van_summary_text(self):
        """Two-line summary of current vehicle config for sidebar display."""
        c = self._van_config
        return f"{c['year']} · {c['engine']}\n{c['trans']} · {c['model']}"

    def _build_chat(self, parent):
        # Console header — label left, mode indicator right
        console_header = tk.Frame(parent, bg=BG)
        console_header.pack(fill="x", padx=4, pady=(0, 4))

        tk.Label(console_header, text="DIAGNOSTIC CONSOLE", fg=GOLD, bg=BG,
                 font=("Courier", 10, "bold"), anchor="w").pack(side="left")

        # Show active provider label (from providers.json) or fall back to LLM_MODE
        _ap       = get_active_provider()
        _ap_name  = _ap.get("name", "")
        _ap_key   = _ap.get("api_key", "").strip()
        _ap_label = _ap.get("label", LLM_MODE.upper()) if (_ap_key or _ap_name == "ollama") else LLM_MODE.upper()
        mode_color = GREEN_LIT if _ap_name == "ollama" else (
                     CYAN if _ap_key else GREEN_LIT)
        self.mode_indicator = tk.Label(
            console_header,
            text=f"[{_ap_label.upper()} / {WAKE_MODE.upper()}]",
            fg=mode_color, bg=BG,
            font=("Courier", 10))
        self.mode_indicator.pack(side="right")

        self.textbox = tk.Text(
            parent,
            bg="#050510",
            fg=TEXT_MAIN,
            font=("Courier", 13),
            relief="flat",
            bd=0,
            wrap="word",
            insertbackground=GOLD,
            padx=10,
            pady=6,
        )

        scrollbar = tk.Scrollbar(parent, bg=FRAME_DIM,
                                 troughcolor=BG, relief="flat")
        scrollbar.pack(side="right", fill="y")
        self.textbox.pack(fill="both", expand=True, padx=(4, 0))
        self.textbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.textbox.yview)

        # ── Right-click context menu for copy/paste ───────────────────────────
        def _show_context_menu(event):
            menu = tk.Menu(self.textbox, tearoff=0,
                           bg=FRAME_DIM, fg=TEXT_MAIN,
                           activebackground=FRAME_BLUE, activeforeground=GOLD,
                           font=("Courier", 10))
            menu.add_command(label="Copy",
                             command=lambda: self.textbox.event_generate("<<Copy>>"))
            menu.add_command(label="Select All",
                             command=lambda: self.textbox.tag_add(
                                 "sel", "1.0", "end"))
            menu.tk_popup(event.x_root, event.y_root)
        self.textbox.bind("<Button-3>", _show_context_menu)

        if WAKE_MODE == "picovoice":
            wake_hint = "Say 'Hey Gunter'"
        elif WAKE_MODE == "manual":
            wake_hint = "Press LISTEN then speak"
        else:
            wake_hint = "Type question below and press SEND or Enter"

        self.textbox.insert(
            "0.0",
            f"Gunter: Standing by... {wake_hint}\n"
            f"Mode: {_ap_label.upper()} / {WAKE_MODE.upper()}\n\n"
        )
        tk.Frame(parent, bg=FRAME_BLUE, height=1).pack(fill="x", pady=(4, 0))

        # ── Text input bar — only shown in WAKE_MODE=text ─────────────────────
        if WAKE_MODE == "text":
            input_frame = tk.Frame(parent, bg=FRAME_DIM)
            input_frame.pack(fill="x", padx=4, pady=(4, 0))

            self._text_input_var = tk.StringVar()
            self._text_entry = tk.Entry(
                input_frame,
                textvariable=self._text_input_var,
                bg=BG, fg=TEXT_MAIN,
                insertbackground=GOLD,
                font=("Courier", 12),
                relief="flat",
                bd=4,
            )
            self._text_entry.pack(side="left", fill="x", expand=True,
                                  padx=(6, 4), pady=6)

            tk.Button(
                input_frame,
                text="SEND",
                command=self._submit_text_input,
                bg=FRAME_BLUE, fg=BG,
                activebackground=FRAME_DIM, activeforeground=GOLD,
                font=("Courier", 10, "bold"),
                relief="flat", bd=0, cursor="hand2",
                padx=12, pady=4,
            ).pack(side="right", padx=(0, 6), pady=6)

            # Enter key submits
            self._text_entry.bind("<Return>",
                                  lambda e: self._submit_text_input())

    # ── Clock ─────────────────────────────────────────────────────────────────
    def _start_clock(self):
        self.stardate_lbl.config(text=time.strftime("SD %Y.%j  %H:%M:%S"))
        self.after(1000, self._start_clock)  # noqa

    # ── Text output ───────────────────────────────────────────────────────────
    def update_text(self, text):
        def _insert():
            self.textbox.insert("end", text + "\n")
            self.textbox.see("end")
        self.after(0, _insert) # noqa

    # ── Sidebar actions ───────────────────────────────────────────────────────
    def open_bentley_manual(self):
        self.update_text("Gunter: Opening the full Bentley for you, Hans.")
        subprocess.run(["pkill", "evince"])
        subprocess.Popen(["evince", BENTLEY_PATH])

    def show_chat_history(self):
        """Display the chat/diagnostic log in the console."""
        self.update_text("\n--- CHAT HISTORY ---")
        try:
            with open("service_history.txt", "r") as f:
                self.update_text(f.read())
        except FileNotFoundError:
            self.update_text(
                "Gunter: 'No records found. Are you even maintaining this bus?'")
        except Exception as e:
            self.update_text(f"Gunter: 'Ach! I cannot read the logbook: {e}'")

    def new_session(self):
        """Clear conversation history — start a fresh diagnostic session."""
        self.conversation_history = []
        cfg = self._van_config
        self.update_text(
            f"\n--- NEW SESSION STARTED — Memory cleared ---\n"
            f"Vehicle: {cfg['year']} Vanagon {cfg['engine']} "
            f"{cfg['trans']} {cfg['model']}\n"
        )

    def _trigger_manual_listen(self):
        """Signal the background thread to record (manual wake mode only)."""
        self._manual_listen_event.set()
        self.update_text("\n[!] Gunter: Ja? I am listening...")

    def _submit_text_input(self):
        """Handle text input submission — WAKE_MODE=text only."""
        question = self._text_input_var.get().strip()
        if not question:
            return
        self._text_input_var.set("")       # clear entry field
        self._text_entry.focus_set()       # keep focus for next question
        threading.Thread(
            target=self._handle_question,
            args=(question,),
            daemon=True
        ).start()

    def _handle_text_question(self, question):
        """Background worker for text mode — keeps GUI responsive."""
        self._handle_question(question)

    def quit_gunter(self):
        self.update_text("Gunter: shutting down systems... Gute Fahrt!")
        print("Gunter: Emergency Shutdown... Auf Wiedersehen!")
        self.after(500, os._exit, 0)

    # ── Service History Modal ─────────────────────────────────────────────────
    def show_service_history(self):
        """Open modal popup showing service records with EDIT buttons."""
        modal = tk.Toplevel(self)
        modal.title("Service History")
        modal.configure(bg=BG)
        modal.geometry("500x500")
        modal.transient(self)
        modal.grab_set()

        # Center the modal
        modal.update_idletasks()
        x = (self.winfo_screenwidth()  // 2) - 250
        y = (self.winfo_screenheight() // 2) - 250
        modal.geometry(f"500x500+{x}+{y}")

        # Header
        tk.Frame(modal, bg=RED_ALERT, height=3).pack(fill="x")
        hdr = tk.Frame(modal, bg=BG)
        hdr.pack(fill="x", pady=(6, 0))
        tk.Label(hdr, text="SERVICE HISTORY", fg=GOLD, bg=BG,
                 font=("Courier", 14, "bold")).pack(side="left", padx=12)
        tk.Button(hdr, text="✕ CLOSE", command=modal.destroy,
                  bg=RED_ALERT, fg=RED_BRIGHT,
                  activebackground=RED_BRIGHT, activeforeground=GOLD,
                  font=("Courier", 10, "bold"),
                  relief="flat", bd=0, cursor="hand2",
                  padx=8, pady=3).pack(side="right", padx=12)
        tk.Frame(modal, bg=FRAME_BLUE, height=2).pack(fill="x", pady=(6, 4))

        # ── CURRENT STATUS section ────────────────────────────────────────────
        records = load_service_records()
        today   = datetime.datetime.now().strftime("%m/%d/%Y")

        status_frame = tk.Frame(modal, bg=FRAME_DIM)
        status_frame.pack(fill="x", padx=8, pady=(0, 6))

        tk.Label(status_frame, text="CURRENT STATUS", fg=CYAN, bg=FRAME_DIM,
                 font=("Courier", 9, "bold"), anchor="w").pack(
                     fill="x", padx=8, pady=(4, 2))

        # Date row
        date_row = tk.Frame(status_frame, bg=FRAME_DIM)
        date_row.pack(fill="x", padx=8, pady=2)
        tk.Label(date_row, text="Date:", fg=TEXT_SUB, bg=FRAME_DIM,
                 font=("Courier", 10), width=8, anchor="w").pack(side="left")
        cur_date_var = tk.StringVar(
            value=records.get("current_date", "") or today)
        cur_date_entry = tk.Entry(
            date_row, textvariable=cur_date_var, width=14,
            bg=BG, fg=TEXT_MAIN, insertbackground=GOLD,
            font=("Courier", 10), relief="flat")
        cur_date_entry.pack(side="left", padx=(0, 6))

        # TODAY button auto-fills date
        tk.Button(date_row, text="TODAY",
                  command=lambda: cur_date_var.set(today),
                  bg=FRAME_BLUE, fg=BG,
                  activebackground=FRAME_DIM, activeforeground=GOLD,
                  font=("Courier", 9, "bold"),
                  relief="flat", bd=0, cursor="hand2",
                  padx=6, pady=2).pack(side="left")

        # Miles row
        miles_row = tk.Frame(status_frame, bg=FRAME_DIM)
        miles_row.pack(fill="x", padx=8, pady=2)
        tk.Label(miles_row, text="Miles:", fg=TEXT_SUB, bg=FRAME_DIM,
                 font=("Courier", 10), width=8, anchor="w").pack(side="left")
        cur_miles_var = tk.StringVar(
            value=records.get("current_miles", ""))
        tk.Entry(miles_row, textvariable=cur_miles_var, width=14,
                 bg=BG, fg=TEXT_MAIN, insertbackground=GOLD,
                 font=("Courier", 10), relief="flat").pack(side="left")

        def _save_status():
            records["current_date"]  = cur_date_var.get().strip() # noqa
            records["current_miles"] = cur_miles_var.get().strip() # noqa
            save_service_records(records)
            self._service_records = records

        tk.Button(status_frame, text="SAVE STATUS",
                  command=_save_status,
                  bg=FRAME_BLUE, fg=BG,
                  activebackground=FRAME_DIM, activeforeground=GOLD,
                  font=("Courier", 9, "bold"),
                  relief="flat", bd=0, cursor="hand2",
                  padx=8, pady=3).pack(anchor="e", padx=8, pady=(2, 6))

        tk.Frame(modal, bg=FRAME_BLUE, height=2).pack(fill="x", pady=(0, 4))

        # ── Scrollable service record list ────────────────────────────────────
        canvas    = tk.Canvas(modal, bg=BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(modal, orient="vertical",
                                 command=canvas.yview,
                                 bg=FRAME_DIM, troughcolor=BG)
        frame     = tk.Frame(canvas, bg=BG)

        frame.bind("<Configure>",
                   lambda e: canvas.configure(
                       scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=(8, 0))
        scrollbar.pack(side="right", fill="y")

        for item in SERVICE_ITEMS:
            rec   = records.get(item["key"], {"date": "", "miles": ""})
            date  = rec.get("date",  "") or "--/--/----"
            miles = rec.get("miles", "") or "-----"

            row = tk.Frame(frame, bg=BG)
            row.pack(fill="x", padx=8, pady=3)

            # Blue accent bar
            tk.Frame(row, bg=FRAME_BLUE, width=6, height=24).pack(
                side="left", padx=(0, 8))

            tk.Label(row, text=item["label"], fg=TEXT_MAIN, bg=BG,
                     font=("Courier", 10), width=16, anchor="w").pack(side="left")
            tk.Label(row, text=date, fg=GOLD, bg=BG,
                     font=("Courier", 10), width=12, anchor="w").pack(side="left")
            tk.Label(row, text=f"{miles} mi", fg=TEXT_SUB, bg=BG,
                     font=("Courier", 10), width=10, anchor="w").pack(side="left")

            tk.Button(row, text="EDIT",
                      command=lambda k=item["key"], l=item["label"],
                                     m=modal: self._edit_service_record(k, l, m),
                      bg=FRAME_DIM, fg=GOLD,
                      activebackground=FRAME_BLUE, activeforeground=GOLD,
                      font=("Courier", 9, "bold"),
                      relief="flat", bd=0, cursor="hand2",
                      padx=6, pady=2).pack(side="right", padx=4)

            tk.Frame(frame, bg=FRAME_DIM, height=1).pack(
                fill="x", padx=8, pady=(0, 2))

    def _edit_service_record(self, key, label, parent_modal):
        """Open a small dialog to update date and miles for a service item."""
        records = load_service_records()
        rec     = records.get(key, {"date": "", "miles": ""})

        dialog = tk.Toplevel(parent_modal)
        dialog.title(f"Update: {label}")
        dialog.configure(bg=BG)
        dialog.geometry("320x200")
        dialog.transient(parent_modal)
        dialog.grab_set()

        # Center over parent modal
        dialog.update_idletasks()
        x = parent_modal.winfo_x() + (parent_modal.winfo_width()  // 2) - 160
        y = parent_modal.winfo_y() + (parent_modal.winfo_height() // 2) - 100
        dialog.geometry(f"320x200+{x}+{y}")

        tk.Frame(dialog, bg=RED_ALERT, height=3).pack(fill="x")
        tk.Label(dialog, text=f"Update: {label}", fg=GOLD, bg=BG,
                 font=("Courier", 12, "bold")).pack(pady=(10, 6))
        tk.Frame(dialog, bg=FRAME_BLUE, height=1).pack(fill="x", pady=(0, 8))

        # Date field
        date_row = tk.Frame(dialog, bg=BG)
        date_row.pack(fill="x", padx=20, pady=4)
        tk.Label(date_row, text="Date (MM/DD/YYYY):", fg=TEXT_SUB, bg=BG,
                 font=("Courier", 10), width=20, anchor="w").pack(side="left")
        date_var = tk.StringVar(value=rec.get("date", ""))
        tk.Entry(date_row, textvariable=date_var, width=12,
                 bg=FRAME_DIM, fg=TEXT_MAIN, insertbackground=GOLD,
                 font=("Courier", 10), relief="flat").pack(side="left")

        # Miles field
        miles_row = tk.Frame(dialog, bg=BG)
        miles_row.pack(fill="x", padx=20, pady=4)
        tk.Label(miles_row, text="Odometer (miles):", fg=TEXT_SUB, bg=BG,
                 font=("Courier", 10), width=20, anchor="w").pack(side="left")
        miles_var = tk.StringVar(value=rec.get("miles", ""))
        tk.Entry(miles_row, textvariable=miles_var, width=12,
                 bg=FRAME_DIM, fg=TEXT_MAIN, insertbackground=GOLD,
                 font=("Courier", 10), relief="flat").pack(side="left")

        def _save():
            records[key] = {
                "date":  date_var.get().strip(),
                "miles": miles_var.get().strip()
            }
            save_service_records(records)
            self._service_records = records
            dialog.destroy()
            # Rebuild parent modal to refresh displayed values
            parent_modal.destroy()
            self.show_service_history()

        def _cancel():
            dialog.destroy()

        btn_row = tk.Frame(dialog, bg=BG)
        btn_row.pack(pady=10)
        tk.Button(btn_row, text="SAVE",
                  command=_save,
                  bg=FRAME_BLUE, fg=BG,
                  activebackground=FRAME_DIM, activeforeground=GOLD,
                  font=("Courier", 10, "bold"),
                  relief="flat", bd=0, cursor="hand2",
                  padx=16, pady=4).pack(side="left", padx=8)
        tk.Button(btn_row, text="CANCEL",
                  command=_cancel,
                  bg=FRAME_DIM, fg=TEXT_SUB,
                  activebackground=FRAME_BLUE, activeforeground=GOLD,
                  font=("Courier", 10, "bold"),
                  relief="flat", bd=0, cursor="hand2",
                  padx=16, pady=4).pack(side="left", padx=8)

    # ── Settings Modal ────────────────────────────────────────────────────────
    def show_settings(self):
        """Settings modal with Voice and API Provider tabs."""
        modal = tk.Toplevel(self)
        modal.title("Gunter Settings")
        modal.configure(bg=BG)
        modal.geometry("540x600")
        modal.transient(self)
        modal.grab_set()

        x = (self.winfo_screenwidth()  // 2) - 270
        y = (self.winfo_screenheight() // 2) - 280
        modal.geometry(f"540x560+{x}+{y}")

        # ── Header ────────────────────────────────────────────────────────────
        tk.Frame(modal, bg=RED_ALERT, height=3).pack(fill="x")
        hdr = tk.Frame(modal, bg=BG)
        hdr.pack(fill="x", pady=(6, 0))
        tk.Label(hdr, text="⚙ SETTINGS", fg=GOLD, bg=BG,
                 font=("Courier", 14, "bold")).pack(side="left", padx=12)
        tk.Button(hdr, text="✕ CLOSE", command=modal.destroy,
                  bg=RED_ALERT, fg=RED_BRIGHT,
                  activebackground=RED_BRIGHT, activeforeground=GOLD,
                  font=("Courier", 10, "bold"),
                  relief="flat", bd=0, cursor="hand2",
                  padx=8, pady=3).pack(side="right", padx=12)
        tk.Frame(modal, bg=FRAME_BLUE, height=2).pack(fill="x", pady=(6, 0))

        # ── Tab bar ───────────────────────────────────────────────────────────
        tab_bar = tk.Frame(modal, bg=BG)
        tab_bar.pack(fill="x")

        content_frame = tk.Frame(modal, bg=BG)
        content_frame.pack(fill="both", expand=True)

        voice_frame     = tk.Frame(content_frame, bg=BG)
        provider_frame  = tk.Frame(content_frame, bg=BG)
        picovoice_frame = tk.Frame(content_frame, bg=BG)

        active_tab = tk.StringVar(value="voice")

        def _show_tab(name):
            active_tab.set(name)
            voice_frame.pack_forget()
            provider_frame.pack_forget()
            picovoice_frame.pack_forget()
            tab_voice_btn.config(bg=FRAME_DIM,     fg=TEXT_SUB)
            tab_provider_btn.config(bg=FRAME_DIM,  fg=TEXT_SUB)
            tab_pico_btn.config(bg=FRAME_DIM,      fg=TEXT_SUB)
            if name == "voice":
                voice_frame.pack(fill="both", expand=True)
                tab_voice_btn.config(bg=FRAME_BLUE, fg=BG)
            elif name == "providers":
                provider_frame.pack(fill="both", expand=True)
                tab_provider_btn.config(bg=FRAME_BLUE, fg=BG)
            elif name == "picovoice":
                picovoice_frame.pack(fill="both", expand=True)
                tab_pico_btn.config(bg=FRAME_BLUE, fg=BG)

        tab_voice_btn = tk.Button(
            tab_bar, text="VOICE",
            command=lambda: _show_tab("voice"),
            bg=FRAME_BLUE, fg=BG,
            activebackground=FRAME_DIM, activeforeground=GOLD,
            font=("Courier", 10, "bold"),
            relief="flat", bd=0, cursor="hand2",
            padx=20, pady=6)
        tab_voice_btn.pack(side="left", padx=(12, 2), pady=6)

        tab_provider_btn = tk.Button(
            tab_bar, text="API PROVIDERS",
            command=lambda: _show_tab("providers"),
            bg=FRAME_DIM, fg=TEXT_SUB,
            activebackground=FRAME_BLUE, activeforeground=GOLD,
            font=("Courier", 10, "bold"),
            relief="flat", bd=0, cursor="hand2",
            padx=20, pady=6)
        tab_provider_btn.pack(side="left", padx=2, pady=6)

        tab_pico_btn = tk.Button(
            tab_bar, text="PICOVOICE",
            command=lambda: _show_tab("picovoice"),
            bg=FRAME_DIM, fg=TEXT_SUB,
            activebackground=FRAME_BLUE, activeforeground=GOLD,
            font=("Courier", 10, "bold"),
            relief="flat", bd=0, cursor="hand2",
            padx=20, pady=6)
        tab_pico_btn.pack(side="left", padx=2, pady=6)

        tk.Frame(modal, bg=FRAME_DIM, height=1).pack(fill="x")

        # ════════════════════════════════════════════════════════════════════
        # VOICE TAB
        # ════════════════════════════════════════════════════════════════════
        tk.Label(voice_frame,
                 text="Select Gunter's voice. Press TEST to preview.",
                 fg=TEXT_SUB, bg=BG,
                 font=("Courier", 9)).pack(anchor="w", padx=14, pady=(10, 4))

        cfg          = load_van_config()
        current_voice = cfg.get("voice_name", "L2Arctic — Speaker 0")
        selected_voice = tk.StringVar(value=current_voice)

        # Scrollable voice list
        v_canvas    = tk.Canvas(voice_frame, bg=BG, highlightthickness=0,
                                height=300)
        v_scrollbar = tk.Scrollbar(voice_frame, orient="vertical",
                                   command=v_canvas.yview,
                                   bg=FRAME_DIM, troughcolor=BG)
        v_list_frame = tk.Frame(v_canvas, bg=BG)

        v_list_frame.bind("<Configure>",
                          lambda e: v_canvas.configure(
                              scrollregion=v_canvas.bbox("all")))
        v_canvas.create_window((0, 0), window=v_list_frame, anchor="nw")
        v_canvas.configure(yscrollcommand=v_scrollbar.set)
        v_scrollbar.pack(side="right", fill="y")
        v_canvas.pack(fill="both", expand=True, padx=(12, 0))

        row_refs = {}

        def _select_voice(name):
            selected_voice.set(name)
            for n, (lbl, bar) in row_refs.items():
                is_sel = (n == name)
                lbl.config(fg=GOLD      if is_sel else TEXT_MAIN,
                           bg=FRAME_DIM if is_sel else BG)
                bar.config(bg=GOLD      if is_sel else FRAME_BLUE)

        for vname in VOICE_NAMES:
            is_current = (vname == current_voice)
            row = tk.Frame(v_list_frame, bg=FRAME_DIM if is_current else BG)
            row.pack(fill="x", pady=1)

            accent = tk.Frame(row, bg=GOLD if is_current else FRAME_BLUE,
                              width=5)
            accent.pack(side="left", fill="y")

            lbl = tk.Label(row, text=vname,
                           fg=GOLD if is_current else TEXT_MAIN,
                           bg=FRAME_DIM if is_current else BG,
                           font=("Courier", 10),
                           anchor="w", cursor="hand2")
            lbl.pack(side="left", fill="x", expand=True, padx=8, pady=4)
            lbl.bind("<Button-1>", lambda e, n=vname: _select_voice(n))
            row.bind("<Button-1>",  lambda e, n=vname: _select_voice(n))

            row_refs[vname] = (lbl, accent)

        # Voice action buttons
        v_btn_row = tk.Frame(voice_frame, bg=BG)
        v_btn_row.pack(fill="x", padx=12, pady=8)

        status_lbl = tk.Label(v_btn_row, text="", fg=CYAN, bg=BG,
                              font=("Courier", 9))
        status_lbl.pack(side="right", padx=8)

        def _test_voice():
            name = selected_voice.get()
            status_lbl.config(text="Testing voice...", fg=AMBER)
            modal.update()
            onnx_file, speaker_id = VOICE_OPTIONS.get(
                name, ("en_US-l2arctic-medium.onnx", 0))
            piper_cmd    = f"{BASE_PATH}/piper/piper"
            model_path   = f"{VOICES_PATH}/{onnx_file}"
            sample_text  = shlex.quote(
                "Hallo! I am Gunter, your Vanagon diagnostic assistant.")
            speaker_flag = f"--speaker {speaker_id} " if speaker_id is not None else ""
            cmd = (f'echo {sample_text} | {piper_cmd} --model {model_path} '
                   f'{speaker_flag}--output_file /tmp/gunter_tts.wav && '
                   f'paplay /tmp/gunter_tts.wav')
            threading.Thread(
                target=lambda: (
                    subprocess.run(cmd, shell=True),
                    status_lbl.config(text="Done.", fg=GREEN_LIT)
                ), daemon=True).start()

        def _save_voice():
            name = selected_voice.get()
            cfg  = load_van_config()
            cfg["voice_name"] = name
            save_van_config(cfg)
            status_lbl.config(text=f"Saved: {name}", fg=GREEN_LIT)

        tk.Button(v_btn_row, text="▶ TEST VOICE",
                  command=_test_voice,
                  bg=FRAME_DIM, fg=CYAN,
                  activebackground=FRAME_BLUE, activeforeground=GOLD,
                  font=("Courier", 10, "bold"),
                  relief="flat", bd=0, cursor="hand2",
                  padx=12, pady=4).pack(side="left", padx=(0, 6))

        tk.Button(v_btn_row, text="SAVE VOICE",
                  command=_save_voice,
                  bg=FRAME_BLUE, fg=BG,
                  activebackground=FRAME_DIM, activeforeground=GOLD,
                  font=("Courier", 10, "bold"),
                  relief="flat", bd=0, cursor="hand2",
                  padx=12, pady=4).pack(side="left")

        # ════════════════════════════════════════════════════════════════════
        # API PROVIDERS TAB
        # ════════════════════════════════════════════════════════════════════
        PROVIDER_LABELS = {
            "anthropic":  "Anthropic Claude",
            "openai":     "OpenAI",
            "groq":       "Groq",
            "openrouter": "OpenRouter",
            "ollama":     "Ollama (Local)",
        }

        def _rebuild_provider_tab():
            """Redraw the providers tab contents."""
            for w in provider_frame.winfo_children():
                w.destroy()

            pdata        = load_providers()
            active_name  = pdata.get("active", "anthropic")

            tk.Label(provider_frame,
                     text="Configure API keys and models for each provider.",
                     fg=TEXT_SUB, bg=BG,
                     font=("Courier", 9)).pack(anchor="w", padx=14, pady=(10, 4))

            # Scrollable provider list
            p_canvas    = tk.Canvas(provider_frame, bg=BG,
                                    highlightthickness=0, height=280)
            p_scrollbar = tk.Scrollbar(provider_frame, orient="vertical",
                                       command=p_canvas.yview,
                                       bg=FRAME_DIM, troughcolor=BG)
            p_list      = tk.Frame(p_canvas, bg=BG)
            p_list.bind("<Configure>",
                        lambda e: p_canvas.configure(
                            scrollregion=p_canvas.bbox("all")))
            p_canvas.create_window((0, 0), window=p_list, anchor="nw")
            p_canvas.configure(yscrollcommand=p_scrollbar.set)
            p_scrollbar.pack(side="right", fill="y")
            p_canvas.pack(fill="x", padx=(12, 0))

            for p in pdata["providers"]:
                is_active = (p["name"] == active_name)
                card = tk.Frame(p_list,
                                bg=FRAME_DIM if is_active else BG,
                                relief="flat")
                card.pack(fill="x", pady=2, padx=4)

                # Accent bar
                tk.Frame(card,
                         bg=GOLD if is_active else FRAME_BLUE,
                         width=5).pack(side="left", fill="y")

                info = tk.Frame(card, bg=card["bg"])
                info.pack(side="left", fill="x", expand=True, padx=8, pady=4)

                label_text = PROVIDER_LABELS.get(p["name"], p["name"])
                if is_active:
                    label_text += "  ★ ACTIVE"
                tk.Label(info, text=label_text,
                         fg=GOLD if is_active else TEXT_MAIN,
                         bg=card["bg"],
                         font=("Courier", 10, "bold")).pack(anchor="w")

                mdl_preview = p.get("model", "")[:40]
                if p["name"] == "ollama":
                    key_preview = "local — no key needed"
                else:
                    key_preview = ("●●●●●●●●" if p.get("api_key") else "no key set")
                tk.Label(info,
                         text=f"Model: {mdl_preview}  |  {key_preview}",
                         fg=TEXT_SUB, bg=card["bg"],
                         font=("Courier", 8)).pack(anchor="w")

                btn_col = tk.Frame(card, bg=card["bg"])
                btn_col.pack(side="right", padx=6, pady=4)

                tk.Button(btn_col, text="EDIT",
                          command=lambda pn=p["name"]: _edit_provider(pn),
                          bg=FRAME_BLUE, fg=BG,
                          activebackground=FRAME_DIM, activeforeground=GOLD,
                          font=("Courier", 9, "bold"),
                          relief="flat", bd=0, cursor="hand2",
                          padx=8, pady=2).pack(pady=1)

                if not is_active:
                    tk.Button(btn_col, text="SET ACTIVE",
                              command=lambda pn=p["name"]: _set_active(pn),
                              bg=GOLD_DIM, fg=BG,
                              activebackground=GOLD, activeforeground=BG,
                              font=("Courier", 9, "bold"),
                              relief="flat", bd=0, cursor="hand2",
                              padx=8, pady=2).pack(pady=1)

        def _set_active(provider_name):
            pdata = load_providers()
            pdata["active"] = provider_name
            save_providers(pdata)
            # Refresh the console mode indicator live
            _ap       = get_active_provider()
            _ap_name  = _ap.get("name", "")
            _ap_key   = _ap.get("api_key", "").strip()
            _ap_label = _ap.get("label", LLM_MODE.upper())
            _is_cloud = _ap_key or _ap_name == "ollama"
            mode_color = GREEN_LIT if _ap_name == "ollama" else (
                         CYAN if _ap_key else GREEN_LIT)
            self.mode_indicator.config(
                text=f"[{_ap_label.upper()} / {WAKE_MODE.upper()}]",
                fg=mode_color)
            _rebuild_provider_tab()

        def _edit_provider(provider_name):
            """Open edit sub-modal for a single provider."""
            pdata = load_providers()
            p     = next((x for x in pdata["providers"]
                          if x["name"] == provider_name), None)
            if not p:
                return

            edit = tk.Toplevel(modal)
            edit.title(f"Edit: {PROVIDER_LABELS.get(provider_name, provider_name)}")
            edit.configure(bg=BG)
            edit.geometry("480x560")
            edit.transient(modal)
            edit.grab_set()
            ex = modal.winfo_x() + (modal.winfo_width()  // 2) - 240
            ey = modal.winfo_y() + (modal.winfo_height() // 2) - 280
            edit.geometry(f"480x560+{ex}+{ey}")

            tk.Frame(edit, bg=RED_ALERT, height=3).pack(fill="x")
            tk.Label(edit,
                     text=f"Edit: {PROVIDER_LABELS.get(provider_name, provider_name)}",
                     fg=GOLD, bg=BG,
                     font=("Courier", 13, "bold")).pack(pady=(10, 2))
            tk.Frame(edit, bg=FRAME_BLUE, height=1).pack(fill="x", pady=(0, 8))

            body = tk.Frame(edit, bg=BG)
            body.pack(fill="x", padx=20)

            # API Key row — skip for Ollama (no key needed)
            key_var = tk.StringVar(value=p.get("api_key", ""))
            if provider_name != "ollama":
                tk.Label(body, text="API KEY:", fg=GOLD_DIM, bg=BG,
                         font=("Courier", 9), anchor="w").pack(fill="x")
                key_entry = tk.Entry(body, textvariable=key_var, width=44,
                                     bg=FRAME_DIM, fg=TEXT_MAIN,
                                     insertbackground=GOLD,
                                     font=("Courier", 10), relief="flat", show="●")
                key_entry.pack(fill="x", pady=(0, 6))

                show_key = tk.BooleanVar(value=False)
                def _toggle_key():
                    key_entry.config(show="" if show_key.get() else "●")
                tk.Checkbutton(body, text="Show key", variable=show_key,
                               command=_toggle_key,
                               fg=TEXT_SUB, bg=BG, selectcolor=FRAME_DIM,
                               activebackground=BG, activeforeground=GOLD,
                               font=("Courier", 9)).pack(anchor="w")
            else:
                tk.Label(body,
                         text="Ollama runs locally — no API key required.\n"
                              "Make sure Ollama is running before fetching models.",
                         fg=TEXT_SUB, bg=BG,
                         font=("Courier", 9), justify="left").pack(
                             anchor="w", pady=(0, 6))

            tk.Frame(body, bg=FRAME_DIM, height=1).pack(fill="x", pady=6)

            # Model selection — searchable listbox (auto-activates for large lists)
            tk.Label(body, text="MODEL:", fg=GOLD_DIM, bg=BG,
                     font=("Courier", 9), anchor="w").pack(fill="x")
            model_var = tk.StringVar(value=p.get("model", ""))

            # Fetch status + button row
            model_row = tk.Frame(body, bg=BG)
            model_row.pack(fill="x", pady=(0, 4))

            fetch_status = tk.Label(model_row, text="", fg=AMBER, bg=BG,
                                    font=("Courier", 8))
            fetch_status.pack(side="right", padx=4)

            # Current model display (always visible)
            current_model_lbl = tk.Label(body,
                textvariable=model_var,
                fg=CYAN, bg=BG,
                font=("Courier", 9), anchor="w",
                wraplength=400)
            current_model_lbl.pack(fill="x", pady=(0, 2))

            # Search + listbox container — built once, shown/hidden as needed
            search_frame = tk.Frame(body, bg=BG)

            search_var = tk.StringVar()
            search_entry = tk.Entry(
                search_frame, textvariable=search_var,
                bg=FRAME_DIM, fg=TEXT_MAIN,
                insertbackground=GOLD,
                font=("Courier", 10), relief="flat")
            search_entry.pack(fill="x", pady=(0, 2))

            list_frame = tk.Frame(search_frame, bg=BG)
            list_frame.pack(fill="x")

            model_listbox = tk.Listbox(
                list_frame,
                bg=FRAME_DIM, fg=TEXT_MAIN,
                selectbackground=FRAME_BLUE, selectforeground=GOLD,
                font=("Courier", 10),
                height=5, relief="flat",
                activestyle="none",
                exportselection=False)
            lb_scroll = tk.Scrollbar(list_frame, orient="vertical",
                                     command=model_listbox.yview,
                                     bg=FRAME_DIM, troughcolor=BG)
            model_listbox.config(yscrollcommand=lb_scroll.set)
            lb_scroll.pack(side="right", fill="y")
            model_listbox.pack(side="left", fill="x", expand=True)

            # SELECT button + hint row below listbox
            select_row = tk.Frame(search_frame, bg=BG)
            select_row.pack(fill="x", pady=(4, 0))

            def _commit_selection():
                sel = model_listbox.curselection()
                if sel:
                    chosen = model_listbox.get(sel[0])
                    model_var.set(chosen)
                    fetch_status.config(
                        text=f"Selected: {chosen[:35]}{'…' if len(chosen) > 35 else ''}",
                        fg=GREEN_LIT)

            tk.Button(select_row, text="✓ USE THIS MODEL",
                      command=_commit_selection,
                      bg=FRAME_BLUE, fg=BG,
                      activebackground=FRAME_DIM, activeforeground=GOLD,
                      font=("Courier", 9, "bold"),
                      relief="flat", bd=0, cursor="hand2",
                      padx=10, pady=3).pack(side="left")

            tk.Label(select_row,
                     text="  ← click model, then confirm",
                     fg=GOLD_DIM, bg=BG,
                     font=("Courier", 8)).pack(side="left")

            # Master model list — populated by FETCH MODELS
            _all_models = [p.get("model", "")] if p.get("model") else []

            def _populate_listbox(models_list, filter_text=""):
                model_listbox.delete(0, "end")
                needle = filter_text.lower()
                for m in models_list:
                    if needle in m.lower():
                        model_listbox.insert("end", m)
                # Highlight current selection if visible
                current = model_var.get()
                for i in range(model_listbox.size()):
                    if model_listbox.get(i) == current:
                        model_listbox.selection_set(i)
                        model_listbox.see(i)
                        break

            def _on_search(*_):
                _populate_listbox(_all_models, search_var.get())

            def _on_select(event):
                sel = model_listbox.curselection()
                if sel:
                    model_var.set(model_listbox.get(sel[0]))

            search_var.trace_add("write", _on_search)
            model_listbox.bind("<<ListboxSelect>>", _on_select)
            model_listbox.bind("<Double-Button-1>",
                               lambda e: _commit_selection())

            def _show_search_widget(models_list):
                """Switch to searchable listbox mode."""
                nonlocal _all_models
                _all_models = models_list
                search_frame.pack(fill="x", pady=(0, 4))
                search_entry.focus_set()
                _populate_listbox(models_list)

            def _fetch_models():
                fetch_status.config(text="Fetching...", fg=AMBER)
                edit.update()
                key = key_var.get().strip()

                def _do_fetch():
                    models = fetch_provider_models(provider_name, key)
                    def _update():
                        if len(models) > 20:
                            # Large list — use searchable listbox
                            _show_search_widget(models)
                        else:
                            # Small list — populate listbox directly
                            _show_search_widget(models)
                        if models and model_var.get() not in models:
                            model_var.set(models[0])
                        fetch_status.config(
                            text=f"{len(models)} models loaded",
                            fg=GREEN_LIT)
                    edit.after(0, _update)
                threading.Thread(target=_do_fetch, daemon=True).start()

            tk.Button(model_row, text="FETCH MODELS",
                      command=_fetch_models,
                      bg=FRAME_DIM, fg=CYAN,
                      activebackground=FRAME_BLUE, activeforeground=GOLD,
                      font=("Courier", 9, "bold"),
                      relief="flat", bd=0, cursor="hand2",
                      padx=8, pady=2).pack(side="left")

            # Save / Cancel
            def _save_provider():
                for px in pdata["providers"]:
                    if px["name"] == provider_name:
                        px["api_key"] = key_var.get().strip()
                        px["model"]   = model_var.get().strip()
                        break
                save_providers(pdata)
                # Refresh mode indicator if this is the active provider
                if pdata.get("active") == provider_name:
                    _ap      = get_active_provider()
                    _ap_name = _ap.get("name", "")
                    _ap_key  = _ap.get("api_key", "").strip()
                    _ap_label = _ap.get("label", LLM_MODE.upper())
                    mode_color = GREEN_LIT if _ap_name == "ollama" else (
                                 CYAN if _ap_key else GREEN_LIT)
                    self.mode_indicator.config(
                        text=f"[{_ap_label.upper()} / {WAKE_MODE.upper()}]",
                        fg=mode_color)
                edit.destroy()
                _rebuild_provider_tab()

            btn_row = tk.Frame(edit, bg=BG)
            btn_row.pack(side="bottom", pady=14)
            tk.Button(btn_row, text="SAVE",
                      command=_save_provider,
                      bg=FRAME_BLUE, fg=BG,
                      activebackground=FRAME_DIM, activeforeground=GOLD,
                      font=("Courier", 10, "bold"),
                      relief="flat", bd=0, cursor="hand2",
                      padx=16, pady=4).pack(side="left", padx=8)
            tk.Button(btn_row, text="CANCEL",
                      command=edit.destroy,
                      bg=FRAME_DIM, fg=TEXT_SUB,
                      activebackground=FRAME_BLUE, activeforeground=GOLD,
                      font=("Courier", 10, "bold"),
                      relief="flat", bd=0, cursor="hand2",
                      padx=16, pady=4).pack(side="left", padx=8)

        _rebuild_provider_tab()

        # ════════════════════════════════════════════════════════════════════
        # PICOVOICE TAB
        # ════════════════════════════════════════════════════════════════════
        tk.Label(picovoice_frame,
                 text="Picovoice powers the 'Hey Gunter' wake word.",
                 fg=TEXT_SUB, bg=BG,
                 font=("Courier", 9)).pack(anchor="w", padx=14, pady=(10, 2))
        tk.Label(picovoice_frame,
                 text="Get a free key at console.picovoice.ai",
                 fg=GOLD_DIM, bg=BG,
                 font=("Courier", 9)).pack(anchor="w", padx=14, pady=(0, 10))

        tk.Frame(picovoice_frame, bg=FRAME_BLUE, height=1).pack(
            fill="x", padx=14, pady=(0, 10))

        pv_body = tk.Frame(picovoice_frame, bg=BG)
        pv_body.pack(fill="x", padx=14)

        tk.Label(pv_body, text="API KEY:", fg=GOLD_DIM, bg=BG,
                 font=("Courier", 9), anchor="w").pack(fill="x")

        pv_data    = load_providers()
        pv_key_var = tk.StringVar(value=pv_data.get("picovoice_key", ""))

        pv_entry = tk.Entry(pv_body, textvariable=pv_key_var, width=48,
                            bg=FRAME_DIM, fg=TEXT_MAIN,
                            insertbackground=GOLD,
                            font=("Courier", 10), relief="flat", show="●")
        pv_entry.pack(fill="x", pady=(0, 4))

        pv_show = tk.BooleanVar(value=False)
        def _toggle_pv():
            pv_entry.config(show="" if pv_show.get() else "●")
        tk.Checkbutton(pv_body, text="Show key", variable=pv_show,
                       command=_toggle_pv,
                       fg=TEXT_SUB, bg=BG, selectcolor=FRAME_DIM,
                       activebackground=BG, activeforeground=GOLD,
                       font=("Courier", 9)).pack(anchor="w", pady=(0, 10))

        tk.Frame(pv_body, bg=FRAME_DIM, height=1).pack(fill="x", pady=(0, 10))

        pv_status = tk.Label(pv_body, text="", fg=GREEN_LIT, bg=BG,
                             font=("Courier", 9))
        pv_status.pack(anchor="w", pady=(0, 6))

        def _save_pv_key():
            pv_data = load_providers()
            pv_data["picovoice_key"] = pv_key_var.get().strip()
            save_providers(pv_data)
            pv_status.config(text="✓ Picovoice key saved.", fg=GREEN_LIT)

        tk.Button(pv_body, text="SAVE KEY",
                  command=_save_pv_key,
                  bg=FRAME_BLUE, fg=BG,
                  activebackground=FRAME_DIM, activeforeground=GOLD,
                  font=("Courier", 10, "bold"),
                  relief="flat", bd=0, cursor="hand2",
                  padx=16, pady=5).pack(anchor="w")

        tk.Frame(picovoice_frame, bg=FRAME_DIM, height=1).pack(
            fill="x", padx=14, pady=(20, 8))

        tk.Label(picovoice_frame,
                 text="WAKE_MODE=picovoice must be set in .env to use wake word.",
                 fg=TEXT_SUB, bg=BG,
                 font=("Courier", 8)).pack(anchor="w", padx=14)
        tk.Label(picovoice_frame,
                 text="WAKE_MODE=manual or text work without any key.",
                 fg=TEXT_SUB, bg=BG,
                 font=("Courier", 8)).pack(anchor="w", padx=14)

        # Show voice tab by default
        _show_tab("voice")

    # ── Vehicle Config Modal ──────────────────────────────────────────────────
    def show_vehicle_config(self):
        """Open modal popup for vehicle configuration."""
        modal = tk.Toplevel(self)
        modal.title("My Vanagon")
        modal.configure(bg=BG)
        modal.geometry("340x320")
        modal.transient(self)
        modal.grab_set()

        x = (self.winfo_screenwidth()  // 2) - 170
        y = (self.winfo_screenheight() // 2) - 160
        modal.geometry(f"340x320+{x}+{y}")

        # Local vars for this modal — don't commit until SAVE
        local_year   = tk.StringVar(value=self._van_config["year"])
        local_engine = tk.StringVar(value=self._van_config["engine"])
        local_trans  = tk.StringVar(value=self._van_config["trans"])
        local_model  = tk.StringVar(value=self._van_config["model"])

        tk.Frame(modal, bg=RED_ALERT, height=3).pack(fill="x")
        hdr = tk.Frame(modal, bg=BG)
        hdr.pack(fill="x", pady=(6, 0))
        tk.Label(hdr, text="MY VANAGON", fg=GOLD, bg=BG,
                 font=("Courier", 14, "bold")).pack(side="left", padx=12)
        tk.Button(hdr, text="✕ CLOSE", command=modal.destroy,
                  bg=RED_ALERT, fg=RED_BRIGHT,
                  activebackground=RED_BRIGHT, activeforeground=GOLD,
                  font=("Courier", 10, "bold"),
                  relief="flat", bd=0, cursor="hand2",
                  padx=8, pady=3).pack(side="right", padx=12)
        tk.Frame(modal, bg=FRAME_BLUE, height=2).pack(fill="x", pady=(6, 8))

        # Dropdowns
        body = tk.Frame(modal, bg=BG)
        body.pack(fill="x", padx=20)

        for label, var, opts in [
            ("YEAR",         local_year,   YEAR_OPTIONS),
            ("ENGINE",       local_engine, ENGINE_OPTIONS),
            ("TRANSMISSION", local_trans,  TRANS_OPTIONS),
            ("MODEL",        local_model,  MODEL_OPTIONS),
        ]:
            row = tk.Frame(body, bg=BG)
            row.pack(fill="x", pady=4)
            tk.Label(row, text=label, fg=GOLD_DIM, bg=BG,
                     font=("Courier", 10), width=14, anchor="w").pack(side="left")
            menu = tk.OptionMenu(row, var, *opts)
            menu.config(
                bg=FRAME_DIM, fg=TEXT_MAIN,
                activebackground=FRAME_BLUE, activeforeground=GOLD,
                font=("Courier", 10), relief="flat",
                highlightthickness=0, bd=0, width=12,
            )
            menu["menu"].config(
                bg=FRAME_DIM, fg=TEXT_MAIN,
                activebackground=FRAME_BLUE, activeforeground=GOLD,
                font=("Courier", 10)
            )
            menu.pack(side="left")

        tk.Frame(modal, bg=FRAME_DIM, height=1).pack(fill="x", padx=20, pady=(12, 6))

        # Live summary
        summary_lbl = tk.Label(modal, text="", fg=CYAN, bg=BG,
                               font=("Courier", 10))
        summary_lbl.pack()

        def _update_summary(*args):
            summary_lbl.config(
                text=f"{local_year.get()} Vanagon {local_engine.get()} "
                     f"{local_trans.get()} {local_model.get()}"
            )

        for v in (local_year, local_engine, local_trans, local_model):
            v.trace_add("write", _update_summary)
        _update_summary()

        def _save():
            self._van_config = {
                "year":   local_year.get(),
                "engine": local_engine.get(),
                "trans":  local_trans.get(),
                "model":  local_model.get(),
            }
            save_van_config(self._van_config)
            # Update sidebar summary label
            self.van_summary_lbl.config(text=self._van_summary_text())
            modal.destroy()
            self.update_text(
                f"Vehicle updated: {self._van_config['year']} Vanagon "
                f"{self._van_config['engine']} {self._van_config['trans']} "
                f"{self._van_config['model']}"
            )

        tk.Button(modal, text="SAVE & CLOSE",
                  command=_save,
                  bg=FRAME_BLUE, fg=BG,
                  activebackground=FRAME_DIM, activeforeground=GOLD,
                  font=("Courier", 11, "bold"),
                  relief="flat", bd=0, cursor="hand2",
                  padx=20, pady=6).pack(pady=10)

    # ── CPU temperature ───────────────────────────────────────────────────────
    def update_temp(self):
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp = int(f.read().strip()) / 1000
            self.temp_label.config(
                text=f"CPU TEMP: {temp:.1f}°C",
                fg=RED_BRIGHT if temp > 75 else TEXT_SUB
            )
        except (FileNotFoundError, ValueError, OSError) as e:
            self.temp_label.config(text="CPU TEMP: ERR")
            print(f"Temp Monitor Error: {e}")
        self.after(5000, self.update_temp)  # noqa

    # ── Shared audio recording ────────────────────────────────────────────────
    def _record_question(self, recorder):
        """Record 5 seconds of audio, save to wav, return file path."""
        audio_frames = []
        recorder.start()
        for _ in range(0, int(16000 / recorder.frame_length * 5)):
            audio_frames.extend(recorder.read())
        recorder.stop()

        wav_path = "gunter_temp.wav"
        with wave.open(wav_path, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(
                struct.pack("h" * len(audio_frames), *audio_frames))
        return wav_path

    # ── Shared diagnostic handler ─────────────────────────────────────────────
    def _handle_question(self, user_text):
        """Process a transcribed question. Returns False if Gunter should exit."""
        self.update_text(f"You: {user_text}")

        if "exit" in user_text.lower() or "quit" in user_text.lower():
            speak("Verstanden. Closing the shop for today. Auf Wiedersehen!")
            self.after(100, self.destroy)  # type: ignore
            return False

        if "history" in user_text.lower():
            self.show_chat_history()
            return True

        if user_text.strip():
            _ap = get_active_provider()
            _ap_key  = _ap.get("api_key", "").strip()
            _ap_name = _ap.get("name", "")
            if _ap_name == "ollama":
                mode_msg = "Searching the Bentley manuals... Bitte warten."
            elif _ap_key or LLM_MODE == "claude":
                _ap_label = _ap.get("label", "Cloud API")
                mode_msg = f"Consulting {_ap_label}..."
            else:
                mode_msg = "Searching the Bentley manuals... Bitte warten."
            self.update_text(f"Gunter: {mode_msg}")
            self.update()

            answer = ask_gunter(
                user_text,
                history=self.conversation_history,
                van_config=self._van_config
            )
            self.conversation_history.append(
                {"user": user_text, "gunter": answer})

            display_manual(user_text, answer)
            self.update_text(f"Gunter: {answer}")
            speak(answer)
            log_service(user_text, answer)

        return True

    # ── Main logic ────────────────────────────────────────────────────────────
    def run_logic(self):
        cfg = self._van_config
        self.update_text(
            f"Vehicle loaded: {cfg['year']} Vanagon "
            f"{cfg['engine']} {cfg['trans']} {cfg['model']}"
        )

        # ── Text input mode — no microphone or Whisper needed ─────────────────
        if WAKE_MODE == "text":
            speak("Hello, I am Gunter. Type your question and press SEND.")
            time.sleep(2)
            self.update_text(
                "Gunter is standing by... (Type question and press SEND or Enter)"
            )
            self.after(0, self._text_entry.focus_set)
            return   # event-driven from here — no polling loop needed

        # ── Voice modes — load Whisper ────────────────────────────────────────
        self.update_text("Loading Gunter's ears (Whisper)...")
        w_model = whisper_model_global

        TRANSCRIBE_PROMPT = (
            "Oil light, flashing buzzer, Vanagon, "
            "Digifant, alternator, brakes, ECU"
        )

        # ── Picovoice wake word mode ──────────────────────────────────────────
        if WAKE_MODE == "picovoice":
            _pv_key = load_providers().get("picovoice_key", "").strip()
            if not _pv_key:
                self.update_text(
                    "Picovoice Error: No API key set.\n"
                    "Add your key in Settings → Picovoice tab.\n"
                    "Tip: Set WAKE_MODE=manual in .env to run fully offline.")
                return
            try:
                porcupine = pvporcupine.create(
                    access_key=_pv_key,
                    keyword_paths=[
                        f"{WAKE_WORD_PATH}/Hey-Gunter_en_raspberry-pi_v4_0_0.ppn"
                    ]
                )
                recorder = PvRecorder(
                    device_index=MIC_INDEX,
                    frame_length=porcupine.frame_length
                )
            except Exception as e:
                self.update_text(
                    f"Picovoice Error: {e}\n"
                    f"Tip: Set WAKE_MODE=manual in .env to run fully offline.")
                return

            speak("Hello, I am Gunter. Let us look at your Vana-gon today.")
            time.sleep(2)
            self.update_text("Gunter is standing by... (Say 'Hey Gunter')")

            try:
                while True:
                    recorder.start()
                    pcm           = recorder.read()
                    keyword_index = porcupine.process(pcm)

                    if keyword_index >= 0:
                        self.update_text("\n[!] Gunter: Ja? I am listening...")
                        recorder.stop()
                        play_ready_sound()

                        wav_path = self._record_question(recorder)

                        if os.path.exists(wav_path):
                            self.update_text("Gunter: Thinking...")
                            segments, _ = w_model.transcribe(
                                wav_path, beam_size=5,
                                initial_prompt=TRANSCRIBE_PROMPT
                            )
                            user_text = " ".join([s.text for s in segments])
                            del segments
                            gc.collect()

                            if not self._handle_question(user_text):
                                break
                        else:
                            self.update_text(
                                "Error: Gunter didn't catch that audio file.")

                        recorder.start()

            except Exception as e:
                self.update_text(f"Critical System Error: {e}")
            finally:
                if 'recorder' in locals() and recorder is not None:
                    try:
                        recorder.stop()
                        recorder.delete()
                    except Exception:  # noqa
                        pass
                if 'porcupine' in locals() and porcupine is not None:
                    try:
                        porcupine.delete()
                    except Exception:  # noqa
                        pass
                self.update_text("Gunter: Hardware released. Auf Wiedersehen!")

        # ── Manual / offline wake mode ────────────────────────────────────────
        elif WAKE_MODE == "manual":
            try:
                recorder = PvRecorder(device_index=MIC_INDEX, frame_length=512)
            except Exception as e:
                self.update_text(f"Microphone Error: {e}")
                return

            speak("Hello, I am Gunter. Press LISTEN and ask your question.")
            time.sleep(2)
            self.update_text(
                "Gunter is standing by... (Press LISTEN to speak)")

            try:
                while True:
                    self._manual_listen_event.wait()
                    self._manual_listen_event.clear()

                    play_ready_sound()
                    wav_path = self._record_question(recorder)

                    if os.path.exists(wav_path):
                        self.update_text("Gunter: Thinking...")
                        segments, _ = w_model.transcribe(
                            wav_path, beam_size=5,
                            initial_prompt=TRANSCRIBE_PROMPT
                        )
                        user_text = " ".join([s.text for s in segments])
                        del segments
                        gc.collect()

                        if not self._handle_question(user_text):
                            break
                    else:
                        self.update_text(
                            "Error: Gunter didn't catch that audio file.")

            except Exception as e:
                self.update_text(f"Critical System Error: {e}")
            finally:
                if 'recorder' in locals() and recorder is not None:
                    try:
                        recorder.stop()
                        recorder.delete()
                    except Exception:  # noqa
                        pass
                self.update_text("Gunter: Hardware released. Auf Wiedersehen!")


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = GunterGUI()
    app.mainloop()


# ── Record audio utility ──────────────────────────────────────────────────────
def record_audio(filename="input.wav", duration=5):
    chunk         = 1024
    sample_format = pyaudio.paInt16
    channels      = 1
    fs            = 44100

    p = pyaudio.PyAudio()
    print("Gunter is listening...")

    stream = p.open(
        format=sample_format,
        channels=channels,
        rate=fs,
        frames_per_buffer=chunk,
        input_device_index=2,
        input=True
    )

    frames = []
    for _ in range(0, int(fs / chunk * duration)):
        data = stream.read(chunk)
        frames.append(data)

    stream.stop_stream()
    stream.close()
    p.terminate()

    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(p.get_sample_size(sample_format))
        wf.setframerate(fs)
        wf.writeframes(b''.join(frames))

    print("Finished recording.")
# End Gunter AI (v2.0)
