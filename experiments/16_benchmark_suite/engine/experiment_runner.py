
import time
import json
import torch
import torch.nn as nn

from pathlib import Path


from engine.model_registry import create_model
from engine.evaluator import evaluate_model
from engine.model_forward import model_forward

from engine.reproducibility import set_seed
from engine.manifest import create_manifest, save_manifest
from engine.dataset_manifest import create_dataset_manifest

from engine.model_artifact import create_model_metadata

from engine.model_metadata import (
    collect_metadata
)



def count_parameters(model):

    return sum(
        p.numel()
        for p in model.parameters()
    )




def run_experiment(
    model_name,
    train_loader,
    val_loader,
    test_loader,
    num_classes,
    cfg,
    output_dir
):


    seed = cfg["training"].get(
        "seed",
        42
    )


    set_seed(
        seed
    )


    device = (
        "cuda"
        if torch.cuda.is_available()
        else "cpu"
    )


    output_dir=Path(
        output_dir
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )



    manifest=create_manifest(
        cfg["dataset"]["name"],
        model_name,
        cfg
    )


    save_manifest(
        output_dir / "experiment_manifest.json",
        manifest
    )


    # -----------------------------
    # Model
    # -----------------------------

    sample_batch = next(
        iter(train_loader)
    )


    if isinstance(sample_batch, (list,tuple)):

        sample_x = sample_batch[0]

    else:

        sample_x = sample_batch


    # Dataset contract:
    #
    # IMU tensors are:
    # (batch, time, channels)
    #
    # Example:
    # (64,128,6)
    #
    # Therefore channel dimension is LAST.

    if sample_x.ndim == 3:

        input_channels = sample_x.shape[-1]

    else:

        raise RuntimeError(
            f"Unsupported input shape: {sample_x.shape}"
        )


    print(
        "MODEL_INPUT_CHANNELS:",
        input_channels
    )


    model=create_model(
        model_name,
        num_classes,
        input_channels
    )


    model=model.to(
        device
    )


    model_metadata=create_model_metadata(
        model
    )


    parameters=count_parameters(
        model
    )


    print(
        "METADATA_MODEL:",
        model.__class__.__name__
    )


    metadata=collect_metadata(
        model,
        train_loader,
        device
    )



    optimizer=torch.optim.Adam(
        model.parameters(),
        lr=cfg["training"]["learning_rate"]
    )


    criterion=nn.CrossEntropyLoss()



    best_f1=0


    checkpoint=(
        output_dir /
        "best_model.pt"
    )



    start=time.time()


    epochs=cfg["training"].get(
        "epochs",
        100
    )


    for epoch in range(
        epochs
    ):


        model.train()


        for batch in train_loader:


            if len(batch)==3:

                x_clean, x_corrupt, y = batch

                x=x_corrupt

            else:

                x,y=batch


            x=x.to(device)

            y=y.to(device)


            optimizer.zero_grad()


            output=model_forward(
                model,
                x
            )


            if isinstance(
                output,
                tuple
            ):
                output=output[0]


            loss=criterion(
                output,
                y
            )


            loss.backward()


            optimizer.step()



        # validation

        result=evaluate_model(
            model,
            val_loader,
            device,
            output_dir
        )


        if result["macro_f1"] > best_f1:


            best_f1=result["macro_f1"]


            torch.save(
                model.state_dict(),
                checkpoint
            )



    training_seconds=(
        time.time()
        -
        start
    )



    # -----------------------------
    # Final test
    # -----------------------------

    model.load_state_dict(
        torch.load(
            checkpoint,
            map_location=device
        )
    )


    test_result=evaluate_model(
        model,
        test_loader,
        device,
        output_dir
    )



    final={

        "model":
            model_name,

        "metadata":
            metadata,

        "training_seconds":
            training_seconds,

        "checkpoint":
            str(checkpoint),

        "model_state":
            model.state_dict(),

        "test":
            test_result

    }



    return final
