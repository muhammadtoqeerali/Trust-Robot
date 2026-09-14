# RC-RGD-IMU

Research code for reliable and compact IMU-based human activity recognition under heterogeneous sensor faults.

This repository contains the implementation, experiment logic, configurations, tests, embedded reference code, and pinned external comparison methods used in the RC-RGD-IMU research project.

## Scope

The repository covers:

- IMU data-integrity monitoring
- heterogeneous sensor-fault injection and evaluation
- reliability-aware runtime decisions
- robustness evaluation under sensor corruption
- out-of-distribution evaluation
- cross-dataset benchmarking
- model efficiency and deployment analysis
- embedded/runtime reference implementations
- reproducibility protocols and experiment scripts

Datasets, trained checkpoints, generated experiment outputs, result tables, logs, and workstation forensic artifacts are intentionally not included.

## Repository structure

    configs/                 Experiment and protocol configurations
    docs/                    Provenance, taxonomy, portability, and project documentation
    embedded/                Reference embedded/runtime implementation
    experiments/             Training, evaluation, robustness, and benchmark scripts
    external/                Pinned external comparison methods
    external_references/     Additional external research references
    models/                  Model architectures
    requirements/            Python dependency specifications
    src/imu_reliability/     Core reliability implementation
    tests/                   Unit, integration, protocol, and reproducibility tests

## Clone

Clone together with the pinned external dependencies:

    git clone --recurse-submodules git@github.com:muhammadtoqeerali/RC-RGD-IMU.git
    cd RC-RGD-IMU

If already cloned without submodules:

    git submodule update --init --recursive

## Environment

Create a Python environment:

    python -m venv .venv
    source .venv/bin/activate
    python -m pip install --upgrade pip
    pip install -r requirements/base.txt

Some historical experiments may require additional dependencies from the original research environment.

## Dataset configuration

Datasets are not distributed with this repository.

Use:

    configs/datasets/local_paths.example.yaml

to create a local configuration:

    cp configs/datasets/local_paths.example.yaml configs/datasets/local_paths.yaml

Then edit `configs/datasets/local_paths.yaml` for the local dataset locations.

`local_paths.yaml` is intentionally excluded from Git.

## Reproducibility

Experiment logic and protocol definitions are preserved under:

    configs/
    experiments/
    docs/

Useful documentation includes:

    docs/experiment_registry.md
    docs/provenance.md
    docs/operating_point_freeze.md
    docs/protected_baseline_v1.md
    docs/taxonomy.md
    docs/PORTABILITY.md

Some frozen historical experiment scripts preserve absolute paths from the original research workstation. These document the original execution environment and may need adaptation before execution on another machine.

## External comparison methods

The project pins the following external implementations to the revisions used during the research:

- TCUQ — a007aa47627f2f0c5e32edf35114670f44495082
- SNAP-UQ — 9a2ef68a1fa68923fd5b8642094b718714cef445
- TrustTiny-HAR — de5a3b8380780322f2d10c4aeca016a09c1332e7
- HAROOD — 3c2ce00e2b408ddd913c3d179cd86daf0c44bc90
- STORM app — dc418c2e2ee6fd80296cb9a5931eb260c810c7bf

Third-party code remains subject to the licensing terms of its respective upstream repository.

## Tests

From the repository root:

    pytest tests

Individual experiment directories may contain additional experiment-specific tests.

## Data and generated artifacts

The public repository intentionally excludes:

- raw datasets
- processed dataset payloads
- generated experimental results
- trained model checkpoints
- exported model binaries
- runtime logs
- temporary files
- workstation forensic reports

The repository therefore focuses on source code, research logic, configurations, tests, and reproducibility.

## Portability

See `docs/PORTABILITY.md` for details about historical workstation paths and adapting experiments to another system.
