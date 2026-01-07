import sys
import os
from pathlib import Path

# Add the project root to the python path so imports work correctly
sys.path.insert(0, str(Path(__file__).parent))

from src.agent.graph import build_graph

def visualize():
    print("🎨 Generating Agent Workflow Visualization...")
    print("-" * 50)
    
    try:
        # 1. Compile the Graph
        # This loads your actual LangGraph structure
        graph = build_graph()
        
        # 2. Generate Mermaid Definition (Text)
        # This string describes the graph nodes and edges
        mermaid_source = graph.get_graph().draw_mermaid()
        
        # 3. Save Mermaid File (.mmd)
        output_mmd = Path("agent_flow.mmd")
        with open(output_mmd, "w", encoding="utf-8") as f:
            f.write(mermaid_source)
            
        print(f"✅ Mermaid Definition saved to: {output_mmd.name}")
        print("   👉 You can view/edit this at https://mermaid.live")

        # 4. Generate PNG Image
        # Note: This requires 'graphviz' to be installed on your system.
        # If it fails, we fall back gracefully to the .mmd file.
        print("\n🖼️  Attempting to generate PNG image...")
        try:
            png_data = graph.get_graph().draw_mermaid_png()
            output_png = Path("agent_flow.png")
            with open(output_png, "wb") as f:
                f.write(png_data)
            print(f"✅ Graph Image saved to: {output_png.name}")
            
            # Attempt to open the file automatically based on OS
            try:
                if os.name == 'nt':  # Windows
                    os.startfile(output_png)
                elif sys.platform == 'darwin':  # macOS
                    os.system(f"open {output_png}")
                else:  # Linux
                    os.system(f"xdg-open {output_png}")
                print("   (Opened image in default viewer)")
            except Exception:
                pass # Ignore if we can't auto-open
                
        except Exception as e:
            print(f"⚠️  Could not generate PNG automatically.")
            print(f"   Reason: {e}")
            print("   (This usually means 'graphviz' is not installed on your system)")
            print("   Don't worry! You can still use the 'agent_flow.mmd' file generated above.")

    except Exception as e:
        print(f"❌ Error building graph: {e}")
    
    print("-" * 50)

if __name__ == "__main__":
    visualize()