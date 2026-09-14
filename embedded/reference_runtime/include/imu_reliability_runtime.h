#ifndef IMU_RELIABILITY_RUNTIME_H
#define IMU_RELIABILITY_RUNTIME_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef uint8_t ir_task_class_t;
enum {
    IR_CLASS_ACTIVITY = 0u,
    IR_CLASS_FALLING = 1u
};

typedef uint8_t ir_trust_state_t;
enum {
    IR_TRUST_VALID = 0u,
    IR_TRUST_OOD_UNKNOWN = 1u,
    IR_TRUST_INTEGRITY_ALERT = 2u
};

typedef uint8_t ir_status_t;
enum {
    IR_STATUS_OK = 0u,
    IR_STATUS_NULL_OUTPUT = 1u,
    IR_STATUS_NONFINITE_LOGIT = 2u,
    IR_STATUS_UNSUPPORTED_HARD_CAUSE = 3u
};

#define IR_CAUSE_NONE ((uint32_t)0u)
#define IR_CAUSE_FRAME_GAP ((uint32_t)1u)

#define IR_SUPPORTED_HARD_CAUSE_MASK \
    ((uint32_t)IR_CAUSE_FRAME_GAP)

/*
 * Exact binary32 constants frozen by
 * PORTABLE_C_RUNTIME_SEMANTIC_CONTRACT_V1.
 *
 * 0x1.2baa4p-7f -> bits 0x3c15d520
 * 0x1.ccccccp-1f -> bits 0x3f666666
 */
#define IR_OOD_THRESHOLD \
    (0x1.2baa4p-7f)

#define IR_HISTORICAL_PREDICTION_BIAS \
    (0x1.ccccccp-1f)

typedef struct {
    uint8_t task_prediction;
    ir_trust_state_t trust_state;
    uint32_t integrity_cause_mask;
    uint32_t suspect_mask;
    float ood_margin;
    float ood_threshold;
} ir_decision_t;

/*
 * Portable post-logit reliability decision.
 *
 * The task-model inference is upstream and is NOT called here.
 * hard_cause_mask contains already-qualified hard causes.
 *
 * On any non-IR_STATUS_OK return, *out remains unmodified.
 */
ir_status_t ir_decide_from_logits(
    float logit_activity,
    float logit_falling,
    uint32_t hard_cause_mask,
    uint32_t suspect_mask,
    ir_decision_t *out
);

#ifdef __cplusplus
}
#endif

#endif
