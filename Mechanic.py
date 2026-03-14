import gc
import os
import shlex
import struct
import subprocess
import time
import datetime
import wave
import pvporcupine
import pyaudio
import requests
import customtkinter as ctk
import threading
from dotenv import load_dotenv

load_dotenv()
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_classic.chains import create_retrieval_chain
from faster_whisper import WhisperModel
from pvrecorder import PvRecorder
from PIL import Image

# Initialize the "Brain" once at the start
embeddings = OllamaEmbeddings(model="mxbai-embed-large")
vectorstore = Chroma(persist_directory="./vanagon_local_db", embedding_function=embeddings)
retriever = vectorstore.as_retriever(search_kwargs={"k": 2})


def log_service(question, answer):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"\n{'=' * 50}\nDATE: {timestamp}\nISSUE: {question}\nGUNTER: {answer}\n"
    with open("service_history.txt", "a") as f:
        f.write(entry)


def play_ready_sound():
    # A quick, non-blocking sound to let you know he's listening
    subprocess.Popen(["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet",
                      "/home/pi/PyCharmMiscProject/PythonAIAgent/ding.wav"])


def display_manual(topic):
    # Paths to your files
    digifant_path = "/home/pi/PyCharmMiscProject/PythonAIAgent/Manuals/digifant_pro.pdf"
    bentley_path = "/home/pi/PyCharmMiscProject/PythonAIAgent/Manuals/bentley_main.pdf"
    manual_path = None
    page = 1
    t_lower = topic.lower() # Clean up the code by making it lowercase once

    # 1. Digifant Logic
    if any(k in t_lower for k in ["ecu", "idle", "throttle", "afm", "digifant", "hall"]):
        manual_path = digifant_path
        if "idle" in t_lower or "surge" in t_lower:
            page = 16
        elif "throttle" in t_lower:
            page = 20
        elif "afm" in t_lower:
            page = 11

    # 2. Wiring Logic (Standalone so it always works)
    elif any(k in t_lower for k in ["wiring", "diagram", "electrical", "schematic"]):
        manual_path = bentley_path
        if "water-cooled" in t_lower or "91" in t_lower:
            page = 474 # Your 1991 Index
        else:
            page = 549 # General Electrical

    # 3. General Mechanical (Fixed the comma!)
    elif any(k in t_lower for k in ["doityourself", "brake", "oil", "coolant", "fuse"]):
        manual_path = bentley_path
        if "doityourself" in t_lower:
            page = 465
        elif "brake" in t_lower:
            page = 400
        elif "oil" in t_lower:
            page = 120

    if manual_path:
        try:
            subprocess.run(["pkill", "evince"])
            print(f"[!] Gunter is opening {manual_path} to page {page}...")
            # We use list format for Popen to be safer
            subprocess.Popen(["evince", f"--page-label={page}", manual_path])
        except Exception as e:
            print(f"Error opening PDF: {e}")


def ask_llama(question):
    # 1. Fetch relevant technical data from your thesamba.com/Bentley vectorstore
    docs = retriever.invoke(question)
    context = "\n".join([doc.page_content for doc in docs])

    url = "http://localhost:11434/api/generate"

    # 2. Refined Persona: Confidence is key for a master mechanic
    full_prompt = f"""
    SYSTEM: You are Gunter, a master VW mechanic specialized in 1980-1991 Vanagons. 
    You have full digital access to the Bentley Manual and Digifant Training Manual.
    NEVER apologize for not having a physical copy.
    If you see technical data in the CONTEXT below, use it as if it's from your own memory.
    Keep your tone professional, and helpful. 
    If a term seems wrong (like 'oral light'), assume they mean 'oil light' but ask for clarification.

    CONTEXT: {context}

    USER: {question}
    GUNTER:"""

    payload = {
        "model": "llama3.2:3b",
        "prompt": full_prompt,
        "stream": False,
        "options": {
            "num_predict": 150,  # Increased slightly for more detailed diagnostic steps
            "num_ctx": 2048,     # Increased to handle the context and persona better
            "temperature": 0.2   # A tiny bit of personality, but still very focused
        }
    }

    try:
        response = requests.post(url, json=payload, timeout=120)
        return response.json().get('response', "The Bentley is greasy and I cannot read it.")
    except Exception as e:
        return f"Ach! My brain is stalled: {e}"

# --- Configuration ---
PICOVOICE_API_KEY = os.getenv("PICOVOICE_API_KEY")

# /home/pi/PyCharmMiscProject/PythonAIAgent/.venv/bin/python /home/pi/PyCharmMiscProject/PythonAIAgent/Check-01.py
# Index 0: Lenovo EasyCamera Digital Stereo (IEC958)
# Index 1: Monitor of SoundCore 2
MIC_INDEX = 0
MODEL_SIZE = "base.en"


def speak(text):
    # Dictionary to help the German voice pronounce English VW terms
    corrections = {
        "Vanagon": "Vana-gon",
        "Aircooled": "Air-koold",
        "Bus": "Buss",
        "Engine": "En-jin",
        "Ollama": "O-llama",
        "ECU": "E--C--U"
    }

    for word, replacement in corrections.items():
        text = text.replace(word, replacement)

    # Safely escape the text for the Linux shell
    safe_text = shlex.quote(text)

    piper_cmd = "/home/pi/PyCharmMiscProject/PythonAIAgent/piper/piper"
    model_path = "/home/pi/PyCharmMiscProject/PythonAIAgent/de_DE-thorsten-medium.onnx"

    # Remove the double quotes around {text} since shlex.quote adds them
    command = f'echo {safe_text} | {piper_cmd} --model {model_path} --output_raw - | ffplay -f s16le -ar 22050 -ac 1 -nodisp -autoexit -loglevel error -'

    print(f"Gunter: {text}")
    subprocess.run(command, shell=True)

# 'tiny.en' is 3x faster than 'base.en' and much safer for the Pi 5's RAM
# 'base.en' is more accurate but uses more resources. You can experiment with 'small.en' as a middle ground.

model_size = "base.en"

# Added 'local_files_only' to skip the login/update check at startup
model = WhisperModel(
    model_size,
    device="cpu",
    compute_type="int8",
    local_files_only=True # Set to True once the model is downloaded
)

def listen():
    # In a full setup, you'd use pyaudio to record a '.wav' file here
    segments, info = model.transcribe("input.wav", beam_size=5, initial_prompt="Oil, Vanagon, Digifant, mechanic, engine, flashing light")
    text = " ".join([segment.text for segment in segments])
    return text


# Set the look and feel
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class GunterGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window Setup for 9" Touchscreen
        self.title("Gunter AI - Vanagon Diagnostic Command")
        self.geometry("800x480")  # Standard 7-9" Pi screen res

        # Create Layout (Grid)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar for Buttons
        self.sidebar = ctk.CTkFrame(self, width=140, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        # --- ADDING THE WOLFSBURG EMBLEM ---
        # 1. Provide the absolute path to your logo image file (e.g., download a clean vintage VW logo and save it as vw_logo.png in the same directory)
        image_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "vw_logo.png")

        # 2. Use Pillow to load and prepare the image (setting it for both light/dark mode)
        # 80x80 is a good size to fit in the 140 width sidebar
        self.vw_logo_image = ctk.CTkImage(light_image=Image.open(image_path),
                                          dark_image=Image.open(image_path),
                                          size=(80, 80))

        # 3. Create a label to hold the image
        self.image_label = ctk.CTkLabel(self.sidebar, text="", image=self.vw_logo_image)
        # Add significant padding at the top to place it as the first item
        self.image_label.grid(row=0, column=0, padx=20, pady=(30, 0))

        # --- EXISTING LABEL (Shift this down one row!) ---
        # Use row=1 and set smaller pady since the logo is above it
        self.logo_label = ctk.CTkLabel(self.sidebar, text="GUNTER v1.0", font=ctk.CTkFont(size=18, weight="bold"))
        self.logo_label.grid(row=1, column=0, padx=20, pady=(10, 20))

        # Shift all your other buttons (Open Bentley, History, Exit, Temp) down one row too!

        # Manual Bentley Button
        self.manual_btn = ctk.CTkButton(self.sidebar, text="OPEN BENTLEY",
                                        fg_color="#004B8D",  # VW Blue
                                        command=self.open_bentley_manual)
        self.manual_btn.grid(row=2, column=0, padx=20, pady=(20, 10))

        # Shift the logo/label up or down as needed to make room

        self.hist_btn = ctk.CTkButton(self.sidebar, text="HISTORY", command=self.show_history)
        self.hist_btn.grid(row=3, column=0, padx=20, pady=10)

        self.exit_btn = ctk.CTkButton(self.sidebar, text="EXIT SHOP", fg_color="red", command=self.quit_gunter)
        self.exit_btn.grid(row=4, column=0, padx=20, pady=10)

        # --- ADD THIS: Temperature Label ---
        self.temp_label = ctk.CTkLabel(self.sidebar, text="CPU TEMP: --°C", font=ctk.CTkFont(size=12))
        self.temp_label.grid(row=5, column=0, padx=20, pady=(100, 10))  # pady adds space above it

        # --- ADD THIS: Start the update loop ---
        self.update_temp()

        # Main Chat Window
        self.textbox = ctk.CTkTextbox(self, width=600, font=("Inter", 16))
        self.textbox.grid(row=0, column=1, padx=(20, 20), pady=(20, 20), sticky="nsew")
        self.textbox.insert("0.0", "Gunter: Standing by... Say 'Hey Gunter'\n\n")

        # Start Gunter's Logic in a background thread
        self.logic_thread = threading.Thread(target=self.run_logic, daemon=True)
        self.logic_thread.start()

        # Force Fullscreen / Kiosk Mode

        # 1. Start the window in normal mode first to let the OS "register" it
        self.update_idletasks()

        # 2. Engage Fullscreen
        self.attributes("-fullscreen", True)

        # 3. CRITICAL: Lift Gunter to the top and force the OS to give him the mouse/touch
        self.lift()
        self.attributes("-topmost", True)
        self.focus_force()

        # 4. Bind the Escape key
        self.bind("<Escape>", lambda event: self.attributes("-fullscreen", False))


    def update_text(self, text):
        # Thread-safe way to add text to the window
        self.textbox.insert("end", text + "\n")
        self.textbox.see("end")

    def open_bentley_manual(self):
        bentley_path = "/home/pi/PyCharmMiscProject/PythonAIAgent/Manuals/bentley_main.pdf"
        self.update_text("Gunter: Opening the full Bentley for you, Hans.")
        subprocess.run(["pkill", "evince"])  # Clear old windows
        subprocess.Popen(["evince", bentley_path])

    def show_history(self):
        self.update_text("\n--- DISPLAYING SERVICE LOG ---")
        try:
            with open("service_history.txt", "r") as f:
                self.update_text(f.read())
        except FileNotFoundError:
            self.update_text("Gunter: 'No records found. Are you even maintaining this bus?'")
        except Exception as e:
            self.update_text(f"Gunter: 'Ach! I cannot read the logbook: {e}'")

    def quit_gunter(self):
        # Using 'self' here silences the PyCharm "static" warning
        self.update_text("Gunter: shutting down systems... Gute Fahrt!")
        print("Gunter: Emergency Shutdown... Auf Wiedersehen!")

        # Give the GUI a millisecond to show the text before killing the process
        self.after(500, os._exit, 0)

    def update_temp(self):
        try:
            # Read the Pi's internal thermal file
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp_raw = f.read().strip()
                temp = int(temp_raw) / 1000

            self.temp_label.configure(text=f"CPU TEMP: {temp:.1f}°C")

            # Thermal logic for the dash
            if temp > 75:
                self.temp_label.configure(text_color="red")
            else:
                self.temp_label.configure(text_color="gray")

        except (FileNotFoundError, ValueError, OSError) as e:
            # Specific exceptions satisfy PyCharm's 'broad' warning
            self.temp_label.configure(text="CPU TEMP: ERR")
            print(f"Temp Monitor Error: {e}")

        # Schedule next update
        self.after(5000, self.update_temp) # noqa

    def run_logic(self):
        # 1. Initialize Whisper
        self.update_text("Loading Gunter's ears (Whisper)...")
        whisper_model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8", local_files_only=True)

        # 2. Initialize Picovoice
        try:
            porcupine = pvporcupine.create(
                access_key=PICOVOICE_API_KEY,
                keyword_paths=['/home/pi/PyCharmMiscProject/PythonAIAgent/Hey-Gunter_en_raspberry-pi_v4_0_0.ppn']
            )
            recorder = PvRecorder(device_index=MIC_INDEX, frame_length=porcupine.frame_length)

        except Exception as e:
            self.update_text(f"Hardware Error: {e}")
            return

        # 3. Gunter's Introduction
        speak("Hello, I am Gunter. Let us look at your Vana-gon today.")
        time.sleep(2)
        self.update_text("Gunter is standing by... (Try saying 'Hey Gunter')")

        # 4. NOW start the while loop
        try:
            while True:
                # 1. Listen for the Wake Word
                # Note: Assuming recorder and porcupine are initialized before this loop
                recorder.start()
                pcm = recorder.read()
                keyword_index = porcupine.process(pcm)

                if keyword_index >= 0:
                    self.update_text("\n[!] Gunter: Ja? I am listening...")
                    recorder.stop()

                    # Play the "Ding" sound
                    play_ready_sound()

                    # Record 5 seconds for the question
                    audio_frames = []
                    recorder.start()
                    for _ in range(0, int(16000 / recorder.frame_length * 5)):
                        audio_frames.extend(recorder.read())
                    recorder.stop()

                    # Save the frames
                    with wave.open("gunter_temp.wav", 'wb') as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2)
                        wf.setframerate(16000)
                        wf.writeframes(struct.pack("h" * len(audio_frames), *audio_frames))

                    if os.path.exists("gunter_temp.wav"):
                        self.update_text("Gunter: Thinking...")

                        segments, _ = whisper_model.transcribe(
                            "gunter_temp.wav",
                            beam_size=5,
                            initial_prompt="Oil light, flashing buzzer, Vanagon, Digifant, alternator, brakes, ECU"
                        )
                        user_text = " ".join([segment.text for segment in segments])
                        self.update_text(f"You: {user_text}")

                        # Check for Exit
                        if "exit" in user_text.lower() or "quit" in user_text.lower():
                            speak("Verstanden. Closing the shop for today. Auf Wiedersehen!")
                            # This tells Gunter to wait 100ms then close the window
                            self.after(100, self.destroy) # type: ignore
                            break

                        # Check for History Recall (Directly uses the GUI method)
                        if "history" in user_text.lower():
                            self.show_history()
                            continue

                        # Regular Diagnostic Logic
                        del segments
                        gc.collect()

                        if user_text.strip():
                            self.update_text("Gunter: Searching the Bentley manuals... Bitte warten.")
                            self.update()  # This forces the GUI to refresh the text immediately
                            answer = ask_llama(user_text)

                            # Show manual, print text to GUI, then speak
                            display_manual(user_text)
                            self.update_text(f"Gunter: {answer}")
                            speak(answer)
                            log_service(user_text, answer)
                    else:
                        self.update_text("Error: Gunter didn't catch that audio file.")

                    # Restart for the next wake word
                    recorder.start()

        except Exception as e:
            self.update_text(f"Critical System Error: {e}")

        finally:
            # 1. Stop and delete the recorder safely
            if 'recorder' in locals() and recorder is not None:
                try:
                    recorder.stop()
                    recorder.delete()
                except Exception:  # noqa
                    pass

            # 2. Delete the porcupine engine safely
            if 'porcupine' in locals() and porcupine is not None:
                try:
                    porcupine.delete()
                except Exception:  # noqa
                    pass

            self.update_text("Gunter: Hardware released. Auf Wiedersehen!")
# --- BOTTOM OF FILE ---
if __name__ == "__main__":
    app = GunterGUI()
    app.mainloop()


def record_audio(filename="input.wav", duration=5):
    chunk = 1024
    sample_format = pyaudio.paInt16
    channels = 1
    fs = 44100

    p = pyaudio.PyAudio()

    print("Gunter is listening...")

    # We use input_device_index=2 because your arecord showed Card 2
    stream = p.open(format=sample_format,
                    channels=channels,
                    rate=fs,
                    frames_per_buffer=chunk,
                    input_device_index=2,
                    input=True)

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
#End Gunter AI (v0.2) chatbot

