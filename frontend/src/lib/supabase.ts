import { createClient, SupabaseClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || "";
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "";

// 招待リンク（type=invite）を検出したらセッションストレージに記録しておく
// → AuthProvider でパスワード設定ページへリダイレクトするために使う
if (typeof window !== "undefined") {
  const hash = window.location.hash;
  if (hash.includes("type=invite")) {
    sessionStorage.setItem("pending_invite", "1");
  }
}

// URL未設定時はnull（認証無効モード）
export const supabase: SupabaseClient | null =
  supabaseUrl ? createClient(supabaseUrl, supabaseAnonKey) : null;
