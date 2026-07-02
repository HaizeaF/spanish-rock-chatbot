import asyncio
from unittest import result
from chatbot.backend.graph.state import GraphState
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_classic.schema import Document
from langchain_tavily import TavilySearch
from chatbot.backend.rag.retriever import get_retriever
from chatbot.backend.graph.chains import answer_chain, hallucination_grader, question_router, web_results_grader, relevance_grader
from chatbot.backend.config import WEB_SEARCH_MAX_RESULTS, OFF_TOPIC_RESPONSE, FALLBACK_RESPONSE

load_dotenv()

retriever = None
web_search_tool = TavilySearch(max_results=WEB_SEARCH_MAX_RESULTS)

# Formatting functions
def _format_history(history: list) -> str:
    if not history:
        return "No previous conversation."
    
    return "\n".join(f"{'Usuario' if isinstance(msg, HumanMessage) else 'Asistente'}: {msg.content}" for msg in history)

def _format_context(documents: list) -> str:
    chunks = []
    for doc in documents:
        source = doc.metadata.get("source", "")
        title = doc.metadata.get("title", "")
        chunk = f"Title: {title}\nContent: {doc.page_content}\nSource: {source}"
        chunks.append(chunk)

    return "\n\n".join(chunks)

# Validation functions
async def _validate_hallucination(documents: list, generation: str) -> bool:
    try:
        score = await hallucination_grader.ainvoke({"documents": _format_context(documents), "generation": generation})

        print(f"Hallucination grader raw result: {score}")
        return score.get("grounded") == "yes"
    except Exception as e:
        print(f"Hallucination grader failed to parse: {e}")
        return False

async def _validate_web_results(doc) -> bool:
    try:
        result = await web_results_grader.ainvoke({"document": _format_context([doc])})

        print(f"Web results grader raw result: {result}")
        return result.get("in_domain") == "yes"
    except Exception as e:
        print(f"Domain grader failed to parse: {e}")
        return False
    
async def _validate_relevance(history: list, question: str, documents: list) -> bool:
    try:
        result = await relevance_grader.ainvoke({"history": _format_history(history), "question": question, "documents": _format_context(documents)})

        print(f"Relevance grader raw result: {result}")
        return result.get("relevant") == "yes"
    except Exception as e:
        print(f"Relevance grader failed to parse: {e}")
        return False

# Node functions
async def retrieve(state: GraphState) -> dict:
    print("Retrieving data")
    vector_retriever = await get_retriever()
    documents = await vector_retriever.ainvoke(state["question"])

    for doc in documents:
        print(f"{doc.page_content[:500]}...")

    print(f"Retrieved {len(documents)} documents")

    return {"documents": documents}

async def web_search(state):
    print("Web search")
    result = await web_search_tool.ainvoke({"query": state["question"]})
    web_docs = [Document(page_content=res["content"],metadata={"source": "web_search", "title": res.get("title", "")}) for res in result.get("results", [])]

    print(f"Web search returned {len(web_docs)} results")

    return {"documents": web_docs}

async def generate(state: GraphState) -> dict:
    print("Generating answer")
    generation = await answer_chain.ainvoke({"context": _format_context(state["documents"]), "question": state["question"], "history": _format_history(state.get("history", []))})

    print(f"Generated answer: {generation}")
    return {"generation": generation}

def generate_off_topic(state: GraphState) -> dict:
    print("Off-topic")
    return {"generation": OFF_TOPIC_RESPONSE}

def generate_fallback(state: GraphState) -> dict:
    print("Hallucinated answer, providing fallback")
    return {"generation": FALLBACK_RESPONSE}

# Route functions
async def route_question(state: GraphState) -> str:
    print("Routing question")
    try:
        result = await question_router.ainvoke({"history": _format_history(state.get("history", [])), "question": state["question"]})

        print(f"Router raw result: {result}")
        route = result.get("route", "off_topic")
    except Exception as e:
        print(f"Router failed to parse: {e}")
        route = "off_topic"
        
    print(f"Route: {route}")

    return route

async def route_relevance(state: GraphState) -> str:
    print("Routing relevance")
    if not state["documents"]:
        print("No documents retrieved, going to web search")
        return "not_relevant"

    is_relevant = await _validate_relevance(state.get("history", []), state["question"], state["documents"])
    print(f"Relevant: {is_relevant}")

    return "relevant" if is_relevant else "not_relevant"

async def route_web_results(state: GraphState) -> str:
    print("Routing web results")
    
    web_docs = [doc for doc in state["documents"] if doc.metadata.get("source") == "web_search"]
    results = await asyncio.gather(*[_validate_web_results(doc) for doc in web_docs])
    topic_docs = [doc for doc, ok in zip(web_docs, results) if ok]

    is_off_topic = len(topic_docs) == 0
    if is_off_topic:
        print("All web results are off-topic")
        return "off_topic"
    
    print(f"{len(topic_docs)} web results are on-topic")

    return "generate"

async def route_hallucination(state: GraphState) -> str:
    print("Routing hallucination")
    is_grounded = await _validate_hallucination(state["documents"], state["generation"])

    print(f"Grounded: {is_grounded}")

    return "grounded" if is_grounded else "not_grounded"