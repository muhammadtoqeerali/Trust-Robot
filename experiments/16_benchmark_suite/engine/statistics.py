
import numpy as np



def aggregate_runs(values):

    values=np.array(values)


    return {

        "mean":
            float(values.mean()),


        "std":
            float(values.std()),


        "min":
            float(values.min()),


        "max":
            float(values.max())

    }
