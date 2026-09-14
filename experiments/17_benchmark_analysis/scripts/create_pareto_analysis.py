from pathlib import Path
import pandas as pd


ROOT = Path(
    "experiments/17_benchmark_analysis/results"
)


INPUT = ROOT / "tables/final_master_results.csv"

OUTPUT = ROOT / "tables/pareto_analysis.csv"


def normalize(series):

    return (
        series - series.min()
    ) / (
        series.max() - series.min() + 1e-12
    )


def main():

    df = pd.read_csv(INPUT)


    df["accuracy_norm"] = normalize(
        df["accuracy"]
    )


    df["reliability_norm"] = normalize(
        df["reliability_mean"]
    )


    # lower latency and fewer parameters are better

    df["latency_norm"] = 1 - normalize(
        df["latency_ms_per_sample"]
    )


    df["parameter_norm"] = 1 - normalize(
        df["parameters"]
    )


    df["efficiency_score"] = (
        0.5 * df["latency_norm"]
        +
        0.5 * df["parameter_norm"]
    )


    df["deployment_score"] = (
        0.35 * df["accuracy_norm"]
        +
        0.35 * df["reliability_norm"]
        +
        0.30 * df["efficiency_score"]
    )


    # simple Pareto dominance test

    pareto = []


    values = df[
        [
            "accuracy",
            "reliability_mean",
            "efficiency_score"
        ]
    ].values


    for i in range(len(df)):

        dominated = False


        for j in range(len(df)):

            if i == j:
                continue


            better_or_equal = (
                values[j] >= values[i]
            ).all()


            strictly_better = (
                values[j] > values[i]
            ).any()


            if (
                better_or_equal
                and strictly_better
            ):
                dominated = True
                break


        pareto.append(
            not dominated
        )


    df["pareto_optimal"] = pareto


    cols = [
        "model",
        "accuracy",
        "macro_f1",
        "reliability_mean",
        "latency_ms_per_sample",
        "parameters",
        "model_size_mb",
        "efficiency_score",
        "deployment_score",
        "pareto_optimal"
    ]


    result = df[cols].sort_values(
        "deployment_score",
        ascending=False
    )


    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    result.to_csv(
        OUTPUT,
        index=False
    )


    print(result)

    print()

    print(
        "PARETO_ANALYSIS_CREATED=True"
    )


if __name__ == "__main__":
    main()
