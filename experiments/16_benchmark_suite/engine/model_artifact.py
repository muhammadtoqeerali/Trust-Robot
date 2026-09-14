import json
from pathlib import Path



def count_parameters(model):

    return sum(
        p.numel()
        for p in model.parameters()
    )



def count_trainable_parameters(model):

    return sum(
        p.numel()
        for p in model.parameters()
        if p.requires_grad
    )



def create_model_metadata(
    model
):

    return {

        "parameters":
            count_parameters(model),

        "trainable_parameters":
            count_trainable_parameters(model),

        "architecture":
            model.__class__.__name__

    }



def save_model_metadata(
    path,
    metadata
):

    Path(path).write_text(
        json.dumps(
            metadata,
            indent=2
        )
    )
