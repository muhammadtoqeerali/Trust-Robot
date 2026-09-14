import hashlib
import json
import statistics

from pathlib import Path

from torch.utils.data import DataLoader

from engine.corruption_registry import (
    load_corruption_registry
)

from engine.evaluator import (
    evaluate_model
)

from engine.reliability_dataset_v2 import (
    ReliabilityDatasetV2
)

from engine.reliability_score import (
    create_reliability_summary
)


DEFAULT_REGISTRY = (
    "configs/reliability/"
    "corruption_registry_v2.json"
)


def sha256_file(
    path
):

    path = Path(
        path
    )

    h = hashlib.sha256()

    with path.open(
        "rb"
    ) as f:

        while True:

            chunk = f.read(
                1024 * 1024
            )

            if not chunk:
                break

            h.update(
                chunk
            )

    return h.hexdigest()


def evaluate_v2_case(
    model,
    clean_loader,
    clean_metrics,
    device,
    output_dir,
    corruption,
    condition_id,
    condition_value,
    corruption_seed,
    channel_std,
    dataset_kwargs
):

    dataset = ReliabilityDatasetV2(

        clean_loader.dataset,

        corruption,

        corruption_seed=(
            0
            if corruption_seed is None
            else corruption_seed
        ),

        channel_std=channel_std,

        **dataset_kwargs
    )


    loader = DataLoader(

        dataset,

        batch_size=64,

        shuffle=False
    )


    metrics = evaluate_model(

        model,

        loader,

        device,

        output_dir
    )


    legacy_summary = (
        create_reliability_summary(

            clean_metrics,

            metrics,

            corruption,

            condition_value
        )
    )


    result = dict(
        legacy_summary
    )


    result.update(
        {

            "protocol_version":
                "v2",

            "family":
                corruption,

            "condition_id":
                condition_id,

            "condition_value":
                condition_value,

            "corruption_seed":
                corruption_seed,

            "clean_metrics": {

                "accuracy":
                    clean_metrics[
                        "accuracy"
                    ],

                "macro_f1":
                    clean_metrics[
                        "macro_f1"
                    ]
            },

            "corrupted_metrics": {

                "accuracy":
                    metrics[
                        "accuracy"
                    ],

                "macro_f1":
                    metrics[
                        "macro_f1"
                    ]
            }
        }
    )


    return result


def summarize_family(
    cases
):

    if not cases:

        raise ValueError(
            "Cannot summarize empty family"
        )


    return {

        "n_cases":
            len(
                cases
            ),

        "reliability_score_mean":
            statistics.mean(
                x[
                    "reliability_score"
                ]
                for x in cases
            ),

        "corrupted_accuracy_mean":
            statistics.mean(
                x[
                    "corrupted_metrics"
                ][
                    "accuracy"
                ]
                for x in cases
            ),

        "corrupted_macro_f1_mean":
            statistics.mean(
                x[
                    "corrupted_metrics"
                ][
                    "macro_f1"
                ]
                for x in cases
            ),

        "relative_accuracy_degradation_mean":
            statistics.mean(
                x[
                    "degradation"
                ][
                    "accuracy_degradation"
                ]
                for x in cases
            ),

        "relative_macro_f1_degradation_mean":
            statistics.mean(
                x[
                    "degradation"
                ][
                    "macro_f1_degradation"
                ]
                for x in cases
            )
    }


def run_reliability_evaluation_v2(
    model,
    clean_loader,
    device,
    output_dir,
    registry_path=DEFAULT_REGISTRY
):

    output_dir = Path(
        output_dir
    )


    if output_dir.exists():

        raise FileExistsError(
            f"V2 output already exists: "
            f"{output_dir}"
        )


    output_dir.mkdir(
        parents=True,
        exist_ok=False
    )


    registry_path = Path(
        registry_path
    )


    registry = load_corruption_registry(
        registry_path
    )


    if registry.get(
        "version"
    ) != "v2":

        raise RuntimeError(
            "Reliability V2 runner requires "
            "registry version v2"
        )


    clean_metrics = evaluate_model(

        model,

        clean_loader,

        device,

        output_dir /
        "clean"
    )


    channel_std = (

        clean_loader
        .dataset
        .tensors[
            0
        ]
        .float()
        .std(
            dim=(
                0,
                1
            ),
            unbiased=False
        )
        .detach()
        .cpu()
        .numpy()

    )


    channels = registry[
        "channels"
    ]


    corruption_seeds = registry[
        "corruption_seeds"
    ]


    cases = []


    missing_cfg = registry[
        "corruptions"
    ][
        "missing_channel"
    ]


    for channel in missing_cfg[
        "channel_indices"
    ]:

        label = channels[
            channel
        ]

        condition_id = (
            f"channel_{channel}_{label}"
        )


        case = evaluate_v2_case(

            model=model,

            clean_loader=clean_loader,

            clean_metrics=clean_metrics,

            device=device,

            output_dir=(
                output_dir /
                "missing_channel" /
                condition_id
            ),

            corruption=
                "missing_channel",

            condition_id=
                condition_id,

            condition_value=
                condition_id,

            corruption_seed=None,

            channel_std=
                channel_std,

            dataset_kwargs={
                "channel":
                    int(
                        channel
                    )
            }
        )


        cases.append(
            case
        )


    dropout_cfg = registry[
        "corruptions"
    ][
        "random_dropout"
    ]


    for ratio in dropout_cfg[
        "drop_ratio"
    ]:

        for corruption_seed in corruption_seeds:

            condition_id = (
                f"drop_{ratio}_"
                f"seed_{corruption_seed}"
            )


            case = evaluate_v2_case(

                model=model,

                clean_loader=clean_loader,

                clean_metrics=clean_metrics,

                device=device,

                output_dir=(
                    output_dir /
                    "random_dropout" /
                    f"drop_{ratio}" /
                    f"seed_{corruption_seed}"
                ),

                corruption=
                    "random_dropout",

                condition_id=
                    condition_id,

                condition_value=
                    float(
                        ratio
                    ),

                corruption_seed=
                    int(
                        corruption_seed
                    ),

                channel_std=
                    channel_std,

                dataset_kwargs={
                    "drop_ratio":
                        float(
                            ratio
                        )
                }
            )


            cases.append(
                case
            )


    gaussian_cfg = registry[
        "corruptions"
    ][
        "gaussian_noise"
    ]


    for snr_db in gaussian_cfg[
        "snr_db"
    ]:

        for corruption_seed in corruption_seeds:

            condition_id = (
                f"snr_{snr_db}db_"
                f"seed_{corruption_seed}"
            )


            case = evaluate_v2_case(

                model=model,

                clean_loader=clean_loader,

                clean_metrics=clean_metrics,

                device=device,

                output_dir=(
                    output_dir /
                    "gaussian_noise" /
                    f"snr_{snr_db}db" /
                    f"seed_{corruption_seed}"
                ),

                corruption=
                    "gaussian_noise",

                condition_id=
                    condition_id,

                condition_value=
                    float(
                        snr_db
                    ),

                corruption_seed=
                    int(
                        corruption_seed
                    ),

                channel_std=
                    channel_std,

                dataset_kwargs={
                    "snr_db":
                        float(
                            snr_db
                        )
                }
            )


            cases.append(
                case
            )


    drift_cfg = registry[
        "corruptions"
    ][
        "sensor_drift"
    ]


    for bias_scale in drift_cfg[
        "bias_scale"
    ]:

        for corruption_seed in corruption_seeds:

            condition_id = (
                f"bias_{bias_scale}_"
                f"seed_{corruption_seed}"
            )


            case = evaluate_v2_case(

                model=model,

                clean_loader=clean_loader,

                clean_metrics=clean_metrics,

                device=device,

                output_dir=(
                    output_dir /
                    "sensor_drift" /
                    f"bias_{bias_scale}" /
                    f"seed_{corruption_seed}"
                ),

                corruption=
                    "sensor_drift",

                condition_id=
                    condition_id,

                condition_value=
                    float(
                        bias_scale
                    ),

                corruption_seed=
                    int(
                        corruption_seed
                    ),

                channel_std=
                    channel_std,

                dataset_kwargs={
                    "bias_scale":
                        float(
                            bias_scale
                        )
                }
            )


            cases.append(
                case
            )


    expected_case_count = (
        len(
            missing_cfg[
                "channel_indices"
            ]
        )
        +
        len(
            dropout_cfg[
                "drop_ratio"
            ]
        )
        *
        len(
            corruption_seeds
        )
        +
        len(
            gaussian_cfg[
                "snr_db"
            ]
        )
        *
        len(
            corruption_seeds
        )
        +
        len(
            drift_cfg[
                "bias_scale"
            ]
        )
        *
        len(
            corruption_seeds
        )
    )


    if len(
        cases
    ) != expected_case_count:

        raise RuntimeError(
            "V2 case-count mismatch: "
            f"{len(cases)} vs "
            f"{expected_case_count}"
        )


    family_names = [

        "missing_channel",
        "random_dropout",
        "gaussian_noise",
        "sensor_drift"

    ]


    family_summaries = {}


    for family in family_names:

        family_cases = [

            case

            for case in cases

            if case[
                "family"
            ]
            ==
            family

        ]


        family_summaries[
            family
        ] = summarize_family(
            family_cases
        )


    overall = {

        "reliability_score":
            statistics.mean(
                family_summaries[
                    family
                ][
                    "reliability_score_mean"
                ]
                for family in family_names
            ),

        "corrupted_accuracy":
            statistics.mean(
                family_summaries[
                    family
                ][
                    "corrupted_accuracy_mean"
                ]
                for family in family_names
            ),

        "corrupted_macro_f1":
            statistics.mean(
                family_summaries[
                    family
                ][
                    "corrupted_macro_f1_mean"
                ]
                for family in family_names
            ),

        "relative_accuracy_degradation":
            statistics.mean(
                family_summaries[
                    family
                ][
                    "relative_accuracy_degradation_mean"
                ]
                for family in family_names
            ),

        "relative_macro_f1_degradation":
            statistics.mean(
                family_summaries[
                    family
                ][
                    "relative_macro_f1_degradation_mean"
                ]
                for family in family_names
            )
    }


    summary = {

        "protocol_version":
            "v2",

        "registry_path":
            str(
                registry_path
            ),

        "registry_sha256":
            sha256_file(
                registry_path
            ),

        "aggregation":
            registry[
                "aggregation"
            ],

        "clean_metrics": {

            "accuracy":
                clean_metrics[
                    "accuracy"
                ],

            "macro_f1":
                clean_metrics[
                    "macro_f1"
                ]
        },

        "n_corrupted_cases":
            len(
                cases
            ),

        "family_summaries":
            family_summaries,

        "overall":
            overall
    }


    (
        output_dir /
        "reliability_cases_v2.json"
    ).write_text(

        json.dumps(
            cases,
            indent=2
        )

    )


    (
        output_dir /
        "reliability_summary_v2.json"
    ).write_text(

        json.dumps(
            summary,
            indent=2
        )

    )


    (
        output_dir /
        "protocol_registry_snapshot.json"
    ).write_text(

        json.dumps(
            registry,
            indent=2
        )

    )


    return {

        "cases":
            cases,

        "summary":
            summary
    }
