import os
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
from langchain.schema import Document  

load_dotenv()

current_dir = os.path.dirname(os.path.abspath(__file__))
pdf_dir = os.path.join(current_dir, "db_pdf")
db_dir = os.path.join(current_dir, "db")
persistent_directory = os.path.join(db_dir, "chroma_db_with_metadata")

embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")

def initialize_vector_store():
    """Processes PDFs and initializes the vector store if not already created."""
    if not os.path.exists(persistent_directory):
        print("Persistent directory does not exist. Initializing vector store...")

        if not os.path.exists(pdf_dir):
            raise FileNotFoundError(f"PDF directory '{pdf_dir}' does not exist.")

        # Load and process PDF files
        pdf_files = [f for f in os.listdir(pdf_dir) if f.endswith(".pdf")]
        documents = []
        for book_file in pdf_files:
            file_path = os.path.join(pdf_dir, book_file)
            print(f"Processing file: {file_path}")

            reader = PdfReader(file_path)
            pdf_text = "".join([page.extract_text() for page in reader.pages if page.extract_text()])

            documents.append(Document(page_content=pdf_text, metadata={"source": book_file}))

        # Split documents
        text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
        docs = text_splitter.split_documents(documents)
        print(f"\nNumber of document chunks: {len(docs)}")

        # Create and persist vector store
        db = Chroma.from_documents(docs, embeddings, persist_directory=persistent_directory)
        print("\nFinished creating and persisting vector store.")
    else:
        print("Vector store already exists.")

    # Return vector store instance
    return Chroma(persist_directory=persistent_directory, embedding_function=embeddings)

# Ensure the vector store is initialized when this module is imported
vector_store = initialize_vector_store()
