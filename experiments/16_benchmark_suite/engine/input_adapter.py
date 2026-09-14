
import torch


def extract_input(batch):

    """
    Universal IMU batch extractor.

    Supports:

    (x,y)

    (x_clean,x_corrupt,y)

    """

    if isinstance(batch,(list,tuple)):

        if len(batch)==3:

            candidates=[
                batch[1],
                batch[0]
            ]

            for c in candidates:

                if hasattr(c,"shape"):

                    return c


        if len(batch)>=2:

            x=batch[0]

            if hasattr(x,"shape"):

                return x


    if hasattr(batch,"shape"):

        return batch


    raise RuntimeError(
        f"Unsupported batch format {type(batch)}"
    )






def prepare_model_input(
    model,
    x
):


    name=model.__class__.__name__



    # -------------------------------------------------
    # CNN1D
    # -------------------------------------------------

    if name=="CNN1D":

        if x.ndim==3 and x.shape[1] < x.shape[2]:

            x=x.transpose(
                1,
                2
            )

        return x



    # -------------------------------------------------
    # Reliability CNN
    # -------------------------------------------------

    if name=="ReliabilityCNN1D":

        if x.ndim==3 and x.shape[1] < x.shape[2]:

            x=x.transpose(
                1,
                2
            )

        return x



    # -------------------------------------------------
    # LSTM
    # -------------------------------------------------

    if name=="LSTMClassifier":

        # B,T,C

        if x.ndim==3 and x.shape[1] < x.shape[2]:

            x=x.transpose(
                1,
                2
            )

        return x



    # -------------------------------------------------
    # DeepConvLSTM
    # -------------------------------------------------

    if name=="DeepConvLSTM":

        # model internally transposes

        # requires B,T,C

        if x.ndim==3 and x.shape[1] > x.shape[2]:

            return x


        if x.ndim==3:

            x=x.transpose(
                1,
                2
            )


        return x



    # -------------------------------------------------
    # Transformer
    # -------------------------------------------------

    if name=="IMUTransformer":

        # B,T,C

        if x.ndim==3 and x.shape[1] < x.shape[2]:

            x=x.transpose(
                1,
                2
            )

        return x



    return x
