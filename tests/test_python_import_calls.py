import json

import pytest

from pyragify.graph import GraphBuilder, GraphQuery, KnowledgeGraph
from pyragify.processor import FileProcessor, RepoContentProcessor
from test_handoff import check_handoff


def calls(graph):
    return {(edge.source, edge.target) for edge in graph.edges if edge.type == "calls"}


def build(tmp_path, sources):
    builder = GraphBuilder(tmp_path)
    graphs = []
    for name, source in sources.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
        graph = FileProcessor(tmp_path, tmp_path / "output", enable_graph=True).chunk_file(path, True)[2]
        graph = KnowledgeGraph.from_dict(json.loads(json.dumps(graph.to_dict())))
        graphs.append(graph)
        builder.graph.merge(graph)
    per_file = [graph.to_dict() for graph in graphs]
    builder.resolve_cross_file_references(graphs)
    assert [graph.to_dict() for graph in graphs] == per_file
    resolved = builder.graph.to_dict()
    builder.graph = KnowledgeGraph.from_dict(json.loads(json.dumps(resolved)))
    builder.resolve_cross_file_references([])
    assert builder.graph.to_dict() == resolved
    return builder.graph


@pytest.mark.parametrize("prefix", ["", "src/"])
@pytest.mark.parametrize("statement, expression, target, dependency", [
    ("from pkg.b import run", "run()", "pkg/b.py", "pkg/b.py"),
    ("from pkg.b import run as alias", "alias()", "pkg/b.py", "pkg/b.py"),
    ("import pkg.b", "pkg.b.run()", "pkg/b.py", "pkg/b.py"),
    ("import pkg.b as mod", "mod.run()", "pkg/b.py", "pkg/b.py"),
    ("from pkg import b as mod", "mod.run()", "pkg/b.py", "pkg/b.py"),
    ("from .b import run", "run()", "pkg/b.py", "pkg/b.py"),
    ("from . import b", "b.run()", "pkg/b.py", "pkg/b.py"),
    ("from ..b import run", "run()", "pkg/b.py", "pkg/b.py"),
    ("from pkg import run", "run()", "pkg/__init__.py", "pkg/__init__.py"),
    ("import pkg as mod", "mod.run()", "pkg/__init__.py", "pkg/__init__.py"),
    ("from .. import run as alias", "alias()", "pkg/__init__.py", "pkg/__init__.py"),
])
def test_explicit_imports_resolve_exact_functions(tmp_path, prefix, statement, expression, target, dependency):
    app = prefix + "pkg/sub/app.py" if ".." in statement else prefix + "pkg/app.py"
    graph = build(tmp_path, {
        prefix + "a.py": "def run(): pass\n",
        prefix + "pkg/__init__.py": "def run(): pass\n",
        prefix + "pkg/b.py": "async def run(): pass\n",
        app: statement + "\ndef caller():\n    " + expression + "\n",
    })
    assert calls(graph) == {(app + "::caller", prefix + target + "::run")}
    assert GraphQuery(graph).find_dependencies(app) == [prefix + dependency]
    assert any(edge.type == "cross_file_reference" and edge.source == "file::" + app
               and edge.target == "file::" + prefix + dependency for edge in graph.edges)
    assert GraphQuery(graph).get_call_hierarchy(prefix + target + "::run")["callers"] == [
        {"name": "caller", "file": app, "line": 3}]
    related = GraphQuery(graph).find_related_context(app + "::caller", 1, ["calls"])
    assert [item.node.id for item in related] == [prefix + target + "::run"]


def test_scoped_imports_and_unrelated_placeholder_are_independent(tmp_path):
    graph = build(tmp_path, {
        "a.py": "def run(): pass\n",
        "b.py": "def run(): pass\n",
        "app.py": """from b import run
def first():
    run()
def second():
    from a import run
    run()
def shadowed(run):
    run()
def mixed():
    callback = lambda run: run()
    run()
def enclosing():
    from a import run
    def inner():
        nonlocal run
        run()
    def use_global():
        global run
        run()
""",
    })
    assert calls(graph) == {
        ("app.py::first", "b.py::run"),
        ("app.py::second", "a.py::run"),
        ("app.py::shadowed", "function::run"),
        ("app.py::mixed", "function::run"),
        ("app.py::mixed", "b.py::run"),
        ("app.py::enclosing.inner", "a.py::run"),
        ("app.py::enclosing.use_global", "b.py::run"),
    }


def test_imported_calls_in_defaults_keep_the_containing_owner(tmp_path):
    graph = build(tmp_path, {
        "b.py": "def run(): pass\n",
        "app.py": """from b import run
@run()
async def caller(arg=run()):
    run()
class A:
    from b import run as alias
    def method(self, arg=alias()):
        alias()
""",
    })
    assert calls(graph) == {
        ("file::app.py", "b.py::run"),
        ("app.py::caller", "b.py::run"),
        ("app.py::A", "b.py::run"),
        ("app.py::A.method", "function::alias"),
    }


@pytest.mark.parametrize("body, parameters", [
    ("run()", "run"),
    ("run()\n    run = value", ""),
    ("import missing as run\n    run()", ""),
    ("def run(): pass\n    run()", ""),
])
def test_import_shadowing_does_not_resolve_to_imported_function(tmp_path, body, parameters):
    graph = build(tmp_path, {
        "b.py": "def run(): pass\n",
        "app.py": f"from b import run\ndef caller({parameters}):\n    {body}\n",
    })
    expected = "app.py::caller.run" if body.startswith("def run") else "function::run"
    assert calls(graph) == {("app.py::caller", expected)}


@pytest.mark.parametrize("source", [
    "def run(): pass\nrun = value\n",
    "def enclosing():\n    def run(): pass\n",
    "from a import run\n",
    "def run(): pass\ndef run(): pass\n",
    "from unknown import *\ndef run(): pass\n",
])
def test_ambiguous_or_nonlocal_exports_are_unresolved(tmp_path, source):
    graph = build(tmp_path, {
        "a.py": "def run(): pass\n",
        "b.py": source,
        "app.py": "from b import run\ndef caller():\n    run()\n",
    })
    assert calls(graph) == {("app.py::caller", "function::run")}


@pytest.mark.parametrize("duplicate", ["src/b.py", "b/__init__.py"])
def test_ambiguous_module_paths_remain_unresolved(tmp_path, duplicate):
    graph = build(tmp_path, {
        "b.py": "def run(): pass\n",
        duplicate: "def run(): pass\n",
        "app.py": "from b import run\ndef caller():\n    run()\n",
    })
    assert calls(graph) == {("app.py::caller", "function::run")}
    assert GraphQuery(graph).find_dependencies("app.py") == []


def test_package_function_takes_precedence_over_same_named_submodule(tmp_path):
    graph = build(tmp_path, {
        "pkg/__init__.py": "def run(): pass\n",
        "pkg/run.py": "def run(): pass\n",
        "app.py": "from pkg import run\ndef caller():\n    run()\n",
    })
    assert calls(graph) == {("app.py::caller", "pkg/__init__.py::run")}
    assert GraphQuery(graph).find_dependencies("app.py") == ["pkg/__init__.py"]


@pytest.mark.parametrize("binding", ["b = value", "from other import b", "from other import *"])
def test_existing_package_binding_prevents_submodule_guessing(tmp_path, binding):
    graph = build(tmp_path, {
        "pkg/__init__.py": binding + "\n",
        "pkg/b.py": "def run(): pass\n",
        "app.py": "from pkg import b\ndef caller():\n    b.run()\n",
    })
    assert calls(graph) == {("app.py::caller", "method::b.run")}


@pytest.mark.parametrize("body, parameters", [
    ("b.run()", "b"),
    ("b.run()\n    b = value", ""),
    ("b = value\n    b.run()", ""),
])
def test_module_receiver_shadowing_blocks_import_resolution(tmp_path, body, parameters):
    graph = build(tmp_path, {
        "b.py": "def run(): pass\n",
        "app.py": f"import b\ndef caller({parameters}):\n    {body}\n",
    })
    assert calls(graph) == {("app.py::caller", "method::b.run")}


@pytest.mark.parametrize("statement, expression, placeholder", [
    ("from b import *", "run()", "function::run"),
    ("import pkg.b", "pkg.other.run()", "method::pkg.other.run"),
    ("from ...b import run", "run()", "function::run"),
    ("import missing as b", "b.run()", "method::b.run"),
])
def test_unsupported_imports_do_not_guess(tmp_path, statement, expression, placeholder):
    graph = build(tmp_path, {
        "b.py": "def run(): pass\n",
        "pkg/b.py": "def run(): pass\n",
        "app.py": statement + "\ndef caller():\n    " + expression + "\n",
    })
    assert calls(graph) == {("app.py::caller", placeholder)}


def test_incremental_import_resolution_uses_current_definitions(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.py").write_text("def run(): pass\n")
    (repo / "b.py").write_text("# café 🐍\ndef run(): pass\n")
    (repo / "app.py").write_bytes(b"from b import run\r\ndef caller():\r\n    run()\r\n")
    output = tmp_path / "output"

    def export():
        processor = RepoContentProcessor(repo, output, enable_graph=True)
        processor.process_repo()
        check_handoff(repo, output)
        loaded = KnowledgeGraph.from_dict(json.loads((output / "graphs/repository_graph.json").read_text()))
        assert loaded.to_dict() == processor.repo_graph.to_dict()
        return loaded

    original = export()
    assert calls(original) == {("app.py::caller", "b.py::run")}
    with monkeypatch.context() as patch:
        patch.setattr("pyragify.processor._process_file_worker", lambda task: pytest.fail("Cache not reused"))
        assert export().to_dict() == original.to_dict()
    cache_path = output / ".pyragify-cache.json"
    cache = json.loads(cache_path.read_text())
    assert next(edge for edge in cache["files"]["app.py"]["graph"]["edges"] if edge["type"] == "calls")["target"] == "function::run"
    cache["version"] = 6
    cache["files"]["app.py"]["graph"]["edges"] = []
    cache_path.write_text(json.dumps(cache))
    assert export().to_dict() == original.to_dict()
    assert check_handoff(repo, output)["reused_files"] == []
    for source in ("\n\ndef run(): pass\n", "def renamed(): pass\n", None, "def run(): pass\n"):
        if source is None:
            (repo / "b.py").unlink()
        else:
            (repo / "b.py").write_text(source)
        incremental = export()
        assert calls(incremental) == {("app.py::caller", "b.py::run" if source and "def run" in source else "function::run")}
        assert "app.py" in check_handoff(repo, output)["reused_files"]
        fresh = RepoContentProcessor(repo, tmp_path / "fresh", enable_graph=True)
        fresh.process_repo()
        assert incremental.to_dict() == fresh.repo_graph.to_dict()
