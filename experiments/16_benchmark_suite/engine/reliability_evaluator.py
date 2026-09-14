import json
from pathlib import Path

import torch
import numpy as np

from torch.utils.data import DataLoader

from sklearn.metrics import (
    accuracy_score,
    f1_score
)

from engine.model_forward import model_forward
from engine.reliability_dataset import ReliabilityDataset



def evaluate_predictions(
    model,
    loader,
    device
):

    model.eval()

    predictions=[]

    labels=[]


    with torch.no_grad():

        for batch in loader:

            x,y=batch[:2]


            x=x.to(device)


            output=model_forward(
                model,
                x
            )


            if isinstance(
                output,
                tuple
            ):

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


    return {

        "accuracy":
            float(
                accuracy_score(
                    labels,
                    predictions
                )
            ),


        "macro_f1":
            float(
                f1_score(
                    labels,
                    predictions,
                    average="macro"
                )
            )

    }



def evaluate_reliability(
    model,
    clean_dataset,
    corruption,
    severity,
    device,
    seed=42,
    output=None
):


    corrupted_dataset=ReliabilityDataset(

        clean_dataset,

        corruption,

        seed=seed,

        severity=severity

    )


    loader=DataLoader(

        corrupted_dataset,

        batch_size=64,

        shuffle=False

    )


    corrupted_metrics=evaluate_predictions(

        model,

        loader,

        device

    )


    result={

        "corruption":
            corruption,

        "severity":
            severity,

        "seed":
            seed,

        "metrics":
            corrupted_metrics

    }



    if output:

        Path(output).write_text(

            json.dumps(
                result,
                indent=2
            )

        )


    return result
