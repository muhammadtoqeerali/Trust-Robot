import argparse
import hashlib
import json
import random
import shutil
import sys
import time

from pathlib import Path


import numpy as np

import torch
import torch.nn as nn

from sklearn.metrics import (
    accuracy_score,
    f1_score
)


HERE = Path(
    __file__
).resolve().parent

REPO = HERE.parents[
    1
]

SUITE = (
    REPO /
    "experiments" /
    "16_benchmark_suite"
)

sys.path.insert(
    0,
    str(HERE)
)

sys.path.insert(
    0,
    str(SUITE)
)


from v25_candidates import (
    create_candidate
)

from engine.dataset_v3r1 import (
    load_dataset_v3r1
)

from engine.reliability_runner_v2 import (
    run_reliability_evaluation_v2
)


RESULT_ROOT = (
    REPO /
    "results" /
    "v25_screening_r1"
)

RAW_ROOT = (
    RESULT_ROOT /
    "raw_runs"
)

REL_ROOT = (
    RESULT_ROOT /
    "reliability_v2"
)

ARCHIVE_ROOT = (
    RESULT_ROOT /
    "_partial_archive"
)

PROTOCOL_DIR = (
    RESULT_ROOT /
    "protocol"
)


REGISTRY = (
    REPO /
    "configs" /
    "reliability" /
    "corruption_registry_v2.json"
)


V3_PROTOCOL = (
    REPO /
    "results" /
    "benchmark_v3r1" /
    "protocol" /
    "protocol_manifest.json"
)


V3_RECEIPT = (
    REPO /
    "results" /
    "benchmark_v3r1" /
    "final_analysis" /
    "benchmark_v3r1_final_integrity_receipt_r2.json"
)


DATASETS = [
    "UCI_HAR",
    "DSADS",
]


EXPECTED = {

    "UCI_HAR": {
        "classes": 6,
        "train": 5817,
        "val": 2196,
        "test": 2286,
    },

    "DSADS": {
        "classes": 19,
        "train": 4560,
        "val": 2280,
        "test": 2280,
    },
}


CANDIDATES = [
    "V25Dense64",
    "V25DS96",
]


SEEDS = [
    42,
    123,
    456,
]


EPOCHS = 100

BATCH_SIZE = 64

LR = 0.001


def sha256_file(
    path
):

    h = hashlib.sha256()

    with Path(
        path
    ).open(
        "rb"
    ) as f:

        while True:

            block = f.read(
                1024 * 1024
            )

            if not block:
                break

            h.update(
                block
            )

    return h.hexdigest()


def load_json(
    path
):

    return json.loads(
        Path(
            path
        ).read_text()
    )


def save_json(
    path,
    data
):

    path = Path(
        path
    )

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


def set_seed(
    seed
):

    random.seed(
        seed
    )

    np.random.seed(
        seed
    )

    torch.manual_seed(
        seed
    )

    torch.cuda.manual_seed_all(
        seed
    )

    torch.backends.cudnn.deterministic = True

    torch.backends.cudnn.benchmark = False


def archive_partial(
    path,
    kind
):

    path = Path(
        path
    )

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


def get_data(
    dataset
):

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
            f"Dataset integrity failure: "
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

    pred = []


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


            prediction = logits.argmax(
                dim=1
            )


            truth.extend(
                y.cpu().tolist()
            )

            pred.extend(
                prediction.cpu().tolist()
            )


    return {

        "accuracy":
            float(
                accuracy_score(
                    truth,
                    pred
                )
            ),

        "macro_f1":
            float(
                f1_score(
                    truth,
                    pred,
                    average="macro",
                    zero_division=0
                )
            ),
    }


def train_one(
    dataset,
    candidate,
    seed,
    device,
    protocol_sha
):

    out = (
        RAW_ROOT /
        dataset /
        candidate /
        f"seed_{seed}"
    )


    required = [

        out /
        "COMPLETE",

        out /
        "best_model.pt",

        out /
        "metrics.json",

        out /
        "history.json",

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
            candidate,
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


    set_seed(
        seed
    )


    data, observed = get_data(
        dataset
    )


    model = create_candidate(
        candidate,
        data[
            "num_classes"
        ],
        input_channels=6
    ).to(
        device
    )


    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=LR
    )

    criterion = nn.CrossEntropyLoss()


    best_f1 = -1.0

    best_epoch = None

    history = []


    print()
    print(
        "=" * 72,
        flush=True
    )

    print(
        "TRAIN_START:",
        dataset,
        candidate,
        seed,
        flush=True
    )

    print(
        "=" * 72,
        flush=True
    )


    start_time = time.time()


    for epoch in range(
        1,
        EPOCHS + 1
    ):

        model.train()

        running_loss = 0.0

        examples = 0


        for x, y in data[
            "train_loader"
        ]:

            x = x.to(
                device
            )

            y = y.to(
                device
            )


            optimizer.zero_grad(
                set_to_none=True
            )


            logits = model(
                x
            )


            loss = criterion(
                logits,
                y
            )


            loss.backward()

            optimizer.step()


            running_loss += (
                float(
                    loss.item()
                )
                *
                y.shape[0]
            )

            examples += y.shape[
                0
            ]


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

                "train_loss":
                    epoch_loss,

                "val_accuracy":
                    validation[
                        "accuracy"
                    ],

                "val_macro_f1":
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


    parameters = int(
        sum(
            parameter.numel()
            for parameter
            in model.parameters()
        )
    )


    metrics = {

        "dataset":
            dataset,

        "candidate":
            candidate,

        "seed":
            seed,

        "training_mode":
            "clean_ce_architecture_screen",

        "epochs":
            EPOCHS,

        "batch_size":
            BATCH_SIZE,

        "learning_rate":
            LR,

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


    save_json(
        out /
        "receipt.json",
        {

            "protocol_manifest_sha256":
                protocol_sha,

            "candidate_source_sha256":
                sha256_file(
                    HERE /
                    "v25_candidates.py"
                ),

            "checkpoint_sha256":
                sha256_file(
                    out /
                    "best_model.pt"
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
        "TRAIN_COMPLETE:",
        dataset,
        candidate,
        seed,
        "TEST_ACC=",
        f"{test['accuracy']:.6f}",
        "TEST_F1=",
        f"{test['macro_f1']:.6f}",
        "PARAMS=",
        parameters,
        flush=True
    )


def reliability_one(
    dataset,
    candidate,
    seed,
    device,
    protocol_sha
):

    out = (
        REL_ROOT /
        dataset /
        candidate /
        f"seed_{seed}"
    )


    summary = (
        out /
        "reliability_summary_v2.json"
    )


    if (
        summary.exists()
        and
        (
            out /
            "COMPLETE"
        ).exists()
    ):

        print(
            "RELIABILITY_SKIP_COMPLETE:",
            dataset,
            candidate,
            seed,
            flush=True
        )

        return


    if out.exists():

        archive_partial(
            out,
            "reliability"
        )


    set_seed(
        seed
    )


    data, _ = get_data(
        dataset
    )


    model = create_candidate(
        candidate,
        data[
            "num_classes"
        ],
        input_channels=6
    )


    checkpoint = (
        RAW_ROOT /
        dataset /
        candidate /
        f"seed_{seed}" /
        "best_model.pt"
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
        "RELIABILITY_START:",
        dataset,
        candidate,
        seed,
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
            f"Missing reliability summary: {summary}"
        )


    save_json(
        out /
        "screening_receipt.json",
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

            "summary_sha256":
                sha256_file(
                    summary
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
        "RELIABILITY_COMPLETE:",
        dataset,
        candidate,
        seed,
        flush=True
    )


def preflight():

    print(
        "=" * 76
    )

    print(
        "V25 SCREENING R1 PREFLIGHT"
    )

    print(
        "=" * 76
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


    if not V3_RECEIPT.exists():

        raise FileNotFoundError(
            V3_RECEIPT
        )


    reference = load_json(
        V3_RECEIPT
    )


    if not reference.get(
        "integrity_pass",
        False
    ):

        raise RuntimeError(
            "V3R1 reference integrity is not PASS"
        )


    for dataset in DATASETS:

        data, observed = get_data(
            dataset
        )


        print(
            "DATASET_PASS:",
            dataset,
            observed
        )


        for candidate in CANDIDATES:

            model = create_candidate(
                candidate,
                data[
                    "num_classes"
                ]
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

                logits = model(
                    x
                )

                logits2, features = (
                    model.forward_with_features(
                        x
                    )
                )


            expected_shape = (
                2,
                data[
                    "num_classes"
                ]
            )


            if tuple(
                logits.shape
            ) != expected_shape:

                raise RuntimeError(
                    f"Bad logits: "
                    f"{dataset}/{candidate}/"
                    f"{tuple(logits.shape)}"
                )


            if not torch.allclose(
                logits,
                logits2,
                atol=0,
                rtol=0
            ):

                raise RuntimeError(
                    f"Forward output mismatch: "
                    f"{dataset}/{candidate}"
                )


            if features.ndim != 2:

                raise RuntimeError(
                    f"Bad feature shape: "
                    f"{dataset}/{candidate}"
                )


            if (
                candidate
                ==
                "V25Dense64"
                and
                params
                >
                50000
            ):

                raise RuntimeError(
                    f"V25Dense64 too large: {params}"
                )


            if (
                candidate
                ==
                "V25DS96"
                and
                params
                >
                40000
            ):

                raise RuntimeError(
                    f"V25DS96 too large: {params}"
                )


            print(
                "CANDIDATE_PASS:",
                dataset,
                candidate,
                "PARAMS=",
                params,
                "FEATURE_SHAPE=",
                tuple(
                    features.shape
                )
            )


    registry = load_json(
        REGISTRY
    )


    if registry.get(
        "version"
    ) != "v2":

        raise RuntimeError(
            "Corruption registry is not V2"
        )


    hashes = {}


    critical = [

        HERE /
        "v25_candidates.py",

        HERE /
        "run_v25_screening_r1.py",

        SUITE /
        "engine" /
        "dataset_v3r1.py",

        SUITE /
        "engine" /
        "reliability_runner_v2.py",

        REGISTRY,

        V3_PROTOCOL,

        V3_RECEIPT,
    ]


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


    manifest = {

        "protocol":
            "v25_screening_r1",

        "reference_benchmark":
            "benchmark_v3r1",

        "purpose":
            "development_architecture_compression_screen",

        "datasets":
            DATASETS,

        "candidates":
            CANDIDATES,

        "seeds":
            SEEDS,

        "epochs":
            EPOCHS,

        "batch_size":
            BATCH_SIZE,

        "learning_rate":
            LR,

        "training_mode":
            "clean_ce_architecture_screen",

        "reliability_protocol":
            "v2",

        "expected_training_runs":
            12,

        "expected_reliability_runs":
            12,

        "expected_corruption_cases":
            396,

        "claim_boundary":
            (
                "Development screening only; "
                "not final paper evidence."
            ),

        "hashes":
            hashes,
    }


    PROTOCOL_DIR.mkdir(
        parents=True,
        exist_ok=True
    )


    manifest_path = (
        PROTOCOL_DIR /
        "protocol_manifest.json"
    )


    if manifest_path.exists():

        existing = load_json(
            manifest_path
        )


        if existing != manifest:

            raise RuntimeError(
                "Existing screening protocol differs. "
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
        "V25_SCREENING_R1_PREFLIGHT_PASS=True"
    )

    print(
        "SCREEN_DATASETS=2"
    )

    print(
        "SCREEN_CANDIDATES=2"
    )

    print(
        "SCREEN_SEEDS=3"
    )

    print(
        "SCREEN_TRAINING_RUNS=12"
    )

    print(
        "SCREEN_RELIABILITY_RUNS=12"
    )

    print(
        "SCREEN_CORRUPTION_CASES=396"
    )


def run(
    datasets
):

    manifest = (
        PROTOCOL_DIR /
        "protocol_manifest.json"
    )


    if not manifest.exists():

        raise RuntimeError(
            "Preflight has not been completed"
        )


    protocol_sha = sha256_file(
        manifest
    )


    device = torch.device(
        "cuda"
    )


    print(
        "V25_SCREENING_R1_WORKER_START=True",
        flush=True
    )

    print(
        "DEVICE=",
        device,
        flush=True
    )

    print(
        "DATASETS=",
        datasets,
        flush=True
    )


    for dataset in datasets:

        for candidate in CANDIDATES:

            for seed in SEEDS:

                train_one(
                    dataset,
                    candidate,
                    seed,
                    device,
                    protocol_sha
                )


    for dataset in datasets:

        for candidate in CANDIDATES:

            for seed in SEEDS:

                reliability_one(
                    dataset,
                    candidate,
                    seed,
                    device,
                    protocol_sha
                )


    print(
        "V25_SCREENING_R1_WORKER_COMPLETE=True",
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
