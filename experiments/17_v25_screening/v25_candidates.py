import torch
import torch.nn as nn


def to_bct(x):

    if x.ndim != 3:
        raise ValueError(
            f"Expected [B,T,C] or [B,C,T], got {tuple(x.shape)}"
        )

    if x.shape[-1] == 6:
        return x.permute(
            0,
            2,
            1
        )

    if x.shape[1] == 6:
        return x

    raise ValueError(
        f"Could not locate six IMU channels: {tuple(x.shape)}"
    )


class ChannelReliabilityAttention(nn.Module):

    def __init__(
        self,
        channels=6
    ):

        super().__init__()

        self.pool = nn.AdaptiveAvgPool1d(
            1
        )

        self.fc = nn.Sequential(
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

        weights = self.pool(
            x
        ).squeeze(
            -1
        )

        weights = self.fc(
            weights
        ).unsqueeze(
            -1
        )

        return x * weights


class DenseResidualBlock(nn.Module):

    def __init__(
        self,
        channels
    ):

        super().__init__()

        self.block = nn.Sequential(

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
            ),
        )

        self.relu = nn.ReLU()


    def forward(
        self,
        x
    ):

        return self.relu(
            x
            +
            self.block(
                x
            )
        )


class DepthwiseSeparableConv1d(nn.Module):

    def __init__(
        self,
        in_channels,
        out_channels,
        kernel_size,
        activation=True
    ):

        super().__init__()

        padding = kernel_size // 2

        layers = [

            nn.Conv1d(
                in_channels,
                in_channels,
                kernel_size=kernel_size,
                padding=padding,
                groups=in_channels
            ),

            nn.Conv1d(
                in_channels,
                out_channels,
                kernel_size=1
            ),

            nn.BatchNorm1d(
                out_channels
            ),
        ]

        if activation:
            layers.append(
                nn.ReLU()
            )

        self.block = nn.Sequential(
            *layers
        )


    def forward(
        self,
        x
    ):

        return self.block(
            x
        )


class DSResidualBlock(nn.Module):

    def __init__(
        self,
        channels
    ):

        super().__init__()

        self.conv1 = DepthwiseSeparableConv1d(
            channels,
            channels,
            3,
            activation=True
        )

        self.conv2 = DepthwiseSeparableConv1d(
            channels,
            channels,
            3,
            activation=False
        )

        self.relu = nn.ReLU()


    def forward(
        self,
        x
    ):

        residual = x

        x = self.conv1(
            x
        )

        x = self.conv2(
            x
        )

        return self.relu(
            x
            +
            residual
        )


class V25Dense64(nn.Module):

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
                64,
                kernel_size=5,
                padding=2
            ),

            nn.BatchNorm1d(
                64
            ),

            nn.ReLU(),

            DenseResidualBlock(
                64
            ),
        )

        self.pool = nn.AdaptiveAvgPool1d(
            1
        )

        self.classifier = nn.Linear(
            64,
            num_classes
        )


    def extract_features(
        self,
        x
    ):

        x = to_bct(
            x
        )

        x = self.attention(
            x
        )

        x = self.features(
            x
        )

        return self.pool(
            x
        ).squeeze(
            -1
        )


    def forward_with_features(
        self,
        x
    ):

        features = self.extract_features(
            x
        )

        logits = self.classifier(
            features
        )

        return logits, features


    def forward(
        self,
        x
    ):

        logits, _ = self.forward_with_features(
            x
        )

        return logits


class V25DS96(nn.Module):

    def __init__(
        self,
        num_classes,
        input_channels=6
    ):

        super().__init__()

        self.attention = ChannelReliabilityAttention(
            input_channels
        )

        self.stem = nn.Sequential(

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
        )

        self.expand = DepthwiseSeparableConv1d(
            64,
            96,
            5,
            activation=True
        )

        self.residual = DSResidualBlock(
            96
        )

        self.pool = nn.AdaptiveAvgPool1d(
            1
        )

        self.classifier = nn.Linear(
            96,
            num_classes
        )


    def extract_features(
        self,
        x
    ):

        x = to_bct(
            x
        )

        x = self.attention(
            x
        )

        x = self.stem(
            x
        )

        x = self.expand(
            x
        )

        x = self.residual(
            x
        )

        return self.pool(
            x
        ).squeeze(
            -1
        )


    def forward_with_features(
        self,
        x
    ):

        features = self.extract_features(
            x
        )

        logits = self.classifier(
            features
        )

        return logits, features


    def forward(
        self,
        x
    ):

        logits, _ = self.forward_with_features(
            x
        )

        return logits


CANDIDATES = {

    "V25Dense64":
        V25Dense64,

    "V25DS96":
        V25DS96,
}


def create_candidate(
    name,
    num_classes,
    input_channels=6
):

    if name not in CANDIDATES:
        raise KeyError(
            name
        )

    return CANDIDATES[
        name
    ](
        num_classes=num_classes,
        input_channels=input_channels
    )
