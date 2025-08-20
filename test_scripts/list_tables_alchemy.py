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
	sql = (
		"select table_schema, table_name "
		"from information_schema.tables "
		"where table_type='BASE TABLE' "
		"and table_schema not in ('pg_catalog','information_schema') "
		"order by 1,2"
	)
	params = {
		"sqlquery": sql,
		"api_key": api_key,
	}
	url = endpoint + "?" + parse.urlencode(params)

	try:
		with request.urlopen(url) as resp:
			status = resp.getcode()
			body = resp.read().decode("utf-8", errors="replace")
			print(f"HTTP {status}")
			try:
				data = json.loads(body)
			except json.JSONDecodeError:
				print("Response is not valid JSON.")
				return 1

			if isinstance(data, list):
				print(f"Found {len(data)} tables")
				for row in data[:20]:
					print(f"- {row.get('table_schema')}.{row.get('table_name')}")
				return 0
			else:
				print("Unexpected response payload (expected a list)")
				return 1
	except error.HTTPError as e:
		body = e.read().decode("utf-8", errors="replace")
		print(f"HTTPError {e.code}")
		print(body)
		return 1
	except Exception as e:
		print(f"LIST TABLES test FAILED: {e}")
		return 1


if __name__ == "__main__":
	sys.exit(main())



