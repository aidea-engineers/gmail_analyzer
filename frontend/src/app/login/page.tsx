"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { useAuth } from "@/components/AuthProvider";

export default function LoginPage() {
  const router = useRouter();
  const { user } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [loginSuccess, setLoginSuccess] = useState(false);

  // AuthProviderがuserをセットしたらロール別にリダイレクト
  useEffect(() => {
    if (user) {
      router.push(user.role === "engineer" ? "/my-profile" : "/");
    }
  }, [user, router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      if (!supabase) {
        router.push("/");
        return;
      }
      const { error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });
      if (error) {
        setError(error.message === "Invalid login credentials"
          ? "メールアドレスまたはパスワードが正しくありません"
          : error.message);
        setLoading(false);
      } else {
        // router.pushはuseEffectでuserが設定されたときに実行
        setLoginSuccess(true);
      }
    } catch {
      setError("ログインに失敗しました");
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
            SES事業管理システム
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1" style={{ color: "var(--foreground)" }}>
              メールアドレス
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full px-3 py-2 rounded-lg text-sm"
              style={{
                background: "var(--background)",
                border: "1px solid var(--border)",
                color: "var(--foreground)",
              }}
              placeholder="example@cloud-link.co.jp"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1" style={{ color: "var(--foreground)" }}>
              パスワード
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full px-3 py-2 rounded-lg text-sm"
              style={{
                background: "var(--background)",
                border: "1px solid var(--border)",
                color: "var(--foreground)",
              }}
            />
          </div>

          {error && (
            <p className="text-sm text-red-500">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading || loginSuccess}
            className="w-full py-2.5 rounded-lg text-sm font-medium text-white transition-colors"
            style={{ background: (loading || loginSuccess) ? "#6b7280" : "var(--primary)" }}
          >
            {loginSuccess ? "認証中..." : loading ? "ログイン中..." : "ログイン"}
          </button>
        </form>
      </div>
    </div>
  );
}
