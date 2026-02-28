import { createClient, SupabaseClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || "";
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "";

// URL未設定時はnull（認証無効モード）
export const supabase: SupabaseClient | null =
  supabaseUrl ? createClient(supabaseUrl, supabaseAnonKey) : null;
