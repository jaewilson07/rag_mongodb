import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    const res = await fetch(`${BACKEND_URL}/api/v1/ingest/web`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: `Backend error: ${res.status}` }));
      return NextResponse.json(error, { status: res.status });
    }

    const data = await res.json();
    return NextResponse.json(data, { status: 202 });
  } catch (error) {
    console.error("Ingest web API error:", error);
    return NextResponse.json(
      { detail: "Failed to connect to backend service. Make sure the RAG agent is running." },
      { status: 502 }
    );
  }
}
