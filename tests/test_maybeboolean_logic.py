import pytest

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
    with pytest.raises(RuntimeError):
        bool(MaybeBoolean.TRUE)

    with pytest.raises(RuntimeError):
        not MaybeBoolean.TRUE


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


def test_postpone_and():
    assert MaybeBoolean.POSTPONE & MaybeBoolean.TRUE == MaybeBoolean.POSTPONE
    assert MaybeBoolean.POSTPONE & MaybeBoolean.FALSE == MaybeBoolean.FALSE
    assert (
        MaybeBoolean.POSTPONE & MaybeBoolean.POSTPONE == MaybeBoolean.POSTPONE
    )
    assert (
        MaybeBoolean.POSTPONE & MaybeBoolean.FALSE & MaybeBoolean.TRUE
        == MaybeBoolean.FALSE
    )

def test_postpone_or():
    assert MaybeBoolean.POSTPONE | MaybeBoolean.TRUE == MaybeBoolean.TRUE
    assert MaybeBoolean.POSTPONE | MaybeBoolean.FALSE == MaybeBoolean.POSTPONE
    assert (
        MaybeBoolean.POSTPONE | MaybeBoolean.POSTPONE == MaybeBoolean.POSTPONE
    )
    assert (
        MaybeBoolean.POSTPONE | MaybeBoolean.FALSE | MaybeBoolean.TRUE
        == MaybeBoolean.TRUE
    )

def test_postpone_invert():
    assert ~MaybeBoolean.POSTPONE == MaybeBoolean.POSTPONE

def test_postpone_cannot_be_automated_interactions():
    # Postpone and cannot be automated should be cannot be automated, since it will never resolve to true
    assert MaybeBoolean.POSTPONE & MaybeBoolean.CANNOT_BE_AUTOMATED == MaybeBoolean.CANNOT_BE_AUTOMATED
    # Postpone or cannot be automated should be postpone, since it still might resolve to true if postponed
    assert MaybeBoolean.POSTPONE | MaybeBoolean.CANNOT_BE_AUTOMATED == MaybeBoolean.POSTPONE
