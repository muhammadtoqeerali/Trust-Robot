import sys
import json
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, f1_score


# -------------------------------
# Paths
# -------------------------------

DATASET = (
    sys.argv[1]
    if len(sys.argv) > 1
    else "UCI_HAR"
)

print(
    "DATASET=",
    DATASET
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


# -------------------------------
# Import model
# -------------------------------

import importlib.util


model_path = Path(
    "experiments/05_reliability_model/reliability_cnn_v1.py"
)


spec = importlib.util.spec_from_file_location(
    "reliability_model",
    model_path
)


module = importlib.util.module_from_spec(
    spec
)

spec.loader.exec_module(
    module
)


ReliabilityCNN = module.ReliabilityCNN1D



# -------------------------------
# Import augmentation
# -------------------------------

aug_path = Path(
    "experiments/07_reliability_training/reliability_augmentation.py"
)


spec = importlib.util.spec_from_file_location(
    "augmentation",
    aug_path
)


aug_module = importlib.util.module_from_spec(
    spec
)

spec.loader.exec_module(
    aug_module
)



# -------------------------------
# Data loading
# -------------------------------

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


test_idx = np.load(
    f"data/processed/splits/{DATASET}/test_idx.npy"
)


val_idx = np.load(
    f"data/processed/splits/{DATASET}/val_idx.npy"
)


train_idx = np.load(
    f"data/processed/splits/{DATASET}/train_idx.npy"
)



X_train = X[train_idx]
y_train = y[train_idx]

X_val = X[val_idx]
y_val = y[val_idx]

X_test = X[test_idx]
y_test = y[test_idx]



encoder = LabelEncoder()

encoder.fit(
    y_train
)


y_train = encoder.transform(
    y_train
)

y_val = encoder.transform(
    y_val
)

y_test = encoder.transform(
    y_test
)



num_classes = len(
    np.unique(y_train)
)


print(
    "NUM_CLASSES=",
    num_classes
)



# -------------------------------
# Normalization
# -------------------------------

mean = X_train.mean(
    axis=(0,1)
)

std = X_train.std(
    axis=(0,1)
)+1e-8


X_train = (
    X_train-mean
)/std


X_val = (
    X_val-mean
)/std


X_test = (
    X_test-mean
)/std



# -------------------------------
# Training dataset
# -------------------------------


class ReliabilityDataset(torch.utils.data.Dataset):

    def __init__(
        self,
        X,
        y
    ):

        self.X=X
        self.y=y


    def __len__(self):

        return len(self.X)


    def __getitem__(
        self,
        idx
    ):

        clean=self.X[idx]

        corrupted,_ = (
            aug_module.apply_random_reliability_corruption(
                clean[None],
                seed=idx,
                probability=0.5
            )
        )

        return (
            torch.tensor(clean),
            torch.tensor(corrupted[0]),
            torch.tensor(self.y[idx])
        )



train_loader = DataLoader(
    ReliabilityDataset(
        X_train,
        y_train
    ),
    batch_size=64,
    shuffle=True
)



val_tensor = torch.tensor(
    X_val
)

val_labels = torch.tensor(
    y_val
)



# -------------------------------
# Model
# -------------------------------

model = ReliabilityCNN(
    num_classes
).to(
    DEVICE
)


optimizer=torch.optim.Adam(
    model.parameters(),
    lr=1e-3
)


criterion=nn.CrossEntropyLoss()



# -------------------------------
# Training
# -------------------------------

start=time.time()


best=0


for epoch in range(20):

    model.train()

    for clean,corrupt,label in train_loader:


        clean=clean.to(DEVICE)
        corrupt=corrupt.to(DEVICE)
        label=label.to(DEVICE)



        optimizer.zero_grad()


        clean_out=model(clean)

        corrupt_out=model(corrupt)


        clean_logits,clean_feat = clean_out

        corrupt_logits,corrupt_feat = corrupt_out



        cls_loss = criterion(
            clean_logits,
            label
        )


        consistency_loss = torch.mean(
            (
                clean_feat
                -
                corrupt_feat
            )**2
        )


        loss = (
            cls_loss
            +
            0.1*consistency_loss
        )


        loss.backward()

        optimizer.step()



    model.eval()

    with torch.no_grad():

        logits,_ = model(
            val_tensor.to(DEVICE)
        )


        pred=logits.argmax(
            1
        ).cpu().numpy()


    acc=accuracy_score(
        y_val,
        pred
    )


    print(
        "epoch",
        epoch+1,
        "val_acc",
        acc
    )


    if acc>best:

        best=acc

        torch.save(
            model.state_dict(),
            f"models/reliability_v2/reliability_cnn_v2_{DATASET}.pt"
        )



# -------------------------------
# Final evaluation
# -------------------------------

model.load_state_dict(
    torch.load(
        f"models/reliability_v2/reliability_cnn_v2_{DATASET}.pt"
    )
)


model.eval()


with torch.no_grad():

    logits,_=model(
        torch.tensor(X_test).to(DEVICE)
    )

    pred=logits.argmax(
        1
    ).cpu().numpy()



result={

    "model":
        "Reliability_CNN_v2",

    "dataset":
        DATASET,

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
        ),

    "parameters":
        sum(
            p.numel()
            for p in model.parameters()
        ),

    "training_seconds":
        time.time()-start,

    "training":
        "reliability_augmentation_plus_consistency"

}



Path(
"results/reliability_v2"
).mkdir(
    exist_ok=True
)



Path(
f"results/reliability_v2/reliability_cnn_v2_{DATASET}_results.json"
).write_text(
    json.dumps(
        result,
        indent=2
    )
)


print(
    "RELIABILITY_CNN_V2_TRAINING_COMPLETE=True"
)

print(result)
