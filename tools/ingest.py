# ingest.py — Load OCR'd Bentley and Digifant manuals into Chroma vectorstore
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

MANUALS = [
    "/home/shogun/PyCharmMiscProject/PythonAIAgent/Manuals/bentley_ocr.pdf",
    "/home/shogun/PyCharmMiscProject/PythonAIAgent/Manuals/digifant_pro_ocr.pdf",
]

DB_PATH = "/home/shogun/PyCharmMiscProject/PythonAIAgent/vanagon_local_db"

print("Loading OCR'd PDFs...")
docs = []
for path in MANUALS:
    print(f"  Reading {path}...")
    loader = PyPDFLoader(path)
    pages  = loader.load()
    docs.extend(pages)
    print(f"  → {len(pages)} pages loaded")

print(f"\nTotal pages: {len(docs)}")

print("\nSplitting into chunks...")
splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50
)
chunks = splitter.split_documents(docs)
print(f"Total chunks to embed: {len(chunks)}")

print("\nEmbedding and storing in Chroma...")
print("(This will take several hours on Pi 5 - safe to leave running overnight)\n")

embeddings = OllamaEmbeddings(model="mxbai-embed-large")

# Process in batches so progress is visible and resumable
BATCH_SIZE = 50
for i in range(0, len(chunks), BATCH_SIZE):
    batch = chunks[i:i + BATCH_SIZE]
    if i == 0:
        # First batch creates the DB
        db = Chroma.from_documents(
            batch,
            embeddings,
            persist_directory=DB_PATH
        )
    else:
        # Subsequent batches add to it
        db.add_documents(batch)

    pct = min(100, int((i + BATCH_SIZE) / len(chunks) * 100))
    print(f"  Progress: {min(i + BATCH_SIZE, len(chunks))}/{len(chunks)} chunks ({pct}%)")

print(f"\nDone! Final chunk count: {len(db.get()['ids'])}")
print("Gunter's brain is loaded. Viel Erfolg!")