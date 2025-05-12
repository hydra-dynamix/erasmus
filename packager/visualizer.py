
from pathlib import Path
from utils.rich_console import get_console_logger
import networkx as nx
import matplotlib.pyplot as plt

console = get_console_logger()

def visualize_graph(files_code_map: dict[str, str], dependency_graph: dict[str, set[str]], output_path: Path | None = None) -> None:
    """Visualize the dependency graph using networkx and matplotlib.
    
    Args:
        files_code_map: Dictionary mapping file paths to their code
        dependency_graph: Dictionary mapping file paths to their dependencies
        output_path: Optional path to save the visualization. If None, the graph is displayed.
    """
    
    # Create a directed graph
    G = nx.DiGraph()
    
    # Add nodes (files)
    for file in files_code_map:
        # Use just the filename for display, not the full path
        node_label = Path(file).name
        G.add_node(file, label=node_label)
    
    # Print dependency information for debugging
    console.print("[info]Dependency relationships:")
    for file, deps in dependency_graph.items():
        if deps:  # Only print if there are dependencies
            console.print(f"  {Path(file).name} depends on: {[Path(d).name for d in deps]}")
    
    # Add edges (dependencies) - Note: In a dependency graph, arrows point FROM the dependent TO the dependency
    # This is the reverse of how we store it in dependency_graph
    for dependent, dependencies in dependency_graph.items():
        for dependency in dependencies:
            # The edge goes FROM the dependent TO the dependency
            G.add_edge(dependent, dependency)
    
    # Set up the plot
    plt.figure(figsize=(12, 8))
    pos = nx.spring_layout(G, seed=42)  # Consistent layout
    
    # Draw nodes and edges with arrows showing dependency direction
    nx.draw_networkx_nodes(G, pos, node_size=700, node_color="skyblue")
    nx.draw_networkx_edges(G, pos, arrowstyle='->', arrowsize=15, width=1.5, edge_color="gray")
    
    # Add labels with just the filename, not the full path
    labels = {node: Path(node).name for node in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=10)
    
    plt.title("Python File Dependencies")
    plt.axis("off")
    
    # Save or display
    if output_path:
        plt.savefig(output_path)
        console.print(f"[success]Graph visualization saved to {output_path}")
    else:
        plt.show()
        console.print("[info]Graph visualization displayed")
    