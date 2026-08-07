import { NextRequest, NextResponse } from "next/server";
import { createHmac, timingSafeEqual } from "crypto";
import { createServerSupabaseClient } from "@/lib/supabase-server";

function generateToken(email: string, secret: string): string {
  return createHmac("sha256", secret)
    .update(email.toLowerCase())
    .digest("base64url")
    .replace(/=+$/, "");
}

export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  const email = searchParams.get("email");
  const token = searchParams.get("token");

  if (!email || !token) {
    return new NextResponse("Missing email or token", { status: 400 });
  }

  const secret = process.env.UNSUBSCRIBE_SECRET;
  if (!secret) {
    return new NextResponse("Server misconfiguration", { status: 500 });
  }

  const expected = generateToken(email, secret);

  // Constant-time comparison to prevent timing attacks
  const tokenBuf = Buffer.from(token);
  const expectedBuf = Buffer.from(expected);
  const valid =
    tokenBuf.length === expectedBuf.length &&
    timingSafeEqual(tokenBuf, expectedBuf);

  if (!valid) {
    return new NextResponse("Invalid unsubscribe link", { status: 403 });
  }

  const supabase = await createServerSupabaseClient();
  const { error } = await supabase
    .from("unsubscribed")
    .upsert({ email: email.toLowerCase() });

  if (error) {
    console.error("Unsubscribe DB error:", error);
    return new NextResponse("Failed to process — please try again", { status: 500 });
  }

  return new NextResponse(
    `<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Unsubscribed</title>
<style>body{font-family:sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;background:#f9fafb}
.box{text-align:center;padding:2rem;max-width:400px}
h1{font-size:1.25rem;font-weight:600;color:#111827;margin-bottom:.5rem}
p{color:#6b7280;font-size:.9rem}</style>
</head>
<body><div class="box">
<h1>You've been unsubscribed</h1>
<p>${email} has been removed from our outreach list. You won't hear from us again.</p>
</div></body></html>`,
    { status: 200, headers: { "Content-Type": "text/html" } }
  );
}
