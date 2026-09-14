
import torch
import torch.nn as nn



class TCNBlock(nn.Module):

    def __init__(
        self,
        channels,
        dilation
    ):

        super().__init__()

        self.net=nn.Sequential(

            nn.Conv1d(
                channels,
                channels,
                kernel_size=3,
                padding=dilation,
                dilation=dilation
            ),

            nn.BatchNorm1d(channels),

            nn.ReLU(),

            nn.Conv1d(
                channels,
                channels,
                kernel_size=3,
                padding=dilation,
                dilation=dilation
            ),

            nn.BatchNorm1d(channels)

        )


        self.relu=nn.ReLU()



    def forward(self,x):

        return self.relu(
            x+self.net(x)
        )




class TCN(nn.Module):

    def __init__(
        self,
        num_classes,
        input_channels=6
    ):

        super().__init__()


        self.input=nn.Sequential(

            nn.Conv1d(
                input_channels,
                64,
                kernel_size=5,
                padding=2
            ),

            nn.ReLU()

        )


        self.blocks=nn.Sequential(

            TCNBlock(64,1),
            TCNBlock(64,2),
            TCNBlock(64,4),
            TCNBlock(64,8)

        )


        self.pool=nn.AdaptiveAvgPool1d(1)


        self.fc=nn.Linear(
            64,
            num_classes
        )



    def forward(self,x):

        if x.shape[-1]==6:

            x=x.transpose(
                1,
                2
            )


        x=self.input(x)

        x=self.blocks(x)

        x=self.pool(x)

        x=x.squeeze(-1)

        return self.fc(x)
