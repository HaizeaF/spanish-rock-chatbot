from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_classic.schema import Document
from langchain_tavily import TavilySearch
from chatbot.backend.rag.retriever import get_retriever
from chatbot.backend.graph.chains import retrieval_grader, answer_chain, hallucination_grader, answer_grader, question_router, web_results_grader
from chatbot.backend.config import MAX_RETRIES, WEB_SEARCH_MAX_RESULTS, OFF_TOPIC_RESPONSE, MIN_DOCS_FOR_GENERATION

load_dotenv()

retriever = None
web_search_tool = TavilySearch(max_results=WEB_SEARCH_MAX_RESULTS)

def _format_history(history: list) -> str:
    if not history:
        return "No previous conversation."
    return "\n".join(
        f"{'Usuario' if isinstance(msg, HumanMessage) else 'Asistente'}: {msg.content}"
        for msg in history
    )


def _format_context(documents: list) -> str:
    chunks = []
    for doc in documents:
        source = doc.metadata.get("source", "")
        title = doc.metadata.get("title", "")
        chunk = f"Title: {title}\nContent: {doc.page_content}\nSource: {source}"
        chunks.append(chunk)
    return "\n\n".join(chunks)


def _validate_relevance(question: str, history: str, doc) -> bool:
    score = retrieval_grader.invoke({
        "history": history,
        "question": question,
        "document": _format_context([doc])
    })
    return score["relevant"] == "yes"


def _validate_hallucination(documents: list, generation: str) -> bool:
    score = hallucination_grader.invoke({
        "documents": _format_context(documents),
        "generation": generation
    })
    return score["grounded"] == "yes"


def _validate_answer(question: str, generation: str) -> bool:
    score = answer_grader.invoke({
        "question": question,
        "generation": generation
    })
    return score["useful"] == "yes"

def get_vector_retriever():
    global retriever

    if retriever is None:
        retriever = get_retriever()

    return retriever

def route_question(state):
    print("Routing question")
    result = question_router.invoke({"question": state["question"]})
    route = result["route"]
    print(f"Route: {route}")
    
    return route


def retrieve(state):
    print("Retrieving data")
    vector_retriever = get_vector_retriever()
    documents = vector_retriever.invoke(state["question"])

    return {"documents": documents, "question": state["question"]}


def grade_documents(state):
    print("Grading documents")
    question = state["question"]
    history = _format_history(state.get("history", []))
    filtered_docs = []
    needs_web_search = False
    
    for doc in state["documents"]:
        if _validate_relevance(question, history, doc):
            print("Document relevant")
            filtered_docs.append(doc)
        else:
            print("Document not relevant")

    if len(filtered_docs) < MIN_DOCS_FOR_GENERATION:
        needs_web_search = True

    return {"documents": filtered_docs, "question": question, "is_web_search": needs_web_search}


def web_search(state):
    print("Web search")
    result = web_search_tool.invoke({"query": state["question"]})
    web_docs = [
        Document(
            page_content=res["content"],
            metadata={"source": "web_search", "title": res.get("title", ""), "url": res.get("url", "")}
        )
        for res in result["results"]
    ]
    documents = state["documents"] or []
    documents.extend(web_docs)
    return {"documents": documents, "question": state["question"]}


def grade_web_results(state):
    print("Grading web results")
    topic_docs = [
        doc for doc in state["documents"]
        if doc.metadata.get("source") == "web_search"
        and web_results_grader.invoke({"document": _format_context([doc])})["in_domain"] == "yes"
    ]

    is_off_topic = len(topic_docs) == 0
    print(f"Web results in domain: {not is_off_topic}")
    return {**state, "is_off_topic": is_off_topic}

def generate(state):
    print("Generating answer")
    generation = answer_chain.invoke({
        "context": _format_context(state["documents"]),
        "question": state["question"],
        "history": _format_history(state.get("history", []))
    })
    return {
        "documents": state["documents"],
        "question": state["question"],
        "generation": generation,
        "retries": state.get("retries", 0) + 1
    }


def generate_off_topic(state):
    print("Off-topic")
    return {
        "generation": OFF_TOPIC_RESPONSE,
        "question": state["question"],
        "documents": []
    }


def route_method(state):
    print("Deciding to generate")
    if state["is_web_search"]:
        print("Decision: web search")
        return "websearch"
    
    print("Decision: generate")
    return "generate"

def route_web_results(state):
    print("Routing web results")
    if state["is_off_topic"]:
        print("Decision: off topic")
        return "off_topic"
    
    print("Decision: generate")
    return "generate"

def route_generation(state):
    print("Grading generation")
    retries = state.get("retries", 0)

    if retries >= MAX_RETRIES:
        print(f"Max retries ({MAX_RETRIES}) reached, forcing end")
        return "useful"

    if not _validate_hallucination(state["documents"], state["generation"]):
        print("Not grounded")
        return "not_supported"

    if _validate_answer(state["question"], state["generation"]):
        print("Useful")
        return "useful"

    print("Not useful")
    return "not_useful"