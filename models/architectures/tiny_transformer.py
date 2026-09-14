
import torch
import torch.nn as nn



class TinyTransformer(nn.Module):

    def __init__(
        self,
        num_classes,
        input_channels=6
    ):

        super().__init__()


        self.embedding=nn.Linear(
            input_channels,
            64
        )


        layer=nn.TransformerEncoderLayer(
            d_model=64,
            nhead=4,
            dim_feedforward=128,
            batch_first=True
        )


        self.encoder=nn.TransformerEncoder(
            layer,
            num_layers=2
        )


        self.pool=nn.AdaptiveAvgPool1d(1)


        self.fc=nn.Linear(
            64,
            num_classes
        )


    def forward(self,x):

        # batch,time,channels

        x=self.embedding(x)

        x=self.encoder(x)

        x=x.transpose(
            1,
            2
        )

        x=self.pool(x)

        x=x.squeeze(-1)

        return self.fc(x)
