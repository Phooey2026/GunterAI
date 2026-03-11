import os
import datetime
import subprocess
import pyaudio
import wave
import requests
import pvporcupine
from dotenv import load_dotenv

load_dotenv()
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from faster_whisper import WhisperModel
from pvrecorder import PvRecorder

def ask_llama(question):
    # This assumes Ollama is running locally on your Pi 5
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": "llama3.2:3b",
        "prompt": f"You are Gunter, a master VW mechanic. Answer this briefly: {question}",
        "stream": False
    }
    response = requests.post(url, json=payload)
    return response.json().get('response', "I am sorry, I cannot hear you over the engine noise.")

# --- Configuration ---
PICOVOICE_API_KEY = os.getenv("PICOVOICE_API_KEY")
# Index 2 matches your Lenovo EasyCamera from 'arecord -l'
MIC_INDEX = 2
MODEL_SIZE = "base.en"

# Initialize Whisper
print("Loading Gunter's ears (Whisper)...")
whisper_model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8",local_files_only=True) # This stops the HF Hub authentication check


def speak(text):
    # Dictionary to help the German voice pronounce English VW terms
    corrections = {
        "Vanagon": "Vana-gon",
        "Aircooled": "Air-koold",
        "Bus": "Buss",
        "Engine": "En-jin",
        "Ollama": "O-llama"
    }

    for word, replacement in corrections.items():
        text = text.replace(word, replacement)

    piper_cmd = "/home/pi/PyCharmMiscProject/PythonAIAgent/piper/piper"
    model_path = "/home/pi/PyCharmMiscProject/PythonAIAgent/de_DE-thorsten-medium.onnx"

    # Using the raw output for the Bluetooth speaker
    command = f'echo "{text}" | {piper_cmd} --model {model_path} --output_raw - | ffplay -f s16le -ar 22050 -ac 1 -nodisp -autoexit -'

    print(f"Gunter: {text}")
    subprocess.run(command, shell=True)

# Example call
speak("Hello, I am Gunter. Let us look at your Vanagon today.")

# 'tiny.en' is 3x faster than 'base.en' and much safer for the Pi 5's RAM
# 'base.en' is more accurate but uses more resources. You can experiment with 'small.en' as a middle ground.

model_size = "base.en"

# Added 'local_files_only' to skip the login/update check at startup
model = WhisperModel(
    model_size,
    device="cpu",
    compute_type="int8",
    local_files_only=False # Set to True once the model is downloaded
)

def listen():
    # In a full setup, you'd use pyaudio to record a '.wav' file here
    segments, info = model.transcribe("input.wav", beam_size=5)
    text = " ".join([segment.text for segment in segments])
    return text

def run_gunter():
    # Load the Porcupine engine for "Hey Gunter"
    # Note: 'porcupine' is a built-in keyword; for a custom 'Gunter' word,
    # you can generate a .ppn file on Picovoice Console.
    # Make sure the path is inside a list [ ]
    # and assigned to 'keyword_paths'
    porcupine = pvporcupine.create(
        access_key=PICOVOICE_API_KEY,
        keyword_paths=['/home/pi/PyCharmMiscProject/PythonAIAgent/Hey-Gunter_en_raspberry-pi_v4_0_0.ppn']
    )

    # Initialize recorder with your Lenovo Camera mic
    recorder = PvRecorder(device_index=MIC_INDEX, frame_length=porcupine.frame_length)

    print(f"Gunter is standing by... (Try saying 'Hey Gunter')")

    try:
        while True:
            recorder.start()
            pcm = recorder.read()

            # 1. Listen for the Wake Word
            keyword_index = porcupine.process(pcm)

            if porcupine.process(pcm) >= 0:
                print("\n[!] Gunter: Ja? I am listening...")

                # IMPORTANT: Stop PvRecorder so it releases the mic for arecord
                recorder.stop()

                # Use -D hw:2,0 to be precise, matching your Lenovo camera card
                # We also added a small delay to let the hardware 'reset'
                os.system(f"arecord -D hw:2,0 -d 5 -f cd gunter_temp.wav")

                # Verify the file was actually created before Whisper tries to read it
                if os.path.exists("gunter_temp.wav"):
                    print("Gunter is thinking...")
                    segments, _ = whisper_model.transcribe("gunter_temp.wav", beam_size=5)
                    user_text = " ".join([segment.text for segment in segments])

                    print(f"---> YOU SAID: {user_text}")

                    if user_text.strip():
                        answer = ask_llama(user_text)
                        speak(answer)
                else:
                    print("Error: Gunter didn't catch that audio file.")

                # Restart the wake-word listener
                recorder.start()

                # This is where you will eventually call your Llama 3.1 model!

    except KeyboardInterrupt:
        print("\nStopping Gunter...")
    finally:
        recorder.delete()
        porcupine.delete()


if __name__ == "__main__":
    run_gunter()

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


def log_service(question, answer):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"\n{'=' * 50}\nDATE: {timestamp}\nISSUE: {question}\nGUNTER: {answer}\n"
    with open("service_history.txt", "a") as f:
        f.write(entry)


def start_gunter_ai():
    # 1. Setup the Brain & Index with memory-efficient settings
    embeddings = OllamaEmbeddings(model="mxbai-embed-large")
    vectorstore = Chroma(persist_directory="./vanagon_local_db", embedding_function=embeddings)

    # We set num_ctx to 2048 to save RAM
    llm = ChatOllama(model="llama3.2:3b", temperature=0.1, num_ctx=4096)

    # 2. Gunter's Specialist Persona
    system_prompt = (
        "You are Gunter, a master VW mechanic for 1980-1991 Vanagons. "
        "Keep it brief and technical. If the user mentions a flashing temp light, "
        "remind them to check the coolant level sensor and the relay behind the dash."
        "\n\nContext: {context}"
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
    ])

    # 3. Create the Chain
    doc_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(vectorstore.as_retriever(search_kwargs={"k": 2}), doc_chain)

    # 4. Chat Loop
    chat_history = []
    print("\n--- GUNTER'S GARAGE (1980-1991 Vanagon Specialist) ---")
    print("Gunter: 'Ja? What is wrong with the bus now?'")

    while True:
        user_input = input("\nYou: ").strip()

        # --- PASTE THE HISTORY LOGIC HERE ---
        if user_input.lower() == "history":
            if os.path.exists("service_history.txt"):
                print("\n" + "=" * 20 + " GUNTER'S SERVICE LOG " + "=" * 20)
                with open("service_history.txt", "r") as f:
                    print(f.read())
                print("=" * 62)
            else:
                print("\nGunter: 'No records found. Are you even maintaining this bus?'")
            continue  # This jumps back to the start of the loop
        # ------------------------------------

        if user_input.lower() in ["quit", "exit", "q"]:
            break

        print("Gunter is reading the Bentley...")
        # ... (rest of your rag_chain.invoke code)

        try:
            result = rag_chain.invoke({"input": user_input, "chat_history": chat_history})
            answer = result['answer']
            print(f"\nGunter: {answer}")
            log_service(user_input, answer)
            chat_history.extend([("human", user_input), ("ai", answer)])
        except Exception as e:
            print(f"Gunter: 'Gah! The Pi is overheating or out of memory! Error: {e}'")


if __name__ == "__main__":
    start_gunter_ai()