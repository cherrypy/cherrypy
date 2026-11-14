# Where to Look First

When picking up a task, get oriented before proposing anything.
Read, in this order:

1. The packaging metadata -- what the project is, what it depends
   on, what it exposes.
2. The source of the module the task is about.
3. The shared test fixtures, then the tests for that module --
   they are the behavioral contract.
4. `tox.ini` and `.pre-commit-config.yaml` -- how things get run
   locally and in CI.
5. The main CI/CD workflow.

Here:

1. `pyproject.toml` (build backend and metadata).
2. `src/pylibsshext/<module>.pyx` and its `.pxd`; libssh
   declarations live under `src/pylibsshext/includes/`.
3. `tests/conftest.py` (e.g. the `sshd_addr` fixture), then
   `tests/unit/<module>_test.py` or `tests/integration/`.
4. As above.
5. `.github/workflows/ci-cd.yml`, with the `reusable-*.yml`
   workflows it calls.

Other places worth knowing:

- `packaging/pep517_backend/` -- the in-tree PEP 517 build backend.
- `packaging/rpm/` -- RPM packaging, used by `.packit.yml`.
- `build-scripts/manylinux-container-image/` -- the manylinux
  images wheels are built in.
- `docs/` -- Sphinx docs (RST); change notes go under
  `docs/changelog-fragments/`.
