import torch
import time

from engine.model_forward import model_forward


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


def extract_input(batch):

    """
    Universal batch extractor.

    Supports:
    (x,y)

    (x_clean,x_corrupt,y)

    tensor
    """

    if torch.is_tensor(batch):
        return batch


    if isinstance(batch,(list,tuple)):

        for item in batch:

            if torch.is_tensor(item):

                return item


    raise RuntimeError(
        f"Unsupported batch type {type(batch)}"
    )


def infer_input_shape(loader):

    batch=next(iter(loader))

    x=extract_input(batch)

    return list(x.shape[1:])


def model_size_mb(model):

    params=count_parameters(model)

    return (
        params*4
    )/(1024**2)



def measure_latency(
    model,
    loader,
    device
):

    model.eval()


    batch=next(
        iter(loader)
    )


    x=extract_input(
        batch
    )


    x=x.to(device)


    runs=50


    with torch.no_grad():


        # warmup
        model_forward(
            model,
            x
        )


        start=time.time()


        for _ in range(runs):

            model_forward(
                model,
                x
            )


        end=time.time()


    return (
        (end-start)
        /
        runs
        *
        1000
    )



def collect_metadata(
    model,
    loader,
    device
):

    return {

        "parameters":
            count_parameters(model),

        "trainable_parameters":
            count_trainable_parameters(model),

        "model_size_mb":
            model_size_mb(model),

        "latency_ms":
            measure_latency(
                model,
                loader,
                device
            )
    }
