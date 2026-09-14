import json
from pathlib import Path
import pandas as pd


RESULT_DIR = Path(
    "results/reliability_v2"
)

OUTPUT_DIR = Path(
    "results/cross_dataset_analysis"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


DATASETS = [
    "UCI_HAR",
    "PAMAP2",
    "DSADS",
    "MotionSense"
]


# -------------------------------------------------
# Load clean performance
# -------------------------------------------------

clean_rows = []


for ds in DATASETS:

    path = RESULT_DIR / f"reliability_cnn_v2_{ds}_results.json"

    data = json.loads(
        path.read_text()
    )

    clean_rows.append(
        {
            "dataset": ds,
            "accuracy": data["accuracy"],
            "macro_f1": data["macro_f1"],
            "parameters": data["parameters"],
            "training_seconds": data["training_seconds"]
        }
    )


clean_df = pd.DataFrame(
    clean_rows
)


clean_df.to_csv(
    OUTPUT_DIR / "reliability_v2_clean_summary.csv",
    index=False
)


# -------------------------------------------------
# Robustness matrix
# -------------------------------------------------

robust_rows = []


for ds in DATASETS:

    path = RESULT_DIR / f"reliability_v2_{ds}_robustness.json"

    text = path.read_text()

    # Extract only JSON object
    start = text.find("{")
    end = text.rfind("}") + 1

    text = text[start:end]

    data = json.loads(
        text
    )


    row = {
        "dataset": ds
    }


    for corruption, values in data.items():

        if corruption == "clean":
            continue

        row[
            corruption + "_accuracy"
        ] = values["accuracy"]

        row[
            corruption + "_drop"
        ] = values["accuracy_drop"]


    robust_rows.append(row)



robust_df = pd.DataFrame(
    robust_rows
)


robust_df.to_csv(
    OUTPUT_DIR / "reliability_v2_robustness_matrix.csv",
    index=False
)



# -------------------------------------------------
# Reliability score
# -------------------------------------------------

score_rows=[]


for _,row in robust_df.iterrows():

    ds=row["dataset"]

    clean_acc = (
        clean_df[
            clean_df.dataset == ds
        ]
        .accuracy
        .values[0]
    )


    drops=[]


    for col in row.index:

        if col.endswith("_drop"):

            drops.append(
                row[col]
            )


    mean_drop=sum(drops)/len(drops)


    reliability = (
        1 -
        mean_drop / clean_acc
    )


    score_rows.append(
        {
            "dataset": ds,
            "mean_accuracy_drop": mean_drop,
            "clean_accuracy": clean_acc,
            "reliability_score": reliability
        }
    )


score_df=pd.DataFrame(
    score_rows
)


score_df=score_df.sort_values(
    "reliability_score",
    ascending=False
)


score_df.to_csv(
    OUTPUT_DIR / "reliability_v2_dataset_ranking.csv",
    index=False
)


# -------------------------------------------------
# Complete report
# -------------------------------------------------

report={

    "clean_performance":
        clean_rows,

    "robustness":
        robust_rows,

    "reliability_ranking":
        score_rows

}


(
OUTPUT_DIR /
"reliability_v2_cross_dataset_report.json"
).write_text(
    json.dumps(
        report,
        indent=2
    )
)


print(
    "CROSS_DATASET_RELIABILITY_ANALYSIS_COMPLETE=True"
)

print(
    "DATASETS=",
    DATASETS
)

