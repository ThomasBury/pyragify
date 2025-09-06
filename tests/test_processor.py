import pytest
from pathlib import Path
from pyragify.processor import FileProcessor, compute_file_hash, save_json, load_json, is_documentation_file, read_file_in_chunks

@pytest.fixture
def sample_python_file(tmp_path):
    """Fixture for a sample Python file with function and class."""
    file_path = tmp_path / "sample.py"
    file_path.write_text("""
def test_function(param):
    \"\"\"Docstring for function.\"\"\"
    return param * 2

class TestClass:
    \"\"\"Docstring for class.\"\"\"
    def method(self):
        return "method"
# Comment line
""")
    return file_path

@pytest.fixture
def sample_markdown_file(tmp_path):
    """Fixture for a sample Markdown file with headers."""
    file_path = tmp_path / "sample.md"
    file_path.write_text("""
# Header 1
Content under header 1.

## Header 2
Content under header 2.
""")
    return file_path

@pytest.fixture
def sample_js_file(tmp_path):
    """Fixture for a sample JavaScript file."""
    file_path = tmp_path / "sample.js"
    file_path.write_text("""
function testFunction(param) {
    return param * 2;
}

class TestClass {
    constructor() {}
    method() {
        return 'test';
    }
}

const arrow = (x) => x * 3;
""")
    return file_path

@pytest.fixture
def sample_java_file(tmp_path):
    """Fixture for a sample Java file."""
    file_path = tmp_path / "Sample.java"
    file_path.write_text("""
public class Sample {
    public static void testMethod(String param) {
        return param.length();
    }
}
""")
    return file_path

@pytest.fixture
def sample_cpp_file(tmp_path):
    """Fixture for a sample C++ file."""
    file_path = tmp_path / "sample.cpp"
    file_path.write_text("""
struct TestStruct {
    int x;
};

int testFunction(int param) {
    return param * 2;
}
""")
    return file_path

@pytest.fixture
def sample_html_file(tmp_path):
    """Fixture for a sample HTML file."""
    file_path = tmp_path / "sample.html"
    file_path.write_text("""
<!DOCTYPE html>
<html>
<script>
function jsFunc() { return 'hi'; }
</script>
<style>
body { color: red; }
</style>
</html>
""")
    return file_path

@pytest.fixture
def sample_css_file(tmp_path):
    """Fixture for a sample CSS file."""
    file_path = tmp_path / "sample.css"
    file_path.write_text("""
body {
    color: red;
}

@media screen {
    div { font-size: 12px; }
}
""")
    return file_path

def test_compute_file_hash(sample_python_file):
    """Test file hash computation."""
    hash_value = compute_file_hash(sample_python_file)
    assert isinstance(hash_value, str)
    assert len(hash_value) == 32  # MD5 hex length

def test_save_json_load_json(tmp_path):
    """Test saving and loading JSON."""
    data = {"test": "value"}
    json_path = tmp_path / "test.json"
    save_json(data, json_path, "test data")
    loaded = load_json(json_path, "test data")
    assert loaded == data

def test_is_documentation_file():
    """Test documentation file detection."""
    assert is_documentation_file(Path("README.md")) == True
    assert is_documentation_file(Path("example.py")) == False

def test_read_file_in_chunks(sample_python_file):
    """Test reading file in chunks."""
    chunks = list(read_file_in_chunks(sample_python_file))
    full_content = sample_python_file.read_text()
    assert ''.join(chunks) == full_content

class TestFileProcessor:
    def test_chunk_python_file(self, sample_python_file, tmp_path):
        """Test Python chunking."""
        output_dir = tmp_path / "output"
        processor = FileProcessor(tmp_path, output_dir)
        chunks, line_count = processor.chunk_python_file(sample_python_file)
        assert line_count > 0
        assert len(chunks) >= 3  # Function, class, and comments
        func_chunk = next((c for c in chunks if c["type"] == "function"), None)
        assert func_chunk is not None
        assert "test_function" in func_chunk["name"]
        assert "def test_function" in func_chunk["code"]
        assert func_chunk["docstring"] == "Docstring for function."
        class_chunk = next((c for c in chunks if c["type"] == "class"), None)
        assert class_chunk is not None
        assert "TestClass" in class_chunk["name"]
        assert "class TestClass" in class_chunk["code"]
        assert class_chunk["docstring"] == "Docstring for class."

    def test_chunk_markdown_file(self, sample_markdown_file, tmp_path):
        """Test Markdown chunking."""
        output_dir = tmp_path / "output"
        processor = FileProcessor(tmp_path, output_dir)
        chunks, line_count = processor.chunk_markdown_file(sample_markdown_file)
        assert line_count > 0
        assert len(chunks) == 2  # Two headers
        assert chunks[0]["header"] == "# Header 1"
        assert "Content under header 1" in chunks[0]["content"]

    @pytest.mark.parametrize("file_fixture, suffix, expected_types", [
        ("sample_js_file", ".js", ["file"]),
        ("sample_java_file", ".java", ["file"]),
        ("sample_cpp_file", ".cpp", ["file"]),
        ("sample_html_file", ".html", ["html_script", "html_style"]),
        ("sample_css_file", ".css", ["css_rule"]),
    ])
    def test_chunk_tree_sitter_file_real(self, request, file_fixture, suffix, expected_types, tmp_path):
        """Test tree-sitter chunking for multiple languages with real parsers."""
        file_path = request.getfixturevalue(file_fixture)
        output_dir = tmp_path / "output"
        processor = FileProcessor(tmp_path, output_dir)
        chunks, line_count = processor.chunk_tree_sitter_file(file_path, suffix)
        assert line_count > 0
        assert chunks
        found_types = {c["type"] for c in chunks}
        for expected_type in expected_types:
            assert expected_type in found_types

    def test_chunk_file_routing(self, sample_python_file, sample_markdown_file, sample_js_file, tmp_path):
        """Test chunk_file routes to correct method."""
        output_dir = tmp_path / "output"
        processor = FileProcessor(tmp_path, output_dir)
        py_chunks, _ = processor.chunk_file(sample_python_file)
        assert any(c["type"] == "function" for c in py_chunks)
        md_chunks, _ = processor.chunk_file(sample_markdown_file)
        assert "header" in md_chunks[0]
        js_chunks, _ = processor.chunk_file(sample_js_file)
        assert any(c["type"] == "file" for c in js_chunks)

    def test_format_chunk(self):
        """Test formatting various chunk types."""
        processor = FileProcessor(Path("."), Path("."))
        func_chunk = {"type": "function", "name": "test", "code": "def test(): pass", "docstring": "A test function."}
        formatted = processor.format_chunk(func_chunk)
        assert "Function: test" in formatted
        assert "Docstring:\nA test function." in formatted
        assert "def test(): pass" in formatted
        html_chunk = {"type": "html_script", "content": "<script>alert('hi');</script>"}
        formatted_html = processor.format_chunk(html_chunk)
        assert "HTML Script:" in formatted_html

    def test_chunk_file_unreadable(self, tmp_path, caplog):
        """Test that chunking an unreadable file is handled gracefully."""
        output_dir = tmp_path / "output"
        processor = FileProcessor(tmp_path, output_dir)
        bad_file = tmp_path / "bad.txt"
        bad_file.write_bytes(b'\x80') # Invalid utf-8
        chunks, line_count = processor.chunk_file(bad_file)
        assert chunks == []
        assert line_count == 0
        assert "Error reading file" in caplog.text