import json
from pathlib import Path


def load_corruption_registry(
    path="configs/reliability/corruption_registry_v1.json"
):

    path=Path(path)

    if not path.exists():

        raise FileNotFoundError(
            f"Missing corruption registry: {path}"
        )


    return json.loads(
        path.read_text()
    )



def list_corruptions(
    registry
):

    return list(
        registry.get(
            "corruptions",
            {}
        ).keys()
    )
