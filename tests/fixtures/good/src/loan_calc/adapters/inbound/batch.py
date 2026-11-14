import logging
from loan_calc.shared.masking import mask_loan
from loan_calc.domain.rules import cutoff
log = logging.getLogger(__name__)


def run(loan_id, t):
    log.info("x %s", mask_loan(loan_id))
    return cutoff(t)
