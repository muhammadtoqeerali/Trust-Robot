import torch.nn as nn



def detect_model_type(model):

    name=model.__class__.__name__


    return name



def prepare_input(
    model,
    x
):


    name=detect_model_type(
        model
    )



    # ---------------------------------
    # Reliability CNN
    # expects:
    # B,T,C
    # ---------------------------------

    if name=="ReliabilityCNN1D":

        return x



    # ---------------------------------
    # CNN1D
    # Conv1d expects:
    # B,C,T
    # ---------------------------------

    if name=="CNN1D":

        if x.ndim==3:

            return x.transpose(
                1,
                2
            )



    # ---------------------------------
    # LSTM
    # expects:
    # B,T,C
    # ---------------------------------

    if name=="LSTMClassifier":

        return x



    # ---------------------------------
    # DeepConvLSTM
    # internally:
    # x.transpose(1,2)
    #
    # therefore give:
    # B,T,C
    # ---------------------------------

    if name=="DeepConvLSTM":

        return x



    # ---------------------------------
    # Transformer
    # expects:
    # B,T,C
    # ---------------------------------

    if name=="IMUTransformer":

        return x



    return x




def model_forward(
    model,
    x
):


    x=prepare_input(
        model,
        x
    )


    output=model(
        x
    )


    if isinstance(
        output,
        tuple
    ):

        output=output[0]


    return output
