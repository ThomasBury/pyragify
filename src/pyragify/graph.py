"""
Knowledge Graph module for Pyragify.

This module provides functionality to build and manage knowledge graphs
representing code relationships and dependencies.
"""

import ast
import json
import logging
import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from queue import Queue
from typing import Any, Dict, List, Optional, Set, Tuple, Union

# Tree-sitter imports (conditionally imported)
try:
    from tree_sitter import Language, Node, Parser
    from tree_sitter_languages import get_language
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    # Define dummy types for type hinting if tree-sitter is not available
    class Language: pass
    class Node: pass

logger = logging.getLogger(__name__)


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
        return f"{edge.source}->{edge.target}:{edge.type}"

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
        graph = cls()
        graph.metadata = data.get("metadata", {})
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
        for chunk in chunks:
            self._process_chunk(chunk, relative_path, language, file_graph)

        return file_graph

    def _relative_path(self, file_path: Path) -> str:
        """Return a repository-relative path string."""
        return str(file_path.relative_to(self.repo_path))

    def _file_node_id(self, file_path: Union[Path, str]) -> str:
        """Build a stable file node identifier from a repo-relative path."""
        relative_path = file_path if isinstance(file_path, str) else self._relative_path(file_path)
        return f"file::{relative_path}"

    def _lookup_local_node_id(self, graph: KnowledgeGraph, symbol_name: str) -> Optional[str]:
        """Find a local node by symbol name within a file graph."""
        for node_id, node in graph.nodes.items():
            if node.type != "file" and node.name == symbol_name:
                return node_id
        return None

    def _normalize_reference_id(self, graph: KnowledgeGraph, file_path: Path, node_id: str) -> str:
        """Map extracted references onto existing graph node IDs when possible."""
        if node_id.startswith("file::"):
            return self._file_node_id(file_path)

        if node_id.startswith(("function::", "class::", "struct::")):
            symbol_name = node_id.split("::", 1)[1]
            return self._lookup_local_node_id(graph, symbol_name) or node_id

        if node_id.startswith("method::"):
            symbol_name = node_id.split("::", 1)[1].split(".")[-1]
            return self._lookup_local_node_id(graph, symbol_name) or node_id

        return node_id

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
        for edge in dependencies:
            edge.source = self._normalize_reference_id(graph, file_path, edge.source)
            edge.target = self._normalize_reference_id(graph, file_path, edge.target)
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

        # Create node ID
        if chunk_type == "file":
            node_id = f"{file_path}::__file_content__"
            if not name:
                name = Path(file_path).name
        else:
            node_id = f"{file_path}::{name}" if name else f"{file_path}::{chunk_type}_{id(chunk)}"

        # Create node
        node = GraphNode(
            id=node_id,
            type=chunk_type,
            file=file_path,
            name=name,
            line_start=start_line,
            line_end=end_line,
            language=language,
            metadata=chunk.get("metadata", {})
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
                language = get_language(language_name)
                parser = Parser()
                parser.set_language(language)
                tree = parser.parse(bytes(content, "utf8"))
                root_node = tree.root_node

                # Extract include statements
                include_query = """
                (preproc_include
                  path: (string_literal) @include_path
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
                            captures = {query.capture_names[i]: node for i, node in match}
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
            include_path = content[captures["include_path"].start_byte:captures["include_path"].end_byte].strip('<>"')
            edges.append(GraphEdge(
                source=file_id,
                target=f"header::{include_path}",
                type="includes",
                metadata={"line": captures["include_path"].start_point[0] + 1}
            ))
        elif query_type == "call" and "function_name" in captures:
            func_name = content[captures["function_name"].start_byte:captures["function_name"].end_byte]
            edges.append(GraphEdge(
                source=file_id,
                target=f"function::{func_name}",
                type="calls",
                metadata={"line": captures["function_name"].start_point[0] + 1}
            ))
        elif query_type == "struct" and "struct_name" in captures:
            struct_name = content[captures["struct_name"].start_byte:captures["struct_name"].end_byte]
            # Note: C/C++ doesn't have inheritance for structs, but we can track them
            edges.append(GraphEdge(
                source=file_id,
                target=f"struct::{struct_name}",
                type="defines",
                metadata={"line": captures["struct_name"].start_point[0] + 1}
            ))
        elif query_type == "class" and "class_name" in captures:
            class_name = content[captures["class_name"].start_byte:captures["class_name"].end_byte]
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

                language = get_language("java")
                parser = Parser()
                parser.set_language(language)
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
                  object: (identifier) @object_name
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
                            captures = {query.capture_names[i]: node for i, node in match}
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
            import_path = content[captures["import_path"].start_byte:captures["import_path"].end_byte]
            edges.append(GraphEdge(
                source=file_id,
                target=f"package::{import_path}",
                type="imports",
                metadata={"line": captures["import_path"].start_point[0] + 1}
            ))
        elif query_type == "method_call" and "method_name" in captures and "object_name" in captures:
            method_name = content[captures["method_name"].start_byte:captures["method_name"].end_byte]
            edges.append(GraphEdge(
                source=file_id,
                target=f"method::{method_name}",
                type="calls",
                metadata={"line": captures["method_name"].start_point[0] + 1}
            ))
        elif query_type == "class" and "class_name" in captures:
            class_name = content[captures["class_name"].start_byte:captures["class_name"].end_byte]
            if "parent_class" in captures:
                parent_name = content[captures["parent_class"].start_byte:captures["parent_class"].end_byte]
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
                    if node.module:
                        module_name = node.module
                        for alias in node.names:
                            edges.append(GraphEdge(
                                source=file_id,
                                target=f"module::{module_name}.{alias.name}",
                                type="imports",
                                metadata={"line": node.lineno, "alias": alias.asname}
                            ))

            # Extract function calls and class inheritance
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        func_name = node.func.id
                        edges.append(GraphEdge(
                            source=file_id,
                            target=f"function::{func_name}",
                            type="calls",
                            metadata={"line": node.lineno}
                        ))
                    elif isinstance(node.func, ast.Attribute):
                        # Handle method calls like obj.method()
                        if isinstance(node.func.value, ast.Name):
                            method_name = node.func.attr
                            edges.append(GraphEdge(
                                source=file_id,
                                target=f"method::{method_name}",
                                type="calls",
                                metadata={"line": node.lineno}
                            ))

                elif isinstance(node, ast.ClassDef):
                    # Extract class inheritance
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
                language = get_language(language_name)
                parser = Parser()
                parser.set_language(language)
                tree = parser.parse(bytes(content, "utf8"))
                root_node = tree.root_node

                # Extract import statements
                import_query = """
                (import_statement
                  (import_clause
                    (named_imports
                      (import_specifier
                        name: (identifier) @imported_name
                      )
                    )
                  )
                  source: (string) @source
                )
                """

                # Extract require statements
                require_query = """
                (call_expression
                  function: (identifier) @require
                  arguments: (arguments (string) @module)
                  (#eq? @require "require")
                )
                """

                # Extract function calls
                call_query = """
                (call_expression
                  function: (identifier) @function_name
                )
                """

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
                    (call_query, "call"),
                    (class_query, "class")
                ]:
                    try:
                        query = language.query(query_str)
                        for match in query.matches(root_node):
                            captures = {query.capture_names[i]: node for i, node in match}
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
        if query_type == "import" and "imported_name" in captures:
            imported_name = content[captures["imported_name"].start_byte:captures["imported_name"].end_byte]
            edges.append(GraphEdge(
                source=file_id,
                target=f"module::{imported_name}",
                type="imports",
                metadata={"line": captures["imported_name"].start_point[0] + 1}
            ))
        elif query_type == "require" and "module" in captures:
            module_name = content[captures["module"].start_byte:captures["module"].end_byte].strip('"\'')
            edges.append(GraphEdge(
                source=file_id,
                target=f"module::{module_name}",
                type="imports",
                metadata={"line": captures["module"].start_point[0] + 1}
            ))
        elif query_type == "call" and "function_name" in captures:
            func_name = content[captures["function_name"].start_byte:captures["function_name"].end_byte]
            edges.append(GraphEdge(
                source=file_id,
                target=f"function::{func_name}",
                type="calls",
                metadata={"line": captures["function_name"].start_point[0] + 1}
            ))
        elif query_type == "class" and "class_name" in captures:
            if "parent_class" in captures:
                parent_name = content[captures["parent_class"].start_byte:captures["parent_class"].end_byte]
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
        # Build global symbol table
        global_symbols = self._build_global_symbol_table(all_file_graphs)

        # Find and resolve cross-file references
        cross_file_edges = self._find_cross_file_references(all_file_graphs, global_symbols)

        # Add cross-file edges to repository graph
        for edge in cross_file_edges:
            self.graph.add_edge(edge)

        logger.info(f"Added {len(cross_file_edges)} cross-file reference edges")

    def _build_global_symbol_table(self, all_file_graphs: List[KnowledgeGraph]) -> Dict[str, Dict[str, Any]]:
        """
        Build a global symbol table from all file graphs.

        Returns
        -------
        Dict[str, Dict[str, Any]]
            Global symbol table mapping symbol names to their definitions
        """
        global_symbols = {}

        for file_graph in all_file_graphs:
            for node in file_graph.nodes.values():
                is_external = node.metadata.get("external") if node.metadata else False
                if (
                    node.type in ['function', 'class', 'module', 'variable']
                    and node.file != "<external>"
                    and not is_external
                ):
                    symbol_key = f"{node.name}"
                    if symbol_key not in global_symbols:
                        global_symbols[symbol_key] = {
                            'definition': node,
                            'files': []
                        }
                    global_symbols[symbol_key]['files'].append(node.file)

        return global_symbols

    def _find_cross_file_references(self, all_file_graphs: List[KnowledgeGraph],
                                  global_symbols: Dict[str, Dict[str, Any]]) -> List[GraphEdge]:
        """
        Find cross-file references based on the global symbol table.

        Parameters
        ----------
        all_file_graphs : List[KnowledgeGraph]
            All file graphs to analyze
        global_symbols : Dict[str, Dict[str, Any]]
            Global symbol table

        Returns
        -------
        List[GraphEdge]
            List of cross-file reference edges
        """
        cross_file_edges = []
        repo_file_ids = {
            node_id for node_id, node in self.graph.nodes.items()
            if node.type == "file" and node.file != "<external>"
        }

        for file_graph in all_file_graphs:
            file_name = None
            # Find the file node in this graph
            for node in file_graph.nodes.values():
                if node.type == 'file':
                    file_name = node.file
                    break

            if not file_name:
                continue

            # Check edges in this file for potential cross-references
            for edge in file_graph.edges:
                if edge.type in ['imports', 'calls', 'references']:
                    # Extract the target symbol name
                    target_symbol = self._extract_symbol_from_edge(edge)
                    if target_symbol and target_symbol in global_symbols:
                        symbol_info = global_symbols[target_symbol]
                        # Check if this symbol is defined in other files
                        other_files = [f for f in symbol_info['files'] if f != file_name]
                        if other_files:
                            # Create cross-file reference edge
                            definition_node = symbol_info['definition']
                            target_file_id = self._file_node_id(definition_node.file)
                            if target_file_id not in repo_file_ids:
                                continue
                            cross_edge = GraphEdge(
                                source=f"file::{file_name}",
                                target=target_file_id,
                                type="cross_file_reference",
                                metadata={
                                    "symbol": target_symbol,
                                    "reference_type": edge.type,
                                    "line": edge.metadata.get("line")
                                }
                            )
                            cross_file_edges.append(cross_edge)

        return cross_file_edges

    def _extract_symbol_from_edge(self, edge: GraphEdge) -> Optional[str]:
        """
        Extract symbol name from an edge target.

        Parameters
        ----------
        edge : GraphEdge
            The edge to analyze

        Returns
        -------
        Optional[str]
            The symbol name if extractable, None otherwise
        """
        target = edge.target

        # Handle different target formats
        if target.startswith("module::"):
            return target.replace("module::", "")
        elif target.startswith("function::"):
            return target.replace("function::", "")
        elif target.startswith("class::"):
            return target.replace("class::", "")
        elif "::" in target:
            # Extract the symbol name from file::symbol format
            parts = target.split("::")
            if len(parts) >= 2:
                return parts[-1]

        return None

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
            signature = f"{edge.source}->{edge.target}:{edge.type}"
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
            signature = f"{edge.source}->{edge.target}:{edge.type}"
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

        visited = set()
        context_chunks = []

        # BFS traversal
        queue = Queue()
        queue.put((entity_id, 0, []))  # (node_id, current_depth, path)

        while not queue.empty():
            current_id, current_depth, path = queue.get()

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
                neighbors = self.graph.get_neighbors(current_id, relationship_types)
                for neighbor_id in neighbors:
                    if neighbor_id not in visited:
                        new_path = path + [self._get_relationship_type(current_id, neighbor_id)]
                        queue.put((neighbor_id, current_depth + 1, new_path))

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
            if node.type == "function" and node.name == function_name:
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
                    if caller_node:
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
                        callee_name = callee_id.split("::")[-1]
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
        dependencies = set()
        file_node_id = f"file::{file_path}"

        if file_node_id not in self.graph.nodes:
            self.logger.warning(f"File {file_path} not found in graph")
            return []

        # Find all import relationships
        for edge in self.graph.edges:
            if edge.source == file_node_id and edge.type in ["imports", "includes"]:
                # Extract target file from the edge
                target = edge.target
                if target.startswith("file::"):
                    dependencies.add(target.replace("file::", ""))
                elif target.startswith("module::"):
                    # Try to find the module's file
                    module_name = target.replace("module::", "")
                    for node in self.graph.nodes.values():
                        if node.type == "file" and module_name in node.file:
                            dependencies.add(node.file)
                            break

        return list(dependencies)

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
        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error as e:
            self.logger.error(f"Invalid regex pattern: {e}")
            return []

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

    def _get_relationship_type(self, source_id: str, target_id: str) -> str:
        """Get the relationship type between two nodes."""
        for edge in self.graph.edges:
            if edge.source == source_id and edge.target == target_id:
                return edge.type
        return "unknown"
