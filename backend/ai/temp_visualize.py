"""Visualize the Resume Assistant LangGraph.

Run this script to generate a visual graph:
    python ai/temp_visualize.py

The graph will be saved as 'graph_visualization.html' which you can open in any browser.
"""

from graph import create_resume_assistant_graph


def save_mermaid_html(mermaid_code: str, filename: str = "graph_visualization.html"):
    """Save mermaid code as an interactive HTML file."""
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Resume Assistant Graph</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e;
            color: #eee;
            padding: 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        h1 {{
            color: #00d9ff;
            margin-bottom: 10px;
        }}
        .graph-container {{
            background: #16213e;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 8px 32px rgba(0, 217, 255, 0.15);
            width: 95%;
            max-width: 1400px;
            overflow: auto;
        }}
        .mermaid {{
            display: flex;
            justify-content: center;
        }}
    </style>
</head>
<body>
    <h1>Resume Assistant Graph</h1>
    <div class="graph-container">
        <pre class="mermaid">
{mermaid_code}
        </pre>
    </div>
    <script>
        mermaid.initialize({{
            startOnLoad: true,
            theme: 'dark',
            flowchart: {{
                useMaxWidth: true,
                htmlLabels: true,
                curve: 'basis'
            }}
        }});
    </script>
</body>
</html>"""
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"✓ Saved to {filename} — open in browser to view interactive graph")


def print_graph_info(graph):
    """Print detailed graph structure info."""
    langgraph_graph = graph.get_graph()

    print("\n" + "=" * 70)
    print("RESUME ASSISTANT - LANGGRAPH VISUALIZATION")
    print("=" * 70)

    print("\n📍 NODES:")
    print("-" * 50)
    node_names = list(langgraph_graph.nodes.keys())
    for i, name in enumerate(node_names, 1):
        print(f"  {i}. {name}")

    print("\n🔗 EDGES (with conditions):")
    print("-" * 50)
    print("  intake --> LLM_ROUTER (conditional)")
    print("    LLM_ROUTER decides based on user intent:")
    print("      → extract_resume")
    print("      → generate_feedback")
    print("      → interview_prep")
    print("      → finalize_resume")
    print("      → END")
    print("  extract_resume --> validate_resume")
    print("  validate_resume --> END")
    print("  generate_feedback --> END")
    print("  interview_prep --> END")
    print("  finalize_resume --> END")

    print("\n📊 GRAPH STATE SCHEMA:")
    print("-" * 50)
    print("""
  ResumeAssistantState {
    messages: Annotated[Messages, add_messages]
    resume_info: ResumeInfo
    interview_context: InterviewContext
    metadata: ConversationMetadata
    needs_resume_review: bool
    is_interview_mode: bool
    resume_complete: bool
    error: str | None
    retry_count: int
    context_window_used: int
  }
    """)

    return langgraph_graph


def main():
    """Generate and display the graph visualization."""
    print("\n⏳ Building graph...")

    graph = create_resume_assistant_graph()
    langgraph_graph = graph.get_graph()

    # Print node/edge info
    print_graph_info(graph)

    # Generate Mermaid diagram
    try:
        mermaid_code = langgraph_graph.draw_mermaid()
        print("\n🌊 MERMAID DIAGRAM CODE:")
        print("-" * 50)
        print(mermaid_code)
        print("-" * 50)

        # Save as interactive HTML
        save_mermaid_html(mermaid_code)
        print("\n✨ Open graph_visualization.html in your browser for interactive view!")

    except Exception as e:
        print(f"\n⚠ Could not generate mermaid diagram: {e}")

    # Try ASCII art
    try:
        ascii_graph = langgraph_graph.draw_ascii()
        print("\n📝 ASCII DIAGRAM:")
        print("-" * 50)
        print(ascii_graph)
    except Exception as e:
        print(f"\n⚠ Could not generate ASCII: {e}")

    print("\n" + "=" * 70)
    print("Visualization complete! Check graph_visualization.html for interactive view.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()