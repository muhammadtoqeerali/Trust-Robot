
import json
import importlib.util

from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

from sklearn.metrics import accuracy_score, f1_score
from sklearn.preprocessing import LabelEncoder




import sys

if len(sys.argv)>1:
    DATASET=sys.argv[1]
else:
    DATASET="UCI_HAR"


DEVICE="cuda" if torch.cuda.is_available() else "cpu"


print("DATASET=",DATASET)
print("DEVICE=",DEVICE)



# ----------------------------------
# dynamic imports
# ----------------------------------

def load_module(name,path):

    spec=importlib.util.spec_from_file_location(
        name,
        path
    )

    module=importlib.util.module_from_spec(
        spec
    )

    spec.loader.exec_module(
        module
    )

    return module



missing=load_module(
    "missing",
    "experiments/04_reliability/corruption/missing_channel.py"
)


dropout=load_module(
    "dropout",
    "experiments/04_reliability/corruption/random_dropout.py"
)


noise=load_module(
    "noise",
    "experiments/04_reliability/corruption/gaussian_noise.py"
)


drift=load_module(
    "drift",
    "experiments/04_reliability/corruption/sensor_drift.py"
)



# ----------------------------------
# Model
# ----------------------------------

class CNN1D(nn.Module):

    def __init__(self,classes):

        super().__init__()

        self.net=nn.Sequential(

            nn.Conv1d(
                6,
                64,
                5,
                padding=2
            ),

            nn.ReLU(),

            nn.BatchNorm1d(64),

            nn.MaxPool1d(2),


            nn.Conv1d(
                64,
                128,
                5,
                padding=2
            ),

            nn.ReLU(),

            nn.BatchNorm1d(128),

            nn.AdaptiveAvgPool1d(1)

        )


        self.fc=nn.Linear(
            128,
            classes
        )


    def forward(self,x):

        x=x.transpose(1,2)

        x=self.net(x)

        x=x.squeeze(-1)

        return self.fc(x)



# ----------------------------------
# Data
# ----------------------------------

base=Path(
f"data/processed/harmonized/{DATASET}"
)

base=f"data/processed/harmonized/{DATASET}"


X=np.load(
    base+"/X.npy"
).astype("float32")


y=np.load(
    base+"/y.npy"
).astype("int64")


test_idx=np.load(
    f"data/processed/splits/{DATASET}/test_idx.npy"
)


X_test=X[test_idx]

y_test=y[test_idx]



encoder=LabelEncoder()

encoder.fit(
    y
)


y_test=encoder.transform(
    y_test
)


X_train=X[
    np.load(
        f"data/processed/splits/{DATASET}/train_idx.npy"
    )
]


mean=X_train.mean(
    axis=(0,1),
    keepdims=True
)


std=X_train.std(
    axis=(0,1),
    keepdims=True
)


std[std==0]=1


X_test=(X_test-mean)/std



# ----------------------------------
# Model loading
# ----------------------------------

model=CNN1D(
    len(
        encoder.classes_
    )
).to(DEVICE)


model.load_state_dict(
torch.load(
f"models/baselines/1dcnn_{DATASET}.pt",
map_location=DEVICE
)
)


model.eval()



def evaluate(X):

    with torch.no_grad():

        pred=model(
            torch.tensor(
                X
            ).to(DEVICE)
        ).argmax(1).cpu().numpy()


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



results={}



# clean

results["clean"]=evaluate(
    X_test
)



# ------------------------------
# Missing channels
# ------------------------------

for name,channels in {

    "missing_gyro":
    [
        "gyro_x",
        "gyro_y",
        "gyro_z"
    ],

    "missing_acceleration":
    [
        "accel_x",
        "accel_y",
        "accel_z"
    ]

}.items():


    Xc,meta=missing.apply_missing_channel(
        X_test,
        channels
    )


    results[name]=evaluate(Xc)

    results[name+"_metadata"]=meta



# ------------------------------
# Dropout
# ------------------------------

for ratio in [
    0.10,
    0.25,
    0.50
]:

    Xc,meta=dropout.apply_random_dropout(
        X_test,
        ratio,
        42
    )


    key=f"dropout_{int(ratio*100)}"


    results[key]=evaluate(
        Xc
    )

    results[key+"_metadata"]=meta



# ------------------------------
# Gaussian noise
# ------------------------------

for snr in [
    20,
    10,
    5
]:

    Xc,meta=noise.apply_gaussian_noise(
        X_test,
        snr,
        42
    )


    key=f"noise_{snr}db"


    results[key]=evaluate(
        Xc
    )

    results[key+"_metadata"]=meta



# ------------------------------
# Drift
# ------------------------------

for scale in [
    0.1,
    0.25,
    0.5
]:

    Xc,meta=drift.apply_sensor_drift(
        X_test,
        scale,
        42
    )


    key=f"drift_{scale}"


    results[key]=evaluate(
        Xc
    )

    results[key+"_metadata"]=meta



# ----------------------------------
# Add degradation scores
# ----------------------------------

clean_acc=results["clean"]["accuracy"]


for k,v in results.items():

    if (
        isinstance(v,dict)
        and
        "accuracy" in v
    ):

        v["accuracy_drop"]=(
            clean_acc-v["accuracy"]
        )



out=Path(

"results/reliability/"
+
DATASET
+
"_reliability_benchmark_v1.json"

)


out.write_text(
json.dumps(
results,
indent=2
)
+"\n"
)


print(
json.dumps(
results,
indent=2
)
)


print(
"RELIABILITY_BENCHMARK_PASS=True"
)

