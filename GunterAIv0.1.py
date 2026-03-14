import gc
import os
import shlex
import struct
import subprocess
import time
import wave

import pvporcupine
import pyaudio
import requests
from dotenv import load_dotenv

load_dotenv()
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_classic.chains import create_retrieval_chain
from faster_whisper import WhisperModel
from pvrecorder import PvRecorder

# This is code used to build version 0.1 of GunterAI it needs some more
# langchain imports (community) to function, but it is close.

# # Begin GunterAI (v0.1) text only
# def log_service(question, answer):
#     timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#     entry = f"\n{'=' * 50}\nDATE: {timestamp}\nISSUE: {question}\nGUNTER: {answer}\n"
#     with open("service_history.txt", "a") as f:
#         f.write(entry)
#
#
# def start_gunter_ai():
#     # 1. Setup the Brain & Index with memory-efficient settings
#     embeddings = OllamaEmbeddings(model="mxbai-embed-large")
#     vectorstore = Chroma(persist_directory="./vanagon_local_db", embedding_function=embeddings)
#
#     # We set num_ctx to 2048 to save RAM
#     llm = ChatOllama(model="llama3.2:3b", temperature=0.1, num_ctx=4096)
#
#     # 2. Gunter's Specialist Persona
#     system_prompt = (
#         "You are Gunter, a master VW mechanic for 1980-1991 Vanagons. "
#         "Keep it brief and technical. If the user mentions a flashing temp light, "
#         "remind them to check the coolant level sensor and the relay behind the dash."
#         "\n\nContext: {context}"
#     )
#
#     prompt = ChatPromptTemplate.from_messages([
#         ("system", system_prompt),
#         MessagesPlaceholder(variable_name="chat_history"),
#         ("human", "{input}"),
#     ])
#
#     # 3. Create the Chain
#     doc_chain = create_stuff_documents_chain(llm, prompt)
#     rag_chain = create_retrieval_chain(vectorstore.as_retriever(search_kwargs={"k": 2}), doc_chain)
#
#     # 4. Chat Loop
#     chat_history = []
#     print("\n--- GUNTER'S GARAGE (1980-1991 Vanagon Specialist) ---")
#     print("Gunter: 'Ja? What is wrong with the bus now?'")
#
#     while True:
#         user_input = input("\nYou: ").strip()
#
#         # --- PASTE THE HISTORY LOGIC HERE ---
#         if user_input.lower() == "history":
#             if os.path.exists("service_history.txt"):
#                 print("\n" + "=" * 20 + " GUNTER'S SERVICE LOG " + "=" * 20)
#                 with open("service_history.txt", "r") as f:
#                     print(f.read())
#                 print("=" * 62)
#             else:
#                 print("\nGunter: 'No records found. Are you even maintaining this bus?'")
#             continue  # This jumps back to the start of the loop
#         # ------------------------------------
#
#         if user_input.lower() in ["quit", "exit", "q"]:
#             break
#
#         print("Gunter is reading the Bentley...")
#         # ... (rest of your rag_chain.invoke code)
#
#         try:
#             result = rag_chain.invoke({"input": user_input, "chat_history": chat_history})
#             answer = result['answer']
#             print(f"\nGunter: {answer}")
#             log_service(user_input, answer)
#             chat_history.extend([("human", user_input), ("ai", answer)])
#         except Exception as e:
#             print(f"Gunter: 'Gah! The Pi is overheating or out of memory! Error: {e}'")
#
#
# if __name__ == "__main__":
#     start_gunter_ai()