import time
import torch

from engine.model_forward import model_forward



def count_parameters(model):

    return sum(
        p.numel()
        for p in model.parameters()
    )



def model_size_mb(model):

    return (
        count_parameters(model)*4
        /
        (1024**2)
    )



def measure_latency(
    model,
    input_shape,
    device,
    runs=100
):


    model.eval()


    x=torch.randn(
        *input_shape
    ).to(device)



    with torch.no_grad():


        for _ in range(10):

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



    total=end-start


    return {

        "latency_ms":
            total/runs*1000,

        "throughput":
            runs/total

    }



def profile_model(
    model,
    input_shape,
    device
):

    result={}


    result["parameters"]=count_parameters(model)

    result["model_size_MB"]=model_size_mb(model)


    result.update(
        measure_latency(
            model,
            input_shape,
            device
        )
    )


    return result
