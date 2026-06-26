from langgraph.graph import END, StateGraph
from chatbot.backend.graph.state import GraphState
from chatbot.backend.graph.nodes import (route_question, retrieve, grade_documents, web_search, generate, generate_off_topic, route_method, route_generation, grade_web_results, route_web_results)

def build_graph():
    graph = StateGraph(GraphState)

    graph.add_node("retrieve", retrieve)
    graph.add_node("grade_documents", grade_documents)
    graph.add_node("web_search", web_search)
    graph.add_node("grade_web_results", grade_web_results)
    graph.add_node("generate", generate)
    graph.add_node("generate_off_topic", generate_off_topic)

    graph.set_conditional_entry_point(
        route_question,
        {
            "vectorstore": "retrieve",
            "off_topic": "generate_off_topic"
        }
    )
    graph.add_edge("retrieve", "grade_documents")
    graph.add_conditional_edges(
        "grade_documents",
        route_method,
        {
            "websearch": "web_search",
            "generate": "generate"
        }
    )
    graph.add_edge("web_search", "grade_web_results")
    graph.add_conditional_edges(
        "grade_web_results",
        route_web_results,
        {
            "off_topic": "generate_off_topic",
            "generate": "generate"
        }
    )
    graph.add_edge("generate_off_topic", END)
    graph.add_conditional_edges(
        "generate",
        route_generation,
        {
            "not_supported": "generate",
            "useful": END,
            "not_useful": "web_search"
        }
    )

    return graph.compile()