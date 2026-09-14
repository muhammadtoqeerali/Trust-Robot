import json
import subprocess
from pathlib import Path
import datetime



BASE = Path(
    "results/benchmark_v1"
)



def get_git_commit():

    try:

        return subprocess.check_output(
            [
                "git",
                "rev-parse",
                "HEAD"
            ]
        ).decode().strip()

    except:

        return "unknown"



def create_run_directory(
    dataset,
    model,
    seed
):

    path = (
        BASE /
        dataset /
        "raw_runs" /
        model /
        f"seed_{seed}"
    )

    path.mkdir(
        parents=True,
        exist_ok=True
    )

    return path



def create_manifest(
    dataset,
    model,
    seed,
    config=None
):

    return {

        "timestamp":
            datetime.datetime.now().isoformat(),

        "git_commit":
            get_git_commit(),

        "dataset":
            dataset,

        "model":
            model,

        "seed":
            seed,

        "benchmark_version":
            "benchmark_v1",

        "config":
            config

    }



def save_json(
    directory,
    name,
    data
):

    path = Path(directory)/name


    path.write_text(
        json.dumps(
            data,
            indent=2
        )
    )


    return path
