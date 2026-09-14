

import torch
import torch.nn as nn


class ChannelReliabilityAttention(nn.Module):

    def __init__(self, channels):

        super().__init__()

        self.pool = nn.AdaptiveAvgPool1d(1)

        self.fc = nn.Sequential(
            nn.Linear(
                channels,
                channels
            ),
            nn.Sigmoid()
        )


    def forward(self, x):

        # x:
        # batch, channels, time

        w = self.pool(x)

        w = w.squeeze(-1)

        w = self.fc(w)

        w = w.unsqueeze(-1)

        return x * w



class ResidualConvBlock(nn.Module):

    def __init__(self, channels):

        super().__init__()

        self.conv = nn.Sequential(

            nn.Conv1d(
                channels,
                channels,
                kernel_size=3,
                padding=1
            ),

            nn.BatchNorm1d(
                channels
            ),

            nn.ReLU(),

            nn.Conv1d(
                channels,
                channels,
                kernel_size=3,
                padding=1
            ),

            nn.BatchNorm1d(
                channels
            )
        )


        self.relu = nn.ReLU()


    def forward(self,x):

        return self.relu(
            x + self.conv(x)
        )



class ReliabilityCNN_v24(nn.Module):

    def __init__(
        self,
        num_classes,
        input_channels=6
    ):

        super().__init__()


        self.attention = ChannelReliabilityAttention(
            input_channels
        )


        self.features = nn.Sequential(

            nn.Conv1d(
                input_channels,
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


            ResidualConvBlock(
                128
            ),


            nn.AdaptiveAvgPool1d(1)

        )


        self.classifier = nn.Linear(
            128,
            num_classes
        )


    def forward(self,x):

        # accept both:
        # (batch, time, channels)
        # (batch, channels, time)

        if x.shape[1] != 6 and x.shape[2] == 6:

            x = x.permute(
                0,
                2,
                1
            )


        x = self.attention(x)

        x = self.features(x)

        x = x.squeeze(-1)

        return self.classifier(x)

