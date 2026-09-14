#include "imu_reliability_runtime.h"

#include <math.h>

_Static_assert(
    IR_CLASS_ACTIVITY == 0u,
    "Activity class value changed"
);

_Static_assert(
    IR_CLASS_FALLING == 1u,
    "Falling class value changed"
);

_Static_assert(
    IR_TRUST_VALID == 0u,
    "VALID trust-state value changed"
);

_Static_assert(
    IR_TRUST_OOD_UNKNOWN == 1u,
    "OOD_UNKNOWN trust-state value changed"
);

_Static_assert(
    IR_TRUST_INTEGRITY_ALERT == 2u,
    "INTEGRITY_ALERT trust-state value changed"
);

_Static_assert(
    IR_CAUSE_FRAME_GAP == 1u,
    "FRAME_GAP cause bit changed"
);


ir_status_t ir_decide_from_logits(
    float logit_activity,
    float logit_falling,
    uint32_t hard_cause_mask,
    uint32_t suspect_mask,
    ir_decision_t *out
)
{
    ir_decision_t candidate;
    float maximum_logit;
    float exp_activity;
    float exp_falling;
    float falling_probability;
    float ood_margin;

    if (out == 0) {
        return IR_STATUS_NULL_OUTPUT;
    }

    if (
        !isfinite(logit_activity)
        || !isfinite(logit_falling)
    ) {
        return IR_STATUS_NONFINITE_LOGIT;
    }

    if (
        (
            hard_cause_mask
            & ~IR_SUPPORTED_HARD_CAUSE_MASK
        )
        != 0u
    ) {
        return IR_STATUS_UNSUPPORTED_HARD_CAUSE;
    }

    maximum_logit = (
        logit_activity > logit_falling
        ? logit_activity
        : logit_falling
    );

    exp_activity = expf(
        logit_activity
        - maximum_logit
    );

    exp_falling = expf(
        logit_falling
        - maximum_logit
    );

    falling_probability = (
        exp_falling
        / (
            exp_activity
            + exp_falling
        )
    );

    if (
        falling_probability
        > IR_HISTORICAL_PREDICTION_BIAS
    ) {
        candidate.task_prediction = (
            (uint8_t)IR_CLASS_FALLING
        );
    } else {
        candidate.task_prediction = (
            (uint8_t)IR_CLASS_ACTIVITY
        );
    }

    ood_margin = fabsf(
        logit_activity
        - logit_falling
    );

    candidate.integrity_cause_mask = (
        hard_cause_mask
    );

    candidate.suspect_mask = (
        suspect_mask
    );

    candidate.ood_margin = (
        ood_margin
    );

    candidate.ood_threshold = (
        IR_OOD_THRESHOLD
    );

    if (
        hard_cause_mask
        != IR_CAUSE_NONE
    ) {
        candidate.trust_state = (
            (ir_trust_state_t)
            IR_TRUST_INTEGRITY_ALERT
        );
    } else if (
        ood_margin
        < IR_OOD_THRESHOLD
    ) {
        candidate.trust_state = (
            (ir_trust_state_t)
            IR_TRUST_OOD_UNKNOWN
        );
    } else {
        candidate.trust_state = (
            (ir_trust_state_t)
            IR_TRUST_VALID
        );
    }

    *out = candidate;

    return IR_STATUS_OK;
}
