from pytest import fixture

from bsa import Edge, Kripke, State


def kripke() -> Kripke:
    states = [State(), State()]
    initial = {
        states[0]: True,
        states[1]: True,
    }
    labels = {
        states[0]: [],
        states[1]: [],
    }
    edges = [
        Edge(states[0], states[1]),
        Edge(states[1], states[0]),
    ]

    return Kripke(states, initial, labels, edges)


@fixture
def k1() -> Kripke:
    return kripke()


@fixture
def k2() -> Kripke:
    return kripke()


def test_join(k1: Kripke, k2: Kripke):
    joined = k1.join(k2)
    assert len(joined.states) == 4
    assert len(joined.initial_states) == 4
    assert len(joined.edges) == 12
