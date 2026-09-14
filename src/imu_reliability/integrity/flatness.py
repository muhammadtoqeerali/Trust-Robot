from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .evidence import (
    EvidenceStatus,
    IntegrityEvidence,
    SuspectIndicator,
)


@dataclass(frozen=True)
class ChannelFreezeConfig:
    """
    Generic implementation parameters.

    These values are NOT the frozen experimental operating point.
    The caller must provide development-selected values later.
    """

    absolute_tolerance: float
    consecutive_deltas: int

    def __post_init__(self) -> None:
        if self.absolute_tolerance < 0:
            raise ValueError(
                "absolute_tolerance must be >= 0"
            )

        if self.consecutive_deltas < 1:
            raise ValueError(
                "consecutive_deltas must be >= 1"
            )


class ChannelFreezeMonitor:
    """
    Incremental per-channel near-equality monitor.

    It deliberately emits only CHANNEL_FREEZE_SUSPECT.
    It cannot emit a hard external cause.
    """

    def __init__(
        self,
        n_channels: int,
        config: ChannelFreezeConfig,
    ) -> None:

        if n_channels < 1:
            raise ValueError(
                "n_channels must be >= 1"
            )

        self.n_channels = int(n_channels)
        self.config = config

        self._previous: np.ndarray | None = None

        self._runs = np.zeros(
            self.n_channels,
            dtype=np.int64,
        )


    def reset(self) -> None:
        self._previous = None
        self._runs.fill(0)


    def update(
        self,
        sample,
        *,
        source: str,
    ) -> list[IntegrityEvidence]:

        current = np.asarray(
            sample,
            dtype=np.float64,
        )

        if current.shape != (
            self.n_channels,
        ):
            raise ValueError(
                "Expected sample shape "
                f"({self.n_channels},), "
                f"got {current.shape}"
            )

        if self._previous is None:
            self._previous = current.copy()
            return []

        unchanged = np.abs(
            current - self._previous
        ) <= self.config.absolute_tolerance

        self._runs[unchanged] += 1
        self._runs[~unchanged] = 0

        self._previous = current.copy()

        evidence: list[IntegrityEvidence] = []

        for channel_index, run_length in enumerate(
            self._runs.tolist()
        ):
            if (
                run_length
                < self.config.consecutive_deltas
            ):
                continue

            evidence.append(
                IntegrityEvidence(
                    indicator="CHANNEL_NEAR_CONSTANT",
                    status=EvidenceStatus.SUSPECT_ONLY,
                    suspect=(
                        SuspectIndicator
                        .CHANNEL_FREEZE_SUSPECT
                    ),
                    source=source,
                    details={
                        "channel_index":
                            channel_index,
                        "consecutive_deltas":
                            run_length,
                        "absolute_tolerance":
                            self.config.absolute_tolerance,
                    },
                )
            )

        return evidence
