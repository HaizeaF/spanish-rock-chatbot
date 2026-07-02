from langgraph.graph import END, StateGraph
from chatbot.backend.graph.state import GraphState
from chatbot.backend.graph.nodes import (retrieve, web_search, generate, generate_off_topic, generate_fallback, route_question, route_relevance, route_web_results, route_hallucination)

def build_graph() -> StateGraph:
    graph = StateGraph(GraphState)

    graph.add_node("retrieve", retrieve)
    graph.add_node("web_search", web_search)
    graph.add_node("generate", generate)
    graph.add_node("generate_off_topic", generate_off_topic)
    graph.add_node("generate_fallback", generate_fallback)

    graph.set_conditional_entry_point(
        route_question,
        {
            "vectorstore": "retrieve",
            "off_topic": "generate_off_topic"
        }
    )

    graph.add_conditional_edges(
        "retrieve",
        route_relevance,
        {
            "relevant": "generate",
            "not_relevant": "web_search"
        }
    )

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
        route_hallucination,
        {
            "grounded": END,
            "not_grounded": "generate_fallback"
        }
    )

    graph.add_edge("generate_off_topic", END)
    graph.add_edge("generate_fallback", END)

    return graph.compile()