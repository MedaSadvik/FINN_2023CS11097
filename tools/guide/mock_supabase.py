"""A tiny pretend Supabase, only to take screenshots for the user guide on a computer with no Supabase project.

    python tools/guide/mock_supabase.py            # listens on http://127.0.0.1:54321

It keeps everything in memory and understands just the calls the FINN website makes: sign up and sign in, profiles,
jobs, schools, connections, sample contacts. It is NOT the real database and does not enforce the real privacy rules
(those are tested against real Postgres in tests/test_rls.py). Never point a real deployment at it.
"""
import base64
import json
import re
import sys
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

ROOT_DEMO = [
    ("demo_priya", "Priya Iyer (demo)", "VP Supply Chain, Micron India",
     [("Texas Instruments India", "ti", "Design Engineer", 2010, 2014), ("Kaynes Technology", "kaynes", "Head of Operations", 2017, 2019),
      ("Micron India", "micron", "VP Supply Chain", 2019, None)], [("IIT Delhi", 2006, 2010)]),
    ("demo_kabir", "Kabir Shah (demo)", "Strategy Lead, Bajaj Finance",
     [("Titan Company", None, "Analyst", 2016, 2020), ("Asian Paints", None, "Brand Manager", 2020, 2023), ("Bajaj Finance", None, "Strategy Lead", 2023, None)],
     [("XLRI Jamshedpur", 2012, 2014)]),
    ("demo_meera", "Meera Nair (demo)", "Head of Digital Banking, HDFC Bank",
     [("Infosys", "infosys", "Senior Consultant", 2012, 2016), ("TCS", "tcs", "Engagement Manager", 2016, 2019),
      ("HDFC Bank", "hdfcbank", "Head of Digital Banking", 2019, None)], [("IIM Bangalore", 2010, 2012)]),
    ("rohan_mehta", "Rohan Mehta", "Portfolio Manager, a mutual fund",
     [("Dixon Technologies", "dixon", "Associate", 2015, 2018), ("Axis Mutual Fund", None, "Portfolio Manager", 2018, None)], [("IIM Ahmedabad", 2013, 2015)]),
]

S = {"users": {}, "profiles": {}, "roles": [], "edu": [], "conns": [], "people": [], "proles": [], "pedu": [], "seq": 0}


def nid():
    S["seq"] += 1
    return S["seq"]


def seed():
    for username, name, headline, roles, edu in ROOT_DEMO:
        uid = str(uuid.uuid4())
        S["users"][uid] = {"id": uid, "email": f"{username}@example.invalid", "password": None}
        S["profiles"][uid] = {"id": uid, "username": username, "display_name": name, "headline": headline}
        for n, k, t, a, b in roles:
            S["roles"].append({"id": nid(), "profile_id": uid, "employer_name": n, "employer_key": k, "title": t, "start_year": a, "end_year": b})
        for i, a, b in edu:
            S["edu"].append({"id": nid(), "profile_id": uid, "institution": i, "start_year": a, "end_year": b})


def jwt(uid):
    b = lambda d: base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()
    return f"{b({'alg': 'HS256', 'typ': 'JWT'})}.{b({'sub': uid, 'aud': 'authenticated', 'role': 'authenticated', 'exp': int(time.time()) + 36000, 'iat': int(time.time())})}.mock"


def user_json(u):
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return {"id": u["id"], "aud": "authenticated", "role": "authenticated", "email": u["email"], "email_confirmed_at": now,
            "app_metadata": {}, "user_metadata": {}, "created_at": now, "updated_at": now}


def session(u):
    return {"access_token": jwt(u["id"]), "token_type": "bearer", "expires_in": 36000, "expires_at": int(time.time()) + 36000,
            "refresh_token": "r-" + u["id"], "user": user_json(u)}


def connected(a, b):
    return any(c["status"] == "accepted" and {c["requester_id"], c["addressee_id"]} == {a, b} for c in S["conns"])


def link_people(a, b):
    """What the database trigger does when two people connect: each gets the other as a contact."""
    for owner, other in ((a, b), (b, a)):
        p = S["profiles"].get(other)
        if p and not any(x["owner_id"] == owner and x["profile_id"] == other for x in S["people"]):
            S["people"].append({"id": nid(), "owner_id": owner, "kind": "contact", "full_name": p["display_name"], "headline": p["headline"],
                                "last_spoke": None, "profile_id": other})


def visible(table, me):
    if table == "profiles":
        mine = {me} | {c["requester_id"] for c in S["conns"] if c["addressee_id"] == me} | {c["addressee_id"] for c in S["conns"] if c["requester_id"] == me}
        return [p for p in S["profiles"].values() if p["id"] in mine]
    if table in ("profile_roles", "profile_education"):
        rows = S["roles"] if table == "profile_roles" else S["edu"]
        return [r for r in rows if r["profile_id"] == me or connected(r["profile_id"], me)]
    if table == "connections":
        return [c for c in S["conns"] if me in (c["requester_id"], c["addressee_id"])]
    if table == "people":
        return [p for p in S["people"] if p["owner_id"] == me]
    if table == "network_roles":
        mine = {p["id"]: p for p in S["people"] if p["owner_id"] == me}
        out = [{"person_id": r["person_id"], **{k: r.get(k) for k in ("employer_key", "employer_name", "title", "start_year", "end_year")}}
               for r in S["proles"] if r["person_id"] in mine]
        for p in mine.values():
            if p["profile_id"] and connected(p["profile_id"], me):
                out += [{"person_id": p["id"], "employer_key": r["employer_key"], "employer_name": r["employer_name"], "title": r["title"],
                         "start_year": r["start_year"], "end_year": r["end_year"]} for r in S["roles"] if r["profile_id"] == p["profile_id"]]
        return out
    if table == "network_education":
        mine = {p["id"]: p for p in S["people"] if p["owner_id"] == me}
        out = [r for r in S["pedu"] if r["person_id"] in mine]
        for p in mine.values():
            if p["profile_id"] and connected(p["profile_id"], me):
                out += [{"person_id": p["id"], "institution": r["institution"], "start_year": r["start_year"], "end_year": r["end_year"]}
                        for r in S["edu"] if r["profile_id"] == p["profile_id"]]
        return out
    return []


def matches(row, key, expr):
    op, _, val = expr.partition(".")
    cell = row.get(key)
    if op == "eq": return str(cell) == val
    if op == "neq": return str(cell) != val
    if op == "in": return str(cell) in [v.strip('"') for v in val.strip("()").split(",")]
    if op == "is": return cell is None if val == "null" else str(cell).lower() == val
    return True


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, body=None):
        data = b"" if body is None else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def me(self):
        tok = (self.headers.get("Authorization") or "").removeprefix("Bearer ").strip()
        try:
            payload = json.loads(base64.urlsafe_b64decode(tok.split(".")[1] + "==="))
            return payload.get("sub") if payload.get("sub") in S["users"] else None
        except Exception:
            return None

    def body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"null") if n else None

    def do_GET(self): self.route("GET")
    def do_POST(self): self.route("POST")
    def do_PATCH(self): self.route("PATCH")
    def do_DELETE(self): self.route("DELETE")

    def route(self, method):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query, keep_blank_values=True).items()}
        try:
            if u.path.startswith("/auth/v1/"): return self.auth(method, u.path[9:], q)
            if u.path.startswith("/rest/v1/rpc/"): return self.rpc(u.path[13:])
            if u.path.startswith("/rest/v1/"): return self.table(method, u.path[9:], q)
            if u.path == "/__send_request" and method == "POST":
                d = self.body()
                by = {p["username"]: p["id"] for p in S["profiles"].values()}
                S["conns"].append({"id": nid(), "requester_id": by[d["from"]], "addressee_id": by[d["to"]], "status": "pending", "created_at": "now"})
                return self.send(200, {"ok": True})
            return self.send(404, {"message": "not found"})
        except Exception as e:  # a bug in this mock should be loud
            print("mock error:", repr(e), file=sys.stderr)
            return self.send(500, {"message": str(e)})

    # ------------------------------------------------------------------ auth
    def auth(self, method, path, q):
        if path == "user":
            me = self.me()
            return self.send(200, user_json(S["users"][me])) if me else self.send(401, {"message": "invalid JWT"})
        if path == "logout": return self.send(204)
        if path == "signup":
            d = self.body()
            if any(u["email"] == d["email"] for u in S["users"].values()): return self.send(422, {"msg": "User already registered"})
            u = {"id": str(uuid.uuid4()), "email": d["email"], "password": d["password"]}
            S["users"][u["id"]] = u
            return self.send(200, session(u))
        if path == "token":
            d = self.body()
            if q.get("grant_type") == "refresh_token":
                u = S["users"].get((d.get("refresh_token") or "")[2:])
            else:
                u = next((x for x in S["users"].values() if x["email"] == d.get("email") and x["password"] == d.get("password")), None)
            return self.send(200, session(u)) if u else self.send(400, {"error": "invalid_grant", "error_description": "Invalid login credentials"})
        return self.send(404, {"message": "not found"})

    # ------------------------------------------------------------------ tables
    def table(self, method, table, q):
        me = self.me()
        if not me and table != "companies_live": return self.send(200, [])
        store = {"profiles": None, "profile_roles": S["roles"], "profile_education": S["edu"], "connections": S["conns"]}
        filters = {k: v for k, v in q.items() if k not in ("select", "order", "limit", "offset", "columns", "on_conflict")}
        if method == "GET":
            rows = [r for r in visible(table, me) if all(matches(r, k, v) for k, v in filters.items())]
            if "order" in q:
                col, _, d = q["order"].partition(".")
                rows.sort(key=lambda r: (r.get(col) is None, r.get(col)), reverse=d.startswith("desc"))
            if "limit" in q: rows = rows[: int(q["limit"])]
            if "vnd.pgrst.object" in (self.headers.get("Accept") or ""):
                return self.send(200, rows[0]) if len(rows) == 1 else self.send(406, {"code": "PGRST116", "message": "no single row"})
            return self.send(200, rows)
        if table == "profiles":
            if method == "POST":
                d = self.body()
                if any(p["username"] == d["username"] for p in S["profiles"].values()):
                    return self.send(409, {"code": "23505", "message": "duplicate key value violates unique constraint"})
                S["profiles"][d["id"]] = {"id": d["id"], "username": d["username"], "display_name": d["display_name"], "headline": d.get("headline")}
                return self.send(201)
            if method == "PATCH":
                S["profiles"][me].update(self.body()); return self.send(204)
        if table in ("profile_roles", "profile_education"):
            rows = S["roles"] if table == "profile_roles" else S["edu"]
            if method == "POST":
                d = self.body(); d["id"] = nid(); rows.append(d); return self.send(201)
            if method == "DELETE":
                rows[:] = [r for r in rows if not (r["profile_id"] == me and all(matches(r, k, v) for k, v in filters.items()))]
                return self.send(204)
        if table == "connections" and method == "DELETE":
            S["conns"][:] = [c for c in S["conns"] if not (me in (c["requester_id"], c["addressee_id"]) and all(matches(c, k, v) for k, v in filters.items()))]
            return self.send(204)
        return self.send(204)

    # ------------------------------------------------------------------ functions
    def rpc(self, fn):
        me, d = self.me(), self.body() or {}
        if not me: return self.send(401, {"message": "sign in"})
        if fn == "request_connection":
            if me not in S["profiles"]: return self.send(400, {"message": "create your profile first"})
            other = next((p for p in S["profiles"].values() if p["username"] == d["p_username"]), None)
            if not other or other["id"] == me: return self.send(400, {"message": "No one with that username."})
            if connected(me, other["id"]): return self.send(200, "already_connected")
            if any({c["requester_id"], c["addressee_id"]} == {me, other["id"]} for c in S["conns"]): return self.send(200, "already_requested")
            demo = other["username"].startswith("demo_")
            S["conns"].append({"id": nid(), "requester_id": me, "addressee_id": other["id"], "status": "accepted" if demo else "pending", "created_at": "now"})
            if demo: link_people(me, other["id"])
            return self.send(200, "connected" if demo else "requested")
        if fn == "respond_connection":
            c = next((c for c in S["conns"] if c["id"] == d["p_id"] and c["addressee_id"] == me), None)
            if c and d["p_accept"]:
                c["status"] = "accepted"; link_people(c["requester_id"], c["addressee_id"])
            elif c:
                S["conns"].remove(c)
            return self.send(200, None)
        if fn == "load_sample_network":
            people = d["p"]["people"]
            for p in people:
                pid = nid()
                S["people"].append({"id": pid, "owner_id": me, "kind": p.get("kind", "contact"), "full_name": p["full_name"], "headline": p.get("headline"),
                                    "last_spoke": p.get("last_spoke"), "profile_id": None})
                for r in p.get("roles", []):
                    S["proles"].append({"person_id": pid, "employer_key": r.get("employer_key"), "employer_name": r.get("employer_name"), "title": r["title"],
                                        "start_year": r["start_year"], "end_year": r.get("end_year")})
                for e in p.get("education", []):
                    S["pedu"].append({"person_id": pid, "institution": e["institution"], "start_year": e["start_year"], "end_year": e["end_year"]})
            return self.send(200, len(people))
        if fn == "clear_sample_network":
            gone = {p["id"] for p in S["people"] if p["owner_id"] == me and not p["profile_id"]}
            S["people"][:] = [p for p in S["people"] if p["id"] not in gone]
            return self.send(200, None)
        if fn == "build_status":
            t = d.get("p_ticker", "")
            return self.send(200, {"state": "building", "message": None, "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())} if t == "TATASTEEL" else {"state": "none"})
        return self.send(200, None)


if __name__ == "__main__":
    seed()
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 54321
    print(f"mock Supabase on http://127.0.0.1:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
