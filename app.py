import os
import logging
import re
from typing import Any, List, Dict
from urllib.parse import urlparse, unquote

from fastapi import FastAPI, HTTPException, Header, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from pydantic import BaseModel

from sqlalchemy import create_engine, text, event
from sqlalchemy.exc import SQLAlchemyError

import psycopg2
from psycopg2.extras import RealDictCursor

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

# ------------------ Config & Logging ------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("app")

RATE_LIMIT = os.getenv("RATE_LIMIT", "100/hour")
logger.info(f"Using rate limit: {RATE_LIMIT}")

REX_API_KEY = os.getenv("REX_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    logger.warning("DATABASE_URL is not set; queries will fail until configured.")
if not REX_API_KEY:
    logger.error("REX_API_KEY is not set; requests will be rejected.")

# Only allow queries that hit this table (set to None to disable)
ALLOWED_TABLE = "public.n8n"            # or "public.documentation"
ENFORCE_TABLE_RESTRICTION = False       # flip to True to enforce

# Safety regexes (used only if ENFORCE_TABLE_RESTRICTION=True)
SELECT_ONLY = re.compile(r"^\s*select\b", re.I)
FORBIDDEN = re.compile(
    r"--|/\*|\b(insert|update|delete|alter|drop|create|grant|revoke|truncate|copy|call|refresh|vacuum|analyze|set|reset)\b",
    re.I,
)  # NOTE: semicolon removed so 'SELECT ...;' is allowed
TABLES = re.compile(r"\b(from|join)\s+((?:\w+\.)?\w+)", re.I)

# ------------------ App & Middleware ------------------
app = FastAPI(title="Cricket Database PostgreSQL API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # lock down in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

limiter = Limiter(key_func=get_remote_address, default_limits=[RATE_LIMIT])
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

# ------------------ DB Engine ------------------
engine = None
if DATABASE_URL:
    # Ensure SSL even if the URL is missing ?sslmode=require
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args={"sslmode": "require"})

    @event.listens_for(engine, "connect")
    def set_session_readonly(dbapi_connection, connection_record):
        try:
            dbapi_connection.set_session(readonly=True, autocommit=False)
            logger.debug("Set DBAPI session to read-only")
        except Exception as e:
            logger.warning(f"Could not set DB session to read-only: {e}")

# Parse DSN only if available (for the /sqlquery_direct/ endpoint)
DB_HOST = DB_PORT = DB_NAME = DB_USER = DB_PASSWORD = None
if DATABASE_URL:
    parsed = urlparse(DATABASE_URL)
    DB_HOST = parsed.hostname
    DB_PORT = parsed.port
    DB_NAME = (parsed.path or "/")[1:]
    DB_USER = parsed.username
    DB_PASSWORD = parsed.password  # urlparse returns decoded password

# ------------------ Models ------------------
class QueryBody(BaseModel):
    sqlquery: str

# ------------------ Helpers ------------------
def _require_key(provided: str) -> None:
    if not REX_API_KEY:
        raise HTTPException(status_code=500, detail="Server misconfigured: REX_API_KEY not set")
    if provided != REX_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

def _validate_sql_for_n8n(raw: str) -> str:
    """Optional: enforce SELECT only + restrict table to ALLOWED_TABLE."""
    q = unquote(raw).strip()
    if not SELECT_ONLY.search(q):
        raise HTTPException(status_code=400, detail="Only SELECT statements are allowed.")
    if FORBIDDEN.search(q):
        raise HTTPException(status_code=400, detail="Forbidden token/statement detected.")
    if ENFORCE_TABLE_RESTRICTION and ALLOWED_TABLE:
        allowed = {ALLOWED_TABLE.lower(), ALLOWED_TABLE.split(".", 1)[-1].lower()}
        refs = [m.group(2).lower() for m in TABLES.finditer(q)]
        if not refs:
            raise HTTPException(status_code=400, detail="Query must reference a table.")
        for t in refs:
            if t not in allowed:
                raise HTTPException(
                    status_code=403,
                    detail=f"Only {ALLOWED_TABLE} is allowed (found reference to '{t}').",
                )
    return q

def _run_query(sqlquery: str) -> Any:
    if engine is None:
        raise HTTPException(status_code=500, detail="Server misconfigured: DATABASE_URL not set")

    # Enforce read-only semantics and optional table restriction
    sql = _validate_sql_for_n8n(sqlquery)

    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            rows = [dict(row._mapping) for row in result]
        return rows
    except SQLAlchemyError as e:
        logger.exception("Database error while running query")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

# ------------------ Routes ------------------
@app.get("/health")
@limiter.exempt
def health():
    return {"status": "ok"}

# GET (supports both with/without trailing slash)
@app.get("/sqlquery_alchemy")
@app.get("/sqlquery_alchemy/")
@limiter.limit(RATE_LIMIT)
def execute_sqlalchemy_query_get(
    request: Request,
    sqlquery: str = Query(..., alias="sqlquery"),
    api_key: str = Query(..., alias="api_key")
):
    _require_key(api_key)
    return _run_query(sqlquery)

# POST + header
@app.post("/sqlquery_alchemy")
@limiter.limit(RATE_LIMIT)
def execute_sqlalchemy_query_post(
    request: Request,
    body: QueryBody,
    x_api_key: str = Header(None)
):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    _require_key(x_api_key)
    return _run_query(body.sqlquery)

# Optional: direct psycopg2 path (read-only)
@app.get("/sqlquery_direct/")
@limiter.limit(RATE_LIMIT)
def sqlquery_direct(request: Request, sqlquery: str, api_key: str) -> Any:
    _require_key(api_key)
    if not (DB_HOST and DB_PORT and DB_NAME and DB_USER and DB_PASSWORD):
        raise HTTPException(status_code=500, detail="Server misconfigured: DATABASE_URL not set")

    try:
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
            user=DB_USER, password=DB_PASSWORD,
            cursor_factory=RealDictCursor,
            sslmode="require"  # Supabase requires TLS
        )
        try:
            with conn.cursor() as cur:
                cur.execute(_validate_sql_for_n8n(sqlquery))
                return list(cur.fetchall())
        finally:
            conn.close()
    except psycopg2.Error as e:
        logger.error(f"PostgreSQL error: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

@app.get("/", include_in_schema=False)
@limiter.exempt
def root():
    return {"status": "ok", "name": "Strouse KB API", "version": "1.0.0"}

@app.head("/", include_in_schema=False)
@limiter.exempt
def root_head():
    return Response(status_code=200)

# Rate limit handler
@app.exception_handler(RateLimitExceeded)
def ratelimit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": "Rate limit exceeded. Please try again later or contact your administrator."}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
