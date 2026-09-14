

import json
import subprocess
import sys

from pathlib import Path



DATASET=sys.argv[1]


CONFIG=Path(
"experiments/16_benchmark_suite/configs/benchmark_config.json"
)


cfg=json.loads(
    CONFIG.read_text()
)



RESULT_DIR=Path(
    f"results/benchmark/{DATASET}"
)


RESULT_DIR.mkdir(
    parents=True,
    exist_ok=True
)



for model in cfg["models"]:

    name=model["name"]

    script=model["script"]


    print(
        "\n===================="
    )

    print(
        "RUNNING:",
        name
    )

    print(
        "===================="
    )


    if not Path(script).exists():

        print(
            "SKIPPED:",
            script,
            "not implemented yet"
        )

        continue



    subprocess.run(
        [
            sys.executable,
            script,
            DATASET
        ],
        check=True
    )



print(
"BENCHMARK_RUN_COMPLETE=True"
)

