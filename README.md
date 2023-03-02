# Python Branch Statement Analyzer

[![Documentation Status](https://readthedocs.org/projects/branch-statement-analzyer/badge/?version=latest)](https://branch-statement-analzyer.readthedocs.io/en/latest/?badge=latest)

The purpose of this library is two-fold:

1. Detect independent paths through a function and represent all paths as a
   fully-connected [Kripke Structure](https://en.wikipedia.org/wiki/Kripke_structure_(model_checking)).
2. Instrument a function to preserve the states of the conditional variables for
   an execution of the function and augment the return value of the function
   with the conditional variable states.

## Path detection

TODO

## Instrumentation

TODO

## Usage

Decomposition of a function into a condition tree is accomplished by calling
the `BranchTree.from_function` static method like so:

```python

def myfunc(x):
   if x <= 10:
      return x**2
   else:
      return x*2


tree = BranchTree.from_function(myfunc)
```

Conversion of the BranchTree into a Kripke Structure can be accomplished by
calling the `BranchTree.into_kripke` method once the function has been analyzed.

A function can be instrumented using the `instrument_function` decorator, which
will return another function that accepts the same inputs and returns a tuple
containing the return value of the function and the states of the conditional
variables.

```python

@instrument_function
def myfunc(x):
   if x <= 10:
      return x**2
   else:
      return x*2

states, retval = myfunc(8)
```

## Documentation

Documentation for this project can be found on
[Read the Docs](https://branch-statement-analzyer.readthedocs.io)
