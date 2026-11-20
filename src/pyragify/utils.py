from pathlib import Path


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
