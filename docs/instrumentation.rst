======================
Instrumentation Module
======================

Introduction
============

This module is responsible for injecting code into a function to save the states of variables used
in any conditional expression. The result is a function that returns a dictionary of variable values
in addition to the original return value. As an example, consider the following function:

.. code-block:: python

   def f(x, y):
      z = exp(x) * x + 10

      if z <= 1:
         if y >= 10:
            return True
         else:
            return False
      else:
         return None

Instrumenting this function will have the following effect:

.. code-block:: python

   def f2(x, y):
      variables = {}
      z = exp(x) * x + 10

      variables["z"] = z
      if variables["z"] <= 1:
         variables["y"] = y
         if variables["y"] >= 10:
            return variables, True
         else:
            return variables, False
      else:
         return variables, None

Variables are only saved before they are used, so should the first condition evaluate to ``False``
the variables dictionary would only contain the value for ``z`` and not ``y``.

Classes
=======

.. autoclass:: bsa.instrumentation.InstrumentedFunction
   :members:

Functions
=========

.. autofunction:: bsa.instrumentation.instrument_function
