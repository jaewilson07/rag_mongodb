import { NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL}/api/v1/wiki/projects`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    if (!res.ok) {
      // Return empty projects list if backend is not available
      return NextResponse.json({ projects: [] });
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Wiki projects API error:", error);
    // Return empty projects list if backend is not available
    return NextResponse.json({ projects: [] });
  }
}
