from pathlib import Path
import numpy as np
import json
from datetime import datetime



def audit_subject_split(dataset_name):

    base = Path(
        f"data/processed/{dataset_name}"
    )


    result = {

        "timestamp":
            datetime.now().isoformat(),

        "dataset":
            dataset_name,

    }


    # possible subject files

    candidates=[

        base/"subjects.npy",

        base/"subject.npy",

        base/"subject_ids.npy",

        Path(
            f"data/processed/harmonized/{dataset_name}/subjects.npy"
        )

    ]


    subject_file=None


    for c in candidates:

        if c.exists():

            subject_file=c
            break



    if subject_file is None:


        result.update(

        {

        "status":
            "subject_file_not_found",

        "validated":
            False

        }

        )


        return result



    subjects=np.load(
        subject_file
    )


    split_base=Path(
        f"data/processed/splits/{dataset_name}"
    )


    train_idx=np.load(
        split_base/"train_idx.npy"
    )


    test_idx=np.load(
        split_base/"test_idx.npy"
    )


    train_subjects=set(
        subjects[train_idx].tolist()
    )


    test_subjects=set(
        subjects[test_idx].tolist()
    )


    overlap = (
        train_subjects
        &
        test_subjects
    )


    result.update(

    {

    "train_subject_count":
        len(train_subjects),

    "test_subject_count":
        len(test_subjects),

    "overlap_count":
        len(overlap),

    "overlap_subjects":
        list(overlap),

    "validated":
        len(overlap)==0

    }

    )


    return result




def save_subject_audit(
    dataset_name,
    output
):


    result=audit_subject_split(
        dataset_name
    )


    Path(output).write_text(
        json.dumps(
            result,
            indent=2
        )
    )


    return result
