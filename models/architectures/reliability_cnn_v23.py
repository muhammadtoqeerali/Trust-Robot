import torch
import torch.nn as nn



class ChannelReliabilityAttention(nn.Module):

    def __init__(
        self,
        channels
    ):

        super().__init__()


        self.pool=nn.AdaptiveAvgPool1d(1)


        self.fc=nn.Sequential(

            nn.Linear(
                channels,
                channels
            ),

            nn.Sigmoid()

        )



    def forward(
        self,
        x
    ):

        # x:
        # batch,time,channels

        z=x.transpose(
            1,
            2
        )


        z=self.pool(
            z
        ).squeeze(
            -1
        )


        weights=self.fc(
            z
        )


        weights=weights.unsqueeze(
            1
        )


        return x*weights





class ReliabilityCNN_v23(nn.Module):

    def __init__(
        self,
        num_classes,
        channels=6
    ):

        super().__init__()


        self.attention=ChannelReliabilityAttention(
            channels
        )


        self.features=nn.Sequential(

            nn.Conv1d(
                channels,
                64,
                kernel_size=5,
                padding=2
            ),

            nn.BatchNorm1d(
                64
            ),

            nn.ReLU(),

            nn.Conv1d(
                64,
                128,
                kernel_size=5,
                padding=2
            ),

            nn.BatchNorm1d(
                128
            ),

            nn.ReLU(),

            nn.AdaptiveAvgPool1d(1)

        )


        self.classifier=nn.Linear(
            128,
            num_classes
        )



    def forward(
        self,
        x
    ):

        x=self.attention(
            x
        )


        x=x.transpose(
            1,
            2
        )


        x=self.features(
            x
        )


        x=x.squeeze(
            -1
        )


        return self.classifier(
            x
        )
