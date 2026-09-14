
import sys
import json
from pathlib import Path

import torch
import numpy as np

from sklearn.metrics import accuracy_score, f1_score


# --------------------------------------------------
# Project root
# --------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(
    0,
    str(ROOT)
)


DATASET = sys.argv[1]


DEVICE = (
    "cuda"
    if torch.cuda.is_available()
    else "cpu"
)


print("DATASET=", DATASET)
print("DEVICE=", DEVICE)



# --------------------------------------------------
# Models
# --------------------------------------------------

from models.architectures.baseline_cnn import CNN1D
from models.architectures.reliability_cnn import ReliabilityCNN1D



# --------------------------------------------------
# Data
# --------------------------------------------------

base = Path(
    f"data/processed/harmonized/{DATASET}"
)


X=np.load(
    base/"X.npy"
).astype(
    "float32"
)


y=np.load(
    base/"y.npy"
).astype(
    "int64"
)


from sklearn.preprocessing import LabelEncoder


encoder=LabelEncoder()

y=encoder.fit_transform(
    y
)



test_idx=np.load(
    f"data/processed/splits/{DATASET}/test_idx.npy"
)


train_idx=np.load(
    f"data/processed/splits/{DATASET}/train_idx.npy"
)


X_test=X[test_idx]

y_test=y[test_idx]


X_train=X[train_idx]


mean=X_train.mean(
    axis=(0,1)
)


std=X_train.std(
    axis=(0,1)
)+1e-8



X_test=(
    X_test-mean
)/std



# --------------------------------------------------
# Corruption functions
# --------------------------------------------------

import importlib.util


def load_function(path,name):

    spec=importlib.util.spec_from_file_location(
        name,
        path
    )

    m=importlib.util.module_from_spec(
        spec
    )

    spec.loader.exec_module(
        m
    )

    return getattr(
        m,
        name
    )


missing_channel=load_function(
"experiments/04_reliability/corruption/missing_channel.py",
"apply_missing_channel"
)


random_dropout=load_function(
"experiments/04_reliability/corruption/random_dropout.py",
"apply_random_dropout"
)


gaussian_noise=load_function(
"experiments/04_reliability/corruption/gaussian_noise.py",
"apply_gaussian_noise"
)


sensor_drift=load_function(
"experiments/04_reliability/corruption/sensor_drift.py",
"apply_sensor_drift"
)



# --------------------------------------------------
# Evaluation
# --------------------------------------------------

def evaluate(model,X):

    model.eval()

    with torch.no_grad():

        out=model(
            torch.tensor(X).to(DEVICE)
        )


        if isinstance(out,tuple):

            out=out[0]


        pred=(
            out.argmax(1)
            .cpu()
            .numpy()
        )


    return {

        "accuracy":
        float(
            accuracy_score(
                y_test,
                pred
            )
        ),

        "macro_f1":
        float(
            f1_score(
                y_test,
                pred,
                average="macro"
            )
        )
    }



# --------------------------------------------------
# Load models
# --------------------------------------------------

num_classes=len(
np.unique(y)
)


models={

"1D_CNN":
(
CNN1D(num_classes),
f"models/baselines/1dcnn_{DATASET}.pt"
),


"Reliability_CNN_v1":
(
ReliabilityCNN1D(num_classes),
f"models/reliability_model/reliability_cnn_{DATASET}.pt"
),


"Reliability_CNN_v2":
(
ReliabilityCNN1D(num_classes),
f"models/reliability_v2/reliability_cnn_v2_{DATASET}.pt"
)

}



for name,(model,path) in models.items():

    model.load_state_dict(
        torch.load(
            path,
            map_location=DEVICE
        )
    )

    model.to(
        DEVICE
    )



# --------------------------------------------------
# Corruption evaluation
# --------------------------------------------------

def extract_corrupted(result):

    if isinstance(
        result,
        tuple
    ):

        return result[0]

    return result



corruptions={

"clean":
lambda x:x,

"missing_gyro":
lambda x:
extract_corrupted(
    missing_channel(
        x,
        channels=[
            "gyro_x",
            "gyro_y",
            "gyro_z"
        ]
    )
),


"missing_acceleration":
lambda x:
extract_corrupted(
    missing_channel(
        x,
        channels=[
            "accel_x",
            "accel_y",
            "accel_z"
        ]
    )
),


"dropout_25":
lambda x:
extract_corrupted(
    random_dropout(
        x,
        drop_ratio=0.25
    )
),


"noise_10db":
lambda x:
extract_corrupted(
    gaussian_noise(
        x,
        snr_db=10
    )
),


"drift_025":
lambda x:
extract_corrupted(
    sensor_drift(
        x,
        bias_scale=0.25
    )
)

}



results={}



for model_name,(model,path) in models.items():

    results[model_name]={}


    clean=None


    for cname,func in corruptions.items():

        Xc=func(
            X_test.copy()
        )


        score=evaluate(
            model,
            Xc
        )


        results[model_name][cname]=score


        if cname=="clean":

            clean=score["accuracy"]

        else:

            score["accuracy_drop"]=(
                clean-score["accuracy"]
            )



print(
json.dumps(
results,
indent=2
)
)



out=Path(
"results/robustness_comparison"
)


out.mkdir(
parents=True,
exist_ok=True
)


(out/f"{DATASET}_model_robustness.json").write_text(
json.dumps(
results,
indent=2
)
)


print(
"MODEL_ROBUSTNESS_COMPARISON_COMPLETE=True"
)

