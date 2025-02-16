import os

from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
from langchain.schema import Document  # Import Document class
from langchain_community.vectorstores import Chroma

from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI, OpenAIEmbeddings


class GPTHandler:
    def __init__(self, persistent_directory: str, pdf_directory: str, embedding_model: str, chat_model: str, system_prompt: str, contextualization_prompt: str, k: int = 1):
        """
        Initializes GPTHandler with the ability to process PDFs, set up Chroma vector store, and handle queries with contextualization.
        :param persistent_directory: Path to Chroma database.
        :param pdf_directory: Directory containing PDF files to process.
        :param embedding_model: OpenAI embedding model.
        :param chat_model: OpenAI chat model.
        :param system_prompt: System prompt for the LLM.
        :param contextualization_prompt: Prompt template for question contextualization.
        :param k: Number of top documents to retrieve.
        """
        self.persistent_directory = persistent_directory
        self.pdf_directory = pdf_directory
        self.embedding_model = embedding_model
        self.chat_model = chat_model
        self.system_prompt = system_prompt
        self.contextualization_prompt = contextualization_prompt
        self.k = k

        # Ensure Chroma vector store is initialized
        self.db = self.initialize_vector_store()

        # Create retriever
        self.retriever = self.db.as_retriever(search_type="similarity", search_kwargs={"k": self.k})

        # LLM setup
        self.llm = ChatOpenAI(model=self.chat_model)

        # Question answering prompt template
        self.qa_prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ])

        # Contextualization prompt template
        self.contextualization_prompt = ChatPromptTemplate.from_messages([
            ("system", self.contextualization_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ])

        # Create chains
        self.question_answer_chain = create_stuff_documents_chain(self.llm, self.qa_prompt)
        self.history_aware_retriever = create_history_aware_retriever(
            llm=self.llm,
            retriever=self.retriever,
            prompt=self.contextualization_prompt
        )

        # Retrieval-Augmented Generation (RAG) pipeline
        self.rag_chain = create_retrieval_chain(self.history_aware_retriever, self.question_answer_chain)

        # Initialize chat history
        self.chat_history = []

    def ask(self, query: str):
        """
        Processes a query using the RAG pipeline with contextualization, updating chat history.
        :param query: User's question.
        :return: AI's response.
        """
        
        # Process the query through the RAG chain
        result = self.rag_chain.invoke({"input": query, "chat_history": self.chat_history})
        response = result["answer"]

        # Append the user's query as a HumanMessage
        self.chat_history.append(HumanMessage(content=query))
        # Append the assistant's response as a SystemMessage
        self.chat_history.append(SystemMessage(content=response))

        return response

    def reset_chat_history(self):
        """
        Clears the chat history.
        """
        self.chat_history = []

    def initialize_vector_store(self):
        """
        Initializes the Chroma vector store from PDFs if not already created.
        :return: A Chroma vector store instance.
        """
        if self.vector_store_exists():
            return self.load_existing_vector_store()
        
        # If vector store doesn't exist, initialize it
        self.check_pdf_directory()
        documents = self.load_and_process_pdfs()
        docs = self.split_documents(documents)
        return self.create_and_persist_vector_store(docs)

    def vector_store_exists(self):
        """Checks if the vector store already exists."""
        return os.path.exists(self.persistent_directory)

    def check_pdf_directory(self):
        """Checks if the PDF directory exists and contains PDF files."""
        if not os.path.exists(self.pdf_directory):
            raise FileNotFoundError(f"PDF directory '{self.pdf_directory}' does not exist.")
        
        pdf_files = [f for f in os.listdir(self.pdf_directory) if f.endswith(".pdf")]
        if not pdf_files:
            raise FileNotFoundError(f"No PDF files found in '{self.pdf_directory}'.")

    def load_and_process_pdfs(self):
        """Loads and processes PDF files to extract text."""
        documents = []
        pdf_files = [f for f in os.listdir(self.pdf_directory) if f.endswith(".pdf")]
        for pdf_file in pdf_files:
            file_path = os.path.join(self.pdf_directory, pdf_file)
            print(f"Processing file: {file_path}")

            # Extract text from the PDF file
            reader = PdfReader(file_path)
            pdf_text = "".join(page.extract_text() for page in reader.pages)

            # Add the extracted text as a Document with metadata
            documents.append(Document(page_content=pdf_text, metadata={"source": pdf_file}))
        return documents

    def split_documents(self, documents):
        """Splits documents into chunks."""
        text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
        return text_splitter.split_documents(documents)

    def create_and_persist_vector_store(self, docs):
        """Creates and persists the vector store."""
        embeddings = OpenAIEmbeddings(model=self.embedding_model)
        db = Chroma.from_documents(docs, embeddings, persist_directory=self.persistent_directory)
        print("Vector store initialized successfully.")
        return db

    def load_existing_vector_store(self):
        """Loads an existing vector store."""
        print(f"Vector store already exists at '{self.persistent_directory}'.")
        embeddings = OpenAIEmbeddings(model=self.embedding_model)
        return Chroma(persist_directory=self.persistent_directory, embedding_function=embeddings)