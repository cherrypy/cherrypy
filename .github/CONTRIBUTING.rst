Read and contribute to CherryPy
-------------------------------

Make sure you read the `README
<https://github.com/cherrypy/cherrypy/blob/master/README.rst>`_. Also ensure
you set up `pre-commit utility <https://pre-commit.com/#install>`_
**correctly** and **TravisCI tests pass**::

  pre-commit run --all-files  # runs the same checks as in CI locally
  pre-commit install  # sets up itself as a pre-commit hook of your local repo

Submitting Pull Requests
------------------------
If you're changing the structure of the repository please create an issue
first. Don't forget to write appropriate test cases, add them into CI process
if applicable and make the TravisCI build pass.

Sync (preferably rebase) your feature branch with upstream regularly to make
us able to merge your PR seamlessly.

Submitting bug reports
----------------------

Make sure you are on latest changes and that you re-ran this command `tox`
after updating your local repository. If you can, please provide more
information about your environment such as browser, operating system,
python version, and any other related software versions.

Also
----
See `Contributing <https://docs.cherrypy.org/en/latest/contribute.html>`_ in
the docs.
