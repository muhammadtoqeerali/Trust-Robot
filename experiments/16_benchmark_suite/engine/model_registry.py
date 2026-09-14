
from pathlib import Path
import yaml
import importlib
import importlib.util
import inspect
import sys


BASE = Path(
    "experiments/16_benchmark_suite"
)


PROJECT_ROOT = Path(
    __file__
).resolve().parents[3]


if str(PROJECT_ROOT) not in sys.path:

    sys.path.insert(
        0,
        str(PROJECT_ROOT)
    )



def load_model_registry():

    config = BASE / "registry/models.yaml"

    data = yaml.safe_load(
        config.read_text()
    )

    return data["models"]



def import_from_file(
    path,
    module_name
):

    spec = importlib.util.spec_from_file_location(
        module_name,
        path
    )

    module = importlib.util.module_from_spec(
        spec
    )

    spec.loader.exec_module(
        module
    )

    return module



def create_model(
    name,
    num_classes,
    input_channels=6
):


    registry=load_model_registry()


    if name not in registry:

        raise ValueError(
            f"Unknown model {name}"
        )


    entry=registry[name]


    module_name=entry["module"]

    class_name=entry["class"]



    # project model

    if module_name.startswith(
        "models."
    ):

        path=(
            PROJECT_ROOT
            /
            module_name.replace(
                ".",
                "/"
            )
        ).with_suffix(
            ".py"
        )


        module=import_from_file(
            path,
            name
        )


    else:


        path=(
            BASE
            /
            "models"
            /
            f"{module_name}.py"
        )


        if path.exists():

            module=import_from_file(
                path,
                name
            )

        else:

            module=importlib.import_module(
                module_name
            )



    cls=getattr(
        module,
        class_name
    )


    signature=inspect.signature(
        cls.__init__
    )



    if "input_channels" in signature.parameters:

        return cls(
            num_classes,
            input_channels=input_channels
        )


    return cls(
        num_classes
    )
