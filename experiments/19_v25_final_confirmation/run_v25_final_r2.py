import argparse
import hashlib
import json
import random
import shutil
import sys
import time

from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn

from sklearn.metrics import (
    accuracy_score,
    f1_score
)


HERE = Path(
    __file__
).resolve().parent

REPO = HERE.parents[1]

SUITE = (
    REPO /
    "experiments" /
    "16_benchmark_suite"
)

SCREEN_CODE = (
    REPO /
    "experiments" /
    "17_v25_screening"
)

ABLATION_CODE = (
    REPO /
    "experiments" /
    "18_v25_training_ablation"
)


sys.path.insert(
    0,
    str(SUITE)
)

sys.path.insert(
    0,
    str(SCREEN_CODE)
)

sys.path.insert(
    0,
    str(ABLATION_CODE)
)


from v25_candidates import (
    create_candidate
)

import run_v25_ablation_r1 as ablation_protocol

from engine.dataset_v3r1 import (
    load_dataset_v3r1
)

from engine.reliability_runner_v2 import (
    run_reliability_evaluation_v2
)


deterministic_corruption = (
    ablation_protocol.deterministic_corruption
)


RESULT_ROOT = (
    REPO /
    "results" /
    "v25_final_r2"
)

RAW_ROOT = (
    RESULT_ROOT /
    "raw_runs"
)

REL_ROOT = (
    RESULT_ROOT /
    "reliability_v2"
)

PROTOCOL_ROOT = (
    RESULT_ROOT /
    "protocol"
)

ARCHIVE_ROOT = (
    RESULT_ROOT /
    "_partial_archive"
)


ABLATION_ROOT = (
    REPO /
    "results" /
    "v25_ablation_r1"
)

ABLATION_MANIFEST = (
    ABLATION_ROOT /
    "protocol" /
    "protocol_manifest.json"
)

ABLATION_RECEIPT = (
    ABLATION_ROOT /
    "final_analysis" /
    "v25_ablation_r1_final_receipt.json"
)

TRAINING_DECISION = (
    ABLATION_ROOT /
    "final_analysis" /
    "final_training_mode_decision.csv"
)


SCREENING_ROOT = (
    REPO /
    "results" /
    "v25_screening_r1"
)

SCREENING_RECEIPT = (
    SCREENING_ROOT /
    "final_analysis" /
    "v25_screening_r1_analysis_receipt.json"
)


V3_RECEIPT = (
    REPO /
    "results" /
    "benchmark_v3r1" /
    "final_analysis" /
    "benchmark_v3r1_final_integrity_receipt_r2.json"
)


REGISTRY = (
    REPO /
    "configs" /
    "reliability" /
    "corruption_registry_v2.json"
)


MODEL_NAME = (
    "ReliabilityCNN_v25"
)

ARCHITECTURE_NAME = (
    "V25Dense64"
)

TRAINING_MODE = (
    "corruption_exposure"
)


DATASETS = [
    "UCI_HAR",
    "PAMAP2",
    "DSADS",
    "MotionSense",
]


EXPECTED = {

    "UCI_HAR": {
        "classes": 6,
        "train": 5817,
        "val": 2196,
        "test": 2286,
    },

    "PAMAP2": {
        "classes": 12,
        "train": 18609,
        "val": 7542,
        "test": 4192,
    },

    "DSADS": {
        "classes": 19,
        "train": 4560,
        "val": 2280,
        "test": 2280,
    },

    "MotionSense": {
        "classes": 6,
        "train": 12370,
        "val": 4809,
        "test": 4349,
    },
}


SEEDS = [
    42,
    123,
    456,
    789,
    2026,
]


DEVELOPMENT_SEEDS = [
    42,
    123,
    456,
]


HELDOUT_SEEDS = [
    789,
    2026,
]


DEVELOPMENT_DATASETS = [
    "UCI_HAR",
    "DSADS",
]


HELDOUT_DATASETS = [
    "PAMAP2",
    "MotionSense",
]


EPOCHS = 100

BATCH_SIZE = 64

LEARNING_RATE = 0.001

CORRUPTION_PROBABILITY = 0.3


def sha256_file(path):

    h = hashlib.sha256()

    with Path(path).open(
        "rb"
    ) as f:

        while True:

            block = f.read(
                1024 * 1024
            )

            if not block:
                break

            h.update(block)

    return h.hexdigest()


def load_json(path):

    return json.loads(
        Path(path).read_text()
    )


def save_json(
    path,
    data
):

    path = Path(path)

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    path.write_text(
        json.dumps(
            data,
            indent=2,
            sort_keys=True
        )
    )


def set_seed(seed):

    random.seed(seed)

    np.random.seed(seed)

    torch.manual_seed(seed)

    torch.cuda.manual_seed_all(seed)

    torch.backends.cudnn.deterministic = True

    torch.backends.cudnn.benchmark = False


def evidence_slice(
    dataset,
    seed
):

    if dataset in HELDOUT_DATASETS:

        return (
            "selection_heldout_confirmation"
        )


    if (
        dataset in DEVELOPMENT_DATASETS
        and
        seed in HELDOUT_SEEDS
    ):

        return (
            "selection_heldout_confirmation"
        )


    return (
        "development_reproduction"
    )


def archive_partial(
    path,
    kind
):

    path = Path(path)

    if not path.exists():
        return


    stamp = time.strftime(
        "%Y%m%d_%H%M%S"
    )


    destination = (
        ARCHIVE_ROOT /
        kind /
        stamp /
        path.relative_to(
            RESULT_ROOT
        )
    )


    destination.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    shutil.move(
        str(path),
        str(destination)
    )


    print(
        "PARTIAL_ARCHIVED:",
        destination,
        flush=True
    )


def get_data(dataset):

    data = load_dataset_v3r1(
        dataset,
        batch_size=BATCH_SIZE,
        reliability_training=False
    )


    observed = {

        "classes":
            int(
                data[
                    "num_classes"
                ]
            ),

        "train":
            len(
                data[
                    "train_loader"
                ].dataset
            ),

        "val":
            len(
                data[
                    "val_loader"
                ].dataset
            ),

        "test":
            len(
                data[
                    "test_loader"
                ].dataset
            ),
    }


    if observed != EXPECTED[
        dataset
    ]:

        raise RuntimeError(
            f"Dataset mismatch: "
            f"{dataset}: "
            f"{observed} != "
            f"{EXPECTED[dataset]}"
        )


    return data, observed


def evaluate(
    model,
    loader,
    device
):

    model.eval()

    truth = []

    prediction = []


    with torch.inference_mode():

        for x, y in loader:

            x = x.to(
                device
            )

            y = y.to(
                device
            )


            logits = model(
                x
            )


            pred = logits.argmax(
                dim=1
            )


            truth.extend(
                y.cpu().tolist()
            )

            prediction.extend(
                pred.cpu().tolist()
            )


    return {

        "accuracy":
            float(
                accuracy_score(
                    truth,
                    prediction
                )
            ),

        "macro_f1":
            float(
                f1_score(
                    truth,
                    prediction,
                    average="macro",
                    zero_division=0
                )
            ),
    }


def train_one(
    dataset,
    seed,
    device,
    protocol_sha
):

    out = (
        RAW_ROOT /
        dataset /
        MODEL_NAME /
        f"seed_{seed}"
    )


    required = [

        out /
        "COMPLETE",

        out /
        "best_model.pt",

        out /
        "checkpoint.pt",

        out /
        "metrics.json",

        out /
        "history.json",

        out /
        "dataset_summary.json",

        out /
        "receipt.json",
    ]


    if all(
        path.exists()
        for path in required
    ):

        print(
            "TRAIN_SKIP_COMPLETE:",
            dataset,
            seed,
            flush=True
        )

        return


    if out.exists():

        archive_partial(
            out,
            "training"
        )


    out.mkdir(
        parents=True,
        exist_ok=False
    )


    set_seed(seed)


    data, observed = get_data(
        dataset
    )


    model = create_candidate(

        ARCHITECTURE_NAME,

        data[
            "num_classes"
        ],

        input_channels=6

    ).to(
        device
    )


    parameters = int(
        sum(
            parameter.numel()
            for parameter
            in model.parameters()
        )
    )


    if parameters > 50000:

        raise RuntimeError(
            f"Final model parameter gate failed: "
            f"{dataset}: {parameters}"
        )


    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=LEARNING_RATE
    )


    criterion = nn.CrossEntropyLoss()


    best_f1 = -1.0

    best_epoch = None

    history = []

    schedule_hasher = (
        hashlib.sha256()
    )


    start_time = time.time()


    print()
    print(
        "=" * 80,
        flush=True
    )

    print(
        "FINAL_TRAIN_START:",
        dataset,
        MODEL_NAME,
        seed,
        "SLICE=",
        evidence_slice(
            dataset,
            seed
        ),
        flush=True
    )

    print(
        "=" * 80,
        flush=True
    )


    for epoch in range(
        1,
        EPOCHS + 1
    ):

        model.train()

        running_loss = 0.0

        examples = 0


        for batch_index, (
            clean,
            y
        ) in enumerate(
            data[
                "train_loader"
            ]
        ):

            clean = clean.to(
                device
            )

            y = y.to(
                device
            )


            corrupted = deterministic_corruption(

                clean,

                seed,

                epoch,

                batch_index,

                schedule_hasher
            )


            optimizer.zero_grad(
                set_to_none=True
            )


            clean_logits, _ = (
                model.forward_with_features(
                    clean
                )
            )


            classification_loss = (
                criterion(
                    clean_logits,
                    y
                )
            )


            # Final selected training method:
            #
            # clean supervised gradient +
            # corrupted forward exposure.
            #
            # The corrupted forward is run while
            # the model remains in train() mode,
            # so BatchNorm running statistics see
            # corrupted inputs.
            #
            # No feature-consistency gradient is
            # applied.

            with torch.no_grad():

                model.forward_with_features(
                    corrupted
                )


            loss = classification_loss


            loss.backward()

            optimizer.step()


            batch_size = y.shape[
                0
            ]


            running_loss += (
                float(
                    loss.item()
                )
                *
                batch_size
            )


            examples += batch_size


        validation = evaluate(
            model,
            data[
                "val_loader"
            ],
            device
        )


        epoch_loss = (
            running_loss
            /
            max(
                examples,
                1
            )
        )


        if (
            validation[
                "macro_f1"
            ]
            >
            best_f1
        ):

            best_f1 = (
                validation[
                    "macro_f1"
                ]
            )


            best_epoch = epoch


            torch.save(
                model.state_dict(),
                out /
                "best_model.pt"
            )


        history.append(
            {

                "epoch":
                    epoch,

                "classification_loss":
                    epoch_loss,

                "consistency_loss":
                    0.0,

                "validation_accuracy":
                    validation[
                        "accuracy"
                    ],

                "validation_macro_f1":
                    validation[
                        "macro_f1"
                    ],

                "best_validation_macro_f1":
                    best_f1,

                "best_epoch":
                    best_epoch,
            }
        )


        if (
            epoch == 1
            or
            epoch % 10 == 0
            or
            epoch == EPOCHS
        ):

            print(
                "EPOCH",
                epoch,
                "/",
                EPOCHS,
                "LOSS=",
                f"{epoch_loss:.6f}",
                "CONS=0.000000",
                "VAL_F1=",
                f"{validation['macro_f1']:.6f}",
                "BEST_F1=",
                f"{best_f1:.6f}",
                "BEST_EPOCH=",
                best_epoch,
                flush=True
            )


    training_seconds = (
        time.time()
        -
        start_time
    )


    try:

        state = torch.load(
            out /
            "best_model.pt",
            map_location="cpu",
            weights_only=True
        )

    except TypeError:

        state = torch.load(
            out /
            "best_model.pt",
            map_location="cpu"
        )


    shutil.copyfile(
        out /
        "best_model.pt",
        out /
        "checkpoint.pt"
    )


    model.load_state_dict(
        state,
        strict=True
    )


    model.to(
        device
    )


    test = evaluate(
        model,
        data[
            "test_loader"
        ],
        device
    )


    schedule_sha = (
        schedule_hasher.hexdigest()
    )


    metrics = {

        "benchmark":
            "v25_final_r2",

        "model":
            MODEL_NAME,

        "architecture":
            ARCHITECTURE_NAME,

        "dataset":
            dataset,

        "seed":
            seed,

        "evidence_slice":
            evidence_slice(
                dataset,
                seed
            ),

        "training_mode":
            TRAINING_MODE,

        "epochs":
            EPOCHS,

        "batch_size":
            BATCH_SIZE,

        "optimizer":
            "Adam",

        "learning_rate":
            LEARNING_RATE,

        "corruption_probability":
            CORRUPTION_PROBABILITY,

        "training_corruption":
            "per_sample_whole_channel_zeroing",

        "corrupted_forward_exposure":
            True,

        "feature_output_available":
            True,

        "consistency_loss_active":
            False,

        "consistency_weight":
            0.0,

        "corruption_schedule_sha256":
            schedule_sha,

        "best_epoch":
            best_epoch,

        "best_validation_macro_f1":
            best_f1,

        "training_seconds":
            training_seconds,

        "parameters":
            parameters,

        "test":
            test,
    }


    save_json(
        out /
        "metrics.json",
        metrics
    )


    save_json(
        out /
        "history.json",
        history
    )


    save_json(
        out /
        "dataset_summary.json",
        observed
    )


    best_sha = sha256_file(
        out /
        "best_model.pt"
    )


    checkpoint_sha = sha256_file(
        out /
        "checkpoint.pt"
    )


    if best_sha != checkpoint_sha:

        raise RuntimeError(
            "best_model.pt and checkpoint.pt "
            "do not match"
        )


    save_json(
        out /
        "receipt.json",
        {

            "protocol_manifest_sha256":
                protocol_sha,

            "best_model_sha256":
                best_sha,

            "checkpoint_sha256":
                checkpoint_sha,

            "candidate_architecture_sha256":
                sha256_file(
                    SCREEN_CODE /
                    "v25_candidates.py"
                ),

            "selected_training_protocol_source_sha256":
                sha256_file(
                    ABLATION_CODE /
                    "run_v25_ablation_r1.py"
                ),

            "corruption_schedule_sha256":
                schedule_sha,

            "evidence_slice":
                evidence_slice(
                    dataset,
                    seed
                ),
        }
    )


    (
        out /
        "COMPLETE"
    ).write_text(
        "COMPLETE\n"
    )


    print(
        "FINAL_TRAIN_COMPLETE:",
        dataset,
        seed,
        "TEST_ACC=",
        f"{test['accuracy']:.6f}",
        "TEST_F1=",
        f"{test['macro_f1']:.6f}",
        "PARAMS=",
        parameters,
        "SLICE=",
        evidence_slice(
            dataset,
            seed
        ),
        flush=True
    )


def reliability_one(
    dataset,
    seed,
    device,
    protocol_sha
):

    out = (
        REL_ROOT /
        dataset /
        MODEL_NAME /
        f"seed_{seed}"
    )


    summary = (
        out /
        "reliability_summary_v2.json"
    )


    complete = (
        out /
        "COMPLETE"
    )


    if (
        summary.exists()
        and
        complete.exists()
        and
        (
            out /
            "final_receipt.json"
        ).exists()
    ):

        print(
            "RELIABILITY_SKIP_COMPLETE:",
            dataset,
            seed,
            flush=True
        )

        return


    if out.exists():

        archive_partial(
            out,
            "reliability"
        )


    set_seed(seed)


    data, _ = get_data(
        dataset
    )


    model = create_candidate(

        ARCHITECTURE_NAME,

        data[
            "num_classes"
        ],

        input_channels=6
    )


    checkpoint = (
        RAW_ROOT /
        dataset /
        MODEL_NAME /
        f"seed_{seed}" /
        "checkpoint.pt"
    )


    try:

        state = torch.load(
            checkpoint,
            map_location="cpu",
            weights_only=True
        )

    except TypeError:

        state = torch.load(
            checkpoint,
            map_location="cpu"
        )


    model.load_state_dict(
        state,
        strict=True
    )


    model = model.to(
        device
    )


    print(
        "FINAL_RELIABILITY_START:",
        dataset,
        seed,
        "SLICE=",
        evidence_slice(
            dataset,
            seed
        ),
        flush=True
    )


    run_reliability_evaluation_v2(

        model,

        data[
            "test_loader"
        ],

        device,

        out,

        registry_path=str(
            REGISTRY
        )
    )


    if not summary.exists():

        raise RuntimeError(
            f"Missing reliability summary: "
            f"{summary}"
        )


    summary_data = load_json(
        summary
    )


    if summary_data.get(
        "protocol_version"
    ) != "v2":

        raise RuntimeError(
            "Final reliability protocol "
            "is not V2"
        )


    if summary_data.get(
        "n_corrupted_cases"
    ) != 33:

        raise RuntimeError(
            "Final reliability case count "
            "is not 33"
        )


    save_json(
        out /
        "final_receipt.json",
        {

            "protocol_manifest_sha256":
                protocol_sha,

            "checkpoint_sha256":
                sha256_file(
                    checkpoint
                ),

            "registry_sha256":
                sha256_file(
                    REGISTRY
                ),

            "reliability_summary_sha256":
                sha256_file(
                    summary
                ),

            "evidence_slice":
                evidence_slice(
                    dataset,
                    seed
                ),
        }
    )


    complete.write_text(
        "COMPLETE\n"
    )


    print(
        "FINAL_RELIABILITY_COMPLETE:",
        dataset,
        seed,
        flush=True
    )


def verify_prior_freeze():

    manifest = load_json(
        ABLATION_MANIFEST
    )


    expected_hashes = manifest[
        "hashes"
    ]


    verified = 0


    for relative, expected_sha in (
        expected_hashes.items()
    ):

        path = (
            REPO /
            relative
        )


        if not path.exists():

            raise FileNotFoundError(
                path
            )


        actual = sha256_file(
            path
        )


        if actual != expected_sha:

            raise RuntimeError(
                "Ablation frozen input changed: "
                f"{relative}"
            )


        verified += 1


    print(
        "ABLATION_FROZEN_HASHES_VERIFIED=",
        verified
    )


def create_selection_decision():

    decision = pd.read_csv(
        TRAINING_DECISION
    )


    required_modes = {
        "clean_ce",
        "exposure",
        "consistency",
    }


    if set(
        decision[
            "mode"
        ].tolist()
    ) != required_modes:

        raise RuntimeError(
            "Unexpected training-mode decision table"
        )


    rows = {
        row[
            "mode"
        ]:
            row
        for _, row
        in decision.iterrows()
    }


    clean = rows[
        "clean_ce"
    ]

    exposure = rows[
        "exposure"
    ]

    consistency = rows[
        "consistency"
    ]


    primary = [

        "clean_macro_f1",

        "corrupted_accuracy",

        "corrupted_macro_f1",
    ]


    for metric in primary:

        if not (
            float(
                exposure[
                    metric
                ]
            )
            >=
            float(
                clean[
                    metric
                ]
            )
        ):

            raise RuntimeError(
                "Exposure no longer dominates "
                f"clean CE on {metric}"
            )


    if not (
        float(
            exposure[
                "clean_macro_f1"
            ]
        )
        >
        float(
            consistency[
                "clean_macro_f1"
            ]
        )
    ):

        raise RuntimeError(
            "Exposure selection condition "
            "failed on clean macro-F1"
        )


    if not (
        float(
            exposure[
                "corrupted_accuracy"
            ]
        )
        >
        float(
            consistency[
                "corrupted_accuracy"
            ]
        )
    ):

        raise RuntimeError(
            "Exposure selection condition "
            "failed on corrupted accuracy"
        )


    selection = {

        "model":
            MODEL_NAME,

        "architecture":
            ARCHITECTURE_NAME,

        "selected_training_mode":
            TRAINING_MODE,

        "selection_source":
            str(
                TRAINING_DECISION.relative_to(
                    REPO
                )
            ),

        "selection_source_sha256":
            sha256_file(
                TRAINING_DECISION
            ),

        "ablation_receipt_sha256":
            sha256_file(
                ABLATION_RECEIPT
            ),

        "selection_rule":
            (
                "Prefer the simplest mode that is "
                "not worse than clean CE on clean "
                "macro-F1, corrupted accuracy, and "
                "corrupted macro-F1, while avoiding "
                "the dataset-dependent degradation "
                "observed for true consistency."
            ),

        "selected_values": {

            "clean_macro_f1":
                float(
                    exposure[
                        "clean_macro_f1"
                    ]
                ),

            "corrupted_accuracy":
                float(
                    exposure[
                        "corrupted_accuracy"
                    ]
                ),

            "corrupted_macro_f1":
                float(
                    exposure[
                        "corrupted_macro_f1"
                    ]
                ),

            "reliability_score":
                float(
                    exposure[
                        "reliability_score"
                    ]
                ),
        },

        "development_boundary":
            (
                "Architecture and training mode were "
                "selected using UCI_HAR and DSADS "
                "with seeds 42,123,456."
            ),

        "confirmation_boundary":
            (
                "PAMAP2 and MotionSense all five "
                "seeds plus UCI_HAR/DSADS seeds "
                "789 and 2026 form the "
                "selection-held-out confirmation "
                "slice."
            ),
    }


    path = (
        PROTOCOL_ROOT /
        "selection_decision.json"
    )


    if path.exists():

        existing = load_json(
            path
        )


        if existing != selection:

            raise RuntimeError(
                "Existing selection decision differs"
            )


        print(
            "SELECTION_DECISION_REUSED=True"
        )

    else:

        save_json(
            path,
            selection
        )


        print(
            "SELECTION_DECISION_CREATED=True"
        )


    print(
        "SELECTED_MODEL=",
        MODEL_NAME
    )

    print(
        "SELECTED_ARCHITECTURE=",
        ARCHITECTURE_NAME
    )

    print(
        "SELECTED_TRAINING_MODE=",
        TRAINING_MODE
    )


    return path


def build_hash_inventory(
    selection_path
):

    critical = [

        HERE /
        "run_v25_final_r2.py",

        SCREEN_CODE /
        "v25_candidates.py",

        ABLATION_CODE /
        "run_v25_ablation_r1.py",

        SUITE /
        "engine" /
        "dataset_v3r1.py",

        SUITE /
        "engine" /
        "reliability_runner_v2.py",

        SUITE /
        "engine" /
        "reliability_dataset_v2.py",

        SUITE /
        "engine" /
        "corruption_engine_v2.py",

        SUITE /
        "engine" /
        "reliability_score.py",

        REGISTRY,

        ABLATION_MANIFEST,

        ABLATION_RECEIPT,

        TRAINING_DECISION,

        SCREENING_RECEIPT,

        V3_RECEIPT,

        selection_path,
    ]


    for dataset in DATASETS:

        critical.extend(
            [

                REPO /
                "data" /
                "processed" /
                "harmonized" /
                dataset /
                "X.npy",

                REPO /
                "data" /
                "processed" /
                "harmonized" /
                dataset /
                "y.npy",

                REPO /
                "data" /
                "processed" /
                "splits" /
                dataset /
                "train_idx.npy",

                REPO /
                "data" /
                "processed" /
                "splits" /
                dataset /
                "val_idx.npy",

                REPO /
                "data" /
                "processed" /
                "splits" /
                dataset /
                "test_idx.npy",

                REPO /
                "data" /
                "processed" /
                "splits" /
                dataset /
                "split_manifest.json",
            ]
        )


    hashes = {}


    for path in critical:

        if not path.exists():

            raise FileNotFoundError(
                path
            )


        hashes[
            str(
                path.relative_to(
                    REPO
                )
            )
        ] = sha256_file(
            path
        )


    return hashes


def preflight():

    print(
        "=" * 84
    )

    print(
        "RELIABILITYCNN V25 FINAL R1 PREFLIGHT"
    )

    print(
        "=" * 84
    )


    if not torch.cuda.is_available():

        raise RuntimeError(
            "CUDA unavailable"
        )


    print(
        "GPU=",
        torch.cuda.get_device_name(
            0
        )
    )


    if abs(
        float(
            ablation_protocol.CORRUPTION_PROBABILITY
        )
        -
        CORRUPTION_PROBABILITY
    ) > 1e-12:

        raise RuntimeError(
            "Corruption probability does not "
            "match selected ablation protocol"
        )


    verify_prior_freeze()


    ablation_receipt = load_json(
        ABLATION_RECEIPT
    )


    if not ablation_receipt.get(
        "integrity_pass",
        False
    ):

        raise RuntimeError(
            "Ablation receipt is not PASS"
        )


    v3_receipt = load_json(
        V3_RECEIPT
    )


    if not v3_receipt.get(
        "integrity_pass",
        False
    ):

        raise RuntimeError(
            "V3R1 reference bank integrity "
            "is not PASS"
        )


    PROTOCOL_ROOT.mkdir(
        parents=True,
        exist_ok=True
    )


    selection_path = (
        create_selection_decision()
    )


    confirmation_count = 0

    reproduction_count = 0


    for dataset in DATASETS:

        data, observed = get_data(
            dataset
        )


        print(
            "DATASET_PASS:",
            dataset,
            observed
        )


        model = create_candidate(

            ARCHITECTURE_NAME,

            data[
                "num_classes"
            ],

            input_channels=6
        )


        params = int(
            sum(
                parameter.numel()
                for parameter
                in model.parameters()
            )
        )


        x = torch.zeros(
            2,
            128,
            6
        )


        model.eval()


        with torch.no_grad():

            logits, features = (
                model.forward_with_features(
                    x
                )
            )


        if tuple(
            logits.shape
        ) != (
            2,
            data[
                "num_classes"
            ]
        ):

            raise RuntimeError(
                f"Bad logits shape: "
                f"{dataset}"
            )


        if tuple(
            features.shape
        ) != (
            2,
            64
        ):

            raise RuntimeError(
                f"Bad feature shape: "
                f"{dataset}: "
                f"{tuple(features.shape)}"
            )


        if params > 50000:

            raise RuntimeError(
                f"Parameter gate failed: "
                f"{dataset}: {params}"
            )


        print(
            "FINAL_MODEL_PASS:",
            dataset,
            "PARAMS=",
            params,
            "FEATURES=",
            tuple(
                features.shape
            )
        )


        for seed in SEEDS:

            slice_name = evidence_slice(
                dataset,
                seed
            )


            if (
                slice_name
                ==
                "selection_heldout_confirmation"
            ):

                confirmation_count += 1

            else:

                reproduction_count += 1


    if confirmation_count != 14:

        raise RuntimeError(
            "Expected 14 selection-held-out "
            f"confirmation points, got "
            f"{confirmation_count}"
        )


    if reproduction_count != 6:

        raise RuntimeError(
            "Expected 6 development-reproduction "
            f"points, got {reproduction_count}"
        )


    # Verify corruption generator identity
    # with the selected ablation implementation.

    dummy = torch.randn(
        16,
        128,
        6
    )


    h1 = hashlib.sha256()

    h2 = hashlib.sha256()


    c1 = deterministic_corruption(
        dummy,
        789,
        3,
        4,
        h1
    )


    c2 = (
        ablation_protocol
        .deterministic_corruption(
            dummy,
            789,
            3,
            4,
            h2
        )
    )


    if not torch.equal(
        c1,
        c2
    ):

        raise RuntimeError(
            "Selected corruption implementation "
            "identity test failed"
        )


    if h1.hexdigest() != h2.hexdigest():

        raise RuntimeError(
            "Selected corruption schedule hash "
            "identity test failed"
        )


    print(
        "SELECTED_CORRUPTION_PROTOCOL_IDENTITY_PASS=True"
    )


    hashes = build_hash_inventory(
        selection_path
    )


    manifest = {

        "protocol":
            "v25_final_r2",

        "parent_protocol":
            "v25_final_r1",

        "revision_type":
            "harness_only_recovery",

        "revision_reason":
            (
                "checkpoint.pt is an exact byte copy "
                "of best_model.pt rather than a fresh "
                "torch.save serialization. Model, data, "
                "training, selection, corruption, and "
                "reliability protocols are unchanged."
            ),

        "model":
            MODEL_NAME,

        "architecture":
            ARCHITECTURE_NAME,

        "selected_training_mode":
            TRAINING_MODE,

        "training_mode_selection_source":
            str(
                TRAINING_DECISION.relative_to(
                    REPO
                )
            ),

        "datasets":
            DATASETS,

        "seeds":
            SEEDS,

        "epochs":
            EPOCHS,

        "batch_size":
            BATCH_SIZE,

        "optimizer":
            "Adam",

        "learning_rate":
            LEARNING_RATE,

        "corruption_probability":
            CORRUPTION_PROBABILITY,

        "training_corruption":
            "per_sample_whole_channel_zeroing",

        "corruption_schedule":
            (
                "dedicated deterministic RNG "
                "derived only from seed, epoch, "
                "and batch index"
            ),

        "corrupted_forward_exposure":
            True,

        "consistency_loss_active":
            False,

        "checkpoint_selection":
            "best_validation_macro_f1",

        "reliability_protocol":
            "v2",

        "expected_training_runs":
            20,

        "expected_reliability_runs":
            20,

        "expected_corruption_cases":
            660,

        "selection_heldout_confirmation_runs":
            14,

        "development_reproduction_runs":
            6,

        "selection_heldout_confirmation_definition": {

            "heldout_datasets":
                HELDOUT_DATASETS,

            "heldout_seeds_on_development_datasets":
                HELDOUT_SEEDS,
        },

        "development_reproduction_definition": {

            "datasets":
                DEVELOPMENT_DATASETS,

            "seeds":
                DEVELOPMENT_SEEDS,
        },

        "claim_boundary":
            (
                "Primary confirmation interpretation "
                "must distinguish the 14 points not "
                "used for model/training-mode selection "
                "from the six development-reproduction "
                "points."
            ),

        "hashes":
            hashes,
    }


    manifest_path = (
        PROTOCOL_ROOT /
        "protocol_manifest.json"
    )


    if manifest_path.exists():

        existing = load_json(
            manifest_path
        )


        if existing != manifest:

            raise RuntimeError(
                "Existing V25 final protocol differs. "
                "Refusing to mix revisions."
            )


        print(
            "PROTOCOL_MANIFEST_REUSED=True"
        )


    else:

        save_json(
            manifest_path,
            manifest
        )


        print(
            "PROTOCOL_MANIFEST_CREATED=True"
        )


    print(
        "PROTOCOL_SHA256=",
        sha256_file(
            manifest_path
        )
    )


    print(
        "FROZEN_HASHES=",
        len(hashes)
    )


    print(
        "V25_FINAL_R2_PREFLIGHT_PASS=True"
    )

    print(
        "FINAL_MODEL=",
        MODEL_NAME
    )

    print(
        "FINAL_ARCHITECTURE=",
        ARCHITECTURE_NAME
    )

    print(
        "FINAL_TRAINING_MODE=",
        TRAINING_MODE
    )

    print(
        "FINAL_DATASETS=4"
    )

    print(
        "FINAL_SEEDS=5"
    )

    print(
        "FINAL_TRAINING_RUNS=20"
    )

    print(
        "FINAL_RELIABILITY_RUNS=20"
    )

    print(
        "FINAL_CORRUPTION_CASES=660"
    )

    print(
        "SELECTION_HELDOUT_CONFIRMATION_RUNS=14"
    )

    print(
        "DEVELOPMENT_REPRODUCTION_RUNS=6"
    )


def run(datasets):

    manifest_path = (
        PROTOCOL_ROOT /
        "protocol_manifest.json"
    )


    if not manifest_path.exists():

        raise RuntimeError(
            "Final preflight has not been run"
        )


    protocol_sha = sha256_file(
        manifest_path
    )


    device = torch.device(
        "cuda"
    )


    print(
        "V25_FINAL_R2_WORKER_START=True",
        flush=True
    )

    print(
        "MODEL=",
        MODEL_NAME,
        flush=True
    )

    print(
        "ARCHITECTURE=",
        ARCHITECTURE_NAME,
        flush=True
    )

    print(
        "TRAINING_MODE=",
        TRAINING_MODE,
        flush=True
    )

    print(
        "DATASETS=",
        datasets,
        flush=True
    )

    print(
        "SEEDS=",
        SEEDS,
        flush=True
    )


    for dataset in datasets:

        for seed in SEEDS:

            train_one(
                dataset,
                seed,
                device,
                protocol_sha
            )


    for dataset in datasets:

        for seed in SEEDS:

            reliability_one(
                dataset,
                seed,
                device,
                protocol_sha
            )


    print(
        "V25_FINAL_R2_WORKER_COMPLETE=True",
        flush=True
    )


def main():

    parser = argparse.ArgumentParser()


    parser.add_argument(
        "--preflight",
        action="store_true"
    )


    parser.add_argument(
        "--datasets",
        nargs="+",
        choices=DATASETS,
        default=DATASETS
    )


    args = parser.parse_args()


    if args.preflight:

        preflight()

    else:

        run(
            args.datasets
        )


if __name__ == "__main__":

    main()
