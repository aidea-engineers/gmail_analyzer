"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  listUsers,
  createUser,
  updateUser,
  deleteUser,
  resetUserPassword,
  inviteUser,
  reinviteUser,
  getEngineersBrief,
} from "@/lib/api";
import type { UserProfile, EngineerBrief } from "@/types";

export default function AdminUsersPage() {
  const [users, setUsers] = useState<UserProfile[]>([]);
  const [engineers, setEngineers] = useState<EngineerBrief[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // 新規作成フォーム
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState({
    email: "",
    password: "",
    role: "engineer",
    engineer_id: "" as string,
    display_name: "",
  });
  const [creating, setCreating] = useState(false);

  // 編集
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState({
    role: "",
    engineer_id: "" as string,
    display_name: "",
  });
  const [saving, setSaving] = useState(false);

  // 招待フォーム
  const [showInvite, setShowInvite] = useState(false);
  const [inviteForm, setInviteForm] = useState({
    email: "",
    role: "engineer",
    engineer_id: "" as string,
    display_name: "",
  });
  const [inviting, setInviting] = useState(false);

  // PW リセット
  const [pwResetId, setPwResetId] = useState<string | null>(null);
  const [newPassword, setNewPassword] = useState("");
  const [resetting, setResetting] = useState(false);

  const load = useCallback(async () => {
    try {
      const [usersRes, engs] = await Promise.all([
        listUsers(),
        getEngineersBrief(),
      ]);
      setUsers(usersRes.users);
      setEngineers(engs);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const clearMessages = () => { setError(""); setSuccess(""); };

  const handleCreate = async () => {
    clearMessages();
    if (!createForm.email || !createForm.password) {
      setError("メールアドレスとパスワードは必須です");
      return;
    }
    setCreating(true);
    try {
      await createUser({
        email: createForm.email,
        password: createForm.password,
        role: createForm.role,
        engineer_id: createForm.engineer_id ? Number(createForm.engineer_id) : null,
        display_name: createForm.display_name,
      });
      setSuccess("ユーザーを作成しました");
      setCreateForm({ email: "", password: "", role: "engineer", engineer_id: "", display_name: "" });
      setShowCreate(false);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setCreating(false);
    }
  };

  const handleEdit = (u: UserProfile) => {
    setEditingId(u.id);
    setEditForm({
      role: u.role,
      engineer_id: u.engineer_id ? String(u.engineer_id) : "",
      display_name: u.display_name || "",
    });
    clearMessages();
  };

  const handleSaveEdit = async () => {
    if (!editingId) return;
    clearMessages();
    setSaving(true);
    try {
      await updateUser(editingId, {
        role: editForm.role,
        engineer_id: editForm.engineer_id ? Number(editForm.engineer_id) : null,
        display_name: editForm.display_name,
      });
      setSuccess("更新しました");
      setEditingId(null);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (u: UserProfile) => {
    clearMessages();
    if (!confirm(`${u.email} を削除しますか？`)) return;
    try {
      await deleteUser(u.id);
      setSuccess("削除しました");
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const handleResetPw = async () => {
    if (!pwResetId || !newPassword) return;
    clearMessages();
    setResetting(true);
    try {
      await resetUserPassword(pwResetId, newPassword);
      setSuccess("パスワードをリセットしました");
      setPwResetId(null);
      setNewPassword("");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setResetting(false);
    }
  };

  const handleInvite = async () => {
    clearMessages();
    if (!inviteForm.email) {
      setError("メールアドレスは必須です");
      return;
    }
    setInviting(true);
    try {
      await inviteUser({
        email: inviteForm.email,
        role: inviteForm.role,
        engineer_id: inviteForm.engineer_id ? Number(inviteForm.engineer_id) : null,
        display_name: inviteForm.display_name,
      });
      setSuccess("招待メールを送信しました");
      setInviteForm({ email: "", role: "engineer", engineer_id: "", display_name: "" });
      setShowInvite(false);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setInviting(false);
    }
  };

  const handleReinvite = async (u: UserProfile) => {
    clearMessages();
    if (!confirm(`${u.email} に招待メールを再送しますか？\n（Auth側のユーザーを再作成して招待メールを送り直します）`)) return;
    try {
      await reinviteUser(u.id);
      setSuccess("招待メールを再送しました");
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const engineerName = (engId: number | null) => {
    if (!engId) return "-";
    const eng = engineers.find((e) => e.id === engId);
    return eng ? eng.name : `ID:${engId}`;
  };

  if (loading) return <p style={{ color: "var(--muted)" }}>読み込み中...</p>;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6" style={{ color: "var(--foreground)" }}>
        アカウント管理
      </h1>

      {error && (
        <div className="mb-4 p-3 rounded-lg bg-red-50 text-red-700 text-sm">{error}</div>
      )}
      {success && (
        <div className="mb-4 p-3 rounded-lg bg-green-50 text-green-700 text-sm">{success}</div>
      )}

      {/* アクションボタン */}
      <div className="flex gap-2 mb-4">
        <button
          onClick={() => { setShowInvite(!showInvite); setShowCreate(false); clearMessages(); }}
          className="px-4 py-2 rounded-lg text-sm text-white"
          style={{ background: showInvite ? "#6b7280" : "var(--primary)" }}
        >
          {showInvite ? "キャンセル" : "招待メール送信"}
        </button>
        <button
          onClick={() => { setShowCreate(!showCreate); setShowInvite(false); clearMessages(); }}
          className="px-4 py-2 rounded-lg text-sm"
          style={{ background: "var(--background)", border: "1px solid var(--border)", color: "var(--foreground)" }}
        >
          {showCreate ? "キャンセル" : "手動ユーザー作成"}
        </button>
      </div>

      {/* 招待フォーム */}
      {showInvite && (
        <div
          className="mb-6 p-4 rounded-xl space-y-3"
          style={{ background: "var(--card-bg)", border: "1px solid var(--border)" }}
        >
          <h2 className="font-semibold text-sm" style={{ color: "var(--foreground)" }}>
            エンジニア招待
          </h2>
          <p className="text-xs" style={{ color: "var(--muted)" }}>
            招待メールが送信され、受信者がパスワードを設定してログインできます。
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="text-xs block mb-1" style={{ color: "var(--muted)" }}>
                メールアドレス *
              </label>
              <input
                type="email"
                value={inviteForm.email}
                onChange={(e) => setInviteForm({ ...inviteForm, email: e.target.value })}
                className="w-full px-3 py-2 rounded-lg text-sm"
                style={{ background: "var(--background)", border: "1px solid var(--border)", color: "var(--foreground)" }}
              />
            </div>
            <div>
              <label className="text-xs block mb-1" style={{ color: "var(--muted)" }}>
                ロール
              </label>
              <select
                value={inviteForm.role}
                onChange={(e) => setInviteForm({ ...inviteForm, role: e.target.value })}
                className="w-full px-3 py-2 rounded-lg text-sm"
                style={{ background: "var(--background)", border: "1px solid var(--border)", color: "var(--foreground)" }}
              >
                <option value="engineer">エンジニア</option>
                <option value="sales">営業</option>
                <option value="admin">管理者</option>
              </select>
            </div>
            <div>
              <label className="text-xs block mb-1" style={{ color: "var(--muted)" }}>
                紐付けエンジニア
              </label>
              <select
                value={inviteForm.engineer_id}
                onChange={(e) => setInviteForm({ ...inviteForm, engineer_id: e.target.value })}
                className="w-full px-3 py-2 rounded-lg text-sm"
                style={{ background: "var(--background)", border: "1px solid var(--border)", color: "var(--foreground)" }}
              >
                <option value="">未設定（後で紐付け）</option>
                {engineers.map((eng) => (
                  <option key={eng.id} value={eng.id}>
                    {eng.name} ({eng.status})
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs block mb-1" style={{ color: "var(--muted)" }}>
                表示名
              </label>
              <input
                type="text"
                value={inviteForm.display_name}
                onChange={(e) => setInviteForm({ ...inviteForm, display_name: e.target.value })}
                className="w-full px-3 py-2 rounded-lg text-sm"
                style={{ background: "var(--background)", border: "1px solid var(--border)", color: "var(--foreground)" }}
              />
            </div>
          </div>
          <button
            onClick={handleInvite}
            disabled={inviting}
            className="px-4 py-2 rounded-lg text-sm text-white disabled:opacity-50"
            style={{ background: "var(--primary)" }}
          >
            {inviting ? "送信中..." : "招待メールを送信"}
          </button>
        </div>
      )}

      {/* 新規作成フォーム */}
      {showCreate && (
        <div
          className="mb-6 p-4 rounded-xl space-y-3"
          style={{ background: "var(--card-bg)", border: "1px solid var(--border)" }}
        >
          <h2 className="font-semibold text-sm" style={{ color: "var(--foreground)" }}>
            新規ユーザー作成
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="text-xs block mb-1" style={{ color: "var(--muted)" }}>
                メールアドレス *
              </label>
              <input
                type="email"
                value={createForm.email}
                onChange={(e) => setCreateForm({ ...createForm, email: e.target.value })}
                className="w-full px-3 py-2 rounded-lg text-sm"
                style={{ background: "var(--background)", border: "1px solid var(--border)", color: "var(--foreground)" }}
              />
            </div>
            <div>
              <label className="text-xs block mb-1" style={{ color: "var(--muted)" }}>
                パスワード *
              </label>
              <input
                type="password"
                value={createForm.password}
                onChange={(e) => setCreateForm({ ...createForm, password: e.target.value })}
                className="w-full px-3 py-2 rounded-lg text-sm"
                style={{ background: "var(--background)", border: "1px solid var(--border)", color: "var(--foreground)" }}
              />
            </div>
            <div>
              <label className="text-xs block mb-1" style={{ color: "var(--muted)" }}>
                ロール
              </label>
              <select
                value={createForm.role}
                onChange={(e) => setCreateForm({ ...createForm, role: e.target.value })}
                className="w-full px-3 py-2 rounded-lg text-sm"
                style={{ background: "var(--background)", border: "1px solid var(--border)", color: "var(--foreground)" }}
              >
                <option value="engineer">エンジニア</option>
                <option value="sales">営業</option>
                <option value="admin">管理者</option>
              </select>
            </div>
            <div>
              <label className="text-xs block mb-1" style={{ color: "var(--muted)" }}>
                紐付けエンジニア
              </label>
              <select
                value={createForm.engineer_id}
                onChange={(e) => setCreateForm({ ...createForm, engineer_id: e.target.value })}
                className="w-full px-3 py-2 rounded-lg text-sm"
                style={{ background: "var(--background)", border: "1px solid var(--border)", color: "var(--foreground)" }}
              >
                <option value="">未設定</option>
                {engineers.map((eng) => (
                  <option key={eng.id} value={eng.id}>
                    {eng.name} ({eng.status})
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs block mb-1" style={{ color: "var(--muted)" }}>
                表示名
              </label>
              <input
                type="text"
                value={createForm.display_name}
                onChange={(e) => setCreateForm({ ...createForm, display_name: e.target.value })}
                className="w-full px-3 py-2 rounded-lg text-sm"
                style={{ background: "var(--background)", border: "1px solid var(--border)", color: "var(--foreground)" }}
              />
            </div>
          </div>
          <button
            onClick={handleCreate}
            disabled={creating}
            className="px-4 py-2 rounded-lg text-sm text-white disabled:opacity-50"
            style={{ background: "var(--primary)" }}
          >
            {creating ? "作成中..." : "作成"}
          </button>
        </div>
      )}

      {/* ユーザー一覧テーブル */}
      <div
        className="rounded-xl overflow-hidden"
        style={{ background: "var(--card-bg)", border: "1px solid var(--border)" }}
      >
        <table className="w-full text-sm">
          <thead>
            <tr style={{ background: "var(--background)" }}>
              <th className="text-left px-4 py-3 font-medium" style={{ color: "var(--muted)" }}>メール</th>
              <th className="text-left px-4 py-3 font-medium" style={{ color: "var(--muted)" }}>ロール</th>
              <th className="text-left px-4 py-3 font-medium" style={{ color: "var(--muted)" }}>紐付けエンジニア</th>
              <th className="text-left px-4 py-3 font-medium" style={{ color: "var(--muted)" }}>表示名</th>
              <th className="text-right px-4 py-3 font-medium" style={{ color: "var(--muted)" }}>操作</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr
                key={u.id}
                className="border-t"
                style={{ borderColor: "var(--border)" }}
              >
                {editingId === u.id ? (
                  <>
                    <td className="px-4 py-3" style={{ color: "var(--foreground)" }}>
                      {u.email}
                    </td>
                    <td className="px-4 py-3">
                      <select
                        value={editForm.role}
                        onChange={(e) => setEditForm({ ...editForm, role: e.target.value })}
                        className="px-2 py-1 rounded text-sm"
                        style={{ background: "var(--background)", border: "1px solid var(--border)", color: "var(--foreground)" }}
                      >
                        <option value="engineer">エンジニア</option>
                        <option value="admin">管理者</option>
                      </select>
                    </td>
                    <td className="px-4 py-3">
                      <select
                        value={editForm.engineer_id}
                        onChange={(e) => setEditForm({ ...editForm, engineer_id: e.target.value })}
                        className="px-2 py-1 rounded text-sm"
                        style={{ background: "var(--background)", border: "1px solid var(--border)", color: "var(--foreground)" }}
                      >
                        <option value="">未設定</option>
                        {engineers.map((eng) => (
                          <option key={eng.id} value={eng.id}>
                            {eng.name}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="px-4 py-3">
                      <input
                        type="text"
                        value={editForm.display_name}
                        onChange={(e) => setEditForm({ ...editForm, display_name: e.target.value })}
                        className="px-2 py-1 rounded text-sm w-full"
                        style={{ background: "var(--background)", border: "1px solid var(--border)", color: "var(--foreground)" }}
                      />
                    </td>
                    <td className="px-4 py-3 text-right space-x-2">
                      <button
                        onClick={handleSaveEdit}
                        disabled={saving}
                        className="px-3 py-1 rounded text-xs text-white disabled:opacity-50"
                        style={{ background: "var(--primary)" }}
                      >
                        {saving ? "保存中..." : "保存"}
                      </button>
                      <button
                        onClick={() => setEditingId(null)}
                        className="px-3 py-1 rounded text-xs"
                        style={{ background: "var(--background)", border: "1px solid var(--border)", color: "var(--foreground)" }}
                      >
                        キャンセル
                      </button>
                    </td>
                  </>
                ) : (
                  <>
                    <td className="px-4 py-3" style={{ color: "var(--foreground)" }}>
                      {u.email}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`px-2 py-0.5 rounded text-xs ${
                          u.role === "admin"
                            ? "bg-purple-100 text-purple-700"
                            : u.role === "sales"
                            ? "bg-green-100 text-green-700"
                            : "bg-blue-100 text-blue-700"
                        }`}
                      >
                        {u.role === "admin" ? "管理者" : u.role === "sales" ? "営業" : "エンジニア"}
                      </span>
                    </td>
                    <td className="px-4 py-3" style={{ color: "var(--foreground)" }}>
                      {u.engineer_id ? (
                        <Link
                          href={`/engineers?id=${u.engineer_id}`}
                          className="underline hover:opacity-70"
                          style={{ color: "var(--primary)" }}
                        >
                          {engineerName(u.engineer_id)}
                        </Link>
                      ) : (
                        "-"
                      )}
                    </td>
                    <td className="px-4 py-3" style={{ color: "var(--foreground)" }}>
                      {u.display_name || "-"}
                    </td>
                    <td className="px-4 py-3 text-right space-x-2">
                      <button
                        onClick={() => handleEdit(u)}
                        className="px-3 py-1 rounded text-xs"
                        style={{ background: "var(--background)", border: "1px solid var(--border)", color: "var(--foreground)" }}
                      >
                        編集
                      </button>
                      <button
                        onClick={() => handleReinvite(u)}
                        className="px-3 py-1 rounded text-xs"
                        style={{ background: "var(--background)", border: "1px solid var(--border)", color: "var(--foreground)" }}
                      >
                        再招待
                      </button>
                      <button
                        onClick={() => { setPwResetId(u.id); setNewPassword(""); clearMessages(); }}
                        className="px-3 py-1 rounded text-xs"
                        style={{ background: "var(--background)", border: "1px solid var(--border)", color: "var(--foreground)" }}
                      >
                        PW変更
                      </button>
                      <button
                        onClick={() => handleDelete(u)}
                        className="px-3 py-1 rounded text-xs bg-red-50 text-red-600 hover:bg-red-100"
                      >
                        削除
                      </button>
                    </td>
                  </>
                )}
              </tr>
            ))}
            {users.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center" style={{ color: "var(--muted)" }}>
                  ユーザーがいません
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* PW リセットモーダル */}
      {pwResetId && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center">
          <div
            className="rounded-xl p-6 w-full max-w-md space-y-4"
            style={{ background: "var(--card-bg)", border: "1px solid var(--border)" }}
          >
            <h3 className="font-semibold" style={{ color: "var(--foreground)" }}>
              パスワードリセット
            </h3>
            <p className="text-sm" style={{ color: "var(--muted)" }}>
              {users.find((u) => u.id === pwResetId)?.email}
            </p>
            <input
              type="password"
              placeholder="新しいパスワード"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="w-full px-3 py-2 rounded-lg text-sm"
              style={{ background: "var(--background)", border: "1px solid var(--border)", color: "var(--foreground)" }}
            />
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => { setPwResetId(null); setNewPassword(""); }}
                className="px-4 py-2 rounded-lg text-sm"
                style={{ background: "var(--background)", border: "1px solid var(--border)", color: "var(--foreground)" }}
              >
                キャンセル
              </button>
              <button
                onClick={handleResetPw}
                disabled={resetting || !newPassword}
                className="px-4 py-2 rounded-lg text-sm text-white disabled:opacity-50"
                style={{ background: "var(--primary)" }}
              >
                {resetting ? "リセット中..." : "リセット"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
