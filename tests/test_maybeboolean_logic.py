from veg2hab.enums import MaybeBoolean


def test_true_false_and():
    assert MaybeBoolean.TRUE & MaybeBoolean.TRUE == MaybeBoolean.TRUE
    assert MaybeBoolean.TRUE & MaybeBoolean.FALSE == MaybeBoolean.FALSE
    assert MaybeBoolean.FALSE & MaybeBoolean.TRUE == MaybeBoolean.FALSE
    assert MaybeBoolean.FALSE & MaybeBoolean.FALSE == MaybeBoolean.FALSE


def test_true_false_or():
    assert MaybeBoolean.TRUE | MaybeBoolean.TRUE == MaybeBoolean.TRUE
    assert MaybeBoolean.TRUE | MaybeBoolean.FALSE == MaybeBoolean.TRUE
    assert MaybeBoolean.FALSE | MaybeBoolean.TRUE == MaybeBoolean.TRUE
    assert MaybeBoolean.FALSE | MaybeBoolean.FALSE == MaybeBoolean.FALSE


def test_true_false_invert():
    assert ~MaybeBoolean.TRUE == MaybeBoolean.FALSE
    assert ~MaybeBoolean.FALSE == MaybeBoolean.TRUE


def test_cast_to_bool():
    try:
        bool(MaybeBoolean.TRUE)
        assert False
    except RuntimeError:
        assert True


def test_cannot_be_automated_and():
    assert (
        MaybeBoolean.CANNOT_BE_AUTOMATED & MaybeBoolean.TRUE
        == MaybeBoolean.CANNOT_BE_AUTOMATED
    )
    assert MaybeBoolean.CANNOT_BE_AUTOMATED & MaybeBoolean.FALSE == MaybeBoolean.FALSE
    assert (
        MaybeBoolean.CANNOT_BE_AUTOMATED & MaybeBoolean.CANNOT_BE_AUTOMATED
        == MaybeBoolean.CANNOT_BE_AUTOMATED
    )
    assert (
        MaybeBoolean.CANNOT_BE_AUTOMATED & MaybeBoolean.FALSE & MaybeBoolean.TRUE
        == MaybeBoolean.FALSE
    )


def test_cannot_be_automated_or():
    assert MaybeBoolean.CANNOT_BE_AUTOMATED | MaybeBoolean.TRUE == MaybeBoolean.TRUE
    assert (
        MaybeBoolean.CANNOT_BE_AUTOMATED | MaybeBoolean.FALSE
        == MaybeBoolean.CANNOT_BE_AUTOMATED
    )
    assert (
        MaybeBoolean.CANNOT_BE_AUTOMATED | MaybeBoolean.CANNOT_BE_AUTOMATED
        == MaybeBoolean.CANNOT_BE_AUTOMATED
    )
    assert (
        MaybeBoolean.CANNOT_BE_AUTOMATED | MaybeBoolean.FALSE | MaybeBoolean.TRUE
        == MaybeBoolean.TRUE
    )


def test_cannot_be_automated_invert():
    assert ~MaybeBoolean.CANNOT_BE_AUTOMATED == MaybeBoolean.CANNOT_BE_AUTOMATED
