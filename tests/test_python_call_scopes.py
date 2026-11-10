import json
import sys

import pytest

from pyragify.graph import GraphQuery, KnowledgeGraph
from pyragify.processor import FileProcessor, RepoContentProcessor
from test_handoff import check_handoff


def build(tmp_path, source):
    path = tmp_path / "app.py"
    path.write_text(source, encoding="utf-8")
    return FileProcessor(tmp_path, tmp_path / "output", enable_graph=True).chunk_file(path, True)[2]


def calls(graph):
    return {(edge.source, edge.target) for edge in graph.edges if edge.type == "calls"}


@pytest.mark.parametrize("body, parameters", [
    ("run()", "run"),
    ("run()", "run, /"),
    ("run()", "*, run"),
    ("run()", "*run"),
    ("run()", "**run"),
    ("run = value\n    run()", ""),
    ("run()\n    run = value", ""),
    ("from elsewhere import run\n    run()", ""),
    ("import elsewhere as run\n    run()", ""),
    ("for run in values:\n        run()", ""),
    ("with manager as run:\n        run()", ""),
    ("try:\n        pass\n    except Exception as run:\n        run()", ""),
    ("(run := value)\n    run()", ""),
    ("del run\n    run()", ""),
])
@pytest.mark.parametrize("definition", ["def", "async def"])
def test_bindings_prevent_fallback_to_module_function(tmp_path, body, parameters, definition):
    graph = build(tmp_path, f"def run(): pass\n{definition} caller({parameters}):\n    {body}\n")
    assert calls(graph) == {("app.py::caller", "function::run")}


def test_nested_bindings_globals_and_nonlocals(tmp_path):
    graph = build(tmp_path, """def run(): pass
def outer(run):
    def shadowed():
        run()
    def use_global():
        global run
        run()
def enclosing():
    def run(): pass
    def use_nonlocal():
        nonlocal run
        run()
    def replace_nonlocal():
        nonlocal run
        run = value
        run()
def replace_global():
    global run
    run = value
    run()
""")
    assert calls(graph) == {
        ("app.py::outer.shadowed", "function::run"),
        ("app.py::outer.use_global", "app.py::run"),
        ("app.py::enclosing.use_nonlocal", "app.py::enclosing.run"),
        ("app.py::enclosing.replace_nonlocal", "function::run"),
        ("app.py::replace_global", "function::run"),
    }


@pytest.mark.parametrize("definition", ["def", "async def"])
def test_definition_expressions_keep_their_execution_owner(tmp_path, definition):
    graph = build(tmp_path, f"""def run(): pass
@run()
{definition} top(arg=run(), *, other=run()):
    run()
def outer():
    @run()
    {definition} inner(arg=run(), *, other=run()):
        run()
class A:
    run()
    @run()
    {definition} method(self, arg=run(), *, other=run()):
        run()
""")
    assert calls(graph) == {
        ("file::app.py", "app.py::run"),
        ("app.py::top", "app.py::run"),
        ("app.py::outer", "app.py::run"),
        ("app.py::outer.inner", "app.py::run"),
        ("app.py::A", "app.py::run"),
        ("app.py::A.method", "app.py::run"),
    }
    assert {item["name"] for item in GraphQuery(graph).get_call_hierarchy("run")["callers"]} == {
        "top", "outer", "inner", "method"}


def test_same_line_calls_and_definition_have_source_columns(tmp_path):
    graph = build(tmp_path, "def first(): pass\ndef second(): pass\ndef caller(arg=first()): second(); first()\n")
    assert calls(graph) == {
        ("file::app.py", "app.py::first"),
        ("app.py::caller", "app.py::second"),
        ("app.py::caller", "app.py::first"),
    }
    positions = {(edge.metadata["line"], edge.metadata["column"]) for edge in graph.edges if edge.type == "calls"}
    assert len(positions) == 3
    assert graph.nodes["app.py::caller"].metadata["column"] == 0


def test_class_scope_is_skipped_by_methods_and_nested_classes(tmp_path):
    graph = build(tmp_path, """def run(): pass
class A:
    def run(self): pass
    def caller(self):
        run()
        self.run()
    class B:
        run()
    def shadowed(self):
        self = value
        self.run()
def other(A):
    A.run()
""")
    assert calls(graph) == {
        ("app.py::A.caller", "app.py::run"),
        ("app.py::A.caller", "app.py::A.run"),
        ("app.py::A.B", "app.py::run"),
        ("app.py::A.shadowed", "method::self.run"),
        ("app.py::other", "method::A.run"),
    }


def test_lambda_and_comprehension_parameters_do_not_leak(tmp_path):
    graph = build(tmp_path, """def run(): pass
def caller():
    callback = lambda run: run()
    values = [run() for run in items]
    run()
""")
    assert calls(graph) == {("app.py::caller", "function::run"), ("app.py::caller", "app.py::run")}


def test_method_defaults_use_class_bindings_but_bodies_do_not(tmp_path):
    graph = build(tmp_path, """def run(): pass
class A:
    def run(self): pass
    def caller(self, arg=run()):
        run()
        self.run()
A.run()
""")
    assert calls(graph) == {
        ("app.py::A", "app.py::A.run"),
        ("app.py::A.caller", "app.py::run"),
        ("app.py::A.caller", "app.py::A.run"),
        ("file::app.py", "app.py::A.run"),
    }


@pytest.mark.parametrize("binding", ["run = value", "from elsewhere import run", "from elsewhere import *"])
def test_module_bindings_prevent_fallback(tmp_path, binding):
    graph = build(tmp_path, f"def run(): pass\n{binding}\ndef caller():\n    run()\n")
    assert calls(graph) == {("app.py::caller", "function::run")}


def test_rebinding_a_local_definition_is_uncertain(tmp_path):
    graph = build(tmp_path, "def run(): pass\ndef caller():\n    def run(): pass\n    run = value\n    run()\n")
    assert calls(graph) == {("app.py::caller", "function::run")}


def test_declarations_in_enclosing_scopes_control_closure_lookup(tmp_path):
    graph = build(tmp_path, """def run(): pass
def outer(run):
    def middle():
        global run
        def inner():
            run()
def enclosing():
    def run(): pass
    class A:
        def run(self): pass
        def method(self):
            nonlocal run
            run()
""")
    assert calls(graph) == {
        ("app.py::outer.middle.inner", "app.py::run"),
        ("app.py::enclosing.A.method", "app.py::enclosing.run"),
    }


def test_comprehension_walrus_binds_in_the_containing_scope(tmp_path):
    graph = build(tmp_path, "def run(): pass\ndef caller():\n    [(run := value) for value in items]\n    run()\n")
    assert calls(graph) == {("app.py::caller", "function::run")}


@pytest.mark.skipif(sys.version_info < (3, 10), reason="Pattern matching requires Python 3.10")
@pytest.mark.parametrize("pattern", ["run", "{'key': run}", "[*run]", "{'key': value, **run}"])
def test_pattern_captures_shadow_definitions(tmp_path, pattern):
    graph = build(tmp_path, f"def run(): pass\ndef caller(value):\n    match value:\n        case {pattern}:\n            run()\n")
    assert calls(graph) == {("app.py::caller", "function::run")}


def test_scope_graph_survives_reload_cache_reuse_and_old_cache_rebuild(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_bytes(b"# caf\xc3\xa9\r\ndef run(): pass\r\ndef caller(run=run()):\r\n    run()\r\n")
    output = tmp_path / "output"
    processor = RepoContentProcessor(repo, output, enable_graph=True)
    processor.process_repo()
    expected = processor.repo_graph.to_dict()
    assert calls(processor.repo_graph) == {("file::app.py", "app.py::run"), ("app.py::caller", "function::run")}
    assert KnowledgeGraph.from_dict(json.loads(json.dumps(expected))).to_dict() == expected
    check_handoff(repo, output)
    with monkeypatch.context() as patch:
        patch.setattr("pyragify.processor._process_file_worker", lambda task: pytest.fail("Cache was not reused"))
        cached = RepoContentProcessor(repo, output, enable_graph=True)
        cached.process_repo()
    assert cached.repo_graph.to_dict() == expected
    assert check_handoff(repo, output)["reused_files"] == ["app.py"]
    cache_path = output / ".pyragify-cache.json"
    cache = json.loads(cache_path.read_text())
    cache["version"] = 5
    cache["files"]["app.py"]["graph"]["edges"] = []
    cache_path.write_text(json.dumps(cache))
    rebuilt = RepoContentProcessor(repo, output, enable_graph=True)
    rebuilt.process_repo()
    assert rebuilt.repo_graph.to_dict() == expected
    assert check_handoff(repo, output)["reused_files"] == []
