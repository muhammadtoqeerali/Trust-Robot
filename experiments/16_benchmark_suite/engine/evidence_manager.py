import json
from pathlib import Path



def save_evidence(
    run_dir,
    manifest,
    config,
    dataset_manifest,
    model_metadata
):

    run_dir=Path(
        run_dir
    )


    run_dir.mkdir(
        parents=True,
        exist_ok=True
    )


    files={

        "manifest.json":
            manifest,

        "config.json":
            config,

        "dataset_manifest.json":
            dataset_manifest,

        "model_metadata.json":
            model_metadata

    }


    for name,data in files.items():

        (run_dir/name).write_text(
            json.dumps(
                data,
                indent=2
            )
        )


    return True
