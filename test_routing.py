"""Run with:  python test_routing.py   (checks the algorithm without the website)"""
from mumbai_data import LOCATIONS, ROADS
from routing import find_route

ids = [loc[0] for loc in LOCATIONS]
place = {loc[1]: loc[0] for loc in LOCATIONS}
roads = [{"id": i, "from_id": a, "to_id": b, "time": t, "safety": s}
         for i, (a, b, t, s, *_rest) in enumerate(ROADS)]


def names(route):
    return [LOCATIONS[i][1] for i in route["path"]]


start, end = place["Mumbai Central"], place["Andheri"]
fast = find_route(ids, roads, start, end, 1.0)
safe = find_route(ids, roads, start, end, 0.0)
bal = find_route(ids, roads, start, end, 0.5)
for label, r in [("fastest", fast), ("balanced", bal), ("safest", safe)]:
    print(f"{label:>8}: {r['time']:3d} min, avg safety {r['avg_safety']}, worst {r['worst_safety']}  {' → '.join(names(r))}")

# The fastest route can never be slower than the others,
# and the safest route can never be less safe than the fastest.
assert fast["time"] <= bal["time"] and fast["time"] <= safe["time"]
assert safe["avg_safety"] >= fast["avg_safety"]
assert names(fast)[0] == "Mumbai Central" and names(fast)[-1] == "Andheri"
# On this trip each preference picks a different route.
assert len({tuple(fast["path"]), tuple(bal["path"]), tuple(safe["path"])}) == 3

same = find_route(ids, roads, start, start, 0.5)
assert same["path"] == [start] and same["time"] == 0, same

# A location with no roads cannot be reached.
assert find_route(ids + [99], roads, start, 99, 0.5) == {"found": False}

print("All routing tests passed.")
