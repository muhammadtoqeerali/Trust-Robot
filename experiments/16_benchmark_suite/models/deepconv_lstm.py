import torch.nn as nn


class DeepConvLSTM(nn.Module):

    def __init__(
        self,
        num_classes,
        input_channels=6
    ):
        super().__init__()


        self.conv=nn.Conv1d(
            input_channels,
            64,
            3,
            padding=1
        )


        self.lstm=nn.LSTM(
            64,
            64,
            batch_first=True
        )


        self.fc=nn.Linear(
            64,
            num_classes
        )


    def forward(self,x):

        x=x.transpose(
            1,
            2
        )


        x=self.conv(x)


        x=x.transpose(
            1,
            2
        )


        x,_=self.lstm(x)


        return self.fc(
            x[:,-1]
        )
