import torch.nn as nn


class IMUTransformer(nn.Module):

    def __init__(
        self,
        num_classes,
        input_channels=6
    ):
        super().__init__()


        encoder_layer=nn.TransformerEncoderLayer(
            d_model=input_channels,
            nhead=3,
            batch_first=True
        )


        self.encoder=nn.TransformerEncoder(
            encoder_layer,
            2
        )


        self.fc=nn.Linear(
            input_channels,
            num_classes
        )


    def forward(self,x):

        x=self.encoder(x)

        x=x.mean(
            dim=1
        )

        return self.fc(x)
