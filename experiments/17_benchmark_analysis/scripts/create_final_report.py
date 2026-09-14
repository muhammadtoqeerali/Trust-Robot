from pathlib import Path
import pandas as pd


ROOT = Path(
    "experiments/17_benchmark_analysis/results"
)


TABLES = ROOT / "tables"

OUT = ROOT / "final_report"


def main():

    OUT.mkdir(
        parents=True,
        exist_ok=True
    )


    master = pd.read_csv(
        TABLES / "final_master_results.csv"
    )


    robustness = pd.read_csv(
        TABLES / "robustness_summary.csv"
    )


    efficiency = pd.read_csv(
        TABLES / "efficiency_summary.csv"
    )


    pareto = pd.read_csv(
        TABLES / "pareto_analysis.csv"
    )


    # ----------------------------
    # Ranking tables
    # ----------------------------

    master.sort_values(
        "accuracy",
        ascending=False
    ).to_csv(
        OUT / "model_accuracy_ranking.csv",
        index=False
    )


    robustness.sort_values(
        "reliability_score",
        ascending=False
    ).to_csv(
        OUT / "model_reliability_ranking.csv",
        index=False
    )


    efficiency.sort_values(
        "accuracy_per_million_params",
        ascending=False
    ).to_csv(
        OUT / "model_efficiency_ranking.csv",
        index=False
    )


    pareto.to_csv(
        OUT / "pareto_analysis.csv",
        index=False
    )


    # ----------------------------
    # Generate markdown summary
    # ----------------------------

    best_accuracy = master.iloc[
        master["accuracy"].idxmax()
    ]


    best_reliability = robustness.iloc[
        robustness["reliability_score"].idxmax()
    ]


    best_efficiency = efficiency.iloc[
        efficiency["accuracy_per_million_params"].idxmax()
    ]


    pareto_models = pareto[
        pareto["pareto_optimal"] == True
    ]["model"].tolist()


    report = f"""
# IMU Reliability Benchmark Final Report


## Benchmark Overview

Models evaluated:
{len(master)}

Evaluation dimensions:

- Clean classification performance
- Reliability under IMU corruption
- Efficiency
- Pareto deployment tradeoff


## Best Clean Performance


Model:

{best_accuracy['model']}


Accuracy:

{best_accuracy['accuracy']:.4f}


Macro F1:

{best_accuracy['macro_f1']:.4f}


## Best Reliability Score


Model:

{best_reliability['model']}


Reliability Score:

{best_reliability['reliability_score']:.4f}


## Best Efficiency


Model:

{best_efficiency['model']}


Accuracy per Million Parameters:

{best_efficiency['accuracy_per_million_params']:.4f}


## Pareto Optimal Models


{chr(10).join(
    "- " + x for x in pareto_models
)}


## Research Interpretation


The benchmark demonstrates that clean accuracy,
robustness under corruption, and computational efficiency
represent different optimization objectives.


Therefore model selection should depend on the
deployment requirement rather than a single metric.


"""


    (OUT / "executive_summary.md").write_text(
        report
    )


    print(report)

    print()

    print(
        "FINAL_REPORT_CREATED=True"
    )


if __name__ == "__main__":
    main()
