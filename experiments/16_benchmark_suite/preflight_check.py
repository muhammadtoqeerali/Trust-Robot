
from engine.config_loader import load_experiment_config
from engine.model_registry import load_model_registry


datasets = [
    "UCI_HAR",
    "PAMAP2"
]


registry = load_model_registry()


failed = []


for model in registry:

    for dataset in datasets:

        try:

            cfg = load_experiment_config(
                dataset,
                model
            )

            print(
                "OK:",
                dataset,
                model,
                "epochs=",
                cfg["training"]["epochs"]
            )

        except Exception as e:

            print(
                "FAILED:",
                dataset,
                model,
                str(e)
            )

            failed.append(
                (dataset, model)
            )


print()
print("==========================")

if failed:

    print(
        "PREFLIGHT_FAILED"
    )

    for item in failed:
        print(item)

else:

    print(
        "PREFLIGHT_PASS"
    )

