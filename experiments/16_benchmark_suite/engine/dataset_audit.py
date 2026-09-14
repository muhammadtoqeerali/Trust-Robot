from pathlib import Path
import json
import hashlib
import numpy as np
from datetime import datetime



def file_hash(path):

    h = hashlib.sha256()

    with open(path,"rb") as f:

        for chunk in iter(
            lambda:f.read(1024*1024),
            b""
        ):
            h.update(chunk)

    return h.hexdigest()



def create_dataset_manifest(
    dataset_name
):

    base = Path(
        f"data/processed/harmonized/{dataset_name}"
    )


    split_base = Path(
        f"data/processed/splits/{dataset_name}"
    )


    X_path = base/"X.npy"
    y_path = base/"y.npy"


    X=np.load(
        X_path
    )


    y=np.load(
        y_path
    )


    train_idx=np.load(
        split_base/"train_idx.npy"
    )


    test_idx=np.load(
        split_base/"test_idx.npy"
    )



    rng=np.random.default_rng(
        42
    )


    shuffled=rng.permutation(
        train_idx
    )


    val_size=int(
        0.15*len(shuffled)
    )


    val_idx=shuffled[:val_size]


    train_final=shuffled[val_size:]



    manifest={


        "timestamp":
            datetime.now().isoformat(),


        "dataset":
            dataset_name,


        "raw_shape":
            list(X.shape),


        "window_samples":
            int(X.shape[1]),


        "channels":
            int(X.shape[2]),



        "samples":

        {

            "total":
                int(len(X)),

            "train":
                int(len(train_final)),

            "validation":
                int(len(val_idx)),

            "test":
                int(len(test_idx))

        },


        "classes":

            {

            str(k):
            int(v)

            for k,v in zip(
                *np.unique(
                    y,
                    return_counts=True
                )
            )

            },


        "files":

        {

            "X.npy":
                file_hash(X_path),

            "y.npy":
                file_hash(y_path),

            "train_idx.npy":
                file_hash(
                    split_base/"train_idx.npy"
                ),

            "test_idx.npy":
                file_hash(
                    split_base/"test_idx.npy"
                )

        },


        "protocol":

        {

            "normalization":
                "train_only",

            "validation_split":
                0.15,

            "seed":
                42

        }


    }


    return manifest



def save_dataset_manifest(
    dataset_name,
    output
):

    manifest=create_dataset_manifest(
        dataset_name
    )


    Path(output).write_text(
        json.dumps(
            manifest,
            indent=2
        )
    )


    return manifest
