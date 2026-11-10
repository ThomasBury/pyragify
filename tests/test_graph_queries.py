import pytest

from pyragify.graph import GraphEdge, GraphNode, GraphQuery, KnowledgeGraph


@pytest.fixture
def graph():
    graph = KnowledgeGraph()
    for name in 'ABCDE':
        graph.add_node(GraphNode(name, 'function', 'app.py', name, language='python'))
    for source, target, relationship in [
        ('B', 'A', 'calls'), ('A', 'C', 'references'), ('A', 'B', 'imports'),
        ('B', 'D', 'calls'), ('C', 'D', 'inherits'), ('D', 'D', 'calls'), ('C', 'E', 'calls'),
    ]:
        graph.add_edge(GraphEdge(source, target, relationship))
    return graph


def related(query, entity='A', depth=2, relationships=None):
    return [(item.node.id, item.relationship_path, item.relevance_score, item.metadata['depth'])
            for item in query.find_related_context(entity, depth, relationships)]


@pytest.mark.parametrize('depth, expected', [
    (-1, []), (0, []),
    (1, [('B', ['calls'], .5, 1), ('C', ['references'], .5, 1)]),
    (2, [('B', ['calls'], .5, 1), ('C', ['references'], .5, 1),
         ('D', ['calls', 'calls'], 1 / 3, 2), ('E', ['references', 'calls'], 1 / 3, 2)]),
    (9, [('B', ['calls'], .5, 1), ('C', ['references'], .5, 1),
         ('D', ['calls', 'calls'], 1 / 3, 2), ('E', ['references', 'calls'], 1 / 3, 2)]),
])
def test_context_preserves_breadth_first_order_cycles_and_depth(graph, depth, expected):
    assert related(GraphQuery(graph), depth=depth) == expected


@pytest.mark.parametrize('relationships, expected', [
    ([], []), (['missing'], []),
    (['calls'], [('B', ['calls'], .5, 1), ('D', ['calls', 'calls'], 1 / 3, 2)]),
    (['imports'], [('B', ['imports'], .5, 1)]),
    (['calls', 'imports'], [('B', ['calls'], .5, 1), ('D', ['calls', 'calls'], 1 / 3, 2)]),
    (['references'], [('C', ['references'], .5, 1)]),
])
def test_context_filters_and_parallel_relationships(graph, relationships, expected):
    assert related(GraphQuery(graph), relationships=relationships) == expected


def test_context_traverses_both_directions_and_retains_relationships(graph):
    assert related(GraphQuery(graph), 'C') == [
        ('A', ['references'], .5, 1), ('D', ['inherits'], .5, 1), ('E', ['calls'], .5, 1),
        ('B', ['references', 'calls'], 1 / 3, 2)]
    assert related(GraphQuery(graph), 'missing') == []


def test_context_reflects_mutations_on_existing_query_instance(graph):
    query = GraphQuery(graph)
    assert related(query, depth=1)[0] == ('B', ['calls'], .5, 1)
    graph.edges.reverse()
    assert related(query, depth=1) == [('B', ['imports'], .5, 1), ('C', ['references'], .5, 1)]
    graph.edges = [GraphEdge('A', 'E', 'includes')]
    assert related(query) == [('E', ['includes'], .5, 1)]
    graph.edges[0].type = 'references'
    assert related(query) == [('E', ['references'], .5, 1)]
    extra = KnowledgeGraph()
    extra.add_node(GraphNode('F', 'function', 'other.py', 'F'))
    extra.add_edge(GraphEdge('E', 'F', 'calls'))
    graph.merge(extra)
    assert related(query) == [('E', ['references'], .5, 1), ('F', ['references', 'calls'], 1 / 3, 2)]
    graph.edges.clear()
    assert related(query) == []


def test_batch_dependency_resolution_preserves_exact_paths_and_edge_order(tmp_path):
    from pyragify.graph import GraphBuilder

    graph = KnowledgeGraph()
    files = ['pkg/app.py', 'pkg/__init__.py', 'pkg/run.py', 'pkg/b.py', 'b.py', 'src/pkg/b.py']
    for file in files:
        graph.add_node(GraphNode('file::' + file, 'file', file, file,
                                 metadata={'python_bindings': {'run': [1, 0]}} if file == 'pkg/__init__.py' else {}))
    graph.add_node(GraphNode('module::pkg', 'module', '<external>', 'pkg'))
    graph.add_node(GraphNode('module::b', 'module', '<external>', 'b'))
    graph.add_node(GraphNode('header::stdio.h', 'header', '<external>', 'stdio.h'))
    for target, relationship, metadata in [
        ('module::pkg', 'imports', {'module': 'pkg', 'symbol': 'run'}),
        ('module::b', 'imports', {'module': 'b', 'level': 1}),
        ('file::b.py', 'includes', {}), ('header::stdio.h', 'includes', {}),
    ]:
        graph.add_edge(GraphEdge('file::pkg/app.py', target, relationship, metadata))
    query = GraphQuery(graph)
    assert query.find_dependencies('pkg/app.py') == ['b.py', 'pkg/__init__.py']
    before = [edge.to_dict() for edge in graph.edges]
    file_graph = KnowledgeGraph()
    file_graph.add_node(graph.nodes['file::pkg/app.py'])
    builder = GraphBuilder(tmp_path)
    builder.graph = graph
    builder.resolve_cross_file_references([file_graph])
    assert [edge.to_dict() for edge in graph.edges[:len(before)]] == before
    assert [(edge.source, edge.target, edge.type) for edge in graph.edges[len(before):]] == [
        ('file::pkg/app.py', 'file::b.py', 'cross_file_reference'),
        ('file::pkg/app.py', 'file::pkg/__init__.py', 'cross_file_reference')]
    first = graph.to_dict()
    builder.resolve_cross_file_references([file_graph])
    assert graph.to_dict() == first
    del graph.nodes['file::src/pkg/b.py']
    assert query.find_dependencies('pkg/app.py') == ['b.py', 'pkg/__init__.py', 'pkg/b.py']
    graph.edges.clear()
    assert query.find_dependencies('pkg/app.py') == []
    assert query.find_dependencies('missing.py') == []
