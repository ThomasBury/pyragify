from pyragify.graph import GraphQuery
from pyragify.processor import FileProcessor


def test_python_call_hierarchy_uses_calling_function_node(tmp_path):
    sample_file = tmp_path / "a.py"
    sample_file.write_text(
        "def foo():\n"
        "    return 1\n"
        "\n"
        "def bar():\n"
        "    return foo()\n",
        encoding="utf-8",
    )

    processor = FileProcessor(tmp_path, tmp_path / "output", enable_graph=True)
    _, _, graph = processor.chunk_file(sample_file, include_graph=True)

    call_edges = [edge for edge in graph.edges if edge.type == "calls"]

    assert any(edge.source == "a.py::bar" and edge.target == "a.py::foo" for edge in call_edges)
    assert not any(edge.source == "file::a.py" and edge.target == "a.py::foo" for edge in call_edges)

    foo_hierarchy = GraphQuery(graph).get_call_hierarchy("foo")
    assert foo_hierarchy["callers"] == [{"name": "bar", "file": "a.py", "line": 5}]

    bar_hierarchy = GraphQuery(graph).get_call_hierarchy("bar")
    assert bar_hierarchy["callees"] == [{"name": "foo", "line": 5}]



def _build_graph(tmp_path, filename, source):
    sample_file = tmp_path / filename
    sample_file.write_text(source, encoding="utf-8")

    processor = FileProcessor(tmp_path, tmp_path / "output", enable_graph=True)
    _, _, graph = processor.chunk_file(sample_file, include_graph=True)
    return graph


def _assert_bar_calls_foo(graph, filename, call_line, scope=""):
    call_edges = [edge for edge in graph.edges if edge.type == "calls"]

    assert any(edge.source == f"{filename}::{scope}bar" and edge.target == f"{filename}::{scope}foo" for edge in call_edges)
    assert not any(edge.source == f"file::{filename}" and edge.target == f"{filename}::foo" for edge in call_edges)

    foo_hierarchy = GraphQuery(graph).get_call_hierarchy("foo")
    assert foo_hierarchy["callers"] == [{"name": "bar", "file": filename, "line": call_line}]

    bar_hierarchy = GraphQuery(graph).get_call_hierarchy("bar")
    assert bar_hierarchy["callees"] == [{"name": "foo", "line": call_line}]


def test_javascript_call_hierarchy_uses_calling_function_node(tmp_path):
    graph = _build_graph(
        tmp_path,
        "a.js",
        "function foo() {\n"
        "    return 1;\n"
        "}\n"
        "\n"
        "function bar() {\n"
        "    return foo();\n"
        "}\n",
    )

    _assert_bar_calls_foo(graph, "a.js", 6)


def test_typescript_call_hierarchy_uses_calling_function_node(tmp_path):
    graph = _build_graph(
        tmp_path,
        "a.ts",
        "function foo(): number {\n"
        "    return 1;\n"
        "}\n"
        "\n"
        "function bar(): number {\n"
        "    return foo();\n"
        "}\n",
    )

    _assert_bar_calls_foo(graph, "a.ts", 6)


def test_java_call_hierarchy_uses_calling_method_node(tmp_path):
    graph = _build_graph(
        tmp_path,
        "A.java",
        "public class A {\n"
        "    public static int foo() {\n"
        "        return 1;\n"
        "    }\n"
        "\n"
        "    public static int bar() {\n"
        "        return foo();\n"
        "    }\n"
        "}\n",
    )

    _assert_bar_calls_foo(graph, "A.java", 7, scope="A.")


def test_cpp_call_hierarchy_uses_calling_function_node(tmp_path):
    graph = _build_graph(
        tmp_path,
        "a.cpp",
        "int foo() {\n"
        "    return 1;\n"
        "}\n"
        "\n"
        "int bar() {\n"
        "    return foo();\n"
        "}\n",
    )

    _assert_bar_calls_foo(graph, "a.cpp", 6)
