import torch
import torch.nn as nn


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

            nn.BatchNorm1d(
                64
            ),

            nn.MaxPool1d(2),


            nn.Conv1d(
                64,
                128,
                kernel_size=5,
                padding=2
            ),

            nn.ReLU(),

            nn.BatchNorm1d(
                128
            ),

            nn.AdaptiveAvgPool1d(1)

        )


        self.fc = nn.Linear(
            128,
            classes
        )


    def forward(self,x):

        # B,T,C -> B,C,T

        x = x.transpose(1,2)


        x = self.net(x)


        x = x.squeeze(-1)


        return self.fc(x)

