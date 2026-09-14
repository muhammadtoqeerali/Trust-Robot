from __future__ import annotations

import sys
from pathlib import Path

import torch
import torch.nn as nn


ROOT = Path(__file__).resolve().parents[2]

SCREEN = (
    ROOT
    / "experiments"
    / "17_v25_screening"
)

if str(SCREEN) not in sys.path:
    sys.path.insert(
        0,
        str(SCREEN),
    )

from v25_candidates import create_candidate


CANDIDATE_IDS = [
    "V26A_V25_PhysCE",
    "V26B_DualGateLite",
    "V26C_DualGateLiteCons",
    "V26D_DualGateCross",
]


class DSBlock(nn.Module):
    """
    Frozen R2 interpretation of protocol-R1 DSBlock.

    No residual connection.

    Depthwise temporal convolution
      -> BatchNorm
      -> SiLU
      -> pointwise 1x1 convolution
      -> BatchNorm
      -> SiLU
    """

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        kernel_size: int,
        stride: int,
    ):
        super().__init__()

        padding = (
            kernel_size // 2
        )

        self.depthwise = nn.Conv1d(
            in_channels,
            in_channels,
            kernel_size=kernel_size,
            stride=stride,
            padding=padding,
            groups=in_channels,
            bias=False,
        )

        self.depthwise_bn = nn.BatchNorm1d(
            in_channels
        )

        self.pointwise = nn.Conv1d(
            in_channels,
            out_channels,
            kernel_size=1,
            bias=False,
        )

        self.pointwise_bn = nn.BatchNorm1d(
            out_channels
        )

        self.act = nn.SiLU()


    def forward(
        self,
        x,
    ):

        x = self.depthwise(
            x
        )

        x = self.depthwise_bn(
            x
        )

        x = self.act(
            x
        )

        x = self.pointwise(
            x
        )

        x = self.pointwise_bn(
            x
        )

        x = self.act(
            x
        )

        return x


class ModalityBranch(nn.Module):

    def __init__(
        self,
    ):
        super().__init__()

        self.stem = nn.Sequential(
            nn.Conv1d(
                3,
                24,
                kernel_size=5,
                stride=1,
                padding=2,
                bias=False,
            ),
            nn.BatchNorm1d(
                24
            ),
            nn.SiLU(),
        )

        self.blocks = nn.Sequential(
            DSBlock(
                24,
                32,
                kernel_size=5,
                stride=2,
            ),
            DSBlock(
                32,
                48,
                kernel_size=5,
                stride=2,
            ),
            DSBlock(
                48,
                48,
                kernel_size=3,
                stride=1,
            ),
        )

        self.pool = nn.AdaptiveAvgPool1d(
            1
        )


    def forward(
        self,
        x,
    ):
        # x: [B,T,3]

        x = x.transpose(
            1,
            2,
        )

        x = self.stem(
            x
        )

        x = self.blocks(
            x
        )

        x = self.pool(
            x
        )

        return x.squeeze(
            -1
        )


class ReliabilityGate(nn.Module):

    def __init__(
        self,
    ):
        super().__init__()

        self.net = nn.Sequential(
            nn.Linear(
                48,
                16,
            ),
            nn.SiLU(),
            nn.Linear(
                16,
                1,
            ),
            nn.Sigmoid(),
        )


    def forward(
        self,
        h,
    ):

        return self.net(
            h
        )


class DualGateLite(nn.Module):

    def __init__(
        self,
        num_classes: int,
        cross_interaction: bool,
    ):
        super().__init__()

        self.cross_interaction = (
            bool(
                cross_interaction
            )
        )

        self.acc_branch = (
            ModalityBranch()
        )

        self.gyro_branch = (
            ModalityBranch()
        )

        self.acc_gate = (
            ReliabilityGate()
        )

        self.gyro_gate = (
            ReliabilityGate()
        )


        if self.cross_interaction:

            fusion_dim = 192

        else:

            fusion_dim = 144


        self.classifier = nn.Sequential(
            nn.Linear(
                fusion_dim,
                64,
            ),
            nn.SiLU(),
            nn.Dropout(
                0.10
            ),
            nn.Linear(
                64,
                num_classes,
            ),
        )


    def encode_modalities(
        self,
        x,
    ):

        if x.ndim != 3:

            raise ValueError(
                "Expected [B,T,6]"
            )


        if x.shape[-1] != 6:

            raise ValueError(
                "Expected six IMU channels"
            )


        acc = x[
            :,
            :,
            0:3,
        ]

        gyro = x[
            :,
            :,
            3:6,
        ]


        h_acc = self.acc_branch(
            acc
        )

        h_gyro = self.gyro_branch(
            gyro
        )


        r_acc = self.acc_gate(
            h_acc
        )

        r_gyro = self.gyro_gate(
            h_gyro
        )


        return (
            h_acc,
            h_gyro,
            r_acc,
            r_gyro,
        )


    def forward_with_reliability(
        self,
        x,
    ):

        (
            h_acc,
            h_gyro,
            r_acc,
            r_gyro,
        ) = self.encode_modalities(
            x
        )


        components = [
            r_acc * h_acc,
            r_gyro * h_gyro,
            torch.abs(
                h_acc
                -
                h_gyro
            ),
        ]


        if self.cross_interaction:

            components.append(
                h_acc
                *
                h_gyro
            )


        fused = torch.cat(
            components,
            dim=1,
        )


        logits = self.classifier(
            fused
        )


        aux = {
            "acc_reliability":
                r_acc,

            "gyro_reliability":
                r_gyro,

            "acc_features":
                h_acc,

            "gyro_features":
                h_gyro,
        }


        return (
            logits,
            aux,
        )


    def forward(
        self,
        x,
    ):

        logits, _ = (
            self.forward_with_reliability(
                x
            )
        )

        return logits


def create_v26_candidate(
    candidate_id: str,
    num_classes: int,
    input_channels: int = 6,
):

    if input_channels != 6:

        raise ValueError(
            "Frozen V26 protocol requires "
            "six IMU channels"
        )


    if candidate_id == "V26A_V25_PhysCE":

        return create_candidate(
            "V25Dense64",
            num_classes,
            input_channels=6,
        )


    if candidate_id in {
        "V26B_DualGateLite",
        "V26C_DualGateLiteCons",
    }:

        return DualGateLite(
            num_classes=num_classes,
            cross_interaction=False,
        )


    if candidate_id == "V26D_DualGateCross":

        return DualGateLite(
            num_classes=num_classes,
            cross_interaction=True,
        )


    raise KeyError(
        f"Unknown candidate: "
        f"{candidate_id}"
    )


def parameter_count(
    model,
):

    return int(
        sum(
            p.numel()
            for p in model.parameters()
        )
    )
