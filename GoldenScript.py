import os
import subprocess
import requests
import pvporcupine
from dotenv import load_dotenv

load_dotenv()
from pvrecorder import PvRecorder
from faster_whisper import WhisperModel

# --- 1. CONFIGURATION ---
PICOVOICE_API_KEY = os.getenv("PICOVOICE_API_KEY")
WAKE_WORD_PATH = "/home/pi/PyCharmMiscProject/PythonAIAgent/Hey-Gunter_en_raspberry-pi_v4_0_0.ppn"
PIPER_CMD = "/home/pi/PyCharmMiscProject/PythonAIAgent/piper/piper"
PIPER_MODEL = "/home/pi/PyCharmMiscProject/PythonAIAgent/de_DE-thorsten-medium.onnx"
MIC_INDEX = 0  # Your Lenovo Camera Index


# --- 2. THE BRAIN (Ollama) ---
def ask_ollama(question):
    url = "http://localhost:11434/api/generate"
    prompt = f"You are Gunter, a master VW mechanic. Answer this briefly and technically: {question}"
    payload = {"model": "llama3.2:3b", "prompt": prompt, "stream": False}
    try:
        response = requests.post(url, json=payload, timeout=30)
        return response.json().get('response', "I cannot hear you over the engine.")
    except Exception as e:
        return f"Ach! Connection error: {e}"


# --- 3. THE VOICE (Piper + ffplay for Bluetooth) ---
def speak(text):
    # Phonetic corrections for the German voice model
    corrections = {"Vanagon": "Vana-gon", "Engine": "En-jin", "Ollama": "O-llama"}
    for word, replacement in corrections.items():
        text = text.replace(word, replacement)

    print(f"Gunter: {text}")
    # Using ffplay for reliable Bluetooth routing on Pi 5
    command = f'echo "{text}" | {PIPER_CMD} --model {PIPER_MODEL} --output_raw - | ffplay -f s16le -ar 22050 -ac 1 -nodisp -autoexit -'
    subprocess.run(command, shell=True)


# --- 4. THE MAIN LOOP ---
def run_gunter():
    print("Loading Gunters's ears (Whisper Base)...")
    whisper_model = WhisperModel("base.en", device="cpu", compute_type="int8")

    porcupine = pvporcupine.create(access_key=PICOVOICE_API_KEY, keyword_paths=[WAKE_WORD_PATH])
    recorder = PvRecorder(device_index=MIC_INDEX, frame_length=porcupine.frame_length)

    print("\n--- GUNTER IS ONLINE (1980-1991 Vanagon Specialist) ---")

    try:
        while True:
            recorder.start()
            pcm = recorder.read()

            if porcupine.process(pcm) >= 0:
                print("\n[!] Gunter: Ja? I am listening...")
                recorder.stop()  # Release mic for arecord

                # Record question (5 seconds)
                os.system(f"arecord -D hw:{MIC_INDEX},0 -d 5 -f cd gunter_temp.wav")

                if os.path.exists("gunter_temp.wav"):
                    segments, _ = whisper_model.transcribe("gunter_temp.wav", beam_size=5)
                    user_text = " ".join([segment.text for segment in segments])
                    print(f"You: {user_text}")

                    if user_text.strip():
                        answer = ask_ollama(user_text)
                        speak(answer)

                recorder.start()  # Resume listening for wake word

    except KeyboardInterrupt:
        print("\nClosing the shop. Auf Wiedersehen!")
    finally:
        recorder.delete()
        porcupine.delete()


if __name__ == "__main__":
    run_gunter()