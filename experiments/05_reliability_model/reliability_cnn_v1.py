

import torch
import torch.nn as nn


class ReliabilityEstimator(nn.Module):

    """
    Estimates reliability score
    for each IMU channel.

    Input:
        B x T x 6

    Output:
        B x 6
    """

    def __init__(self):

        super().__init__()

        self.encoder=nn.Sequential(

            nn.Conv1d(
                6,
                32,
                kernel_size=5,
                padding=2
            ),

            nn.ReLU(),

            nn.AdaptiveAvgPool1d(1)

        )


        self.fc=nn.Sequential(

            nn.Linear(
                32,
                6
            ),

            nn.Sigmoid()

        )


    def forward(self,x):

        # B,T,C -> B,C,T

        x=x.transpose(1,2)

        x=self.encoder(x)

        x=x.squeeze(-1)

        return self.fc(x)



class ReliabilityCNN1D(nn.Module):

    """
    Reliability-aware 1D CNN

    Input:
        B x 128 x 6

    Output:
        class logits
    """

    def __init__(self,classes):

        super().__init__()


        self.reliability=ReliabilityEstimator()


        self.feature_extractor=nn.Sequential(

            nn.Conv1d(
                6,
                64,
                kernel_size=5,
                padding=2
            ),

            nn.ReLU(),

            nn.BatchNorm1d(
                64
            ),


            nn.MaxPool1d(2),


            nn.Conv1d(
                64,
                128,
                kernel_size=5,
                padding=2
            ),

            nn.ReLU(),

            nn.BatchNorm1d(
                128
            ),


            nn.AdaptiveAvgPool1d(1)

        )


        self.classifier=nn.Linear(
            128,
            classes
        )


    def forward(self,x):


        # estimate sensor quality

        r=self.reliability(x)


        # B,6 -> B,1,6

        r=r.unsqueeze(1)


        # adaptive sensor weighting

        x=x*r


        # CNN expects B,C,T

        x=x.transpose(1,2)


        x=self.feature_extractor(x)


        x=x.squeeze(-1)


        return self.classifier(x), r.squeeze(1)



if __name__=="__main__":


    model=ReliabilityCNN1D(
        classes=6
    )


    x=torch.randn(
        8,
        128,
        6
    )


    logits,reliability=model(x)


    print(
        "INPUT=",
        x.shape
    )


    print(
        "LOGITS=",
        logits.shape
    )


    print(
        "RELIABILITY=",
        reliability.shape
    )


    params=sum(
        p.numel()
        for p in model.parameters()
    )


    print(
        "PARAMETERS=",
        params
    )


    print(
        "RELIABILITY_CNN_V1_FORWARD_PASS=True"
    )

