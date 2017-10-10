Testing
-------

-  To run the regression tests, first install tox:

   .. code:: sh

       pip install 'tox>=2.5'

   then run it

   .. code:: sh

       tox

-  To run individual tests type:

   .. code:: sh

       tox -- -k test_foo
