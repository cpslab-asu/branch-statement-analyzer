from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Generic, Iterable, Mapping, Sequence, TypeVar

_LabelT = TypeVar("_LabelT")


def _concat(lists: list[list[_LabelT]]) -> list[_LabelT]:
    return [elem for list_ in lists for elem in list_]


@dataclass(frozen=True)
class State:
    _id: uuid.UUID = field(init=False, default_factory=uuid.uuid4)


@dataclass(frozen=True)
class Edge:
    source: State
    target: State


class Kripke(Generic[_LabelT]):
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
        return self._states.copy()

    @property
    def initial_states(self) -> list[State]:
        return [state for state in self._states if self._initial[state] is True]

    def states_from(self, state: State) -> list[State]:
        if state not in self.states:
            raise ValueError(f"State {state} is not a member of Kripke structure")

        return [edge.target for edge in self._edges if edge.source == state] + [state]

    def add_labels(self, labels: list[_LabelT]) -> Kripke[_LabelT]:
        labels_ = {state: self._labels[state] + labels for state in self._states}
        return Kripke(self._states, self._initial, labels_, self._edges)

    def add_edge(self, source: State, target: State) -> Kripke[_LabelT]:
        if source not in self._states:
            raise ValueError(f"State {source} is not a member of Kripke structure")

        if target not in self._states:
            raise ValueError(f"State {target} is not a member of Kripke structure")

        edges = self._edges + [Edge(source, target)]
        return Kripke(self._states, self._initial, self._labels, edges)

    def labels_for(self, state: State) -> list[_LabelT]:
        if state not in self._states:
            raise ValueError(f"State {state} is not a member of Kripke structure")

        return self._labels[state].copy()

    def join(self, other: Kripke[_LabelT]) -> Kripke[_LabelT]:
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
        state = State()
        return cls([state], {state: True}, {state: labels}, [])

    def _replace_duplicates(self, states: Iterable[State]) -> Kripke[_LabelT]:
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
