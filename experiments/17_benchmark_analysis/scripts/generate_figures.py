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
    aggregate_performance
)

from engine.robustness_analyzer import (
    aggregate_robustness,
    aggregate_corruption_type
)

from engine.visualization import (
    plot_bar,
    plot_heatmap
)



OUT=Path(
    "experiments/17_benchmark_analysis/results/figures"
)

OUT.mkdir(
    parents=True,
    exist_ok=True
)



# ----------------------------
# Performance
# ----------------------------

benchmark=collect_benchmark_results(
    "results/benchmark_v1/UCI_HAR/raw_runs"
)


performance=aggregate_performance(
    benchmark
)


plot_bar(
    performance,
    "model",
    "accuracy",
    OUT/"clean_accuracy.png",
    "Clean Accuracy Comparison"
)



# ----------------------------
# Robustness
# ----------------------------

reliability=collect_reliability_results(
    "results/benchmark_v1/UCI_HAR/reliability"
)


robustness=aggregate_robustness(
    reliability
)


plot_bar(
    robustness,
    "model",
    "corrupted_accuracy",
    OUT/"corrupted_accuracy.png",
    "Mean Corrupted Accuracy"
)


plot_bar(
    robustness,
    "model",
    "reliability_score",
    OUT/"reliability_score.png",
    "Reliability Score"
)



corruption=aggregate_corruption_type(
    reliability
)


plot_heatmap(
    corruption,
    OUT/"corruption_heatmap.png"
)



print(
    "FIGURE_GENERATION_PASS=True"
)

