#include "imu_reliability_runtime.h"

#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>


static float f32_from_bits(
    uint32_t bits
)
{
    float value;

    memcpy(
        &value,
        &bits,
        sizeof(value)
    );

    return value;
}


static uint32_t f32_bits(
    float value
)
{
    uint32_t bits;

    memcpy(
        &bits,
        &value,
        sizeof(bits)
    );

    return bits;
}


static void assert_output_unchanged(
    const ir_decision_t *before,
    const ir_decision_t *after
)
{
    assert(
        memcmp(
            before,
            after,
            sizeof(*before)
        )
        == 0
    );
}


static void test_constant_bits(
    void
)
{
    assert(
        f32_bits(
            IR_OOD_THRESHOLD
        )
        == UINT32_C(0x3c15d520)
    );

    assert(
        f32_bits(
            IR_HISTORICAL_PREDICTION_BIAS
        )
        == UINT32_C(0x3f666666)
    );
}


static void test_valid_activity(
    void
)
{
    ir_decision_t out;
    ir_status_t status;

    status = ir_decide_from_logits(
        1.0f,
        0.0f,
        IR_CAUSE_NONE,
        UINT32_C(0),
        &out
    );

    assert(status == IR_STATUS_OK);
    assert(out.task_prediction == IR_CLASS_ACTIVITY);
    assert(out.trust_state == IR_TRUST_VALID);
    assert(out.integrity_cause_mask == IR_CAUSE_NONE);
    assert(out.ood_margin == 1.0f);
    assert(out.ood_threshold == IR_OOD_THRESHOLD);
}


static void test_equal_logits_are_ood_unknown(
    void
)
{
    ir_decision_t out;

    assert(
        ir_decide_from_logits(
            0.0f,
            0.0f,
            IR_CAUSE_NONE,
            UINT32_C(0),
            &out
        )
        == IR_STATUS_OK
    );

    assert(out.task_prediction == IR_CLASS_ACTIVITY);
    assert(out.trust_state == IR_TRUST_OOD_UNKNOWN);
    assert(out.ood_margin == 0.0f);
}


static void test_historical_rule_is_not_plain_argmax(
    void
)
{
    ir_decision_t out;

    assert(
        ir_decide_from_logits(
            0.0f,
            2.0f,
            IR_CAUSE_NONE,
            UINT32_C(0),
            &out
        )
        == IR_STATUS_OK
    );

    /*
     * Falling logit is larger, but P(Falling) is below
     * the historical strict > 0.9 threshold.
     */
    assert(out.task_prediction == IR_CLASS_ACTIVITY);
    assert(out.trust_state == IR_TRUST_VALID);
}


static void test_confident_falling(
    void
)
{
    ir_decision_t out;

    assert(
        ir_decide_from_logits(
            0.0f,
            3.0f,
            IR_CAUSE_NONE,
            UINT32_C(0),
            &out
        )
        == IR_STATUS_OK
    );

    assert(out.task_prediction == IR_CLASS_FALLING);
    assert(out.trust_state == IR_TRUST_VALID);
}


static void test_ood_threshold_adjacent_float32_values(
    void
)
{
    const float below = f32_from_bits(
        UINT32_C(0x3c15d51f)
    );

    const float equal = f32_from_bits(
        UINT32_C(0x3c15d520)
    );

    const float above = f32_from_bits(
        UINT32_C(0x3c15d521)
    );

    ir_decision_t out;

    assert(below < IR_OOD_THRESHOLD);
    assert(equal == IR_OOD_THRESHOLD);
    assert(above > IR_OOD_THRESHOLD);

    assert(
        ir_decide_from_logits(
            0.0f,
            below,
            IR_CAUSE_NONE,
            UINT32_C(0),
            &out
        )
        == IR_STATUS_OK
    );

    assert(out.ood_margin == below);
    assert(out.trust_state == IR_TRUST_OOD_UNKNOWN);

    assert(
        ir_decide_from_logits(
            0.0f,
            equal,
            IR_CAUSE_NONE,
            UINT32_C(0),
            &out
        )
        == IR_STATUS_OK
    );

    assert(out.ood_margin == equal);
    assert(out.trust_state == IR_TRUST_VALID);

    assert(
        ir_decide_from_logits(
            0.0f,
            above,
            IR_CAUSE_NONE,
            UINT32_C(0),
            &out
        )
        == IR_STATUS_OK
    );

    assert(out.ood_margin == above);
    assert(out.trust_state == IR_TRUST_VALID);
}


static void test_integrity_precedes_ood(
    void
)
{
    ir_decision_t out;

    assert(
        ir_decide_from_logits(
            0.0f,
            0.0f,
            IR_CAUSE_FRAME_GAP,
            UINT32_C(0),
            &out
        )
        == IR_STATUS_OK
    );

    assert(out.task_prediction == IR_CLASS_ACTIVITY);
    assert(out.ood_margin == 0.0f);
    assert(out.trust_state == IR_TRUST_INTEGRITY_ALERT);
    assert(out.integrity_cause_mask == IR_CAUSE_FRAME_GAP);
}


static void test_suspect_mask_is_passthrough_only(
    void
)
{
    const uint32_t suspect = UINT32_C(0xa5a55a5a);
    ir_decision_t out;

    assert(
        ir_decide_from_logits(
            1.0f,
            0.0f,
            IR_CAUSE_NONE,
            suspect,
            &out
        )
        == IR_STATUS_OK
    );

    assert(out.suspect_mask == suspect);
    assert(out.trust_state == IR_TRUST_VALID);
}


static void test_unsupported_hard_cause_rejected_without_output_change(
    void
)
{
    ir_decision_t out = {
        UINT8_C(77),
        UINT8_C(88),
        UINT32_C(0x11223344),
        UINT32_C(0x55667788),
        123.25f,
        -456.5f
    };

    const ir_decision_t before = out;

    assert(
        ir_decide_from_logits(
            1.0f,
            0.0f,
            UINT32_C(2),
            UINT32_C(0),
            &out
        )
        == IR_STATUS_UNSUPPORTED_HARD_CAUSE
    );

    assert_output_unchanged(
        &before,
        &out
    );
}


static void test_nonfinite_nan_rejected_without_output_change(
    void
)
{
    ir_decision_t out = {
        UINT8_C(7),
        UINT8_C(8),
        UINT32_C(9),
        UINT32_C(10),
        11.0f,
        12.0f
    };

    const ir_decision_t before = out;

    assert(
        ir_decide_from_logits(
            NAN,
            0.0f,
            IR_CAUSE_NONE,
            UINT32_C(0),
            &out
        )
        == IR_STATUS_NONFINITE_LOGIT
    );

    assert_output_unchanged(
        &before,
        &out
    );
}


static void test_nonfinite_inf_rejected_without_output_change(
    void
)
{
    ir_decision_t out = {
        UINT8_C(17),
        UINT8_C(18),
        UINT32_C(19),
        UINT32_C(20),
        21.0f,
        22.0f
    };

    const ir_decision_t before = out;

    assert(
        ir_decide_from_logits(
            0.0f,
            INFINITY,
            IR_CAUSE_NONE,
            UINT32_C(0),
            &out
        )
        == IR_STATUS_NONFINITE_LOGIT
    );

    assert_output_unchanged(
        &before,
        &out
    );
}


static void test_null_output_rejected(
    void
)
{
    assert(
        ir_decide_from_logits(
            0.0f,
            0.0f,
            IR_CAUSE_NONE,
            UINT32_C(0),
            NULL
        )
        == IR_STATUS_NULL_OUTPUT
    );
}


static void test_task_prediction_survives_integrity_alert(
    void
)
{
    ir_decision_t out;

    assert(
        ir_decide_from_logits(
            0.0f,
            3.0f,
            IR_CAUSE_FRAME_GAP,
            UINT32_C(0),
            &out
        )
        == IR_STATUS_OK
    );

    assert(out.task_prediction == IR_CLASS_FALLING);
    assert(out.trust_state == IR_TRUST_INTEGRITY_ALERT);
}


int main(
    void
)
{
    test_constant_bits();
    test_valid_activity();
    test_equal_logits_are_ood_unknown();
    test_historical_rule_is_not_plain_argmax();
    test_confident_falling();
    test_ood_threshold_adjacent_float32_values();
    test_integrity_precedes_ood();
    test_suspect_mask_is_passthrough_only();
    test_unsupported_hard_cause_rejected_without_output_change();
    test_nonfinite_nan_rejected_without_output_change();
    test_nonfinite_inf_rejected_without_output_change();
    test_null_output_rejected();
    test_task_prediction_survives_integrity_alert();

    printf(
        "NATIVE_C_TEST_COUNT = 13\n"
    );

    printf(
        "NATIVE_C_TESTS_PASS = True\n"
    );

    return 0;
}
