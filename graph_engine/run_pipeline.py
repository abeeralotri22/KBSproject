import subprocess
import sys
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
SNA = os.path.join(ROOT, "sna")

steps = [
    (ROOT, "createandupdategraph.py"),
    (ROOT, "filter_graph.py"),
    (SNA,  "1_sna.py"),
    # (SNA,  "2_sna_impact.py"),
    # (SNA,  "sna_impact2.py"),
    (SNA,  "new_sna_impact2.py"),
    # (SNA,  "3_sna_edge_impact.py"),
    # (SNA,  "sna_edge_impact2.py"),
    (SNA,  "new_sna_edge_impact2.py"),
    # (SNA,  "4_sna_plot_graph.py"),
    # (SNA,  "sna_plot_graph.py"),
    (SNA,  "new_sna_plot_graph.py"),
    # (SNA,  "sna_plot_graph_filtered.py"),
    (SNA,  "new_sna_plot_graph_filtered.py"),
    (SNA,  "antonym.py"),
]

for cwd, script in steps:
    print(f"\n{'─'*50}")
    print(f"  {script}")
    print(f"{'─'*50}")
    result = subprocess.run([sys.executable, script], cwd=cwd)
    if result.returncode != 0:
        print(f"\nfailed {script} (exit code {result.returncode})")
        sys.exit(1)

print("\n succeeded ")
