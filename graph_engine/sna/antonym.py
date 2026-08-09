import json
import os
import runpy


with open("./results/criticality_scores.json", "r", encoding="utf-8") as f:
    crit = json.load(f)

archetype = crit.get("archetype", "hub")
chain_subtype = crit.get("chain_subtype")

if archetype == "hub":
    script = "antonym_plot.py"
elif archetype == "chain" and chain_subtype == "causal":
    script = "antonym_chain.py"
else:
    script = None
    print(
        f"skipping antonym step: archetype={archetype!r} chain_subtype={chain_subtype!r}")

if script:
    runpy.run_path(os.path.join(os.path.dirname(
        __file__), script), run_name="__main__")
