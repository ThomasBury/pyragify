import pytest

from pyragify.graph import GraphBuilder, GraphQuery, KnowledgeGraph
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


def test_enabling_graphs_rebuilds_empty_chunk_cache(tmp_path):
    from pyragify.processor import RepoContentProcessor
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "imports.py").write_text("import os\n")
    (repo / "empty.py").write_text("")
    output = tmp_path / "output"
    RepoContentProcessor(repo, output).process_repo()
    processor = RepoContentProcessor(repo, output, enable_graph=True)
    processor.process_repo()
    assert "file::imports.py" in processor.repo_graph.nodes
    assert "file::empty.py" in processor.repo_graph.nodes
    assert any(edge.target == "module::os" for edge in processor.repo_graph.edges)


@pytest.mark.parametrize("filename, source, target", [
    ("a.js", "// café 🐍\nfunction foo() {}\nfunction bar() { foo(); }", "a.js::foo"),
    ("a.ts", "// café 🐍\nfunction foo() {}\nfunction bar() { foo(); }", "a.ts::foo"),
    ("a.c", "// café 🐍\nint foo() { return 1; }\nint bar() { return foo(); }", "a.c::foo"),
    ("a.cpp", "// café 🐍\nint foo() { return 1; }\nint bar() { return foo(); }", "a.cpp::foo"),
    ("A.java", "// café 🐍\nclass A {\nint foo() { return 1; }\nint bar() { return foo(); }\n}", "A.java::A.foo"),
])
def test_unicode_preserves_parser_code_and_references(tmp_path, filename, source, target):
    graph = build(tmp_path, filename, source)
    assert any(edge.type == "calls" and edge.target == target for edge in graph.edges)
    file = tmp_path / filename
    chunks, _ = FileProcessor(tmp_path, tmp_path / "output").chunk_file(file)
    assert chunks[0]["content"] == source
    assert all(chunk["code"] in source for chunk in chunks if "code" in chunk)


@pytest.mark.parametrize("extension", ["js", "ts"])
def test_javascript_import_sources_are_distinct(tmp_path, extension):
    graph = build(tmp_path, "app." + extension, """
import { foo as first } from './a';
import { foo as second } from './b';
import value from './default';
import * as ns from './namespace';
import './side-effect';
first();
""")
    imports = [edge for edge in graph.edges if edge.type == "imports"]
    assert {edge.target for edge in imports} == {"module::" + name for name in
        ["./a", "./b", "./default", "./namespace", "./side-effect"]}
    assert any("foo as first" in edge.metadata["statement"] for edge in imports)


def test_system_include_survives_other_edges(tmp_path):
    graph = build(tmp_path, "app.c", "#include <stdio.h>\nint run() { return puts(\"hi\"); }\n")
    assert any(edge.type == "includes" and edge.target == "header::stdio.h" for edge in graph.edges)


def test_many_unnamed_chunks_have_unique_ids(tmp_path):
    path = tmp_path / "app.css"
    path.write_text("a {} b {} c {} d {}")
    graph = GraphBuilder(tmp_path).build_from_chunks(path, [{"type": "css_rule", "content": "{}"}] * 5, "css")
    assert len([node for node in graph.nodes.values() if node.type == "css_rule"]) == 5


def test_inheritance_connects_each_scoped_subclass(tmp_path):
    graph = build(tmp_path, "app.py", """
class Outer:
    class Base: pass
    class First(Base): pass
    class Second(Base): pass
""")
    edges = {(edge.source, edge.target) for edge in graph.edges if edge.type == "inherits"}
    assert edges == {("app.py::Outer.First", "app.py::Outer.Base"),
                     ("app.py::Outer.Second", "app.py::Outer.Base")}
    related = GraphQuery(graph).find_related_context("app.py::Outer.First", 1, ["inherits"])
    assert [(item.node.id, item.relationship_path) for item in related] == [
        ("app.py::Outer.Base", ["inherits"])]


@pytest.mark.parametrize("relationship", ["contains", "calls"])
def test_reverse_context_retains_traversed_relationship(tmp_path, relationship):
    from pyragify.graph import GraphEdge, GraphNode, KnowledgeGraph
    graph = KnowledgeGraph()
    for name in ("source", "target"):
        graph.add_node(GraphNode(id=name, type="function", name=name, file="app.py", language="python"))
    graph.add_edge(GraphEdge(source="source", target="target", type="references"))
    graph.add_edge(GraphEdge(source="source", target="target", type=relationship))
    related = GraphQuery(graph).find_related_context("target", 1, [relationship])
    assert len(related) == 1
    assert related[0].node.id == "source"
    assert related[0].relationship_path == [relationship]
    assert GraphQuery(graph).find_related_context("target", 1, []) == []


@pytest.mark.parametrize("suffix", [".js", ".ts"])
@pytest.mark.parametrize("separator", ["\r\n", " "])
def test_native_javascript_imports_and_inheritance(tmp_path, monkeypatch, caplog, suffix, separator):
    monkeypatch.setattr(GraphBuilder, '_extract_js_regex_fallback',
                        lambda *args: pytest.fail('Valid source must use the parser'))
    source = ('// café 🐍\r\nimport value from "./first";\r\n'
              'const other = require("./second");\r\n'
              + separator.join(['class Base {}', 'class First extends Base {}', 'class Second extends Base {}']))
    graph = build(tmp_path, 'app' + suffix, source)
    inherits = {(edge.source, edge.target) for edge in graph.edges if edge.type == 'inherits'}
    assert inherits == {('app' + suffix + '::First', 'app' + suffix + '::Base'),
                        ('app' + suffix + '::Second', 'app' + suffix + '::Base')}
    assert {edge.target for edge in graph.edges if edge.type == 'imports'} == {
        'module::./first', 'module::./second'}
    assert not caplog.records
    loaded = KnowledgeGraph.from_dict(graph.to_dict())
    assert loaded.to_dict() == graph.to_dict()
    assert {item.node.id for item in GraphQuery(loaded).find_related_context(
        'app' + suffix + '::First', 1, ['inherits'])} == {'app' + suffix + '::Base'}


def test_native_java_imports_calls_and_optional_inheritance(tmp_path, monkeypatch, caplog):
    monkeypatch.setattr(GraphBuilder, '_extract_java_regex_fallback',
                        lambda *args: pytest.fail('Valid source must use the parser'))
    graph = build(tmp_path, 'App.java', '// café 🐍\r\nimport java.util.List;\r\n'
                  'import java.util.Map;\r\nclass Base {}\r\nclass App extends Base {\r\n'
                  '  void leaf() {}\r\n  void run() { leaf(); leaf(); }\r\n}\r\nclass Plain {}\r\n')
    assert {'App.java::Base', 'App.java::App', 'App.java::Plain',
            'App.java::App.leaf', 'App.java::App.run'} <= graph.nodes.keys()
    assert {edge.target for edge in graph.edges if edge.type == 'imports'} == {
        'package::java.util.List', 'package::java.util.Map'}
    assert {(edge.source, edge.target) for edge in graph.edges if edge.type == 'inherits'} == {
        ('App.java::App', 'App.java::Base')}
    assert {(edge.source, edge.target) for edge in graph.edges if edge.type == 'calls'} == {
        ('App.java::App.run', 'App.java::App.leaf')}
    assert not caplog.records


@pytest.mark.parametrize('suffix', ['.c', '.cpp'])
def test_native_c_includes_calls_and_cpp_classes(tmp_path, monkeypatch, caplog, suffix):
    monkeypatch.setattr(GraphBuilder, '_extract_cpp_regex_fallback',
                        lambda *args: pytest.fail('Valid source must use the parser'))
    source = ('// café 🐍\r\n#include <stdio.h>\r\n#include "local.h"\r\n'
              'int leaf() { return 1; }\r\nint run() { return leaf(); }\r\nstruct Data { int value; };\r\n')
    if suffix == '.cpp':
        source += 'class Item {};\r\n'
    file = 'app' + suffix
    graph = build(tmp_path, file, source)
    assert {file + '::leaf', file + '::run'} <= graph.nodes.keys()
    assert {edge.target for edge in graph.edges if edge.type == 'includes'} == {
        'header::stdio.h', 'header::local.h'}
    assert {(edge.source, edge.target) for edge in graph.edges if edge.type == 'calls'} == {
        (file + '::run', file + '::leaf')}
    if suffix == '.cpp':
        assert graph.nodes[file + '::Item'].type == 'cpp_class'
        assert graph.nodes[file + '::Data'].type == 'cpp_struct'
    assert not caplog.records


def test_native_go_symbols(tmp_path):
    graph = build(tmp_path, 'app.go', 'package main\r\n// café 🐍\r\n'
                  'type Item struct { value int }\r\nfunc first() {}\r\nfunc second() {}\r\n')
    assert {node.name: node.type for node in graph.nodes.values() if node.type != 'file'} == {
        'Item': 'go_type', 'first': 'go_function', 'second': 'go_function'}


@pytest.mark.parametrize('filename, source', [
    ('app.js', 'import value from "./other"; class Child extends Base {}'),
    ('App.java', 'import java.util.List; class App extends Base {}'),
    ('app.c', '#include <stdio.h>\nint run() { return puts("hi"); }'),
])
def test_dependency_query_failures_are_logged(tmp_path, monkeypatch, caplog, filename, source):
    def fail_query(*args):
        raise ValueError('injected invalid query')
    monkeypatch.setattr('pyragify.graph.Query', fail_query)
    GraphBuilder(tmp_path).extract_dependencies(tmp_path / filename, source,
                                               {'.js': 'javascript', '.java': 'java', '.c': 'c'}[
                                                   (tmp_path / filename).suffix])
    assert 'Tree-sitter query failed' in caplog.text
    assert 'injected invalid query' in caplog.text
    assert all(record.levelname == 'WARNING' for record in caplog.records)
