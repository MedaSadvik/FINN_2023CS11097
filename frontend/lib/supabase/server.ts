import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";
import { connection } from "next/server";
import { supabaseKey, supabaseUrl } from "./env";

/** A database client that acts as the signed-in person: every query goes through their row level security. */
export async function createClient() {
  await connection(); // per-person data: render at request time, never at build time (the auth library reads the clock)
  const store = await cookies();
  return createServerClient(supabaseUrl!, supabaseKey!, {
    cookies: {
      getAll: () => store.getAll(),
      setAll(list) {
        try {
          list.forEach(({ name, value, options }) => store.set(name, value, options));
        } catch {
          // called from a page, where cookies are read-only. proxy.ts refreshes the session instead.
        }
      },
    },
  });
}
