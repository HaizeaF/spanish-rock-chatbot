"""Graph visualization service for the chatbot conversational graph.

Wraps LangGraph's built-in Mermaid rendering so the compiled graph can be exported as a PNG image.
"""

from pathlib import Path
from langgraph.graph.state import CompiledStateGraph
from chatbot.backend.config.config import Config
from chatbot.backend.services.graph_service import build_graph
 
class GraphVisualizerService:
    """Render a compiled LangGraph state graph as a PNG image.

    Attributes:
        graph: The compiled state graph to visualize.
    """

    def __init__(self, graph: CompiledStateGraph) -> None:
        """Store the compiled graph that will be rendered."""
        self.graph = graph

    def save_png(self, output_path: str = "") -> Path:
        """Render the graph as a PNG image and save it to disk."""
        path = Path(output_path or Config.GRAPH_IMAGE_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)

        print(f"Generating graph image at {path}")
        png_bytes = self.graph.get_graph().draw_mermaid_png()
        path.write_bytes(png_bytes)
        print(f"Graph image saved to {path}")

        return path


if __name__ == "__main__":
    GraphVisualizerService(build_graph()).save_png()