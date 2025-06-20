from allocator import allocate, compute_cost
from fee_map import get_venue_fees

ORDER_SIZE = 5000

def run_backtest(snapshots, lambda_over, lambda_under, theta_queue):
    filled = 0
    cash_spent = 0
    snapshot_index = 0

    while filled < ORDER_SIZE and snapshot_index < len(snapshots):
        snapshot = snapshots[snapshot_index]
        venues = []

        for row in snapshot:
            ask = row["ask_px_00"]
            ask_size = row["ask_sz_00"]
            venue = row["publisher_id"]
            fee, rebate = get_venue_fees(venue)
            venues.append({
                "ask": ask,
                "ask_size": ask_size,
                "fee": fee,
                "rebate": rebate
            })

        split, _ = allocate(ORDER_SIZE - filled, venues, lambda_over, lambda_under, theta_queue)
        print(f"Split: {split}")
        for i, shares in enumerate(split):
            executed = min(shares, venues[i]["ask_size"])
            cash_spent += executed * (venues[i]["ask"] + venues[i]["fee"])
            filled += executed
            print(f"Snapshot {snapshot_index}: Executed {executed}, Filled {filled}/{ORDER_SIZE}")

        snapshot_index += 1

    avg_px = cash_spent / filled if filled else 0

    return {
        "total_cash": cash_spent,
        "avg_fill_px": avg_px
    }
