from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from vector_store import vector_store  # Import the vector store

# Load retriever
retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 1})

# Load LLM
llm = ChatOpenAI(model="gpt-4o-mini")

# Contextualized question prompt
contextualize_q_system_prompt = (
    "Учитывая историю чата и последний вопрос пользователя, "
    "который может ссылаться на контекст в истории чата, "
    "сформулируйте самостоятельный вопрос, который можно понять "
    "без истории чата. НЕ отвечайте на вопрос, просто "
    "переформулируйте его, если это необходимо, иначе оставьте без изменений."
)

contextualize_q_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", contextualize_q_system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ]
)

history_aware_retriever = create_history_aware_retriever(llm, retriever, contextualize_q_prompt)

# QA System prompt (Updated for language adaptation)
qa_system_prompt = (
    "Ты — многоязычный Telegram-бот, созданный для регистрации жителей города "
    "и управления системой бонусов в виде бутылок воды. Твоя задача — помогать "
    "пользователям зарегистрироваться, использовать бонусы и находить магазины, где можно "
    "обменять бонусы на воду. Ты должен отвечать на языке пользователя."
)

qa_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", qa_system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
        ("system", 
         "Ответь на том же языке, что и пользовательский ввод. Если язык не распознан, используй последний язык из истории чата. Контекст: {context}")
    ]
)

question_answer_chain = create_stuff_documents_chain(llm, qa_prompt, document_variable_name="context")

# RAG pipeline
rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)

def chatbot_loop():
    """Starts the chatbot interaction loop."""
    print("Start chatting with the AI! Type 'exit' to end the conversation.")
    chat_history = []
    
    while True:
        query = input("You: ")
        if query.lower() == "exit":
            break
        
        
        result = rag_chain.invoke({"input": query, "chat_history": chat_history})
        
        print(f"AI: {result['answer']}")
    
        chat_history.append(HumanMessage(content=query))
        chat_history.append(SystemMessage(content=result["answer"]))

        if len(chat_history) > 10:
            chat_history = []

# Run chatbot loop
if __name__ == "__main__":
    chatbot_loop()
