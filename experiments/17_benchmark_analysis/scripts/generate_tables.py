import sys
from pathlib import Path

sys.path.insert(
    0,
    "experiments/17_benchmark_analysis"
)


from engine.benchmark_collector import (
    collect_benchmark_results
)

from engine.reliability_collector import (
    collect_reliability_results
)

from engine.aggregator import (
    aggregate_performance,
    aggregate_reliability,
    add_efficiency_metrics
)



OUT=Path(
    "experiments/17_benchmark_analysis/results/tables"
)

OUT.mkdir(
    parents=True,
    exist_ok=True
)



benchmark_records=collect_benchmark_results(
    "results/benchmark_v1/UCI_HAR/raw_runs"
)


reliability_records=collect_reliability_results(
    "results/benchmark_v1/UCI_HAR/reliability"
)



performance=aggregate_performance(
    benchmark_records
)


performance=add_efficiency_metrics(
    performance
)


performance.to_csv(
    OUT/"performance_summary.csv",
    index=False
)



reliability, corruption=aggregate_reliability(
    reliability_records
)


reliability.to_csv(
    OUT/"reliability_summary.csv",
    index=False
)


corruption.to_csv(
    OUT/"reliability_by_corruption.csv",
    index=False
)



efficiency=performance[

    [
        "model",
        "accuracy",
        "macro_f1",
        "parameters",
        "model_size_mb",
        "latency_ms_per_sample",
        "accuracy_per_million_params",
        "f1_per_mb"
    ]

]


efficiency.to_csv(
    OUT/"efficiency_summary.csv",
    index=False
)



print(
"PERFORMANCE_TABLE_ROWS:",
len(performance)
)


print(
"RELIABILITY_TABLE_ROWS:",
len(reliability)
)


print(
"TABLE_GENERATION_PASS=True"
)

