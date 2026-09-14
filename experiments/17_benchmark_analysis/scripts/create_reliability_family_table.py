
from pathlib import Path
import json
import pandas as pd


ROOT = Path(
    "results/benchmark_v1/UCI_HAR/reliability_v2"
)


OUTPUT = Path(
    "experiments/17_benchmark_analysis/results/tables/reliability_family_analysis.csv"
)


def main():

    rows = []


    for model_dir in sorted(ROOT.iterdir()):

        if not model_dir.is_dir():
            continue


        model = model_dir.name


        for seed_dir in sorted(model_dir.iterdir()):

            summary_file = (
                seed_dir /
                "reliability_summary_v2.json"
            )


            cases_file = (
                seed_dir /
                "reliability_cases_v2.json"
            )


            if not cases_file.exists():
                continue


            cases = json.loads(
                cases_file.read_text()
            )


            for case in cases:

                rows.append(
                    {

                        "model":
                            model,

                        "seed":
                            seed_dir.name,

                        "family":
                            case["family"],

                        "corruption":
                            case["corruption"],

                        "reliability_score":
                            case["reliability_score"],

                        "corrupted_accuracy":
                            case["corrupted_metrics"]["accuracy"],

                        "corrupted_macro_f1":
                            case["corrupted_metrics"]["macro_f1"],

                        "accuracy_degradation":
                            case["degradation"]["accuracy_degradation"],

                        "macro_f1_degradation":
                            case["degradation"]["macro_f1_degradation"]

                    }
                )


    df = pd.DataFrame(rows)


    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    df.to_csv(
        OUTPUT,
        index=False
    )


    print(
        df.groupby(
            [
                "model",
                "family"
            ]
        )
        [
            [
                "reliability_score",
                "corrupted_accuracy",
                "accuracy_degradation"
            ]
        ]
        .mean()
        .to_string()
    )


    print(
        "RELIABILITY_FAMILY_TABLE_CREATED=True"
    )


if __name__=="__main__":
    main()

