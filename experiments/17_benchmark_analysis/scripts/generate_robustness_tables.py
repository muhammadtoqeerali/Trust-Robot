import sys
from pathlib import Path

sys.path.insert(
    0,
    "experiments/17_benchmark_analysis"
)


from engine.reliability_collector import (
    collect_reliability_results
)

from engine.robustness_analyzer import (
    aggregate_robustness,
    aggregate_corruption_type
)



OUT=Path(
"experiments/17_benchmark_analysis/results/tables"
)

OUT.mkdir(
    parents=True,
    exist_ok=True
)



records=collect_reliability_results(
    "results/benchmark_v1/UCI_HAR/reliability"
)



robustness=aggregate_robustness(
    records
)


corruption=aggregate_corruption_type(
    records
)



robustness.to_csv(
    OUT/"robustness_summary.csv",
    index=False
)


corruption.to_csv(
    OUT/"robustness_by_corruption.csv",
    index=False
)



print(
"ROBUSTNESS_ROWS:",
len(robustness)
)


print(
"ROBUSTNESS_TABLE_GENERATION_PASS=True"
)
