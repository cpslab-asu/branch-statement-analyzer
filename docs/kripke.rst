=============
Kripke Module
=============

.. A Kripke structure is defined as the four-tuple :math:`\langle S, I, R, L \rangle` where :math:`S`
  is the set of Kripke states, :math:`I \subseteq S` is the set of initial states, :math:`R \subseteq
  S \times S` is the set of edges between states, and :math:`L: S \rightarrow AP^2` is the labeling
  function. The set of edges :math:`R` must be left-total, which means that each state must have at
  least one outgoing edge i.e. :math:`\forall s \in S{:}\ \exists s' \in S\ \text{s.t.}\ (s, s')
  \in R`. For a set of atomic propositions :math:`AP` the labeling function :math:`L` associates a
  subset of :math:`AP` that hold in each state.

Introduction
============

This module defines the Kripke structure used to represent the different branches of a potentially
nested conditional expression. The labels for each state represent a single combination of
evaluations for the conditional expression guards. For example, given the following simple
function:

.. code-block:: python

   def example(x: int) -> int:
      if x <= 10:
         return x + 1  # s1
      else:
         return x - 5  # s2

the resulting Kripke structure will contain two states :math:`\{S_1, S_2\}` representing the two
possible outcomes of the evaluating the conditional statement with the labels, :math:`L(S_1)=\{x
\leq 10\}` and :math:`L(S_2) = \{x > 10\}`. For the more complex example:

.. code-block:: python

   def example2(x: int, y: int) -> int:
      if x <= 10:
         if y <= 20:
            return x + y  # s1
         else:
            return x - y  # s2
      else:
         if y >= 30:
            return y  # s3
         else:
            return x  # s4

the Kripke structure will have four states :math:`\{S_1, S_2, S_3, S_4\}` with the labeling

* :math:`L(S_1)=\{x \leq 10, y \leq 20\}`
* :math:`L(S_2)=\{x \leq 10, y > 20\}`
* :math:`L(S_3)=\{x > 10, y \geq 30\}`
* :math:`L(S_4)=\{x > 10, y < 30\}`

An example of creating a Kripke structure can be seen below:

.. code-block:: python

   from bsa.kripke import Kripke, State

   states = [State(), State(), State()]
   initial = {
      state[0]: True,
      state[1]: False,
      state[2]: False,
   }
   labels = {
      state[0]: [
         "color = green",
         "timer <= 10"
      ],
      state[1]: [
         "color = yellow",
         "timer <= 5"
      ],
      state[2]: [
         "color = red",
         "timer <= 10"
      ],
   }
   edges = [
      (states[0], states[1]),
      (states[1], states[2]),
      (states[2], states[0]),
   ]

   kripke = Kripke(states, initial, labels, edges)

Classes
=======

.. autoclass:: bsa.kripke.State

.. autoclass:: bsa.kripke.Kripke
   :members:
