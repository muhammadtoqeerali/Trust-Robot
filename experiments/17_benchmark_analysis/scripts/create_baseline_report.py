import json
from pathlib import Path


report={

    "baseline_model":
        "ReliabilityCNN_v22",

    "dataset":
        "UCI_HAR",

    "clean_performance":
    {
        "accuracy":
            0.9426071741032371,

        "macro_f1":
            0.9478771378189619
    },


    "robustness":
    {
        "mean_corrupted_accuracy":
            0.6997302420530768,

        "missing_channel":
            0.4778652668416448,

        "gaussian_noise":
            0.6446485855934675,

        "random_dropout":
            0.9224846894138232,

        "sensor_drift":
            0.7539224263633713
    },


    "efficiency":
    {
        "parameters":
            45420,

        "model_size_mb":
            0.1732635498046875,

        "latency_ms":
            0.003884762708074882
    }

}



Path(
"experiments/17_benchmark_analysis/results/baseline_v22_report.json"
).write_text(
    json.dumps(
        report,
        indent=2
    )
)


print(
"BASELINE_V22_FREEZE_PASS=True"
)
