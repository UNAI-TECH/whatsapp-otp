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
  const phone = (body.phone ?? "").trim();
  if (!phone)
    return new Response(JSON.stringify({ error: "phone required" }), {
      status: 400,
      headers: { ...cors, "Content-Type": "application/json" },
    });

  // Extract clean client IP (first entry if x-forwarded-for contains proxy chain)
  const clientIp = req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() || null;
  const userAgent = req.headers.get("user-agent") ?? null;

  // Validate API key
  const { data: keyData, error: keyErr } = await db.rpc("validate_api_key", {
    p_raw_key: key,
    p_required_scope: "generate",
    p_caller_ip: clientIp,
  });
  if (keyErr)
    return new Response(JSON.stringify({ error: keyErr.message }), {
      status: 401,
      headers: { ...cors, "Content-Type": "application/json" },
    });

  // Generate OTP
  const { data: otp, error: otpErr } = await db.rpc("generate_otp", {
    p_app_id: MY_VIDYON_APP_ID,
    p_phone_e164: phone,
    p_ip: clientIp,
    p_user_agent: userAgent,
  });

  // Audit log
  await db.from("otp_audit_log").insert({
    app_id: MY_VIDYON_APP_ID,
    key_id: keyData?.id,
    action: "generate",
    outcome: otpErr ? (otpErr.message.includes("RATE") ? "rate_limited" : "error") : "success",
    request_id: otp?.request_id ?? null,
    error_code: otpErr?.message ?? null,
    latency_ms: Date.now() - t0,
    ip_address: clientIp,
  });

  if (otpErr)
    return new Response(JSON.stringify({ error: otpErr.message }), {
      status: otpErr.message.includes("RATE") ? 429 : 400,
      headers: { ...cors, "Content-Type": "application/json" },
    });

  return new Response(JSON.stringify(otp), {
    status: 200,
    headers: { ...cors, "Content-Type": "application/json" },
  });
});
