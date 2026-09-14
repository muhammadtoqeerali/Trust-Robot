from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
from types import MappingProxyType
from typing import Any, Mapping
import json

import numpy as np


class P0CorruptionKind(str, Enum):
    FRAME_GAP = "FRAME_GAP"
    FRAME_REPEAT = "FRAME_REPEAT"
    CHANNEL_FREEZE = "CHANNEL_FREEZE"
    TIMING_PERTURBATION = "TIMING_PERTURBATION"
    RANGE_CLIP = "RANGE_CLIP"


def _readonly_array(
    value,
    *,
    dtype=None,
) -> np.ndarray | None:

    if value is None:
        return None

    arr = np.asarray(
        value,
        dtype=dtype,
    ).copy()

    arr.setflags(
        write=False
    )

    return arr


def _canonical_json(
    value,
) -> str:

    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


@dataclass(frozen=True)
class P0InjectionSpec:
    """
    Immutable description of one offline P0 corruption.

    Indices are zero-based and refer to the clean input stream supplied
    to the injector.
    """

    kind: P0CorruptionKind
    start_index: int
    length: int
    severity: str

    channels: tuple[int, ...] = ()
    seed: int = 0

    parameters: Mapping[str, Any] = field(
        default_factory=dict
    )


    def __post_init__(self) -> None:

        object.__setattr__(
            self,
            "kind",
            P0CorruptionKind(
                self.kind
            ),
        )

        if self.start_index < 0:
            raise ValueError(
                "start_index must be >= 0"
            )

        if self.length < 1:
            raise ValueError(
                "length must be >= 1"
            )

        if any(
            int(c) < 0
            for c in self.channels
        ):
            raise ValueError(
                "channel indices must be >= 0"
            )

        channels = tuple(
            int(c)
            for c in self.channels
        )

        if len(set(channels)) != len(channels):
            raise ValueError(
                "channel indices must be unique"
            )

        object.__setattr__(
            self,
            "channels",
            channels,
        )

        params = {
            str(k): v
            for k, v in dict(
                self.parameters
            ).items()
        }

        # Validate JSON serializability now rather than during manifest
        # generation.
        _canonical_json(params)

        object.__setattr__(
            self,
            "parameters",
            MappingProxyType(
                params
            ),
        )


    def canonical_dict(self) -> dict[str, Any]:

        return {
            "kind": self.kind.value,
            "start_index":
                self.start_index,
            "length":
                self.length,
            "severity":
                self.severity,
            "channels":
                list(
                    self.channels
                ),
            "seed":
                self.seed,
            "parameters":
                dict(
                    self.parameters
                ),
        }


    @property
    def spec_id(self) -> str:
        """
        Deterministic identifier for the corruption specification.

        This intentionally does NOT identify a particular dataset
        stream. Per-stream corruption instances receive a separate
        P0Truth.injection_id.
        """

        payload = _canonical_json(
            self.canonical_dict()
        ).encode("utf-8")

        return (
            "P0S_"
            + sha256(
                payload
            ).hexdigest()[:20]
        )


@dataclass(frozen=True)
class P0Stream:
    """
    Immutable sample stream.

    `origin_indices` maps each current row to the corresponding row
    index in the input stream. It allows frame-removal experiments to
    preserve pairing/alignment information.
    """

    values: np.ndarray

    timestamps: np.ndarray | None = None
    counters: np.ndarray | None = None
    origin_indices: np.ndarray | None = None

    source_id: str = ""


    def __post_init__(self) -> None:

        values = _readonly_array(
            self.values
        )

        if values is None:
            raise ValueError(
                "values cannot be None"
            )

        if values.ndim != 2:
            raise ValueError(
                "values must have shape "
                "(n_samples, n_channels)"
            )

        n = values.shape[0]

        timestamps = _readonly_array(
            self.timestamps
        )

        counters = _readonly_array(
            self.counters
        )

        if self.origin_indices is None:
            origin = np.arange(
                n,
                dtype=np.int64,
            )
            origin.setflags(
                write=False
            )
        else:
            origin = _readonly_array(
                self.origin_indices,
                dtype=np.int64,
            )


        for name, arr in (
            (
                "timestamps",
                timestamps,
            ),
            (
                "counters",
                counters,
            ),
            (
                "origin_indices",
                origin,
            ),
        ):

            if (
                arr is not None
                and arr.shape != (n,)
            ):
                raise ValueError(
                    f"{name} must have shape ({n},), "
                    f"got {arr.shape}"
                )


        object.__setattr__(
            self,
            "values",
            values,
        )

        object.__setattr__(
            self,
            "timestamps",
            timestamps,
        )

        object.__setattr__(
            self,
            "counters",
            counters,
        )

        object.__setattr__(
            self,
            "origin_indices",
            origin,
        )


    @property
    def n_samples(self) -> int:
        return int(
            self.values.shape[0]
        )


    @property
    def n_channels(self) -> int:
        return int(
            self.values.shape[1]
        )


    def fingerprint(self) -> str:
        """
        Deterministic content hash for pairing/manifests.
        """

        h = sha256()

        h.update(
            self.source_id.encode(
                "utf-8"
            )
        )

        for name, arr in (
            ("values", self.values),
            (
                "timestamps",
                self.timestamps,
            ),
            (
                "counters",
                self.counters,
            ),
            (
                "origin_indices",
                self.origin_indices,
            ),
        ):

            h.update(
                name.encode(
                    "utf-8"
                )
            )

            if arr is None:
                h.update(
                    b"<NONE>"
                )
                continue

            contiguous = np.ascontiguousarray(
                arr
            )

            h.update(
                contiguous.dtype.str.encode(
                    "ascii"
                )
            )

            h.update(
                _canonical_json(
                    list(
                        contiguous.shape
                    )
                ).encode("utf-8")
            )

            h.update(
                contiguous.tobytes()
            )

        return h.hexdigest()


@dataclass(frozen=True)
class P0Truth:
    """
    Experimental ground truth for one injected corruption.

    This is not runtime causal evidence.

    `injection_id` identifies this particular corruption applied to
    this particular clean stream. `spec.spec_id` identifies only the
    corruption specification.
    """

    spec: P0InjectionSpec
    injection_id: str

    clean_n_samples: int
    corrupt_n_samples: int

    affected_clean_start: int
    affected_clean_end_exclusive: int

    corrupt_anchor_index: int

    details: Mapping[str, Any] = field(
        default_factory=dict
    )


    def __post_init__(self) -> None:

        if not str(self.injection_id).strip():
            raise ValueError(
                "injection_id cannot be empty"
            )

        details = {
            str(k): v
            for k, v in dict(
                self.details
            ).items()
        }

        _canonical_json(
            details
        )

        object.__setattr__(
            self,
            "details",
            MappingProxyType(
                details
            ),
        )


    def manifest_dict(self) -> dict[str, Any]:

        return {
            "injection_id":
                self.injection_id,
            "spec_id":
                self.spec.spec_id,
            "spec":
                self.spec.canonical_dict(),
            "clean_n_samples":
                self.clean_n_samples,
            "corrupt_n_samples":
                self.corrupt_n_samples,
            "affected_clean_start":
                self.affected_clean_start,
            "affected_clean_end_exclusive":
                self.affected_clean_end_exclusive,
            "corrupt_anchor_index":
                self.corrupt_anchor_index,
            "details":
                dict(
                    self.details
                ),
        }


@dataclass(frozen=True)
class P0Pair:
    clean: P0Stream
    corrupt: P0Stream
    truths: tuple[P0Truth, ...]


    def __post_init__(self) -> None:

        object.__setattr__(
            self,
            "truths",
            tuple(
                self.truths
            ),
        )

        if not self.truths:
            raise ValueError(
                "P0Pair must contain at least one truth record"
            )
