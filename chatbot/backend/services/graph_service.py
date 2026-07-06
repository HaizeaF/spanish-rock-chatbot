"""Graph construction for the chatbot.
 
Builds a LangGraph StateGraph that wires together the rewriting, routing, retrieval, generation and grading nodes.
"""

from langgraph.graph import END, StateGraph
from chatbot.backend.schemas.state import GraphState
from chatbot.backend.graph.nodes import retrieve, web_search, generate, generate_off_topic, generate_fallback, route_question, route_web_results, generate_keywords, rewrite_question, route_generation

def build_graph():
    """Build and compile the conversational graph for the chatbot."""
    graph = StateGraph(GraphState)

    graph.add_node("rewrite_question", rewrite_question)
    graph.add_node("generate_keywords", generate_keywords)
    graph.add_node("retrieve", retrieve)
    graph.add_node("web_search", web_search)
    graph.add_node("generate", generate)
    graph.add_node("generate_off_topic", generate_off_topic)
    graph.add_node("generate_fallback", generate_fallback)


    graph.set_entry_point("rewrite_question")

    graph.add_conditional_edges(
        "rewrite_question",
        route_question,
        {
            "vectorstore": "generate_keywords",
            "off_topic": "generate_off_topic"
        }
    )

    graph.add_edge("generate_keywords", "retrieve")
    
    graph.add_edge("retrieve", "generate")

    graph.add_conditional_edges(
        "web_search",
        route_web_results,
        {
            "generate": "generate",
            "off_topic": "generate_off_topic"
        }
    )

    graph.add_conditional_edges(
        "generate",
        route_generation,
        {
            "generate_fallback": "generate_fallback",
            "web_search": "web_search",
            "end": END
        }
    )

    graph.add_edge("generate_off_topic", END)
    graph.add_edge("generate_fallback", END)

    return graph.compile()