import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt


INPUT_DIR = Path(
    "results/cross_dataset_analysis"
)

OUTPUT_DIR = Path(
    "results/figures"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# -------------------------------------------------
# Figure 1
# Clean accuracy
# -------------------------------------------------

clean = pd.read_csv(
    INPUT_DIR /
    "reliability_v2_clean_summary.csv"
)


plt.figure(
    figsize=(8,5)
)

plt.bar(
    clean["dataset"],
    clean["accuracy"]
)

plt.ylabel(
    "Accuracy"
)

plt.xlabel(
    "Dataset"
)

plt.title(
    "Reliability CNN v2 Clean Performance"
)

plt.xticks(
    rotation=45
)

plt.tight_layout()

plt.savefig(
    OUTPUT_DIR /
    "fig1_clean_accuracy.png",
    dpi=300
)

plt.close()



# -------------------------------------------------
# Figure 2
# Robustness heatmap
# -------------------------------------------------

robust = pd.read_csv(
    INPUT_DIR /
    "reliability_v2_robustness_matrix.csv"
)


drop_columns = [
    c for c in robust.columns
    if c.endswith("_drop")
]


heat = robust[
    ["dataset"] + drop_columns
]


heat = heat.set_index(
    "dataset"
)


plt.figure(
    figsize=(10,5)
)


plt.imshow(
    heat.values,
    aspect="auto"
)


plt.colorbar(
    label="Accuracy drop"
)


plt.xticks(
    range(len(heat.columns)),
    [
        c.replace("_drop","")
        for c in heat.columns
    ],
    rotation=45,
    ha="right"
)


plt.yticks(
    range(len(heat.index)),
    heat.index
)


plt.title(
    "Reliability CNN v2 Robustness Degradation"
)


plt.tight_layout()


plt.savefig(
    OUTPUT_DIR /
    "fig2_robustness_heatmap.png",
    dpi=300
)

plt.close()



# -------------------------------------------------
# Figure 3
# Reliability ranking
# -------------------------------------------------

ranking = pd.read_csv(
    INPUT_DIR /
    "reliability_v2_dataset_ranking.csv"
)


plt.figure(
    figsize=(8,5)
)


plt.bar(
    ranking["dataset"],
    ranking["reliability_score"]
)


plt.ylabel(
    "Reliability Score"
)

plt.xlabel(
    "Dataset"
)

plt.title(
    "Cross Dataset Reliability Ranking"
)


plt.xticks(
    rotation=45
)

plt.tight_layout()


plt.savefig(
    OUTPUT_DIR /
    "fig3_reliability_ranking.png",
    dpi=300
)


plt.close()



print(
    "RELIABILITY_FIGURES_GENERATED=True"
)

print(
    "OUTPUT=",
    OUTPUT_DIR
)

