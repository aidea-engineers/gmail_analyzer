"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";

export default function SetPasswordPage() {
  const router = useRouter();
  const [ready, setReady] = useState(false); // セッション確立済みかどうか
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (!supabase) {
      router.replace("/login");
      return;
    }

    // Supabase が URL ハッシュ（招待トークン）を処理してセッションを確立するまで待つ
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if (session) {
        // セッション確立 → パスワード設定フォームを表示
        setReady(true);
      }
    });

    // 既にセッションがある場合の対応（ページリロード時など）
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session) {
        setReady(true);
      }
    });

    return () => subscription.unsubscribe();
  }, [router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    if (password.length < 8) {
      setError("パスワードは8文字以上で入力してください");
      return;
    }
    if (password !== confirm) {
      setError("パスワードが一致しません");
      return;
    }

    setLoading(true);
    try {
      const { error: updateError } = await supabase!.auth.updateUser({ password });
      if (updateError) {
        setError(updateError.message);
      } else {
        setDone(true);
        // 設定完了後、マイプロフィールへ
        setTimeout(() => router.replace("/my-profile"), 2000);
      }
    } catch {
      setError("パスワードの設定に失敗しました");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center" style={{ background: "var(--background)" }}>
      <div
        className="w-full max-w-sm p-8 rounded-xl shadow-lg"
        style={{ background: "var(--card-bg)", border: "1px solid var(--border)" }}
      >
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold" style={{ color: "var(--foreground)" }}>
            AIdea Platform
          </h1>
          <p className="text-sm mt-2" style={{ color: "var(--muted)" }}>
            パスワードを設定してください
          </p>
        </div>

        {done ? (
          <p className="text-center text-sm" style={{ color: "var(--primary)" }}>
            パスワードを設定しました。マイプロフィールへ移動します…
          </p>
        ) : !ready ? (
          <p className="text-center text-sm" style={{ color: "var(--muted)" }}>
            認証情報を確認中…
          </p>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1" style={{ color: "var(--foreground)" }}>
                新しいパスワード
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
                placeholder="8文字以上"
                className="w-full px-3 py-2 rounded-lg text-sm"
                style={{
                  background: "var(--background)",
                  border: "1px solid var(--border)",
                  color: "var(--foreground)",
                }}
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1" style={{ color: "var(--foreground)" }}>
                パスワード（確認）
              </label>
              <input
                type="password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                required
                className="w-full px-3 py-2 rounded-lg text-sm"
                style={{
                  background: "var(--background)",
                  border: "1px solid var(--border)",
                  color: "var(--foreground)",
                }}
              />
            </div>

            {error && <p className="text-sm text-red-500">{error}</p>}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 rounded-lg text-sm font-medium text-white transition-colors"
              style={{ background: loading ? "#6b7280" : "var(--primary)" }}
            >
              {loading ? "設定中…" : "パスワードを設定する"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
