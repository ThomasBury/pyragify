# pyragify

**pyragify** is a Python-based tool designed to process python code repositories and extract their content into semantic chunks for analysis. It supports Python files, Markdown files, and other common file types. The extracted content is saved in plain text format for compatibility with tools like `NotebookLM`.

---

## Features

- **Semantic Chunking**: Extracts functions, classes, and inline comments from Python files, as well as headers and sections from Markdown files.
- **Supported Formats**: Outputs `.txt` files for compatibility with NotebookLM.
- **Flexible Configuration**: Configure processing options via a YAML file or command-line arguments.
- **File Skipping**: Respects `.gitignore` and `.dockerignore` patterns and allows custom skip patterns.
- **Word Limit**: Automatically chunks output files based on a configurable word limit.

---

## Installation

If you are using `uv`

```bash
uv pip install pyragify
```

To install pyragify, use `pip`:

```bash
pip install pyragify
```

---

## Usage

### Best Practice: Run with `uv`

Using `uv` ensures consistent dependency management and reproducibility. First, make sure you have `uv` installed:

```bash
pip install uv
```

Then, run pyragify using `uv`:

```bash
uv run python -m pyragify --config-file config.yaml
```

This ensures your environment is properly isolated and consistent.

---

### Chat With Your Code-Base

Head over []() and input the text file you will find under `[...]/output/remaining/chunk_0.txt` and drop it in a new notebook.

You can now ask questions, with precise citations. You can even generate a podcast.

![code_chat](chat_code_base.png "Chat with your code base")


### Command-Line Interface (CLI)

If you prefer to run pyragify directly without `uv`, use the following command:

```bash
python -m pyragify.cli process-repo
```

### Arguments and Options

- **`--config-file`** (default: `config.yaml`): Path to the YAML configuration file.
- **`--repo-path`**: Override the path to the repository to process.
- **`--output-dir`**: Override the directory where output files will be saved.
- **`--max-words`**: Override the maximum number of words per output file.
- **`--max-file-size`**: Override the maximum size (in bytes) of files to process.
- **`--skip-patterns`**: Override the list of file patterns to skip.
- **`--skip-dirs`**: Override the list of directories to skip.
- **`--verbose`**: Enable verbose logging for debugging purposes.

---

## Configuration

The tool can be configured using a YAML file (default: `config.yaml`). Here is an example configuration:

```yaml
repo_path: /path/to/repository
output_dir: /path/to/output
max_words: 200000
max_file_size: 10485760  # 10 MB
skip_patterns:
  - "*.log"
  - "*.tmp"
skip_dirs:
  - "__pycache__"
  - "node_modules"
verbose: false
```

Command-line arguments override the settings in the YAML file.

---

## Example Workflow

### 1. Prepare Your Repository

Ensure your repository contains the code you want to process. Add any files or directories you want to exclude to `.gitignore` or `.dockerignore`.

### 2. Configure pyragify

Create a `config.yaml` file with your desired settings or use the default settings.

### 3. Process the Repository

Run the following command with `uv` for the best practice:

```bash
uv run python -m pyragify --config-file config.yaml
```

Alternatively, use the CLI directly:

```bash
python -m pyragify.cli process-repo --repo-path /path/to/repository --output-dir /path/to/output
```

### 4. Check the Output

The processed content will be saved in the specified output directory, organized into subdirectories like `python` and `markdown`.

---

## Examples

### Process a Repository with Default Settings

```bash
uv run python -m pyragify --config-file config.yaml
```

### Process a Specific Repository with Custom Settings

```bash
uv run python -m pyragify.cli process-repo \
  --repo-path /my/repo \
  --output-dir /my/output \
  --max-words 100000 \
  --max-file-size 5242880 \
  --skip-patterns "*.log,*.tmp" \
  --skip-dirs "__pycache__,node_modules" \
  --verbose
```

---

## File Outputs

The processed content is saved in `.txt` format and categorized into subdirectories based on file type:

- **`python/`**: Contains chunks of Python functions and classes with their code.
- **`markdown/`**: Contains sections of Markdown files, split by headers.
- **`other/`**: Contains plain text versions of unsupported file types.

---

## Advanced Features

### Respecting `.gitignore` and `.dockerignore`

pyragify automatically skips files and directories listed in `.gitignore` and `.dockerignore` if they are present in the repository.

### Incremental Processing

pyragify uses MD5 hashes to skip unchanged files during subsequent runs.

---

## Development

To contribute to pyragify:

1. Clone the repository:
   ```bash
   git clone https://github.com/your-repo/pyragify.git
   cd pyragify
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run tests:
TODO: write test suite 😅
   ```bash
   pytest
   ```

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## Support

For issues or feature requests, please create a GitHub issue in the repository or contact the maintainers.
