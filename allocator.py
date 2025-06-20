def allocate(order_size, venues, λ_over, λ_under, θ_queue):
    step = max(1, order_size // 100)  # dynamic step
    splits = [[]]

    for v in range(len(venues)):
        new_splits = []
        for alloc in splits:
            used = sum(alloc)
            max_v = min(order_size - used, int(venues[v]['ask_size']))
            for q in range(0, max_v + 1, step):
                new_splits.append(alloc + [q])
        splits = new_splits

    best_cost = float('inf')
    best_split = []

    for alloc in splits:
        # Allow up to 1% underfill
        if sum(alloc) == 0:
            continue
        cost = compute_cost(alloc, venues, order_size, λ_over, λ_under, θ_queue)
        if cost < best_cost:
            best_cost = cost
            best_split = alloc

    if not best_split:
        print(f"⚠️ No valid allocation found for order size {order_size}")
        print(f"Venues: {[v['ask_size'] for v in venues]}")
    return best_split, best_cost



def compute_cost(split, venues, order_size, λo, λu, θ):
    executed = 0
    cash_spent = 0
    for i in range(len(venues)):
        exe = min(split[i], venues[i]['ask_size'])
        executed += exe
        cash_spent += exe * (venues[i]['ask'] + venues[i]['fee'])
        rebate = max(split[i] - exe, 0) * venues[i]['rebate']
        cash_spent -= rebate

    underfill = max(order_size - executed, 0)
    overfill = max(executed - order_size, 0)
    risk_pen = θ * (underfill + overfill)
    cost_pen = λu * underfill + λo * overfill
    return cash_spent + risk_pen + cost_pen
