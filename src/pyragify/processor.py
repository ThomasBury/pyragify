import ast
import hashlib
import json
import re
import tokenize
import pathspec
import logging
from io import StringIO
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from os import cpu_count
from collections import defaultdict
from typing import Optional, Dict, Any, Tuple, List, Union
from pyragify.utils import validate_directory
from pyragify.graph import GraphBuilder, KnowledgeGraph

# Tree-sitter imports (conditionally imported)
# Note: Tree-sitter has version compatibility issues with current versions
# TODO: Fix tree-sitter version compatibility for proper JS/TS/Java/C++ parsing
try:
    from tree_sitter import Language, Node, Parser
    from tree_sitter_languages import get_language
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    # Define dummy types for type hinting if tree-sitter is not available
    class Language: pass
    class Node: pass


# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def save_json(data: dict, file_path: Path, description: str):
    """
    Save a dictionary to a JSON file with error handling.

    Parameters
    ----------
    data : dict
        The data to be saved as a JSON file.
    file_path : pathlib.Path
        The path where the JSON file should be saved.
    description : str
        A description of the file being saved, used in logging messages.

    Raises
    ------
    Exception
        If an error occurs during saving, it will be logged but not raised.

    Notes
    -----
    This function logs both successful saves and any errors encountered.
    """

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        logger.info(f"{description} saved to {file_path}")
    except Exception as e:
        logger.error(f"Error saving {description}: {e}")

def compute_file_hash(file_path: Path) -> str:
    """
    Compute the MD5 hash of a file.

    Parameters
    ----------
    file_path : pathlib.Path
        The path to the file whose hash is to be computed.

    Returns
    -------
    str or None
        The MD5 hash of the file as a hexadecimal string, or None if an error occurs.

    Raises
    ------
    Exception
        If the file cannot be read, the error is logged and None is returned.

    Notes
    -----
    MD5 is not suitable for cryptographic purposes but is sufficient for file integrity checks.
    """

    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
    except Exception as e:
        logger.error(f"Error computing hash for {file_path}: {e}")
        return None
    return hash_md5.hexdigest()

def load_json(file_path: Path, description: str) -> dict:
    """
    Load a JSON file into a dictionary with error handling.

    Parameters
    ----------
    file_path : pathlib.Path
        The path to the JSON file to be loaded.
    description : str
        A description of the file being loaded, used in logging messages.

    Returns
    -------
    dict
        The contents of the JSON file as a dictionary. Returns an empty dictionary if the file cannot be loaded.

    Raises
    ------
    Exception
        If an error occurs during file loading, it will be logged but not raised.
    """

    if file_path.exists():
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading {description}: {e}")
    return {}

def is_documentation_file(file_path: Path) -> bool:
    """
    Check if a file is a documentation file based on its name.

    Parameters
    ----------
    file_path : pathlib.Path
        The path to the file being checked.

    Returns
    -------
    bool
        True if the file is recognized as a documentation file, otherwise False.

    Notes
    -----
    This function specifically checks for common documentation filenames such as 'README.md' or 'CHANGELOG.md'.
    """

    documentation_files = ["README.md", "README.rst", "CONTRIBUTING.md", "CHANGELOG.md"]
    return file_path.name in documentation_files

FILE_TYPE_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".java": "java",
    ".cpp": "cpp",
    ".go": "go",
    ".c": "c",
    ".html": "html",
    ".css": "css",
    ".md": "markdown",
    ".markdown": "markdown"
}

DEFAULT_SKIP_PATTERNS = [
    ".git",
    "*.png",
    "*.jpg",
    "*.jpeg",
    "*.gif",
    "*.bmp",
    "*.webp",
    "*.ico",
    "*.svg",
]

MARKDOWN_HEADER_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
MARKDOWN_FENCE_RE = re.compile(r"^\s*(```|~~~)")


def is_probably_binary_file(file_path: Path, sample_size: int = 2048) -> bool:
    """Heuristically detect binary files so they can be skipped before decoding."""
    try:
        with open(file_path, "rb") as file:
            sample = file.read(sample_size)
    except OSError:
        return False

    if not sample:
        return False

    if b"\x00" in sample:
        return True

    try:
        sample.decode("utf-8")
    except UnicodeDecodeError:
        return True

    return False

def read_file_in_chunks(file_path: Path, chunk_size: int = 4096):
    """
    Read a file in chunks to handle large files efficiently.

    Parameters
    ----------
    file_path : pathlib.Path
        The path to the file to be read.
    chunk_size : int, optional
        The size of each chunk in bytes. Default is 4096.

    Yields
    ------
    str
        A chunk of the file as a string.

    Notes
    -----
    This function is useful for processing very large files without loading them entirely into memory.
    """

    with open(file_path, "r", encoding="utf-8") as file:
        while chunk := file.read(chunk_size):
            yield chunk

def _process_file_worker(task_args: tuple[str, str, str, bool, Optional[Dict[str, Any]]]) -> tuple[str, str, dict, list, Optional[Dict[str, Any]]] | None:
    """
    Worker function to process a single file in a separate process.

    This function is designed to be called by a ProcessPoolExecutor. It computes
    the file's hash, chunks its content using a FileProcessor, and returns
    all necessary metadata and content for aggregation.

    Parameters
    ----------
    task_args : tuple[str, str, str, bool, Optional[Dict[str, Any]]]
        A tuple containing (file_path, repo_path, output_dir, enable_graph, graph_config).

    Returns
    -------
    tuple[str, str, dict, list, Optional[Dict[str, Any]]] or None
        A tuple containing (relative_path, new_hash, file_metadata, chunks, graph_dict) on success,
        or None if an error occurs during processing.
    """
    file_path_str, repo_path_str, output_dir_str, enable_graph, graph_config = task_args
    file_path = Path(file_path_str)
    repo_path = Path(repo_path_str)
    output_dir = Path(output_dir_str)

    try:
        new_hash = compute_file_hash(file_path)
        if not new_hash:
            logger.warning(f"Worker failed to compute hash for {file_path}")
            return None

        # Each worker needs its own FileProcessor
        file_processor = FileProcessor(repo_path, output_dir, enable_graph=enable_graph, graph_config=graph_config)
        chunks, line_count, graph = file_processor.chunk_file(file_path, include_graph=True)

        if not chunks and line_count == 0:  # Indicates a read error in chunk_file
            logger.warning(f"Worker failed to chunk file {file_path}")
            return None

        relative_path = str(file_path.relative_to(repo_path))
        total_words = sum(len(file_processor.format_chunk(chunk, relative_path).split()) for chunk in chunks)
        file_metadata = {"path": relative_path, "chunks": len(chunks), "size": file_path.stat().st_size, "lines": line_count, "words": total_words}

        # Convert graph to dict for serialization (or None if no graph)
        graph_dict = graph.to_dict() if graph else None

        return (relative_path, new_hash, file_metadata, chunks, graph_dict)
    except Exception as e:
        logger.error(f"Unhandled exception in worker for file {file_path}: {e}")
        return None

class FileProcessor:
    """
    Class for handling file processing logic.

    This class provides methods for chunking files based on their type, including Python files, Markdown files, and others.

    Attributes
    ----------
    repo_path : pathlib.Path
        The path to the repository being processed.
    output_dir : pathlib.Path
        The directory where processed output will be saved.

    Methods
    -------
    chunk_python_file(file_path)
        Chunk a Python file into semantic sections.
    chunk_markdown_file(file_path)
        Chunk a Markdown file into sections based on headers.
    chunk_file(file_path)
        Chunk a file into semantic sections based on its type.
    """

    def __init__(self, repo_path: Path, output_dir: Path,
                 enable_graph: bool = False, graph_config: Optional[Dict[str, Any]] = None):
        self.repo_path = repo_path.resolve()
        self.output_dir = output_dir.resolve()
        validate_directory(self.output_dir)

        # Graph building configuration
        self.enable_graph = enable_graph
        self.graph_config = graph_config or {}
        self.graph_builder = None

        if self.enable_graph:
            self.graph_builder = GraphBuilder(self.repo_path)
            logger.info("Graph building enabled for FileProcessor")

    def format_chunk(self, chunk: dict, file_path: str) -> str:
        """
        Format a chunk into plain text for saving.

        Parameters
        ----------
        chunk : dict
            The chunk of content to format.
        file_path : str
            The relative path of the file the chunk belongs to.

        Returns
        -------
        str
            A formatted plain-text representation of the chunk.
        """
        chunk_type = chunk.get("type", "unknown")
        name = chunk.get("name")
        start_line = chunk.get("start_line")
        end_line = chunk.get("end_line")
        lines_str = f"{start_line}-{end_line}" if start_line and end_line else None

        # Helper to create a metadata header
        def create_header(display_type: str):
            parts = ["---", f"File: {file_path}", f"Type: {display_type}"]
            if name:
                parts.append(f"Name: {name}")
            if chunk_type == "markdown" and chunk.get("header"):
                parts.append(f"Header: {chunk['header']}")
            if lines_str:
                parts.append(f"Lines: {lines_str}")
            return "\n".join(parts) + "\n---\n\n"

        # Generic code chunk formatting
        if "code" in chunk:
            docstring = chunk.get("docstring")
            code = chunk.get("code", "")
            lang = FILE_TYPE_MAP.get(Path(file_path).suffix, chunk_type.split('_')[0])
            display_type = chunk_type.replace('_', ' ').title()

            header = create_header(display_type)
            title = f"### {display_type}: `{name}`\n\n"
            docstring_md = f"**Docstring:**\n> {docstring}\n\n" if docstring else ""
            code_md = f"**Code:**\n```{lang}\n{code.strip()}\n```"
            return f"{header}{title}{docstring_md}{code_md}"

        # Fallback for content-based chunks (like full files or markdown sections)
        elif "content" in chunk:
            content = chunk.get("content", "")
            suffix = Path(file_path).suffix
            lang = FILE_TYPE_MAP.get(suffix, "text")
            if chunk_type == "file":
                display_type = "File Content"
            elif chunk_type == "markdown":
                display_type = "Markdown Section"
            else:
                display_type = chunk_type.replace('_', ' ').title()
            header = create_header(display_type)
            title = f"### {chunk.get('name') or chunk.get('header') or display_type}\n\n"

            # Handle different content types
            if isinstance(content, list):
                # For comments or other list-based content
                if chunk_type == "comments":
                    content_md = "\n".join(f"- Line {c['line']}: {c['text']}" for c in content)
                else:
                    content_md = "\n".join(str(item) for item in content)
            else:
                # For string content
                content_md = f"```{lang}\n{content.strip()}\n```" if chunk_type == "file" else content.strip()

            return f"{header}{title}{content_md}"

        else:
            return f"---\nFile: {file_path}\nType: {chunk_type.title()}\n---\n\n{chunk}"

    def chunk_python_file(self, file_path: Path) -> tuple[list, int]:
        """
        Chunk a Python file into semantic sections, including code, functions, and comments.

        Parameters
        ----------
        file_path : pathlib.Path
            The path to the Python file to be chunked.

        Returns
        -------
        list of dict
            A list of dictionaries where each dictionary represents a chunk with metadata and content.

        Notes
        -----
        The chunks include functions, classes, and inline comments. Each chunk contains the following keys:
        - 'type': The type of the chunk (e.g., 'function', 'class', 'comments').
        - 'name': The name of the function or class (if applicable).
        - 'docstring': The docstring associated with the function or class.
        - 'code': The actual code of the function or class.
        - 'line_count': The number of lines in the file.
        """

        chunks = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                file_content = f.read()

            lines = file_content.splitlines()
            line_count = len(lines)

            # Extract functions and classes using AST
            tree = ast.parse(file_content, filename=file_path)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_name = node.name
                    code_snippet = ast.get_source_segment(file_content, node)
                    chunks.append({
                        "type": "function",
                        "name": func_name,
                        "docstring": ast.get_docstring(node),
                        "code": code_snippet,
                        "start_line": node.lineno,
                        "end_line": node.end_lineno,
                    })
                elif isinstance(node, ast.ClassDef):
                    if not hasattr(node, 'end_lineno'): continue # Skip nodes without end line info
                    class_name = node.name
                    code_snippet = ast.get_source_segment(file_content, node)
                    methods = []
                    for class_node in node.body:
                        if isinstance(class_node, ast.FunctionDef):
                            method_name = class_node.name
                            methods.append({
                                "name": method_name,
                            })
                    chunks.append({
                        "type": "class",
                        "name": class_name,
                        "methods": methods,
                        "docstring": ast.get_docstring(node),
                        "code": code_snippet,
                        "start_line": node.lineno,
                        "end_line": node.end_lineno,
                    })

            # Extract inline comments using tokenize
            tokens = tokenize.generate_tokens(StringIO(file_content).readline)
            comments = []
            for token in tokens:
                if token.type == tokenize.COMMENT:
                    line_number = token.start[0]
                    comment_text = token.string.lstrip("#").strip()
                    comments.append({
                        "type": "comment",
                        "line": line_number,
                        "text": comment_text
                    })
            if comments:
                chunks.append({"type": "comments", "name": "Comments", "content": comments})

        except Exception as e:
            logger.warning(f"Error chunking Python file {file_path}: {e}")
        return chunks, line_count if 'line_count' in locals() else 0

    def chunk_markdown_file(self, file_path: Path) -> tuple[list, int]:
        """
        Chunk a Markdown file into sections based on headers.

        Parameters
        ----------
        file_path : pathlib.Path
            The path to the Markdown file to be chunked.

        Returns
        -------
        list of dict
            A list of dictionaries where each dictionary represents a chunk with a header and its associated content.

        Notes
        -----
        Each chunk contains the following keys:
        - 'header': The header text (e.g., '# Title').
        - 'content': The content under the header.
        """

        chunks = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            line_count = len(lines)
    
            current_chunk = {"type": "markdown", "header": None, "name": file_path.stem, "content": ""}
            heading_stack: List[str] = []
            in_code_block = False

            for line_number, line in enumerate(lines, start=1):
                if MARKDOWN_FENCE_RE.match(line):
                    in_code_block = not in_code_block
                    current_chunk["content"] += line
                    continue

                header_match = MARKDOWN_HEADER_RE.match(line) if not in_code_block else None
                if header_match:
                    if current_chunk["header"] or current_chunk["content"].strip():
                        chunks.append(current_chunk)

                    level = len(header_match.group(1))
                    title = header_match.group(2).strip()
                    heading_stack = heading_stack[:level - 1]
                    heading_stack.append(title)

                    current_chunk = {
                        "type": "markdown",
                        "header": line.strip(),
                        "name": " > ".join(heading_stack),
                        "content": "",
                        "start_line": line_number,
                    }
                else:
                    current_chunk["content"] += line
            if current_chunk["header"] or current_chunk["content"].strip():
                chunks.append(current_chunk)
        except Exception as e:
            logger.warning(f"Error chunking Markdown file {file_path}: {e}")
        return chunks, line_count if 'line_count' in locals() else 0

    def chunk_file(
        self,
        file_path: Path,
        include_graph: bool = False,
    ) -> Union[Tuple[List[Dict[str, Any]], int], Tuple[List[Dict[str, Any]], int, Optional[KnowledgeGraph]]]:
        """
        Chunk a file into semantic sections based on its type.

        Parameters
        ----------
        file_path : pathlib.Path
            The path to the file to be chunked.

        Returns
        -------
        Tuple[List[Dict[str, Any]], int, Optional[KnowledgeGraph]]
            A tuple containing:
            - List of chunks (dict)
            - Total number of lines in the file (int)
            - Knowledge graph for the file (optional, only if graph building is enabled)

        Notes
        -----
        This method delegates to type-specific chunking methods based on the file extension.
        For unsupported types, the entire file content is treated as a single chunk.
        If graph building is enabled, a knowledge graph is also constructed.
        """
        suffix = file_path.suffix
        language = FILE_TYPE_MAP.get(suffix, "unknown")

        # Get chunks using existing logic
        if suffix == ".py":
            chunks, line_count = self.chunk_python_file(file_path)
        elif suffix in [".md", ".markdown"]:
            chunks, line_count = self.chunk_markdown_file(file_path)
        elif suffix in FILE_TYPE_MAP:
            chunks, line_count = self.chunk_tree_sitter_file(file_path, suffix)
        else:
            try:
                content = file_path.read_text(encoding="utf-8")
                line_count = content.count('\n') + 1
                chunks = [{
                    "type": "file",
                    "name": file_path.name,
                    "content": content
                }]
            except Exception as e:
                logger.warning(f"Error reading file {file_path}: {e}")
                chunks, line_count = [], 0

        # Build graph if enabled
        graph = None
        if self.enable_graph and self.graph_builder and chunks:
            try:
                graph = self.graph_builder.build_from_chunks(file_path, chunks, language)

                # Extract additional dependencies from file content
                try:
                    content = file_path.read_text(encoding="utf-8")
                    dependencies = self.graph_builder.extract_dependencies(file_path, content, language)
                    self.graph_builder.add_dependency_edges(graph, file_path, language, dependencies)
                except Exception as e:
                    logger.warning(f"Error extracting dependencies from {file_path}: {e}")

                logger.debug(f"Built knowledge graph for {file_path} with {len(graph.nodes)} nodes and {len(graph.edges)} edges")
            except Exception as e:
                logger.warning(f"Error building graph for {file_path}: {e}")

        if include_graph:
            return chunks, line_count, graph
        return chunks, line_count

    def _query_tree_sitter(self, language: Language, root_node: Node, source: str, query_str: str, chunk_type: str) -> list[dict[str, str]]:
        """
        Run a tree-sitter query and create code chunks from the matches.

        This helper function executes a given tree-sitter query against a parsed
        source code tree. For each match, it extracts the relevant code segment
        and an associated name (if available), then packages them into a
        dictionary representing a code chunk.

        Parameters
        ----------
        language : Language
            The tree-sitter language object used for the query.
        root_node : Node
            The root node of the parsed source code's abstract syntax tree.
        source : str
            The original source code as a string, used to extract code snippets.
        query_str : str
            The S-expression-based query string to run against the tree.
        chunk_type : str
            A string label to assign to the 'type' key of the created chunks.

        Returns
        -------
        list[dict[str, str]]
            A list of dictionaries, where each dictionary is a chunk containing
            'type', 'name', and 'code' keys. Returns an empty list if an
            error occurs or no matches are found.
        """
        chunks = []
        try:
            query = language.query(query_str)
            for match in query.matches(root_node):
                # A match is a list of (capture_index, node) tuples
                match_captures = {query.capture_names[c_id]: node for c_id, node in match}

                name_node = match_captures.get('name')
                name = name_node.text.decode('utf8') if name_node else "anonymous"

                main_node = None
                for key, node in match_captures.items():
                    if key != 'name':
                        main_node = node
                        break  # Found the main node
                if not main_node:
                    continue

                code = source[main_node.start_byte:main_node.end_byte]
                chunks.append({
                    "type": chunk_type, "name": name, "code": code,
                    "start_line": main_node.start_point[0] + 1, "end_line": main_node.end_point[0] + 1
                })
        except Exception as e:
            logger.warning(f"Error in tree-sitter query for {chunk_type}: {e}")
        return chunks

    def chunk_tree_sitter_file(self, file_path: Path, suffix: str) -> tuple[list, int]:
        """
        Chunk a file using tree-sitter for supported languages.

        Parameters
        ----------
        file_path : pathlib.Path
            The path to the file to be chunked.
        suffix : str
            The file suffix (extension) to determine the language.

        Returns
        -------
        list of dict
            A list of dictionaries, each representing a semantic chunk with keys like 'type', 'name', and 'code' or 'content'.

        Notes
        -----
        Supports semantic extraction for JavaScript/TypeScript (functions, classes, arrow functions), Java (methods, classes), C/C++ (functions, structs), HTML (scripts, styles), and CSS (rules). Falls back to full content if parsing fails.
        """
        try:
            source = file_path.read_text(encoding="utf-8")
            line_count = source.count('\n') + 1
            lang_name = FILE_TYPE_MAP[suffix]

            chunks = []

            # Try tree-sitter parsing first
            if TREE_SITTER_AVAILABLE:
                try:
                    language = get_language(lang_name)
                    parser = Parser()
                    parser.set_language(language)
                    tree = parser.parse(bytes(source, "utf8"))
                    root_node = tree.root_node

                    if lang_name in ["javascript", "typescript"]:
                        chunks.extend(self._query_tree_sitter(language, root_node, source,
                            "(function_declaration name: (identifier) @name) @function_declaration", "javascript_function"))
                        chunks.extend(self._query_tree_sitter(language, root_node, source,
                            "(class_declaration name: (identifier) @name) @class_declaration", "javascript_class"))
                        chunks.extend(self._query_tree_sitter(language, root_node, source,
                            "(arrow_function) @arrow_function", "javascript_arrow_function"))

                    elif lang_name == "java":
                        chunks.extend(self._query_tree_sitter(language, root_node, source,
                            "(method_declaration name: (identifier) @name) @method_declaration", "java_method"))
                        chunks.extend(self._query_tree_sitter(language, root_node, source,
                            "(class_declaration name: (identifier) @name) @class_declaration", "java_class"))

                    elif lang_name in ["cpp", "c"]:
                        chunks.extend(self._query_tree_sitter(language, root_node, source, '''
                        (function_definition
                          declarator: (function_declarator
                            declarator: (identifier) @name
                          )
                        ) @function_definition
                        ''', "cpp_function"))

                        # Struct/Class for C++
                        if lang_name == "cpp":
                            chunks.extend(self._query_tree_sitter(language, root_node, source, '''
                                (struct_specifier name: (type_identifier) @name) @struct_specifier
                            ''', "cpp_struct"))
                            chunks.extend(self._query_tree_sitter(language, root_node, source, '''
                                (class_specifier name: (type_identifier) @name) @class_specifier
                            ''', "cpp_class"))
                    
                    elif lang_name == "go":
                        chunks.extend(self._query_tree_sitter(language, root_node, source, '''
                            (function_declaration
                              name: (identifier) @name
                            ) @function_declaration
                        ''', "go_function"))
                        chunks.extend(self._query_tree_sitter(language, root_node, source, '''
                            (type_declaration
                              (type_spec name: (type_identifier) @name)
                            ) @type
                        ''', "go_type"))

                except Exception as e:
                    logger.warning(f"Tree-sitter parsing failed for {lang_name}: {e}")

            # Fallback to regex for HTML/CSS or if tree-sitter failed
            if not chunks:
                if lang_name == "html":
                    # Simple regex fallback for tags
                    import re
                    scripts = re.findall(r'<script[^>]*>(.*?)</script>', source, re.DOTALL | re.IGNORECASE)
                    for script in scripts:
                        chunks.append({"type": "html_script", "content": script.strip()})
                    styles = re.findall(r'<style[^>]*>(.*?)</style>', source, re.DOTALL | re.IGNORECASE)
                    for style in styles:
                        chunks.append({"type": "html_style", "content": style.strip()})
                    if not chunks:
                        chunks = [{"type": "html", "content": source}]

                # CSS: Chunk by rules
                elif lang_name == "css":
                    import re
                    rules = re.split(r'([@][^{]+{[^}]*}|{[^{}]*})', source)
                    for rule in rules:
                        if rule.strip() and '{' in rule:
                            chunks.append({"type": "css_rule", "content": rule.strip()})
                    if not chunks:
                        chunks = [{"type": "css", "content": source}]

                else:
                    # For other languages, fall back to full file content
                    chunks = [{"type": "file", "name": file_path.name, "content": source}]

            return chunks, line_count
        except Exception as e:
            logger.warning(f"Error chunking {suffix} file {file_path}: {e}")
            content = file_path.read_text(encoding="utf-8")
            return [{"type": "file", "name": file_path.name, "content": content}], content.count('\n') + 1

class RepoContentProcessor:
    """
    Class for processing an entire repository.

    This class orchestrates file-level processing, manages metadata, and saves the results to disk.

    Attributes
    ----------
    repo_path : pathlib.Path
        The path to the repository being processed.
    output_dir : pathlib.Path
        The directory where processed output will be saved.
    max_words : int
        The maximum number of words allowed per output chunk.
    max_file_size : int
        The maximum file size (in bytes) for processing.
    skip_patterns : list of str
        Patterns for files to skip.
    skip_dirs : list of str
        Directory names to skip.
    ignore_patterns : pathspec.PathSpec
        Compiled patterns for ignoring files.
    current_word_count : int
        The current word count for the current chunk.
    content : str
        The current content being accumulated for a chunk.
    hashes : dict
        Cached file hashes to avoid reprocessing unchanged files.
    file_counter : collections.defaultdict
        Counter for output files by type.
    metadata : dict
        Metadata about processed and skipped files.

    Methods
    -------
    load_ignore_patterns()
        Load ignore patterns from .gitignore and .dockerignore files.
    should_skip(file_path)
        Determine if a file or directory should be skipped.
    save_chunk(chunk, subdir)
        Save a chunk of content to a file.
    save_content(subdir)
        Save the accumulated content to a file.
    process_file(file_path)
        Process a single file, chunking and saving its content.
    process_repo()
        Process all files in the repository.
    get_file_type_subdir(file_path)
        Determine the output subdirectory for a file based on its type.
    """

    def __init__(self, repo_path: Path, output_dir: Path, max_words: int = 200000, max_file_size: int = 10 * 1024 * 1024, skip_patterns: list = None, skip_dirs: list = None, enable_graph: bool = False, graph_config: Optional[Dict[str, Any]] = None):
        self.repo_path = repo_path.resolve()
        self.output_dir = output_dir.resolve()
        self.max_words = max_words
        self.max_file_size = max_file_size
        self.skip_patterns = list(dict.fromkeys(DEFAULT_SKIP_PATTERNS + (skip_patterns or [])))
        self.skip_dirs = skip_dirs or ["node_modules", "__pycache__"]
        self.ignore_patterns = self.load_ignore_patterns()
        self.current_word_counts = defaultdict(int)
        self.content_buffers = defaultdict(str)
        self.hashes = load_json(self.output_dir / "hashes.json", "hashes")
        self.file_counter = defaultdict(int)
        self.metadata = {
            "processed_files": [],
            "skipped_files": [],
            "summary": {"total_files_processed": 0, "total_words": 0}
        }

        # Graph-related attributes
        self.enable_graph = enable_graph
        self.graph_config = graph_config or {}
        self.repo_graph = None
        self.all_file_graphs = []  # Store all individual file graphs

        if self.enable_graph:
            from pyragify.graph import KnowledgeGraph
            self.repo_graph = KnowledgeGraph()
            logger.info("Repository graph building enabled")

        self.file_processor = FileProcessor(self.repo_path, self.output_dir, enable_graph=enable_graph, graph_config=graph_config)

        validate_directory(self.output_dir)

    def load_ignore_patterns(self) -> pathspec.PathSpec:
        """
        Load patterns from .gitignore and .dockerignore files if they exist.

        Returns
        -------
        pathspec.PathSpec
            A compiled PathSpec object containing all ignore patterns.

        Notes
        -----
        Additional patterns provided via `skip_patterns` are also included. 
        If the ignore files are missing, only the additional patterns are used.
        """

        ignore_patterns = []

        for ignore_file in [".gitignore", ".dockerignore"]:
            file_path = self.repo_path / ignore_file
            if file_path.exists():
                logger.info(f"Loading ignore patterns from {ignore_file}")
                with open(file_path, "r", encoding="utf-8") as f:
                    ignore_patterns.extend(f.readlines())

        # Add additional skip_patterns
        ignore_patterns.extend(self.skip_patterns)

        # Compile patterns using pathspec
        return pathspec.PathSpec.from_lines("gitwildmatch", ignore_patterns)

    def should_skip(self, file_path: Path) -> bool:
        """
        Determine if a file or directory should be skipped based on patterns.

        Parameters
        ----------
        file_path : pathlib.Path
            The path to the file or directory to check.

        Returns
        -------
        bool
            True if the file or directory should be skipped, otherwise False.

        Notes
        -----
        This method checks against ignore patterns and explicit directory or file size limits.
        """

        relative_path = file_path.relative_to(self.repo_path)

        # Skip files contained in explicitly skipped directories.
        if any(part in self.skip_dirs for part in relative_path.parts[:-1]):
            logger.debug(f"Skipped path inside configured skip directory: {file_path}")
            return True

        # Check if the path matches .gitignore or .dockerignore patterns
        if self.ignore_patterns.match_file(str(relative_path)):
            logger.debug(f"Skipping {relative_path} due to ignore pattern.")
            return True

        # Skip directories explicitly listed
        if file_path.is_dir() and file_path.name in self.skip_dirs:
            logger.debug(f"Skipped directory: {file_path}")
            return True

        # Skip large files
        if file_path.is_file() and file_path.stat().st_size > self.max_file_size:
            self.metadata["skipped_files"].append({
                "path": str(file_path.relative_to(self.repo_path)),
                "reason": "File exceeds size limit"
            })
            logger.debug(f"Skipped file due to size: {file_path}")
            return True

        if file_path.is_file() and is_probably_binary_file(file_path):
            self.metadata["skipped_files"].append({
                "path": str(file_path.relative_to(self.repo_path)),
                "reason": "Binary or image file"
            })
            logger.debug(f"Skipped binary/image file: {file_path}")
            return True

        return False

    def save_chunk(self, chunk: dict, subdir: Path, file_path: str):
        """
        Save a chunk of content to a text file.

        Parameters
        ----------
        chunk : dict
            The chunk of content to save.
        subdir : pathlib.Path
            The subdirectory where the chunk should be saved.
        file_path : str
            The relative path of the file the chunk belongs to.
        """
        formatted = self.file_processor.format_chunk(chunk, file_path)
        chunk_word_count = len(formatted.split())
        if self.current_word_counts[subdir] + chunk_word_count > self.max_words:
            self.save_content(subdir)
        self.content_buffers[subdir] += formatted + "\n\n"
        self.current_word_counts[subdir] += chunk_word_count


    def save_content(self, subdir: Path):
        """
        Save the accumulated content to a file.

        This method writes the currently accumulated content to a file in the specified subdirectory.
        After saving, the content and word count are reset for the next chunk.

        Parameters
        ----------
        subdir : pathlib.Path
            The subdirectory within the output directory where the chunk file should be saved.

        Notes
        -----
        - The file is named `chunk_<counter>.json`, where `<counter>` is an incrementing number for the subdirectory.
        - If the subdirectory does not exist, it is created automatically.
        - Once the content is saved, the internal buffer (`self.content`) and the current word count (`self.current_word_count`) are reset to prepare for the next chunk.

        Examples
        --------
        To save the current content to a subdirectory:
            >>> processor = RepoContentProcessor(repo_path=Path("repo"), output_dir=Path("output"))
            >>> processor.content = "This is some chunked content."
            >>> processor.current_word_count = 5
            >>> processor.save_content(Path("python"))

        Raises
        ------
        OSError
            If the file cannot be created or written, an error is logged.
        """

        if self.content_buffers[subdir]:
            file_path = self.output_dir / subdir / f"chunk_{self.file_counter[subdir]}.txt"
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(self.content_buffers[subdir])
            logger.info(f"Saved chunk to {file_path}")
            self.file_counter[subdir] += 1
            self.content_buffers[subdir] = ""
            self.current_word_counts[subdir] = 0
            
    def process_repo(self):
        """
        Process all files in the repository in parallel.

        This method iterates over all files, filters out skipped and unchanged files,
        and then processes the remaining files in parallel using a process pool.
        Results are aggregated and saved to the output directory.
        """
        logger.info(f"Processing repository: {self.repo_path}")

        # 1. Discover and filter files to process
        logger.info("Discovering and filtering files...")
        files_to_process = []
        for file_path in self.repo_path.rglob("*"):
            if not file_path.is_file():
                continue
            if self.should_skip(file_path):
                relative_path = str(file_path.relative_to(self.repo_path))
                if not any(entry["path"] == relative_path for entry in self.metadata["skipped_files"]):
                    self.metadata["skipped_files"].append({"path": relative_path, "reason": "Skipped by pattern or size"})
                continue

            current_hash = compute_file_hash(file_path)
            if not current_hash:
                self.metadata["skipped_files"].append({"path": str(file_path), "reason": "Error computing file hash"})
                logger.warning(f"Skipped file due to hash error: {file_path}")
                continue

            relative_path = str(file_path.relative_to(self.repo_path))
            if relative_path in self.hashes and self.hashes[relative_path] == current_hash:
                self.metadata["skipped_files"].append({"path": relative_path, "reason": "Unchanged file (hash match)"})
                logger.debug(f"Skipped unchanged file: {file_path}")
                continue
            
            files_to_process.append(file_path)

        if not files_to_process:
            logger.info("No new or modified files to process.")
        else:
            logger.info(f"Found {len(files_to_process)} new or modified files to process.")
            # 2. Process files in parallel
            tasks = [(str(fp), str(self.repo_path), str(self.output_dir), self.enable_graph, self.graph_config) for fp in files_to_process]
            with ProcessPoolExecutor(max_workers=cpu_count()) as executor:
                results = executor.map(_process_file_worker, tasks)
                for i, result in enumerate(results):
                    if result is None:
                        logger.warning(f"A worker failed to process a file.")
                        continue

                    relative_path, new_hash, file_metadata, chunks, graph_dict = result
                    logger.info(f"Aggregating results for {relative_path} ({i + 1}/{len(files_to_process)})")

                    # 3. Aggregate results serially
                    self.hashes[relative_path] = new_hash
                    self.metadata["processed_files"].append(file_metadata)
                    self.metadata["summary"]["total_files_processed"] += 1
                    self.metadata["summary"]["total_words"] += file_metadata['words']

                    # Merge graph if available
                    if self.enable_graph and graph_dict and self.repo_graph:
                        try:
                            from pyragify.graph import KnowledgeGraph
                            file_graph = KnowledgeGraph.from_dict(graph_dict)
                            self.all_file_graphs.append(file_graph)
                            self.repo_graph.merge(file_graph)
                            logger.debug(f"Merged graph for {relative_path} into repository graph")
                        except Exception as e:
                            logger.warning(f"Failed to merge graph for {relative_path}: {e}")

                    subdir = self.get_file_type_subdir(Path(self.repo_path, relative_path))
                    for chunk in chunks:
                        self.save_chunk(chunk, subdir, relative_path)

        # 4. Resolve cross-file references
        if self.enable_graph and self.repo_graph and self.all_file_graphs:
            try:
                from pyragify.graph import GraphBuilder
                graph_builder = GraphBuilder(self.repo_path)
                graph_builder.graph = self.repo_graph
                graph_builder.resolve_cross_file_references(self.all_file_graphs)
                logger.info("Cross-file reference resolution completed")

                # Validate and repair the graph
                validation_results = graph_builder.validate_graph()
                if not validation_results["is_valid"] or validation_results["warnings"]:
                    logger.info("Graph validation found issues, attempting repair...")
                    graph_builder.repair_graph(validation_results)

                    # Re-validate after repair
                    final_validation = graph_builder.validate_graph()
                    if final_validation["is_valid"]:
                        logger.info("Graph repair successful")
                    else:
                        logger.warning("Some graph issues could not be repaired")

            except Exception as e:
                logger.warning(f"Failed to resolve cross-file references: {e}")

        # 5. Save final state
        for subdir in list(self.content_buffers.keys()):
            self.save_content(subdir)

        # Save repository graph if enabled
        if self.enable_graph and self.repo_graph:
            try:
                graph_output_dir = Path(self.graph_config.get("output_dir", "./graphs"))
                graph_output_dir = self.output_dir / graph_output_dir
                graph_output_dir.mkdir(parents=True, exist_ok=True)

                graph_path = graph_output_dir / "repository_graph.json"
                graph_dict = self.repo_graph.to_dict()
                with open(graph_path, 'w', encoding='utf-8') as f:
                    json.dump(graph_dict, f, indent=2, ensure_ascii=False)

                # Update metadata with graph statistics
                self.metadata["graph"] = graph_dict["metadata"].copy()
                self.metadata["graph"]["output_path"] = str(graph_path)

                logger.info(f"Saved repository knowledge graph to {graph_path}")
                logger.info(f"Graph contains {len(self.repo_graph.nodes)} nodes and {len(self.repo_graph.edges)} edges")
            except Exception as e:
                logger.error(f"Failed to save repository graph: {e}")

        save_json(self.metadata, self.output_dir / "metadata.json", "Metadata")
        save_json(self.hashes, self.output_dir / "hashes.json", "Hashes")

        logger.info("Repository processing complete.")

    def get_file_type_subdir(self, file_path: Path) -> str:
        """
        Determine the subdirectory for a file based on its type.

        This method maps a file's extension to a predefined subdirectory name using the `FILE_TYPE_MAP` dictionary.
        If the file extension is not recognized, it defaults to "other".

        Parameters
        ----------
        file_path : pathlib.Path
            The path to the file whose subdirectory is being determined.

        Returns
        -------
        str
            The name of the subdirectory where the file should be categorized.
            For example, "python" for `.py` files, "markdown" for `.md` files, and "other" for unrecognized file types.

        Notes
        -----
        - The `FILE_TYPE_MAP` dictionary defines the mappings between file extensions and subdirectory names.
        - This method ensures that files are categorized consistently based on their type.

        Examples
        --------
        To get the subdirectory for a file:
            >>> processor = RepoContentProcessor(repo_path=Path("repo"), output_dir=Path("output"))
            >>> processor.get_file_type_subdir(Path("example.py"))
            'python'

            >>> processor.get_file_type_subdir(Path("README.md"))
            'markdown'

            >>> processor.get_file_type_subdir(Path("unknown.xyz"))
            'other'
        """

        return FILE_TYPE_MAP.get(file_path.suffix, "other")
