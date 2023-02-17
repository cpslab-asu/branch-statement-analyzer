from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Generic, Iterable, Mapping, Sequence, TypeVar

_LabelT = TypeVar("_LabelT")


def _concat(lists: list[list[_LabelT]]) -> list[_LabelT]:
    """Flatten a list of lists."""
    return [elem for list_ in lists for elem in list_]


@dataclass(frozen=True)
class State:
    """Kripke structure state.

    This class ensures that all states are unique and can be used as keys in a dictionary. To
    accomplish this, this class maintains a unique value that is used for comparison and hashing.
    """

    _id: uuid.UUID = field(init=False, default_factory=uuid.uuid4)


@dataclass(frozen=True)
class Edge:
    """A Kripke structure directed edge."""

    source: State
    target: State


class Kripke(Generic[_LabelT]):
    """Representation of a Kripke structure.

    A Kripke structure is a 4-tuple composed of the following elements:
      - A set of states S
      - A set of initial states I that is a subset of S
      - A set of directed edges E where each edge has a starting state S1 and an ending state S2 that are both elements of S
      - A labeling function L that returns a set of labels for each state in S

    This class is generic over the type used to represent the labels. In general, labels are boolean
    functions (atomic propositions) representing things that are true within the state. In this
    class we represent the labeling function as a python dict with the states as keys. Practically,
    since any type is allowed as a label it is up to the user to ensure the semantics of the label.

    Args:
        states: Set of states of the Kripke structure
        initial: Set of initial states
        labels: Dictionary with states as keys and sets of labels as values
        edges: Set of directed edges between states
    """

    _states: list[State]
    _initial: dict[State, bool]
    _labels: dict[State, list[_LabelT]]
    _edges: list[Edge]

    def __init__(
        self,
        states: Sequence[State],
        initial: Mapping[State, bool],
        labels: Mapping[State, Sequence[_LabelT]],
        edges: Sequence[Edge],
    ):
        self._states = list(states)
        self._initial = {state: initial.get(state, False) for state in states}
        self._labels = {state: list(labels.get(state, [])) for state in states}
        self._edges = list(edges)

    @property
    def states(self) -> list[State]:
        """Set of states of the Kripke structure."""
        return self._states.copy()

    @property
    def initial_states(self) -> list[State]:
        """Set of initial states of the Kripke structure"""
        return [state for state in self._states if self._initial[state] is True]

    def states_from(self, state: State) -> list[State]:
        """Return the set of all states reachable from a given state.

        Args:
            state: The starting state

        Returns:
            The set of states reachable from the starting state

        Raises:
            ValueError: If the starting state is not in the set of states
        """

        if state not in self.states:
            raise ValueError(f"State {state} is not a member of Kripke structure")

        return [edge.target for edge in self._edges if edge.source == state] + [state]

    def add_labels(self, labels: list[_LabelT]) -> Kripke[_LabelT]:
        """Add a set of labels to a every state in the Kripke structure.

        This function returns a new Kripke structure instead of modifying the existing one.

        Args:
            labels: The set of labels to add to each state

        Returns:
            A new Kripke structure with the amended label map
        """

        labels_ = {state: self._labels[state] + labels for state in self._states}
        return Kripke(self._states, self._initial, labels_, self._edges)

    def add_edge(self, source: State, target: State) -> Kripke[_LabelT]:
        """Add an edge to the Kripke structure.

        This function returns a new Kripke structure instead of modifying the existing one.

        Args:
            source: The state the edge states from
            target: The state the edge terminates at

        Returns:
            A new Kripke structure with the new edge
        
        Raises:
            ValueError: If the source or target state is not in the Kripke structure
        """

        if source not in self._states:
            raise ValueError(f"State {source} is not a member of Kripke structure")

        if target not in self._states:
            raise ValueError(f"State {target} is not a member of Kripke structure")

        edges = self._edges + [Edge(source, target)]
        return Kripke(self._states, self._initial, self._labels, edges)

    def labels_for(self, state: State) -> list[_LabelT]:
        """Return the set of labels for a state.

        This function returns a copy of the set of labels to avoid mutations to the label list held
        by the Kripke structure.

        Args:
            state: The state to get labels for

        Returns:
            The set of labels associated with the state

        Raises:
            ValueError: If the state is not in the Kripke structure
        """

        if state not in self._states:
            raise ValueError(f"State {state} is not a member of Kripke structure")

        return self._labels[state].copy()

    def join(self, other: Kripke[_LabelT]) -> Kripke[_LabelT]:
        """Combine two Kripke structures.

        This function combines the two Kripke structures by merging the sets of states, initial
        states and labels of the operands. To protect against the event that two Kripke structures
        share a state with the same id, the other Kripke structure is scanned for duplicate states
        that are replaced. The edges of the combined Kripke structure are the union of the two sets
        of edges from each operand, as well as a set of new edges from each state in the left Kripke
        structure to the right Kripke structure and vice versa.

        Args:
            other: The second Kripke structure

        Returns:
            The combined Kripke structure
        """
        # pylint: disable=protected-access

        deduped = other._replace_duplicates(self._states)
        new_edges = [[Edge(s1, s2), Edge(s2, s1)] for s1 in self.states for s2 in deduped.states]

        deduped._states.extend(self._states)
        deduped._initial.update(self._initial)
        deduped._labels.update(self._labels)
        deduped._edges.extend(self._edges + _concat(new_edges))

        return deduped

    @classmethod
    def singleton(cls, labels: Sequence[_LabelT]) -> Kripke[_LabelT]:
        """Create a new Kripke structure with a single state.

        Args:
            labels: The labels for the single state

        Returns:
            A new Kripke structure with a single state
        """

        state = State()
        return cls([state], {state: True}, {state: labels}, [])

    def _replace_duplicates(self, states: Iterable[State]) -> Kripke[_LabelT]:
        """Create a Kripke structure by replacing matching states.

        This function returns a Kripke structure with states that match any state in the provided
        set replaced. For any state that is replaced, it is also replaced in the edges, labels and
        initial states. This function returns a new Kripke structure rather than modifying the
        existing Kripke structure.

        Args:
            states: Set of states that should be replaced

        Returns:
            A Kripke structure with matching states replaced
        """

        replacements: dict[State, State] = {}

        for state in self.states:
            if state in states:
                replacements[state] = State()

        states = [replacements.get(state, state) for state in self._states]
        initial = {replacements.get(state, state): self._initial[state] for state in self._states}
        labels = {replacements.get(state, state): self._labels[state] for state in self._states}

        def _update_edge(edge: Edge) -> Edge:
            if edge.source not in replacements and edge.target not in replacements:
                return edge

            source = replacements.get(edge.source, edge.source)
            target = replacements.get(edge.target, edge.target)
            return Edge(source, target)

        edges = [_update_edge(edge) for edge in self._edges]

        return Kripke(states, initial, labels, edges)


__all__ = ["Kripke", "State"]
