from bsa import BranchTree, Comparison, Condition


def func(x1, x2):
    if x1 <= 10:
        if x2 >= 5:
            return x1 + x2
        else:
            return x2 - x1
    else:
        if x2 <= 20:
            return x1 + 2
        else:
            return x2 - 5


def test_branches():
    trees = BranchTree.from_function(func)
    assert len(trees) == 1

    tree = trees[0]
    assert tree.condition == Condition("x1", Comparison.LTE, 10, False)
    assert len(tree.true_children) == 1
    assert len(tree.false_children) == 1

    true_child = tree.true_children[0]
    assert true_child.condition == Condition("x2", Comparison.GTE, 5, False)
    assert len(true_child.true_children) == 0
    assert len(true_child.false_children) == 0

    false_child = tree.false_children[0]
    assert false_child.condition == Condition("x2", Comparison.LTE, 20, False)
    assert len(false_child.true_children) == 0
    assert len(false_child.false_children) == 0
