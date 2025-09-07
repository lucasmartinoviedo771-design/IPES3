# tasks.ps1
param([string]$t)

switch ($t) {
  "test" { python -m pytest --cov --cov-report=term-missing -q; break }
  "lint" { python -m ruff check .; break }
  "fix"  { python -m ruff check . --fix; python -m ruff format; break }
  "run"  { python manage.py runserver; break }
  "covhtml" { python -m pytest --cov --cov-report=html -q; break }
  "check" { python manage.py check && python -m ruff check .; break }
  default { "Uso: .\tasks.ps1 [test|lint|fix|run|covhtml|check]"; break }
}