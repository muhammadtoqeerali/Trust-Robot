import pandas as pd



def aggregate_robustness(records):

    df=pd.DataFrame(records)


    summary=(

        df

        .groupby("model")

        .agg({

            "clean_accuracy":
                "mean",

            "corrupted_accuracy":
                "mean",

            "clean_f1":
                "mean",

            "corrupted_f1":
                "mean",

            "accuracy_degradation":
                "mean",

            "macro_f1_degradation":
                "mean",

            "reliability_score":
                "mean"

        })

        .reset_index()

    )


    summary["robustness_gap"]=(

        summary["clean_accuracy"]

        -

        summary["corrupted_accuracy"]

    )


    return summary



def aggregate_corruption_type(records):

    df=pd.DataFrame(records)


    result=(

        df

        .groupby(
            [
                "model",
                "corruption"
            ]
        )

        ["corrupted_accuracy"]

        .mean()

        .unstack()

        .reset_index()

    )


    return result
