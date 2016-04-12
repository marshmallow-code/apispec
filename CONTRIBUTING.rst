Contributing Guidelines
=======================

In General
----------

- `PEP 8`_, when sensible.
- Test ruthlessly. Write docs for new features.
- Even more important than Test-Driven Development--*Human-Driven Development*.

.. _`PEP 8`: http://www.python.org/dev/peps/pep-0008/

In Particular
-------------

Questions, Feature Requests, Bug Reports, and Feedback. . .
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

. . .should all be reported on the `Github Issue Tracker`_ .

.. _`Github Issue Tracker`: https://github.com/marshmallow-code/apispec/issues?state=open

Setting Up for Local Development
++++++++++++++++++++++++++++++++

1. Fork apispec_ on Github. ::

    $ git clone https://github.com/marshmallow-code/apispec.git
    $ cd apispec

2. Install development requirements. It is highly recommended that you use a virtualenv. ::

    # After activating your virtualenv
    $ pip install -r dev-requirements.txt
    $ npm install -g swagger-tools

3. Install apispec in develop mode. ::

   $ pip install -e .

Git Branch Structure
++++++++++++++++++++

apispec abides by the following branching model:


``dev``
    Current development branch. **New features should branch off here**.

``pypi``
    Latest PyPI release.

``X.Y-line``
    Maintenance branch for release ``X.Y``. **Bug fixes should be sent to the most recent release branch.** The maintainer will forward-port the fix to ``dev``. Note: exceptions may be made for bug fixes that introduce large code changes.

**Always make a new branch for your work**, no matter how small. Also, **do not put unrelated changes in the same branch or pull request**. This makes it more difficult to merge your changes.

Pull Requests
++++++++++++++

1. Create a new local branch.
::

    # For a new feature
    $ git checkout -b name-of-feature dev

    # For a bugfix
    $ git checkout -b fix-something 1.2-line

2. Commit your changes. Write `good commit messages <http://tbaggery.com/2008/04/19/a-note-about-git-commit-messages.html>`_.
::

    $ git commit -m "Detailed commit message"
    $ git push origin name-of-feature

3. Before submitting a pull request, check the following:

- If the pull request adds functionality, it is tested and the docs are updated.
- You've added yourself to ``AUTHORS.rst``.

4. Submit a pull request to ``marshmallow-code:dev`` or the appropriate maintenance branch. The `Travis CI <https://travis-ci.org/marshmallow-code/apispec>`_ build must be passing before your pull request is merged.

Running Tests
+++++++++++++

To run all tests: ::

    $ invoke test

To run tests on Python 2.7, 3.3, 3.4, and 3.5 virtual environments (must have each interpreter installed): ::

    $ tox

Documentation
+++++++++++++

Contributions to the documentation are welcome. Documentation is written in `reStructured Text`_ (rST). A quick rST reference can be found `here <http://docutils.sourceforge.net/docs/user/rst/quickref.html>`_. Builds are powered by Sphinx_.

To install the packages for building the docs: ::

    $ pip install -r docs/requirements.txt

To build the docs: ::

    $ invoke docs -b

The ``-b`` (for "browse") automatically opens up the docs in your browser after building.

.. _Sphinx: http://sphinx.pocoo.org/
.. _`reStructured Text`: http://docutils.sourceforge.net/rst.html

.. _`apispec`: https://github.com/marshmallow-code/apispec
