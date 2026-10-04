"""Initialize local credentials and a non-superuser Django role. Not for RDS."""
import secrets
from pathlib import Path
from urllib.parse import urlsplit

import psycopg
from psycopg import sql
from dotenv import dotenv_values

root = Path(__file__).resolve().parent.parent
path = root / ".env"
if not path.exists():
    path.write_text(
        f"POSTGRES_PASSWORD={secrets.token_urlsafe(32)}\n"
        f"DATABASE_URL=postgresql://wims:{secrets.token_urlsafe(32)}@127.0.0.1:55432/wims\n",
        encoding="utf-8",
    )
    print("Local credentials created. Start docker compose, then rerun this script.")
    raise SystemExit(0)
env = dotenv_values(path)
url = urlsplit(env["DATABASE_URL"])
if url.hostname != "127.0.0.1" or url.port != 55432 or url.username != "wims" or url.path != "/wims":
    raise SystemExit("This bootstrap is restricted to the local compose database.")
with psycopg.connect(host=url.hostname, port=url.port, user="postgres", password=env["POSTGRES_PASSWORD"], dbname="postgres", autocommit=True) as conn:
    if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname='wims'").fetchone():
        conn.execute(sql.SQL("CREATE ROLE wims LOGIN CREATEDB PASSWORD {}").format(sql.Literal(url.password)))
    if not conn.execute("SELECT 1 FROM pg_database WHERE datname='wims'").fetchone():
        conn.execute("CREATE DATABASE wims OWNER wims")
print("Local app database ready. Role wims is not a superuser; CREATEDB supports isolated tests.")
