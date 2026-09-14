
import torch
import torch.nn as nn



class ReliabilityEstimator(nn.Module):

    def __init__(self):

        super().__init__()

        self.encoder = nn.Sequential(

            nn.Conv1d(
                6,
                32,
                kernel_size=5,
                padding=2
            ),

            nn.ReLU(),

            nn.AdaptiveAvgPool1d(1)

        )


        self.fc = nn.Sequential(

            nn.Linear(
                32,
                6
            ),

            nn.Sigmoid()

        )


    def forward(self,x):

        x=x.transpose(1,2)

        x=self.encoder(x)

        x=x.squeeze(-1)

        return self.fc(x)



class ReliabilityCNN1D(nn.Module):


    def __init__(self, classes):

        super().__init__()


        self.reliability = ReliabilityEstimator()


        self.feature_extractor = nn.Sequential(

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


        self.classifier = nn.Linear(
            128,
            classes
        )


    def forward(self,x):

        r=self.reliability(x)

        x=x*r.unsqueeze(1)

        x=x.transpose(1,2)

        x=self.feature_extractor(x)

        x=x.squeeze(-1)

        logits=self.classifier(x)


        return logits, r

