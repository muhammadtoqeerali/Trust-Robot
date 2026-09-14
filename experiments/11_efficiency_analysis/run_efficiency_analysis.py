
import json
import time
import sys
from pathlib import Path


# --------------------------------------------------
# Add project root to Python path
# --------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(
    0,
    str(ROOT)
)


import torch
import numpy as np


# --------------------------------------------------
# Paths
# --------------------------------------------------

ROOT = Path(".")

MODEL_DIR = ROOT / "models"

OUTPUT_DIR = ROOT / "results/efficiency"

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


DEVICE = (
    "cuda"
    if torch.cuda.is_available()
    else "cpu"
)


print(
    "DEVICE=",
    DEVICE
)


# --------------------------------------------------
# Import architectures
# --------------------------------------------------

from models.architectures.baseline_cnn import CNN1D
from models.architectures.reliability_cnn import ReliabilityCNN1D



DATASET = "UCI_HAR"



# --------------------------------------------------
# Utility
# --------------------------------------------------

def count_parameters(model):

    return sum(
        p.numel()
        for p in model.parameters()
        if p.requires_grad
    )



def measure_latency(model):

    model.eval()


    x = torch.randn(
        1,
        128,
        6
    ).to(
        DEVICE
    )


    # warmup

    with torch.no_grad():

        for _ in range(20):

            model(x)


    if DEVICE=="cuda":

        torch.cuda.synchronize()



    start=time.time()


    with torch.no_grad():

        for _ in range(200):

            model(x)



    if DEVICE=="cuda":

        torch.cuda.synchronize()



    end=time.time()


    latency_ms = (
        (end-start)
        /
        200
        *
        1000
    )


    return latency_ms



def model_size(path):

    return (
        Path(path).stat().st_size
        /
        (1024*1024)
    )



# --------------------------------------------------
# Evaluate models
# --------------------------------------------------

results={}



models={

    "1D_CNN":

    (
        CNN1D(6),
        "models/baselines/1dcnn_UCI_HAR.pt"
    ),


    "Reliability_CNN_v1":

    (
        ReliabilityCNN1D(6),
        "models/reliability_model/reliability_cnn_UCI_HAR.pt"
    ),


    "Reliability_CNN_v2":

    (
        ReliabilityCNN1D(6),
        "models/reliability_v2/reliability_cnn_v2_UCI_HAR.pt"
    )

}



for name,(model,path) in models.items():


    state=torch.load(
        path,
        map_location=DEVICE
    )


    model.load_state_dict(
        state
    )


    model.to(
        DEVICE
    )


    params=count_parameters(
        model
    )


    latency=measure_latency(
        model
    )


    size=model_size(
        path
    )


    results[name]={

        "parameters":
            params,

        "model_size_MB":
            size,

        "latency_ms":
            latency,

        "device":
            DEVICE
    }



print(
    json.dumps(
        results,
        indent=2
    )
)



(OUTPUT_DIR/"efficiency_report.json").write_text(
    json.dumps(
        results,
        indent=2
    )
)



print(
    "EFFICIENCY_ANALYSIS_COMPLETE=True"
)

