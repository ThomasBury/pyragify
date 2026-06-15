# Pyragify

**Pyragify takes a code repository and converts it into readable text files you can upload to [NotebookLM](https://notebooklm.google.com/) or other AI tools — so you can ask questions about a codebase in plain English.**

It works by breaking source code files into meaningful pieces (functions, classes, sections) rather than dumping everything into one giant file. This makes it much easier for AI tools to understand and reference your code accurately.

---

## What Problem Does This Solve?

AI tools like NotebookLM work best with well-organized text documents. Code repositories, however, are a mix of many file types, deeply nested folders, and technical structure that AI tools struggle to parse on their own.

Pyragify bridges that gap: point it at a folder of code, and it produces clean `.txt` files organized by file type, ready to upload.

---

## What It Does

- Breaks Python files into individual functions, classes, and comments
- Splits Markdown files by their headings
- Extracts scripts and styles from HTML files
- Handles CSS, and includes other readable files as plain text
- Skips files listed in your `.gitignore` automatically
- Remembers which files it already processed, so re-runs are fast

---

## Requirements

Before you start, you need **Python** installed on your computer (version 3.9 to 3.12).

To check if you have Python, open your terminal (on Mac: `Terminal`; on Windows: `Command Prompt` or `PowerShell`) and type:

```bash
python --version
```

If you see something like `Python 3.11.2`, you're good. If not, download it from [python.org](https://www.python.org/downloads/).

---

## Installation

You have two options: install from PyPI (the standard Python package registry) or install from source.

### Option A — Install with pip (recommended for most users)

Open your terminal and run:

```bash
pip install pyragify
```

That's it. `pip` is Python's built-in package installer and comes pre-installed with Python.

### Option B — Install with uv (faster, for advanced users)

[uv](https://github.com/astral-sh/uv) is a faster alternative to pip. If you have it installed:

```bash
uv pip install pyragify
```

### Option C — Install from source (for developers)

If you want to contribute or run the latest unreleased code:

```bash
git clone https://github.com/ThomasBury/pyragify.git
cd pyragify
pip install -e ".[dev]"
```

> **What is a terminal?** It's a text-based window where you type commands. On Mac, search for "Terminal" in Spotlight. On Windows, search for "Command Prompt" or "PowerShell" in the Start menu.

---

## Your First Run (Step by Step)

### Step 1 — Create a config file

In the folder where you want to work, create a file called `config.yaml` and paste this in, replacing the paths with your own:

```yaml
# The folder containing the code you want to process
repo_path: /Users/yourname/projects/my-repo

# Where Pyragify should save the output files
output_dir: ./output

# Maximum words per output file (200,000 is a good default)
max_words: 200000

# Skip files larger than 10 MB
max_file_size: 10485760

# Files and folders to ignore
skip_patterns:
  - "*.log"
  - "*.tmp"
skip_dirs:
  - "__pycache__"
  - "node_modules"

# Set to true to see detailed progress in the terminal
verbose: false
```

> **How do I find my folder path?**
> - On **Mac**: Right-click the folder in Finder → "Get Info" → copy the path shown under "Where"
> - On **Windows**: Open the folder in File Explorer → click the address bar at the top → copy the full path

### Step 2 — Run Pyragify

In your terminal, navigate to the folder containing your `config.yaml` file:

```bash
cd /path/to/folder/with/config
```

Then run:

```bash
pyragify --config-file config.yaml
```

You should see progress messages in the terminal as it processes your files.

### Step 3 — Find your output files

When it finishes, open the `output/` folder (or wherever you set `output_dir`). You'll find subfolders organized by file type:

```
output/
├── python/         ← Python functions, classes, and comments
├── markdown/       ← Markdown content split by headings
├── html/           ← Scripts and styles extracted from HTML
├── css/            ← CSS rules
├── other/          ← Other readable files
├── remaining/      ← Overflow content that didn't fit elsewhere
├── metadata.json   ← Summary of what was processed
└── hashes.json     ← Used to skip unchanged files on re-runs
```

### Step 4 — Upload to NotebookLM

1. Go to [notebooklm.google.com](https://notebooklm.google.com/)
2. Create a new notebook
3. Click **"Add sources"** and upload one or more `.txt` files from your output folder
4. Start asking questions about the codebase!

---

## Running Without a Config File

If you prefer not to create a config file, you can pass everything directly in the terminal command:

```bash
pyragify \
  --repo-path /path/to/your/repo \
  --output-dir ./output \
  --max-words 200000
```

Any option you pass on the command line overrides what's in the config file.

Run `pyragify --help` to see all available options.

---

## Supported File Types

| File type  | Extensions           | How it's chunked                        |
|------------|----------------------|-----------------------------------------|
| Python     | `.py`                | Per function, class, and comment block  |
| Markdown   | `.md`, `.markdown`   | Per heading section                     |
| HTML       | `.html`              | Extracted `<script>` and `<style>` tags |
| CSS        | `.css`               | Per CSS rule                            |
| Everything else | any readable file | Whole file as a single chunk       |

---

## Re-running on Updated Code

Pyragify stores an `hashes.json` file in your output directory. On subsequent runs, it compares file hashes and **skips files that haven't changed**, so re-runs are much faster.

Just run the same command again after updating your code.

---

## Troubleshooting

**"command not found: pyragify"**
Try running it as a Python module instead:
```bash
python -m pyragify --config-file config.yaml
```

**"No such file or directory" for repo_path**
Double-check your path in `config.yaml`. Make sure you're using the full path (e.g. `/Users/yourname/projects/my-repo`, not just `my-repo`).

**Output folder is empty**
Check that your `repo_path` actually contains supported files, and that they aren't all matched by `skip_patterns` or `skip_dirs`.

---

## Development

To contribute or run tests locally:

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run a specific test
pytest tests/test_processor.py -k markdown
```

---

## Contributing

Contributions are welcome. Open an issue for bugs or feature requests, then send a pull request with focused changes and matching tests.

---

## License

Released into the public domain under [The Unlicense](LICENSE).

---

[![Star History Chart](https://api.star-history.com/svg?repos=ThomasBury/pyragify&type=Date)](https://www.star-history.com/#ThomasBury/pyragify&Date)
