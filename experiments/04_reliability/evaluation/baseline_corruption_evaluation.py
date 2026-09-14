
import json
import time

from pathlib import Path

import numpy as np
import torch

from sklearn.metrics import accuracy_score, f1_score
from sklearn.preprocessing import LabelEncoder

import importlib.util



DATASET="UCI_HAR"


DEVICE="cuda" if torch.cuda.is_available() else "cpu"


print("DATASET=", DATASET)
print("DEVICE=", DEVICE)



# -----------------------------
# Load corruption module
# -----------------------------

spec = importlib.util.spec_from_file_location(
    "missing_channel",
    "experiments/04_reliability/corruption/missing_channel.py"
)

missing_module = importlib.util.module_from_spec(spec)

spec.loader.exec_module(
    missing_module
)



# -----------------------------
# Model definition
# -----------------------------

import torch.nn as nn


class CNN1D(nn.Module):

    def __init__(self, classes):

        super().__init__()

        self.net = nn.Sequential(

            nn.Conv1d(
                6,
                64,
                kernel_size=5,
                padding=2
            ),

            nn.ReLU(),

            nn.BatchNorm1d(64),

            nn.MaxPool1d(2),


            nn.Conv1d(
                64,
                128,
                kernel_size=5,
                padding=2
            ),

            nn.ReLU(),

            nn.BatchNorm1d(128),

            nn.AdaptiveAvgPool1d(1)

        )


        self.fc = nn.Linear(
            128,
            classes
        )


    def forward(self,x):

        x=x.transpose(1,2)

        x=self.net(x)

        x=x.squeeze(-1)

        return self.fc(x)



# -----------------------------
# Load data
# -----------------------------

base = Path(
    "data/processed/harmonized/UCI_HAR"
)


X=np.load(
    base/"X_test.npy"
).astype("float32")


y=np.load(
    base/"y_test.npy"
).astype("int64")


encoder=LabelEncoder()

y=encoder.fit_transform(y)



# -----------------------------
# Normalize using training statistics
# -----------------------------

X_train=np.load(
    base/"X_train.npy"
).astype("float32")


mean=X_train.mean(
    axis=(0,1),
    keepdims=True
)


std=X_train.std(
    axis=(0,1),
    keepdims=True
)

std[std==0]=1


X=(X-mean)/std



# -----------------------------
# Load model
# -----------------------------

model=CNN1D(
    len(
        np.unique(y)
    )
).to(DEVICE)


model.load_state_dict(
    torch.load(
        "models/baselines/1dcnn_UCI_HAR.pt",
        map_location=DEVICE
    )
)


model.eval()



def evaluate(X_input):

    with torch.no_grad():

        pred=model(
            torch.tensor(
                X_input
            ).to(DEVICE)
        ).argmax(1).cpu().numpy()


    return {

        "accuracy":
            float(
                accuracy_score(
                    y,
                    pred
                )
            ),

        "macro_f1":
            float(
                f1_score(
                    y,
                    pred,
                    average="macro"
                )
            )

    }



results={}


# clean

results["clean"]=evaluate(X)



# missing gyro

X_missing_gyro, meta = missing_module.apply_missing_channel(
    X,
    [
        "gyro_x",
        "gyro_y",
        "gyro_z"
    ]
)


results["missing_gyro"]=evaluate(
    X_missing_gyro
)

results["metadata_missing_gyro"]=meta



# missing acceleration

X_missing_acc, meta = missing_module.apply_missing_channel(
    X,
    [
        "accel_x",
        "accel_y",
        "accel_z"
    ]
)


results["missing_acceleration"]=evaluate(
    X_missing_acc
)

results["metadata_missing_acceleration"]=meta



# compute drops

results["accuracy_drop_missing_gyro"] = (
    results["clean"]["accuracy"]
    -
    results["missing_gyro"]["accuracy"]
)


results["accuracy_drop_missing_acceleration"] = (
    results["clean"]["accuracy"]
    -
    results["missing_acceleration"]["accuracy"]
)



out=Path(
    "results/reliability/"
    "baseline_missing_channel_UCI_HAR.json"
)


out.write_text(
    json.dumps(
        results,
        indent=2
    )
    + "\n"
)


print(
    json.dumps(
        results,
        indent=2
    )
)


print(
    "BASELINE_CORRUPTION_EVALUATION_PASS=True"
)
