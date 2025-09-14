import os
import yaml
import logging
import logging.config
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv("keys/.env")


def init_logs_folder(folder_name="logs"):
    """
    Ensures that a logs folder exists in the current working directory.
    Returns the full path of the logs folder.
    """
    current_directory = os.getcwd()
    logs_directory = os.path.join(current_directory, folder_name)
    if not os.path.isdir(logs_directory):
        try:
            os.makedirs(logs_directory)
        except Exception as e:
            print("Log Folder Creation Failed - " + str(e))
    return logs_directory


# Create (or verify) logs directory
logs_dir = init_logs_folder()


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


def load_config(config_path="config/ivr_config.yaml"):
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
    try:
        logging_config = config_data.get('logging')
        if logging_config is None:
            raise ValueError(
                "Logging configuration ('logging') section missing from config file.")
        logging.config.dictConfig(logging_config)
        logger = logging.getLogger(__name__)
        return logger
    except Exception as e:
        print("Logging configuration failed: " + str(e))


# Initialize the logger using the setup_logging function
logger = setup_logging()
