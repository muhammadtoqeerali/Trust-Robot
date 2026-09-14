from __future__ import annotations

import torch
import torch.nn.functional as F


CONSISTENCY_CANDIDATES = {
    "V26C_DualGateLiteCons",
    "V26D_DualGateCross",
}


def symmetric_kl(
    clean_logits,
    fault_logits,
):

    clean_logp = F.log_softmax(
        clean_logits,
        dim=1,
    )

    fault_logp = F.log_softmax(
        fault_logits,
        dim=1,
    )

    clean_p = clean_logp.exp()
    fault_p = fault_logp.exp()


    kl_clean_fault = (
        clean_p
        *
        (
            clean_logp
            -
            fault_logp
        )
    ).sum(
        dim=1
    ).mean()


    kl_fault_clean = (
        fault_p
        *
        (
            fault_logp
            -
            clean_logp
        )
    ).sum(
        dim=1
    ).mean()


    return 0.5 * (
        kl_clean_fault
        +
        kl_fault_clean
    )


def candidate_training_loss(
    candidate_id,
    clean_logits,
    fault_logits,
    labels,
):

    clean_ce = F.cross_entropy(
        clean_logits,
        labels,
    )

    fault_ce = F.cross_entropy(
        fault_logits,
        labels,
    )


    if candidate_id in CONSISTENCY_CANDIDATES:

        consistency = symmetric_kl(
            clean_logits,
            fault_logits,
        )

        total = (
            clean_ce
            +
            fault_ce
            +
            0.20
            *
            consistency
        )

    else:

        consistency = torch.zeros(
            (),
            dtype=clean_logits.dtype,
            device=clean_logits.device,
        )

        total = (
            clean_ce
            +
            fault_ce
        )


    return {
        "loss":
            total,

        "clean_ce":
            clean_ce,

        "fault_ce":
            fault_ce,

        "consistency":
            consistency,
    }
