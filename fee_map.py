VENUE_FEES = {
    "XNAS": (0.0030, 0.0020),
    "XNYS": (0.0025, 0.0015),
    "BATS": (0.0029, 0.0020),
    "EDGX": (0.0020, 0.0010),
    "ARCA": (0.0030, 0.0024)
}

DEFAULT_FEE = 0.0025
DEFAULT_REBATE = 0.0015

def get_venue_fees(venue):
    return VENUE_FEES.get(venue, (DEFAULT_FEE, DEFAULT_REBATE))
