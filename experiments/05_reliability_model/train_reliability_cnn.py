

import sys
import json
import time
from pathlib import Path

import numpy as np
import torch

from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, f1_score


sys.path.append(
    "experiments/05_reliability_model"
)

from reliability_cnn_v1 import ReliabilityCNN1D


# -----------------------------
# configuration
# -----------------------------

if len(sys.argv)>1:
    DATASET=sys.argv[1]
else:
    DATASET="UCI_HAR"


DEVICE="cuda" if torch.cuda.is_available() else "cpu"


print(
    "DATASET=",
    DATASET
)

print(
    "DEVICE=",
    DEVICE
)


EPOCHS=20
BATCH_SIZE=64
LR=1e-3



# -----------------------------
# data loading
# -----------------------------

base=Path(
    f"data/processed/harmonized/{DATASET}"
)


X=np.load(
    base/"X.npy"
).astype("float32")


y=np.load(
    base/"y.npy"
).astype("int64")


split_base=Path(
    f"data/processed/splits/{DATASET}"
)


train_idx=np.load(
    split_base/"train_idx.npy"
)


val_idx=np.load(
    split_base/"val_idx.npy"
)


test_idx=np.load(
    split_base/"test_idx.npy"
)



encoder=LabelEncoder()

y=encoder.fit_transform(y)


num_classes=len(
    encoder.classes_
)


print(
    "NUM_CLASSES=",
    num_classes
)



# -----------------------------
# normalization
# -----------------------------

mean=X[train_idx].mean(
    axis=(0,1),
    keepdims=True
)


std=X[train_idx].std(
    axis=(0,1),
    keepdims=True
)


std[std==0]=1


X=(X-mean)/std



# -----------------------------
# tensors
# -----------------------------

X_train=torch.tensor(
    X[train_idx]
)

y_train=torch.tensor(
    y[train_idx]
)


X_val=torch.tensor(
    X[val_idx]
)

y_val=torch.tensor(
    y[val_idx]
)


X_test=torch.tensor(
    X[test_idx]
)

y_test=torch.tensor(
    y[test_idx]
)



train_loader=DataLoader(
    TensorDataset(
        X_train,
        y_train
    ),
    batch_size=BATCH_SIZE,
    shuffle=True
)



# -----------------------------
# model
# -----------------------------

model=ReliabilityCNN1D(
    num_classes
).to(
    DEVICE
)



optimizer=torch.optim.Adam(
    model.parameters(),
    lr=LR
)


criterion=nn.CrossEntropyLoss()



best=-1


start=time.time()


# -----------------------------
# training
# -----------------------------

for epoch in range(1,EPOCHS+1):


    model.train()


    for xb,yb in train_loader:

        xb=xb.to(DEVICE)
        yb=yb.to(DEVICE)


        logits,_=model(xb)


        loss=criterion(
            logits,
            yb
        )


        optimizer.zero_grad()

        loss.backward()

        optimizer.step()



    model.eval()

    with torch.no_grad():

        val_logits,_=model(
            X_val.to(DEVICE)
        )


        val_pred=val_logits.argmax(
            1
        ).cpu()


    val_acc=accuracy_score(
        y_val,
        val_pred
    )


    print(
        "epoch",
        epoch,
        "val_acc",
        val_acc
    )


    if val_acc>best:

        best=val_acc

        torch.save(
            model.state_dict(),
            f"models/reliability_model/reliability_cnn_{DATASET}.pt"
        )



# -----------------------------
# evaluation
# -----------------------------

train_time=time.time()-start


model.load_state_dict(
    torch.load(
        f"models/reliability_model/reliability_cnn_{DATASET}.pt",
        map_location=DEVICE
    )
)


model.eval()


with torch.no_grad():

    logits,_=model(
        X_test.to(DEVICE)
    )

    pred=logits.argmax(
        1
    ).cpu()



accuracy=accuracy_score(
    y_test,
    pred
)


macro_f1=f1_score(
    y_test,
    pred,
    average="macro"
)



params=sum(
    p.numel()
    for p in model.parameters()
)



result={

    "model":
    "Reliability_CNN_v1",

    "dataset":
    DATASET,

    "accuracy":
    float(accuracy),

    "macro_f1":
    float(macro_f1),

    "parameters":
    int(params),

    "training_seconds":
    float(train_time),

    "baseline_comparison":
    "1D_CNN"

}



Path(
    f"results/reliability_model/reliability_cnn_{DATASET}_results.json"
).write_text(
    json.dumps(
        result,
        indent=2
    )
    +
    "\n"
)



print(
    "RELIABILITY_CNN_TRAINING_COMPLETE=True"
)


print(
    result
)

