
import json
from pathlib import Path
import pandas as pd


ROOT = Path(".")


FINAL_DIR = ROOT / "results/final_analysis"
FINAL_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# --------------------------------------------------
# Load clean performance
# --------------------------------------------------

clean_rows = []


for f in Path("results/model_comparison").glob(
    "*_clean_comparison.json"
):

    dataset = f.stem.replace(
        "_clean_comparison",
        ""
    )

    data = json.loads(
        f.read_text()
    )


    for model, metrics in data.items():

        clean_rows.append({

            "dataset":
                dataset,

            "model":
                model,

            "accuracy":
                metrics["accuracy"],

            "macro_f1":
                metrics["macro_f1"]

        })



clean_df = pd.DataFrame(
    clean_rows
)


clean_df.to_csv(
    FINAL_DIR /
    "clean_performance_table.csv",
    index=False
)



# --------------------------------------------------
# Robustness analysis
# --------------------------------------------------

robust_rows=[]


for f in Path("results/robustness_comparison").glob(
    "*_model_robustness.json"
):

    dataset=f.stem.replace(
        "_model_robustness",
        ""
    )


    data=json.loads(
        f.read_text()
    )


    for model,conditions in data.items():

        clean_acc = conditions["clean"]["accuracy"]

        drops=[]

        corrupted_acc=[]


        for name,value in conditions.items():

            if name=="clean":
                continue


            drops.append(
                value["accuracy_drop"]
            )

            corrupted_acc.append(
                value["accuracy"]
            )


        robust_rows.append({

            "dataset":
                dataset,

            "model":
                model,

            "clean_accuracy":
                clean_acc,

            "average_accuracy_drop":
                sum(drops)/len(drops),

            "average_corrupted_accuracy":
                sum(corrupted_acc)/len(corrupted_acc),

            "robustness_score":
                (
                    clean_acc +
                    sum(corrupted_acc)/len(corrupted_acc)
                )/2

        })



robust_df=pd.DataFrame(
    robust_rows
)


robust_df.to_csv(
    FINAL_DIR /
    "robustness_summary_table.csv",
    index=False
)



ranking = (
    robust_df
    .groupby("model")
    ["robustness_score"]
    .mean()
    .sort_values(
        ascending=False
    )
    .reset_index()
)


ranking.to_csv(
    FINAL_DIR /
    "robustness_score_ranking.csv",
    index=False
)



# --------------------------------------------------
# Efficiency
# --------------------------------------------------

eff=json.loads(
    Path(
        "results/efficiency/efficiency_report.json"
    ).read_text()
)


eff_rows=[]


for model,values in eff.items():

    row={
        "model":
            model
    }

    row.update(values)

    eff_rows.append(row)



pd.DataFrame(
    eff_rows
).to_csv(
    FINAL_DIR /
    "efficiency_summary_table.csv",
    index=False
)



# --------------------------------------------------
# Final JSON report
# --------------------------------------------------

report={

    "clean_performance":
        clean_rows,

    "robustness_summary":
        robust_rows,

    "robustness_ranking":
        ranking.to_dict(
            orient="records"
        ),

    "efficiency":
        eff_rows

}


(
FINAL_DIR /
"final_comparison_report.json"
).write_text(
    json.dumps(
        report,
        indent=2
    )
)



print(
    "FINAL_ANALYSIS_COMPLETE=True"
)

print(
    "OUTPUT=",
    FINAL_DIR
)

