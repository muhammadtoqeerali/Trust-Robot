"""Local-linearization 15D Schur information priors.

This module is mathematics infrastructure for the analytic
TRUST-ROBOT rolling-state estimator.

A stored Gaussian prior approximates selected factors at a
fixed linearization point. This is not physical observability
or posterior consistency certification.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping

import numpy as np

STATE_DIM = 15


def _vec(value, length, name):
    result = np.asarray(value, dtype=np.float64)

    if (
        result.shape != (length,)
        or not np.isfinite(result).all()
    ):
        raise ValueError(
            f"Invalid {name}: expected finite {length}-vector"
        )

    return result


@dataclass(frozen=True)
class SquareRootInformationPrior:
    node_ids: tuple[int, ...]
    reference: np.ndarray
    square_root_information: np.ndarray
    residual_offset: np.ndarray

    def __post_init__(self):
        dim = STATE_DIM * len(self.node_ids)

        if (
            not self.node_ids
            or len(set(self.node_ids)) != len(self.node_ids)
            or not all(
                isinstance(i, int) and i >= 0
                for i in self.node_ids
            )
        ):
            raise ValueError("Invalid prior node IDs")

        _vec(self.reference, dim, "prior reference")

        S = np.asarray(
            self.square_root_information,
            dtype=np.float64,
        )
        b = np.asarray(
            self.residual_offset,
            dtype=np.float64,
        )

        if (
            S.ndim != 2
            or S.shape[1] != dim
            or S.shape[0] < 1
            or b.shape != (S.shape[0],)
            or not np.isfinite(S).all()
            or not np.isfinite(b).all()
        ):
            raise ValueError(
                "Invalid square-root information prior"
            )

    def residual(
        self,
        states: Mapping[int, np.ndarray],
    ) -> np.ndarray:
        concatenated = np.concatenate([
            _vec(
                states[k],
                STATE_DIM,
                f"state {k}",
            )
            for k in self.node_ids
        ])

        return (
            self.square_root_information
            @ (concatenated - self.reference)
            + self.residual_offset
        )

    def normal_equations(self):
        S = self.square_root_information

        return (
            S.T @ S,
            S.T @ self.residual_offset,
        )


def synthetic_initial_anchor(
    initial_state: np.ndarray,
    sigma: float = 0.1,
):
    """Explicit synthetic gauge anchor, not a measured prior."""
    x = _vec(
        initial_state,
        STATE_DIM,
        "initial state",
    )

    if not np.isfinite(sigma) or sigma <= 0:
        raise ValueError("Invalid synthetic anchor sigma")

    return SquareRootInformationPrior(
        (0,),
        x.copy(),
        np.eye(STATE_DIM) / sigma,
        np.zeros(STATE_DIM),
    )


def information_prior(
    node_ids,
    reference,
    information,
    gradient,
):
    """Construct PSD least-squares prior H=S.T@S, g=S.T@b.

    Zero-information directions remain unconstrained.
    They are not silently regularized into observations.
    """
    ids = tuple(node_ids)
    dim = len(ids) * STATE_DIM

    ref = _vec(
        reference,
        dim,
        "prior reference",
    )
    H = np.asarray(
        information,
        dtype=np.float64,
    )
    g = _vec(
        gradient,
        dim,
        "prior gradient",
    )

    if (
        H.shape != (dim, dim)
        or not np.isfinite(H).all()
        or not np.allclose(
            H,
            H.T,
            atol=1e-8,
            rtol=1e-8,
        )
    ):
        raise ValueError(
            "Invalid symmetric information matrix"
        )

    H = 0.5 * (H + H.T)

    eigenvalues, eigenvectors = np.linalg.eigh(H)

    threshold = max(
        1e-10,
        1e-10 * max(
            1.0,
            float(eigenvalues[-1]),
        ),
    )

    if eigenvalues[0] < -threshold:
        raise ValueError(
            "Negative information eigenvalue"
        )

    retained = eigenvalues > threshold

    if not np.any(retained):
        raise ValueError(
            "No supported prior information"
        )

    null_gradient = (
        eigenvectors[:, ~retained].T @ g
    )

    if np.linalg.norm(null_gradient) > (
        1e-5 * max(1.0, np.linalg.norm(g))
    ):
        raise ValueError(
            "Gradient has unsupported null-space component"
        )

    values = eigenvalues[retained]
    vectors = eigenvectors[:, retained]

    sqrt_H = (
        np.sqrt(values)[:, None]
        * vectors.T
    )

    offset = (
        vectors.T @ g
    ) / np.sqrt(values)

    return SquareRootInformationPrior(
        ids,
        ref.copy(),
        sqrt_H,
        offset,
    )


def finite_difference_linearization(
    residual_fn: Callable,
    x,
    eps=2e-6,
):
    """Central-difference Jacobian at a fixed linearization."""
    x = np.asarray(x, dtype=np.float64)

    if (
        x.ndim != 1
        or not np.isfinite(x).all()
        or not 0 < eps < 1e-3
    ):
        raise ValueError(
            "Invalid linearization arguments"
        )

    def evaluate(z):
        value = np.asarray(
            residual_fn(z),
            dtype=np.float64,
        )

        if (
            value.ndim != 1
            or value.size < 1
            or not np.isfinite(value).all()
        ):
            raise ValueError(
                "Nonfinite or invalid residual"
            )

        return value

    baseline = evaluate(x)
    J = np.empty((baseline.size, x.size))

    for k in range(x.size):
        delta = np.zeros_like(x)
        delta[k] = eps

        up = evaluate(x + delta)
        down = evaluate(x - delta)

        if (
            up.shape != baseline.shape
            or down.shape != baseline.shape
        ):
            raise ValueError(
                "Residual size changed during linearization"
            )

        J[:, k] = (
            up - down
        ) / (2.0 * eps)

    return baseline, J


def marginalize_one(
    node_ids,
    reference_states,
    residual_fn,
    eliminate_node,
):
    """Eliminate one 15D state from selected factor residuals.

    The caller must supply the previous prior and every
    unconsumed factor incident to the eliminated node.

    Independent factors that remain active must be excluded
    here, otherwise measurement double counting occurs.
    """
    ids = tuple(node_ids)

    if (
        len(ids) < 2
        or len(set(ids)) != len(ids)
        or eliminate_node not in ids
    ):
        raise ValueError(
            "Invalid marginalization node set"
        )

    reference = np.concatenate([
        _vec(
            reference_states[k],
            STATE_DIM,
            f"state {k}",
        )
        for k in ids
    ])

    def stacked_residual(flat):
        states = {
            k: flat[
                i * STATE_DIM:
                (i + 1) * STATE_DIM
            ]
            for i, k in enumerate(ids)
        }

        return residual_fn(states)

    r0, J = finite_difference_linearization(
        stacked_residual,
        reference,
    )

    H = J.T @ J
    g = J.T @ r0

    first = (
        ids.index(eliminate_node)
        * STATE_DIM
    )

    eliminated = np.arange(
        first,
        first + STATE_DIM,
    )

    kept = np.asarray([
        j
        for j in range(len(reference))
        if (
            j < first
            or j >= first + STATE_DIM
        )
    ], dtype=int)

    Hmm = H[np.ix_(
        eliminated,
        eliminated,
    )]

    values = np.linalg.eigvalsh(Hmm)

    if values[0] <= max(
        1e-11,
        1e-11 * values[-1],
    ):
        raise ValueError(
            "Marginalized state has singular information pivot"
        )

    Hkm = H[np.ix_(
        kept,
        eliminated,
    )]
    Hmk = H[np.ix_(
        eliminated,
        kept,
    )]

    reduced_H = (
        H[np.ix_(kept, kept)]
        - Hkm @ np.linalg.solve(Hmm, Hmk)
    )

    reduced_g = (
        g[kept]
        - Hkm @ np.linalg.solve(
            Hmm,
            g[eliminated],
        )
    )

    remaining_ids = tuple(
        k
        for k in ids
        if k != eliminate_node
    )

    prior = information_prior(
        remaining_ids,
        reference[kept],
        reduced_H,
        reduced_g,
    )

    return prior, {
        "eliminated_node": eliminate_node,
        "retained_nodes": list(remaining_ids),
        "elimination_pivot_min_eigenvalue":
            float(values[0]),
        "retained_prior_rank":
            int(prior.square_root_information.shape[0]),
        "retained_state_dimension":
            int(len(kept)),
        "consumed_factor_residual_dimension":
            int(r0.size),
        "fixed_first_estimate_linearization": True,
        "physical_observability_proven": False,
        "probabilistic_consistency_proven": False,
    }
