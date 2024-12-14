import typer
import logging
from pathlib import Path
from omegaconf import OmegaConf
from pyragify.processor import RepoContentProcessor

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

app = typer.Typer(help="A tool to process repositories and output text files for NotebookLM.")

@app.command()
def process_repo(
    config_file: Path = typer.Option("config.yaml", help="Path to the configuration YAML file."),
    repo_path: Path = typer.Option(None, help="Override: Path to the repository to process."),
    output_dir: Path = typer.Option(None, help="Override: Directory to save output files."),
    max_words: int = typer.Option(None, help="Override: Maximum number of words per output file."),
    max_file_size: int = typer.Option(None, help="Override: Maximum file size to process (in bytes)."),
    skip_patterns: list[str] = typer.Option(None, help="Override: List of file patterns to skip."),
    skip_dirs: list[str] = typer.Option(None, help="Override: List of directories to skip."),
    verbose: bool = typer.Option(None, help="Override: Enable verbose output.")
):
    """
    Process a repository and output its content to text files with a specified word limit.

    This command processes a repository using a configuration file and optional command-line overrides. 
    It outputs text files based on the repository's contents and saves metadata about the processing.

    Parameters
    ----------
    config_file : pathlib.Path, optional
        The path to the configuration YAML file. Default is "config.yaml".
    repo_path : pathlib.Path, optional
        Override for the path to the repository to process. Defaults to the value in the configuration file.
    output_dir : pathlib.Path, optional
        Override for the directory where output files will be saved. Defaults to the value in the configuration file.
    max_words : int, optional
        Override for the maximum number of words allowed per output file. Defaults to the value in the configuration file.
    max_file_size : int, optional
        Override for the maximum file size (in bytes) to process. Defaults to the value in the configuration file.
    skip_patterns : list of str, optional
        Override for the list of file patterns to skip (e.g., "*.log", "*.tmp"). Defaults to the value in the configuration file.
    skip_dirs : list of str, optional
        Override for the list of directory names to skip (e.g., "node_modules", "__pycache__"). Defaults to the value in the configuration file.
    verbose : bool, optional
        Override for enabling verbose output. When enabled, the logging level is set to DEBUG. Defaults to the value in the configuration file.

    Notes
    -----
    - If a configuration file exists, its settings are loaded first.
    - Command-line options take precedence and override corresponding configuration file values.
    - The repository is processed based on the final resolved configuration, and results are saved to the specified output directory.
    - Errors during processing are logged, and the command exits with an error code.

    Examples
    --------
    Run the command with the default configuration file:
        $ python -m yourmodule.cli process-repo

    Override the repository path and enable verbose output:
        $ python -m yourmodule.cli process-repo --repo-path /path/to/repo --verbose

    Specify a custom configuration file:
        $ python -m yourmodule.cli process-repo --config-file custom_config.yaml
    """

    # Load configuration from YAML
    if config_file.exists():
        config = OmegaConf.load(config_file)
        logger.info(f"Loaded configuration from {config_file}")
    else:
        logger.error(f"Configuration file {config_file} not found.")
        raise typer.Exit(code=1)

    # Apply CLI overrides
    overrides = {
        "repo_path": repo_path,
        "output_dir": output_dir,
        "max_words": max_words,
        "max_file_size": max_file_size,
        "skip_patterns": skip_patterns,
        "skip_dirs": skip_dirs,
        "verbose": verbose,
    }
    for key, value in overrides.items():
        if value is not None:
            config[key] = value

    if config.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose mode enabled. Setting logging level to DEBUG.")

    # Initialize and run the processor
    try:
        processor = RepoContentProcessor(
            repo_path=Path(config.repo_path),
            output_dir=Path(config.output_dir),
            max_words=config.max_words,
            max_file_size=config.max_file_size,
            skip_patterns=config.skip_patterns,
            skip_dirs=config.skip_dirs
        )
        processor.process_repo()
        logger.info("Repository processing completed successfully!")
    except Exception as e:
        logger.error(f"An error occurred during repository processing: {e}")
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
