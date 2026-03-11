import sys
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_community.vectorstores import Chroma
from langchain_classic.chains import ConversationalRetrievalChain
from langchain_classic.memory import ConversationBufferMemory


def start_garage_chat():
    # 1. Load the existing "Brain" (The index you created in the last step)
    embeddings = OllamaEmbeddings(model="mxbai-embed-large")
    vectorstore = Chroma(
        persist_directory="./vanagon_local_db",
        embedding_function=embeddings
    )

    # 2. Setup the "Brain" (Llama 3.1)
    llm = ChatOllama(model="llama3.1:8b", temperature=0.2)

    # 3. Setup Memory
    # This stores the back-and-forth in RAM while the script is running
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True
    )

    # 4. Create the Conversational Chain
    qa_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vectorstore.as_retriever(search_kwargs={"k": 3}),
        memory=memory
    )

    print("\n=== Vanagon Mechanic AI Active ===")
    print("(Type 'exit' to quit or 'clear' to reset memory)\n")

    # 5. The Chat Loop
    while True:
        user_input = input("You: ").strip()

        if user_input.lower() in ['exit', 'quit']:
            print("Mechanic: Good luck with the repair! Closing shop.")
            break

        if user_input.lower() == 'clear':
            memory.clear()
            print("Mechanic: Memory cleared. What's the new issue?")
            continue

        if not user_input:
            continue

        print("Mechanic is thinking...", end="\r")

        # Get response
        result = qa_chain.invoke({"question": user_input})

        print(f"Mechanic: {result['answer']}\n")


if __name__ == "__main__":
    start_garage_chat()