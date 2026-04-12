import sys
from pathlib import Path
import mkdocs_gen_files

# Add src to sys.path so mkdocstrings can resolve imports
root = Path(__file__).resolve().parent.parent
src = root / "src"
sys.path.insert(0, str(src))

# 1) Gather all module files...
module_files = sorted(src.rglob("*.py"))

# 2) Generate per-module pages
for path in module_files:
    module_path = path.relative_to(src).with_suffix("")
    doc_path = path.relative_to(src).with_suffix(".md")
    full_doc_path = Path("reference", doc_path)

    parts = module_path.parts
    if parts[-1] in {"__main__", "__init__"}:
        if len(parts) == 1:
            continue
        parts = parts[:-1]

    identifier = ".".join(parts)

    with mkdocs_gen_files.open(full_doc_path, "w") as fd:
        print(f"::: {identifier}", file=fd)
    mkdocs_gen_files.set_edit_path(full_doc_path, path.relative_to(root))

# 3) Now build an index.md for each package directory
package_dirs = set()
for path in module_files:
    pkg = path.parent  # e.g. src/apex_fin/agents
    # only if it’s not the top-level src/
    if pkg != src:
        # drop the leading src, mirror into reference/
        rel_pkg = pkg.relative_to(src)
        package_dirs.add(rel_pkg)

for rel_pkg in sorted(package_dirs):
    index_doc = Path("reference", rel_pkg) / "index.md"
    mkdocs_gen_files.set_edit_path(index_doc, src / rel_pkg)  # enable “edit on GitHub”
    with mkdocs_gen_files.open(index_doc, "w") as fd:
        # Title (optional)
        fd.write(f"# `{rel_pkg}` package\n\n")
        # Include each child module/subpackage
        for child in sorted((src / rel_pkg).iterdir()):
            if child.is_dir() and (child / "__init__.py").exists():
                name = child.name
                fd.write(f"- [ `{name}` sub-package ]({name}/)\n")
            elif child.suffix == ".py" and child.name not in {
                "__init__.py",
                "__main__.py",
            }:
                name = child.stem
                fd.write(f"- [ `{name}` module ]({name}.md)\n")