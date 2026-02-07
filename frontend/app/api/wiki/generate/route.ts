import { NextRequest } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    const res = await fetch(`${BACKEND_URL}/api/v1/wiki/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      const error = await res.text();
      return new Response(error || `Backend error: ${res.status}`, {
        status: res.status,
      });
    }

    // Stream the response through
    return new Response(res.body, {
      headers: {
        "Content-Type": "text/plain; charset=utf-8",
        "Transfer-Encoding": "chunked",
      },
    });
  } catch (error) {
    console.error("Wiki generate API error:", error);
    return new Response("Failed to connect to backend service", {
      status: 502,
    });
  }
}
