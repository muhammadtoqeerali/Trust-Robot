
import json
from sklearn.preprocessing import LabelEncoder
from pathlib import Path
import time

import numpy as np
import torch
import torch.nn as nn

from sklearn.metrics import accuracy_score, f1_score


DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

DATASET="DSADS"


print("DATASET=", DATASET)

print(
"DEVICE=",
DEVICE
)


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

        x = x.transpose(1,2)

        x = self.net(x)

        x = x.squeeze(-1)

        return self.fc(x)



base=f"data/processed/harmonized/{DATASET}"

X=np.load(base+"/X.npy").astype("float32")
y=np.load(base+"/y.npy").astype("int64")

encoder = LabelEncoder()

y = encoder.fit_transform(y)

num_classes = len(
    encoder.classes_
)

print(
    "NUM_CLASSES=",
    num_classes
)




train_idx=np.load(
f"data/processed/splits/{DATASET}/train_idx.npy"
)

val_idx=np.load(
f"data/processed/splits/{DATASET}/val_idx.npy"
)

test_idx=np.load(
f"data/processed/splits/{DATASET}/test_idx.npy"
)



# training-only normalization
mean = X[train_idx].mean(axis=(0,1), keepdims=True)
std = X[train_idx].std(axis=(0,1), keepdims=True)

std[std==0] = 1

X = (X - mean) / std


X_train=torch.tensor(X[train_idx])
y_train=torch.tensor(y[train_idx])

X_val=torch.tensor(X[val_idx])
y_val=torch.tensor(y[val_idx])

X_test=torch.tensor(X[test_idx])
y_test=torch.tensor(y[test_idx])



classes=int(
np.max(y)+1
)


model=CNN1D(classes).to(DEVICE)


optimizer=torch.optim.Adam(
model.parameters(),
lr=1e-3
)


loss_fn=nn.CrossEntropyLoss()


batch=128
epochs=20


best=-1


Path(
    "results/baselines/"
    + DATASET
    + "_label_mapping.json"
).write_text(
    json.dumps(
        {
            "classes":
            encoder.classes_.tolist()
        },
        indent=2
    )
)




start=time.time()


for epoch in range(epochs):

    model.train()


    perm=torch.randperm(
        len(X_train)
    )


    for i in range(
        0,
        len(X_train),
        batch
    ):

        idx=perm[i:i+batch]

        xb=X_train[idx].to(DEVICE)
        yb=y_train[idx].to(DEVICE)


        optimizer.zero_grad()


        out=model(xb)

        loss=loss_fn(
            out,
            yb
        )


        loss.backward()

        optimizer.step()



    model.eval()

    with torch.no_grad():

        pred=model(
            X_val.to(DEVICE)
        ).argmax(1).cpu()


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
            f"models/baselines/1dcnn_{DATASET}.pt"
        )



train_time=time.time()-start



model.load_state_dict(
torch.load(
f"models/baselines/1dcnn_{DATASET}.pt",
map_location=DEVICE
)
)


model.eval()

with torch.no_grad():

    pred=model(
        X_test.to(DEVICE)
    ).argmax(1).cpu()



accuracy=accuracy_score(
y_test,
pred
)

f1=f1_score(
y_test,
pred,
average="macro"
)



params=sum(
p.numel()
for p in model.parameters()
)


result={

"model":"1D_CNN",

"dataset":DATASET,

"accuracy":float(accuracy),

"macro_f1":float(f1),

"parameters":int(params),

"training_seconds":float(train_time)

}



Path(
f"results/baselines/1dcnn_{DATASET}_results.json"
).write_text(
json.dumps(
result,
indent=2
)
)


print(
"BASELINE_TRAINING_COMPLETE=True"
)

print(result)

