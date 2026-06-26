from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import WebBaseLoader
from langchain_milvus import Milvus
from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_ollama import ChatOllama
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_tavily import TavilySearch
from typing_extensions import TypedDict
from typing import List
from langchain_classic.schema import Document
from langgraph.graph import END, StateGraph
from pprint import pprint

load_dotenv()

# LLM
local_llm = "llama3"

# Index
urls = [
    "https://es.wikipedia.org/wiki/H%C3%A9roes_del_Silencio",
    "https://es.wikipedia.org/wiki/Fito_%26_Fitipaldis",
    "https://es.wikipedia.org/wiki/Extremoduro"
]

docs = [WebBaseLoader(url).load() for url in urls]
docs_list = [item for sublist in docs for item in sublist]
text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(chunk_size=500, chunk_overlap=50)
doc_splits = text_splitter.split_documents(docs_list)

# Milvus
vectorstore = Milvus.from_documents(
    documents=doc_splits,
    collection_name="spanish_rock",
    embedding=HuggingFaceEmbeddings(),
    connection_args={"uri": "./spanish_rock.db"}
)

retriever = vectorstore.as_retriever()

# TODO: Cambiar los pipes por create_agent y langgraph
## Retrieval Grader

llm = ChatOllama(model=local_llm, format="json", temperature=0)

prompt = PromptTemplate(
    template="""You are a retrieval grader evaluating the relevance of a retrieved document to a user question.

    If the document contains keywords or semantic content related to the question, return true. 
    If it does not, return false.
    Do not need it to be a full answer just relevant content. Your job is to filter erroneus retrievals.

    Return a JSON with a single key "relevant" and a boolean value. No explanations.

    Retrieved document: {document}
    User question: {question}""",
    input_variables=["question", "document"]
)

retrieval_grader = prompt | llm | JsonOutputParser() # TODO: Cambiar a langgraph

## Answer writter

# Prompt # TODO: Si es busqueda web y no wikipedia, que no cite la wikipedia. Darle formato correcto a las citas de wikipedia. Que no mencione nada del contexto.
prompt = PromptTemplate(
    template="""You are an expert assistant on Spanish rock music.
    Answer always in Spanish.

    Answer the user's question based solely on the provided context. Never infer or assume information that is not explicitly stated in the context.
    If the context does not contain enough information to answer, respond exactly with: "No tengo información suficiente para responder." Do not make up information.

    At the end of your response, always cite the Wikipedia article(s) used as source. Do not include references or citations found within the Wikipedia articles (such as [1], [2], etc.).

    User question: {question}
    Retrieved context: {context}
    Answer:""",
    input_variables=["question", "context"]
)

llm = ChatOllama(model=local_llm, temperature=0)

# Post-processing
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

# Chain
rag_chain = prompt | llm | StrOutputParser()

## Hallucination grader

# llm
llm = ChatOllama(model=local_llm, temperature=0)

# prompt
prompt = PromptTemplate(
    template="""You are a hallucination grader evaluating whether an answer is grounded in the provided documents.
    If the answer is supported by the facts in the documents, return true.
    If the answer contains information not present in the documents, return false.

    Return a JSON with a single key "grounded" and a boolean value. No explanations.

    Retrieved facts: {documents}
    User question: {generation}""",
    input_variables=["generation", "documents"]
)

hallucination_grader = prompt | llm | JsonOutputParser()

## Answer Grader

# llm
llm = ChatOllama(model=local_llm, temperature=0)

# prompt
prompt = PromptTemplate(
    template="""You are an answer grader evaluating whether an answer is useful and relevant to the user's question.
    If the answer resolves the question, return true.
    If the answer is not useful or off-topic, return false.

    Return a JSON with a single key "useful" and a boolean value. No explanations.

    User question: {question}
    Answer: {generation}""",
    input_variables=["question", "generation"]
)

answer_grader = prompt | llm | JsonOutputParser()

## Router #TODO: Posiblemente borrar este agente

# llm
llm = ChatOllama(model=local_llm, temperature=0)

# prompt
prompt = PromptTemplate(
    template="""You are a question router deciding where to send a user question.
    If the question is related to Spanish rock music, bands, artists, albums or concerts, even if not explicitly mentioned, return "vectorstore".
    If the question is about a different topic, return "web_search".

    Return a JSON with a single key "datasource" and a string value "vectorstore" or "web_search". No explanations.

    User question: {question}""",
    input_variables=["question"]
)

question_router = prompt | llm | JsonOutputParser()

### Search
web_search_tool = TavilySearch(max_results=5)

## State # TODO: Diferenciar mediante nombre los nodos de los demás métodos
class GraphState(TypedDict):
    question : str
    generation : str
    web_search : str
    documents : List[str]

def retrieve(state):
    print("//----- RETRIEVE ----- //")
    question = state["question"]

    documents = retriever.invoke(question)
    return {"documents": documents, "question": question}

def generate(state):
    print("//----- GENERATE ----- //")
    question = state["question"]
    documents = state["documents"]

    generation = rag_chain.invoke({"context": documents, "question": question})
    return {"documents": documents, "question": question, "generation": generation}

def grade_documents(state):
    print("//----- CHECK RELEVANCE ----- //")
    question = state["question"]
    documents = state["documents"]

    filtered_docs = []
    web_search = "false"

    for d in documents:
        score = retrieval_grader.invoke({"question": question, "document": d.page_content})
        relevant = str(score["relevant"])
        if relevant.lower() == "true":
            print("//----- GRADE: DOCUMENT RELEVANT  ----- //")
            filtered_docs.append(d)
        else:
            print("//----- GRADE: DOCUMENT NOT RELEVANT  ----- //")
            web_search = "true"
            continue
    
    return {"documents": filtered_docs, "question": question, "web_search": web_search}

def web_search(state):
    print("//----- WEB SEARCH ----- //")
    question = state["question"]
    documents = state["documents"]

    docs = web_search_tool.invoke({"query": question})
    web_results = "\n".join([d["content"] for d in docs["results"]])
    web_results = Document(page_content=web_results)

    # TODO: ¿Hacer directamente el append siempre o None me lo impide?
    if documents is not None:
        documents.append(web_results)
    else:
        documents = [web_results]
    
    return {"documents": documents, "question": question}

def route_question(state):
    print("//----- ROUTE QUESTION ----- //")
    question = state["question"]
    print("question")
    source = question_router.invoke({"question": question})
    print(source)
    pprint(source["datasource"])

    # TODO: ¿Devolver el source["datasource"] directamente?
    if source["datasource"] == "web_search":
        print("//----- ROUTE QUESTION TO WEB SEARCH ----- //")
        return "websearch"
    elif source["datasource"] == "vectorstore":
        print("//----- ROUTE QUESTION TO RAG ----- //")
        return "vectorstore"

def decide_to_generate(state):
    print("//----- ASSESS GRADED DOCUMENTS ----- //")
    web_search = state["web_search"]

    # TODO: ¿No es al reves, con que uno de los documentos se marque como no util ya deja el web_search a true?
    if web_search == "true":
        print("//----- DECISION: ALL DOCUMENTS ARE NOT RELEVANT, INCLUDE WEB SEARCH ----- //")
        return "websearch"
    else:
        print("//----- DECISION: GENERATE ----- //")
        return "generate"
    
def grade_generation_v_documents_and_question(state):
    print("//----- CHECK HALLUCINATIONS ----- //")
    question = state["question"]
    documents = state["documents"]
    generation = state["generation"]

    score = hallucination_grader.invoke({"documents": documents, "generation": generation})
    grounded = str(score["grounded"])

    if grounded.lower() == "true":
        print("//----- DECISION: GENERATION IS GROUNDED IN DOCUMENTS ----- //")
        print("//----- GRADE GENERATION VS QUESTION ----- //")
        score = answer_grader.invoke({"question": question, "generation": generation})
        useful = str(score["useful"])
        if useful.lower() == "true":
            print("//----- DECISION: GENERATION ADDRESSES QUESTION ----- //")
            return "useful"
        else:
            print("//----- DECISION: GENERATION DOES NOT ADDRESSES QUESTION ----- //")
            return "not useful"
    else:
        print("//----- DECISION: GENERATION IS NOT GROUNDED IN DOCUMENTS ----- //")
        return "not supported"
    
## Graph
graph = StateGraph(GraphState)

graph.add_node("websearch", web_search)
graph.add_node("retrieve", retrieve)
graph.add_node("grade_documents", grade_documents)
graph.add_node("generate", generate)

graph.set_conditional_entry_point(
    route_question,
    {
        "websearch": "websearch",
        "vectorstore": "retrieve"
    }
)

graph.add_edge("retrieve", "grade_documents")
graph.add_conditional_edges(
    "grade_documents",
    decide_to_generate,
    {
        "websearch": "websearch",
        "generate": "generate"
    }
)

graph.add_edge("websearch", "generate")

# TODO: Añadir fallback o evitar que generate llame a generate infinitamente
graph.add_conditional_edges(
    "generate",
    grade_generation_v_documents_and_question,
    {
        "not supported": "generate",
        "useful": END,
        "not useful": "websearch"
    }
)

app = graph.compile()
inputs = {"question": "¿Quien es Robe?"}
for output in app.stream(inputs):
    for key, value in output.items():
        pprint(f"Finished running: {key}:")
pprint(value["generation"])

with open("graph.png", "wb") as f:
    f.write(app.get_graph(xray=True).draw_mermaid_png())