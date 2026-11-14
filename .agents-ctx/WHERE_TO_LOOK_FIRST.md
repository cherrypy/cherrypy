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
2. `cherrypy/<module>.py` -- the underscored `_cp*.py` modules
   are the core, `cherrypy/lib/` the tools, `cherrypy/process/`
   the process bus.
3. `cherrypy/test/helper.py` -- `CPWebCase`, the base most tests
   build on -- then `cherrypy/test/test_<topic>.py`.
4. As above.
5. `.github/workflows/ci-cd.yml`, with the workflows it calls.

Other places worth knowing:

- `docs/` -- Sphinx docs (RST).
- `CHANGES.rst` -- the hand-maintained changelog, with a
  `v(next)` section at the top for unreleased changes.
