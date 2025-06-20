import json
from backtest_runner import run_backtest
from baseline_strategies import run_baselines

# --- Search Space ---
lambda_overs = [0.1, 0.3, 0.5]
lambda_unders = [0.1, 0.3, 0.5]
theta_queues = [0.0, 0.1, 0.2]

# --- Load Historical Snapshots from Kafka (or cache if needed) ---
with open("snapshots.json", "r") as f:
    all_snapshots = json.load(f)

if not all_snapshots:
    print("Error: snapshots.json is empty. No data to backtest. Exiting.")
    exit(1)


# --- Search over parameters ---
best_result = {"cost": float("inf")}
results = []

for lo in lambda_overs:
    for lu in lambda_unders:
        for tq in theta_queues:
            outcome = run_backtest(all_snapshots, lo, lu, tq)
            results.append(outcome)
            if outcome["total_cash"] < best_result["cost"]:
                best_result = {
                    "lambda_over": lo,
                    "lambda_under": lu,
                    "theta_queue": tq,
                    "cost": outcome["total_cash"],
                    "avg_fill_px": outcome["avg_fill_px"]
                }

# --- Run Baselines ---
baselines = run_baselines(all_snapshots)

# --- Compare Savings (in basis points) ---
bps_savings = {
    name: round((baseline["total_cash"] - best_result["cost"]) / baseline["total_cash"] * 10000, 1)
    for name, baseline in baselines.items()
}

# --- Output JSON ---
report = {
    "best_parameters": {
        "lambda_over": best_result["lambda_over"],
        "lambda_under": best_result["lambda_under"],
        "theta_queue": best_result["theta_queue"],
    },
    "optimized": {
        "total_cash": round(best_result["cost"]),
        "avg_fill_px": round(best_result["avg_fill_px"], 4)
    },
    "baselines": baselines,
    "savings_vs_baselines_bps": bps_savings
}

with open("execution_report.json", "w") as f:
    json.dump(report, f, indent=2)

print("✅ Report written to execution_report.json")
