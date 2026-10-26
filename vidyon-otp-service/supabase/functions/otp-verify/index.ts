import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const MY_VIDYON_APP_ID = Deno.env.get("MY_VIDYON_APP_ID")!;

const cors = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "x-otp-api-key, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: cors });
  if (req.method !== "POST")
    return new Response(JSON.stringify({ error: "Method not allowed" }), {
      status: 405,
      headers: { ...cors, "Content-Type": "application/json" },
    });

  const t0 = Date.now();
  const db = createClient(SUPABASE_URL, SERVICE_ROLE_KEY);
  const key = req.headers.get("x-otp-api-key") ?? "";

  if (!key.startsWith("otp_"))
    return new Response(JSON.stringify({ error: "Missing API key" }), {
      status: 401,
      headers: { ...cors, "Content-Type": "application/json" },
    });

  const body = await req.json().catch(() => ({}));
  if (!body.request_id || !body.otp)
    return new Response(JSON.stringify({ error: "request_id and otp required" }), {
      status: 400,
      headers: { ...cors, "Content-Type": "application/json" },
    });

  // Extract clean client IP (first entry if x-forwarded-for contains proxy chain)
  const clientIp = req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() || null;

  const { data: keyData, error: keyErr } = await db.rpc("validate_api_key", {
    p_raw_key: key,
    p_required_scope: "verify",
    p_caller_ip: clientIp,
  });
  if (keyErr)
    return new Response(JSON.stringify({ error: keyErr.message }), {
      status: 401,
      headers: { ...cors, "Content-Type": "application/json" },
    });

  const { data: result, error: verErr } = await db.rpc("verify_otp", {
    p_app_id: MY_VIDYON_APP_ID,
    p_request_id: body.request_id,
    p_otp_input: body.otp,
  });

  await db.from("otp_audit_log").insert({
    app_id: MY_VIDYON_APP_ID,
    key_id: keyData?.id,
    action: "verify",
    outcome: verErr ? "error" : result?.verified ? "success" : "invalid",
    request_id: body.request_id,
    error_code: verErr?.message ?? null,
    latency_ms: Date.now() - t0,
    ip_address: clientIp,
  });

  if (verErr)
    return new Response(JSON.stringify({ error: verErr.message }), {
      status: 400,
      headers: { ...cors, "Content-Type": "application/json" },
    });

  return new Response(JSON.stringify(result), {
    status: 200,
    headers: { ...cors, "Content-Type": "application/json" },
  });
});
