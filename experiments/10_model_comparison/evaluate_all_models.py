import sys
import json
import torch
import numpy as np

from pathlib import Path
from sklearn.metrics import accuracy_score, f1_score


# --------------------------------------------------
# Add project root to Python path
# --------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(
    0,
    str(ROOT)
)


DATASET = sys.argv[1]


print("DATASET=", DATASET)


DEVICE = (
    "cuda"
    if torch.cuda.is_available()
    else "cpu"
)

print("DEVICE=", DEVICE)



# --------------------------------------------------
# Import model architectures
# --------------------------------------------------

from models.architectures.baseline_cnn import CNN1D
from models.architectures.reliability_cnn import ReliabilityCNN1D


BaselineCNN = CNN1D

ReliabilityCNN = ReliabilityCNN1D



# --------------------------------------------------
# Data
# --------------------------------------------------

base = Path(
    f"data/processed/harmonized/{DATASET}"
)


X = np.load(
    base/"X.npy"
).astype(
    "float32"
)


y = np.load(
    base/"y.npy"
).astype(
    "int64"
)


# --------------------------------------------------
# Match training label encoding
# --------------------------------------------------

from sklearn.preprocessing import LabelEncoder


encoder = LabelEncoder()

y = encoder.fit_transform(
    y
).astype(
    "int64"
)




test_idx = np.load(
    f"data/processed/splits/{DATASET}/test_idx.npy"
)


train_idx = np.load(
    f"data/processed/splits/{DATASET}/train_idx.npy"
)



X_test = X[test_idx]

y_test = y[test_idx]


X_train = X[train_idx]


mean = X_train.mean(
    axis=(0,1)
)


std = X_train.std(
    axis=(0,1)
)+1e-8


X_test = (
    X_test-mean
)/std



num_classes = len(
    np.unique(y)
)



# --------------------------------------------------
# Evaluation function
# --------------------------------------------------

def evaluate(model):

    model.eval()

    with torch.no_grad():

        out = model(
            torch.tensor(
                X_test
            ).to(
                DEVICE
            )
        )


        if isinstance(out,tuple):

            logits = out[0]

        else:

            logits = out


        pred = (
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



# --------------------------------------------------
# Load models
# --------------------------------------------------

results={}



# baseline

baseline = BaselineCNN(
    num_classes
)


baseline.load_state_dict(
    torch.load(
        f"models/baselines/1dcnn_{DATASET}.pt",
        map_location=DEVICE
    )
)


baseline.to(DEVICE)



results["1D_CNN"] = evaluate(
    baseline
)



# reliability v1

rel1 = ReliabilityCNN(
    num_classes
)


rel1.load_state_dict(
    torch.load(
        f"models/reliability_model/reliability_cnn_{DATASET}.pt",
        map_location=DEVICE
    )
)


rel1.to(DEVICE)



results["Reliability_CNN_v1"] = evaluate(
    rel1
)



# reliability v2

rel2 = ReliabilityCNN(
    num_classes
)


rel2.load_state_dict(
    torch.load(
        f"models/reliability_v2/reliability_cnn_v2_{DATASET}.pt",
        map_location=DEVICE
    )
)


rel2.to(DEVICE)



results["Reliability_CNN_v2"] = evaluate(
    rel2
)



# --------------------------------------------------
# Save
# --------------------------------------------------

out_dir = Path(
    "results/model_comparison"
)

out_dir.mkdir(
    parents=True,
    exist_ok=True
)


(out_dir /
 f"{DATASET}_clean_comparison.json"
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
"MODEL_COMPARISON_EVALUATION_COMPLETE=True"
)
