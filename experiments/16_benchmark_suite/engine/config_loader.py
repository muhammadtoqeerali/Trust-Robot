from pathlib import Path
import yaml


BASE = Path(
    "experiments/16_benchmark_suite/configs"
)



def load_yaml(path):

    with open(path,"r") as f:

        return yaml.safe_load(f)



def load_model_config(
    dataset,
    model
):

    registry = load_yaml(
        BASE /
        "models" /
        "model_registry.yaml"
    )


    entry = registry["models"][model]


    filename = (
        entry[dataset]["config"]
    )


    path = (
        BASE /
        dataset /
        filename
    )


    return load_yaml(path)



def load_default_config():

    return load_yaml(
        BASE /
        "experiments" /
        "benchmark_default.yaml"
    )



def merge_configs(
    default,
    specific
):

    result = default.copy()


    for key,value in specific.items():

        if isinstance(value,dict) and key in result:

            result[key].update(
                value
            )

        else:

            result[key]=value


    return result



def load_experiment_config(
    dataset,
    model
):

    default = load_default_config()


    specific = load_model_config(
        dataset,
        model
    )


    return merge_configs(
        default,
        specific
    )
