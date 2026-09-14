import torch
from torch.utils.data import Dataset

from engine.corruption_engine import apply_corruption



class ReliabilityDataset(
    Dataset
):


    def __init__(
        self,
        base_dataset,
        corruption,
        seed=42,
        severity=None
    ):


        self.x = base_dataset.tensors[0]

        self.y = base_dataset.tensors[1]

        self.corruption = corruption

        self.seed = seed

        self.severity = severity



    def __len__(self):

        return len(
            self.y
        )



    def __getitem__(
        self,
        idx
    ):


        x = self.x[idx].numpy()

        y = self.y[idx]


        kwargs={}


        if self.severity is not None:

            if self.corruption=="gaussian_noise":

                kwargs["sigma"]=self.severity


            elif self.corruption=="random_dropout":

                kwargs["probability"]=self.severity


            elif self.corruption=="sensor_drift":

                kwargs["drift_strength"]=self.severity



        x_corrupt = apply_corruption(
            x[None,:,:],
            self.corruption,
            seed=self.seed,
            **kwargs
        )[0]


        x_corrupt=torch.tensor(
            x_corrupt,
            dtype=torch.float32
        )


        metadata={

            "corruption":
                self.corruption,

            "severity":
                self.severity,

            "seed":
                self.seed

        }


        return (

            x_corrupt,

            y,

            metadata

        )
