import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const res = await fetch(`${BACKEND_URL}/api/v1/readings/${params.id}`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    if (!res.ok) {
      if (res.status === 404) {
        return NextResponse.json({ detail: "Reading not found" }, { status: 404 });
      }
      return NextResponse.json({ detail: `Error ${res.status}` }, { status: res.status });
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Reading detail API error:", error);
    return NextResponse.json(
      { detail: "Failed to connect to backend service" },
      { status: 502 }
    );
  }
}
