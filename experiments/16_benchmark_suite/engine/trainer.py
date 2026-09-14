import time
import json
from pathlib import Path

import torch

from sklearn.metrics import f1_score

from engine.model_forward import model_forward



def unpack_output(output):

    if isinstance(output, tuple):

        return output[0], output[1]

    return output, None



def train_model(
    model,
    train_loader,
    val_loader,
    optimizer,
    criterion,
    device,
    epochs,
    save_path,
    mode="standard",
    consistency_weight=0.2,
    patience=15
):


    best_f1=0.0
    patience_count=0

    history=[]


    start=time.time()


    for epoch in range(1,epochs+1):


        model.train()

        total_loss=0.0



        for batch in train_loader:


            optimizer.zero_grad()



            if mode=="reliability":


                clean,corrupt,y=batch


                clean=clean.to(device)
                corrupt=corrupt.to(device)
                y=y.to(device)


                clean_raw=model_forward(
                    model,
                    clean
                )


                corrupt_raw=model_forward(
                    model,
                    corrupt
                )


                clean_logits,clean_feat=unpack_output(
                    clean_raw
                )

                corrupt_logits,corrupt_feat=unpack_output(
                    corrupt_raw
                )


                cls_loss=criterion(
                    clean_logits,
                    y
                )


                if clean_feat is not None and corrupt_feat is not None:

                    consistency_loss=torch.mean(
                        (clean_feat-corrupt_feat)**2
                    )

                else:

                    consistency_loss=torch.tensor(
                        0.0,
                        device=device
                    )


                loss=(
                    cls_loss
                    +
                    consistency_weight*
                    consistency_loss
                )


            else:


                x,y=batch


                x=x.to(device)
                y=y.to(device)


                output=model_forward(
                    model,
                    x
                )


                loss=criterion(
                    output,
                    y
                )



            loss.backward()

            optimizer.step()


            total_loss += loss.item()



        # validation

        model.eval()


        predictions=[]
        labels=[]


        with torch.no_grad():


            for batch in val_loader:


                x,y=batch


                x=x.to(device)
                y=y.to(device)


                output=model_forward(
                    model,
                    x
                )


                pred=output.argmax(
                    dim=1
                )


                predictions.extend(
                    pred.cpu().numpy()
                )

                labels.extend(
                    y.cpu().numpy()
                )



        accuracy=sum(
            p==l
            for p,l in zip(
                predictions,
                labels
            )
        )/len(labels)



        macro_f1=f1_score(
            labels,
            predictions,
            average="macro"
        )



        history.append(
            {
                "epoch":epoch,
                "train_loss":
                    total_loss/len(train_loader),
                "val_accuracy":
                    accuracy,
                "val_macro_f1":
                    macro_f1
            }
        )



        if macro_f1 > best_f1:

            best_f1=macro_f1

            patience_count=0


            torch.save(
                model.state_dict(),
                save_path
            )

        else:

            patience_count+=1


        if patience_count>=patience:

            break



    return {

        "history":history,

        "best_f1":best_f1,

        "training_time":
            time.time()-start

    }
