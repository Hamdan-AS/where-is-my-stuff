#!/usr/bin/env python3
"""Exercise the actual HTTP routes against an explicitly isolated MySQL instance."""
import concurrent.futures
import http.cookiejar
import json
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
if os.environ.get("NED_TEST_MODE") != "1" or not os.environ.get("NED_DB_SOCKET", "").startswith("/tmp/ned-workflow-test."):
    raise SystemExit("Set NED_TEST_MODE=1 and an isolated NED_DB_SOCKET under /tmp/ned-workflow-test.*.")
assertions = 0

def check(condition, message):
    global assertions
    if not condition:
        raise AssertionError(message)
    assertions += 1
    print("PASS: " + message, flush=True)

def fixture(query=None, values=None, action=None):
    result = subprocess.run(["php", str(ROOT / "tests/db_fixture.php")],
        input=json.dumps({"query": query, "values": values or [], "action": action}),
        text=True, capture_output=True, check=True, cwd=ROOT)
    return json.loads(result.stdout)

def one(query, values=None):
    return fixture(query, values)[0]

class Client:
    def __init__(self):
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.csrf = ""
    def request(self, path, data=None):
        payload = None if data is None else urllib.parse.urlencode(data).encode()
        try:
            response = self.opener.open(base + "/" + path, payload, timeout=15)
        except urllib.error.HTTPError as error:
            response = error
        html = response.read().decode()
        token = re.search(r'name="csrf" value="([^"]+)"', html)
        if token:
            self.csrf = token.group(1)
        return response.status, html, response.url
    def post(self, path, data):
        return self.request(path, dict(data, csrf=self.csrf))
    def register(self, name, email):
        self.request("auth.php?mode=register")
        status, html, url = self.post("auth.php", {"mode":"register","name":name,"email":email,"password":"Student123"})
        check(status == 200 and url.endswith("index.php"), "register " + name)
    def login(self, email, password):
        self.request("auth.php")
        return self.post("auth.php", {"mode":"login","email":email,"password":password})

run = str(time.time_ns())
a, b, c, mod, admin = (Client() for _ in range(5))
wallet = {"colour":"Black","material":"Leather","visible_logo":"No","cnic_nic_present":"Yes","cnic_nic_last_3_digits":"123","bank_card_present":"No","distinguishing_mark":"Scratch"}
card = {"card_type":"Bank Card","issuer":"Meezan Bank","colour":"Green","masked_suffix":"7391","visible_mark":"Scratch"}
def report(client, kind="Lost", title="Wallet", category="Wallet / Purse", answers=None, id="", **changes):
    client.request("report_form.php" + ("?id="+str(id) if id else ""))
    data = {"id":str(id), "type":kind, "item_name":title, "category":category,
        "description":"black leather wallet", "location":"Central Library", "location_description":"By the entrance",
        "event_date":time.strftime("%Y-%m-%d"), "contact":"contact-private-" + title}
    data.update(changes)
    for key, value in (answers or wallet).items():
        data["answers_by_category["+category+"]["+key+"]"] = value
    return client.post("reports.php", data)

with socket.socket() as temporary:
    temporary.bind(("127.0.0.1", 0))
    port = temporary.getsockname()[1]
base = "http://127.0.0.1:" + str(port)
log_path = Path(os.environ["NED_DB_SOCKET"]).parent / "http-test.log"
env = dict(os.environ, PHP_CLI_SERVER_WORKERS="4")
with log_path.open("w") as log:
    server = subprocess.Popen(["php","-S","127.0.0.1:"+str(port),"router.php"], cwd=ROOT, env=env,
        stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    try:
        for _ in range(100):
            try:
                if Client().request("auth.php")[0] == 200:
                    break
            except urllib.error.URLError:
                time.sleep(.05)
        else:
            raise RuntimeError("PHP server failed: " + log_path.read_text())
        check(Client().request("index.php")[2].endswith("auth.php"), "unauthenticated dashboard redirects to login")
        for private_path in ["database.sql","config.php","data.sqlite","tests/db_fixture.php","scope-freeze.md"]:
            check(Client().request(private_path)[0] == 404, "router blocks " + private_path)
        for client, name in [(a,"Ahmed"),(b,"Sara"),(c,"Ali")]:
            client.register(name, name.lower()+run+"@example.test")
        aid = one("SELECT id FROM users WHERE email=?", ["ahmed"+run+"@example.test"])["id"]
        bid = one("SELECT id FROM users WHERE email=?", ["sara"+run+"@example.test"])["id"]
        cid = one("SELECT id FROM users WHERE email=?", ["ali"+run+"@example.test"])["id"]
        check(a.request("admin.php")[0] == 403, "Student cannot open management")
        check(mod.login("moderator@ned.edu.pk","Moderator@123")[0] == 200 and "Moderator" in mod.request("admin.php")[1], "Moderator seed password and page work")
        check(admin.login("admin@ned.edu.pk","Admin@123")[0] == 200 and "User roles" in admin.request("admin.php")[1], "Admin seed password and page work")
        check(a.request("reports.php")[0] == 405, "GET cannot mutate reports")
        check(a.request("reports.php", {"action":"delete","id":"1"})[0] == 403, "missing CSRF token blocks mutation")
        before = one("SELECT COUNT(*) AS n FROM reports")["n"]
        report(a, title="Invalid", event_date="2026-02-31")
        check(one("SELECT COUNT(*) AS n FROM reports")["n"] == before, "invalid date is rejected through HTTP")
        report(a, title="Full ID", category="Cards / IDs", answers=dict(card, masked_suffix="1234567890123456"))
        check(one("SELECT COUNT(*) AS n FROM reports")["n"] == before, "full card number rejected through HTTP")
        report(a, title="Lost "+run)
        lost = one("SELECT id FROM reports WHERE user_id=? ORDER BY id DESC LIMIT 1",[aid])["id"]
        report(a, kind="Found", title="Own found "+run)
        own_found = one("SELECT id FROM reports WHERE user_id=? ORDER BY id DESC LIMIT 1",[aid])["id"]
        check(not fixture("SELECT * FROM matches WHERE lost_report_id=?",[lost]), "same user's Lost and Found reports never match")
        report(b, kind="Found", title="Found "+run)
        found = one("SELECT id FROM reports WHERE user_id=? ORDER BY id DESC LIMIT 1",[bid])["id"]
        match = one("SELECT * FROM matches WHERE lost_report_id=? AND found_report_id=?",[lost,found])
        mid = match["id"]
        check(match["total_score"] == 100 and match["private_match_count"] == 9, "stored match has expected factor total and private count")
        page = a.request("index.php")[1]
        check("match.php?id="+str(mid) in page and "Possible Match" in page, "dashboard links to match and displays recovery status")
        check(c.request("match.php?id="+str(mid))[0] == 404, "unrelated user cannot read match")
        check(c.post("handover.php", {"match_id":mid,"action":"propose"})[0] == 404, "unrelated user cannot change match")
        check(c.request("report.php?id="+str(lost))[0] == 404, "unrelated user cannot read report details")
        check(c.request("report_form.php?id="+str(lost))[2].endswith("index.php"), "unrelated user cannot load another report's editor")
        c.post("reports.php", {"id":lost,"action":"delete"})
        check(bool(fixture("SELECT id FROM reports WHERE id=?",[lost])), "unrelated user cannot delete another report")
        c.post("reports.php", {"id":lost,"action":"close"})
        check(one("SELECT status FROM reports WHERE id=?",[lost])["status"] == "Open", "unrelated user cannot close another report")
        for who, path in [(a,"match.php?id="+str(mid)),(b,"index.php"),(mod,"admin.php")]:
            html = who.request(path)[1]
            check("Brand logo" not in html and "contact-private-" not in html, "private answers and contacts omitted from "+path)
        report(a, title="Lost "+run, id=lost, description="totally unrelated", location="Main Gate", answers={"colour":"Blue","material":"Fabric","cnic_nic_present":"No","bank_card_present":"No","distinguishing_mark":"None"})
        check(not fixture("SELECT id FROM matches WHERE lost_report_id=?",[lost]), "editing removes a stale possible match")
        report(a, title="Lost "+run, id=lost)
        mid = one("SELECT id FROM matches WHERE lost_report_id=? AND found_report_id=?",[lost,found])["id"]
        report(c, kind="Found", title="Competing "+run)
        other = one("SELECT m.id FROM matches m JOIN reports r ON r.id=m.found_report_id WHERE m.lost_report_id=? AND r.user_id=?",[lost,cid])["id"]
        meeting = time.strftime("%Y-%m-%dT%H:%M")
        with concurrent.futures.ThreadPoolExecutor() as pool:
            results = list(pool.map(lambda pair: pair[0].post("handover.php", {"match_id":pair[1],"action":"propose","location":"NED Security Office","meeting_at":meeting}), [(b,mid),(c,other)]))
        active = fixture("SELECT id FROM matches WHERE lost_report_id=? AND status='Handover Proposed'", [lost])
        check(len(active) == 1, "concurrent proposals cannot book one report twice")
        winner = active[0]["id"]
        proposer = b if winner == mid else c
        check("contact-private-" not in a.request("match.php?id="+str(winner))[1], "contacts remain hidden after only proposer acceptance")
        proposer.post("handover.php", {"match_id":winner,"action":"accept"})
        check(one("SELECT status FROM matches WHERE id=?",[winner])["status"] == "Handover Proposed", "proposer cannot accept twice")
        a.post("handover.php", {"match_id":winner,"action":"returned"})
        check(one("SELECT status FROM matches WHERE id=?",[winner])["status"] == "Handover Proposed", "cannot skip mutual acceptance")
        original_title = one("SELECT item_name FROM reports WHERE id=?",[lost])["item_name"]
        report(a, title="Unauthorized change", id=lost)
        check(one("SELECT item_name FROM reports WHERE id=?",[lost])["item_name"] == original_title, "report edit blocked during proposal")
        a.post("handover.php", {"match_id":winner,"action":"accept"})
        check(one("SELECT status FROM matches WHERE id=?",[winner])["status"] == "Handover Scheduled", "other participant schedules exact proposal")
        check("contact-private-" in a.request("match.php?id="+str(winner))[1], "participant contacts revealed after mutual acceptance")
        check("Handover Scheduled" in a.request("index.php")[1], "dashboard shows scheduled status")
        a.post("handover.php", {"match_id":winner,"action":"accept"})
        check(one("SELECT status FROM matches WHERE id=?",[winner])["status"] == "Handover Scheduled", "repeated acceptance does not change scheduled handover")
        a.post("handover.php", {"match_id":winner,"action":"returned"})
        check(one("SELECT status FROM matches WHERE id=?",[winner])["status"] == "Returned", "participant records completed return")
        check(one("SELECT status FROM reports WHERE id=?",[lost])["status"] == "Returned", "lost report becomes Returned")
        returned_found = one("SELECT found_report_id FROM matches WHERE id=?",[winner])["found_report_id"]
        check(one("SELECT status FROM reports WHERE id=?",[returned_found])["status"] == "Returned", "found report becomes Returned")
        check(one("SELECT COUNT(*) AS n FROM matches WHERE lost_report_id=? AND status NOT IN ('Returned','Rejected')",[lost])["n"] == 0, "return cancels competing suggestions")
        check(one("SELECT completed_at FROM handovers WHERE match_id=?",[winner])["completed_at"] is not None, "completion timestamp stored")
        check("Returned" in a.request("index.php")[1], "dashboard shows returned status")
        report(a, title="Card "+run, category="Cards / IDs", answers=card, description="student bank card")
        card_lost = one("SELECT id FROM reports WHERE user_id=? ORDER BY id DESC LIMIT 1",[aid])["id"]
        report(b, kind="Found", title="Card found "+run, category="Cards / IDs", answers=card, description="student bank card")
        card_match = one("SELECT id FROM matches WHERE lost_report_id=? ORDER BY id DESC LIMIT 1",[card_lost])["id"]
        check("7391" not in b.request("match.php?id="+str(card_match))[1], "card suffix never appears in match HTML")
        check("7391" not in mod.request("admin.php")[1], "staff do not see private card suffix")
        a.post("handover.php", {"match_id":card_match,"action":"propose","location":"Department Office","meeting_at":meeting})
        b.post("handover.php", {"match_id":card_match,"action":"reject"})
        check(one("SELECT status FROM matches WHERE id=?",[card_match])["status"] == "Rejected", "counterpart rejects proposal")
        report(a, title="Card edited "+run, id=card_lost, category="Cards / IDs", answers=card, description="student bank card")
        check(one("SELECT status FROM matches WHERE id=?",[card_match])["status"] == "Rejected", "editing does not revive a rejected pair")
        mod.post("moderation.php", {"action":"close_report","report_id":card_lost})
        check(one("SELECT status FROM reports WHERE id=?",[card_lost])["status"] == "Closed", "Moderator closes report")
        a.post("reports.php", {"action":"delete","id":card_lost})
        check(bool(fixture("SELECT id FROM reports WHERE id=?",[card_lost])), "student cannot delete a report")
        mod.post("moderation.php", {"action":"delete_report","report_id":card_lost})
        check(not fixture("SELECT id FROM reports WHERE id=?",[card_lost]), "management deletes a report")
        check(mod.post("moderation.php", {"action":"set_role","user_id":cid,"role":"Admin"})[0] == 403, "Moderator cannot change roles")
        admin.post("moderation.php", {"action":"set_role","user_id":cid,"role":"Moderator"})
        check(c.request("admin.php")[0] == 200, "Admin role assignment applies without logging out")
        admin.post("moderation.php", {"action":"set_role","user_id":cid,"role":"Student"})
        check(c.request("admin.php")[0] == 403, "role demotion applies to existing session")
        check(fixture(action="rollback") == 0, "transaction failure rolls back all report changes")
        a.post("logout.php", {})
        check(a.request("index.php")[2].endswith("auth.php"), "logout ends authenticated session")
        print(str(assertions) + " HTTP/database assertions passed.", flush=True)
    finally:
        os.killpg(server.pid, signal.SIGTERM)
        server.wait(timeout=10)
