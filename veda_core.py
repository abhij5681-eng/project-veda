import os
import fitz  # PyMuPDF
from dotenv import load_dotenv
from google import genai
import chromadb
from chromadb.utils import embedding_functions

# 1. Setup Environment and API Configuration
load_dotenv()
client = genai.Client()

# 2. Setup Local Vector Database
# This creates a folder named 'veda_memory' in your project directory to store data persistently
chroma_client = chromadb.PersistentClient(path="./veda_memory")

# CORRECT (Using the newest embedding model)
gemini_ef = embedding_functions.GoogleGenaiEmbeddingFunction(
    model_name="gemini-embedding-001"
)

# Create or get an existing collection (think of it like a database table for your class)
collection = chroma_client.get_or_create_collection(
    name="class_materials", 
    embedding_function=gemini_ef
)

def process_and_store_pdf(pdf_path):
    """Extracts text from PDF, splits it into digestible chunks, and saves to ChromaDB."""
    print(f"📄 Extracting text from {pdf_path}...")
    
    # Extract full text
    full_text = ""
    with fitz.open(pdf_path) as doc:
        for page in doc:
            full_text += page.get_text()
            
    # Chunking: Split text into blocks of ~1000 characters with a 200 character overlap
    print("🧠 Slicing document into memory chunks...")
    chunk_size = 1000
    overlap = 200
    chunks = []
    
    start = 0
    while start < len(full_text):
        end = start + chunk_size
        chunks.append(full_text[start:end])
        start += (chunk_size - overlap)
        
    # Prepare data for ChromaDB
    documents = chunks
    ids = [f"chunk_{i}" for i in range(len(chunks))]
    metadatas = [{"source": os.path.basename(pdf_path)} for _ in range(len(chunks))]
    
    # Save into our database
    print(f"💾 Saving {len(chunks)} chunks into Project Veda's long-term memory...")
    collection.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas
    )
    print("✅ Document successfully indexed!")

def ask_veda(question):
    """Queries the vector database for relevant text and generates an answer using Gemini."""
    print(f"\n🔍 Searching memory for: '{question}'")
    
    # Query ChromaDB for the top 3 closest matching chunks of text
    results = collection.query(
        query_texts=[question],
        n_results=3
    )
    
    # Combine the found text segments into one background context string
    retrieved_chunks = results['documents'][0]
    context = "\n---\n".join(retrieved_chunks)
    
    print("🤖 Formulating answer based on retrieved source material...")
    
    # Direct prompt keeping the AI strictly bound to the textbook facts
    prompt = f"""
    You are Project Veda, an expert AI Teacher. 
    Answer the student's question using ONLY the provided textbook context below. 
    If the answer cannot be found or reasonably inferred from the context, say:
    "I'm sorry, I couldn't find that specific information in your uploaded class materials."
    Do not make up facts outside of the text.

    Textbook Context:
    {context}

    Student Question:
    {question}
    """
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return response.text

if __name__ == "__main__":
    pdf_filename = "lecture.pdf"
    
    if not os.path.exists(pdf_filename):
        print(f"⚠️ Action Required: Please place a PDF named '{pdf_filename}' in this folder first!")
    else:
        # Step 1: Run ingestion (You only need to do this once per file, but running it again updates it)
        process_and_store_pdf(pdf_filename)
        
        # Step 2: Test targeted Q&A across the whole document
        test_question = "What are the components of Data Science?" 
        answer = ask_veda(test_question)
        
        print("\n" + "="*50)
        print(f"🎓 VEDA ANSWER TO: '{test_question}'")
        print("="*50)
        print(answer)