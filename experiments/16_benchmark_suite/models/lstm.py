import torch.nn as nn


class LSTMClassifier(nn.Module):

    def __init__(
        self,
        num_classes,
        input_channels=6
    ):
        super().__init__()


        self.lstm=nn.LSTM(
            input_size=input_channels,
            hidden_size=64,
            batch_first=True
        )


        self.fc=nn.Linear(
            64,
            num_classes
        )


    def forward(self,x):

        out,_=self.lstm(x)

        return self.fc(
            out[:,-1]
        )
