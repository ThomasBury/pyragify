import yaml
from pathlib import Path

def load_yaml_config(config_path: Path) -> dict:
    """
    Load a YAML configuration file.

    Parameters
    ----------
    config_path : pathlib.Path
        The path to the YAML configuration file to load.

    Returns
    -------
    dict
        A dictionary representing the contents of the YAML file.

    Raises
    ------
    FileNotFoundError
        If the configuration file does not exist.
    ValueError
        If there is an error parsing the YAML file.

    Notes
    -----
    This function uses `yaml.safe_load` to safely parse the YAML file, ensuring only standard YAML structures are loaded.

    Examples
    --------
    To load a configuration file:
        >>> config = load_yaml_config(Path("config.yaml"))
        >>> print(config)
        {'repo_path': '/path/to/repo', 'max_words': 100000}
    """
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing YAML file: {e}")

def validate_directory(path: Path):
    """
    Ensure a directory exists or create it.
    
    Parameters
    ----------
    path : pathlib.Path
        The path to the directory to validate or create.
    
    Notes
    -----
    - If the directory does not exist, it will be created, including any intermediate directories.
    - If the directory already exists, no action is taken.
    
    Examples
    --------
    To validate or create a directory:
        >>> validate_directory(Path("/path/to/output"))
        # If the directory doesn't exist, it will be created.
    """

    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
