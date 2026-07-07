"""
End-to-end run: load sample_chunks.jsonl -> run each chunk through the
LangGraph extraction pipeline -> persist graph + chroma -> run gap detection
-> print a summary -> optionally write a pyvis HTML view.

Usage:
    python main.py
    python main.py --chunks path/to/other_chunks.jsonl --no-viz
"""

import argparse
import json

from tqdm import tqdm

from extraction_pipeline import build_pipeline, run_pipeline_on_chunk
from gap_detection import detect_gaps, detect_missing_timestamps
from storage import G, save_graph


def load_chunks(path: str) -> list[dict]:
    chunks = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                chunks.append(json.loads(line))
    return chunks


def render_pyvis(graph, out_path: str = "graph_view.html") -> None:
    from pyvis.network import Network

    net = Network(height="800px", width="100%", directed=True, notebook=False)
    for node_id, data in graph.nodes(data=True):
        label = data.get("label", node_id)
        title = (
            f"type: {data.get('node_type')}\n"
            f"evidence: {data.get('evidence_type')}\n"
            f"confidence: {data.get('confidence')}\n"
            f"desc: {data.get('description')}"
        )
        color = {
            "decision": "#4C6EF5",
            "outcome": "#FA5252",
            "person": "#40C057",
            "skill": "#F59F00",
            "project": "#868E96",
        }.get(data.get("node_type"), "#ADB5BD")
        net.add_node(node_id, label=label, title=title, color=color)

    for u, v, data in graph.edges(data=True):
        net.add_edge(
            u,
            v,
            title=f"{data.get('edge_type')}: {data.get('description')}",
            label=data.get("edge_type"),
        )

    net.write_html(out_path)
    print(f"Wrote interactive graph view to {out_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunks", default="sample_chunks.jsonl")
    parser.add_argument("--no-viz", action="store_true", help="Skip pyvis HTML export")
    args = parser.parse_args()

    chunks = load_chunks(args.chunks)
    print(f"Loaded {len(chunks)} chunks from {args.chunks}")

    pipeline = build_pipeline()

    all_contradictions = []
    for chunk in tqdm(chunks, desc="Extracting"):
        result = run_pipeline_on_chunk(pipeline, chunk)
        all_contradictions.extend(result.get("contradictions", []))

    save_graph()
    print(f"\nGraph now has {G.number_of_nodes()} nodes and {G.number_of_edges()} edges.")

    print("\n--- Gap detection ---")
    gaps = detect_gaps(chunks)
    if gaps:
        for g in gaps:
            print(f"  SPARSE: project={g.project!r} period={g.period} chunk_count={g.chunk_count}")
    else:
        print("  No sparse (project, month) buckets found.")

    missing_ts = detect_missing_timestamps(chunks)
    if missing_ts:
        print(f"  {len(missing_ts)} chunk(s) with no timestamp at all: "
              f"{[c['chunk_id'] for c in missing_ts]}")

    print("\n--- Contradiction detection ---")
    if all_contradictions:
        for c in all_contradictions:
            print(f"  {c.node_id_a} <-> {c.node_id_b}: {c.note}")
    else:
        print("  No contradictions flagged.")

    if not args.no_viz:
        render_pyvis(G)


if __name__ == "__main__":
    main()