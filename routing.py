"""
Route finding: Dijkstra's algorithm with a user-preference cost.
This file has no web or database code, so it can be tested on its own.

Same cost model as saferoute.c:
    risk = time * (10 - safety)
    cost = w * time/maxTime + (1 - w) * risk/maxRisk
    w = 1.0 -> fastest, w = 0.0 -> safest, 0.5 -> balanced
"""
import math

MAX_SAFETY = 10


def risk(road):
    return road["time"] * (MAX_SAFETY - road["safety"])


def find_route(location_ids, roads, src, dst, w):
    """
    location_ids: list of vertex ids
    roads: list of dicts with keys id, from_id, to_id, time, safety
    Returns a dict describing the cheapest route for preference w.
    """
    max_time = max((r["time"] for r in roads), default=1) or 1
    max_risk = max((risk(r) for r in roads), default=1) or 1

    # Build an adjacency list: vertex -> list of (neighbour, road).
    adj = {v: [] for v in location_ids}
    for r in roads:
        adj[r["from_id"]].append((r["to_id"], r))
        adj[r["to_id"]].append((r["from_id"], r))

    dist = {v: math.inf for v in location_ids}
    prev = {}   # vertex -> vertex we came from
    via = {}    # vertex -> road we used to get here
    visited = set()
    dist[src] = 0

    while True:
        # Greedy step: pick the unvisited vertex with the smallest distance.
        # (Simple O(V^2) version, like the C program. A heap would make this faster.)
        u = min((v for v in location_ids if v not in visited), key=lambda v: dist[v], default=None)
        if u is None or dist[u] == math.inf or u == dst:
            break
        visited.add(u)

        for v, road in adj[u]:
            cost = w * road["time"] / max_time + (1 - w) * risk(road) / max_risk
            if v not in visited and dist[u] + cost < dist[v]:
                dist[v] = dist[u] + cost
                prev[v] = u
                via[v] = road

    if dist.get(dst, math.inf) == math.inf:
        return {"found": False}

    # Walk backwards from the destination to rebuild the path.
    path, used = [dst], []
    while path[-1] != src:
        used.append(via[path[-1]])
        path.append(prev[path[-1]])
    path.reverse()
    used.reverse()

    time = sum(r["time"] for r in used)
    return {
        "found": True,
        "path": path,
        "road_ids": [r["id"] for r in used],
        "time": time,
        "avg_safety": round(sum(r["time"] * r["safety"] for r in used) / time, 1) if time else None,
        "worst_safety": min((r["safety"] for r in used), default=None),
    }
