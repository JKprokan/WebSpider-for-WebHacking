from pyvis.network import Network
import sqlite3
import os
import json
from urllib.parse import urlparse

def generate_interactive_graph(db_path, url, output_html=None):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT link, parent, depth, input_fields FROM crawl_links")
    rows = cursor.fetchall()
    conn.close()

    print(f"불러온 링크 수: {len(rows)}")

    net = Network(height="900px", width="100%", bgcolor="#ffffff", font_color="black", directed=True)
    
    # 계층적 레이아웃 설정
    net.set_options("""
    {
      "layout": {
        "hierarchical": {
          "enabled": true,
          "levelSeparation": 150,
          "nodeSpacing": 100,
          "treeSpacing": 200,
          "direction": "LR",
          "sortMethod": "directed"
        }
      },
      "physics": {
        "enabled": true,
        "hierarchicalRepulsion": {
          "nodeDistance": 120
        },
        "solver": "hierarchicalRepulsion"
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

        # 노드 색상 및 크기 조정 (depth 대신 다른 기준으로 변경 가능)
        color = "#3498db" # 기본 색상
        if has_input:
            color = "#e74c3c" # 입력 필드가 있으면 강조
        if depth == 0:
            color = "#2ecc71" # 시작 URL은 다른 색상

        size = 22 if depth == 0 else max(16 - depth * 2, 6)
        shape = "star" if depth == 0 else "dot"
        display_label = link if len(link) <= 40 else link[:37] + "..."

        if has_input:
            input_fields_str = json.dumps(input_fields, indent=2)
        else:
            input_fields_str = "No"

        title = f"""
        Link:{link}
        Depth:{depth}
        Input Fields:{input_fields_str}
        """

        if link not in added_nodes:
            net.add_node(link, label=display_label, color=color, title=title, shape=shape, size=size)
            added_nodes.add(link)

        if parent and parent not in added_nodes:
            # 부모 노드가 아직 추가되지 않았다면 추가 (레이블은 비워두고 나중에 채워질 수 있음)
            net.add_node(parent, label=" ", color="#bdc3c7", title=f"Parent: {parent}", size=10)
            added_nodes.add(parent)

        if parent:
            net.add_edge(parent, link)

    if output_html is None:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.replace(":", "_").replace(".", "_")
        output_html = os.path.join("data", f"{domain}_graph.html")

    net.write_html(output_html)
    print(f"시각화 완료: {output_html}")
