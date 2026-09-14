
import json
import time
import numpy as np
import torch

from engine.model_forward import model_forward

from engine.input_adapter import extract_input

from pathlib import Path

from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    confusion_matrix,
    classification_report
)



def evaluate_model(
    model,
    test_loader,
    device,
    output_dir
):


    model.eval()


    predictions=[]
    labels=[]

    inference_times=[]



    with torch.no_grad():


        for batch in test_loader:


            if len(batch)==3:

                x,y,metadata=batch

            else:

                x,y=batch


            x=x.to(device)



            start=time.time()


            output=model_forward(
                model,
                x
            )


            end=time.time()


            inference_times.append(
                end-start
            )



            if isinstance(output,tuple):

                output=output[0]



            pred=(
                output.argmax(
                    dim=1
                )
                .cpu()
                .numpy()
            )



            predictions.extend(
                pred
            )


            labels.extend(
                y.numpy()
            )



    predictions=np.array(
        predictions
    )


    labels=np.array(
        labels
    )



    accuracy=accuracy_score(
        labels,
        predictions
    )


    macro_f1=f1_score(
        labels,
        predictions,
        average="macro"
    )


    weighted_f1=f1_score(
        labels,
        predictions,
        average="weighted"
    )


    precision=precision_score(
        labels,
        predictions,
        average="macro",
        zero_division=0
    )


    recall=recall_score(
        labels,
        predictions,
        average="macro",
        zero_division=0
    )



    cm=confusion_matrix(
        labels,
        predictions
    )


    report=classification_report(
        labels,
        predictions,
        output_dict=True,
        zero_division=0
    )



    total_time=sum(
        inference_times
    )


    latency_ms=(
        total_time /
        len(labels)
    ) * 1000



    output_dir=Path(
        output_dir
    )


    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )



    np.save(
        output_dir/"confusion_matrix.npy",
        cm
    )



    (output_dir/"classification_report.json").write_text(
        json.dumps(
            report,
            indent=2
        )
    )



    metrics={

        "accuracy":
            float(accuracy),

        "macro_f1":
            float(macro_f1),

        "weighted_f1":
            float(weighted_f1),

        "macro_precision":
            float(precision),

        "macro_recall":
            float(recall),

        "latency_ms_per_sample":
            float(latency_ms),

        "samples":
            int(len(labels))

    }



    (output_dir/"metrics.json").write_text(
        json.dumps(
            metrics,
            indent=2
        )
    )




    # -----------------------------
    # Model metadata artifact
    # -----------------------------

    if hasattr(model, "parameters"):

        parameters = sum(
            p.numel()
            for p in model.parameters()
        )

        trainable_parameters = sum(
            p.numel()
            for p in model.parameters()
            if p.requires_grad
        )

        model_size_mb = (
            parameters * 4
        ) / (
            1024 * 1024
        )


        metadata = {

            "parameters":
                int(parameters),

            "trainable_parameters":
                int(trainable_parameters),

            "model_size_mb":
                float(model_size_mb)

        }


        (output_dir/"model_metadata.json").write_text(
            json.dumps(
                metadata,
                indent=2
            )
        )


    return metrics

