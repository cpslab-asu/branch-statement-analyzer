.. Branch Statement Analyzer documentation master file, created by
   sphinx-quickstart on Wed Mar  1 08:20:38 2023.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Python Branch Statement Analyzer
================================

This library provides three main functionalities:

1. Decompose the conditional statements in the body of a python function into a
   :py:class:`.BranchTree` representing the heirarchy of conditional guards.
2. Transform the conditional expression tree into a set of `kripke structures`_ where the labels for
   each state contain one combination of guard expression evaluations.
3. Instrument a function to save the state of the variables used in each conditional guard
   expression during evaluation.

An example usage of this library can be seen in the `two room thermostat`_ system, which is
designed to be used in conjunction with `psy-taliro`_ to search for test inputs to cover all
thermostat controller branches.

.. _`kripke structures`: https://en.wikipedia.org/wiki/Kripke_structure_(model_checking)
.. _`psy-taliro`: https://gitlab.com/sbtg/psy-taliro
.. _`two room thermostat`: https://gitlab.com/sbtg/instrumentation/thermostat-model

Installation
============

This project is available for installation on `PyPI`_ using the command ``pip install
branch-statement-analyzer``. For most cases, we suggest using a virtual environment manager like
`Poetry`_, `Pipenv`_, `Hatch`_, or a full installation manager like `Conda`_ or `Mamba`_.

.. _`PyPI`: https://pypi.org
.. _`Poetry`: https://python-poetry.org
.. _`Pipenv`: https://pipenv.pypa.io
.. _`Hatch`: https://hatch.pypa.io
.. _`Conda`: https://conda.io
.. _`Mamba`: https://mamba.readthedocs.io

Repository
==========

The source code for this repository can be found `here
<https://gitlab.com/sbtg/instrumentation/branch-statement-analyzer>`_. Pull requests are always
welcome, please see the
`contribution guide <https://gitlab.com/sbtg/instrumentation/branch-statement-analyzer/-/wikis/contributing>`_
for more information.

.. toctree::
   :maxdepth: 1
   :caption: Modules:

   Branches <branches>
   Kripke <kripke>
   Instrumentation <instrumentation>

