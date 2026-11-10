"""Reproduce M7 on synthetic code, not the unrecorded historical workload.

uv run --locked python scripts/benchmark_graph.py /tmp/pyragify-before
uv run --locked python scripts/benchmark_graph.py /tmp/pyragify-after --compare /tmp/pyragify-before/results.json

Requires a new output directory. Timings include processor initialization, cache
loading, and publication, but exclude process startup and verification. Application
caches are cold/reused; filesystem and OS caches are not flushed. No timing gates.
"""

import argparse
import cProfile
import gc
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import pstats
import resource
import statistics
import subprocess
import sys
import time
import tracemalloc
from dataclasses import asdict
from pathlib import Path

from pyragify.graph import GraphQuery, KnowledgeGraph
from pyragify import processor as processing


FILES = 1000
FUNCTIONS = 10
PAIRS = 5
REPETITIONS = 30
QUERIES = [f'module_{index:04d}.py::function_{index % FUNCTIONS}' for index in range(0, FILES, 50)]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def summary(values):
    ordered = sorted(values)
    return {'median': statistics.median(values), 'min': min(values), 'max': max(values),
            'p95': ordered[math.ceil(len(ordered) * .95) - 1], 'samples': values}


def make_corpus(root):
    root.mkdir()
    hashes = {}
    for index in range(FILES):
        lines = [f'from module_{(index + 1) % FILES:04d} import function_0 as imported']
        for function in range(FUNCTIONS):
            block = [f'def function_{function}(value=0):',
                     f'    initial = value + {function}', '    adjusted = initial + 1',
                     '    total = adjusted + 2', '    copied = total',
                     f'    local = function_{(function + 1) % FUNCTIONS}(copied)',
                     '    remote = imported(copied)', '    return local + remote', '', '']
            lines.extend(block[:-1] if function == 0 else block)
        assert len(lines) == 100
        source = ('\n'.join(lines) + '\n').encode()
        name = f'module_{index:04d}.py'
        (root / name).write_bytes(source)
        hashes[name] = hashlib.sha256(source).hexdigest()
    assert len(hashes) == FILES and len(QUERIES) == 20
    return {'files': FILES, 'lines_per_file': 100, 'functions_per_file': FUNCTIONS,
            'total_lines': FILES * 100, 'sha256': digest(hashes)}


def verify_handoff(repo, output):
    manifest = json.loads((output / 'metadata.json').read_text())
    assert not manifest['failed_files']
    paths = [item['path'] for item in manifest['processed_files']]
    assert paths == sorted(path.name for path in repo.glob('*.py'))
    parts = {}
    hashes = {}
    for item in manifest['processed_files']:
        source = (repo / item['path']).read_bytes()
        mapping = item['output']
        if mapping['part'] not in parts:
            parts[mapping['part']] = (output / mapping['part']).read_bytes()
        retained = parts[mapping['part']][mapping['start_byte']:mapping['end_byte']]
        assert retained == source
        assert hashlib.md5(source).hexdigest() == item['hash']
        assert mapping['start_line'] == 1 and mapping['end_line'] == item['lines'] == 100
        hashes[item['path']] = hashlib.sha256(source).hexdigest()
    return {'selection_sha256': digest(hashes), 'files': len(paths),
            'reused_files': len(manifest['reused_files'])}


def graph_fingerprint(graph):
    data = graph.to_dict()
    data['metadata']['languages'].sort()
    ordered = digest(data)
    data['edges'].sort(key=lambda edge: json.dumps(edge, sort_keys=True))
    return {'canonical_sha256': digest(data), 'ordered_sha256': ordered,
            'nodes': len(graph.nodes), 'edges': len(graph.edges)}


def peak_rss(who):
    # ru_maxrss is bytes on macOS and KiB on Linux; report each process class separately.
    return resource.getrusage(who).ru_maxrss * (1 if sys.platform == 'darwin' else 1024)


def export_child(repo, output, workers, graph, profile_path):
    processing.cpu_count = lambda: workers  # Benchmark-only control; the public API stays unchanged.
    profiler = cProfile.Profile() if profile_path else None
    if profiler:
        profiler.enable()
    start = time.perf_counter()
    processor = processing.RepoContentProcessor(repo, output, enable_graph=graph)
    processor.process_repo()
    elapsed = time.perf_counter() - start
    if profiler:
        profiler.disable()
        profiler.dump_stats(str(profile_path))
    result = {'seconds': elapsed, 'parent_peak_rss_bytes': peak_rss(resource.RUSAGE_SELF),
              'largest_child_peak_rss_bytes': peak_rss(resource.RUSAGE_CHILDREN)}
    result.update(verify_handoff(repo, output))
    if graph:
        result['graph'] = graph_fingerprint(processor.repo_graph)
    print(json.dumps(result))


def run_export(repo, output, workers, graph, profile_path=None):
    result = subprocess.run([sys.executable, str(Path(__file__).resolve()), '_export', str(repo),
                             str(output), str(workers), str(int(graph)),
                             str(profile_path) if profile_path else '-'],
                            capture_output=True, text=True, check=True)
    output.with_suffix('.log').write_text(result.stderr, encoding='utf-8')
    return json.loads(result.stdout)


def profile_text(path):
    with path.with_suffix('.txt').open('w') as stream:
        pstats.Stats(str(path), stream=stream).strip_dirs().sort_stats('cumulative').print_stats(35)


def query_benchmark(graph_path, output):
    loading = []
    for _ in range(PAIRS):
        gc.collect()
        start = time.perf_counter()
        data = json.loads(graph_path.read_text())
        decoded = time.perf_counter()
        graph = KnowledgeGraph.from_dict(data)
        loaded = time.perf_counter()
        loading.append({'json_seconds': decoded - start, 'model_seconds': loaded - decoded})
        del data, graph
    graph = KnowledgeGraph.from_dict(json.loads(graph_path.read_text()))
    query = GraphQuery(graph)
    expected = {}
    samples = {entity: [] for entity in QUERIES}
    for entity in QUERIES:
        assert entity in graph.nodes
        expected[entity] = [asdict(chunk) for chunk in query.find_related_context(entity, 2)]
    for repeat in range(REPETITIONS):
        # Rotate the same fixed query set so a query does not always occupy the same slot.
        for entity in QUERIES[repeat % len(QUERIES):] + QUERIES[:repeat % len(QUERIES)]:
            start = time.perf_counter()
            chunks = query.find_related_context(entity, 2)
            samples[entity].append(time.perf_counter() - start)
            assert [asdict(chunk) for chunk in chunks] == expected[entity]
    tracemalloc.start()
    query.find_related_context(QUERIES[0], 2)
    _, query_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    profile_path = output / 'query.prof'
    cProfile.runctx('query.find_related_context(QUERIES[0], 2)', globals(), locals(), str(profile_path))
    profile_text(profile_path)
    return {'depth': 2, 'relationship_types': None, 'repetitions': REPETITIONS,
            'queries': {entity: summary(values) for entity, values in samples.items()},
            'all_seconds': summary([value for values in samples.values() for value in values]),
            'ordered_results_sha256': digest(expected), 'peak_traced_query_bytes': query_peak,
            'json_loading_seconds': summary([item['json_seconds'] for item in loading]),
            'model_loading_seconds': summary([item['model_seconds'] for item in loading])}


def environment():
    repo = Path(__file__).resolve().parents[1]
    git = lambda *args: subprocess.check_output(['git', '-C', str(repo), *args])
    return {'revision': git('rev-parse', 'HEAD').decode().strip(),
            'tracked_diff_sha256': hashlib.sha256(git('diff', 'HEAD', '--binary')).hexdigest(),
            'source_sha256': {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                              for path in sorted((repo / 'src/pyragify').glob('*.py'))},
            'harness_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'python': sys.version, 'platform': platform.platform(), 'machine': platform.machine(),
            'cpu_count': os.cpu_count(),
            'cpu_affinity': sorted(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else None,
            'dependencies': {name: importlib.metadata.version(name) for name in
                             ('pyragify', 'tree-sitter', 'tree-sitter-javascript',
                              'tree-sitter-typescript', 'tree-sitter-java', 'tree-sitter-c',
                              'tree-sitter-cpp', 'tree-sitter-go', 'tree-sitter-html',
                              'tree-sitter-css', 'pathspec')}}


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '_export':
        _, _, repo, output, workers, graph, profile = sys.argv
        export_child(Path(repo), Path(output), int(workers), bool(int(graph)),
                     Path(profile) if profile != '-' else None)
        return
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--compare', type=Path, help='Previous results.json; assert graph and query equivalence.')
    args = parser.parse_args()
    if args.workers < 1:
        parser.error('--workers must be positive')
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    repo = output / 'corpus'
    results = {'synthetic': True, 'environment': environment(), 'workers': args.workers,
               'corpus': make_corpus(repo), 'exports': [], 'summaries': {}}
    print('Profiling a cold graph export and ten representative worker extractions...', flush=True)
    results['profile_export'] = run_export(repo, output / 'profile-export', args.workers, True,
                                           output / 'export.prof')
    profile_text(output / 'export.prof')
    profiler = cProfile.Profile()
    profiler.enable()
    for index in range(0, FILES, 100):
        result = processing._process_file_worker((str(repo / f'module_{index:04d}.py'), str(repo),
                                                  str(output / 'worker-profile'), True, None))
        assert result is not None
    profiler.disable()
    profiler.dump_stats(str(output / 'worker.prof'))
    profile_text(output / 'worker.prof')
    reference = results['profile_export']['graph']
    for pair in range(PAIRS):
        for cache in ('cold', 'reused'):
            for graph in ([False, True] if pair % 2 == 0 else [True, False]):
                destination = output / f'pair-{pair}-graph-{int(graph)}'
                run = run_export(repo, destination, args.workers, graph)
                assert run['selection_sha256'] == results['corpus']['sha256']
                assert run['reused_files'] == (FILES if cache == 'reused' else 0)
                if graph:
                    assert run['graph'] == reference
                results['exports'].append(dict(run, pair=pair, cache=cache, graph_enabled=graph))
                print(f"Pair {pair + 1}/{PAIRS}, {cache}, graph={graph}: {run['seconds']:.3f}s", flush=True)
    for cache in ('cold', 'reused'):
        for graph in (False, True):
            runs = [run for run in results['exports'] if run['cache'] == cache and run['graph_enabled'] == graph]
            results['summaries'][f'{cache}_graph_{int(graph)}'] = {
                key: summary([run[key] for run in runs]) for key in
                ('seconds', 'parent_peak_rss_bytes', 'largest_child_peak_rss_bytes')}
    results['graph'] = reference
    results['query'] = query_benchmark(output / 'pair-0-graph-1/graphs/repository_graph.json', output)
    if args.compare:
        previous = json.loads(args.compare.read_text())
        assert previous['corpus'] == results['corpus']
        assert previous['workers'] == results['workers']
        assert previous['graph'] == results['graph']
        assert previous['query']['ordered_results_sha256'] == results['query']['ordered_results_sha256']
        assert previous['environment']['python'] == results['environment']['python']
        assert previous['environment']['dependencies'] == results['environment']['dependencies']
        results['comparison'] = {'baseline': str(args.compare.resolve()), 'graph_and_queries_equal': True,
            'export_median_ratios': {key: value['seconds']['median'] / previous['summaries'][key]['seconds']['median']
                                     for key, value in results['summaries'].items()},
            'query_median_ratio': results['query']['all_seconds']['median'] / previous['query']['all_seconds']['median']}
    (output / 'results.json').write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'graph': reference,
                      'export_seconds': {key: value['seconds'] for key, value in results['summaries'].items()},
                      'query_seconds': {key: value for key, value in results['query']['all_seconds'].items() if key != 'samples'},
                      'comparison': results.get('comparison')}, indent=2))


if __name__ == '__main__':
    main()
