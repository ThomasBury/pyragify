"""
Knowledge Graph module for Pyragify.

This module provides functionality to build and manage knowledge graphs
representing code relationships and dependencies.
"""

import ast
import json
import logging
import re
import warnings
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

# Tree-sitter imports (conditionally imported)
try:
    from tree_sitter import Language, Node, Parser
    from tree_sitter_languages import get_language, get_parser
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    # Define dummy types for type hinting if tree-sitter is not available
    class Language: pass
    class Node: pass
    class Parser: pass

logger = logging.getLogger(__name__)

FUNCTION_NODE_TYPES = {
    "function",
    "javascript_function",
    "javascript_arrow_function",
    "java_method",
    "cpp_function",
    "go_function",
}


def is_function_like_node(node: "GraphNode") -> bool:
    return node.type in FUNCTION_NODE_TYPES


def get_tree_sitter_language_and_parser(language_name: str) -> Tuple[Language, Parser]:
    if not TREE_SITTER_AVAILABLE:
        raise RuntimeError("tree-sitter support is not available")
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=r"Language\(path, name\) is deprecated.*",
            category=FutureWarning,
        )
        language = get_language(language_name)
        parser = get_parser(language_name)
    return language, parser


def tree_sitter_match_captures(query: Any, match: Any) -> Dict[str, Node]:
    if isinstance(match, tuple) and len(match) == 2 and isinstance(match[1], dict):
        return {
            name: nodes[0] if isinstance(nodes, list) else nodes
            for name, nodes in match[1].items()
        }
    return {query.capture_names[i]: node for i, node in match}


@dataclass
class GraphNode:
    """Represents a node in the knowledge graph (code entity)."""
    id: str
    type: str  # 'file', 'function', 'class', 'module', etc.
    file: str
    name: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    language: str = "unknown"
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert node to dictionary for serialization."""
        return asdict(self)


@dataclass
class GraphEdge:
    """Represents an edge in the knowledge graph (relationship)."""
    source: str  # Source node ID
    target: str  # Target node ID
    type: str    # 'imports', 'calls', 'inherits', 'references', etc.
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert edge to dictionary for serialization."""
        return asdict(self)


@dataclass
class KnowledgeGraph:
    """Represents the complete knowledge graph."""
    nodes: Dict[str, GraphNode]
    edges: List[GraphEdge]
    metadata: Dict[str, Any]

    def __init__(self):
        self.nodes = {}
        self.edges = []
        self._edge_signatures = set()
        self.metadata = {
            "version": "1.0",
            "created_at": None,
            "total_nodes": 0,
            "total_edges": 0,
            "languages": set()
        }

    @staticmethod
    def _edge_signature(edge: GraphEdge) -> str:
        """Create a stable signature for duplicate-edge detection."""
        signature = f"{edge.source}->{edge.target}:{edge.type}"
        if (edge.type == "calls" and edge.target.startswith(("function::", "method::"))
                and edge.metadata.get("import")):
            # Shared placeholders can represent different lexical import bindings.
            signature += ":" + json.dumps(edge.metadata["import"], sort_keys=True)
        return signature

    def add_node(self, node: GraphNode) -> None:
        """Add a node to the graph."""
        self.nodes[node.id] = node
        self.metadata["total_nodes"] = len(self.nodes)
        if node.language not in self.metadata["languages"]:
            self.metadata["languages"].add(node.language)

    def add_edge(self, edge: GraphEdge) -> None:
        """Add an edge to the graph."""
        signature = self._edge_signature(edge)
        if signature in self._edge_signatures:
            return
        self.edges.append(edge)
        self._edge_signatures.add(signature)
        self.metadata["total_edges"] = len(self.edges)

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        """Get a node by ID."""
        return self.nodes.get(node_id)

    def get_edges_for_node(self, node_id: str) -> List[GraphEdge]:
        """Get all edges connected to a node."""
        return [edge for edge in self.edges
                if edge.source == node_id or edge.target == node_id]

    def get_neighbors(self, node_id: str, edge_types: Optional[List[str]] = None) -> List[str]:
        """Get neighboring node IDs, optionally filtered by edge types."""
        neighbors = set()
        for edge in self.edges:
            if edge.source == node_id:
                if edge_types is None or edge.type in edge_types:
                    neighbors.add(edge.target)
            elif edge.target == node_id:
                if edge_types is None or edge.type in edge_types:
                    neighbors.add(edge.source)
        return list(neighbors)

    def to_dict(self) -> Dict[str, Any]:
        """Convert graph to dictionary for serialization."""
        # Convert sets to lists for JSON serialization
        metadata = {}
        for key, value in self.metadata.items():
            if isinstance(value, set):
                metadata[key] = list(value)
            else:
                metadata[key] = value

        return {
            "nodes": {node_id: node.to_dict() for node_id, node in self.nodes.items()},
            "edges": [edge.to_dict() for edge in self.edges],
            "metadata": metadata
        }

    def sync_metadata(self) -> None:
        """Refresh derived metadata after bulk graph mutations."""
        self._edge_signatures = {self._edge_signature(edge) for edge in self.edges}
        self.metadata["total_nodes"] = len(self.nodes)
        self.metadata["total_edges"] = len(self.edges)
        self.metadata["languages"] = {node.language for node in self.nodes.values()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KnowledgeGraph':
        """Create graph from dictionary (deserialization)."""
        if (not isinstance(data, dict)
                or not isinstance(data.get("nodes"), dict)
                or not isinstance(data.get("edges"), list)):
            raise ValueError("Graph must contain a nodes object and an edges list")
        graph = cls()
        graph.metadata = data.get("metadata", {}).copy()
        languages = graph.metadata.get("languages", set())
        if not isinstance(languages, set):
            graph.metadata["languages"] = set(languages or [])

        # Reconstruct nodes
        for node_id, node_data in data.get("nodes", {}).items():
            node = GraphNode(**node_data)
            graph.nodes[node_id] = node

        # Reconstruct edges
        for edge_data in data.get("edges", []):
            edge = GraphEdge(**edge_data)
            graph.edges.append(edge)

        graph.sync_metadata()
        return graph

    def merge(self, other: 'KnowledgeGraph') -> None:
        """Merge another graph into this one."""
        # Add nodes (overwrite if exists)
        for node_id, node in other.nodes.items():
            self.add_node(node)

        # Add edges
        for edge in other.edges:
            self.add_edge(edge)

        # Update metadata
        self.metadata["total_nodes"] = len(self.nodes)
        self.metadata["total_edges"] = len(self.edges)
        self.metadata["languages"].update(other.metadata.get("languages", set()))


class _PythonScope:
    """Bindings collected before resolving any calls in a lexical scope."""

    def __init__(self, node, parent=None):
        self.node = node
        self.parent = parent
        self.owner = parent.owner if parent else None
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            self.owner = node
        self.bindings = defaultdict(list)
        self.globals = set()
        self.nonlocals = set()
        self.wildcard_import = False

    def lookup(self, name):
        scope = self
        while scope:
            if scope.parent and (name in scope.globals or name in scope.nonlocals):
                # A write through a declaration has an uncertain callable value.
                if name in scope.bindings:
                    return None
                if name in scope.globals:
                    while scope.parent:
                        scope = scope.parent
                    continue
                scope = scope.parent
                while scope and isinstance(scope.node, ast.ClassDef):
                    scope = scope.parent
                continue
            if scope.wildcard_import:
                return None
            if name in scope.bindings:
                bindings = scope.bindings[name]
                return bindings[0] if len(bindings) == 1 else None
            scope = scope.parent
            while scope and isinstance(scope.node, ast.ClassDef):
                scope = scope.parent
        return None


class _PythonCallVisitor(ast.NodeVisitor):
    """Collect execution owners and lexical bindings, then resolve local calls."""

    def __init__(self, tree):
        self.scope = _PythonScope(tree)
        self.scopes = {tree: self.scope}
        self.calls = []
        self.visit(tree)

    def _body(self, node, body, arguments=None):
        parent = self.scope
        self.scope = self.scopes[node] = _PythonScope(node, parent)
        if arguments:
            parameters = arguments.posonlyargs + arguments.args + arguments.kwonlyargs
            parameters += [arg for arg in (arguments.vararg, arguments.kwarg) if arg]
            for arg in parameters:
                self.scope.bindings[arg.arg].append(arg)
                self.scopes[arg] = self.scope
        for child in body:
            self.visit(child)
        self.scope = parent

    def _defaults(self, node):
        for expression in node.args.defaults + node.args.kw_defaults:
            if expression is not None:
                self.visit(expression)

    def visit_FunctionDef(self, node):
        self.scope.bindings[node.name].append(node)
        for decorator in node.decorator_list:
            self.visit(decorator)
        self._defaults(node)
        for arg in node.args.posonlyargs + node.args.args + node.args.kwonlyargs + [node.args.vararg, node.args.kwarg]:
            if arg and arg.annotation:
                self.visit(arg.annotation)
        if node.returns:
            self.visit(node.returns)
        self._body(node, node.body, node.args)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node):
        self.scope.bindings[node.name].append(node)
        for expression in node.decorator_list + node.bases + [keyword.value for keyword in node.keywords]:
            self.visit(expression)
        self._body(node, node.body)

    def visit_Lambda(self, node):
        self._defaults(node)
        self._body(node, [node.body], node.args)

    def visit_ListComp(self, node):
        # The first iterable executes outside the comprehension's implicit scope.
        self.visit(node.generators[0].iter)
        parent = self.scope
        self.scope = self.scopes[node] = _PythonScope(node, parent)
        for index, generator in enumerate(node.generators):
            if index:
                self.visit(generator.iter)
            self.visit(generator.target)
            for condition in generator.ifs:
                self.visit(condition)
        if isinstance(node, ast.DictComp):
            self.visit(node.key)
            self.visit(node.value)
        else:
            self.visit(node.elt)
        self.scope = parent

    visit_SetComp = visit_ListComp
    visit_DictComp = visit_ListComp
    visit_GeneratorExp = visit_ListComp

    def visit_NamedExpr(self, node):
        scope = self.scope
        while isinstance(scope.node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            scope = scope.parent
        scope.bindings[node.target.id].append(node.target)
        self.visit(node.value)

    def visit_Name(self, node):
        if isinstance(node.ctx, (ast.Store, ast.Del)):
            self.scope.bindings[node.id].append(node)

    def visit_Import(self, node):
        self.scopes[node] = self.scope
        for alias in node.names:
            self.scope.bindings[alias.asname or alias.name.split(".")[0]].append(node)

    def visit_ImportFrom(self, node):
        self.scopes[node] = self.scope
        for alias in node.names:
            if alias.name == "*":
                self.scope.wildcard_import = True
            else:
                self.scope.bindings[alias.asname or alias.name].append(node)

    def visit_ExceptHandler(self, node):
        if node.name:
            self.scope.bindings[node.name].append(node)
        self.generic_visit(node)

    def visit_MatchAs(self, node):
        if node.name:
            self.scope.bindings[node.name].append(node)
        self.generic_visit(node)

    visit_MatchStar = visit_MatchAs

    def visit_MatchMapping(self, node):
        if node.rest:
            self.scope.bindings[node.rest].append(node)
        self.generic_visit(node)

    def visit_Global(self, node):
        self.scope.globals.update(node.names)

    def visit_Nonlocal(self, node):
        self.scope.nonlocals.update(node.names)

    def visit_Call(self, node):
        self.calls.append((node, self.scope))
        self.generic_visit(node)

    def definition(self, call, scope):
        if isinstance(call.func, ast.Name):
            binding = scope.lookup(call.func.id)
        elif isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name):
            receiver = call.func.value.id
            binding = scope.lookup(receiver)
            if isinstance(binding, ast.arg) and receiver in ("self", "cls"):
                method = self.scopes[binding]
                positional = method.node.args.posonlyargs + method.node.args.args
                binding = method.parent.node if positional and binding is positional[0] else None
            if not isinstance(binding, ast.ClassDef):
                return None
            members = self.scopes[binding].bindings.get(call.func.attr, [])
            binding = members[0] if len(members) == 1 else None
        else:
            return None
        return binding if isinstance(binding, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) else None

    def imported_call(self, parts, scope):
        binding = scope.lookup(parts[0])
        if not isinstance(binding, (ast.Import, ast.ImportFrom)):
            return None
        for alias in binding.names:
            name = alias.asname or (
                alias.name.split(".")[0] if isinstance(binding, ast.Import) else alias.name)
            if name != parts[0]:
                continue
            attributes = parts[1:]
            if isinstance(binding, ast.Import):
                prefix = alias.name.split(".")[1:] if not alias.asname else []
                if attributes[:len(prefix)] != prefix:
                    return None
                module, level, symbol = alias.name, 0, None
                attributes = attributes[len(prefix):]
            else:
                module, level, symbol = binding.module or "", binding.level, alias.name
            owner = self.scopes[binding].node
            return {
                "module": module, "level": level, "symbol": symbol,
                "attributes": attributes, "line": binding.lineno, "column": binding.col_offset,
                "scope": [owner.lineno, owner.col_offset] if not isinstance(owner, ast.Module) else None,
            }
        return None


def _python_module_files(file_nodes, file_path, module, level=0):
    """Match exact root/src module paths without selecting an ambiguous match."""
    if level:
        package = list(Path(file_path).parent.parts)
        if package[:1] == ["src"]:
            package = package[1:]
        if level > len(package):
            return set()
        module = ".".join(package[:len(package) - level + 1] + ([module] if module else []))
    path = module.replace(".", "/")
    return file_nodes.intersection({path + ".py", path + "/__init__.py",
                                    "src/" + path + ".py", "src/" + path + "/__init__.py"})


class _JavaScriptScope:
    """Lexical bindings; repeated declarations and writes have unknown values."""

    def __init__(self, parent=None, function=False):
        self.parent = parent
        self.function = function
        self.bindings = defaultdict(list)

    def binding_scope(self, name):
        scope = self
        while scope and name not in scope.bindings:
            scope = scope.parent
        return scope

    def lookup(self, name):
        scope = self.binding_scope(name)
        values = scope.bindings[name] if scope else []
        return values[0] if len(values) == 1 else None


class _JavaScriptAnalysis:
    """Use the same parser positions for symbols, execution owners, and bindings."""

    function_types = {"function_declaration", "generator_function_declaration",
                      "arrow_function", "function", "function_expression",
                      "generator_function", "method_definition"}
    class_types = {"class_declaration", "abstract_class_declaration", "class"}

    def __init__(self, root):
        self.chunks = []
        self.calls = []
        self.writes = []
        self._visit(root, _JavaScriptScope(function=True), None)
        for scope, name in self.writes:
            binding_scope = scope.binding_scope(name)
            if binding_scope:
                binding_scope.bindings[name].append(None)

    def _bind(self, node, scope, definition=None):
        if node is None:
            return
        if node.type in {"identifier", "type_identifier", "shorthand_property_identifier_pattern"}:
            scope.bindings[node.text.decode("utf-8")].append(definition)
        elif node.type in {"pair_pattern", "assignment_pattern", "object_assignment_pattern"}:
            self._bind(node.child_by_field_name("value" if node.type == "pair_pattern" else "left"), scope)
        elif node.type in {"required_parameter", "optional_parameter"}:
            self._bind(node.child_by_field_name("pattern"), scope)
        elif node.type in {"formal_parameters", "rest_pattern", "array_pattern", "object_pattern"}:
            for child in node.named_children:
                self._bind(child, scope)

    def _visit(self, node, scope, owner):
        is_function = node.type in self.function_types
        is_class = node.type in self.class_types
        name = node.child_by_field_name("name") if is_function or is_class else None
        if node.type in {"function_declaration", "generator_function_declaration",
                         "class_declaration", "abstract_class_declaration"}:
            self._bind(name, scope, node.start_byte if is_function else None)

        if is_function or is_class:
            if node.type == "arrow_function":
                parent = node.parent
                if parent.type == "variable_declarator" and parent.child_by_field_name("value") == node:
                    candidate = parent.child_by_field_name("name")
                    name = candidate if candidate.type == "identifier" else None
            symbol_name = name.text.decode("utf-8") if name else f"anonymous@{node.start_point[0] + 1}:{node.start_point[1]}"
            self.chunks.append({
                "type": "javascript_class" if is_class else (
                    "javascript_arrow_function" if node.type == "arrow_function" else "javascript_function"),
                "name": symbol_name, "code": node.text.decode("utf-8"),
                "start_line": node.start_point[0] + 1, "end_line": node.end_point[0] + 1,
                "metadata": {"start_byte": node.start_byte, "end_byte": node.end_byte,
                             "column": node.start_point[1], "parent_start_byte": owner},
            })
            owner = node.start_byte
            scope = _JavaScriptScope(scope, function=is_function)
            if node.type in {"function", "function_expression", "generator_function", "class"}:
                self._bind(name, scope, node.start_byte if is_function else None)
            if is_function:
                self._bind(node.child_by_field_name("parameters") or node.child_by_field_name("parameter"), scope)
        elif node.type in {"statement_block", "for_statement", "for_in_statement", "catch_clause", "switch_body"}:
            scope = _JavaScriptScope(scope)

        if node.type == "variable_declarator":
            binding_scope = scope
            if node.parent.type == "variable_declaration":  # var belongs to the function, not its block.
                while not binding_scope.function:
                    binding_scope = binding_scope.parent
            value = node.child_by_field_name("value")
            self._bind(node.child_by_field_name("name"), binding_scope,
                       value.start_byte if value and value.type == "arrow_function" else None)
        elif node.type in {"internal_module", "module"}:
            self._bind(node.child_by_field_name("name"), scope)
            scope = _JavaScriptScope(scope, function=True)
        elif node.type == "enum_declaration":
            self._bind(node.child_by_field_name("name"), scope)
        elif node.type == "function_signature":
            self._bind(node.child_by_field_name("name"), scope)
            return
        elif node.type == "catch_clause":
            self._bind(node.child_by_field_name("parameter"), scope)
        elif node.type == "for_in_statement":
            left = node.child_by_field_name("left")
            kind = node.child_by_field_name("kind")
            if kind:
                binding_scope = scope
                if kind.type == "var":
                    while not binding_scope.function:
                        binding_scope = binding_scope.parent
                self._bind(left, binding_scope)
            else:
                self._write(left, scope)
        elif node.type in {"assignment_expression", "augmented_assignment_expression", "update_expression"}:
            self._write(node.child_by_field_name("left") or node.child_by_field_name("argument"), scope)
        elif node.type == "import_specifier":
            self._bind(node.child_by_field_name("alias") or node.child_by_field_name("name"), scope)
            return
        elif node.type in {"import_clause", "namespace_import", "import_require_clause"}:
            for child in node.named_children:
                if child.type == "identifier":
                    self._bind(child, scope)
        elif node.type == "call_expression":
            function = node.child_by_field_name("function")
            if function and function.type == "identifier":
                self.calls.append((function, scope, owner))

        for child in node.named_children:
            self._visit(child, scope, owner)

    def _write(self, node, scope):
        # Reuse pattern binding rules without treating a write as a new declaration.
        bindings = _JavaScriptScope()
        self._bind(node, bindings)
        self.writes.extend((scope, name) for name in bindings.bindings)


class GraphBuilder:
    """
    Builder class for constructing knowledge graphs from code analysis.

    This class coordinates the extraction of dependencies and relationships
    from various programming languages and builds a unified knowledge graph.
    """

    def __init__(self, repo_path: Path):
        self.repo_path = repo_path.resolve()
        self.graph = KnowledgeGraph()
        self.file_nodes: Dict[str, GraphNode] = {}
        self.logger = logging.getLogger(__name__)

    def build_from_chunks(self, file_path: Path, chunks: List[Dict[str, Any]],
                         language: str) -> KnowledgeGraph:
        """
        Build graph from file chunks and their dependencies.

        Parameters
        ----------
        file_path : Path
            Path to the file being processed
        chunks : List[Dict[str, Any]]
            List of code chunks from the file
        language : str
            Programming language of the file

        Returns
        -------
        KnowledgeGraph
            The constructed knowledge graph for this file
        """
        file_graph = KnowledgeGraph()
        relative_path = self._relative_path(file_path)

        # Create file node
        file_node = GraphNode(
            id=self._file_node_id(relative_path),
            type="file",
            file=relative_path,
            name=file_path.name,
            language=language,
            metadata={"size": file_path.stat().st_size}
        )
        file_graph.add_node(file_node)
        self.file_nodes[relative_path] = file_node

        # Process chunks and extract entities
        for chunk in sorted(chunks, key=lambda item: (item.get("start_line") or 0,
                                                    item.get("metadata", {}).get("start_byte", 0))):
            self._process_chunk(chunk, relative_path, language, file_graph)

        return file_graph

    def _relative_path(self, file_path: Path) -> str:
        """Return a repository-relative path string."""
        return str(file_path.relative_to(self.repo_path))

    def _file_node_id(self, file_path: Union[Path, str]) -> str:
        """Build a stable file node identifier from a repo-relative path."""
        relative_path = file_path if isinstance(file_path, str) else self._relative_path(file_path)
        return f"file::{relative_path}"

    def _lookup_local_node_id(self, graph: KnowledgeGraph, symbol_name: str,
                              scope: str = "", skip_classes: bool = False) -> Optional[str]:
        """Resolve only an unambiguous definition in an enclosing scope."""
        while True:
            qualified = f"{scope}.{symbol_name}" if scope else symbol_name
            matches = [node.id for node in graph.nodes.values()
                       if node.file != "<external>" and node.type != "file"
                       and node.metadata.get("qualified_name", node.name) == qualified]
            if skip_classes and any(node.type == "class" and node.language == "python"
                                    and node.metadata.get("qualified_name") == scope
                                    for node in graph.nodes.values()):
                matches = []
            if matches:
                return matches[0] if len(matches) == 1 else None
            if not scope:
                return None
            scope = scope.rpartition(".")[0]

    def _normalize_reference_id(self, graph: KnowledgeGraph, file_path: Path,
                                node_id: str, line: Optional[int] = None) -> str:
        """Map references to scoped definitions, leaving unknown receivers unresolved."""
        if node_id.startswith("file::"):
            return self._file_node_id(file_path)
        if not node_id.startswith(("function::", "class::", "struct::", "method::")):
            return node_id
        enclosing = self._find_enclosing_node_id(graph, file_path, line)
        scope = graph.nodes[enclosing].metadata.get("qualified_name", "") if enclosing else ""
        symbol = node_id.split("::", 1)[1]
        if node_id.startswith("method::") and "." in symbol:
            receiver, _, name = symbol.rpartition(".")
            if receiver in ("self", "cls", "this"):
                scope = scope.rpartition(".")[0]
                symbol = name
            else:
                scope = ""
        return self._lookup_local_node_id(
            graph, symbol, scope, skip_classes=not node_id.startswith("method::")) or node_id

    def _find_enclosing_node_id(
        self, graph: KnowledgeGraph, file_path: Path, line: Optional[int],
        node_types: Set[str] = FUNCTION_NODE_TYPES,
    ) -> Optional[str]:
        """Find the smallest node of the requested types covering a source line."""
        if line is None:
            return None

        relative_path = self._relative_path(file_path)
        candidates = []
        for node_id, node in graph.nodes.items():
            if node.type not in node_types or node.file != relative_path:
                continue
            if node.line_start is None or node.line_end is None:
                continue
            if node.line_start <= line <= node.line_end:
                span = node.line_end - node.line_start
                candidates.append((span, -node.line_start, node_id))

        if not candidates:
            return None
        return min(candidates)[2]

    def _ensure_reference_node(self, graph: KnowledgeGraph, node_id: str, language: str) -> None:
        """Create a placeholder node for an external reference when needed."""
        if node_id in graph.nodes:
            return

        node_type = "reference"
        name = node_id
        file_name = "<external>"

        if "::" in node_id:
            prefix, remainder = node_id.split("::", 1)
            node_type = prefix
            name = remainder
            if prefix == "file":
                file_name = remainder
                name = Path(remainder).name
            elif prefix == "method":
                name = remainder.split(".")[-1]

        graph.add_node(
            GraphNode(
                id=node_id,
                type=node_type,
                file=file_name,
                name=name,
                language=language if node_type == "file" else "unknown",
                metadata={"external": file_name == "<external>"},
            )
        )

    def add_dependency_edges(
        self,
        graph: KnowledgeGraph,
        file_path: Path,
        language: str,
        dependencies: List[GraphEdge],
    ) -> None:
        """Normalize dependency endpoints, materialize missing nodes, and add edges."""
        file_node_id = self._file_node_id(file_path)
        python_definitions = {
            (node.line_start, node.metadata.get("column")): node.id
            for node in graph.nodes.values()
            if node.language == "python" and node.type in {"function", "class"}
        }
        javascript_definitions = {
            node.metadata["start_byte"]: node.id for node in graph.nodes.values()
            if node.language in {"javascript", "typescript"} and "start_byte" in node.metadata
        }
        for edge in dependencies:
            line = edge.metadata.get("line")
            if language == "python" and edge.type == "calls":
                owner = edge.metadata["owner"]
                definition = edge.metadata["definition"]
                source = python_definitions.get(tuple(owner), file_node_id) if owner else file_node_id
                target = python_definitions.get(tuple(definition), edge.target) if definition else edge.target
            elif language in {"javascript", "typescript"} and edge.type == "calls":
                source = javascript_definitions.get(edge.metadata.get("owner"), file_node_id)
                target = javascript_definitions.get(edge.metadata.get("definition"), edge.target)
            else:
                source = self._normalize_reference_id(graph, file_path, edge.source, line)
                target = self._normalize_reference_id(graph, file_path, edge.target, line)
                if edge.type == "calls":
                    source = self._find_enclosing_node_id(graph, file_path, line) or file_node_id
            if edge.type == "inherits":
                subclass = self._find_enclosing_node_id(
                    graph, file_path, line, {"class", "java_class", "javascript_class", "cpp_class"})
                if subclass:
                    source = subclass
                    scope = graph.nodes[subclass].metadata["qualified_name"].rpartition(".")[0]
                    symbol = edge.target.split("::", 1)[-1]
                    target = self._lookup_local_node_id(graph, symbol, scope) or target

            edge.source = source
            edge.target = target
            self._ensure_reference_node(graph, edge.source, language)
            self._ensure_reference_node(graph, edge.target, language)
            graph.add_edge(edge)

    def _process_chunk(self, chunk: Dict[str, Any], file_path: str,
                      language: str, graph: KnowledgeGraph) -> None:
        """Process a single chunk and extract entities and relationships."""
        chunk_type = chunk.get("type", "")
        name = chunk.get("name", "")
        start_line = chunk.get("start_line")
        end_line = chunk.get("end_line")

        containers = [node for node in graph.nodes.values()
                      if node.line_start is not None and start_line is not None
                      and node.line_end is not None and end_line is not None
                      and node.line_start < start_line and node.line_end >= end_line
                      and (is_function_like_node(node) or node.type in
                           {"class", "javascript_class", "java_class", "cpp_class", "cpp_struct"})]
        parent = min(containers, key=lambda node: node.line_end - node.line_start) if containers else None
        if language in {"javascript", "typescript"} and "parent_start_byte" in chunk.get("metadata", {}):
            parent_position = chunk["metadata"]["parent_start_byte"]
            parent = next((node for node in graph.nodes.values()
                           if node.metadata.get("start_byte") == parent_position), None) if parent_position is not None else None
        qualified = f"{parent.metadata['qualified_name']}.{name}" if parent else name
        metadata = dict(chunk.get("metadata", {}), qualified_name=qualified)

        # Create node ID
        if chunk_type == "file":
            node_id = f"{file_path}::__file_content__"
            if not name:
                name = Path(file_path).name
        else:
            node_id = f"{file_path}::{qualified}" if name else f"{file_path}::{chunk_type}_{start_line}"
            base_id = node_id
            counter = 1
            while node_id in graph.nodes:
                node_id = f"{base_id}@{start_line}#{counter}"
                counter += 1

        # Create node
        node = GraphNode(
            id=node_id,
            type=chunk_type,
            file=file_path,
            name=name,
            line_start=start_line,
            line_end=end_line,
            language=language,
            metadata=metadata
        )
        graph.add_node(node)

        # Create relationship to file
        file_node_id = self._file_node_id(file_path)
        graph.add_edge(GraphEdge(
            source=file_node_id,
            target=node_id,
            type="contains",
            metadata={"line_start": start_line, "line_end": end_line}
        ))

    def extract_dependencies(self, file_path: Path, content: str,
                           language: str) -> List[GraphEdge]:
        """
        Extract dependencies from file content.

        This is a placeholder method that should be implemented
        with language-specific dependency extraction logic.
        """
        # Placeholder implementation - will be expanded in Phase 2
        dependencies = []

        if language == "python":
            dependencies.extend(self._extract_python_dependencies(content, file_path))
        elif language in ["javascript", "typescript"]:
            dependencies.extend(self._extract_js_dependencies(content, file_path))
        elif language == "java":
            dependencies.extend(self._extract_java_dependencies(content, file_path))
        elif language in ["c", "cpp"]:
            dependencies.extend(self._extract_cpp_dependencies(content, file_path))
        # Add other languages as implemented

        return dependencies

    def _extract_cpp_dependencies(self, content: str, file_path: Path) -> List[GraphEdge]:
        """Extract C/C++ dependencies using tree-sitter."""
        edges = []
        file_id = self._file_node_id(file_path)

        try:
            if TREE_SITTER_AVAILABLE:

                language_name = "cpp" if file_path.suffix == ".cpp" else "c"
                language, parser = get_tree_sitter_language_and_parser(language_name)
                tree = parser.parse(bytes(content, "utf8"))
                root_node = tree.root_node

                # Extract include statements
                include_query = """
                (preproc_include
                  path: [(string_literal) (system_lib_string)] @include_path
                )
                """

                # Extract function calls
                call_query = """
                (call_expression
                  function: (identifier) @function_name
                )
                """

                # Extract struct/class declarations
                struct_query = """
                (struct_specifier
                  name: (type_identifier) @struct_name
                )
                """

                class_query = """
                (class_specifier
                  name: (type_identifier) @class_name
                )
                """

                for query_str, query_type in [
                    (include_query, "include"),
                    (call_query, "call"),
                    (struct_query, "struct"),
                    (class_query, "class")
                ]:
                    try:
                        query = language.query(query_str)
                        for match in query.matches(root_node):
                            captures = tree_sitter_match_captures(query, match)
                            self._process_cpp_captures(captures, query_type, file_id, edges, content)
                    except Exception as e:
                        logger.debug(f"Tree-sitter query failed for C/C++ {query_type}: {e}")

            # Fallback to regex for basic include detection
            if not edges:
                self._extract_cpp_regex_fallback(content, file_id, edges)

        except Exception as e:
            logger.warning(f"Error extracting C/C++ dependencies from {file_path}: {e}")

        return edges

    def _process_cpp_captures(self, captures: Dict[str, Any], query_type: str,
                            file_id: str, edges: List[GraphEdge], content: str) -> None:
        """Process tree-sitter captures for C/C++."""
        if query_type == "include" and "include_path" in captures:
            include_path = captures["include_path"].text.decode("utf-8").strip('<>"')
            edges.append(GraphEdge(
                source=file_id,
                target=f"header::{include_path}",
                type="includes",
                metadata={"line": captures["include_path"].start_point[0] + 1}
            ))
        elif query_type == "call" and "function_name" in captures:
            func_name = captures["function_name"].text.decode("utf-8")
            edges.append(GraphEdge(
                source=file_id,
                target=f"function::{func_name}",
                type="calls",
                metadata={"line": captures["function_name"].start_point[0] + 1}
            ))
        elif query_type == "struct" and "struct_name" in captures:
            struct_name = captures["struct_name"].text.decode("utf-8")
            # Note: C/C++ doesn't have inheritance for structs, but we can track them
            edges.append(GraphEdge(
                source=file_id,
                target=f"struct::{struct_name}",
                type="defines",
                metadata={"line": captures["struct_name"].start_point[0] + 1}
            ))
        elif query_type == "class" and "class_name" in captures:
            class_name = captures["class_name"].text.decode("utf-8")
            edges.append(GraphEdge(
                source=file_id,
                target=f"class::{class_name}",
                type="defines",
                metadata={"line": captures["class_name"].start_point[0] + 1}
            ))

    def _extract_cpp_regex_fallback(self, content: str, file_id: str, edges: List[GraphEdge]) -> None:
        """Fallback regex-based extraction for C/C++."""
        import re

        # Extract #include statements
        include_pattern = r'#include\s*[<"]([^>"]+)[>"]'
        for match in re.finditer(include_pattern, content):
            include_path = match.group(1)
            edges.append(GraphEdge(
                source=file_id,
                target=f"header::{include_path}",
                type="includes",
                metadata={"line": content[:match.start()].count('\n') + 1}
            ))

    def _extract_java_dependencies(self, content: str, file_path: Path) -> List[GraphEdge]:
        """Extract Java dependencies using tree-sitter."""
        edges = []
        file_id = self._file_node_id(file_path)

        try:
            if TREE_SITTER_AVAILABLE:

                language, parser = get_tree_sitter_language_and_parser("java")
                tree = parser.parse(bytes(content, "utf8"))
                root_node = tree.root_node

                # Extract import statements
                import_query = """
                (import_declaration
                  (scoped_identifier) @import_path
                )
                """

                # Extract method calls
                method_call_query = """
                (method_invocation
                  name: (identifier) @method_name
                )
                """

                # Extract class declarations and inheritance
                class_query = """
                (class_declaration
                  name: (identifier) @class_name
                  superclass: (superclass
                    (type_identifier) @parent_class
                  )?
                )
                """

                for query_str, query_type in [
                    (import_query, "import"),
                    (method_call_query, "method_call"),
                    (class_query, "class")
                ]:
                    try:
                        query = language.query(query_str)
                        for match in query.matches(root_node):
                            captures = tree_sitter_match_captures(query, match)
                            self._process_java_captures(captures, query_type, file_id, edges, content)
                    except Exception as e:
                        logger.debug(f"Tree-sitter query failed for Java {query_type}: {e}")

            # Fallback to regex for basic import detection
            if not edges:
                self._extract_java_regex_fallback(content, file_id, edges)

        except Exception as e:
            logger.warning(f"Error extracting Java dependencies from {file_path}: {e}")

        return edges

    def _process_java_captures(self, captures: Dict[str, Any], query_type: str,
                             file_id: str, edges: List[GraphEdge], content: str) -> None:
        """Process tree-sitter captures for Java."""
        if query_type == "import" and "import_path" in captures:
            import_path = captures["import_path"].text.decode("utf-8")
            edges.append(GraphEdge(
                source=file_id,
                target=f"package::{import_path}",
                type="imports",
                metadata={"line": captures["import_path"].start_point[0] + 1}
            ))
        elif query_type == "method_call" and "method_name" in captures:
            method_name = captures["method_name"].text.decode("utf-8")
            edges.append(GraphEdge(
                source=file_id,
                target=f"method::{method_name}",
                type="calls",
                metadata={"line": captures["method_name"].start_point[0] + 1}
            ))
        elif query_type == "class" and "class_name" in captures:
            class_name = captures["class_name"].text.decode("utf-8")
            if "parent_class" in captures:
                parent_name = captures["parent_class"].text.decode("utf-8")
                edges.append(GraphEdge(
                    source=file_id,
                    target=f"class::{parent_name}",
                    type="inherits",
                    metadata={"line": captures["class_name"].start_point[0] + 1}
                ))

    def _extract_java_regex_fallback(self, content: str, file_id: str, edges: List[GraphEdge]) -> None:
        """Fallback regex-based extraction for Java."""
        import re

        # Extract import statements
        import_pattern = r'import\s+([^\s;]+);'
        for match in re.finditer(import_pattern, content):
            import_path = match.group(1)
            edges.append(GraphEdge(
                source=file_id,
                target=f"package::{import_path}",
                type="imports",
                metadata={"line": content[:match.start()].count('\n') + 1}
            ))

    def _extract_python_dependencies(self, content: str, file_path: Path) -> List[GraphEdge]:
        """Extract Python-specific dependencies using AST."""
        edges = []
        try:
            tree = ast.parse(content, filename=str(file_path))
            file_id = self._file_node_id(file_path)

            # Extract imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module_name = alias.name
                        edges.append(GraphEdge(
                            source=file_id,
                            target=f"module::{module_name}",
                            type="imports",
                            metadata={"line": node.lineno, "alias": alias.asname}
                        ))
                elif isinstance(node, ast.ImportFrom):
                    module_name = "." * node.level + (node.module or "")
                    for alias in node.names:
                        edges.append(GraphEdge(
                            source=file_id,
                            target=f"module::{module_name}.{alias.name}",
                            type="imports",
                            metadata={"line": node.lineno, "alias": alias.asname,
                                      "module": node.module or "", "level": node.level,
                                      "symbol": alias.name}
                        ))

            visitor = _PythonCallVisitor(tree)
            file_node = self.file_nodes.get(self._relative_path(file_path))
            if file_node:
                bindings = visitor.scope.bindings
                file_node.metadata["python_bindings"] = {
                    name: [nodes[0].lineno, nodes[0].col_offset]
                    if len(nodes) == 1 and isinstance(nodes[0], (ast.FunctionDef, ast.AsyncFunctionDef))
                    and not visitor.scope.wildcard_import else None
                    for name, nodes in bindings.items()
                }
                if visitor.scope.wildcard_import:
                    file_node.metadata["python_bindings"]["*"] = None
            for call, scope in visitor.calls:
                expression = call.func
                parts = []
                while isinstance(expression, ast.Attribute):
                    parts.insert(0, expression.attr)
                    expression = expression.value
                if not isinstance(expression, ast.Name):
                    continue
                parts.insert(0, expression.id)
                target = ("function::" if len(parts) == 1 else "method::") + ".".join(parts)
                definition = visitor.definition(call, scope)
                imported = visitor.imported_call(parts, scope)
                edges.append(GraphEdge(
                    source=file_id,
                    target=target,
                    type="calls",
                    metadata={
                        "line": call.lineno, "column": call.col_offset,
                        "end_line": call.end_lineno, "end_column": call.end_col_offset,
                        "owner": [scope.owner.lineno, scope.owner.col_offset] if scope.owner else None,
                        "definition": [definition.lineno, definition.col_offset] if definition else None,
                        "import": imported,
                        "unresolved_target": target,
                    },
                ))

            # Extract class inheritance
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            edges.append(GraphEdge(
                                source=file_id,
                                target=f"class::{base.id}",
                                type="inherits",
                                metadata={"line": node.lineno}
                            ))

        except SyntaxError as e:
            logger.warning(f"Syntax error in {file_path}: {e}")
        except Exception as e:
            logger.warning(f"Error extracting Python dependencies from {file_path}: {e}")

        return edges

    def _extract_js_dependencies(self, content: str, file_path: Path) -> List[GraphEdge]:
        """Extract JavaScript/TypeScript dependencies using tree-sitter."""
        edges = []
        file_id = self._file_node_id(file_path)

        try:
            # Try tree-sitter parsing first
            if TREE_SITTER_AVAILABLE:

                language_name = "typescript" if file_path.suffix == ".ts" else "javascript"
                language, parser = get_tree_sitter_language_and_parser(language_name)
                tree = parser.parse(bytes(content, "utf8"))
                root_node = tree.root_node

                # Extract import statements
                import_query = """
                (import_statement source: (string) @source) @statement
                """

                # Extract require statements
                require_query = """
                (call_expression
                  function: (identifier) @require
                  arguments: (arguments (string) @module)
                  (#eq? @require "require")
                )
                """

                analysis = _JavaScriptAnalysis(root_node)
                for function, scope, owner in analysis.calls:
                    name = function.text.decode("utf-8")
                    edges.append(GraphEdge(
                        source=file_id, target=f"function::{name}", type="calls",
                        metadata={"line": function.start_point[0] + 1, "column": function.start_point[1],
                                  "owner": owner, "definition": scope.lookup(name)},
                    ))

                # Extract class declarations and inheritance
                class_query = """
                (class_declaration
                  name: (identifier) @class_name
                  heritage_clause: (heritage_clause
                    (extends_clause
                      (identifier) @parent_class
                    )
                  )?
                )
                """

                for query_str, query_type in [
                    (import_query, "import"),
                    (require_query, "require"),
                    (class_query, "class")
                ]:
                    try:
                        query = language.query(query_str)
                        for match in query.matches(root_node):
                            captures = tree_sitter_match_captures(query, match)
                            self._process_js_captures(captures, query_type, file_id, edges, content)
                    except Exception as e:
                        logger.debug(f"Tree-sitter query failed for {query_type}: {e}")

            # Fallback to regex for basic import detection
            if not edges:
                self._extract_js_regex_fallback(content, file_id, edges)

        except Exception as e:
            logger.warning(f"Error extracting JS dependencies from {file_path}: {e}")

        return edges

    def _process_js_captures(self, captures: Dict[str, Any], query_type: str,
                           file_id: str, edges: List[GraphEdge], content: str) -> None:
        """Process tree-sitter captures for JavaScript/TypeScript."""
        if query_type == "import" and "source" in captures:
            source = captures["source"].text.decode("utf-8").strip('"\'')
            edges.append(GraphEdge(
                source=file_id,
                target=f"module::{source}",
                type="imports",
                metadata={"line": captures["source"].start_point[0] + 1,
                          "statement": captures["statement"].text.decode("utf-8")}
            ))
        elif query_type == "require" and "module" in captures:
            module_name = captures["module"].text.decode("utf-8").strip('"\'')
            edges.append(GraphEdge(
                source=file_id,
                target=f"module::{module_name}",
                type="imports",
                metadata={"line": captures["module"].start_point[0] + 1}
            ))
        elif query_type == "class" and "class_name" in captures:
            if "parent_class" in captures:
                parent_name = captures["parent_class"].text.decode("utf-8")
                edges.append(GraphEdge(
                    source=file_id,
                    target=f"class::{parent_name}",
                    type="inherits",
                    metadata={"line": captures["class_name"].start_point[0] + 1}
                ))

    def _extract_js_regex_fallback(self, content: str, file_id: str, edges: List[GraphEdge]) -> None:
        """Fallback regex-based extraction for JavaScript/TypeScript."""
        import re

        # Extract ES6 imports
        import_pattern = r'import\s+{[^}]*}|\s*from\s+[\'"]([^\'"]+)[\'"]'
        for match in re.finditer(import_pattern, content):
            if match.group(1):
                module_name = match.group(1)
                edges.append(GraphEdge(
                    source=file_id,
                    target=f"module::{module_name}",
                    type="imports",
                    metadata={"line": content[:match.start()].count('\n') + 1}
                ))

        # Extract CommonJS requires
        require_pattern = r'require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)'
        for match in re.finditer(require_pattern, content):
            module_name = match.group(1)
            edges.append(GraphEdge(
                source=file_id,
                target=f"module::{module_name}",
                type="imports",
                metadata={"line": content[:match.start()].count('\n') + 1}
            ))

    def save_graph(self, output_path: Path) -> None:
        """Save the knowledge graph to a JSON file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.graph.to_dict(), f, indent=2, ensure_ascii=False)

        self.logger.info(f"Saved knowledge graph to {output_path}")

    def load_graph(self, input_path: Path) -> KnowledgeGraph:
        """Load a knowledge graph from a JSON file."""
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.graph = KnowledgeGraph.from_dict(data)
        self.logger.info(f"Loaded knowledge graph from {input_path}")
        return self.graph

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the knowledge graph."""
        return {
            "total_nodes": len(self.graph.nodes),
            "total_edges": len(self.graph.edges),
            "node_types": self._count_node_types(),
            "edge_types": self._count_edge_types(),
            "languages": list(self.graph.metadata["languages"])
        }

    def _count_node_types(self) -> Dict[str, int]:
        """Count nodes by type."""
        counts = defaultdict(int)
        for node in self.graph.nodes.values():
            counts[node.type] += 1
        return dict(counts)

    def _count_edge_types(self) -> Dict[str, int]:
        """Count edges by type."""
        counts = defaultdict(int)
        for edge in self.graph.edges:
            counts[edge.type] += 1
        return dict(counts)

    def resolve_cross_file_references(self, all_file_graphs: List[KnowledgeGraph]) -> None:
        """
        Resolve cross-file references and add them to the repository graph.

        This method analyzes all file graphs to find references between files
        and adds appropriate cross-file edges to the repository graph.

        Parameters
        ----------
        all_file_graphs : List[KnowledgeGraph]
            List of all file graphs to analyze for cross-references
        """
        query = GraphQuery(self.graph)
        self._resolve_python_calls()
        file_nodes = {node.file for node in self.graph.nodes.values() if node.type == "file"}
        imports = defaultdict(list)
        for edge in self.graph.edges:
            if edge.type in {"imports", "includes"}:
                imports[edge.source].append(edge)
        for file_graph in all_file_graphs:
            for node in file_graph.nodes.values():
                if node.type == "file":
                    for dependency in query._dependencies_for_file(
                            node.file, file_nodes, imports.get(f"file::{node.file}", ())):
                        if dependency != node.file:
                            self.graph.add_edge(GraphEdge(
                                source=node.id, target=self._file_node_id(dependency),
                                type="cross_file_reference", metadata={"reference_type": "imports"}))

    def _resolve_python_calls(self) -> None:
        """Retarget calls individually using their serialized lexical import evidence."""
        files = {node.file for node in self.graph.nodes.values() if node.type == "file"}
        definitions = {
            (node.file, node.line_start, node.metadata.get("column")): node.id
            for node in self.graph.nodes.values() if node.language == "python" and node.type == "function"
        }
        previous_targets = set()
        edges = self.graph.edges
        self.graph.edges = []
        self.graph.sync_metadata()
        for edge in edges:
            imported = edge.metadata.get("import") if edge.type == "calls" else None
            if imported:
                source_file = self.graph.nodes[edge.source].file
                module, symbol = imported["module"], imported["symbol"]
                attributes = imported["attributes"]
                if symbol and attributes:
                    parents = _python_module_files(files, source_file, module, imported["level"])
                    bindings = {}
                    if len(parents) == 1:
                        parent = self.graph.nodes["file::" + next(iter(parents))]
                        bindings = parent.metadata.get("python_bindings", {})
                    if len(parents) > 1 or symbol in bindings or "*" in bindings:
                        matches = set()
                    else:
                        child_module = ".".join(filter(None, (module, symbol)))
                        matches = _python_module_files(files, source_file, child_module, imported["level"])
                else:
                    matches = _python_module_files(files, source_file, module, imported["level"])
                    if symbol:
                        attributes = [symbol]
                target = edge.metadata["unresolved_target"]
                if len(matches) == 1 and len(attributes) == 1:
                    path = next(iter(matches))
                    position = self.graph.nodes["file::" + path].metadata.get("python_bindings", {}).get(attributes[0])
                    if position:
                        target = definitions.get((path, *position), target)
                previous_targets.update((edge.target, edge.metadata["unresolved_target"]))
                edge = GraphEdge(edge.source, target, edge.type, edge.metadata.copy())
                self._ensure_reference_node(self.graph, target, "python")
            self.graph.add_edge(edge)
        connected = {endpoint for edge in self.graph.edges for endpoint in (edge.source, edge.target)}
        for target in previous_targets - connected:
            if self.graph.nodes.get(target) and self.graph.nodes[target].metadata.get("external"):
                del self.graph.nodes[target]
        self.graph.sync_metadata()

    def validate_graph(self) -> Dict[str, Any]:
        """
        Validate the knowledge graph for consistency and integrity.

        Returns
        -------
        Dict[str, Any]
            Validation results with errors, warnings, and statistics
        """
        validation_results = {
            "errors": [],
            "warnings": [],
            "statistics": self.get_statistics(),
            "is_valid": True
        }

        # Check for orphaned edges (edges referencing non-existent nodes)
        node_ids = set(self.graph.nodes.keys())
        for edge in self.graph.edges:
            if edge.source not in node_ids:
                validation_results["errors"].append(f"Edge source '{edge.source}' does not exist in nodes")
                validation_results["is_valid"] = False
            if edge.target not in node_ids:
                validation_results["errors"].append(f"Edge target '{edge.target}' does not exist in nodes")
                validation_results["is_valid"] = False

        # Check for duplicate edges
        edge_signatures = set()
        for edge in self.graph.edges:
            signature = self.graph._edge_signature(edge)
            if signature in edge_signatures:
                validation_results["warnings"].append(f"Duplicate edge: {signature}")
            else:
                edge_signatures.add(signature)

        # Check for nodes without required fields
        for node_id, node in self.graph.nodes.items():
            if not node.name:
                validation_results["warnings"].append(f"Node '{node_id}' has empty name")
            if not node.type:
                validation_results["errors"].append(f"Node '{node_id}' has empty type")
                validation_results["is_valid"] = False

        # Check for isolated nodes (nodes with no edges)
        connected_nodes = set()
        for edge in self.graph.edges:
            connected_nodes.add(edge.source)
            connected_nodes.add(edge.target)

        isolated_nodes = set(self.graph.nodes.keys()) - connected_nodes
        if isolated_nodes:
            validation_results["warnings"].append(f"Found {len(isolated_nodes)} isolated nodes")

        # Validate edge types
        valid_edge_types = {"imports", "calls", "inherits", "references", "contains",
                          "includes", "defines", "cross_file_reference"}
        for edge in self.graph.edges:
            if edge.type not in valid_edge_types:
                validation_results["warnings"].append(f"Unknown edge type: '{edge.type}'")

        logger.info(f"Graph validation completed: {len(validation_results['errors'])} errors, "
                   f"{len(validation_results['warnings'])} warnings")

        return validation_results

    def repair_graph(self, validation_results: Dict[str, Any]) -> None:
        """
        Attempt to repair common graph issues found during validation.

        Parameters
        ----------
        validation_results : Dict[str, Any]
            Results from validate_graph() method
        """
        repairs_made = 0

        # Remove edges with non-existent nodes
        valid_edges = []
        node_ids = set(self.graph.nodes.keys())

        for edge in self.graph.edges:
            if edge.source in node_ids and edge.target in node_ids:
                valid_edges.append(edge)
            else:
                repairs_made += 1
                logger.debug(f"Removed invalid edge: {edge.source} -> {edge.target}")

        self.graph.edges = valid_edges

        # Remove duplicate edges (keep first occurrence)
        seen_signatures = set()
        deduplicated_edges = []

        for edge in self.graph.edges:
            signature = self.graph._edge_signature(edge)
            if signature not in seen_signatures:
                seen_signatures.add(signature)
                deduplicated_edges.append(edge)
            else:
                repairs_made += 1

        self.graph.edges = deduplicated_edges
        self.graph.sync_metadata()

        if repairs_made > 0:
            logger.info(f"Graph repair completed: {repairs_made} issues fixed")
        else:
            logger.info("Graph repair completed: no issues found")


@dataclass
class ContextChunk:
    """Represents a chunk of context retrieved from the knowledge graph."""
    node: GraphNode
    relevance_score: float
    relationship_path: List[str]
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class GraphQuery:
    """
    Query interface for retrieving context from the knowledge graph.

    This class provides methods to search and traverse the knowledge graph
    to find related code entities and their relationships.
    """

    def __init__(self, graph: KnowledgeGraph):
        self.graph = graph
        self.logger = logging.getLogger(__name__)

    def find_related_context(self, entity_id: str, depth: int = 2,
                           relationship_types: Optional[List[str]] = None) -> List[ContextChunk]:
        """
        Find related context for a given entity using breadth-first search.

        Parameters
        ----------
        entity_id : str
            The ID of the entity to find related context for
        depth : int, optional
            Maximum depth to traverse (default: 2)
        relationship_types : List[str], optional
            Types of relationships to follow (default: all)

        Returns
        -------
        List[ContextChunk]
            List of related context chunks with relevance scores
        """
        if entity_id not in self.graph.nodes:
            self.logger.warning(f"Entity {entity_id} not found in graph")
            return []

        if depth <= 0:
            return []

        adjacency = defaultdict(list)
        for edge in self.graph.edges:
            if relationship_types is not None and edge.type not in relationship_types:
                continue
            adjacency[edge.source].append(edge)
            if edge.target != edge.source:
                adjacency[edge.target].append(edge)

        visited = set()
        context_chunks = []

        # BFS traversal
        queue = deque([(entity_id, 0, [])])  # (node_id, current_depth, path)

        while queue:
            current_id, current_depth, path = queue.popleft()

            if current_id in visited or current_depth > depth:
                continue

            visited.add(current_id)
            current_node = self.graph.nodes[current_id]

            # Skip the original entity
            if current_id != entity_id:
                # Calculate relevance score based on depth and relationship type
                relevance_score = 1.0 / (current_depth + 1)
                if relationship_types and path and path[-1] not in relationship_types:
                    relevance_score *= 0.5  # Reduce score for filtered relationships

                context_chunks.append(ContextChunk(
                    node=current_node,
                    relevance_score=relevance_score,
                    relationship_path=path.copy(),
                    metadata={"depth": current_depth}
                ))

            # Add neighbors to queue
            if current_depth < depth:
                for edge in adjacency.get(current_id, ()):
                    neighbor_id = edge.target if edge.source == current_id else edge.source
                    if neighbor_id not in visited:
                        queue.append((neighbor_id, current_depth + 1, path + [edge.type]))

        # Sort by relevance score
        context_chunks.sort(key=lambda x: x.relevance_score, reverse=True)
        return context_chunks

    def get_call_hierarchy(self, function_name: str) -> Dict[str, Any]:
        """
        Get the call hierarchy for a given function.

        Parameters
        ----------
        function_name : str
            Name of the function to analyze

        Returns
        -------
        Dict[str, Any]
            Call hierarchy with callers and callees
        """
        hierarchy = {
            "function": function_name,
            "callers": [],
            "callees": [],
            "locations": []
        }

        # Find all function nodes with this name
        function_nodes = []
        for node in self.graph.nodes.values():
            if is_function_like_node(node) and function_name in (
                    node.name, node.metadata.get("qualified_name"), node.id):
                function_nodes.append(node)
                hierarchy["locations"].append({
                    "file": node.file,
                    "line": node.line_start
                })

        # Find callers and callees
        for node in function_nodes:
            # Find callers (functions that call this function)
            for edge in self.graph.edges:
                if edge.target == node.id and edge.type == "calls":
                    caller_node = self.graph.nodes.get(edge.source)
                    if caller_node and is_function_like_node(caller_node):
                        hierarchy["callers"].append({
                            "name": caller_node.name,
                            "file": caller_node.file,
                            "line": edge.metadata.get("line")
                        })

            # Find callees (functions called by this function)
            for edge in self.graph.edges:
                if edge.source == node.id and edge.type == "calls":
                    callee_id = edge.target
                    # Extract function name from target
                    if "::" in callee_id:
                        callee_node = self.graph.nodes.get(callee_id)
                        callee_name = callee_node.name if callee_node else callee_id.split("::")[-1]
                        hierarchy["callees"].append({
                            "name": callee_name,
                            "line": edge.metadata.get("line")
                        })

        return hierarchy

    def find_dependencies(self, file_path: str) -> List[str]:
        """
        Find all dependencies for a given file.

        Parameters
        ----------
        file_path : str
            Path to the file to analyze

        Returns
        -------
        List[str]
            List of dependency file paths
        """
        file_node_id = f"file::{file_path}"

        file_nodes = {node.file for node in self.graph.nodes.values() if node.type == "file"}
        imports = (edge for edge in self.graph.edges
                   if edge.source == file_node_id and edge.type in {"imports", "includes"})
        return self._dependencies_for_file(file_path, file_nodes, imports)

    def _dependencies_for_file(self, file_path, file_nodes, imports):
        """Resolve a file's import edges using a file index shared by this operation."""
        if f"file::{file_path}" not in self.graph.nodes:
            self.logger.warning(f"File {file_path} not found in graph")
            return []

        dependencies = set()
        for edge in imports:
            # Extract target file from the edge
            target = edge.target
            if target.startswith("file::"):
                dependencies.add(target.replace("file::", ""))
            elif target.startswith("module::"):
                module = edge.metadata.get("module")
                if module is None:
                    module = target.split("::", 1)[1]
                symbol = edge.metadata.get("symbol")
                modules = [module]
                if symbol and symbol != "*":
                    parents = _python_module_files(file_nodes, file_path, module, edge.metadata.get("level", 0))
                    bindings = {}
                    if len(parents) == 1:
                        bindings = self.graph.nodes["file::" + next(iter(parents))].metadata.get("python_bindings", {})
                    if symbol not in bindings:
                        modules.insert(0, ".".join(filter(None, (module, symbol))))
                for candidate in modules:
                    matches = _python_module_files(file_nodes, file_path, candidate, edge.metadata.get("level", 0))
                    if matches:
                        if len(matches) == 1:
                            dependencies.update(matches)
                        break

        return sorted(dependencies)

    def search_by_pattern(self, pattern: str, node_types: Optional[List[str]] = None) -> List[GraphNode]:
        """
        Search for nodes matching a pattern in their name or content.

        Parameters
        ----------
        pattern : str
            Regex pattern to search for
        node_types : List[str], optional
            Types of nodes to search (default: all)

        Returns
        -------
        List[GraphNode]
            List of matching nodes
        """
        matching_nodes = []
        regex = re.compile(pattern, re.IGNORECASE)

        for node in self.graph.nodes.values():
            if node_types and node.type not in node_types:
                continue

            # Search in node name
            if regex.search(node.name):
                matching_nodes.append(node)
                continue

            # Search in metadata
            for key, value in node.metadata.items():
                if isinstance(value, str) and regex.search(value):
                    matching_nodes.append(node)
                    break

        return matching_nodes
