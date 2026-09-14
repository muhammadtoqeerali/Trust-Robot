
import torch
import torch.nn as nn


class DepthwiseSeparableBlock(nn.Module):

    def __init__(self, in_ch, out_ch):

        super().__init__()

        self.block = nn.Sequential(

            nn.Conv1d(
                in_ch,
                in_ch,
                kernel_size=3,
                padding=1,
                groups=in_ch
            ),

            nn.BatchNorm1d(
                in_ch
            ),

            nn.ReLU(),

            nn.Conv1d(
                in_ch,
                out_ch,
                kernel_size=1
            ),

            nn.BatchNorm1d(
                out_ch
            ),

            nn.ReLU()
        )


    def forward(self,x):

        return self.block(x)



class DS_CNN(nn.Module):

    def __init__(
        self,
        num_classes,
        input_channels=6
    ):

        super().__init__()


        self.features=nn.Sequential(

            nn.Conv1d(
                input_channels,
                64,
                kernel_size=5,
                padding=2
            ),

            nn.BatchNorm1d(64),

            nn.ReLU(),


            DepthwiseSeparableBlock(
                64,
                128
            ),

            DepthwiseSeparableBlock(
                128,
                128
            ),

            nn.AdaptiveAvgPool1d(1)

        )


        self.classifier=nn.Linear(
            128,
            num_classes
        )


    def forward(self,x):

        # input:
        # batch,time,channels

        if x.shape[-1]==6:

            x=x.transpose(
                1,
                2
            )


        x=self.features(x)

        x=x.squeeze(-1)

        return self.classifier(x)
