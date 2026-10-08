from calc import add, divide


def test_add_passes():
    assert add(2, 3) == 5


def test_divide_fails_on_purpose():
    # Deliberately wrong expectation: the gate must surface this failure.
    assert divide(1, 4) == 0.5
