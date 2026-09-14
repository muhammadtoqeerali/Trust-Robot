import random
import numpy as np
import torch
import os


def set_seed(seed=42):

    random.seed(seed)

    np.random.seed(
        seed
    )

    torch.manual_seed(
        seed
    )


    if torch.cuda.is_available():

        torch.cuda.manual_seed_all(
            seed
        )


    os.environ[
        "PYTHONHASHSEED"
    ] = str(seed)


    torch.backends.cudnn.deterministic=True

    torch.backends.cudnn.benchmark=False



def get_seed():

    return 42
