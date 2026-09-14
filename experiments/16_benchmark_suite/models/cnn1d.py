
import torch
import torch.nn as nn



class CNN1D(nn.Module):

    def __init__(
        self,
        num_classes,
        input_channels=6
    ):
        super().__init__()


        self.net=nn.Sequential(

            nn.Conv1d(
                input_channels,
                64,
                5,
                padding=2
            ),

            nn.ReLU(),

            nn.AdaptiveAvgPool1d(1)

        )


        self.fc=nn.Linear(
            64,
            num_classes
        )


    def forward(self,x):

        # expected:
        # batch, channels, time
        # or batch, time, channels

        if x.ndim==3 and x.shape[1] != self.net[0].in_channels:

            x=x.transpose(
                1,
                2
            )


        x=self.net(x)

        x=x.squeeze(-1)

        return self.fc(x)

