from loan_calc.adapters.inbound.batch import run


def test_cutoff():
    """REGLA: R-013"""
    assert run("LN-1", 2001) is True
    assert run("LN-1", 2000) is False
