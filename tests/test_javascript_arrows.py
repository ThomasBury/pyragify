import json

import pytest

from pyragify.graph import GraphQuery, KnowledgeGraph
from pyragify.processor import FileProcessor, RepoContentProcessor
from test_handoff import check_handoff


def build(tmp_path, suffix, source):
    path = tmp_path / ('app' + suffix)
    path.write_text(source, encoding='utf-8')
    graph = FileProcessor(tmp_path, tmp_path / 'output', enable_graph=True).chunk_file(path, True)[2]
    assert graph is not None
    loaded = KnowledgeGraph.from_dict(json.loads(json.dumps(graph.to_dict())))
    assert loaded.to_dict() == graph.to_dict()
    return loaded


def calls(graph):
    return {(edge.source, edge.target) for edge in graph.edges if edge.type == 'calls'}


@pytest.mark.parametrize('suffix', ['.js', '.ts'])
@pytest.mark.parametrize('async_keyword, body', [('', 'leaf()'), ('async ', 'await leaf()'),
                                               ('', '{ return leaf(); }'), ('async ', '{ return await leaf(); }')])
def test_named_arrows_are_callers_and_callees(tmp_path, suffix, async_keyword, body):
    file = 'app' + suffix
    graph = build(tmp_path, suffix, f'function leaf() {{}}\nconst run = {async_keyword}() => {body};\nfunction caller() {{ run(); }}\ncaller();\n')
    assert calls(graph) == {(file + '::run', file + '::leaf'),
                            (file + '::caller', file + '::run'),
                            ('file::' + file, file + '::caller')}
    assert GraphQuery(graph).get_call_hierarchy('run')['callers'] == [
        {'name': 'caller', 'file': file, 'line': 3}]
    assert GraphQuery(graph).get_call_hierarchy('run')['callees'] == [{'name': 'leaf', 'line': 2}]
    assert {item.node.id for item in GraphQuery(graph).find_related_context(file + '::caller', 1, ['calls'])} == {file + '::run', 'file::' + file}


@pytest.mark.parametrize('suffix', ['.js', '.ts'])
def test_ancestry_separates_same_line_nested_arrows_and_neighbors(tmp_path, suffix):
    file = 'app' + suffix
    graph = build(tmp_path, suffix, '// café 🐍\nfunction leaf() {} const outer = () => { const inner = () => leaf(); inner(); }; const other = () => leaf(); outer(); other(); leaf();\n')
    assert calls(graph) == {(file + '::outer.inner', file + '::leaf'),
                            (file + '::outer', file + '::outer.inner'),
                            (file + '::other', file + '::leaf'),
                            ('file::' + file, file + '::outer'),
                            ('file::' + file, file + '::other'),
                            ('file::' + file, file + '::leaf')}
    assert graph.nodes[file + '::outer.inner'].metadata['qualified_name'] == 'outer.inner'


@pytest.mark.parametrize('suffix', ['.js', '.ts'])
def test_anonymous_callbacks_have_deterministic_source_identities(tmp_path, suffix):
    file = 'app' + suffix
    source = 'function leaf() {}\nconst run = () => { /* café 🐍 */ visit(() => leaf(), async () => { leaf(); }); leaf(); }; run();\n'
    graph = build(tmp_path, suffix, source)
    positions = [source.splitlines()[1].encode().index(text) for text in (b'() => leaf()', b'async () =>')]
    anonymous = [file + f'::run.anonymous@2:{column}' for column in positions]
    assert all(node in graph.nodes for node in anonymous)
    assert calls(graph) == {(anonymous[0], file + '::leaf'), (anonymous[1], file + '::leaf'),
                            (file + '::run', 'function::visit'), (file + '::run', file + '::leaf'),
                            ('file::' + file, file + '::run')}
    assert build(tmp_path, suffix, source).to_dict() == graph.to_dict()


@pytest.mark.parametrize('suffix', ['.js', '.ts'])
@pytest.mark.parametrize('source, owner', [
    ('const run = () => {}; const caller = (run) => run();', 'caller'),
    ('const run = () => {}; function caller(run) { run(); }', 'caller'),
    ('const run = () => {}; const caller = () => { run(); let run = other; };', 'caller'),
    ('const run = () => {}; const caller = () => { const {run} = obj; run(); };', 'caller'),
    ('const run = () => {}; const caller = () => { const {x: run} = obj; run(); };', 'caller'),
    ('const run = () => {}; const caller = () => { var run; run(); };', 'caller'),
    ('let run = () => {}; run = other; const caller = () => run();', 'caller'),
    ('let run = () => {}; const caller = () => { run(); run = other; };', 'caller'),
    ('const run = () => {}; function caller() { try {} catch (run) { run(); } }', 'caller'),
    ('const run = () => {}; const caller = () => { for (const run of xs) { run(); } };', 'caller'),
    ('const run = () => {}; const caller = () => { if (ok) { var run = other; } run(); };', 'caller'),
    ('const run = () => {}; const caller = () => { let [run] = xs; run(); };', 'caller'),
    ('const run = () => {}; const caller = (...run) => run();', 'caller'),
    ('const run = () => {}; const caller = (run = other) => run();', 'caller'),
    ('const run = () => {}; const caller = () => { run++; run(); };', 'caller'),
    ('const obj = {run: () => {}}; const caller = () => run();', 'caller'),
    ('let run; run = () => {}; const caller = () => run();', 'caller'),
])
def test_shadowed_unsupported_and_rebound_calls_stay_unresolved(tmp_path, suffix, source, owner):
    file = 'app' + suffix
    graph = build(tmp_path, suffix, source)
    assert (file + '::' + owner, 'function::run') in calls(graph)
    assert not any(target == file + '::run' for _, target in calls(graph))


@pytest.mark.parametrize('suffix', ['.js', '.ts'])
def test_block_scope_does_not_hide_outer_arrow_after_block(tmp_path, suffix):
    file = 'app' + suffix
    graph = build(tmp_path, suffix, 'const run = () => {}; const caller = () => { { let run = other; run(); } run(); };')
    assert calls(graph) == {(file + '::caller', 'function::run'), (file + '::caller', file + '::run')}


def test_typescript_arrow_annotations_and_parameters(tmp_path):
    graph = build(tmp_path, '.ts', 'function leaf(): number { return 1; }\nconst run = async (x: number): Promise<number> => leaf();\nconst caller = (run: () => number) => run();\nrun(1);\n')
    assert calls(graph) == {('app.ts::run', 'app.ts::leaf'), ('app.ts::caller', 'function::run'),
                            ('file::app.ts', 'app.ts::run')}


def test_arrow_cache_rebuild_and_source_handoff(tmp_path, monkeypatch):
    repo = tmp_path / 'repo'
    repo.mkdir()
    (repo / 'app.js').write_bytes('// café 🐍\r\nconst leaf = () => 1; const run = () => leaf(); run();\r\n'.encode())
    (repo / 'typed.ts').write_bytes(b'const run = (x: number): number => x;\r\nrun(1);\r\n')
    output = tmp_path / 'output'

    def export():
        processor = RepoContentProcessor(repo, output, enable_graph=True)
        processor.process_repo()
        check_handoff(repo, output)
        loaded = KnowledgeGraph.from_dict(json.loads((output / 'graphs/repository_graph.json').read_text()))
        assert loaded.to_dict() == processor.repo_graph.to_dict()
        return loaded

    original = export()
    assert calls(original) == {('app.js::run', 'app.js::leaf'), ('file::app.js', 'app.js::run'),
                               ('file::typed.ts', 'typed.ts::run')}
    with monkeypatch.context() as patch:
        patch.setattr('pyragify.processor._process_file_worker', lambda task: pytest.fail('Cache not reused'))
        assert export().to_dict() == original.to_dict()
    path = output / '.pyragify-cache.json'
    cache = json.loads(path.read_text())
    assert cache['version'] == 8
    cache['version'] = 7
    for record in cache['files'].values():
        record['graph']['edges'] = []
    path.write_text(json.dumps(cache))
    assert export().to_dict() == original.to_dict()
    assert check_handoff(repo, output)['reused_files'] == []
    fresh = RepoContentProcessor(repo, tmp_path / 'fresh', enable_graph=True)
    fresh.process_repo()
    check_handoff(repo, tmp_path / 'fresh')
    assert fresh.repo_graph.to_dict() == original.to_dict()


@pytest.mark.parametrize('suffix', ['.js', '.ts'])
def test_existing_named_functions_keep_ids_and_nested_scope(tmp_path, suffix):
    file = 'app' + suffix
    graph = build(tmp_path, suffix, 'function leaf() {}\nfunction outer() { function inner() { leaf(); } const run = () => inner(); run(); }\nouter(); leaf();\n')
    assert calls(graph) == {(file + '::outer.inner', file + '::leaf'),
                            (file + '::outer.run', file + '::outer.inner'),
                            (file + '::outer', file + '::outer.run'),
                            ('file::' + file, file + '::outer'), ('file::' + file, file + '::leaf')}


@pytest.mark.parametrize('suffix', ['.js', '.ts'])
def test_anonymous_non_arrow_callback_does_not_absorb_neighbor_calls(tmp_path, suffix):
    file = 'app' + suffix
    source = 'function leaf() {} const run = () => { visit(function () { leaf(); }); leaf(); }; run();'
    graph = build(tmp_path, suffix, source)
    callback = file + f'::run.anonymous@1:{source.index("function ()")}'
    assert calls(graph) == {(callback, file + '::leaf'), (file + '::run', 'function::visit'),
                            (file + '::run', file + '::leaf'), ('file::' + file, file + '::run')}


@pytest.mark.parametrize('source', [
    'namespace Local { const run = () => 1; } const caller = () => run();',
    'namespace Local { var run = () => 1; } const caller = () => run();',
    'declare function run(): number; const run = () => 1; const caller = () => run();',
])
def test_unsupported_typescript_bindings_do_not_invent_targets(tmp_path, source):
    graph = build(tmp_path, '.ts', source)
    assert calls(graph) == {('app.ts::caller', 'function::run')}


@pytest.mark.parametrize('suffix', ['.js', '.ts'])
@pytest.mark.parametrize('source', [
    'const run = () => {}; function caller() { try {} catch ({run = other}) { run(); } }',
    'const run = () => {}; const caller = ({x: run = other}) => run();',
    'const run = () => {}; const caller = () => { [run] = xs; run(); };',
    'const run = () => {}; const caller = () => { for (run of xs) {} run(); };',
    'const run = () => {}; const caller = () => { run += other; run(); };',
    'const run = () => {}; const run = () => {}; const caller = () => run();',
])
def test_more_uncertain_bindings_stay_unresolved(tmp_path, suffix, source):
    graph = build(tmp_path, suffix, source)
    assert calls(graph) == {('app' + suffix + '::caller', 'function::run')}


@pytest.mark.parametrize('declaration', ['class run {}', 'abstract class run {}', 'enum run { A }'])
def test_typescript_value_declarations_shadow_arrows(tmp_path, declaration):
    graph = build(tmp_path, '.ts', 'const run = () => {}; function caller() { ' + declaration + ' run(); }')
    assert calls(graph) == {('app.ts::caller', 'function::run')}


@pytest.mark.parametrize('suffix', ['.js', '.ts'])
def test_arrow_nested_in_method_keeps_its_execution_owner(tmp_path, suffix):
    file = 'app' + suffix
    graph = build(tmp_path, suffix, 'function leaf() {} class A { method() { const run = () => leaf(); run(); } } leaf();')
    assert calls(graph) == {(file + '::A.method.run', file + '::leaf'),
                            (file + '::A.method', file + '::A.method.run'),
                            ('file::' + file, file + '::leaf')}
