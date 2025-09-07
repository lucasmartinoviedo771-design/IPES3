![CI](https://github.com/<org>/<repo>/actions/workflows/ci.yml/badge.svg)
![CodeQL](https://github.com/<org>/<repo>/actions/workflows/codeql.yml/badge.svg)

Setup: python -m uv sync --all-groups, python manage.py migrate, python manage.py runserver.

Tests: python -m pytest --cov --cov-report=html.

CI: Se publica un artefacto coverage-html.