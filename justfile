run-cmd := "poetry run"

default:
    just --list

check:
    ruff check --show-source src test

fix:
    ruff fix src test

test:
    {{run-cmd}} pytest test
    {{run-cmd}} sphinx-build -b doctest docs docs/_build

build: wheel docs

docs:
    {{run-cmd}} sphinx-build -b html docs docs/_build

wheel:
    poetry build

serve-docs:
    {{run-cmd}} sphinx-autobuild docs docs/_build/html
