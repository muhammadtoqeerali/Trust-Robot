import sys
import json
import torch
import numpy as np
from pathlib import Path

from sklearn.metrics import accuracy_score, f1_score


DATASET = sys.argv[1]

print("DATASET=", DATASET)


DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

print("DEVICE=", DEVICE)


# -------------------------------------------------
# Import model
# -------------------------------------------------

import importlib.util


model_path = (
    "experiments/07_reliability_training/"
    "train_reliability_v2.py"
)


spec = importlib.util.spec_from_file_location(
    "train_v2",
    model_path
)

module = importlib.util.module_from_spec(spec)

spec.loader.exec_module(module)


ReliabilityCNN = module.ReliabilityCNN


# -------------------------------------------------
# Import corruption functions
# -------------------------------------------------

def load_function(path, name):

    spec = importlib.util.spec_from_file_location(
        name,
        path
    )

    m = importlib.util.module_from_spec(spec)

    spec.loader.exec_module(m)

    return getattr(m,name)



apply_missing_channel = load_function(
"experiments/04_reliability/corruption/missing_channel.py",
"apply_missing_channel"
)


apply_random_dropout = load_function(
"experiments/04_reliability/corruption/random_dropout.py",
"apply_random_dropout"
)


apply_gaussian_noise = load_function(
"experiments/04_reliability/corruption/gaussian_noise.py",
"apply_gaussian_noise"
)


apply_sensor_drift = load_function(
"experiments/04_reliability/corruption/sensor_drift.py",
"apply_sensor_drift"
)



# -------------------------------------------------
# Data
# -------------------------------------------------

base = Path(
f"data/processed/harmonized/{DATASET}"
)


X_test=np.load(
base/"X_test.npy"
).astype("float32")


y_test=np.load(
base/"y_test.npy"
).astype("int64")


X_train=np.load(
base/"X_train.npy"
).astype("float32")


mean=X_train.mean(
axis=(0,1)
)

std=X_train.std(
axis=(0,1)
)+1e-8


X_test=(X_test-mean)/std



# -------------------------------------------------
# Model
# -------------------------------------------------

num_classes=len(
np.unique(y_test)
)


model=ReliabilityCNN(
classes=num_classes
)


model.load_state_dict(
torch.load(
f"models/reliability_v2/reliability_cnn_v2_{DATASET}.pt",
map_location=DEVICE
)
)


model.to(DEVICE)

model.eval()



# -------------------------------------------------
# Evaluation
# -------------------------------------------------

def evaluate(X):

    with torch.no_grad():

        out=model(
            torch.tensor(X)
            .to(DEVICE)
        )


        if isinstance(out,tuple):
            logits=out[0]
        else:
            logits=out


        pred=(
            logits.argmax(1)
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



results={}


clean=evaluate(
X_test
)


results["clean"]=clean



corruptions={


"missing_gyro":
lambda x:
apply_missing_channel(
x,
["gyro_x","gyro_y","gyro_z"],
42
)[0],


"missing_acceleration":
lambda x:
apply_missing_channel(
x,
["accel_x","accel_y","accel_z"],
42
)[0],



"dropout_25":
lambda x:
apply_random_dropout(
x,
0.25,
42
)[0],



"noise_10db":
lambda x:
apply_gaussian_noise(
x,
10,
42
)[0],



"drift_025":
lambda x:
apply_sensor_drift(
x,
0.25,
42
)[0]

}



for name,func in corruptions.items():

    out=evaluate(
        func(
            X_test.copy()
        )
    )


    out["accuracy_drop"]=(
        clean["accuracy"]
        -
        out["accuracy"]
    )


    results[name]=out



print(
json.dumps(
results,
indent=2
)
)



Path(
"results/reliability_v2"
).mkdir(
exist_ok=True
)


Path(
f"results/reliability_v2/"
f"reliability_v2_{DATASET}_robustness.json"
).write_text(
json.dumps(
results,
indent=2
)
)


print(
"RELIABILITY_V2_ROBUSTNESS_PASS=True"
)

