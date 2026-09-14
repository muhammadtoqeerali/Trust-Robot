import json
from pathlib import Path



def compute_degradation(
    clean,
    corrupted
):


    result={}


    for metric in [

        "accuracy",
        "macro_f1"

    ]:


        clean_value=clean.get(
            metric,
            0
        )


        corrupt_value=corrupted.get(
            metric,
            0
        )


        if clean_value == 0:

            degradation=1.0

        else:

            degradation=(

                clean_value -
                corrupt_value

            ) / clean_value



        result[

            metric+"_degradation"

        ]=float(
            degradation
        )


    return result




def compute_reliability_score(
    degradation,
    weights=None
):


    if weights is None:

        weights={

            "accuracy_degradation":0.5,

            "macro_f1_degradation":0.5

        }



    total=0


    for key,value in weights.items():

        total += (

            degradation.get(
                key,
                0
            )
            *
            value

        )


    score=1-total


    return float(
        max(
            0,
            min(
                1,
                score
            )
        )
    )



def create_reliability_summary(
    clean,
    corrupted,
    corruption,
    severity
):


    degradation=compute_degradation(
        clean,
        corrupted
    )


    score=compute_reliability_score(
        degradation
    )


    return {

        "corruption":
            corruption,

        "severity":
            severity,

        "clean_metrics":
            clean,

        "corrupted_metrics":
            corrupted,

        "degradation":
            degradation,

        "reliability_score":
            score

    }



def save_reliability_summary(
    path,
    summary
):

    Path(path).write_text(

        json.dumps(
            summary,
            indent=2
        )

    )
