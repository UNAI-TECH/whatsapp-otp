-- ═══════════════════════════════════════════════════════════════════════════════
-- MASTER SQL — My Vidyon WhatsApp OTP Platform
-- Project: MYV-SMS-OTP  ·  Project C (dedicated OTP Supabase project)
-- Run this entire script TOP-TO-BOTTOM in one session in the Supabase SQL Editor.
-- Never run this on Project A (ERP production) or Project B (ERP staging).
-- ═══════════════════════════════════════════════════════════════════════════════

-- ───────────────────────────────────────────────────────────────────────────────
-- STEP 0 · Extensions
-- ───────────────────────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
-- pg_cron is optional; enable it in the Supabase dashboard under
-- Database → Extensions → pg_cron before uncommenting the cron lines below.
-- CREATE EXTENSION IF NOT EXISTS "pg_cron";


-- ───────────────────────────────────────────────────────────────────────────────
-- STEP 1 · Shared trigger function (reused by multiple tables)
-- ───────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public._set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;


-- ───────────────────────────────────────────────────────────────────────────────
-- STEP 2 · registered_apps
-- One row per application that is allowed to use this OTP service.
-- Add My Vidyon ERP now; add future apps with a single INSERT later.
-- ───────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.registered_apps (
  id                  UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at          TIMESTAMPTZ  NOT NULL DEFAULT now(),
  updated_at          TIMESTAMPTZ  NOT NULL DEFAULT now(),

  app_name            TEXT         NOT NULL UNIQUE,
  app_description     TEXT,
  is_active           BOOLEAN      NOT NULL DEFAULT TRUE,

  -- OTP policy (per app, configurable per row)
  otp_length          INT          NOT NULL DEFAULT 6
                                   CHECK (otp_length BETWEEN 4 AND 10),
  otp_expiry_seconds  INT          NOT NULL DEFAULT 300
                                   CHECK (otp_expiry_seconds BETWEEN 60 AND 3600),
  max_otps_per_window INT          NOT NULL DEFAULT 5,
  rate_window_seconds INT          NOT NULL DEFAULT 600,
  max_verify_attempts INT          NOT NULL DEFAULT 3,
  allowed_prefix      TEXT         NOT NULL DEFAULT '+91'
);

DROP TRIGGER IF EXISTS registered_apps_updated_at ON public.registered_apps;
CREATE TRIGGER registered_apps_updated_at
  BEFORE UPDATE ON public.registered_apps
  FOR EACH ROW EXECUTE FUNCTION public._set_updated_at();

ALTER TABLE public.registered_apps ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.registered_apps FROM anon, authenticated, public;


-- ───────────────────────────────────────────────────────────────────────────────
-- STEP 3 · otp_tokens
-- One row per OTP request. Plain OTP is NEVER stored — only SHA-256(otp||salt).
-- ───────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.otp_tokens (
  id              BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
  expires_at      TIMESTAMPTZ  NOT NULL,

  app_id          UUID         NOT NULL REFERENCES public.registered_apps(id) ON DELETE CASCADE,
  phone_e164      TEXT         NOT NULL,
  request_id      TEXT         NOT NULL UNIQUE DEFAULT gen_random_uuid()::TEXT,

  otp_hash        TEXT         NOT NULL,
  otp_salt        TEXT         NOT NULL,

  status          TEXT         NOT NULL DEFAULT 'pending'
                               CHECK (status IN ('pending','verified','expired','cancelled')),
  attempt_count   INT          NOT NULL DEFAULT 0,
  max_attempts    INT          NOT NULL DEFAULT 3,

  verified_at     TIMESTAMPTZ,
  ip_address      INET,
  user_agent      TEXT
);

CREATE INDEX IF NOT EXISTS idx_otp_tokens_app_phone_pending
  ON public.otp_tokens (app_id, phone_e164, status)
  WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS idx_otp_tokens_expires
  ON public.otp_tokens (expires_at)
  WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS idx_otp_tokens_request_id
  ON public.otp_tokens (request_id);

ALTER TABLE public.otp_tokens ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.otp_tokens FROM anon, authenticated, public;


-- ───────────────────────────────────────────────────────────────────────────────
-- STEP 4 · otp_rate_limits
-- Rolling per-(app, phone_hash) counter. Checked atomically in generate_otp().
-- ───────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.otp_rate_limits (
  id              BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  app_id          UUID         NOT NULL REFERENCES public.registered_apps(id) ON DELETE CASCADE,
  phone_hash      TEXT         NOT NULL,
  window_start    TIMESTAMPTZ  NOT NULL,
  request_count   INT          NOT NULL DEFAULT 1,
  UNIQUE (app_id, phone_hash, window_start)
);

CREATE INDEX IF NOT EXISTS idx_rate_limits_lookup
  ON public.otp_rate_limits (app_id, phone_hash, window_start);

ALTER TABLE public.otp_rate_limits ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.otp_rate_limits FROM anon, authenticated, public;


-- ───────────────────────────────────────────────────────────────────────────────
-- STEP 5 · api_keys
-- Raw key is shown ONCE (via issue_api_key). Only SHA-256 hash stored here.
-- Key format: otp_<64 hex chars>
-- ───────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.api_keys (
  id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
  last_used_at    TIMESTAMPTZ,

  app_id          UUID         NOT NULL REFERENCES public.registered_apps(id) ON DELETE CASCADE,
  key_name        TEXT         NOT NULL,
  key_hash        TEXT         NOT NULL UNIQUE,
  key_preview     TEXT         NOT NULL,

  is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
  expires_at      TIMESTAMPTZ,
  allowed_ips     INET[],

  can_generate    BOOLEAN      NOT NULL DEFAULT TRUE,
  can_verify      BOOLEAN      NOT NULL DEFAULT TRUE,
  can_read_stats  BOOLEAN      NOT NULL DEFAULT FALSE,

  UNIQUE (app_id, key_name)
);

DROP TRIGGER IF EXISTS api_keys_updated_at ON public.api_keys;
CREATE TRIGGER api_keys_updated_at
  BEFORE UPDATE ON public.api_keys
  FOR EACH ROW EXECUTE FUNCTION public._set_updated_at();

ALTER TABLE public.api_keys ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.api_keys FROM anon, authenticated, public;


-- ───────────────────────────────────────────────────────────────────────────────
-- STEP 6 · otp_audit_log
-- One row per API call. Never stores OTP values, phone numbers or raw keys.
-- ───────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.otp_audit_log (
  id          BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),

  app_id      UUID         NOT NULL REFERENCES public.registered_apps(id),
  key_id      UUID         REFERENCES public.api_keys(id),
  action      TEXT         NOT NULL CHECK (action IN ('generate','verify','cleanup','stats')),
  outcome     TEXT         NOT NULL CHECK (outcome IN ('success','rate_limited','invalid','error')),

  phone_hash  TEXT,
  request_id  TEXT,
  error_code  TEXT,
  latency_ms  INT,
  ip_address  INET
);

CREATE INDEX IF NOT EXISTS idx_audit_log_app_created
  ON public.otp_audit_log (app_id, created_at DESC);

ALTER TABLE public.otp_audit_log ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.otp_audit_log FROM anon, authenticated, public;


-- ═══════════════════════════════════════════════════════════════════════════════
-- FUNCTIONS
-- ═══════════════════════════════════════════════════════════════════════════════

-- ───────────────────────────────────────────────────────────────────────────────
-- FUNCTION 1 · generate_otp()
-- ───────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.generate_otp(
  p_app_id      UUID,
  p_phone_e164  TEXT,
  p_ip          INET DEFAULT NULL,
  p_user_agent  TEXT DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_app           public.registered_apps%ROWTYPE;
  v_otp           TEXT;
  v_salt          TEXT;
  v_hash          TEXT;
  v_request_id    TEXT;
  v_expires_at    TIMESTAMPTZ;
  v_phone_hash    TEXT;
  v_window_start  TIMESTAMPTZ;
  v_req_count     INT;
  v_rand          BIGINT;
BEGIN
  SELECT * INTO v_app FROM public.registered_apps WHERE id = p_app_id;
  IF NOT FOUND THEN RAISE EXCEPTION 'APP_NOT_FOUND'; END IF;
  IF NOT v_app.is_active THEN RAISE EXCEPTION 'APP_INACTIVE'; END IF;

  IF p_phone_e164 IS NULL OR p_phone_e164 = '' THEN
    RAISE EXCEPTION 'INVALID_PHONE';
  END IF;
  IF v_app.allowed_prefix <> '' AND p_phone_e164 NOT LIKE v_app.allowed_prefix || '%' THEN
    RAISE EXCEPTION 'PHONE_PREFIX_NOT_ALLOWED'
      USING HINT = 'Phone must start with ' || v_app.allowed_prefix;
  END IF;

  v_phone_hash   := encode(digest(p_phone_e164, 'sha256'), 'hex');
  v_window_start := date_trunc('second', now())
                  - make_interval(secs =>
                      (extract(epoch FROM now())::BIGINT % v_app.rate_window_seconds));

  INSERT INTO public.otp_rate_limits (app_id, phone_hash, window_start, request_count)
  VALUES (p_app_id, v_phone_hash, v_window_start, 1)
  ON CONFLICT (app_id, phone_hash, window_start)
  DO UPDATE SET request_count = otp_rate_limits.request_count + 1
  RETURNING request_count INTO v_req_count;

  IF v_req_count > v_app.max_otps_per_window THEN
    RAISE EXCEPTION 'RATE_LIMIT_EXCEEDED';
  END IF;

  UPDATE public.otp_tokens
  SET    status = 'cancelled'
  WHERE  app_id = p_app_id AND phone_e164 = p_phone_e164
    AND  status = 'pending' AND expires_at > now();

  v_rand := (
    (get_byte(gen_random_bytes(4), 0)::BIGINT << 24) |
    (get_byte(gen_random_bytes(4), 1)::BIGINT << 16) |
    (get_byte(gen_random_bytes(4), 2)::BIGINT <<  8) |
     get_byte(gen_random_bytes(4), 3)::BIGINT
  );

  v_otp        := lpad((abs(v_rand) % (10 ^ v_app.otp_length)::BIGINT)::TEXT,
                       v_app.otp_length, '0');
  v_salt       := encode(gen_random_bytes(16), 'hex');
  v_hash       := encode(digest(v_otp || v_salt, 'sha256'), 'hex');
  v_expires_at := now() + make_interval(secs => v_app.otp_expiry_seconds);
  v_request_id := gen_random_uuid()::TEXT;

  INSERT INTO public.otp_tokens
    (app_id, phone_e164, request_id, otp_hash, otp_salt,
     expires_at, max_attempts, ip_address, user_agent)
  VALUES
    (p_app_id, p_phone_e164, v_request_id, v_hash, v_salt,
     v_expires_at, v_app.max_verify_attempts, p_ip, p_user_agent);

  RETURN jsonb_build_object(
    'request_id', v_request_id,
    'otp',        v_otp,
    'expires_at', v_expires_at,
    'otp_length', v_app.otp_length
  );
END;
$$;

REVOKE ALL ON FUNCTION public.generate_otp(UUID,TEXT,INET,TEXT) FROM anon, authenticated, public;
GRANT  EXECUTE ON FUNCTION public.generate_otp(UUID,TEXT,INET,TEXT) TO service_role;


-- ───────────────────────────────────────────────────────────────────────────────
-- FUNCTION 2 · verify_otp()
-- ───────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.verify_otp(
  p_app_id      UUID,
  p_request_id  TEXT,
  p_otp_input   TEXT
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_token      public.otp_tokens%ROWTYPE;
  v_input_hash TEXT;
  v_verified   BOOLEAN := FALSE;
BEGIN
  SELECT * INTO v_token
  FROM   public.otp_tokens
  WHERE  request_id = p_request_id AND app_id = p_app_id
  FOR UPDATE;

  IF NOT FOUND THEN RAISE EXCEPTION 'REQUEST_NOT_FOUND'; END IF;
  IF v_token.status = 'verified'                   THEN RAISE EXCEPTION 'ALREADY_VERIFIED'; END IF;
  IF v_token.status IN ('expired','cancelled')     THEN RAISE EXCEPTION 'OTP_EXPIRED_OR_CANCELLED'; END IF;
  IF v_token.expires_at <= now() THEN
    UPDATE public.otp_tokens SET status='expired' WHERE id=v_token.id;
    RAISE EXCEPTION 'OTP_EXPIRED';
  END IF;
  IF v_token.attempt_count >= v_token.max_attempts THEN
    UPDATE public.otp_tokens SET status='expired' WHERE id=v_token.id;
    RAISE EXCEPTION 'MAX_ATTEMPTS_EXCEEDED';
  END IF;

  v_input_hash := encode(digest(p_otp_input || v_token.otp_salt, 'sha256'), 'hex');
  v_verified   := (v_input_hash = v_token.otp_hash);

  IF v_verified THEN
    UPDATE public.otp_tokens
    SET status='verified', verified_at=now(), attempt_count=attempt_count+1
    WHERE id=v_token.id;
  ELSE
    UPDATE public.otp_tokens SET attempt_count=attempt_count+1 WHERE id=v_token.id;
  END IF;

  RETURN jsonb_build_object(
    'verified',           v_verified,
    'status',             CASE WHEN v_verified THEN 'verified' ELSE 'pending' END,
    'attempts_remaining', GREATEST(0, v_token.max_attempts - v_token.attempt_count - 1)
  );
END;
$$;

REVOKE ALL ON FUNCTION public.verify_otp(UUID,TEXT,TEXT) FROM anon, authenticated, public;
GRANT  EXECUTE ON FUNCTION public.verify_otp(UUID,TEXT,TEXT) TO service_role;


-- ───────────────────────────────────────────────────────────────────────────────
-- FUNCTION 3 · issue_api_key()
-- ───────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.issue_api_key(
  p_app_id       UUID,
  p_key_name     TEXT,
  p_can_generate BOOLEAN     DEFAULT TRUE,
  p_can_verify   BOOLEAN     DEFAULT TRUE,
  p_can_stats    BOOLEAN     DEFAULT FALSE,
  p_expires_at   TIMESTAMPTZ DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_raw TEXT;
  v_hash TEXT;
  v_preview TEXT;
  v_key_id UUID;
BEGIN
  IF NOT EXISTS (SELECT 1 FROM public.registered_apps WHERE id=p_app_id) THEN
    RAISE EXCEPTION 'APP_NOT_FOUND';
  END IF;

  v_raw     := 'otp_' || encode(gen_random_bytes(32), 'hex');
  v_hash    := encode(digest(v_raw, 'sha256'), 'hex');
  v_preview := left(v_raw, 16) || '...';

  INSERT INTO public.api_keys
    (app_id, key_name, key_hash, key_preview,
     can_generate, can_verify, can_read_stats, expires_at)
  VALUES
    (p_app_id, p_key_name, v_hash, v_preview,
     p_can_generate, p_can_verify, p_can_stats, p_expires_at)
  RETURNING id INTO v_key_id;

  RETURN jsonb_build_object(
    'api_key',     v_raw,
    'key_preview', v_preview,
    'key_id',      v_key_id,
    'warning',     'Store this key immediately — it cannot be retrieved again.'
  );
END;
$$;

REVOKE ALL ON FUNCTION public.issue_api_key(UUID,TEXT,BOOLEAN,BOOLEAN,BOOLEAN,TIMESTAMPTZ)
  FROM anon, authenticated, public;
GRANT  EXECUTE ON FUNCTION public.issue_api_key(UUID,TEXT,BOOLEAN,BOOLEAN,BOOLEAN,TIMESTAMPTZ)
  TO service_role;


-- ───────────────────────────────────────────────────────────────────────────────
-- FUNCTION 4 · validate_api_key()
-- ───────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.validate_api_key(
  p_raw_key        TEXT,
  p_required_scope TEXT,
  p_caller_ip      INET DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_hash TEXT;
  v_key  public.api_keys%ROWTYPE;
BEGIN
  v_hash := encode(digest(p_raw_key, 'sha256'), 'hex');
  SELECT * INTO v_key FROM public.api_keys WHERE key_hash = v_hash;

  IF NOT FOUND             THEN RAISE EXCEPTION 'INVALID_API_KEY';  END IF;
  IF NOT v_key.is_active   THEN RAISE EXCEPTION 'API_KEY_INACTIVE'; END IF;
  IF v_key.expires_at IS NOT NULL AND v_key.expires_at <= now()
                           THEN RAISE EXCEPTION 'API_KEY_EXPIRED';  END IF;

  IF p_required_scope='generate' AND NOT v_key.can_generate  THEN RAISE EXCEPTION 'SCOPE_NOT_ALLOWED'; END IF;
  IF p_required_scope='verify'   AND NOT v_key.can_verify    THEN RAISE EXCEPTION 'SCOPE_NOT_ALLOWED'; END IF;
  IF p_required_scope='stats'    AND NOT v_key.can_read_stats THEN RAISE EXCEPTION 'SCOPE_NOT_ALLOWED'; END IF;

  IF v_key.allowed_ips IS NOT NULL AND p_caller_ip IS NOT NULL
     AND NOT (p_caller_ip = ANY(v_key.allowed_ips)) THEN
    RAISE EXCEPTION 'IP_NOT_ALLOWED';
  END IF;

  UPDATE public.api_keys SET last_used_at=now() WHERE id=v_key.id;
  RETURN to_jsonb(v_key);
END;
$$;

REVOKE ALL ON FUNCTION public.validate_api_key(TEXT,TEXT,INET) FROM anon, authenticated, public;
GRANT  EXECUTE ON FUNCTION public.validate_api_key(TEXT,TEXT,INET) TO service_role;


-- ───────────────────────────────────────────────────────────────────────────────
-- FUNCTION 5 · cleanup_expired_otps()
-- ───────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.cleanup_expired_otps()
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_marked INT; v_deleted INT;
BEGIN
  UPDATE public.otp_tokens SET status='expired'
  WHERE  status='pending' AND expires_at <= now();
  GET DIAGNOSTICS v_marked = ROW_COUNT;

  DELETE FROM public.otp_tokens  WHERE created_at < now() - INTERVAL '7 days';
  GET DIAGNOSTICS v_deleted = ROW_COUNT;

  DELETE FROM public.otp_rate_limits WHERE window_start < now() - INTERVAL '1 day';
  DELETE FROM public.otp_audit_log   WHERE created_at   < now() - INTERVAL '30 days';

  RETURN jsonb_build_object('marked_expired',v_marked,'rows_deleted',v_deleted,'ran_at',now());
END;
$$;

REVOKE ALL ON FUNCTION public.cleanup_expired_otps() FROM anon, authenticated, public;
GRANT  EXECUTE ON FUNCTION public.cleanup_expired_otps() TO service_role;


-- ───────────────────────────────────────────────────────────────────────────────
-- FUNCTION 6 · get_otp_stats()
-- ───────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.get_otp_stats(
  p_app_id UUID,
  p_since  TIMESTAMPTZ DEFAULT now() - INTERVAL '24 hours'
)
RETURNS JSONB
LANGUAGE sql
SECURITY DEFINER
AS $$
  SELECT jsonb_build_object(
    'app_id',               p_app_id,
    'since',                p_since,
    'total_requests',       count(*),
    'verified',             count(*) FILTER (WHERE status='verified'),
    'expired_or_cancelled', count(*) FILTER (WHERE status IN ('expired','cancelled')),
    'pending',              count(*) FILTER (WHERE status='pending'),
    'avg_verify_seconds',   ROUND(AVG(EXTRACT(EPOCH FROM (verified_at - created_at)))
                              FILTER (WHERE status='verified'))::INT
  )
  FROM public.otp_tokens
  WHERE app_id=p_app_id AND created_at >= p_since;
$$;

REVOKE ALL ON FUNCTION public.get_otp_stats(UUID,TIMESTAMPTZ) FROM anon, authenticated, public;
GRANT  EXECUTE ON FUNCTION public.get_otp_stats(UUID,TIMESTAMPTZ) TO service_role;

-- Optional scheduled cleanup (uncomment after enabling pg_cron):
-- SELECT cron.schedule('otp-cleanup', '*/15 * * * *', 'SELECT public.cleanup_expired_otps()');


-- ═══════════════════════════════════════════════════════════════════════════════
-- SEED · Register My Vidyon ERP
-- ═══════════════════════════════════════════════════════════════════════════════
INSERT INTO public.registered_apps (
  app_name, app_description,
  otp_length, otp_expiry_seconds, max_otps_per_window,
  rate_window_seconds, max_verify_attempts, allowed_prefix
) VALUES (
  'my_vidyon_erp',
  'My Vidyon school ERP — WhatsApp OTP for password reset (Tamil Nadu schools)',
  6, 300, 5, 600, 3, '+91'
)
ON CONFLICT (app_name) DO NOTHING
RETURNING id AS my_vidyon_app_id, app_name, otp_length, otp_expiry_seconds;

-- Run the statement below to automatically issue the API key for My Vidyon ERP:
/*
SELECT public.issue_api_key(
  (SELECT id FROM public.registered_apps WHERE app_name = 'my_vidyon_erp'),
  'my_vidyon_production',
  TRUE, TRUE, FALSE, NULL
);
-- api_key in result → store as OTP_PLATFORM_API_KEY in Render env vars
*/


-- ═══════════════════════════════════════════════════════════════════════════════
-- ROLLBACK  (uncomment and run to remove everything)
-- ═══════════════════════════════════════════════════════════════════════════════
/*
DROP FUNCTION IF EXISTS public.get_otp_stats(UUID,TIMESTAMPTZ);
DROP FUNCTION IF EXISTS public.cleanup_expired_otps();
DROP FUNCTION IF EXISTS public.verify_otp(UUID,TEXT,TEXT);
DROP FUNCTION IF EXISTS public.generate_otp(UUID,TEXT,INET,TEXT);
DROP FUNCTION IF EXISTS public.validate_api_key(TEXT,TEXT,INET);
DROP FUNCTION IF EXISTS public.issue_api_key(UUID,TEXT,BOOLEAN,BOOLEAN,BOOLEAN,TIMESTAMPTZ);
DROP FUNCTION IF EXISTS public._set_updated_at();
DROP TABLE IF EXISTS public.otp_audit_log;
DROP TABLE IF EXISTS public.otp_rate_limits;
DROP TABLE IF EXISTS public.otp_tokens;
DROP TABLE IF EXISTS public.api_keys;
DROP TABLE IF EXISTS public.registered_apps;
*/
