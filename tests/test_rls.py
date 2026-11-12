"""Privacy rules for profiles and connections, tested against a REAL Postgres.

Skipped unless TEST_DATABASE_URL points at an empty scratch database, e.g.
    TEST_DATABASE_URL=postgresql://postgres:test@localhost/finn_test python -m pytest tests/test_rls.py
Never point it at a database you care about: the test drops and recreates the public schema.
"""
import os
import subprocess
from pathlib import Path

import pytest

URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="set TEST_DATABASE_URL to run the privacy tests")
ROOT = Path(__file__).resolve().parent.parent
ALICE, BOB, CARA = ("00000000-0000-0000-0000-00000000000%d" % i for i in (1, 2, 3))

AUTH_STUB = """
drop schema if exists public cascade; create schema public;
drop schema if exists auth cascade; create schema auth;
create table auth.users (id uuid primary key);
create function auth.uid() returns uuid language sql stable as
  $$ select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid $$;
do $$ begin
  if not exists (select 1 from pg_roles where rolname = 'authenticated') then create role authenticated nologin; end if;
  if not exists (select 1 from pg_roles where rolname = 'anon') then create role anon nologin; end if;
end $$;
grant usage on schema public, auth to authenticated, anon;
alter default privileges in schema public grant all on tables to authenticated, anon;
alter default privileges in schema public grant all on sequences to authenticated, anon;
"""


def psql(sql: str, user=None, role="authenticated", check=True):
    # user=None with a role means "connected, but not signed in" (the anon key); neither means superuser setup
    pre = (f"set request.jwt.claim.sub = '{user}'; " if user else "") + (f"set role {role}; " if (user or role == "anon") else "")
    r = subprocess.run(["psql", URL, "-q", "-v", "ON_ERROR_STOP=1", "-At", "-F", "|", "-c", pre + sql],
                       capture_output=True, text=True)
    if check and r.returncode:
        raise AssertionError(r.stderr)
    return r if not check else r.stdout.strip()


def fails(sql, user, role="authenticated"):
    return psql(sql, user, role, check=False).returncode != 0


@pytest.fixture(autouse=True)
def fresh():
    psql(AUTH_STUB)
    psql((ROOT / "db" / "schema.sql").read_text())
    psql((ROOT / "db" / "migrations" / "002_profiles_connections.sql").read_text())
    # alter default privileges in the stub already gave the roles table access; the migration then
    # revokes/grants precisely, so tests see the real rules. Re-apply them last:
    psql((ROOT / "db" / "migrations" / "003_sample_network.sql").read_text())
    psql((ROOT / "db" / "migrations" / "004_on_demand_build.sql").read_text())
    psql((ROOT / "db" / "migrations" / "005_free_text_employers.sql").read_text())
    psql((ROOT / "db" / "seed_reference.sql").read_text())
    for i, u in enumerate((ALICE, BOB, CARA)):
        psql(f"insert into auth.users values ('{u}')")
        psql(f"insert into profiles(id,username,display_name,headline) values ('{u}','{['alice','bob','cara'][i]}','{['Alice','Bob','Cara'][i]}','h{i}')", u)
    psql("insert into profile_roles(profile_id,employer_name,employer_key,title,start_year,end_year) "
         f"values ('{BOB}','Syrma SGS','syrma','Head of Ops',2019,2023)", BOB)
    psql(f"insert into profile_education(profile_id,institution,start_year,end_year) values ('{BOB}','IIT Delhi',2010,2014)", BOB)


def connect(a_user, b_username, b_user):
    assert psql(f"select request_connection('{b_username}')", a_user) == "requested"
    row = psql(f"select id from connections", b_user)
    psql(f"select respond_connection({row}, true)", b_user)


def test_strangers_see_nothing():
    assert psql("select count(*) from profiles", ALICE) == "1"           # only herself
    assert psql("select count(*) from profile_roles", ALICE) == "0"
    assert psql("select count(*) from profile_education", ALICE) == "0"


def test_lookup_is_exact_and_minimal():
    assert psql("select count(*) from find_user('bo')", ALICE) == "0"
    assert psql("select * from find_user(' BOB ')", ALICE) == "bob|Bob"   # name only, case-insensitive
    assert psql("select count(*) from find_user('alice')", ALICE) == "0"  # not yourself
    assert fails("select * from find_user('bob')", None, role="anon")


def test_pending_shows_name_but_not_career():
    assert psql("select request_connection('bob')", ALICE) == "requested"
    assert psql("select display_name from profiles where id = '%s'" % BOB, ALICE) == "Bob"
    assert psql("select display_name from profiles where id = '%s'" % ALICE, BOB) == "Alice"
    assert psql("select count(*) from profile_roles", ALICE) == "0"
    assert psql("select count(*) from profiles where id = '%s'" % CARA, ALICE) == "0"


def test_connection_cannot_be_forged_or_self_accepted():
    assert fails(f"insert into connections(requester_id,addressee_id,status) values ('{ALICE}','{BOB}','accepted')", ALICE)
    psql("select request_connection('bob')", ALICE)
    cid = psql("select id from connections", ALICE)
    assert fails(f"select respond_connection({cid}, true)", ALICE)           # requester cannot accept
    assert fails(f"update connections set status='accepted' where id={cid}", ALICE)
    assert fails(f"select respond_connection({cid}, true)", CARA)            # a stranger cannot either
    assert psql("select count(*) from connections", CARA) == "0"


def test_accept_shares_career_and_links_address_books():
    connect(ALICE, "bob", BOB)
    assert psql("select title from profile_roles", ALICE) == "Head of Ops"
    assert psql("select institution from profile_education", ALICE) == "IIT Delhi"
    assert psql("select full_name||'|'||synthetic from people", ALICE) == "Bob|false"
    assert psql("select full_name from people", BOB) == "Alice"
    assert psql("select count(*) from profile_roles", CARA) == "0"           # a third person still sees nothing
    # Alice does not see Cara, who has not connected
    assert psql("select count(*) from profiles", ALICE) == "2"


def test_call_sheet_view_reads_live_career_and_follows_edits():
    connect(ALICE, "bob", BOB)
    assert psql("select employer_key||'|'||title from network_roles", ALICE) == "syrma|Head of Ops"
    psql("update profile_roles set title = 'VP Operations'", BOB)
    assert psql("select title from network_roles", ALICE) == "VP Operations"
    assert psql("select count(*) from network_roles", CARA) == "0"


def test_private_notes_stay_private():
    connect(ALICE, "bob", BOB)
    psql("update people set notes = 'met at conference', last_spoke = '2026-05-01'", ALICE)
    assert psql("select count(*) from people where notes is not null", BOB) == "0"
    assert psql("select notes from people", BOB) == ""


def test_reverse_request_connects_immediately():
    psql("select request_connection('bob')", ALICE)
    assert psql("select request_connection('alice')", BOB) == "connected"
    assert psql("select request_connection('bob')", ALICE) == "already_connected"
    assert psql("select count(*) from connections", ALICE) == "1"


def test_duplicates_and_self_and_unknown_are_refused():
    psql("select request_connection('bob')", ALICE)
    assert psql("select request_connection('bob')", ALICE) == "already_requested"
    assert fails("select request_connection('alice')", ALICE)
    assert "No user with that username" in psql("select request_connection('nobody')", ALICE, check=False).stderr


def test_decline_removes_the_request_and_removing_hides_career_again():
    psql("select request_connection('bob')", ALICE)
    psql(f"select respond_connection({psql('select id from connections', BOB)}, false)", BOB)
    assert psql("select count(*) from connections", ALICE) == "0"
    connect(ALICE, "bob", BOB)
    psql("delete from connections", BOB)                                      # either side can remove
    assert psql("select count(*) from profile_roles", ALICE) == "0"
    assert psql("select count(*) from people", ALICE) == "0" and psql("select count(*) from people", BOB) == "0"


def test_nobody_edits_someone_elses_profile_or_career():
    connect(ALICE, "bob", BOB)
    assert psql("update profiles set headline='hacked' where id = '%s' returning id" % BOB, ALICE) == ""
    assert psql("update profile_roles set title='x' returning id", ALICE) == ""
    assert fails(f"insert into profile_roles(profile_id,employer_name,title,start_year) values ('{BOB}','X','y',2020)", ALICE)
    assert fails(f"insert into profiles(id,username,display_name) values ('{CARA}','cara2','C')", ALICE)


def test_input_rules():
    for bad in ("Al", "has space", "UPPER", "x" * 21, "dash-name"):
        assert fails(f"update profiles set username='{bad}' where id='{ALICE}'", ALICE), bad
    assert fails(f"update profiles set username='bob' where id='{ALICE}'", ALICE)  # unique
    assert fails(f"insert into profile_roles(profile_id,employer_name,title,start_year,end_year) values ('{ALICE}','X','y',2020,2010)", ALICE)


def test_profile_edit_updates_linked_contact_name():
    connect(ALICE, "bob", BOB)
    psql("update profiles set display_name='Robert', headline='New role'", BOB)
    assert psql("select full_name||'|'||headline from people", ALICE) == "Robert|New role"


def test_anonymous_has_no_access():
    for t in ("profiles", "profile_roles", "connections"):
        assert fails(f"select 1 from {t}", None, role="anon"), t


def sample_json():
    import json
    d = json.loads((ROOT / "data" / "network" / "synthetic_network.json").read_text())
    return json.dumps({"people": d["people"]}).replace("'", "''"), len(d["people"])


def test_reference_seed_loads_and_is_repeatable():
    psql((ROOT / "db" / "seed_reference.sql").read_text())                # second run changes nothing
    assert int(psql("select count(*) from companies")) == 17
    assert int(psql("select count(*) from employers")) > 10


def test_sample_network_loads_privately_and_replaces_itself():
    payload, n = sample_json()
    assert psql(f"select load_sample_network('{payload}'::jsonb)", ALICE) == str(n)
    assert psql("select count(*) from people where synthetic", ALICE) == str(n)
    assert psql("select count(*) from people", BOB) == "0"                    # nobody else sees it
    assert int(psql("select count(*) from roles", ALICE)) > 0
    psql(f"select load_sample_network('{payload}'::jsonb)", ALICE)             # loading twice does not duplicate
    assert psql("select count(*) from people where synthetic", ALICE) == str(n)
    assert fails(f"select load_sample_network('{payload}'::jsonb)", None, role="anon")


def test_sample_network_never_touches_real_connections():
    connect(ALICE, "bob", BOB)
    payload, n = sample_json()
    psql(f"select load_sample_network('{payload}'::jsonb)", ALICE)
    assert psql("select count(*) from people where profile_id is not null", ALICE) == "1"
    psql("select clear_sample_network()", ALICE)
    assert psql("select count(*) from people", ALICE) == "1"                  # only Bob is left


# ---------------------------------------------------------------- on-demand company builds
def ask(user, ticker):
    import json
    return json.loads(psql(f"select request_build('{ticker}')", user))


def test_build_needs_sign_in_and_a_sane_ticker():
    assert fails("select request_build('INFY')", None, role="anon")
    assert ask(ALICE, "infy")["state"] == "queued"                    # case-insensitive
    assert ask(ALICE, "bad ticker!")["state"] == "bad_ticker"
    assert ask(ALICE, "")["state"] == "bad_ticker"
    assert ask(ALICE, "X" * 21)["state"] == "bad_ticker"


def test_nobody_can_write_build_tables_directly():
    for sql in ("insert into build_requests(ticker, requested_by) values ('TCS', '%s')" % ALICE,
                "insert into companies_live(ticker,name,provider,data) values ('TCS','TCS','gemini','{}')",
                "update build_limits set global_per_day = 9999"):
        assert fails(sql, ALICE), sql
    assert fails("select count(*) from build_requests", None, role="anon")
    assert fails("select count(*) from build_limits", ALICE)


def test_same_ticker_is_not_built_twice_at_once():
    assert ask(ALICE, "TCS")["state"] == "queued"
    again = ask(BOB, "TCS")
    assert again["state"] == "in_progress"                            # no second job, no second budget use
    assert psql("select count(*) from build_requests", ALICE) == "1"


def test_per_user_and_global_caps():
    psql("update build_limits set per_user_per_day = 2, global_per_day = 3")
    assert ask(ALICE, "AAA")["state"] == "queued"
    assert ask(ALICE, "BBB")["state"] == "queued"
    assert ask(ALICE, "CCC")["state"] == "user_limit"
    assert ask(BOB, "DDD")["state"] == "queued"
    r = ask(CARA, "EEE")
    assert r["state"] == "global_limit" and "limit" in r["message"].lower()


def test_no_data_and_not_started_do_not_use_budget():
    psql("update build_limits set per_user_per_day = 1")
    rid = ask(ALICE, "NOPE")["request_id"]
    psql(f"update build_requests set status = 'no_data', message = 'No transcripts.' where id = {rid}")  # the job
    assert ask(BOB, "NOPE") == {"state": "no_data", "message": "No transcripts."}   # cached for a day
    assert ask(ALICE, "REAL")["state"] == "queued"                    # the failed lookup cost nothing
    rid = ask(BOB, "OTHER")["request_id"]
    psql(f"select mark_not_started({rid})", BOB)
    assert psql("select status from build_requests where ticker = 'OTHER'", BOB) == "not_started"
    assert ask(BOB, "THIRD")["state"] == "queued"
    assert psql(f"select mark_not_started({rid})", ALICE) == ""       # someone else's request: no effect


def test_requests_are_private_but_status_is_public():
    ask(ALICE, "TCS")
    assert psql("select count(*) from build_requests", ALICE) == "1"
    assert psql("select count(*) from build_requests", BOB) == "0"
    import json
    st = json.loads(psql("select build_status('tcs')", None, role="anon"))
    assert st["state"] == "queued" and set(st) == {"state", "message", "updated_at"}   # no user ids leak
    assert json.loads(psql("select build_status('NONE')", None, role="anon"))["state"] == "none"


def test_built_company_is_public_and_stops_new_requests():
    psql("insert into companies_live(ticker,name,provider,data) values ('TCS','TCS','gemini','{\"promises\":[]}')")  # the job
    assert psql("select name from companies_live where ticker = 'TCS'", None, role="anon") == "TCS"
    assert ask(ALICE, "TCS")["state"] == "exists"


# ---------------------------------------------------------------- free-text employers in the Call Sheet view
def test_free_text_roles_reach_connections_but_not_strangers():
    psql("insert into profile_roles(profile_id,employer_name,title,start_year,end_year) "
         f"values ('{BOB}','Titan Company','Analyst',2018,2021)", BOB)
    assert psql("select count(*) from network_roles where employer_name = 'Titan Company'", ALICE) == "0"  # not connected
    connect(ALICE, "bob", BOB)
    assert psql("select employer_key is null, employer_name, title from network_roles "
                "where employer_name = 'Titan Company'", ALICE) == "t|Titan Company|Analyst"
    assert psql("select count(*) from network_roles where employer_name = 'Titan Company'", CARA) == "0"  # a stranger still sees nothing
    psql("delete from connections", ALICE)                                                                    # remove the connection
    assert psql("select count(*) from network_roles where employer_name = 'Titan Company'", ALICE) == "0"


def test_linked_and_sample_roles_keep_their_names():
    psql("select load_sample_network('{\"people\":[{\"kind\":\"contact\",\"full_name\":\"S\",\"headline\":\"h\","
         "\"roles\":[{\"employer_key\":\"syrma\",\"title\":\"t\",\"start_year\":2020}],\"education\":[]}]}')", ALICE)
    assert psql("select employer_key, employer_name from network_roles where employer_key = 'syrma'", ALICE) == "syrma|Syrma SGS"
