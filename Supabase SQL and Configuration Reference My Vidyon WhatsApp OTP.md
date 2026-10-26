# Supabase SQL and Configuration Reference: My Vidyon WhatsApp OTP

Prepared by Claude · October 24, 2026 · Companion to the Antigravity Master Prompt · Project ID MYV-SMS-OTP

## 1. Purpose and ground rules

This document lists every SQL statement and Supabase setting the project needs. Supabase Auth keeps generating and verifying OTPs, so almost nothing here changes a database. The SQL is mainly for discovery and verification.

- **Production (Project A) gets read-only SQL only**, apart from one optional, reversible hook function described in section 5.
- **Never insert, update or delete rows in the auth schema with SQL.** Use the Supabase Auth Admin API for test users.
- **Never create a public function that reveals whether a phone number exists.** That would defeat account-enumeration protection.
- **Do not create an OTP table or a user table.** Supabase Auth already stores what it needs.
- **Run configuration changes in a staging project first.** Project B is the suggested staging project, with test users only.
- **Supabase Auth’s own tables change during normal OTP use** (for example sign-in timestamps and one-time tokens). That is expected. The claim to preserve is that no ERP table in the public schema is modified.
- Placeholders in angle brackets, such as \<erp\_table>, must be replaced before running.

## 2. How to run read-only queries safely

In the Supabase SQL editor, wrap discovery work in a read-only transaction so a typo cannot write anything:

```sql
begin read only;

-- paste one or more read-only queries here

rollback;
```

Save results as counts only. Do not export phone numbers or names into chats, tickets or this project.

## 3. Discovery queries for Project A (read-only)

### 3.1 Phone coverage of Auth users

```sql
select
  count(*) as total_users,
  count(*) filter (where phone is not null and phone <> '') as with_phone,
  count(*) filter (where phone_confirmed_at is not null) as phone_confirmed,
  count(*) filter (where banned_until is not null and banned_until > now()) as banned,
  count(*) filter (where deleted_at is not null) as soft_deleted,
  count(*) filter (where is_anonymous) as anonymous
from auth.users;
```

Why it matters: phone OTP only works for users whose phone is stored and confirmed. A low with\_phone number means most accounts cannot use the flow until phones are attached.

### 3.2 Phone number format

Supabase may store phone numbers with or without a leading plus. This query shows which, so the service and the app normalise correctly.

```sql
select
  count(*) filter (where phone ~ '^\+91[6-9][0-9]{9}$') as india_with_plus,
  count(*) filter (where phone ~ '^91[6-9][0-9]{9}$') as india_without_plus,
  count(*) filter (
    where phone is not null and phone <> ''
      and phone !~ '^\+?91[6-9][0-9]{9}$'
  ) as other_format
from auth.users;
```

Also confirm from a real hook test whether user.phone in the payload carries a plus. Record both answers in the architecture documents.

### 3.3 Is the phone column unique?

```sql
select indexname, indexdef
from pg_indexes
where schemaname = 'auth'
  and tablename = 'users'
  and indexdef ilike '%phone%';
```

If a unique index on phone appears, two accounts cannot share a number. That matters for sibling accounts that share a parent’s phone.

### 3.4 Duplicate phones inside Auth (expected: none)

```sql
select phone, count(*) as accounts
from auth.users
where phone is not null and phone <> ''
group by phone
having count(*) > 1;
```

Report only the number of rows returned, not the numbers.

### 3.5 Sign-in methods in use

```sql
select provider, count(*) as identities
from auth.identities
group by provider
order by identities desc;
```

This shows how many users sign in by email, phone or another method, so you can see what the Forgot Password flow must preserve.

### 3.6 Shared numbers in ERP data (template)

Replace the placeholders with your real ERP table and column names. This is a template and will not run as written.

```sql
-- How many ERP phone numbers belong to more than one ERP record?
select regexp_replace(<phone_col>, '\D', '', 'g') as digits, count(*) as records
from public.<erp_table>
where <phone_col> is not null
group by 1
having count(*) > 1
order by records desc;

-- How many ERP users have no phone stored in Auth?
select count(*)
from public.<erp_table> e
join auth.users u on u.id = e.<auth_user_id_col>
where u.phone is null or u.phone = '';

-- How many ERP phones differ from the Auth phone for the same user?
select count(*)
from public.<erp_table> e
join auth.users u on u.id = e.<auth_user_id_col>
where regexp_replace(coalesce(e.<phone_col>, ''), '\D', '', 'g')
   <> regexp_replace(coalesce(u.phone, ''), '\D', '', 'g');
```

The first query answers the sibling question: records sharing a number cannot each own that number in Auth.

## 4. Reading and changing Auth settings (Management API)

Some settings are not SQL. Use a personal access token stored in your shell session, never in a file or in chat.

### 4.1 Read current settings (safe)

```bash
export SUPABASE_ACCESS_TOKEN='<token from your account settings>'
export PROJECT_REF='<project ref>'

curl -s "https://api.supabase.com/v1/projects/$PROJECT_REF/config/auth" \
  -H "Authorization: Bearer $SUPABASE_ACCESS_TOKEN" \
  | jq '{
      disable_signup,
      external_phone_enabled,
      sms_otp_exp,
      sms_otp_length,
      rate_limit_sms_sent,
      rate_limit_otp,
      rate_limit_verify,
      hook_send_sms_enabled,
      hook_send_sms_uri,
      hook_before_user_created_enabled
    }'
```

The rate\_limit\_\* names come from Supabase’s rate-limit documentation. The other key names are from memory, so if a value prints as null, list the real names with `jq 'keys'` and adjust. Never print the hook secret.

### 4.2 Settings to apply in staging first

| Setting | Suggested value | Notes |
| --- | --- | --- |
| Phone provider enabled | on | Required for phone OTP. |
| Public sign-ups | off | See section 5. Admin-created users still work. |
| SMS OTP length | 6 | Check the dashboard for the allowed values. |
| SMS OTP expiry | 300 seconds | The default may be shorter. Match the template’s expiry line. |
| SMS sent per hour (project) | 100 to 150 | The default is 30 per hour for the whole project. Size it from real usage. |
| OTP resend window per user | 60 seconds | Matches the default. |
| Verify requests per 5 minutes per IP | review | Schools share one public IP, so 30 may be too low. |
| CAPTCHA | decide | Supports hCaptcha and Turnstile. Awkward in native and desktop clients. |

Example of changing rate limits through the API, for staging only. Adjust the numbers before running:

```bash
curl -s -X PATCH "https://api.supabase.com/v1/projects/$PROJECT_REF/config/auth" \
  -H "Authorization: Bearer $SUPABASE_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{ "rate_limit_sms_sent": 120, "rate_limit_otp": 30, "rate_limit_verify": 60 }'
```

### 4.3 The hook itself

Configure the Send SMS hook in the dashboard under Authentication, Hooks, choosing the HTTP endpoint type. Paste the hook URL (your Render HTTPS address ending in /hooks/send-message) and generate the signing secret there. Copy the secret straight into Render’s environment variables. Do not set the secret through a command line, where it would stay in shell history.

## 5. Blocking unwanted account creation

A phone OTP request normally creates a user if the number is unknown. The app sets shouldCreateUser to false, but that is only a client-side option. Anyone can call the Auth API directly, so the server must refuse sign-ups. Without this, a stranger could trigger paid WhatsApp messages to arbitrary numbers.

### 5.1 Preferred option: turn public sign-ups off

If every ERP user is created by an administrator, switch off public sign-ups in the Auth settings. Admin-created users and existing sign-ins keep working. This is the simplest and strongest control. Test it in staging first, because the setting applies to the whole project, including email sign-ups.

### 5.2 Fallback: a Before User Created hook

Use this only if sign-ups must stay on for other methods. The hook receives the user about to be created. It returns an empty object to allow the sign-up, or an error object to reject it. The payload shape has a metadata object and a user object, and the sign-up method appears in app\_metadata.provider.

```sql
create or replace function public.hook_block_phone_signups(event jsonb)
returns jsonb
language plpgsql
as $$
declare
  signup_provider text;
begin
  signup_provider := event->'user'->'app_metadata'->>'provider';

  if signup_provider = 'phone' then
    return jsonb_build_object(
      'error', jsonb_build_object(
        'http_code', 403,
        'message', 'Sign-ups are not permitted.'
      )
    );
  end if;

  return '{}'::jsonb;
end;
$$;

grant usage on schema public to supabase_auth_admin;

grant execute
  on function public.hook_block_phone_signups
  to supabase_auth_admin;

revoke execute
  on function public.hook_block_phone_signups
  from authenticated, anon, public;
```

Then enable it in the dashboard under Authentication, Hooks, as the Before User Created hook, using the Postgres function type. Do not mark the function security definer, following Supabase’s own guidance.

Assumption to verify in staging: that a phone sign-up arrives with the provider set to phone. If it does not, check user.phone instead, and record what you find.

### 5.3 Staging proof

Send a direct API request for a phone number that has no account, with create-user enabled. Expected result: the request is rejected, no user is created and no WhatsApp message is sent. Record the real outcome in the test report.

## 6. Staging test users (use the Admin API, not SQL)

Create test users in the staging project only, with numbers you control. This uses the staging service-role key, which must never go into the Python service, the repository or the ERP app.

```bash
curl -s -X POST "https://<staging-ref>.supabase.co/auth/v1/admin/users" \
  -H "apikey: $STAGING_SERVICE_ROLE_KEY" \
  -H "Authorization: Bearer $STAGING_SERVICE_ROLE_KEY" \
  -H "Content-Type: application/json" \
  -d '{ "phone": "+91XXXXXXXXXX", "phone_confirm": true, "password": "<temporary-test-password>" }'
```

Delete these test users when testing ends.

## 7. Verification queries after staging tests (read-only)

### 7.1 No unexpected users were created

```sql
select count(*) as users_created_since
from auth.users
where created_at > timestamptz '<test start time>';
```

Expected: only the test users you created on purpose.

### 7.2 Recent Auth events

Supabase keeps an Auth audit log. If the table is available in your project, this shows the latest actions without exposing codes:

```sql
select created_at, payload->>'action' as action
from auth.audit_log_entries
order by created_at desc
limit 50;
```

If the table is empty or missing, use the Auth logs page in the dashboard instead.

### 7.3 ERP tables untouched

Take a snapshot of write counters before and after a test session, and compare the numbers. The counters are cumulative and approximate, so look for any change in your ERP tables, not exact totals.

```sql
select schemaname, relname, n_tup_ins, n_tup_upd, n_tup_del
from pg_stat_user_tables
where schemaname = 'public'
order by relname;
```

## 8. Optional: an operations log in Project B (not part of version 1)

The service does not need a database. Only create this if you later want delivery metrics. It belongs in Project B, never in Project A, and it must never hold an OTP, a password, a token or a readable phone number. The service stores a keyed hash of the phone number that it computes itself, using a secret kept outside the database.

```sql
create table if not exists public.otp_delivery_log (
  id            bigint generated always as identity primary key,
  created_at    timestamptz not null default now(),
  webhook_id    text not null,
  phone_hash    text not null,
  outcome       text not null check (outcome in ('accepted', 'rejected', 'timeout', 'error')),
  provider_code text,
  provider_msg  text,
  unique (webhook_id)
);

alter table public.otp_delivery_log enable row level security;

revoke all on table public.otp_delivery_log from anon, authenticated, public;

create index if not exists otp_delivery_log_created_idx
  on public.otp_delivery_log (created_at);
```

Because row level security is on and no policies exist, only the service-role key can use this table. That key goes only into the Render environment for this one service, only if you adopt this option, and it must never be a Project A key.

Retention: delete rows older than 30 days on a schedule.

```sql
delete from public.otp_delivery_log
where created_at < now() - interval '30 days';
```

## 9. Rollback

Rollback never needs a data restore, because nothing in your ERP data is changed.

1. Disable the Send SMS hook in the dashboard. Phone OTP stops sending messages, and nothing else is affected.
2. If you enabled the fallback hook, disable the Before User Created hook, then remove the function:

```sql
drop function if exists public.hook_block_phone_signups(jsonb);
```

3. Restore the previous rate-limit values you saved in section 4.1.
4. Restore the previous public sign-up setting if you changed it.
5. If you created the optional log table in Project B:

```sql
drop table if exists public.otp_delivery_log;
```

6. Remove the Render environment variables and revoke the WhatsApp access token if the service is being retired.

## 10. Pre-production checklist

- Discovery results recorded as counts only, and the shared-number decision made.
- Staging hook configured, with real WhatsApp delivery verified.
- Sign-up blocking tested and the result recorded.
- Rate limits sized for about 2,000 students and about 1,000 parent numbers, with headroom.
- OTP expiry matches the WhatsApp template’s expiry line.
- Hook secret stored only in Render and Supabase.
- Rollback steps rehearsed in staging.
- Written approval before any change to Project A.

## 11. References

- Send SMS Hook: https://supabase.com/docs/guides/auth/auth-hooks/send-sms-hook
- Auth Hooks overview: https://supabase.com/docs/guides/auth/auth-hooks
- Before User Created Hook: https://supabase.com/docs/guides/auth/auth-hooks/before-user-created-hook
- Rate limits: https://supabase.com/docs/guides/auth/rate-limits
- Phone login: https://supabase.com/docs/guides/auth/phone-login
- Password management: https://supabase.com/docs/guides/auth/passwords
