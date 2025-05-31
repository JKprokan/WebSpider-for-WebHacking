from pyvis.network import Network
import sqlite3
import os
import json

def generate_interactive_graph(db_path="data/crawl_links.db", output_html="data/link_graph.html"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT link, parent, depth, input_fields FROM crawl_links")
    rows = cursor.fetchall()
    conn.close()

    print(f"불러온 링크 수: {len(rows)}")

    net = Network(height="900px", width="100%", bgcolor="#ffffff", font_color="black", directed=True)
    net.barnes_hut()
    net.set_options("""
    var options = {
      "physics": {
        "enabled": true
      },
      "nodes": {
        "scaling": {
          "min": 5,
          "max": 25
        },
        "font": {
          "size": 12,
          "face": "arial"
        },
        "borderWidth": 1,
        "shadow": true
      },
      "edges": {
        "arrows": {
          "to": {
            "enabled": true
          }
        },
        "smooth": {
          "enabled": true
        }
      },
      "interaction": {
        "hover": true,
        "zoomView": true,
        "dragView": true,
        "dragNodes": true
      }
    }
    """)

    added_nodes = set()

    for link, parent, depth, input_fields_json in rows:
        try:
            input_fields = json.loads(input_fields_json)
        except:
            input_fields = []

        has_input = bool(input_fields)

        depth_colors = {
            0: "#e74c3c",
            1: "#3498db",
            2: "#f39c12",
            3: "#2ecc71",
            4: "#9b59b6",
            5: "#1abc9c"
        }
        color = depth_colors.get(depth, "#95a5a6") if has_input else "#bdc3c7"

        size = 22 if depth == 0 else max(16 - depth * 2, 6)
        shape = "star" if depth == 0 else "dot"
        display_label = link if len(link) <= 40 else link[:37] + "..."

        if has_input:
            input_fields_str = json.dumps(input_fields, indent=2)
        else:
            input_fields_str = "No"

        title = f"""
        Link:{link}\n
        Depth:{depth}\n
        Input Fields:{input_fields_str}
        """

        if link not in added_nodes:
            net.add_node(link, label=display_label, color=color, title=title, shape=shape, size=size)
            added_nodes.add(link)

        if parent and parent not in added_nodes:
            net.add_node(parent, label=" ", color="#7f8c8d", title="(Unlisted parent)", size=10)
            added_nodes.add(parent)

        if parent:
            net.add_edge(parent, link)

    net.write_html(output_html)
    print(f"시각화 완료: {output_html}")
