import torch
import numpy as np

from engine.model_forward import model_forward



def corrupt_signal(
    x,
    mode
):

    x=x.clone()


    if mode=="noise":

        x += torch.randn_like(x)*0.1


    elif mode=="channel_dropout":

        c=np.random.randint(
            x.shape[-1]
        )

        x[:,:,c]=0


    elif mode=="sensor_missing":

        x[:,:,:]=0


    return x



def evaluate_corruption(
    model,
    loader,
    device
):


    model.eval()

    results={}



    for mode in [

        "noise",
        "channel_dropout",
        "sensor_missing"

    ]:


        correct=0
        total=0



        with torch.no_grad():


            for x,y in loader:


                x=corrupt_signal(
                    x,
                    mode
                )


                x=x.to(device)
                y=y.to(device)


                out=model_forward(
                    model,
                    x
                )


                pred=out.argmax(
                    dim=1
                )


                correct += (
                    pred==y
                ).sum().item()


                total += y.size(0)



        results[mode]={

            "accuracy":
                correct/total

        }



    return results
