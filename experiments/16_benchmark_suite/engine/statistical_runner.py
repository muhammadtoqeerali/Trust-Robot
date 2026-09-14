import json
import math
from pathlib import Path



def mean(values):

    return sum(values)/len(values)



def std(values):

    m=mean(values)

    return math.sqrt(
        sum(
            (x-m)**2
            for x in values
        )
        /
        len(values)
    )



def confidence_interval(values):

    m=mean(values)

    s=std(values)

    margin=1.96*s/math.sqrt(
        len(values)
    )

    return {

        "mean":m,

        "lower":
            m-margin,

        "upper":
            m+margin

    }




def aggregate_seed_results(
    seed_results
):


    metrics={}


    if len(seed_results)==0:

        return metrics



    keys=seed_results[0].keys()



    for key in keys:


        values=[]


        for result in seed_results:


            value=result.get(
                key
            )


            if isinstance(
                value,
                (int,float)
            ):

                values.append(
                    value
                )



        # only numerical metrics

        if len(values)==0:

            continue



        metrics[key]={

            "values":
                values,


            "mean":
                mean(values),


            "std":
                std(values),


            "confidence_interval":
                confidence_interval(values)

        }



    return metrics



def save_statistics(
    model,
    seed_results,
    output
):


    result={

        "model":
            model,

        "runs":
            len(seed_results),

        "statistics":
            aggregate_seed_results(
                seed_results
            )

    }


    Path(output).write_text(
        json.dumps(
            result,
            indent=2
        )
    )


    return result
