from backend.rest import app

with app.test_client() as c:
    rules = sorted(r.rule for r in app.url_map.iter_rules())
    print("\n".join(r for r in rules if "admin" in r or "health" in r))

    r = c.get("/api/health")
    print("health:", r.status_code, r.get_json())       # expect 200

    r = c.get("/api/health/db")
    print("health/db:", r.status_code, r.get_json())    # expect 200, "connected"

    r = c.get("/api/v1/admin/directory")
    print("admin/directory (no token):", r.status_code) # expect 401/403, NOT 404       