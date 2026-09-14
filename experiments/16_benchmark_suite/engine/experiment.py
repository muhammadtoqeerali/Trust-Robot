
from pathlib import Path
import json


def create_experiment_directory(
    base_dir,
    dataset,
    model
):

    path = Path(
        base_dir
    ) / dataset / model


    path.mkdir(
        parents=True,
        exist_ok=True
    )


    return path



def save_metadata(
    path,
    metadata
):

    file = Path(path) / "metadata.json"


    file.write_text(
        json.dumps(
            metadata,
            indent=2
        )
    )



def checkpoint_exists(
    path
):

    return (
        Path(path) /
        "best_model.pt"
    ).exists()

