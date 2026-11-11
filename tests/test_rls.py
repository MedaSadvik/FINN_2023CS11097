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
    psql("insert into employers(key,name,sector) values ('syrma','Syrma SGS','electronics'),('kaynes','Kaynes','electronics');")
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
