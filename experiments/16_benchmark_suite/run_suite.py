
import argparse
import json
import sys

from pathlib import Path
from engine.config_loader import (
    load_experiment_config
)




sys.path.insert(
    0,
    str(Path(__file__).parent)
)


from engine.model_registry import (
    load_model_registry
)

from engine.experiment_runner import (
    run_experiment
)

from engine.seed_runner import run_multi_seed

from engine.config_loader import load_experiment_config

from engine.dataset import (
    load_dataset
)

from engine.dataset_manifest import (
    create_dataset_manifest
)

from engine.reliability_runner import (
    run_reliability_evaluation
)

from engine.checkpoint_loader import (
    load_checkpoint
)

from engine.model_registry import (
    create_model
)



RESULT_DIR = Path(
    "experiments/16_benchmark_suite/results/suite"
)


RESULT_DIR.mkdir(
    parents=True,
    exist_ok=True
)



def run_suite(dataset_name):


    registry = load_model_registry()


    dataset_result = load_dataset(
        dataset_name
    )


    dataset_manifest=create_dataset_manifest(
        dataset_name,
        dataset_result
    )


    train_loader = dataset_result["train_loader"]

    val_loader = dataset_result["val_loader"]

    test_loader = dataset_result["test_loader"]

    num_classes = dataset_result["num_classes"]


    results={}


    for model_name in registry:


        print(
            "\n===================="
        )

        print(
            "TRAINING:",
            model_name
        )


        output_dir = (
            RESULT_DIR /
            model_name
        )


        cfg = load_experiment_config(
            dataset_name,
            model_name
        )


        print(
            "CONFIG_LOADED:",
            cfg["experiment"].get(
                "name",
                model_name
            )
        )


        print(
            "EPOCHS:",
            cfg["training"]["epochs"]
        )


        print(
            "BATCH_SIZE:",
            cfg["training"]["batch_size"]
        )


        print(
            "LR:",
            cfg["training"]["learning_rate"]
        )


        def experiment(seed):


            cfg["training"]["seed"]=seed


            return run_experiment(

                model_name,

                train_loader,

                val_loader,

                test_loader,

                num_classes,

                cfg,

                output_dir

            )



        seed_results=run_multi_seed(

            model_name,

            dataset_name,

            experiment,

            cfg,

            dataset_manifest,

            None,

            output_dir=str(
                RESULT_DIR /
                "statistics"
            )

        )


        # Reliability evaluation on final checkpoint

        for seed in [42,123,456,789,2026]:

            checkpoint = Path(
                "results/benchmark_v1"
            ) / dataset_name / "raw_runs" / model_name / f"seed_{seed}" / "checkpoint.pt"


            if checkpoint.exists():

                model=create_model(
                    model_name,
                    num_classes,
                    6
                )


                model=load_checkpoint(
                    model,
                    checkpoint,
                    "cpu"
                )


                run_reliability_evaluation(

                    model,

                    test_loader,

                    "cpu",

                    Path(
                        "results/benchmark_v1"
                    )
                    /
                    dataset_name
                    /
                    "reliability"
                    /
                    model_name
                    /
                    f"seed_{seed}"

                )


        results[model_name]=seed_results



        # ==========================================
        # Reliability evaluation using seed_42 model
        # ==========================================


        reliability_checkpoint = (

            Path(
                "results/benchmark_v1"
            )
            /
            dataset_name
            /
            "raw_runs"
            /
            model_name
            /
            "seed_42"
            /
            "checkpoint.pt"

        )


        if reliability_checkpoint.exists():


            print(
                "\nRELIABILITY_EVALUATION:",
                model_name
            )


            reliability_model=create_model(

                model_name,

                num_classes,

                6

            )


            device = (

                "cuda"
                if __import__(
                    "torch"
                ).cuda.is_available()
                else
                "cpu"

            )


            reliability_model=load_checkpoint(

                reliability_model,

                reliability_checkpoint,

                device

            )


            run_reliability_evaluation(

                reliability_model,

                test_loader,

                device,

                Path(
                    "results/benchmark_v1"
                )
                /
                dataset_name
                /
                "reliability"
                /
                model_name

            )


        else:

            print(
                "WARNING: reliability checkpoint missing:",
                reliability_checkpoint
            )



        with open(
            output_dir /
            "seed_results.json",
            "w"
        ) as f:

            json.dump(
                seed_results,
                f,
                indent=2
            )



    with open(
        RESULT_DIR /
        "comparison.json",
        "w"
    ) as f:

        json.dump(
            results,
            f,
            indent=2
        )


    print(
        "\nFULL_SUITE_COMPLETE=True"
    )




if __name__=="__main__":


    parser=argparse.ArgumentParser()


    parser.add_argument(
        "--dataset",
        required=True
    )


    parser.add_argument(
        "--all-models",
        action="store_true"
    )


    args=parser.parse_args()


    run_suite(
        args.dataset
    )
