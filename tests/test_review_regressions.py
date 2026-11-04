import pytest

from pyragify.graph import GraphBuilder, GraphQuery
from pyragify.processor import FileProcessor, is_probably_binary_file


@pytest.mark.parametrize("character", ["é", "€", "🐍"])
def test_utf8_sample_boundary_is_text(tmp_path, character):
    path = tmp_path / "text.md"
    path.write_text("a" * 2047 + character, encoding="utf-8")
    assert not is_probably_binary_file(path)


@pytest.mark.parametrize("content", [b"abc\xff", b"a" * 2047 + b"\xc3", b"a\x00b"])
def test_invalid_utf8_or_nul_is_binary(tmp_path, content):
    path = tmp_path / "binary"
    path.write_bytes(content)
    assert is_probably_binary_file(path)


def build(tmp_path, path, content):
    file = tmp_path / path
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(content, encoding="utf-8")
    return FileProcessor(tmp_path, tmp_path / "output", enable_graph=True).chunk_file(file, include_graph=True)[2]


@pytest.mark.parametrize("source", ["", "import os\n", "VALUE = 1\n", "print('hello')\n"])
def test_graph_without_semantic_chunks(tmp_path, source):
    graph = build(tmp_path, "app.py", source)
    assert "file::app.py" in graph.nodes
    if source.startswith("import"):
        assert any(edge.type == "imports" and edge.target == "module::os" for edge in graph.edges)
    if source.startswith("print"):
        assert any(edge.type == "calls" and edge.source == "file::app.py" for edge in graph.edges)


def test_same_named_methods_have_separate_callees(tmp_path):
    graph = build(tmp_path, "app.py", """
def first(): pass
def second(): pass
class A:
    def run(self):
        first()
    def again(self):
        self.run()
class B:
    def run(self):
        second()
    def again(self):
        self.run()
""")
    query = GraphQuery(graph)
    assert {item["name"] for item in query.get_call_hierarchy("A.run")["callees"]} == {"first"}
    assert {item["name"] for item in query.get_call_hierarchy("B.run")["callees"]} == {"second"}
    assert len(query.get_call_hierarchy("run")["locations"]) == 2
    calls = {(edge.source, edge.target) for edge in graph.edges if edge.type == "calls"}
    assert ("app.py::A.again", "app.py::A.run") in calls
    assert ("app.py::B.again", "app.py::B.run") in calls


def test_nested_functions_resolve_in_their_own_scopes(tmp_path):
    graph = build(tmp_path, "app.py", """
def one():
    def helper(): pass
    helper()
def two():
    def helper(): pass
    helper()
""")
    calls = {(edge.source, edge.target) for edge in graph.edges if edge.type == "calls"}
    assert calls == {("app.py::one", "app.py::one.helper"), ("app.py::two", "app.py::two.helper")}


@pytest.mark.parametrize("statement, dependency", [
    ("from pkg.helper import foo", "pkg/helper.py"),
    ("import pkg.helper", "pkg/helper.py"),
    ("from .helper import foo", "pkg/helper.py"),
    ("from . import helper", "pkg/helper.py"),
    ("from pkg import foo", "pkg/__init__.py"),
    ("import missing", None),
])
def test_package_imports_resolve_to_exact_files(tmp_path, statement, dependency):
    builder = GraphBuilder(tmp_path)
    graphs = [build(tmp_path, path, content) for path, content in [
        ("pkg/__init__.py", "foo = 1\n"),
        ("pkg/helper.py", "def foo(): pass\n"),
        ("pkg/app.py", statement + "\n"),
        ("pkg/missing_suffix.py", "def foo(): pass\n"),
    ]]
    for graph in graphs:
        builder.graph.merge(graph)
    assert GraphQuery(builder.graph).find_dependencies("pkg/app.py") == ([dependency] if dependency else [])
    builder.resolve_cross_file_references(graphs)
    refs = {edge.target for edge in builder.graph.edges if edge.source == "file::pkg/app.py"
            and edge.type == "cross_file_reference"}
    assert refs == ({"file::" + dependency} if dependency else set())
