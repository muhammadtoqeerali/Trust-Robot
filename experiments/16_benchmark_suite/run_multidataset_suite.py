from pathlib import Path
import json
import torch
import sys
import time


ROOT = Path(__file__).resolve().parent

sys.path.insert(
    0,
    str(ROOT)
)


from engine.config_loader import load_experiment_config
from engine.dataset import load_dataset
from engine.model_registry import (
    load_model_registry,
    create_model
)
from engine.seed_runner import run_multi_seed
from engine.experiment_runner import run_experiment
from engine.checkpoint_loader import load_checkpoint
from engine.reliability_runner import run_reliability_evaluation


DATASETS = [
    "UCI_HAR",
    "PAMAP2",
    "DSADS",
    "MotionSense"
]


SEEDS = [
    42,
    123,
    456,
    789,
    2026
]


RESULT_ROOT = Path(
    "results/benchmark_v2"
)


LOG_ROOT = Path(
    "results/logs"
)


RAW_ROOT = RESULT_ROOT / "raw_runs"



def ensure_dirs():

    RESULT_ROOT.mkdir(
        parents=True,
        exist_ok=True
    )

    RAW_ROOT.mkdir(
        parents=True,
        exist_ok=True
    )



def train_one_dataset(dataset_name):


    print()
    print("="*70)
    print("DATASET_START:", dataset_name)
    print("="*70)


    registry = load_model_registry()


    dataset = load_dataset(
        dataset_name
    )


    train_loader = dataset["train_loader"]
    val_loader = dataset["val_loader"]
    test_loader = dataset["test_loader"]
    num_classes = dataset["num_classes"]


    dataset_summary = {

        "dataset":
            dataset_name,

        "num_classes":
            num_classes,

        "train_batches":
            len(train_loader),

        "val_batches":
            len(val_loader),

        "test_batches":
            len(test_loader)

    }


    dataset_dir = RESULT_ROOT / dataset_name

    dataset_dir.mkdir(
        parents=True,
        exist_ok=True
    )


    with open(
        dataset_dir/"dataset_summary.json",
        "w"
    ) as f:

        json.dump(
            dataset_summary,
            f,
            indent=2
        )



    for model_name in registry:


        print()
        print("#"*60)
        print("MODEL_START:", model_name)
        print("#"*60)


        cfg = load_experiment_config(
            dataset_name,
            model_name
        )


        model_dir = (
            RAW_ROOT
            /
            dataset_name
            /
            model_name
        )


        model_dir.mkdir(
            parents=True,
            exist_ok=True
        )



        def experiment(seed):


            seed_dir = (
                model_dir
                /
                f"seed_{seed}"
            )


            checkpoint = (
                seed_dir
                /
                "checkpoint.pt"
            )


            metrics_file = (
                seed_dir
                /
                "metrics.json"
            )


            if (
                checkpoint.exists()
                and
                metrics_file.exists()
            ):

                print(
                    "SKIPPING_EXISTING:",
                    dataset_name,
                    model_name,
                    seed
                )

                return json.loads(
                    metrics_file.read_text()
                )



            print()
            print(
                "TRAINING",
                dataset_name,
                model_name,
                "SEED",
                seed
            )


            seed_dir.mkdir(
                parents=True,
                exist_ok=True
            )


            cfg["training"]["seed"] = seed


            start=time.time()


            result = run_experiment(
                model_name,
                train_loader,
                val_loader,
                test_loader,
                num_classes,
                cfg,
                seed_dir
            )


            elapsed=time.time()-start


            result["training_wall_time_seconds"]=elapsed


            with open(
                metrics_file,
                "w"
            ) as f:

                json.dump(
                    result,
                    f,
                    indent=2,
                    default=str
                )


            return result



        seed_results = run_multi_seed(
            model_name,
            dataset_name,
            experiment,
            cfg,
            None,
            None,
            output_dir=str(model_dir)
        )



        # reliability evaluation
        for seed in SEEDS:


            checkpoint = (
                model_dir
                /
                f"seed_{seed}"
                /
                "best_model.pt"
            )


            if not checkpoint.exists():

                checkpoint = (
                    model_dir
                    /
                    f"seed_{seed}"
                    /
                    "checkpoint.pt"
                )


            if not checkpoint.exists():

                print(
                    "NO_CHECKPOINT_FOR_RELIABILITY:",
                    checkpoint
                )

                continue



            reliability_dir = (
                RESULT_ROOT
                /
                dataset_name
                /
                "reliability"
                /
                model_name
                /
                f"seed_{seed}"
            )


            if reliability_dir.exists():

                print(
                    "RELIABILITY_EXISTS_SKIP",
                    reliability_dir
                )

                continue



            print(
                "RELIABILITY_START:",
                dataset_name,
                model_name,
                seed
            )


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
                reliability_dir
            )



def main():

    ensure_dirs()


    for dataset in DATASETS:

        train_one_dataset(
            dataset
        )


    print()
    print(
        "MULTI_DATASET_BENCHMARK_COMPLETE=True"
    )



if __name__=="__main__":

    main()

