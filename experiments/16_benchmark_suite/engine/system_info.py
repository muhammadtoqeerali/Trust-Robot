
import platform
import torch



def collect_system_info():

    return {

        "python":
            platform.python_version(),

        "pytorch":
            torch.__version__,

        "cuda":
            torch.version.cuda,

        "gpu":
            torch.cuda.get_device_name(0)
            if torch.cuda.is_available()
            else "CPU"

    }
