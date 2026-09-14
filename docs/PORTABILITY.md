# Portability Notes

This repository contains the source code, experiment logic, configurations,
tests, and pinned external dependencies used for the RC-RGD-IMU research work.

Datasets, generated experiment outputs, trained checkpoints, and workstation
artifacts are intentionally not included.

Some frozen historical experiment scripts preserve absolute paths from the
original research workstation, including paths under:

- /mnt/hdd16T/protechto
- /mnt/hdd16T/ToqeerHomeBackup

These paths document the original execution environment and should be adapted
to the local environment before re-running those historical scripts.

For dataset path configuration, use:

    configs/datasets/local_paths.example.yaml

and create a local:

    configs/datasets/local_paths.yaml

The local_paths.yaml file is intentionally excluded from Git.

External comparison implementations are preserved as pinned Git submodules.
Clone this repository with submodules or initialize them after cloning.
