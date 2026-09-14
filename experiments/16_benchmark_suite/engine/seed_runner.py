from pathlib import Path

import torch

from engine.reproducibility import set_seed
from engine.statistical_runner import save_statistics

from engine.artifact_manager import (
    create_run_directory,
    create_manifest,
    save_json
)


DEFAULT_SEEDS=[

    42,
    123,
    456,
    789,
    2026

]



def run_multi_seed(
    model_name,
    dataset_name,
    experiment_function,
    config,
    dataset_manifest,
    model_metadata,
    seeds=DEFAULT_SEEDS,
    output_dir="results/benchmark_v1"
):


    results=[]


    for seed in seeds:


        print(
            "\n================"
        )

        print(
            "MODEL:",
            model_name
        )

        print(
            "SEED:",
            seed
        )


        set_seed(
            seed
        )


        run_dir=create_run_directory(
            dataset_name,
            model_name,
            seed
        )


        manifest=create_manifest(
            dataset_name,
            model_name,
            seed,
            config
        )


        save_json(
            run_dir,
            "manifest.json",
            manifest
        )


        save_json(
            run_dir,
            "config.json",
            config
        )


        save_json(
            run_dir,
            "dataset_manifest.json",
            dataset_manifest
        )


        result=experiment_function(
            seed
        )


        clean_result={

            "model":
                result.get(
                    "model"
                ),

            "training_seconds":
                result.get(
                    "training_seconds"
                ),

            "test":
                result.get(
                    "test"
                ),

            "metadata":
                result.get(
                    "metadata"
                )

        }


        save_json(
            run_dir,
            "metrics.json",
            clean_result
        )


        if clean_result["metadata"]:

            save_json(
                run_dir,
                "model_metadata.json",
                clean_result["metadata"]
            )


        if "model_state" in result:

            torch.save(
                result["model_state"],
                run_dir / "checkpoint.pt"
            )


        results.append(
            clean_result
        )



    statistics_dir=Path(
        output_dir
    )/"statistics"


    statistics_dir.mkdir(
        parents=True,
        exist_ok=True
    )


    save_statistics(
        model_name,
        results,
        statistics_dir /
        f"{model_name}_statistics.json"
    )


    return results
