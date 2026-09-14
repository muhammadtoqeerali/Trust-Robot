import torch
from torch import nn


class HistoricalIMUNormalizer(nn.Module):
    """
    Reproduces the recovered Protechto normalization arithmetic.

    Input:
        [batch, 40, 9]

    Output:
        [batch, 40, 6]

    Euler channels are split but not passed to the CNN.
    """

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.ndim != 3:
            raise ValueError(
                f"Expected [B,T,C], got shape {tuple(x.shape)}"
            )

        if x.shape[-1] != 9:
            raise ValueError(
                f"Expected 9 stored channels, got {x.shape[-1]}"
            )

        acc_data, gyro_data, angle_data = torch.split(
            x, 3, dim=2
        )

        # Keep the two historical gyro divisions separate so that the
        # arithmetic follows the recovered implementation exactly.
        gyro_data = gyro_data / torch.tensor(
            1000,
            dtype=torch.float32,
            device=x.device,
        )

        acc_data = acc_data / torch.tensor(
            [4000, 4000, 4000],
            dtype=torch.float32,
            device=x.device,
        )

        gyro_data = gyro_data / torch.tensor(
            [1800, 1800, 1800],
            dtype=torch.float32,
            device=x.device,
        )

        return torch.concat(
            [acc_data, gyro_data],
            dim=-1,
        )


class Date2025CNN400(nn.Module):
    """
    Reconstruction from recovered checkpoint tensor geometry.

    Historical checkpoint evidence:
      input window        : 40 x 9
      effective channels  : 6
      conv channels       : 32
      kernel              : 4
      pool                : 2
      flatten             : 224
      FC                  : 256
      classes             : 2
    """

    WINDOW_SAMPLES = 40
    STORED_CHANNELS = 9
    EFFECTIVE_CHANNELS = 6

    def __init__(self):
        super().__init__()

        self.normalizer = HistoricalIMUNormalizer()

        self.conv_1 = nn.Sequential(
            nn.Conv1d(
                self.EFFECTIVE_CHANNELS,
                32,
                4,
            ),
            nn.BatchNorm1d(32),
            nn.PReLU(),
            nn.MaxPool1d(2),
            nn.Dropout(p=0.1),
        )

        self.conv_2 = nn.Sequential(
            nn.Conv1d(
                32,
                32,
                4,
            ),
            nn.BatchNorm1d(32),
            nn.PReLU(),
            nn.MaxPool1d(2),
            nn.Dropout(p=0.4),
        )

        # 40 -> 37 -> 18 -> 15 -> 7
        # 7 * 32 = 224
        self.fc = nn.Sequential(
            nn.Flatten(),
            nn.Linear(224, 256),
            nn.PReLU(),
            nn.Dropout(p=0.2),
            nn.Linear(256, 2),
        )

    def _backbone(
        self,
        x: torch.Tensor,
    ) -> torch.Tensor:
        if x.shape[1] != self.WINDOW_SAMPLES:
            raise ValueError(
                "This protected checkpoint requires exactly "
                f"{self.WINDOW_SAMPLES} samples; got {x.shape[1]}."
            )

        x = self.normalizer(x)
        x = x.permute(0, 2, 1)
        x = self.conv_1(x)
        x = self.conv_2(x)

        return x

    def forward(
        self,
        x: torch.Tensor,
    ) -> torch.Tensor:
        """
        Reference task-only forward.
        """
        x = self._backbone(x)
        return self.fc(x)

    def forward_with_features(
        self,
        x: torch.Tensor,
    ):
        """
        Single task-model forward returning:
          logits   [B,2]
          feature  [B,256]

        The feature is the post-PReLU penultimate representation.
        No second backbone/task forward is performed.
        """
        x = self._backbone(x)

        flat = self.fc[0](x)
        hidden = self.fc[1](flat)
        feature = self.fc[2](hidden)
        dropped = self.fc[3](feature)
        logits = self.fc[4](dropped)

        return logits, feature
