import pandas as pd


def aggregate_performance(records):

    df=pd.DataFrame(records)

    summary=(

        df
        .groupby("model")
        .agg({

            "accuracy":"mean",
            "macro_f1":"mean",
            "weighted_f1":"mean",
            "precision":"mean",
            "recall":"mean",
            "latency_ms_per_sample":"mean",
            "parameters":"mean",
            "model_size_mb":"mean",
            "training_seconds":"mean"

        })

        .reset_index()

    )


    return summary



def aggregate_reliability(records):

    df=pd.DataFrame(records)


    overall=(

        df
        .groupby("model")
        .agg({

            "reliability_score":"mean",

            "accuracy_degradation":"mean",

            "macro_f1_degradation":"mean"

        })

        .reset_index()

    )


    corruption=(

        df

        .groupby(
            [
                "model",
                "corruption"
            ]
        )

        ["reliability_score"]

        .mean()

        .unstack()

        .reset_index()

    )


    return overall, corruption



def add_efficiency_metrics(df):

    df=df.copy()


    df["accuracy_per_million_params"]=(

        df["accuracy"]

        /

        (
            df["parameters"]/1_000_000
        )

    )


    df["f1_per_mb"]=(

        df["macro_f1"]

        /

        df["model_size_mb"]

    )


    return df
