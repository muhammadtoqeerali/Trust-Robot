
import argparse
import json
import shutil
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(
    0,
    str(ROOT)
)


import torch
import torch.nn as nn


from engine.config import load_config
from engine.reproducibility import set_seed
from engine.model_registry import get_model
from engine.dataset import create_dataloaders
from engine.trainer import train_model
from engine.evaluator import evaluate_model

from engine.efficiency import profile_model

from engine.system_info import collect_system_info

from engine.reliability_eval import evaluate_corruption

from engine.experiment import create_experiment_directory, save_metadata



def main(config_path):


    cfg = load_config(
        config_path
    )


    set_seed(
        cfg["training"]["seed"]
    )


    dataset = cfg["dataset"]["name"]

    model_name = cfg["model"]["name"]



    print("====================")
    print("DATASET:",dataset)
    print("MODEL:",model_name)
    print("====================")



    # -------------------------------------
    # Dataset
    # -------------------------------------


    train_loader, val_loader, test_loader, num_classes = create_dataloaders(
        dataset,
        cfg
    )



    print(
        "NUM_CLASSES:",
        num_classes
    )



    # -------------------------------------
    # Model
    # -------------------------------------


    device = (
        "cuda"
        if torch.cuda.is_available()
        else "cpu"
    )


    model=get_model(
        model_name,
        num_classes
    )


    model=model.to(device)



    params=sum(
        p.numel()
        for p in model.parameters()
    )


    print(
        "PARAMETERS:",
        params
    )


    print(
        "DEVICE:",
        device
    )



    # -------------------------------------
    # Optimizer
    # -------------------------------------


    optimizer=torch.optim.Adam(
        model.parameters(),
        lr=cfg["training"]["learning_rate"]
    )


    criterion=nn.CrossEntropyLoss()



    # -------------------------------------
    # Output directory
    # -------------------------------------


    run_name = (
        model_name
        +
        "_"
        +
        dataset
    )


    out_dir=Path(
        "results/benchmark"
    )/run_name


    out_dir.mkdir(
        parents=True,
        exist_ok=True
    )



    checkpoint=out_dir/"best_model.pt"



    # -------------------------------------
    # Training
    # -------------------------------------


    mode="standard"


    if cfg["augmentation"].get(
        "reliability_training",
        False
    ):

        mode="reliability"



    train_result=train_model(

        model,

        train_loader,

        val_loader,

        optimizer,

        criterion,

        device,

        cfg["training"]["epochs"],

        checkpoint,

        mode=mode,

        consistency_weight=
            cfg["augmentation"].get(
                "consistency_weight",
                0.2
            )

    )



    # -------------------------------------
    # Test evaluation
    # -------------------------------------


    model.load_state_dict(
        torch.load(
            checkpoint,
            map_location=device
        )
    )


    eval_dir = out_dir

    eval_dir.mkdir(
        parents=True,
        exist_ok=True
    )


    test_result=evaluate_model(

        model,

        test_loader,

        device,

        eval_dir

    )




    # -------------------------------------
    # Research profiling
    # -------------------------------------

    sample_batch = next(
        iter(train_loader)
    )[0]


    efficiency = profile_model(
        model,
        (
            1,
            sample_batch.shape[1],
            sample_batch.shape[2]
        ),
        device
    )


    reliability = evaluate_corruption(
        model,
        test_loader,
        device
    )


    system = collect_system_info()



    (out_dir/"efficiency.json").write_text(
        json.dumps(
            efficiency,
            indent=2
        )
    )


    (out_dir/"reliability.json").write_text(
        json.dumps(
            reliability,
            indent=2
        )
    )


    (out_dir/"system.json").write_text(
        json.dumps(
            system,
            indent=2
        )
    )




    final={

        "dataset":
            dataset,

        "model":
            model_name,

        "parameters":
            params,

        "training":
            train_result,

        "test":
            test_result

    }



    (out_dir/"results.json").write_text(

        json.dumps(
            final,
            indent=2
        )

    )


    shutil.copy(
        config_path,
        out_dir/"config.yaml"
    )



    print(
        json.dumps(
            final,
            indent=2
        )
    )


    print(
        "BENCHMARK_COMPLETE=True"
    )





if __name__=="__main__":


    parser=argparse.ArgumentParser()


    parser.add_argument(
        "--config",
        required=True
    )


    args=parser.parse_args()


    main(
        args.config
    )

