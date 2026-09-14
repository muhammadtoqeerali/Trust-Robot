
from pathlib import Path
import json
import pandas as pd


PERFORMANCE = Path(
    "experiments/17_benchmark_analysis/results/tables/performance_summary.csv"
)


REL_ROOT = Path(
    "results/benchmark_v1/UCI_HAR/reliability_v2"
)


OUTPUT = Path(
    "experiments/17_benchmark_analysis/results/tables/final_master_results.csv"
)


def main():


    perf = pd.read_csv(
        PERFORMANCE
    )


    rows = []


    for model_dir in sorted(REL_ROOT.iterdir()):

        if not model_dir.is_dir():
            continue


        model = model_dir.name


        scores = []


        for seed_dir in sorted(model_dir.iterdir()):

            summary_file = (
                seed_dir /
                "reliability_summary_v2.json"
            )


            if not summary_file.exists():
                continue


            data=json.loads(
                summary_file.read_text()
            )


            overall=data["overall"]


            scores.append(
                {
                    "seed":
                        seed_dir.name.replace(
                            "seed_",
                            ""
                        ),

                    "reliability_score":
                        overall["reliability_score"],

                    "corrupted_accuracy":
                        overall["corrupted_accuracy"],

                    "corrupted_macro_f1":
                        overall["corrupted_macro_f1"],

                    "accuracy_degradation":
                        overall["relative_accuracy_degradation"],

                    "macro_f1_degradation":
                        overall["relative_macro_f1_degradation"]
                }
            )


        if scores:

            df=pd.DataFrame(scores)


            rows.append(
                {

                    "model":
                        model,

                    "reliability_mean":
                        df.reliability_score.mean(),

                    "reliability_std":
                        df.reliability_score.std(),

                    "corrupted_accuracy_mean":
                        df.corrupted_accuracy.mean(),

                    "accuracy_degradation_mean":
                        df.accuracy_degradation.mean(),

                    "macro_f1_degradation_mean":
                        df.macro_f1_degradation.mean()

                }
            )


    rel=pd.DataFrame(rows)


    final = perf.merge(
        rel,
        on="model",
        how="inner"
    )


    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    final.to_csv(
        OUTPUT,
        index=False
    )


    print(
        final.to_string()
    )


    print(
        "MASTER_RESULTS_CREATED=True"
    )



if __name__=="__main__":
    main()

