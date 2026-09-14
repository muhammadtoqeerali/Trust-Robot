from pathlib import Path
import json


def collect_benchmark_results(root):

    root=Path(root)

    records=[]


    for metrics_file in root.glob(
        "*/seed_*/metrics.json"
    ):

        data=json.loads(
            metrics_file.read_text()
        )


        metadata_file = (
            metrics_file.parent /
            "model_metadata.json"
        )


        if metadata_file.exists():

            metadata=json.loads(
                metadata_file.read_text()
            )

        else:

            metadata={}


        model=metrics_file.parts[-3]
        seed=metrics_file.parts[-2]


        record={

            "model":model,

            "seed":int(
                seed.replace(
                    "seed_",
                    ""
                )
            ),

            "accuracy":
                data.get("test",data)["accuracy"],

            "macro_f1":
                data.get("test",data)["macro_f1"],

            "weighted_f1":
                data.get("test",data)["weighted_f1"],

            "precision":
                data.get("test",data)["macro_precision"],

            "recall":
                data.get("test",data)["macro_recall"],

            "latency_ms_per_sample":
                data.get("test",data)["latency_ms_per_sample"],

            "parameters":
                metadata.get("parameters",0),

            "model_size_mb":
                metadata.get("model_size_mb",0),

            "training_seconds":
                data.get("training_seconds",0)

        }


        records.append(record)


    return records
