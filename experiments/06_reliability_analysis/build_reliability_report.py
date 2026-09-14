import json
from pathlib import Path
import statistics


RESULT_DIR = Path(
    "results/reliability_model"
)

OUTPUT_DIR = Path(
    "results/final_analysis"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


datasets = [
    "UCI_HAR",
    "PAMAP2",
    "DSADS",
    "MotionSense"
]


clean_results = {}
robustness_results = {}


# ------------------------------------
# Load results
# ------------------------------------

for dataset in datasets:

    clean_file = RESULT_DIR / (
        f"reliability_cnn_{dataset}_results.json"
    )

    robust_file = RESULT_DIR / (
        f"reliability_cnn_{dataset}_robustness.json"
    )


    if clean_file.exists():

        clean_results[dataset] = json.loads(
            clean_file.read_text()
        )


    if robust_file.exists():

        text = robust_file.read_text()

        # remove possible print lines
        text = "\n".join(
            [
                x for x in text.splitlines()
                if not x.startswith("DATASET=")
                and not x.startswith("DEVICE=")
                and not x.startswith("RELIABILITY")
            ]
        )

        robustness_results[dataset] = json.loads(
            text
        )



# ------------------------------------
# Clean performance table
# ------------------------------------

clean_table = {}

for d,r in clean_results.items():

    clean_table[d] = {

        "accuracy":
            r["accuracy"],

        "macro_f1":
            r["macro_f1"],

        "parameters":
            r["parameters"],

        "training_seconds":
            r["training_seconds"]

    }



(OUTPUT_DIR/"clean_performance_table.json").write_text(
    json.dumps(
        clean_table,
        indent=2
    )
)



# ------------------------------------
# Robustness summary
# ------------------------------------

robust_summary={}


for dataset,result in robustness_results.items():

    robust_summary[dataset]={}


    for name,value in result.items():

        if (
            isinstance(value,dict)
            and
            "accuracy_drop" in value
        ):

            robust_summary[dataset][name]={
                "accuracy_drop":
                    value["accuracy_drop"],

                "accuracy":
                    value["accuracy"]
            }



(OUTPUT_DIR/"robustness_summary.json").write_text(
    json.dumps(
        robust_summary,
        indent=2
    )
)



# ------------------------------------
# Reliability ranking
# ------------------------------------

corruption_scores={}


for dataset,result in robust_summary.items():

    for corruption,data in result.items():

        corruption_scores.setdefault(
            corruption,
            []
        ).append(
            data["accuracy_drop"]
        )


ranking={}

for corruption,drops in corruption_scores.items():

    ranking[corruption]={

        "mean_accuracy_drop":
            statistics.mean(drops),

        "max_accuracy_drop":
            max(drops),

        "datasets":
            len(drops)

    }


ranking=dict(
    sorted(
        ranking.items(),
        key=lambda x:x[1]["mean_accuracy_drop"],
        reverse=True
    )
)


(OUTPUT_DIR/"reliability_ranking.json").write_text(
    json.dumps(
        ranking,
        indent=2
    )
)



# ------------------------------------
# Efficiency summary
# ------------------------------------

efficiency={}


for d,r in clean_results.items():

    efficiency[d]={

        "accuracy":
            r["accuracy"],

        "parameters":
            r["parameters"],

        "training_seconds":
            r["training_seconds"],

        "accuracy_per_10k_parameters":
            r["accuracy"] /
            (r["parameters"]/10000)

    }


(OUTPUT_DIR/"model_efficiency_summary.json").write_text(
    json.dumps(
        efficiency,
        indent=2
    )
)



# ------------------------------------
# Complete report
# ------------------------------------

report={

    "clean_performance":
        clean_table,

    "robustness":
        robust_summary,

    "reliability_ranking":
        ranking,

    "efficiency":
        efficiency

}


(OUTPUT_DIR/"complete_reliability_report.json").write_text(
    json.dumps(
        report,
        indent=2
    )
)



print(
"RELIABILITY_ANALYSIS_COMPLETE=True"
)

print(
"DATASETS_ANALYZED=",
list(clean_results.keys())
)

