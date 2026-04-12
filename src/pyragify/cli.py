import typer
import logging
from pathlib import Path
from omegaconf import OmegaConf
from pyragify.processor import RepoContentProcessor, load_json

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
    verbose: bool = typer.Option(None, help="Override: Enable verbose output."),
    enable_graph: bool = typer.Option(None, help="Override: Enable knowledge graph building."),
    graph_output_dir: str = typer.Option(None, help="Override: Directory to save graph files."),
    graph_format: str = typer.Option(None, help="Override: Graph serialization format (json, graphml)."),
    include_relationships: list[str] = typer.Option(None, help="Override: Types of relationships to extract.")
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
        logger.info(f"Loaded configuration from '{config_file}'")
    else:
        config = OmegaConf.create()
        if repo_path is None: # No --repo-path override
            logger.error(f"Configuration file '{config_file}' not found and --repo-path not provided.")
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

    # Handle graph configuration
    if "graph" not in config:
        config["graph"] = {}

    graph_overrides = {
        "enabled": enable_graph,
        "output_dir": graph_output_dir,
        "format": graph_format,
        "relationships": include_relationships,
    }
    for key, value in graph_overrides.items():
        if value is not None:
            config["graph"][key] = value

    if config.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose mode enabled. Setting logging level to DEBUG.")

    # Validate repo_path after config is loaded and merged
    if "repo_path" not in config or not config.repo_path:
        typer.echo("Error: repo_path must be defined in the config file or via --repo-path.", err=True)
        raise typer.Exit(code=1)

    repo_path_obj = Path(config.repo_path)
    if not repo_path_obj.exists():
        typer.echo(f"Error: Repository path '{config.repo_path}' does not exist.", err=True)
        raise typer.Exit(code=1)
    if not repo_path_obj.is_dir():
        typer.echo(f"Error: Repository path '{config.repo_path}' is not a directory.", err=True)
        raise typer.Exit(code=1)
    # Initialize and run the processor
    try:
        processor = RepoContentProcessor(
            repo_path=repo_path_obj,
            output_dir=Path(config.output_dir),
            max_words=config.max_words,
            max_file_size=config.max_file_size,
            skip_patterns=config.skip_patterns,
            skip_dirs=config.skip_dirs,
            enable_graph=config.get("graph", {}).get("enabled", False),
            graph_config=config.get("graph", {})
        )
        processor.process_repo()
        logger.info("Repository processing completed successfully!")
    except Exception as e:
        logger.error(f"An error occurred during repository processing: {e}")
        raise typer.Exit(code=1)

@app.command()
def query_graph(
    graph_path: Path = typer.Option(None, help="Path to the knowledge graph JSON file."),
    command: str = typer.Option(..., help="Query command to execute."),
    entity: str = typer.Option(None, help="Entity ID or name for queries."),
    depth: int = typer.Option(2, help="Traversal depth for related context."),
    pattern: str = typer.Option(None, help="Search pattern for pattern matching."),
    output_format: str = typer.Option("json", help="Output format (json, text).")
):
    """
    Query the knowledge graph for context and relationships.

    Available commands:
    - related: Find related context for an entity
    - hierarchy: Get call hierarchy for a function
    - dependencies: Find dependencies for a file
    - search: Search nodes by pattern
    - stats: Show graph statistics

    Examples:
        python -m pyragify.cli query-graph --graph-path output/graphs/repository_graph.json --command related --entity "src/pyragify/graph.py::GraphBuilder"
        python -m pyragify.cli query-graph --graph-path output/graphs/repository_graph.json --command hierarchy --entity "add_node"
        python -m pyragify.cli query-graph --graph-path output/graphs/repository_graph.json --command dependencies --entity "src/pyragify/graph.py"
        python -m pyragify.cli query-graph --graph-path output/graphs/repository_graph.json --command search --pattern "function"
    """

    # Load the knowledge graph
    if not graph_path:
        # Try to find the default graph
        default_graph = Path("output/graphs/repository_graph.json")
        if default_graph.exists():
            graph_path = default_graph
        else:
            typer.echo("Error: No graph path provided and default graph not found.", err=True)
            raise typer.Exit(1)

    if not graph_path.exists():
        typer.echo(f"Error: Graph file '{graph_path}' not found.", err=True)
        raise typer.Exit(1)

    try:
        from pyragify.graph import KnowledgeGraph, GraphQuery

        # Load graph
        graph = KnowledgeGraph.from_dict(load_json(graph_path, "graph"))
        query = GraphQuery(graph)

        # Execute command
        if command == "related":
            if not entity:
                typer.echo("Error: --entity required for 'related' command", err=True)
                raise typer.Exit(1)

            results = query.find_related_context(entity, depth)
            if output_format == "json":
                import json
                output = {
                    "entity": entity,
                    "results": [
                        {
                            "node": {
                                "id": chunk.node.id,
                                "type": chunk.node.type,
                                "name": chunk.node.name,
                                "file": chunk.node.file
                            },
                            "relevance_score": chunk.relevance_score,
                            "relationship_path": chunk.relationship_path
                        } for chunk in results
                    ]
                }
                typer.echo(json.dumps(output, indent=2))
            else:
                typer.echo(f"Related context for {entity}:")
                for chunk in results:
                    typer.echo(f"  {chunk.node.name} ({chunk.node.type}) - Score: {chunk.relevance_score:.2f}")

        elif command == "hierarchy":
            if not entity:
                typer.echo("Error: --entity required for 'hierarchy' command", err=True)
                raise typer.Exit(1)

            results = query.get_call_hierarchy(entity)
            if output_format == "json":
                import json
                typer.echo(json.dumps(results, indent=2))
            else:
                typer.echo(f"Call hierarchy for {entity}:")
                typer.echo(f"  Locations: {results['locations']}")
                typer.echo(f"  Callers: {[c['name'] for c in results['callers']]}")
                typer.echo(f"  Callees: {[c['name'] for c in results['callees']]}")

        elif command == "dependencies":
            if not entity:
                typer.echo("Error: --entity required for 'dependencies' command", err=True)
                raise typer.Exit(1)

            results = query.find_dependencies(entity)
            if output_format == "json":
                import json
                typer.echo(json.dumps({"file": entity, "dependencies": results}, indent=2))
            else:
                typer.echo(f"Dependencies for {entity}:")
                for dep in results:
                    typer.echo(f"  {dep}")

        elif command == "search":
            if not pattern:
                typer.echo("Error: --pattern required for 'search' command", err=True)
                raise typer.Exit(1)

            results = query.search_by_pattern(pattern)
            if output_format == "json":
                import json
                output = {
                    "pattern": pattern,
                    "results": [
                        {
                            "id": node.id,
                            "type": node.type,
                            "name": node.name,
                            "file": node.file
                        } for node in results
                    ]
                }
                typer.echo(json.dumps(output, indent=2))
            else:
                typer.echo(f"Search results for pattern '{pattern}':")
                for node in results:
                    typer.echo(f"  {node.name} ({node.type}) in {node.file}")

        elif command == "stats":
            # Use GraphBuilder to get statistics
            from pyragify.graph import GraphBuilder
            builder = GraphBuilder(Path("."))  # Dummy path, won't be used for stats
            builder.graph = graph
            stats = builder.get_statistics()

            if output_format == "json":
                import json
                typer.echo(json.dumps(stats, indent=2))
            else:
                typer.echo("Graph Statistics:")
                typer.echo(f"  Total nodes: {stats['total_nodes']}")
                typer.echo(f"  Total edges: {stats['total_edges']}")
                typer.echo(f"  Languages: {', '.join(stats['languages'])}")
                typer.echo("  Node types:")
                for node_type, count in stats['node_types'].items():
                    typer.echo(f"    {node_type}: {count}")
                typer.echo("  Edge types:")
                for edge_type, count in stats['edge_types'].items():
                    typer.echo(f"    {edge_type}: {count}")

        else:
            typer.echo(f"Error: Unknown command '{command}'", err=True)
            typer.echo("Available commands: related, hierarchy, dependencies, search, stats", err=True)
            raise typer.Exit(1)

    except typer.Exit:
        raise
    except Exception as e:
        logger.error(f"Error executing query: {e}")
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
