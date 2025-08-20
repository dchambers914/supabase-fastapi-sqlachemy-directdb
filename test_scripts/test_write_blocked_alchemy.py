import os
import json
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

    endpoint = f"{base_url.rstrip('/')}/sqlquery_alchemy/"
    # Attempt a harmless write against a temp table name that likely doesn't exist; we expect a DB error due to read-only
    params = {
        "sqlquery": "create table tmp_test_ro(id int)",
        "api_key": api_key,
    }
    url = endpoint + "?" + parse.urlencode(params)

    try:
        with request.urlopen(url) as resp:
            status = resp.getcode()
            body = resp.read().decode("utf-8", errors="replace")
            print(f"HTTP {status}")
            print(body)
            # If we reached here with 200, that's unexpected for a write in read-only
            print("WRITE-BLOCK test FAILED: write unexpectedly succeeded")
            return 1
    except error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"HTTPError {e.code}")
        print(body)
        # We expect a 500 from our API when DB rejects write in read-only
        if e.code in (400, 401, 403):
            print("WRITE-BLOCK test FAILED: auth/validation error instead of read-only rejection")
            return 1
        print("WRITE-BLOCK test PASSED: write was blocked by read-only")
        return 0
    except Exception as e:
        print(f"WRITE-BLOCK test FAILED: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())


