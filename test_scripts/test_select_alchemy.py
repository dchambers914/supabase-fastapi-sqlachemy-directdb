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
    params = {
        "sqlquery": "select 1 as one",
        "api_key": api_key,
    }
    url = endpoint + "?" + parse.urlencode(params)

    try:
        with request.urlopen(url) as resp:
            status = resp.getcode()
            body = resp.read().decode("utf-8", errors="replace")
            print(f"HTTP {status}")
            print(body)
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                print("Response is not valid JSON.")
                return 1

            if isinstance(data, list) and data and isinstance(data[0], dict) and data[0].get("one") in (1, "1"):
                print("SELECT test PASSED")
                return 0
            else:
                print("SELECT test FAILED: unexpected response payload")
                return 1
    except error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"HTTPError {e.code}")
        print(body)
        print("SELECT test FAILED: endpoint returned error")
        return 1
    except Exception as e:
        print(f"SELECT test FAILED: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())


