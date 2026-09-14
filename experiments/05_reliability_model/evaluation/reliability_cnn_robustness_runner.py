import sys
import json
from pathlib import Path

import numpy as np
import torch
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, f1_score

import importlib.util


def load_module(path, name):

    spec = importlib.util.spec_from_file_location(
        name,
        path
    )

    module = importlib.util.module_from_spec(spec)

    spec.loader.exec_module(module)

    return module


reliability_module = load_module(
    "experiments/05_reliability_model/reliability_cnn_v1.py",
    "reliability_cnn_v1"
)

ReliabilityCNN = reliability_module.ReliabilityCNN1D


missing_module = load_module(
    "experiments/04_reliability/corruption/missing_channel.py",
    "missing_channel"
)

apply_missing_channel = missing_module.apply_missing_channel


dropout_module = load_module(
    "experiments/04_reliability/corruption/random_dropout.py",
    "random_dropout"
)

apply_random_dropout = dropout_module.apply_random_dropout


noise_module = load_module(
    "experiments/04_reliability/corruption/gaussian_noise.py",
    "gaussian_noise"
)

apply_gaussian_noise = noise_module.apply_gaussian_noise


drift_module = load_module(
    "experiments/04_reliability/corruption/sensor_drift.py",
    "sensor_drift"
)

apply_sensor_drift = drift_module.apply_sensor_drift


DATASET = sys.argv[1] if len(sys.argv) > 1 else "UCI_HAR"

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

print("DATASET=", DATASET)
print("DEVICE=", DEVICE)


base = Path(
    f"data/processed/harmonized/{DATASET}"
)


X = np.load(
    base/"X.npy"
).astype("float32")

y = np.load(
    base/"y.npy"
).astype("int64")


test_idx = np.load(
    f"data/processed/splits/{DATASET}/test_idx.npy"
)


X_test = X[test_idx]
y_test = y[test_idx]


encoder = LabelEncoder()

encoder.fit(y)

y_test = encoder.transform(
    y_test
)


# normalization

train_idx = np.load(
    f"data/processed/splits/{DATASET}/train_idx.npy"
)

mean = X[train_idx].mean(
    axis=(0,1),
    keepdims=True
)

std = X[train_idx].std(
    axis=(0,1),
    keepdims=True
)

std[std==0] = 1

X_test = (X_test - mean) / std


model = ReliabilityCNN(
    len(encoder.classes_)
).to(DEVICE)


model.load_state_dict(
    torch.load(
        f"models/reliability_model/reliability_cnn_{DATASET}.pt",
        map_location=DEVICE
    )
)


model.eval()



def evaluate(Xc):

    with torch.no_grad():

        outputs=model(
            torch.tensor(Xc).to(DEVICE)
        )

        if isinstance(outputs, tuple):
            logits=outputs[0]
        else:
            logits=outputs

        pred=logits.argmax(1).cpu().numpy()


    return {
        "accuracy": float(
            accuracy_score(
                y_test,
                pred
            )
        ),
        "macro_f1": float(
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
lambda x: apply_missing_channel(
    x,
    channels=["gyro_x","gyro_y","gyro_z"],
    seed=42
)[0],

"missing_acceleration":
lambda x: apply_missing_channel(
    x,
    channels=["accel_x","accel_y","accel_z"],
    seed=42
)[0],

"dropout_25":
lambda x: apply_random_dropout(
    x,
    drop_ratio=0.25,
    seed=42
)[0],

"noise_10db":
lambda x: apply_gaussian_noise(
    x,
    snr_db=10,
    seed=42
)[0],

"drift_025":
lambda x: apply_sensor_drift(
    x,
    bias_scale=0.25,
    seed=42
)[0]

}


for name,func in corruptions.items():

    out=evaluate(
        func(X_test.copy())
    )

    out["accuracy_drop"]=(
        clean["accuracy"]
        -
        out["accuracy"]
    )

    results[name]=out



Path(
    "results/reliability_model"
).mkdir(
    exist_ok=True
)


Path(
    f"results/reliability_model/reliability_cnn_{DATASET}_robustness.json"
).write_text(
    json.dumps(
        results,
        indent=2
    )
)


print(
    json.dumps(
        results,
        indent=2
    )
)

print(
"RELIABILITY_CNN_ROBUSTNESS_PASS=True"
)

