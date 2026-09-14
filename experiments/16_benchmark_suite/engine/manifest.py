from pathlib import Path
import json
import subprocess
import datetime



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



def create_manifest(
    dataset,
    model,
    cfg
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


        "training":
            cfg.get(
                "training",
                {}
            ),


        "augmentation":
            cfg.get(
                "augmentation",
                {}
            )

    }



def save_manifest(
    path,
    manifest
):

    Path(path).write_text(
        json.dumps(
            manifest,
            indent=2
        )
    )
