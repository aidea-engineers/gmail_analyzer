"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";

export default function SetPasswordPage() {
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    // Supabase が招待リンクからのトークンを自動処理し、セッションを確立するのを待つ
    if (!supabase) {
      setError("認証システムが設定されていません");
      setChecking(false);
      return;
    }

    const sb = supabase!;
    const handleSession = async () => {
      // URLハッシュにトークンがある場合、Supabaseが自動的にセッションを確立する
      const { data: { session } } = await sb.auth.getSession();
      if (!session) {
        // セッションがない場合は少し待ってリトライ（リダイレクト直後の場合）
        await new Promise(r => setTimeout(r, 1000));
        const { data: { session: retrySession } } = await sb.auth.getSession();
        if (!retrySession) {
          setError("招待リンクが無効または期限切れです。管理者に再招待を依頼してください。");
        }
      }
      setChecking(false);
    };

    handleSession();
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    if (password.length < 8) {
      setError("パスワードは8文字以上で入力してください");
      return;
    }
    if (password !== confirmPassword) {
      setError("パスワードが一致しません");
      return;
    }

    setLoading(true);
    try {
      if (!supabase) throw new Error("認証システムが設定されていません");

      const { error } = await supabase.auth.updateUser({ password });
      if (error) {
        setError(error.message);
        setLoading(false);
        return;
      }

      setSuccess(true);
      // 2秒後にプロフィール登録ページへ自動遷移
      setTimeout(() => router.push("/my-profile"), 2000);
    } catch {
      setError("パスワード設定に失敗しました");
      setLoading(false);
    }
  }

  if (checking) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: "var(--background)" }}>
        <p style={{ color: "var(--muted)" }}>認証情報を確認中...</p>
      </div>
    );
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
            パスワード設定
          </p>
        </div>

        {success ? (
          <div className="text-center space-y-5">
            <div className="p-4 rounded-lg bg-green-50 text-green-700 text-sm">
              <p className="font-semibold text-base mb-2">パスワード設定完了</p>
              <p className="mb-3">
                プロフィール登録ページに移動します...
              </p>
              <p className="text-xs" style={{ color: "var(--muted)" }}>
                次回ログイン: <span className="font-mono">gmail-analyzer-nu.vercel.app</span>
              </p>
            </div>
          </div>
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
                className="w-full px-3 py-2 rounded-lg text-sm"
                style={{
                  background: "var(--background)",
                  border: "1px solid var(--border)",
                  color: "var(--foreground)",
                }}
                placeholder="8文字以上"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1" style={{ color: "var(--foreground)" }}>
                パスワード確認
              </label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                className="w-full px-3 py-2 rounded-lg text-sm"
                style={{
                  background: "var(--background)",
                  border: "1px solid var(--border)",
                  color: "var(--foreground)",
                }}
                placeholder="もう一度入力"
              />
            </div>

            {error && (
              <p className="text-sm text-red-500">{error}</p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 rounded-lg text-sm font-medium text-white transition-colors"
              style={{ background: loading ? "#6b7280" : "var(--primary)" }}
            >
              {loading ? "設定中..." : "パスワードを設定"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
