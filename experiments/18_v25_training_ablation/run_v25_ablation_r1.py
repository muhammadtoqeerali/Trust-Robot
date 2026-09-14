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

REPO = HERE.parents[1]

SUITE = (
    REPO /
    "experiments" /
    "16_benchmark_suite"
)

SCREEN = (
    REPO /
    "experiments" /
    "17_v25_screening"
)

sys.path.insert(
    0,
    str(SUITE)
)

sys.path.insert(
    0,
    str(SCREEN)
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
    "v25_ablation_r1"
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


SCREEN_RESULT_ROOT = (
    REPO /
    "results" /
    "v25_screening_r1"
)


SCREEN_PROTOCOL = (
    SCREEN_RESULT_ROOT /
    "protocol" /
    "protocol_manifest.json"
)


SCREEN_RECEIPT = (
    SCREEN_RESULT_ROOT /
    "final_analysis" /
    "v25_screening_r1_analysis_receipt.json"
)


REGISTRY = (
    REPO /
    "configs" /
    "reliability" /
    "corruption_registry_v2.json"
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


SEEDS = [
    42,
    123,
    456,
]


NEW_MODES = [
    "exposure",
    "consistency"
]


EPOCHS = 100

BATCH_SIZE = 64

LEARNING_RATE = 0.001

CORRUPTION_PROBABILITY = 0.3

CONSISTENCY_WEIGHT = 0.2


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
            f"Dataset integrity mismatch: "
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

    predictions = []

    with torch.inference_mode():

        for x, y in loader:

            x = x.to(device)

            y = y.to(device)

            logits = model(x)

            pred = logits.argmax(
                dim=1
            )

            truth.extend(
                y.cpu().tolist()
            )

            predictions.extend(
                pred.cpu().tolist()
            )

    return {

        "accuracy":
            float(
                accuracy_score(
                    truth,
                    predictions
                )
            ),

        "macro_f1":
            float(
                f1_score(
                    truth,
                    predictions,
                    average="macro",
                    zero_division=0
                )
            ),
    }


def deterministic_corruption(
    clean,
    seed,
    epoch,
    batch_index,
    schedule_hasher
):

    if clean.ndim != 3:

        raise ValueError(
            f"Expected [B,T,C], got "
            f"{tuple(clean.shape)}"
        )

    if clean.shape[-1] != 6:

        raise ValueError(
            f"Expected six channels, got "
            f"{tuple(clean.shape)}"
        )


    generator = torch.Generator(
        device="cpu"
    )


    corruption_seed = (
        int(seed)
        *
        10_000_019
        +
        int(epoch)
        *
        100_003
        +
        int(batch_index)
        *
        1_009
    ) % (
        2**63 - 1
    )


    generator.manual_seed(
        corruption_seed
    )


    batch_size = clean.shape[0]


    apply_mask = (
        torch.rand(
            batch_size,
            generator=generator
        )
        <
        CORRUPTION_PROBABILITY
    )


    channels = torch.randint(
        low=0,
        high=6,
        size=(
            batch_size,
        ),
        generator=generator
    )


    schedule_hasher.update(
        np.asarray(
            [
                seed,
                epoch,
                batch_index,
                batch_size,
            ],
            dtype=np.int64
        ).tobytes()
    )


    schedule_hasher.update(
        apply_mask.numpy().astype(
            np.uint8
        ).tobytes()
    )


    schedule_hasher.update(
        channels.numpy().astype(
            np.int16
        ).tobytes()
    )


    corrupted = clean.clone()


    selected = torch.nonzero(
        apply_mask,
        as_tuple=False
    ).squeeze(1)


    if selected.numel() > 0:

        selected_device = selected.to(
            clean.device
        )

        channel_device = channels[
            selected
        ].to(
            clean.device
        )


        corrupted[
            selected_device,
            :,
            channel_device
        ] = 0.0


    return corrupted


def train_one(
    dataset,
    mode,
    seed,
    device,
    protocol_sha
):

    out = (
        RAW_ROOT /
        dataset /
        mode /
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
            mode,
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

        "V25Dense64",

        data[
            "num_classes"
        ],

        input_channels=6

    ).to(device)


    if not hasattr(
        model,
        "forward_with_features"
    ):

        raise RuntimeError(
            "V25Dense64 has no "
            "forward_with_features()"
        )


    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=LEARNING_RATE
    )


    criterion = (
        nn.CrossEntropyLoss()
    )


    consistency_criterion = (
        nn.MSELoss()
    )


    best_f1 = -1.0

    best_epoch = None

    history = []

    schedule_hasher = (
        hashlib.sha256()
    )


    start_time = time.time()


    print()
    print(
        "=" * 76,
        flush=True
    )

    print(
        "TRAIN_START:",
        dataset,
        "V25Dense64",
        mode,
        seed,
        flush=True
    )

    print(
        "=" * 76,
        flush=True
    )


    for epoch in range(
        1,
        EPOCHS + 1
    ):

        model.train()

        running_loss = 0.0

        running_cls = 0.0

        running_consistency = 0.0

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


            clean_logits, clean_features = (
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


            if mode == "exposure":

                # Replicates the effective V3R1
                # behavior:
                #
                # corrupted forward exposure
                # updates BatchNorm statistics,
                # but contributes no explicit
                # consistency gradient.

                with torch.no_grad():

                    model.forward_with_features(
                        corrupted
                    )


                consistency_loss = (
                    torch.zeros(
                        (),
                        device=device
                    )
                )


                loss = (
                    classification_loss
                )


            elif mode == "consistency":

                _, corrupted_features = (
                    model.forward_with_features(
                        corrupted
                    )
                )


                consistency_loss = (
                    consistency_criterion(

                        clean_features,

                        corrupted_features
                    )
                )


                loss = (
                    classification_loss
                    +
                    CONSISTENCY_WEIGHT
                    *
                    consistency_loss
                )


            else:

                raise KeyError(
                    mode
                )


            loss.backward()

            optimizer.step()


            batch_size = y.shape[0]


            running_loss += (
                float(
                    loss.item()
                )
                *
                batch_size
            )


            running_cls += (
                float(
                    classification_loss.item()
                )
                *
                batch_size
            )


            running_consistency += (
                float(
                    consistency_loss.item()
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


        epoch_cls = (
            running_cls
            /
            max(
                examples,
                1
            )
        )


        epoch_consistency = (
            running_consistency
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

                "training_loss":
                    epoch_loss,

                "classification_loss":
                    epoch_cls,

                "consistency_loss":
                    epoch_consistency,

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
                "CLS=",
                f"{epoch_cls:.6f}",
                "CONS=",
                f"{epoch_consistency:.6f}",
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

    model.to(device)


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


    schedule_sha = (
        schedule_hasher.hexdigest()
    )


    metrics = {

        "dataset":
            dataset,

        "model":
            "V25Dense64",

        "mode":
            mode,

        "seed":
            seed,

        "epochs":
            EPOCHS,

        "batch_size":
            BATCH_SIZE,

        "learning_rate":
            LEARNING_RATE,

        "corruption_probability":
            CORRUPTION_PROBABILITY,

        "corruption_type":
            (
                "deterministic_random_"
                "full_channel_zeroing"
            ),

        "corruption_schedule_sha256":
            schedule_sha,

        "consistency_feature_available":
            True,

        "consistency_weight":
            (
                CONSISTENCY_WEIGHT
                if mode == "consistency"
                else 0.0
            ),

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
                    SCREEN /
                    "v25_candidates.py"
                ),

            "checkpoint_sha256":
                sha256_file(
                    out /
                    "best_model.pt"
                ),

            "corruption_schedule_sha256":
                schedule_sha,
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
        mode,
        seed,
        "TEST_ACC=",
        f"{test['accuracy']:.6f}",
        "TEST_F1=",
        f"{test['macro_f1']:.6f}",
        "SCHEDULE_SHA=",
        schedule_sha,
        flush=True
    )


def reliability_one(
    dataset,
    mode,
    seed,
    device,
    protocol_sha
):

    out = (
        REL_ROOT /
        dataset /
        mode /
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
    ):

        print(
            "RELIABILITY_SKIP_COMPLETE:",
            dataset,
            mode,
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

        "V25Dense64",

        data[
            "num_classes"
        ],

        input_channels=6
    )


    checkpoint = (
        RAW_ROOT /
        dataset /
        mode /
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
        mode,
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
            f"Missing reliability summary: "
            f"{summary}"
        )


    save_json(
        out /
        "ablation_receipt.json",
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


    complete.write_text(
        "COMPLETE\n"
    )


    print(
        "RELIABILITY_COMPLETE:",
        dataset,
        mode,
        seed,
        flush=True
    )


def verify_screening_freeze():

    if not SCREEN_PROTOCOL.exists():

        raise FileNotFoundError(
            SCREEN_PROTOCOL
        )


    screen_manifest = load_json(
        SCREEN_PROTOCOL
    )


    for relative, expected_sha in (
        screen_manifest[
            "hashes"
        ].items()
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
                f"Screening frozen file changed: "
                f"{relative}"
            )


    print(
        "SCREENING_FROZEN_HASHES_VERIFIED=",
        len(
            screen_manifest[
                "hashes"
            ]
        )
    )


def build_protocol_hashes():

    critical = [

        HERE /
        "run_v25_ablation_r1.py",

        SCREEN /
        "v25_candidates.py",

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

        SCREEN_PROTOCOL,

        SCREEN_RECEIPT,
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
        "=" * 78
    )

    print(
        "V25 TRAINING ABLATION R1 PREFLIGHT"
    )

    print(
        "=" * 78
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


    verify_screening_freeze()


    screening_receipt = load_json(
        SCREEN_RECEIPT
    )


    if not screening_receipt.get(
        "integrity_pass",
        False
    ):

        raise RuntimeError(
            "V25 screening receipt is not PASS"
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


        model = create_candidate(

            "V25Dense64",

            data[
                "num_classes"
            ],

            input_channels=6
        )


        params = sum(
            parameter.numel()
            for parameter
            in model.parameters()
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
                "Bad logits shape"
            )


        if features.shape[0] != 2:

            raise RuntimeError(
                "Bad feature output"
            )


        if params > 50000:

            raise RuntimeError(
                f"Parameter target failed: {params}"
            )


        print(
            "V25DENSE64_PASS:",
            dataset,
            "PARAMS=",
            params,
            "FEATURES=",
            tuple(
                features.shape
            )
        )


    # Explicit schedule-equivalence test:
    #
    # same seed/epoch/batch must generate
    # exactly the same corrupted tensor
    # independent of training mode.

    dummy = torch.randn(
        64,
        128,
        6
    )


    h1 = hashlib.sha256()

    h2 = hashlib.sha256()


    c1 = deterministic_corruption(
        dummy,
        42,
        1,
        0,
        h1
    )


    c2 = deterministic_corruption(
        dummy,
        42,
        1,
        0,
        h2
    )


    if not torch.equal(
        c1,
        c2
    ):

        raise RuntimeError(
            "Deterministic corruption failed"
        )


    if h1.hexdigest() != h2.hexdigest():

        raise RuntimeError(
            "Corruption schedule hashes differ"
        )


    print(
        "DETERMINISTIC_CORRUPTION_PASS=True"
    )


    hashes = build_protocol_hashes()


    manifest = {

        "protocol":
            "v25_training_ablation_r1",

        "architecture":
            "V25Dense64",

        "architecture_selection_source":
            "v25_screening_r1",

        "datasets":
            DATASETS,

        "seeds":
            SEEDS,

        "existing_control_mode":
            "clean_ce",

        "new_modes":
            NEW_MODES,

        "epochs":
            EPOCHS,

        "batch_size":
            BATCH_SIZE,

        "learning_rate":
            LEARNING_RATE,

        "training_corruption":
            (
                "per-sample whole-channel zeroing"
            ),

        "corruption_probability":
            CORRUPTION_PROBABILITY,

        "corruption_schedule":
            (
                "dedicated deterministic RNG "
                "derived only from seed, epoch, "
                "batch index"
            ),

        "consistency_weight":
            CONSISTENCY_WEIGHT,

        "reliability_protocol":
            "v2",

        "new_training_runs":
            12,

        "new_reliability_runs":
            12,

        "new_corruption_evaluations":
            396,

        "development_boundary":
            (
                "Training-objective ablation on "
                "two development datasets and "
                "three seeds; final four-dataset "
                "confirmation occurs only after "
                "mode selection."
            ),

        "hashes":
            hashes,
    }


    PROTOCOL_ROOT.mkdir(
        parents=True,
        exist_ok=True
    )


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
                "Existing ablation manifest differs. "
                "Refusing to mix protocol revisions."
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
        "V25_ABLATION_R1_PREFLIGHT_PASS=True"
    )

    print(
        "ARCHITECTURE=V25Dense64"
    )

    print(
        "CONTROL_RUNS_REUSED=6"
    )

    print(
        "NEW_TRAINING_RUNS=12"
    )

    print(
        "NEW_RELIABILITY_RUNS=12"
    )

    print(
        "NEW_CORRUPTION_CASES=396"
    )


def run(datasets):

    manifest = (
        PROTOCOL_ROOT /
        "protocol_manifest.json"
    )


    if not manifest.exists():

        raise RuntimeError(
            "Preflight has not been run"
        )


    protocol_sha = sha256_file(
        manifest
    )


    device = torch.device(
        "cuda"
    )


    print(
        "V25_ABLATION_R1_WORKER_START=True",
        flush=True
    )


    print(
        "ARCHITECTURE=V25Dense64",
        flush=True
    )


    print(
        "NEW_MODES=",
        NEW_MODES,
        flush=True
    )


    print(
        "DATASETS=",
        datasets,
        flush=True
    )


    for dataset in datasets:

        for mode in NEW_MODES:

            for seed in SEEDS:

                train_one(
                    dataset,
                    mode,
                    seed,
                    device,
                    protocol_sha
                )


    for dataset in datasets:

        for mode in NEW_MODES:

            for seed in SEEDS:

                reliability_one(
                    dataset,
                    mode,
                    seed,
                    device,
                    protocol_sha
                )


    print(
        "V25_ABLATION_R1_WORKER_COMPLETE=True",
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
