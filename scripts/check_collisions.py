#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_colision.py
------------------

Analizador rápido para detectar posibles colisiones/duplicados en proyectos Django + JS.

Secciones:
 [1/5] Plantillas y estáticos con misma ruta relativa
 [2/5] Nombres de URL de Django repetidos (name="...")
 [3/5] Funciones Python de nivel módulo definidas en múltiples archivos
 [4/5] Importaciones riesgosas (alias para distintos módulos en el mismo archivo, import *, from models import ...)
 [5/5] Funciones JS/TS duplicadas por nombre

Uso:
  python check_colision.py [PATH_BASE]
Si omitís PATH_BASE, usa el directorio actual.
"""

from __future__ import annotations
import ast
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple, Iterable

# -------------------- Config --------------------
IGNORE_DIRS = {
    ".git", ".hg", ".svn",
    ".venv", "venv", "env", ".env",
    "node_modules", "__pycache__",
    "dist", "build", "migrations",
    "staticfiles",
}

PY_EXTS = {".py"}
JS_EXTS = {".js", ".ts"}
TEMPLATE_DIR_NAME = "templates"
STATIC_DIR_NAME = "static"

# Para [3/5]
DUNDER = lambda name: name.startswith("__") and name.endswith("__")
PY_IGNORE_FUNCS = {
    "main",
    "__init__", "__str__",
    "dispatch", "get_context_data", "get_queryset",
    "get_success_url", "post", "form_valid", "clean",
}  # main suele repetirse (manage.py, scripts, etc.)

# ------------------------------------------------
# Utilidades
# ------------------------------------------------

def should_skip_dir(p: Path) -> bool:
    return any(part in IGNORE_DIRS for part in p.parts)


def read_text_safe(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except Exception:
        try:
            return p.read_text(encoding="latin-1")
        except Exception:
            return ""


# ------------------------------------------------
# [1/5] Plantillas y estáticos con misma ruta relativa
# ------------------------------------------------

def collect_relative_under_marker(base_dir: Path, marker: str, file_exts: Iterable[str]) -> Dict[str, List[str]]:
    """Devuelve mapping: ruta_relativa_desde_marker -> [archivos_absolutos]"""
    hits: Dict[str, List[str]] = defaultdict(list)
    for root, dirs, files in os.walk(base_dir):
        # filtrar dirs ignorados
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for fname in files:
            p = Path(root, fname)
            if p.suffix.lower() in file_exts and not should_skip_dir(p):
                if marker in p.parts:
                    parts = list(p.parts)
                    idx = parts.index(marker)
                    rel = Path(*parts[idx + 1:])  # ruta relativa DESPUÉS del marker
                    # normalizamos a string con separador del SO
                    key = str(rel)
                    hits[key].append(str(p))
    return hits


def print_section_1(base_dir: Path) -> None:
    print("[1/5] Plantillas y estáticos con misma ruta relativa…")
    tmpl = collect_relative_under_marker(base_dir, TEMPLATE_DIR_NAME, {".html", ".txt"})
    stat = collect_relative_under_marker(base_dir, STATIC_DIR_NAME, {".css", ".js", ".png", ".jpg", ".jpeg", ".svg", ".gif", ".ico", ".webp"})

    reported = False
    for key, paths in sorted(tmpl.items()):
        if len(paths) > 1:
            reported = True
            print(f"  [!] template: '{key}' aparece {len(paths)} veces:")
            for p in paths:
                print(f"     - {p}")

    for key, paths in sorted(stat.items()):
        if len(paths) > 1:
            reported = True
            print(f"  ⚠ static: '{key}' aparece {len(paths)} veces:")
            for p in paths:
                print(f"     - {p}")

    if not reported:
        print("  ✓ Sin colisiones en templates/static")


# ------------------------------------------------
# [2/5] Nombres de URL de Django repetidos
# ------------------------------------------------

def extract_url_names_from_ast(tree: ast.AST) -> List[str]:
    names: List[str] = []

    class V(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call):
            for kw in node.keywords:
                if kw.arg == "name":
                    val = kw.value
                    if isinstance(val, ast.Constant) and isinstance(val.value, str):
                        names.append(val.value)
                    elif isinstance(val, ast.Str):  # py<3.8
                        names.append(val.s)
            self.generic_visit(node)

    V().visit(tree)
    return names


def collect_django_url_names(base_dir: Path) -> Dict[str, List[str]]:
    """Busca en archivos *urls.py* names de rutas Django."""
    acc: Dict[str, List[str]] = defaultdict(list)
    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for fname in files:
            if fname != "urls.py":
                continue
            p = Path(root, fname)
            if should_skip_dir(p):
                continue
            src = read_text_safe(p)
            if not src:
                continue
            try:
                tree = ast.parse(src, filename=str(p))
            except SyntaxError:
                continue
            for nm in extract_url_names_from_ast(tree):
                acc[nm].append(str(p))
    return acc


def print_section_2(base_dir: Path) -> None:
    print("[2/5] Nombres de URL de Django repetidos…")
    names_map = collect_django_url_names(base_dir)
    dups = {k: v for k, v in names_map.items() if len(v) > 1}
    if not dups:
        print("  ✓ Nombres de URL únicos")
        return
    for name, paths in sorted(dups.items()):
        print(f"  ⚠ nombre de URL '{name}' definido en:")
        for p in paths:
            print(f"     - {p}")


# ------------------------------------------------
# [3/5] Funciones Python de nivel módulo en múltiples archivos
#       (sin métodos de clase, omite dunders y algunos helpers comunes)
# ------------------------------------------------

def iter_top_level_functions(py_file: Path) -> List[str]:
    src = read_text_safe(py_file)
    if not src:
        return []
    try:
        tree = ast.parse(src, filename=str(py_file))
    except SyntaxError:
        return []

    funcs: List[str] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            name = node.name
            if DUNDER(name) or name in PY_IGNORE_FUNCS:
                continue
            funcs.append(name)
    return funcs


def check_py_function_collisions(base_dir: Path) -> Dict[str, List[str]]:
    by_name: Dict[str, List[str]] = defaultdict(list)  # nombre -> [archivos...]
    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for fname in files:
            p = Path(root, fname)
            if p.suffix.lower() in PY_EXTS and not should_skip_dir(p):
                for fn in iter_top_level_functions(p):
                    by_name[fn].append(str(p))
    collisions = {name: paths for name, paths in by_name.items() if len(paths) > 1}
    return collisions


def print_section_3(base_dir: Path) -> None:
    print("[3/5] Funciones/clases Python definidas en múltiples módulos…")
    col = check_py_function_collisions(base_dir)
    if not col:
        print("  ✓ Definiciones de módulo únicas")
        return
    for name, paths in sorted(col.items()):
        print(f"  ⚠ función '{name}' está en:")
        for p in paths:
            print(f"     - {p}")


# ------------------------------------------------
# [4/5] Importaciones riesgosas (ruido reducido)
# ------------------------------------------------

def analyze_imports_in_file(py_file: Path) -> Tuple[Dict[str, set], bool, List[int]]:
    """Devuelve:
       - alias_conflicts: {alias: {módulos}} si el MISMO alias se usa para distintos módulos en el MISMO archivo
       - star_imports: True/False si aparece import *
       - short_models_imports: líneas con 'from models import ...' (no absoluto, nivel 0)
    """
    src = read_text_safe(py_file)
    if not src:
        return {}, False, []
    try:
        tree = ast.parse(src, filename=str(py_file))
    except SyntaxError:
        return {}, False, []

    alias_to_mods: Dict[str, set] = defaultdict(set)
    star_imports = False
    short_models_lines: List[int] = []

    class V(ast.NodeVisitor):
        def visit_Import(self, node: ast.Import):
            for alias in node.names:
                asname = alias.asname or alias.name.split(".")[0]
                alias_to_mods[asname].add(alias.name)

        def visit_ImportFrom(self, node: ast.ImportFrom):
            nonlocal star_imports, short_models_lines
            mod = node.module or ""
            # 'from . import x' => node.level >= 1 (eso NO es problema aquí)
            if node.level == 0 and mod == "models":
                short_models_lines.append(node.lineno)
            for alias in node.names:
                if alias.name == "*":
                    star_imports = True
                    continue
                asname = alias.asname or alias.name
                origin = (("." * node.level) + mod).strip(".") or "(relative)"
                alias_to_mods[asname].add(origin)

    V().visit(tree)

    alias_conflicts = {a: mods for a, mods in alias_to_mods.items() if len(mods) > 1}
    return alias_conflicts, star_imports, short_models_lines


def check_risky_imports(base_dir: Path):
    per_file_conflicts: Dict[str, Dict[str, set]] = {}
    star_files: List[str] = []
    short_models: List[Tuple[str, int]] = []

    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for fname in files:
            p = Path(root, fname)
            if p.suffix.lower() in PY_EXTS and not should_skip_dir(p):
                conflicts, has_star, short_lines = analyze_imports_in_file(p)
                if conflicts:
                    per_file_conflicts[str(p)] = conflicts
                if has_star:
                    star_files.append(str(p))
                for ln in short_lines:
                    short_models.append((str(p), ln))
    return per_file_conflicts, star_files, short_models


def print_section_4(base_dir: Path) -> None:
    print("[4/5] Importaciones riesgosas (alias repetidos / import *)…")
    conflicts, star_files, short_models = check_risky_imports(base_dir)

    something = False

    if conflicts:
        something = True
        for fpath, alias_map in conflicts.items():
            for alias, mods in alias_map.items():
                mods_str = ", ".join(sorted(mods))
                print(f"  ⚠ alias '{alias}' usado para múltiples módulos en {fpath}: {mods_str}")

    if star_files:
        something = True
        for f in star_files:
            print(f"  [!] import * en {f}")

    for f, ln in short_models:
        something = True
        print(f"  ⚠ import relativo ambiguo en {f}:{ln}  ← usa import absoluto (p.ej. from tu_app.models import …)")

    if not something:
        print("  ✓ Sin importaciones riesgosas detectadas")


# ------------------------------------------------
# [5/5] Funciones JS/TS duplicadas por nombre
# ------------------------------------------------
JS_FUNC_PATTERNS = [
    re.compile(r"\bfunction\s+([A-Za-zA-Z0-9_]+)\s*\(", re.MULTILINE),
    re.compile(r"\bexport\s+function\s+([A-Za-zA-Z0-9_]+)\s*\(", re.MULTILINE),
    re.compile(r"\b(?:const|let|var)\s+([A-Za-zA-Z0-9_]+)\s*=\s*(?:async\s+)?function\s*\(", re.MULTILINE),
    re.compile(r"\b(?:const|let|var)\s+([A-Za-zA-Z0-9_]+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>", re.MULTILINE),
    re.compile(r"\bexport\s+(?:const|let|var)\s+([A-Za-zA-Z0-9_]+)\s*=", re.MULTILINE),
]


def collect_js_functions(base_dir: Path) -> Dict[str, List[str]]:
    by_name: Dict[str, List[str]] = defaultdict(list)
    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for fname in files:
            p = Path(root, fname)
            if p.suffix.lower() in JS_EXTS and not should_skip_dir(p):
                src = read_text_safe(p)
                if not src:
                    continue
                names_found = set()
                for rx in JS_FUNC_PATTERNS:
                    for m in rx.finditer(src):
                        names_found.add(m.group(1))
                for nm in names_found:
                    by_name[nm].append(str(p))
    return {k: v for k, v in by_name.items() if len(v) > 1}


def print_section_5(base_dir: Path) -> None:
    print("[5/5] Funciones JS/TS duplicadas por nombre…")
    dups = collect_js_functions(base_dir)
    if not dups:
        print("  ✓ Sin funciones JS/TS duplicadas")
        return
    for name, paths in sorted(dups.items()):
        print(f"  [!] función JS '{name}' está en:")
        for p in paths:
            print(f"     - {p}")


# ------------------------------------------------
# Main
# ------------------------------------------------

def main() -> None:
    if len(sys.argv) > 1:
        base = Path(sys.argv[1]).resolve()
    else:
        base = Path.cwd().resolve()

    print(f"== Analizando {base} ==\n")

    # 1
    print_section_1(base)
    print()

    # 2
    print_section_2(base)
    print()

    # 3
    print_section_3(base)
    print()

    # 4
    print_section_4(base)
    print()

    # 5
    print_section_5(base)


if __name__ == "__main__":
    main()



