import os
import sys
import time
from urllib import request, parse, error

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


def hit(endpoint_path: str) -> int:
    base_url = os.environ.get("BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    api_key = os.environ.get("REX_API_KEY")
    if not api_key:
        print("REX_API_KEY not set in environment. Set it or put it in a .env file.")
        return 0
    url = f"{base_url}{endpoint_path}?" + parse.urlencode({
        "sqlquery": "select 1 as one",
        "api_key": api_key,
    })
    try:
        with request.urlopen(url) as resp:
            print(f"HTTP {resp.getcode()} (OK)")
            return resp.getcode()
    except error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"HTTPError {e.code}: {body}")
        return e.code


def main() -> int:
    # Endpoint to test: pass '/sqlquery_alchemy/' or '/sqlquery_direct/' via ENDPOINT env var
    endpoint_path = os.environ.get("ENDPOINT", "/sqlquery_alchemy/")
    print(f"Testing rate limit on {endpoint_path}")
    print("For a quick test, set RATE_LIMIT=2/minute in your server env and restart the server.")

    codes = []
    for i in range(3):
        print(f"Request {i+1}:")
        codes.append(hit(endpoint_path))
        # Tiny pause between requests
        time.sleep(0.1)

    # Expectation when RATE_LIMIT=2/minute: first two are 200, third is 429
    if len(codes) == 3 and codes[0] == 200 and codes[1] == 200 and codes[2] == 429:
        print("RATE-LIMIT test PASSED: third request blocked with 429")
        return 0
    else:
        print(f"RATE-LIMIT test result codes: {codes}. If you didn't set RATE_LIMIT low, this may be expected.")
        return 1


if __name__ == "__main__":
    sys.exit(main())


