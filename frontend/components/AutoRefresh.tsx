"use client";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

/** Re-reads the page every few seconds while a build is running, so the result appears without a manual reload. */
export function AutoRefresh({ everyMs = 8000 }: { everyMs?: number }) {
  const router = useRouter();
  useEffect(() => {
    const id = setInterval(() => router.refresh(), everyMs);
    return () => clearInterval(id);
  }, [router, everyMs]);
  return null;
}
