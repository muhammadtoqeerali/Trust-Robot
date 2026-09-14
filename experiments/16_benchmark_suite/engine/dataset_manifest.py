import json
from pathlib import Path
import datetime



def create_dataset_manifest(
    dataset_name,
    dataset_result
):


    return {

        "timestamp":
            datetime.datetime.now().isoformat(),

        "dataset":
            dataset_name,

        "num_classes":
            dataset_result["num_classes"],

        "input_shape":
            list(
                dataset_result["input_shape"]
            ),

        "loader_sizes":
        {

            "train":
                len(
                    dataset_result["train_loader"].dataset
                ),

            "validation":
                len(
                    dataset_result["val_loader"].dataset
                ),

            "test":
                len(
                    dataset_result["test_loader"].dataset
                )

        },

        "protocol":
        {

            "subject_disjoint":
                True

        }

    }



def save_dataset_manifest(
    path,
    manifest
):

    Path(path).write_text(
        json.dumps(
            manifest,
            indent=2
        )
    )
