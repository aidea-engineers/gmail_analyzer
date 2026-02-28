"use client";

import { createContext, useContext, useEffect, useState, useRef, ReactNode } from "react";
import { Session } from "@supabase/supabase-js";
import { supabase } from "@/lib/supabase";

interface AuthUser {
  id: string;
  email: string;
  role: string;
  engineer_id: number | null;
  display_name: string;
  is_admin: boolean;
}

interface AuthContextType {
  session: Session | null;
  user: AuthUser | null;
  loading: boolean;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
  session: null,
  user: null,
  loading: true,
  signOut: async () => {},
});

export function useAuth() {
  return useContext(AuthContext);
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const CACHE_KEY = "aidea_user_profile";
const CACHE_TTL = 5 * 60 * 1000; // 5分

function getCachedUser(): AuthUser | null {
  try {
    const raw = sessionStorage.getItem(CACHE_KEY);
    if (!raw) return null;
    const { user, ts } = JSON.parse(raw);
    if (Date.now() - ts > CACHE_TTL) {
      sessionStorage.removeItem(CACHE_KEY);
      return null;
    }
    return user;
  } catch {
    return null;
  }
}

function setCachedUser(user: AuthUser | null) {
  try {
    if (user) {
      sessionStorage.setItem(CACHE_KEY, JSON.stringify({ user, ts: Date.now() }));
    } else {
      sessionStorage.removeItem(CACHE_KEY);
    }
  } catch { /* ignore */ }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const fetchingRef = useRef(false);

  useEffect(() => {
    // Supabase未設定の場合は認証をスキップ（ダミー管理者として動作）
    if (!supabase) {
      setUser({
        id: "__auth_disabled__",
        email: "admin@localhost",
        role: "admin",
        engineer_id: null,
        display_name: "Admin",
        is_admin: true,
      });
      setLoading(false);
      return;
    }

    // 初期セッション取得
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      if (session) {
        // キャッシュがあればすぐ表示し、バックグラウンドで最新化
        const cached = getCachedUser();
        if (cached) {
          setUser(cached);
          setLoading(false);
          fetchUserProfile(session.access_token, true); // バックグラウンド更新
        } else {
          fetchUserProfile(session.access_token, false);
        }
      } else {
        setLoading(false);
      }
    });

    // セッション変更の監視（ログイン/ログアウト時）
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, session) => {
        setSession(session);
        if (session) {
          setLoading(true); // ログイン直後にloadingをtrueに戻す
          fetchUserProfile(session.access_token, false);
        } else {
          setUser(null);
          setCachedUser(null);
          setLoading(false);
        }
      }
    );

    return () => subscription.unsubscribe();
  }, []);

  async function fetchUserProfile(token: string, background: boolean) {
    // 重複呼び出し防止
    if (fetchingRef.current) return;
    fetchingRef.current = true;

    try {
      const res = await fetch(`${API_BASE}/api/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
      });
      if (res.ok) {
        const data = await res.json();
        setUser(data);
        setCachedUser(data);
      } else {
        setUser(null);
        setCachedUser(null);
      }
    } catch {
      // バックグラウンド更新失敗時はキャッシュを維持
      if (!background) {
        setUser(null);
        setCachedUser(null);
      }
    } finally {
      fetchingRef.current = false;
      if (!background) {
        setLoading(false);
      }
    }
  }

  async function signOut() {
    if (supabase) {
      await supabase.auth.signOut();
    }
    setSession(null);
    setUser(null);
    setCachedUser(null);
  }

  return (
    <AuthContext.Provider value={{ session, user, loading, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}
