"""Node and routing functions for the chatbot conversational graph.
 
Each node performs a single responsibility and returns a partial state update, following LangGraph conventions.
"""

import asyncio
from chatbot.backend.schemas.state import GraphState
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_classic.schema import Document
from langchain_tavily import TavilySearch
from chatbot.backend.rag.retriever import get_retriever
from chatbot.backend.graph.chains import answer_chain, hallucination_grader, question_router, web_results_grader, keywords_generator, question_rewriter
from chatbot.backend.config.config import Config

load_dotenv()

_web_search_tool = TavilySearch(max_results=Config.WEB_SEARCH_MAX_RESULTS)

# Formatting helpers
def _format_history(history: list, max_turns: int = 1) -> str:
    """Format the last conversation turns into a readable block for prompts.
 
    Off-topic and fallback responses are excluded so they do not pollute the context used to resolve pronouns or references.
    """
    if not history:
        return "No previous conversation."
    
    filtered = [msg for msg in history if msg.content not in (Config.OFF_TOPIC_RESPONSE, Config.FALLBACK_RESPONSE)]

    if not filtered:
        return "No previous conversation."
    
    filtered = filtered[-max_turns * 2:]

    return "\n".join(f"{'User' if isinstance(msg, HumanMessage) else 'Agent'}: {msg.content}"for msg in filtered)

def _format_context(documents: list) -> str:
    """Format a list of documents into a single text block for prompts."""
    chunks = []
    for doc in documents:
        source = doc.metadata.get("source", "")
        title = doc.metadata.get("title", "")
        chunk = f"Title: {title}\nContent: {doc.page_content}\nSource: {source}"
        chunks.append(chunk)

    return "\n\n".join(chunks)

# Validation helpers
async def _validate_hallucination(documents: list, generation: str) -> bool:
    """Check whether a generated answer is grounded in the retrieved documents."""
    try:
        result = await hallucination_grader.ainvoke({"documents": _format_context(documents), "generation": generation})

        print(f"Hallucination grader raw result: {result}")
        return result.get("grounded") == "yes"
    except Exception as e:
        print(f"Hallucination grader failed to parse: {e}")
        return False

async def _validate_web_results(doc) -> bool:
    """Check whether a single web search result is within the chatbot's domain."""
    try:
        result = await web_results_grader.ainvoke({"document": _format_context([doc])})

        print(f"Web results grader raw result: {result}")
        return result.get("in_domain") == "yes"
    except Exception as e:
        print(f"Domain grader failed to parse: {e}")
        return False

# Node functions
async def rewrite_question(state: GraphState) -> dict:
    """Rewrite the user question into a standalone version using conversation history."""
    print("Rewriting question")

    try:
        result = await question_rewriter.ainvoke({"history": _format_history(state.get("history", [])), "question": state["question"]})

        print(f"Question rewriter raw result: {result}")

        standalone = result.get("question", state["question"])

    except Exception as e:
        print(f"Question rewriter failed: {e}")
        standalone = state["question"]

    return {"standalone_question": standalone}

async def generate_keywords(state: GraphState) -> dict:
    """Generate a retrieval-optimized keyword query from the standalone question."""
    print("Rewriting query")
    try:
        result = await keywords_generator.ainvoke({"question": state["standalone_question"]})
        print (f"Query rewriter raw result: {result}")
        keywords = result.get("query", state["standalone_question"])
    except Exception as e:
        print(f"Query rewriter failed to parse: {e}")
        keywords = state["standalone_question"]

    return {"keywords": keywords}

async def retrieve(state: GraphState) -> dict:
    """Retrieve candidate documents from the vector store using the generated keywords."""
    print("Retrieving data")
    vector_retriever = await get_retriever()
    documents = await vector_retriever.ainvoke(state["keywords"])

    print(f"Retrieved {len(documents)} documents")

    return {"documents": documents}

async def web_search(state) -> dict:
    """Fetch live web search results for the standalone question as a fallback source."""
    print("Web search")
    result = await _web_search_tool.ainvoke({"query": state["standalone_question"]})
    web_docs = [Document(page_content=res["content"],metadata={"source": "web_search", "title": res.get("title", "")}) for res in result.get("results", [])]

    print(f"Web search returned {len(web_docs)} results")

    return {"documents": web_docs, "web_searched": True}

async def generate(state: GraphState) -> dict:
    """Generate an answer grounded in the retrieved documents."""
    print("Generating answer")
    generation = await answer_chain.ainvoke({"context": _format_context(state["documents"]), "question": state["standalone_question"]})

    print(f"Generated answer: {generation}")
    return {"generation": generation}

def generate_off_topic(state: GraphState) -> dict:
    """Return the fixed off-topic response."""
    print("Off-topic")
    return {"generation": Config.OFF_TOPIC_RESPONSE}

def generate_fallback(state: GraphState) -> dict:
    """Return the fixed fallback response when no grounded answer could be produced."""
    print("Hallucinated answer, providing fallback")
    return {"generation": Config.FALLBACK_RESPONSE}

# Route functions
async def route_question(state: GraphState) -> str:
    """Route the standalone question to the vector store or the off-topic branch."""
    print("Routing question")
    try:
        result = await question_router.ainvoke({"question": state["standalone_question"]})

        print(f"Router raw result: {result}")
        route = result.get("route", "off_topic")
    except Exception as e:
        print(f"Router failed to parse: {e}")
        route = "off_topic"
        
    print(f"Route: {route}")

    return route

async def route_web_results(state: GraphState) -> str:
    """Route to generation only if at least one web result is within the chatbot's domain."""
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

async def route_generation(state: GraphState) -> str:
    """Decide whether the answer is final, needs a fallback, or needs a web search retry.
 
    Web search is attempted exactly once per turn. If the answer is not grounded and the web has not been searched yet, the graph falls back to web search, otherwise the fixed fallback response is returned to avoid infinite loops.
    """
    if state["generation"] != Config.FALLBACK_RESPONSE:
        grounded = await _validate_hallucination(state["documents"], state["generation"])
        if grounded:
            return "end"
        
        if state.get("web_searched", False):
            return "generate_fallback"
        
        return "web_search"

    if state.get("web_searched", False):
        return "end"

    return "web_search"