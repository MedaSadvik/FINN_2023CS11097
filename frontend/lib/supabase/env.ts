export const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
export const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
/** Accounts are optional: without these two variables the site runs as a signed-out demo. */
export const accountsEnabled = Boolean(supabaseUrl && supabaseKey);
