
import json
import importlib.util

from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

from sklearn.metrics import accuracy_score, f1_score
from sklearn.preprocessing import LabelEncoder



DEVICE="cuda" if torch.cuda.is_available() else "cpu"

DATASET="UCI_HAR"


print(
"DATASET=",
DATASET
)

print(
"DEVICE=",
DEVICE
)



# -------------------------
# Load dropout corruption
# -------------------------

spec=importlib.util.spec_from_file_location(
    "random_dropout",
    "experiments/04_reliability/corruption/random_dropout.py"
)

drop_module=importlib.util.module_from_spec(spec)

spec.loader.exec_module(
    drop_module
)



# -------------------------
# Model
# -------------------------

class CNN1D(nn.Module):

    def __init__(self, classes):

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



# -------------------------
# Load test data
# -------------------------

base=Path(
"data/processed/harmonized/UCI_HAR"
)


X_test=np.load(
base/"X_test.npy"
).astype("float32")


y_test=np.load(
base/"y_test.npy"
).astype("int64")


X_train=np.load(
base/"X_train.npy"
).astype("float32"
)



encoder=LabelEncoder()

y_train_encoded=encoder.fit_transform(
    np.load(base/"y_train.npy")
)

y_test=encoder.transform(
    y_test
)



# normalization

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



# -------------------------
# Load trained model
# -------------------------

model=CNN1D(
    len(
        np.unique(y_test)
    )
).to(DEVICE)


model.load_state_dict(
torch.load(
"models/baselines/1dcnn_UCI_HAR.pt",
map_location=DEVICE
)
)


model.eval()



def evaluate(X):

    with torch.no_grad():

        pred=model(
            torch.tensor(X).to(DEVICE)
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


results["clean"]=evaluate(
    X_test
)



for ratio in [
    0.10,
    0.25,
    0.50
]:

    X_corrupted,meta = drop_module.apply_random_dropout(
        X_test,
        drop_ratio=ratio,
        seed=42
    )


    results[
        f"dropout_{int(ratio*100)}"
    ]=evaluate(
        X_corrupted
    )


    results[
        f"dropout_{int(ratio*100)}_metadata"
    ]=meta



out=Path(
"results/reliability/"
"baseline_dropout_UCI_HAR.json"
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
"DROPOUT_EVALUATION_PASS=True"
)

