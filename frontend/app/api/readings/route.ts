import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const params = new URLSearchParams();
    if (searchParams.get("user_id")) params.set("user_id", searchParams.get("user_id")!);
    if (searchParams.get("limit")) params.set("limit", searchParams.get("limit")!);
    if (searchParams.get("offset")) params.set("offset", searchParams.get("offset")!);

    const qs = params.toString() ? `?${params.toString()}` : "";

    const res = await fetch(`${BACKEND_URL}/api/v1/readings${qs}`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    if (!res.ok) {
      return NextResponse.json({ readings: [], total: 0 });
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Readings list API error:", error);
    return NextResponse.json({ readings: [], total: 0 });
  }
}
