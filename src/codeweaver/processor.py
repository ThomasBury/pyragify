import ast
import hashlib
import json
import tokenize
import pathspec
import logging
from io import StringIO
from pathlib import Path
from collections import defaultdict
from codeweaver.utils import validate_directory

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
    ".md": "markdown",
    ".markdown": "markdown"
}

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

    def __init__(self, repo_path: Path, output_dir: Path):
        self.repo_path = repo_path.resolve()
        self.output_dir = output_dir.resolve()
        validate_directory(self.output_dir)

    def chunk_python_file(self, file_path: Path) -> list:
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
        """

        chunks = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                file_content = f.read()

            # Extract functions and classes using AST
            tree = ast.parse(file_content)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_name = node.name
                    start_line, end_line = node.lineno, node.end_lineno
                    code_snippet = "\n".join(file_content.splitlines()[start_line - 1:end_line])
                    chunks.append({
                        "type": "function",
                        "name": func_name,
                        "code": code_snippet
                    })
                elif isinstance(node, ast.ClassDef):
                    class_name = node.name
                    start_line, end_line = node.lineno, node.end_lineno
                    code_snippet = "\n".join(file_content.splitlines()[start_line - 1:end_line])
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
                        "code": code_snippet
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
                chunks.append({"type": "comments", "content": comments})

        except Exception as e:
            logger.warning(f"Error chunking Python file {file_path}: {e}")
        return chunks

    def chunk_markdown_file(self, file_path: Path) -> list:
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
    
            current_chunk = {"header": None, "content": ""}
            for line in lines:
                if line.startswith("#"):  # Header
                    if current_chunk["header"] or current_chunk["content"]:
                        chunks.append(current_chunk)
                    current_chunk = {"header": line.strip(), "content": ""}
                else:
                    current_chunk["content"] += line
            if current_chunk["header"] or current_chunk["content"]:
                chunks.append(current_chunk)
        except Exception as e:
            logger.warning(f"Error chunking Markdown file {file_path}: {e}")
        return chunks

    def chunk_file(self, file_path: Path) -> list:
        """
        Chunk a file into semantic sections based on its type.

        Parameters
        ----------
        file_path : pathlib.Path
            The path to the file to be chunked.

        Returns
        -------
        list of dict
            A list of chunks, where each chunk is a dictionary with metadata and content.

        Notes
        -----
        This method delegates to type-specific chunking methods based on the file extension. 
        For unsupported types, the entire file content is treated as a single chunk.
        """

        if file_path.suffix == ".py":
            return self.chunk_python_file(file_path)
        elif file_path.suffix in [".md", ".markdown"]:
            return self.chunk_markdown_file(file_path)
        else:
            try:
                return [{
                    "type": "file",
                    "name": file_path.name,
                    "content": file_path.read_text(encoding="utf-8")
                }]
            except Exception as e:
                logger.warning(f"Error reading file {file_path}: {e}")
                return []

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

    def __init__(self, repo_path: Path, output_dir: Path, max_words: int = 200000, max_file_size: int = 10 * 1024 * 1024, skip_patterns: list = None, skip_dirs: list = None):
        self.repo_path = repo_path.resolve()
        self.output_dir = output_dir.resolve()
        self.max_words = max_words
        self.max_file_size = max_file_size
        self.skip_patterns = skip_patterns or [".git"]
        self.skip_dirs = skip_dirs or ["node_modules", "__pycache__"]
        self.ignore_patterns = self.load_ignore_patterns()
        self.current_word_count = 0
        self.content = ""
        self.hashes = load_json(self.output_dir / "hashes.json", "hashes")
        self.file_counter = defaultdict(int)
        self.metadata = {
            "processed_files": [],
            "skipped_files": [],
            "summary": {"total_files_processed": 0, "total_words": 0}
        }
        self.file_processor = FileProcessor(self.repo_path, self.output_dir)

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

        # Check if the path matches .gitignore or .dockerignore patterns
        relative_path = file_path.relative_to(self.repo_path)
        if self.ignore_patterns.match_file(str(relative_path)):
            logger.info(f"Skipping {relative_path} due to ignore pattern.")
            return True

        # Skip directories explicitly listed
        if file_path.is_dir() and file_path.name in self.skip_dirs:
            logger.info(f"Skipped directory: {file_path}")
            return True

        # Skip large files
        if file_path.is_file() and file_path.stat().st_size > self.max_file_size:
            self.metadata["skipped_files"].append({
                "path": str(file_path),
                "reason": "File exceeds size limit"
            })
            logger.info(f"Skipped file due to size: {file_path}")
            return True

        return False

    def save_chunk(self, chunk: dict, subdir: Path):
        """
        Save a chunk of content to a text file.

        Parameters
        ----------
        chunk : dict
            The chunk of content to save.
        subdir : pathlib.Path
            The subdirectory where the chunk should be saved.
        """
        chunk_content = chunk.get("content", "")
        chunk_word_count = len(chunk_content.split())
        if self.current_word_count + chunk_word_count > self.max_words:
            self.save_content(subdir)
        self.content += self.format_chunk(chunk) + "\n\n"
        self.current_word_count += chunk_word_count


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

        if self.content:
            file_path = self.output_dir / subdir / f"chunk_{self.file_counter[subdir]}.txt"
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(self.content)
            logger.info(f"Saved chunk to {file_path}")
            self.file_counter[subdir] += 1
            self.content = ""
            self.current_word_count = 0
            
    def format_chunk(self, chunk: dict) -> str:
        """
        Format a chunk into plain text for saving.
    
        Parameters
        ----------
        chunk : dict
            The chunk of content to format.
    
        Returns
        -------
        str
            A formatted plain-text representation of the chunk.
        """
        chunk_type = chunk.get("type", "unknown")
        if chunk_type == "function":
            return f"Function: {chunk.get('name')}\nCode:\n{chunk.get('code')}"
        elif chunk_type == "class":
            return f"Class: {chunk.get('name')}\nCode:\n{chunk.get('code')}"
        elif chunk_type == "comments":
            comments = "\n".join(f"Line {c['line']}: {c['text']}" for c in chunk.get("content", []))
            return f"Comments:\n{comments}"
        elif chunk_type == "file":
            return f"File: {chunk.get('name')}\nContent:\n{chunk.get('content', '')}"
        else:
            return f"Unknown chunk type:\n{chunk}"



    def process_file(self, file_path: Path):
        """
        Process a single file.

        This method handles the processing of a single file by checking its hash for changes, chunking its content, and saving the resulting chunks.
        Metadata about the processed file is updated, and any errors are logged.

        Parameters
        ----------
        file_path : pathlib.Path
            The path to the file to be processed.

        Notes
        -----
        - Files that have unchanged hashes (compared to the cached hashes) are skipped.
        - Skipped files are logged in the `metadata['skipped_files']` list with reasons for skipping.
        - Processed files are chunked based on their type, and each chunk is saved to the appropriate subdirectory.
        - Metadata about processed files, such as the number of chunks, file size, number of lines, and total words, is recorded.

        Raises
        ------
        Exception
            Any errors encountered during file processing are logged and added to the skipped files list, but do not halt execution.

        Examples
        --------
        To process a file:
            >>> processor = RepoContentProcessor(repo_path=Path("repo"), output_dir=Path("output"))
            >>> processor.process_file(Path("repo/example.py"))
        """

        try:
            current_hash = compute_file_hash(file_path)
            if not current_hash:
                self.metadata["skipped_files"].append({"path": str(file_path), "reason": "Error computing file hash"})
                logger.warning(f"Skipped file due to hash error: {file_path}")
                return

            relative_path = str(file_path.relative_to(self.repo_path))
            if relative_path in self.hashes and self.hashes[relative_path] == current_hash:
                self.metadata["skipped_files"].append({"path": relative_path, "reason": "Unchanged file (hash match)"})
                logger.info(f"Skipped unchanged file: {file_path}")
                return

            subdir = self.get_file_type_subdir(file_path)
            chunks = self.file_processor.chunk_file(file_path)
            for chunk in chunks:
                self.save_chunk(chunk, subdir)

            self.metadata["processed_files"].append({
                "path": relative_path,
                "chunks": len(chunks),
                "size": file_path.stat().st_size,
                "lines": sum(1 for _ in open(file_path, encoding="utf-8")),
                "words": sum(len(chunk["content"].split()) for chunk in chunks if "content" in chunk)
            })
            self.metadata["summary"]["total_files_processed"] += 1
            self.metadata["summary"]["total_words"] += sum(len(chunk["content"].split()) for chunk in chunks if "content" in chunk)
            self.hashes[relative_path] = current_hash
        except Exception as e:
            logger.warning(f"Error processing file {file_path}: {e}")
            self.metadata["skipped_files"].append({"path": str(file_path), "reason": f"Error processing file: {e}"})

    def process_repo(self):
        """
        Process all files in the repository.

        This method iterates over all files in the specified repository directory. It skips files and directories 
        based on ignore patterns and file size limits, processes supported file types, and saves the results. 
        Metadata about processed and skipped files is recorded, and the final results are saved to the output directory.

        Notes
        -----
        - Files are processed based on their type (e.g., Python files, Markdown files).
        - Skipped files and directories are logged in the `metadata['skipped_files']`.
        - Processed files are chunked, and their metadata is updated in `metadata['processed_files']`.
        - All metadata and hash information is saved to the output directory at the end of processing.

        Parameters
        ----------
        None

        Raises
        ------
        Exception
            Errors during individual file processing are logged and added to the skipped files list, but do not halt execution.

        Examples
        --------
        To process a repository:
            >>> processor = RepoContentProcessor(repo_path=Path("repo"), output_dir=Path("output"))
            >>> processor.process_repo()

        Metadata Example:
            After processing, metadata is saved as JSON:
            {
                "processed_files": [
                    {
                        "path": "example.py",
                        "chunks": 3,
                        "size": 2048,
                        "lines": 50,
                        "words": 300
                    }
                ],
                "skipped_files": [
                    {
                        "path": ".git/config",
                        "reason": "Matches ignore pattern"
                    }
                ],
                "summary": {
                    "total_files_processed": 10,
                    "total_words": 5000
                }
            }
        """

        logger.info(f"Processing repository: {self.repo_path}")
        total_files = sum(1 for _ in self.repo_path.rglob("*"))
        file_count = 0

        for file_path in self.repo_path.rglob("*"):
            file_count += 1
            logger.info(f"Processing file {file_count}/{total_files}: {file_path}")
            if self.should_skip(file_path):
                continue

            if is_documentation_file(file_path):
                chunks = self.file_processor.chunk_markdown_file(file_path)
                for chunk in chunks:
                    self.save_chunk(chunk, Path("markdown"))
            elif file_path.suffix == ".py":
                self.process_file(file_path)
            elif file_path.is_file():
                self.process_file(file_path)

        save_json(self.metadata, self.output_dir / "metadata.json", "Metadata")
        save_json(self.hashes, self.output_dir / "hashes.json", "Hashes")

        if self.content:
            self.save_content(Path("remaining"))

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
