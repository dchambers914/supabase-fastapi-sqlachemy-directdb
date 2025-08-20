import os
import sys
from urllib import request, parse, error

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


def main() -> int:
    base_url = os.environ.get("BASE_URL", "http://127.0.0.1:8000")
    api_key = os.environ.get("REX_API_KEY")
    if not api_key:
        print("REX_API_KEY not set in environment. Set it or put it in a .env file.")
        return 2

    endpoint = f"{base_url.rstrip('/')}/sqlquery_direct/"
    sql = "select 1 as one; create table tmp_ro_multi_direct(id int)"
    url = endpoint + "?" + parse.urlencode({"sqlquery": sql, "api_key": api_key})

    try:
        with request.urlopen(url) as resp:
            status = resp.getcode()
            body = resp.read().decode("utf-8", errors="replace")
            print(f"HTTP {status}")
            print(body)
            print("MULTI-STMT (direct) test FAILED: server returned 200 for a multi-statement with write")
            return 1
    except error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"HTTPError {e.code}")
        print(body)
        # Expecting a DB error due to read-only or disallowed multi-statement execution
        if e.code in (400, 401, 403):
            print("MULTI-STMT (direct) test FAILED: unexpected auth/validation error")
            return 1
        print("MULTI-STMT (direct) test PASSED: multi-statement with write was blocked")
        return 0
    except Exception as e:
        print(f"MULTI-STMT (direct) test FAILED: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())


