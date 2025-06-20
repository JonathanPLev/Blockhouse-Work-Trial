from fee_map import get_venue_fees

ORDER_SIZE = 5000

def run_baselines(snapshots):
    if not snapshots:
        raise ValueError("No snapshots provided to run_baselines")
    return {
        "best_ask": best_ask(snapshots),
        "twap": twap(snapshots, interval=5),
        "vwap": vwap(snapshots)
    }

def best_ask(snapshots):
    quotes = [row for snap in snapshots for row in snap]
    if not quotes:
        raise ValueError("No quotes available in snapshots for best_ask")
    best_quote = min(quotes, key=lambda x: x["ask_px_00"])
    
    fee, _ = get_venue_fees(best_quote["publisher_id"])
    px = best_quote["ask_px_00"] + fee
    return {
        "total_cash": px * ORDER_SIZE,
        "avg_fill_px": px
    }

def twap(snapshots, interval):
    step = ORDER_SIZE // interval
    filled = 0
    cash = 0
    for i in range(interval):
        snap = snapshots[i % len(snapshots)]
        best = min(snap, key=lambda x: x["ask_px_00"])
        fee, _ = get_venue_fees(best["publisher_id"])
        px = best["ask_px_00"] + fee
        cash += step * px
        filled += step
    return {
        "total_cash": cash,
        "avg_fill_px": cash / filled
    }

def vwap(snapshots):
    weighted = []
    for snap in snapshots:
        for row in snap:
            fee, _ = get_venue_fees(row["publisher_id"])
            px = row["ask_px_00"] + fee
            size = row["ask_sz_00"]
            weighted.append((px, size))
    weighted.sort(key=lambda x: x[0])
    remaining = ORDER_SIZE
    cash = 0
    for px, size in weighted:
        fill = min(size, remaining)
        cash += px * fill
        remaining -= fill
        if remaining <= 0:
            break
    return {
        "total_cash": cash,
        "avg_fill_px": cash / ORDER_SIZE
    }
