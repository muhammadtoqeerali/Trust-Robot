"""TRUST-ROBOT scientific implementation.

The inherited ``imu_reliability`` package remains a historical/reference
implementation. New multimodal robotics science is introduced here
incrementally by project phase.
"""

from .data_contracts import (
    ContractError,
    DatasetReadiness,
    DerivativeKind,
    FrameSpec,
    MeasurementTimeBasis,
    ReferenceCoverage,
    ReferenceSpec,
    SplitRole,
    StreamSpec,
    SynchronizationSpec,
    VerificationStatus,
    TrajectoryRecord,
    validate_trajectory_records,
)

__all__ = [
    "ContractError",
    "DatasetReadiness",
    "DerivativeKind",
    "FrameSpec",
    "MeasurementTimeBasis",
    "ReferenceCoverage",
    "ReferenceSpec",
    "SplitRole",
    "StreamSpec",
    "SynchronizationSpec",
    "VerificationStatus",
    "TrajectoryRecord",
    "validate_trajectory_records",
]
