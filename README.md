# FastAPI Database Connector

A FastAPI service that provides SQL query endpoints for Supabase (or any PostgreSQL database). The service offers two connection methods:
- SQLAlchemy 
- Direct psycopg2 database connection

## 📧 Contact

For any issues or questions, please drop me an email at: **amar@harolikar.com**


### 1. Deployment Steps

You can deploy this service on various platforms like Render, Railway, Heroku, or any other cloud platform of your choice.


1. Choose your preferred platform (Render/Railway/Heroku/etc.)
2. Connect your repository
3. Configure the build:
   ```
   Build Command: pip install -r requirements.txt
   Start Command: uvicorn app:app --host 0.0.0.0 --port $PORT
   ```
4. Add environment variable in platform settings:
   - Key: `DATABASE_URL`
   - Value: Your database connection string in URI format - example below:
     ```
     "postgresql://postgres.gsutseqhzrdzdhxabcd:4yHoBJ9pXaDabdd@aws-0-us-east-2.pooler.supabase.com:6543/postgres"
     ```
     For Supabase, you can find this under Project Settings > Database > Connect > URI format
   - Key: `REX_API_KEY`
   - Value: Your API key for authentication (default: "rex-QAQ_bNvD7j0E2wXrCEzRL")
   - Key: `RATE_LIMIT` (optional)
   - Value: Simple rate limit in SlowAPI format (default: `100/hour`). Examples: `2/minute`, `1000/day`
5. After deployment, you'll get an API URL. Your endpoints will be:
   - `{YOUR_API_URL}/sqlquery_alchemy/?sqlquery=YOUR_QUERY&api_key=YOUR_API_KEY`
   - `{YOUR_API_URL}/sqlquery_direct/?sqlquery=YOUR_QUERY&api_key=YOUR_API_KEY`

   #### These can be used for Custom GPT as well as any other application also

### 2. Runtime safeguards in this app

- Read-only enforcement (PostgreSQL):
  - SQLAlchemy endpoint: every request runs in a read-only DB session and a read-only transaction.
  - Direct psycopg2 endpoint: the session is set to `readonly=True` for each request.
  - Effects: write attempts (INSERT/UPDATE/DELETE/CREATE/ALTER/DROP, SELECT FOR UPDATE, multi-statement writes) fail with a read-only error. Multi-statement payloads like `SELECT 1; CREATE TABLE ...` are also blocked by the read-only transaction.
- Simple rate limiting:
  - SlowAPI limiter with `@limiter.limit(RATE_LIMIT)` applied to both endpoints.
  - Configure via `RATE_LIMIT` env var (e.g., `100/hour`). This is a basic throttle, not DDoS protection.

### 3. ChatGPT Integration

1. Create a new Custom GPT
2. Copy the OpenAPI schema from `customGPT_actionSchema.json` and paste it in the GPT configuration
3. Make the following required changes in the schema:
   - Update the server URL with your actual URL e.g. https://supabase-hosting.on-render.com 
     ```json
     "servers": [
         {
             "url": "YOUR_DEPLOYED_API_URL",
             "description": "Main API server"
         }
     ]
     ```
   - **IMPORTANT**: Set your API key in the `description` field (NOT the example field):
     ```json
     {
         "name": "api_key",
         "in": "query",
         "required": true,
         "schema": {
             "type": "string"
         },
         "description": "YOUR_REX_API_KEY",  // ← PUT YOUR ACTUAL API KEY HERE
         "example": "rex-jasjf887^&^jjf"     // ← This is just an example, don't change
     }
     ```
4. Configure your Custom GPT with appropriate instructions for handling database queries

```
Your task is to answer questions exclusively based on a PostgreSQL database containing data from two distinct tables: One Day International (ODI) cricket data and RBI monthly card and ATM statistics for November 2024. Your primary task is to interpret user queries and generate PostgreSQL-compliant SQL queries to fetch the required data from the database.

Your Responsibilities:
- Respond concisely to user questions with factual answers derived exclusively from the database.
- Convert user questions into PostgreSQL queries while ensuring they comply with the database schema.
- Avoid speculating, making up data, using external sources, or performing tasks outside your scope.
- While computing any averages do not use the AVG function. For denominator always use NULLIF to avoid division by zero error
- Always share results in table format

**Critical Rules for SELECT Query Generation:**
For SELECT queries: if retrieving rows, always append LIMIT 100; if performing aggregation, never use LIMIT.


Database Context:
1. ODI Cricket Data:
   - The database contains ODI cricket data stored in a Postgres database.
   - The data resides in the `public` schema under a single table with the structure illustrated below. The table contains one row per ball bowled in ODIs.
   - Table name: 'cricket_one_day_international'
   - Schema.Table: public.cricket_one_day_international
   - Example rows:

     match_id|season|start_date|venue|innings|ball|batting_team|bowling_team|striker|non_striker|bowler|runs_off_bat|extras|wides|noballs|byes|legbyes|penalty|wicket_type|player_dismissed|other_wicket_type|other_player_dismissed  
     366711|2008/09|2009-01-07|Westpac Stadium|1|0.1|West Indies|New Zealand|CH Gayle|XM Marshall|KD Mills|1|0|0|0|0|0|0||||  
     366711|2008/09|2009-01-07|Westpac Stadium|1|0.2|West Indies|New Zealand|XM Marshall|CH Gayle|KD Mills|0|0|0|0|0|0|0||||  
     366711|2008/09|2009-01-07|Westpac Stadium|1|0.4|West Indies|New Zealand|XM Marshall|CH Gayle|KD Mills|0|0|0|0|0|0|0|caught|XM Marshall||  

   - Critical Details:
     1. Focus:
        - Answer only questions related to ODI cricket data from this database only.
        - Do not make up data or use external sources like web search.
     2. Ball Counting:
        - The `ball` field (e.g., `0.1`, `7.5`) is an identifier for the over and ball number, not a count of total balls.
        - Use a `COUNT(*)` query to calculate the number of balls bowled.
     3. Run Calculation:
        - If the user specifies "runs" or "runs off bat," prioritize the `runs_off_bat` field.
        - Otherwise, interpret the query context and use appropriate fields like `extras` or `total runs` as required.
     4. Judgment:
        - Users may not explicitly specify the schema, table name, or field names.
        - Use the sample rows to infer the structure and intelligently map user queries to database fields.
     5. Context:
        - The table includes critical fields such as:
          - Match details: `match_id`, `season`, `start_date`, `venue`.
          - Inning and ball information: `innings`, `ball`.
          - Teams and players: `batting_team`, `bowling_team`, `striker`, `non_striker`, `bowler`.
          - Outcome: `runs_off_bat`, `extras`, `wicket_type`, `player_dismissed`.

2. RBI Cards and ATM Statistics Data:
   - The database contains monthly statistics for June 2025 on cards and ATM usage, categorized by bank type.
   - The data resides in the `public` schema under the following table:
     - Table name: 'rbi_cards_pos_atm_statistics_jun2025'
     - Schema.Table: public.rbi_cards_pos_atm_statistics_jun2025
   - Example rows:

      category             |    date    |       bank_name        | atm_crm_onsite_nos | atm_crm_offsite_nos | pos_nos | micro_atm_nos | bharat_qr_codes_nos | upi_qr_codes_nos | credit_cards_nos | debit_cards_nos | credit_card_pos_txn_volume_nos | credit_card_pos_txn_value_amt | credit_card_ecom_volume_nos | credit_card_ecom_value_amt | credit_card_others_volume_nos | credit_card_others_value_amt | cash_withdrawal_atm_volume_nos | cash_withdrawal_atm_value_amt | debit_card_pos_txn_volume_nos | debit_card_pos_txn_value_amt | debit_card_ecom_volume_nos | debit_card_ecom_value_amt | debit_card_others_volume_nos | debit_card_others_value_amt | cash_withdrawal_atm_volume_nos_1 | cash_withdrawal_atm_value_amt_1 | cash_withdrawal_pos_volume_nos | cash_withdrawal_pos_value_amt
-----------------------+------------+------------------------+--------------------+---------------------+---------+---------------+---------------------+------------------+------------------+-----------------+--------------------------------+-------------------------------+-----------------------------+-----------------------------+--------------------------------+-------------------------------+--------------------------------+--------------------------------+--------------------------------+-------------------------------+-----------------------------+----------------------------+-------------------------------+-------------------------------+-----------------------------------+-----------------------------------+--------------------------------+-------------------------------
 Public Sector Banks   | 2025-06-30 | BANK OF BARODA         | 8710               | 2420                | 52130   | 44362         | 24248               | 2658077          | 3028877          | 87776511        | 7374472                        | 13892652.494                  | 3256646                     | 16800430.447                | 0                              | 0.0                           | 9003                           | 46579.8                        | 2809540                        | 6606462.2855                  | 195902                      | 2077040.58668                | 15                            | 36.661                        | 21197051                           | 107766070.301                      | 4                              | 2.3
 Public Sector Banks   | 2025-06-30 | BANK OF INDIA          | 5339               | 2647                | 18450   | 23603         | 0                   | 1292420          | 74463            | 37225651        | 238702                         | 820457.53938                   | 64775                       | 311792.72345                | 0                              | 0.0                           | 6948                           | 36755.56826                    | 2016826                        | 4335662.01787                  | 349219                      | 821597.76295                 | 0                             | 0.0                           | 13805735                           | 59003197.815                       | 4                              | 3.10999
 


   - Key Details:
     1. Focus:
        - Answer only questions related to this table’s data, such as bank-wise statistics for ATMs, POS, and cards.
        - Do not make up data or use external sources.
     2. Data Categories:
        - Covers categories such as Public Sector Banks, Foreign Banks, Payment Banks, Private Sector Banks, and Small Banks.
3. All amounts are the fields with suffix _VALUE_AMT and the values are in Rs '000. So while sharing totals mention that and while computing averages involving amounts convert to Rupees in full by multiplying by 1000 and share. This only applies to amount and not to the _VOLUME_NOS  OR _NOS fields which have the transactions number, counts and volumes
     

Guidelines:
- Ensure all responses are context-specific to the database structure and sample rows.
- Utilize concise, relevant examples to illustrate SQL queries as needed.
```

## 🔒 Security Considerations


### Current Security Setup:
- Authentication:  API key only; prefer OAuth2/JWT in production
- SQL validation: none; arbitrary SQL accepted; add a validator to restrict to single SELECT
- Rate limiting: basic SlowAPI; not DDoS/multi-tenant grade controls
- Authorization/RBAC: none in-app
- Database role: app uses a least-privileged read-only role; avoid admin credentials

### Essential Security Measures for Production:

1. **Authentication & Authorization**
   - Implement proper OAuth 2.0 or JWT-based authentication
   - Add role-based access control (RBAC)
   - Use API rate limiting and throttling

2. **Database Security**
   - Prefer a dedicated database user with minimal privileges (ideally read-only for this app)
   - For PostgreSQL/Supabase: use a read-only role or a read replica for query-only use cases
   - For testing: grant only SELECT on specific tables or expose read-only views
   - Consider connection pooling with restricted credentials

3. **SQL Injection Protection**
   - While `text()` executes raw SQL, there is no in-app validation of arbitrary SQL
   - For enhanced safety, add a SQL validator that only allows single-statement SELECT and rejects write/DDL/DO/COPY etc.
   - Consider using stored procedures or a constrained query API

4. **Row-Level Security (RLS)**
   - Implement PostgreSQL/Supabase Row Level Security policies
   - Control data access at the database level based on user context

5. **Infrastructure Security**
   - Use HTTPS/TLS for all communications
   - Implement proper firewall rules
   - Regular security audits and dependency updates
   - Monitor and log all database access

### Quick Implementation Tips:
- Use a non-admin database user with only SELECT permissions when your app is read-only
- Set `RATE_LIMIT` (e.g., `100/hour`) to control traffic
- Use environment variables for all sensitive configuration
- Implement request logging and monitoring
- For Supabase, leverage RLS and auth for per-user controls

### About read-only enforcement in this app
- Both endpoints enforce PostgreSQL read-only behavior at the session/transaction level, causing any write attempts to error at the database.
- In production we also connect using a restricted read-only role; together these provide defense-in-depth (multi-statement writes are still rejected).


### Ideal access control patterns
- Per-user access control: implement proper authentication and authorization (OAuth2/JWT) and apply roles per user.
- For non-Supabase deployments and simple read scenarios, use a read-only DB user or a read replica.
- Add SQL validation controls if accepting arbitrary SQL:
  - Allow only single top-level `SELECT` (reject writes, `SELECT FOR UPDATE`, procedural commands)
  - Optionally parse SQL and allowlist schemas/tables/views
  - Enforce single-statement execution

**Remember**: Security requirements vary by use case. Always conduct a thorough security assessment before deploying to production.

##  Sample Files
Sample files for the above instructions are available in the following link:  
https://drive.google.com/drive/folders/1QlE8tJDKAX9XaHUCabfflPgRnNiOXigV

## 🔐 Use a restricted, read-only database user

This app is intended to run with a restricted database role (read-only), not admin credentials. Examples below show how to connect via the Supabase pooler using a read-only role.

### Recommended DATABASE_URL for Supabase (pooler + read-only user)

Use one of the following formats (replace placeholders):

- Username-suffix (recommended):
```
postgresql://reporter.abcd1234xyz:My_Secure_ReadOnly_Pass@aws-0-us-east-2.pooler.supabase.com:6543/postgres?sslmode=require
```
Where `reporter` is your DB role and `abcd1234xyz` is your Supabase project ref.

- Pass the project via options parameter:
```
postgresql://reporter:My_Secure_ReadOnly_Pass@aws-0-us-east-2.pooler.supabase.com:6543/postgres?sslmode=require&options=project%3Dabcd1234xyz
```

Notes:
- Pooler runs on port 6543 (not 5432)
- Always include sslmode=require
- Prefer the pooler to avoid IPv6/egress issues common in containers

### Create and use a Supabase read-only user

Run in Supabase SQL editor as an admin once per project (adjust role/password as needed):

```sql
create role reporter login password 'My_Secure_ReadOnly_Pass';
grant usage on schema public to reporter;
grant select on all tables in schema public to reporter;
alter default privileges in schema public grant select on tables to reporter;
```

Connect using the pooler with your project ref, as shown above.

### Security note

This app is designed to use a least-privileged, read-only database role in production. Avoid using admin credentials. If you see permission errors, ensure the role has USAGE on the schema and SELECT on the necessary tables, and that new tables inherit SELECT via default privileges.


## Deployment example (read-only update)

Use a least-privileged role for `DATABASE_URL`. Recommended Supabase pooler formats (replace placeholders):

- Username-suffix (recommended):
```
postgresql://reporter.abcd1234xyz:My_Secure_ReadOnly_Pass@aws-0-us-east-2.pooler.supabase.com:6543/postgres?sslmode=require
```
- Or pass project via options:
```
postgresql://reporter:My_Secure_ReadOnly_Pass@aws-0-us-east-2.pooler.supabase.com:6543/postgres?sslmode=require&options=project%3Dabcd1234xyz
```
Notes: port is 6543 (pooler), always include `sslmode=require`.

## Security update (read-only role expected)

This app now expects a restricted, read-only DB role in production. If you encounter permission errors, ensure the role has `USAGE` on the schema and `SELECT` on needed tables, and default privileges grant `SELECT` for new tables.

## Note on "About read-only enforcement in this app"

Read-only enforcement at the session/transaction level is combined with using a restricted DB role. Together, this provides defense-in-depth for query-only workloads.



