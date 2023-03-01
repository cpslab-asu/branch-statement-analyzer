.. Branch Statement Analyzer documentation master file, created by
   sphinx-quickstart on Wed Mar  1 08:20:38 2023.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Branch Statement Analyzer's documentation!
=====================================================

.. toctree::
   :maxdepth: 1
   :caption: Modules:

   Branches <branches>
   Kripke <kripke>
   Instrumentation <instrumentation>

This library provides three main functionalities:

1. Decompose the conditional statements in the body of a python function into a
   :py:class:`.BranchTree` representing the heirarchy of conditional guards.
2. Transform the conditional expression tree into a `kripke structure`_ where the labels for each
   state contain one combination of guard expression evaluations.
3. Instrument a function to save the state of the variables used in each conditional guard
   expression during evaluation.

To better understand this functionality, please consider the following example:

.. code:: python

   from bsa import BranchTree, instrument_function

   def controller(x: int) -> int:
      if x <= 10:
         return x * 2
      else:
         return x + 1

   trees = BranchTree.from_function(controller)
   assert len(trees) == 1

   tree = trees[0]
   kripkes = tree.as_kripke()
   assert len(kripkes) == 1

   kripke = kripkes[0]
   instrumented_fn = instrument_function(controller)

   variables, _ = instrumented_function(5)
   kripke



.. _`kripke structure`: https://en.wikipedia.org/wiki/Kripke_structure_(model_checking)
.. _`psy-taliro`: https://gitlab.com/sbtg/psy-taliro


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
