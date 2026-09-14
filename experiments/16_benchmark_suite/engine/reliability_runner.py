from pathlib import Path
import json

from torch.utils.data import DataLoader


from engine.reliability_dataset import ReliabilityDataset
from engine.evaluator import evaluate_model
from engine.reliability_score import (
    create_reliability_summary
)



CORRUPTIONS=[

    "missing_channel",
    "random_dropout",
    "gaussian_noise",
    "sensor_drift"

]



SEVERITIES=[

    0.05,
    0.1,
    0.2

]



def run_reliability_evaluation(
    model,
    clean_dataset,
    device,
    output_dir
):


    output_dir=Path(
        output_dir
    )


    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )



    clean_loader=clean_dataset


    clean_metrics=evaluate_model(
        model,
        clean_loader,
        device,
        output_dir/"clean"
    )



    summaries=[]



    for corruption in CORRUPTIONS:


        for severity in SEVERITIES:


            dataset=ReliabilityDataset(

                clean_dataset.dataset,

                corruption,

                severity=severity

            )


            loader=DataLoader(
                dataset,
                batch_size=64,
                shuffle=False
            )



            metrics=evaluate_model(

                model,

                loader,

                device,

                output_dir /
                corruption /
                str(severity)

            )



            summary=create_reliability_summary(

                clean_metrics,

                metrics,

                corruption,

                severity

            )


            summaries.append(
                summary
            )



    (output_dir/"reliability_summary.json").write_text(

        json.dumps(
            summaries,
            indent=2
        )

    )


    return summaries
