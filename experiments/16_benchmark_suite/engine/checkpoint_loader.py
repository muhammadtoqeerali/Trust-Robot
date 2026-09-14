from pathlib import Path
import torch


def load_checkpoint(
    model,
    checkpoint_path,
    device
):

    checkpoint_path=Path(
        checkpoint_path
    )


    state=torch.load(
        checkpoint_path,
        map_location=device
    )


    model.load_state_dict(
        state
    )


    model.to(
        device
    )


    model.eval()


    return model
