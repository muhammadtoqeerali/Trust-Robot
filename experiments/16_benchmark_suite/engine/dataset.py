
from pathlib import Path

import numpy as np
import torch

from torch.utils.data import TensorDataset, DataLoader



def load_dataset(
    dataset_name,
    batch_size=64
):


    base = Path(
        f"data/processed/harmonized/{dataset_name}"
    )


    split_base = Path(
        f"data/processed/splits/{dataset_name}"
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


    # -----------------------------------------
    # label normalization
    # -----------------------------------------

    classes = np.unique(y)

    label_map = {
        label:i
        for i,label in enumerate(classes)
    }


    y = np.array(
        [
            label_map[v]
            for v in y
        ],
        dtype="int64"
    )



    train_idx = np.load(
        split_base/"train_idx.npy"
    )


    test_idx = np.load(
        split_base/"test_idx.npy"
    )



    # -----------------------------------------
    # create validation split from training set
    # -----------------------------------------

    rng = np.random.default_rng(
        42
    )


    shuffled = rng.permutation(
        train_idx
    )


    val_size = int(
        0.15 * len(shuffled)
    )


    val_idx = shuffled[:val_size]

    train_idx = shuffled[val_size:]



    X_train = X[train_idx]
    y_train = y[train_idx]


    X_val = X[val_idx]
    y_val = y[val_idx]


    X_test = X[test_idx]
    y_test = y[test_idx]



    # -----------------------------------------
    # normalization using train only
    # -----------------------------------------

    mean = X_train.mean(
        axis=(0,1)
    )


    std = X_train.std(
        axis=(0,1)
    ) + 1e-8



    X_train = (
        X_train - mean
    ) / std


    X_val = (
        X_val - mean
    ) / std


    X_test = (
        X_test - mean
    ) / std



    train_dataset = TensorDataset(
        torch.tensor(X_train),
        torch.tensor(y_train)
    )


    val_dataset = TensorDataset(
        torch.tensor(X_val),
        torch.tensor(y_val)
    )


    test_dataset = TensorDataset(
        torch.tensor(X_test),
        torch.tensor(y_test)
    )



    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True
    )


    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False
    )


    test_loader = DataLoader(
        test_dataset,
        batch_size=batch_size,
        shuffle=False
    )



    return {

        "train_loader":
            train_loader,

        "val_loader":
            val_loader,

        "test_loader":
            test_loader,

        "num_classes":
            len(
                np.unique(y)
            ),

        "input_shape":
            X.shape[1:]

    }




def create_dataloaders(
    dataset_name,
    cfg
):


    batch_size = cfg["training"]["batch_size"]


    result = load_dataset(
        dataset_name,
        batch_size=batch_size
    )


    if cfg["augmentation"].get(
        "reliability_training",
        False
    ):


        train_dataset = ReliabilityDataset(
            result["train_loader"].dataset.tensors[0],
            result["train_loader"].dataset.tensors[1],
            cfg["augmentation"].get(
                "corruption_probability",
                0.3
            )
        )


        result["train_loader"] = DataLoader(
            train_dataset,
            batch_size=batch_size,
            shuffle=True
        )



    return (

        result["train_loader"],

        result["val_loader"],

        result["test_loader"],

        result["num_classes"]

    )



from torch.utils.data import Dataset


class ReliabilityDataset(Dataset):


    def __init__(
        self,
        X,
        y,
        corruption_probability=0.3
    ):

        self.X=X
        self.y=y
        self.probability=corruption_probability



    def __len__(self):

        return len(self.y)



    def __getitem__(self,index):


        clean=self.X[index]


        corrupt=clean.clone()


        if torch.rand(1).item() < self.probability:


            channel=torch.randint(
                0,
                corrupt.shape[-1],
                (1,)
            ).item()


            corrupt[:,channel]=0



        label=self.y[index]


        return (
            clean,
            corrupt,
            label
        )


