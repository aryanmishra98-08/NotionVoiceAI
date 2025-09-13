import os
import yaml
import logging


class YamalParser(yaml.YAMLObject):
    yaml_loader = yaml.SafeLoader
    yaml_tag = '!Parse'

    @classmethod
    def from_yaml(cls, loader, node):
        """
        Concatenates the values in the YAML node. If a part of the value includes an environment
        variable reference (using os.environ.get), it is evaluated and concatenated accordingly.
        """
        concat_value = ""
        for item in node.value:
            # Check if the item requires environment variable resolution
            if "os.environ.get" in str(item.value):
                # Evaluate the os.environ.get() call
                env_value = eval(item.value)
                concat_value += env_value
            else:
                concat_value += item.value
        return concat_value


# Register the custom YAML parser so that PyYAML uses it when it encounters the !Parse tag
yaml.add_constructor(YamalParser.yaml_tag,
                     YamalParser.from_yaml, Loader=YamalParser.yaml_loader)


def load_config(config_path="config/app_config.yaml"):
    """
    Loads configuration from a YAML file located at config_path.
    Returns the loaded configuration as a Python dictionary.
    """
    # Use the directory of this script rather than the current working directory
    script_directory = os.path.dirname(os.path.abspath(__file__))
    full_config_path = os.path.join(script_directory, config_path)
    with open(full_config_path, "r") as f:
        config_data = yaml.safe_load(f)
    return config_data


# Load the configuration data from the specified YAML file
config_data = load_config()

def setup_logging():
    """
    Sets up logging configuration based on the loaded config_data.
    """
    logger = logging.getLogger()
    logger.setLevel(level=logging.INFO)
    return logger


# Initialize the logger using the setup_logging function
logger = setup_logging()