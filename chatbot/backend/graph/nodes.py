import asyncio
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_classic.schema import Document
from langchain_tavily import TavilySearch
from chatbot.backend.rag.retriever import get_retriever
from chatbot.backend.graph.chains import retrieval_grader, answer_chain, hallucination_grader, answer_grader, question_router, web_results_grader, format_chain
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


async def _validate_relevance(question: str, history: str, doc) -> bool:
    score = await retrieval_grader.ainvoke({
        "history": history,
        "question": question,
        "document": _format_context([doc])
    })
    return score["relevant"] == "yes"


async def _validate_hallucination(documents: list, generation: str) -> bool:
    score = await hallucination_grader.ainvoke({
        "documents": _format_context(documents),
        "generation": generation
    })
    return score["grounded"] == "yes"


async def _validate_answer(question: str, generation: str) -> bool:
    score = await answer_grader.ainvoke({
        "question": question,
        "generation": generation
    })
    return score["useful"] == "yes"

async def _validate_domain(doc) -> bool:
    result = await web_results_grader.ainvoke({"document": _format_context([doc])})
    return result["in_domain"] == "yes"

async def route_question(state):
    print("Routing question")
    result = await question_router.ainvoke({"question": state["question"]})
    route = result["route"]
    print(f"Route: {route}")
    
    return route

async def retrieve(state):
    print("Retrieving data")
    vector_retriever = await get_retriever()
    documents = await vector_retriever.ainvoke(state["question"])

    return {"documents": documents, "question": state["question"]}

async def grade_documents(state):
    print("Grading documents")
    question = state["question"]
    history = _format_history(state.get("history", []))
    filtered_docs = []
    needs_web_search = False
    
    results = await asyncio.gather(
        *[_validate_relevance(question, history, doc) for doc in state["documents"]]
    )
    filtered_docs = [doc for doc, ok in zip(state["documents"], results) if ok]

    needs_web_search = len(filtered_docs) < MIN_DOCS_FOR_GENERATION

    return {"documents": filtered_docs, "question": question, "is_web_search": needs_web_search}


async def web_search(state):
    print("Web search")
    result = await web_search_tool.ainvoke({"query": state["question"]})
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


async def grade_web_results(state):
    print("Grading web results")
    
    web_docs = [doc for doc in state["documents"] if doc.metadata.get("source") == "web_search"]
    results = await asyncio.gather(*[_validate_domain(doc) for doc in web_docs])
    topic_docs = [doc for doc, ok in zip(web_docs, results) if ok]

    is_off_topic = len(topic_docs) == 0
    print(f"Web results in domain: {not is_off_topic}")

    return {**state, "is_off_topic": is_off_topic}

async def generate(state):
    print("Generating answer")
    generation = await answer_chain.ainvoke({
        "context": _format_context(state["documents"]),
        "question": state["question"],
        "history": _format_history(state.get("history", []))
    })

    return {"documents": state["documents"], "question": state["question"], "generation": generation, "retries": state.get("retries", 0) + 1}

async def format_response(state):
    print("Formatting response")
    source = ""
    for doc in state["documents"]:
        source = doc.metadata.get("source", "")
        if source:
            break

    formatted = await format_chain.ainvoke({
        "raw_answer": state["generation"],
        "source": source
    })

    return {**state, "formatted_generation": formatted}

def generate_off_topic(state):
    print("Off-topic")

    return {"generation": OFF_TOPIC_RESPONSE, "question": state["question"], "documents": []}


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

async def route_generation(state):
    print("Grading generation")
    retries = state.get("retries", 0)

    if retries >= MAX_RETRIES:
        print(f"Max retries ({MAX_RETRIES}) reached, forcing end")
        return "useful"

    if not await _validate_hallucination(state["documents"], state["generation"]):
        print("Not grounded")
        if retries == 1:
            return "not_supported"
        return "not_useful"

    if await _validate_answer(state["question"], state["generation"]):
        print("Useful")
        return "useful"

    print("Not useful")
    return "not_useful"