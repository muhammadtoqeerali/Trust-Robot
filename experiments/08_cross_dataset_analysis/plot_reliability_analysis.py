import json
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


ROOT = Path(".")
RESULT_DIR = ROOT / "results" / "cross_dataset_analysis"

FIG_DIR = RESULT_DIR / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)


def load_data():

    degradation = pd.read_csv(
        RESULT_DIR / "robustness_degradation_matrix.csv"
    )

    clean = pd.read_csv(
        RESULT_DIR / "clean_performance_summary.csv"
    )

    with open(
        RESULT_DIR / "dataset_ranking.json"
    ) as f:
        ranking = json.load(f)

    return degradation, clean, ranking



def plot_heatmap(degradation):

    pivot = degradation.pivot(
        index="dataset",
        columns="corruption",
        values="accuracy_drop"
    )

    plt.figure(figsize=(10, 5))

    plt.imshow(
        pivot.values,
        aspect="auto"
    )

    plt.colorbar(
        label="Accuracy Drop"
    )

    plt.xticks(
        range(len(pivot.columns)),
        pivot.columns,
        rotation=45,
        ha="right"
    )

    plt.yticks(
        range(len(pivot.index)),
        pivot.index
    )

    plt.title(
        "Reliability V2 Robustness Degradation"
    )

    plt.tight_layout()

    path = FIG_DIR / "robustness_heatmap.png"

    plt.savefig(
        path,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()

    print("Saved:", path)



def plot_reliability_ranking(ranking):

    data = ranking[
        "dataset_average_reliability"
    ]

    datasets = [
        x[0]
        for x in data
    ]

    scores = [
        x[1]
        for x in data
    ]

    plt.figure(figsize=(8, 4))

    plt.bar(
        datasets,
        scores
    )

    plt.ylabel(
        "Average Reliability Score"
    )

    plt.title(
        "Cross Dataset Reliability Ranking"
    )

    plt.xticks(
        rotation=30
    )

    plt.tight_layout()

    path = FIG_DIR / "reliability_ranking.png"

    plt.savefig(
        path,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()

    print("Saved:", path)



def plot_clean_vs_corrupted(clean, degradation):

    datasets = clean["dataset"].tolist()

    clean_acc = clean["accuracy"].tolist()

    corrupted_avg = []

    for dataset in datasets:

        losses = degradation[
            degradation["dataset"] == dataset
        ]["accuracy_drop"]

        corrupted_avg.append(
            clean[
                clean["dataset"] == dataset
            ]["accuracy"].iloc[0]
            -
            losses.mean()
        )


    x = range(len(datasets))


    plt.figure(figsize=(8, 4))


    plt.plot(
        x,
        clean_acc,
        marker="o",
        label="Clean"
    )


    plt.plot(
        x,
        corrupted_avg,
        marker="o",
        label="Average Corrupted"
    )


    plt.xticks(
        x,
        datasets,
        rotation=30
    )


    plt.ylabel(
        "Accuracy"
    )

    plt.title(
        "Clean vs Corrupted Performance"
    )

    plt.legend()

    plt.tight_layout()


    path = FIG_DIR / "clean_vs_corrupted_performance.png"


    plt.savefig(
        path,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()

    print("Saved:", path)



def main():

    degradation, clean, ranking = load_data()

    plot_heatmap(
        degradation
    )

    plot_reliability_ranking(
        ranking
    )

    plot_clean_vs_corrupted(
        clean,
        degradation
    )

    print(
        "EXPERIMENT_08_VISUALIZATION_COMPLETE=True"
    )


if __name__ == "__main__":
    main()PY
cat > experiments/08_cross_dataset_analysis/plot_reliability_analysis.py <<'PY'
import json
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


ROOT = Path(".")
RESULT_DIR = ROOT / "results" / "cross_dataset_analysis"

FIG_DIR = RESULT_DIR / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)


def load_data():

    degradation = pd.read_csv(
        RESULT_DIR / "robustness_degradation_matrix.csv"
    )

    clean = pd.read_csv(
        RESULT_DIR / "clean_performance_summary.csv"
    )

    with open(
        RESULT_DIR / "dataset_ranking.json"
    ) as f:
        ranking = json.load(f)

    return degradation, clean, ranking



def plot_heatmap(degradation):

    pivot = degradation.pivot(
        index="dataset",
        columns="corruption",
        values="accuracy_drop"
    )

    plt.figure(figsize=(10, 5))

    plt.imshow(
        pivot.values,
        aspect="auto"
    )

    plt.colorbar(
        label="Accuracy Drop"
    )

    plt.xticks(
        range(len(pivot.columns)),
        pivot.columns,
        rotation=45,
        ha="right"
    )

    plt.yticks(
        range(len(pivot.index)),
        pivot.index
    )

    plt.title(
        "Reliability V2 Robustness Degradation"
    )

    plt.tight_layout()

    path = FIG_DIR / "robustness_heatmap.png"

    plt.savefig(
        path,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()

    print("Saved:", path)



def plot_reliability_ranking(ranking):

    data = ranking[
        "dataset_average_reliability"
    ]

    datasets = [
        x[0]
        for x in data
    ]

    scores = [
        x[1]
        for x in data
    ]

    plt.figure(figsize=(8, 4))

    plt.bar(
        datasets,
        scores
    )

    plt.ylabel(
        "Average Reliability Score"
    )

    plt.title(
        "Cross Dataset Reliability Ranking"
    )

    plt.xticks(
        rotation=30
    )

    plt.tight_layout()

    path = FIG_DIR / "reliability_ranking.png"

    plt.savefig(
        path,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()

    print("Saved:", path)



def plot_clean_vs_corrupted(clean, degradation):

    datasets = clean["dataset"].tolist()

    clean_acc = clean["accuracy"].tolist()

    corrupted_avg = []

    for dataset in datasets:

        losses = degradation[
            degradation["dataset"] == dataset
        ]["accuracy_drop"]

        corrupted_avg.append(
            clean[
                clean["dataset"] == dataset
            ]["accuracy"].iloc[0]
            -
            losses.mean()
        )


    x = range(len(datasets))


    plt.figure(figsize=(8, 4))


    plt.plot(
        x,
        clean_acc,
        marker="o",
        label="Clean"
    )


    plt.plot(
        x,
        corrupted_avg,
        marker="o",
        label="Average Corrupted"
    )


    plt.xticks(
        x,
        datasets,
        rotation=30
    )


    plt.ylabel(
        "Accuracy"
    )

    plt.title(
        "Clean vs Corrupted Performance"
    )

    plt.legend()

    plt.tight_layout()


    path = FIG_DIR / "clean_vs_corrupted_performance.png"


    plt.savefig(
        path,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()

    print("Saved:", path)



def main():

    degradation, clean, ranking = load_data()

    plot_heatmap(
        degradation
    )

    plot_reliability_ranking(
        ranking
    )

    plot_clean_vs_corrupted(
        clean,
        degradation
    )

    print(
        "EXPERIMENT_08_VISUALIZATION_COMPLETE=True"
    )


if __name__ == "__main__":
    main()
cat > experiments/08_cross_dataset_analysis/plot_reliability_analysis.py <<'PY'
import json
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


ROOT = Path(".")
RESULT_DIR = ROOT / "results" / "cross_dataset_analysis"

FIG_DIR = RESULT_DIR / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)


def load_data():

    degradation = pd.read_csv(
        RESULT_DIR / "robustness_degradation_matrix.csv"
    )

    clean = pd.read_csv(
        RESULT_DIR / "clean_performance_summary.csv"
    )

    with open(
        RESULT_DIR / "dataset_ranking.json"
    ) as f:
        ranking = json.load(f)

    return degradation, clean, ranking



def plot_heatmap(degradation):

    pivot = degradation.pivot(
        index="dataset",
        columns="corruption",
        values="accuracy_drop"
    )

    plt.figure(figsize=(10, 5))

    plt.imshow(
        pivot.values,
        aspect="auto"
    )

    plt.colorbar(
        label="Accuracy Drop"
    )

    plt.xticks(
        range(len(pivot.columns)),
        pivot.columns,
        rotation=45,
        ha="right"
    )

    plt.yticks(
        range(len(pivot.index)),
        pivot.index
    )

    plt.title(
        "Reliability V2 Robustness Degradation"
    )

    plt.tight_layout()

    path = FIG_DIR / "robustness_heatmap.png"

    plt.savefig(
        path,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()

    print("Saved:", path)



def plot_reliability_ranking(ranking):

    data = ranking[
        "dataset_average_reliability"
    ]

    datasets = [
        x[0]
        for x in data
    ]

    scores = [
        x[1]
        for x in data
    ]

    plt.figure(figsize=(8, 4))

    plt.bar(
        datasets,
        scores
    )

    plt.ylabel(
        "Average Reliability Score"
    )

    plt.title(
        "Cross Dataset Reliability Ranking"
    )

    plt.xticks(
        rotation=30
    )

    plt.tight_layout()

    path = FIG_DIR / "reliability_ranking.png"

    plt.savefig(
        path,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()

    print("Saved:", path)



def plot_clean_vs_corrupted(clean, degradation):

    datasets = clean["dataset"].tolist()

    clean_acc = clean["accuracy"].tolist()

    corrupted_avg = []

    for dataset in datasets:

        losses = degradation[
            degradation["dataset"] == dataset
        ]["accuracy_drop"]

        corrupted_avg.append(
            clean[
                clean["dataset"] == dataset
            ]["accuracy"].iloc[0]
            -
            losses.mean()
        )


    x = range(len(datasets))


    plt.figure(figsize=(8, 4))


    plt.plot(
        x,
        clean_acc,
        marker="o",
        label="Clean"
    )


    plt.plot(
        x,
        corrupted_avg,
        marker="o",
        label="Average Corrupted"
    )


    plt.xticks(
        x,
        datasets,
        rotation=30
    )


    plt.ylabel(
        "Accuracy"
    )

    plt.title(
        "Clean vs Corrupted Performance"
    )

    plt.legend()

    plt.tight_layout()


    path = FIG_DIR / "clean_vs_corrupted_performance.png"


    plt.savefig(
        path,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()

    print("Saved:", path)



def main():

    degradation, clean, ranking = load_data()

    plot_heatmap(
        degradation
    )

    plot_reliability_ranking(
        ranking
    )

    plot_clean_vs_corrupted(
        clean,
        degradation
    )

    print(
        "EXPERIMENT_08_VISUALIZATION_COMPLETE=True"
    )


if __name__ == "__main__":
    main()
cat > experiments/08_cross_dataset_analysis/plot_reliability_analysis.py <<'PY'
import json
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


ROOT = Path(".")
RESULT_DIR = ROOT / "results" / "cross_dataset_analysis"

FIG_DIR = RESULT_DIR / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)


def load_data():

    degradation = pd.read_csv(
        RESULT_DIR / "robustness_degradation_matrix.csv"
    )

    clean = pd.read_csv(
        RESULT_DIR / "clean_performance_summary.csv"
    )

    with open(
        RESULT_DIR / "dataset_ranking.json"
    ) as f:
        ranking = json.load(f)

    return degradation, clean, ranking



def plot_heatmap(degradation):

    pivot = degradation.pivot(
        index="dataset",
        columns="corruption",
        values="accuracy_drop"
    )

    plt.figure(figsize=(10, 5))

    plt.imshow(
        pivot.values,
        aspect="auto"
    )

    plt.colorbar(
        label="Accuracy Drop"
    )

    plt.xticks(
        range(len(pivot.columns)),
        pivot.columns,
        rotation=45,
        ha="right"
    )

    plt.yticks(
        range(len(pivot.index)),
        pivot.index
    )

    plt.title(
        "Reliability V2 Robustness Degradation"
    )

    plt.tight_layout()

    path = FIG_DIR / "robustness_heatmap.png"

    plt.savefig(
        path,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()

    print("Saved:", path)



def plot_reliability_ranking(ranking):

    data = ranking[
        "dataset_average_reliability"
    ]

    datasets = [
        x[0]
        for x in data
    ]

    scores = [
        x[1]
        for x in data
    ]

    plt.figure(figsize=(8, 4))

    plt.bar(
        datasets,
        scores
    )

    plt.ylabel(
        "Average Reliability Score"
    )

    plt.title(
        "Cross Dataset Reliability Ranking"
    )

    plt.xticks(
        rotation=30
    )

    plt.tight_layout()

    path = FIG_DIR / "reliability_ranking.png"

    plt.savefig(
        path,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()

    print("Saved:", path)



def plot_clean_vs_corrupted(clean, degradation):

    datasets = clean["dataset"].tolist()

    clean_acc = clean["accuracy"].tolist()

    corrupted_avg = []

    for dataset in datasets:

        losses = degradation[
            degradation["dataset"] == dataset
        ]["accuracy_drop"]

        corrupted_avg.append(
            clean[
                clean["dataset"] == dataset
            ]["accuracy"].iloc[0]
            -
            losses.mean()
        )


    x = range(len(datasets))


    plt.figure(figsize=(8, 4))


    plt.plot(
        x,
        clean_acc,
        marker="o",
        label="Clean"
    )


    plt.plot(
        x,
        corrupted_avg,
        marker="o",
        label="Average Corrupted"
    )


    plt.xticks(
        x,
        datasets,
        rotation=30
    )


    plt.ylabel(
        "Accuracy"
    )

    plt.title(
        "Clean vs Corrupted Performance"
    )

    plt.legend()

    plt.tight_layout()


    path = FIG_DIR / "clean_vs_corrupted_performance.png"


    plt.savefig(
        path,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()

    print("Saved:", path)



def main():

    degradation, clean, ranking = load_data()

    plot_heatmap(
        degradation
    )

    plot_reliability_ranking(
        ranking
    )

    plot_clean_vs_corrupted(
        clean,
        degradation
    )

    print(
        "EXPERIMENT_08_VISUALIZATION_COMPLETE=True"
    )


if __name__ == "__main__":
    main()
