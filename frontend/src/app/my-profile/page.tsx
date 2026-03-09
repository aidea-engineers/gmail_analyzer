"use client";

import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/components/AuthProvider";
import { getEngineerDetail, updateEngineer, changeMyPassword } from "@/lib/api";
import type { EngineerDetail, EngineerForm } from "@/types";
import {
  EMPTY_FORM,
  SKILL_CATEGORY_COLORS,
  SKILL_CATEGORY_ORDER,
  SKILL_CHECKBOXES,
  ALL_CHECKBOX_SKILLS,
  STATUS_COLORS,
  PROCESS_OPTIONS,
  JOB_TYPE_OPTIONS,
  POSITION_OPTIONS,
  REMOTE_OPTIONS,
  AREA_OPTIONS,
  EDUCATION_OPTIONS,
  INDUSTRY_OPTIONS,
  PROFICIENCY_OPTIONS,
} from "@/lib/constants";

export default function MyProfilePage() {
  const { user } = useAuth();
  const [engineer, setEngineer] = useState<EngineerDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // 編集モード
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<EngineerForm>({ ...EMPTY_FORM });
  const [saving, setSaving] = useState(false);

  // PW 変更
  const [newPassword, setNewPassword] = useState("");
  const [pwConfirm, setPwConfirm] = useState("");
  const [changingPw, setChangingPw] = useState(false);

  // スキルカテゴリ折りたたみ
  const [openCategories, setOpenCategories] = useState<Record<string, boolean>>({});

  const loadProfile = useCallback(async () => {
    if (!user?.engineer_id) {
      setLoading(false);
      return;
    }
    try {
      const data = await getEngineerDetail(user.engineer_id);
      setEngineer(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [user?.engineer_id]);

  useEffect(() => { loadProfile(); }, [loadProfile]);

  const startEditing = () => {
    if (!engineer) return;
    // エンジニアデータをフォームに変換
    const checkboxSkills = engineer.skills.filter((s) => ALL_CHECKBOX_SKILLS.includes(s));
    const otherSkills = engineer.skills.filter((s) => !ALL_CHECKBOX_SKILLS.includes(s));
    const areas = engineer.preferred_areas
      ? engineer.preferred_areas.split(",").map((s) => s.trim()).filter(Boolean)
      : [];
    const knownAreas = areas.filter((a) => AREA_OPTIONS.includes(a));
    const otherAreas = areas.filter((a) => !AREA_OPTIONS.includes(a));

    let proficiency: Record<string, string> = {};
    try {
      proficiency = JSON.parse(engineer.skill_proficiency || "{}");
    } catch { /* ignore */ }

    setForm({
      name: engineer.name,
      name_kana: engineer.name_kana || "",
      email: engineer.email || "",
      phone: engineer.phone || "",
      address: engineer.address || "",
      nearest_station: engineer.nearest_station || "",
      skills: checkboxSkills,
      skills_other: otherSkills.join("; "),
      experience_years: engineer.experience_years?.toString() || "",
      current_price: engineer.current_price?.toString() || "",
      desired_price_min: engineer.desired_price_min?.toString() || "",
      desired_price_max: engineer.desired_price_max?.toString() || "",
      status: engineer.status,
      preferred_areas: knownAreas,
      preferred_areas_other: otherAreas.join(", "),
      available_from: engineer.available_from || "",
      notes: engineer.notes || "",
      processes: engineer.processes ? engineer.processes.split(",").map((s) => s.trim()).filter(Boolean) : [],
      job_type_experience: engineer.job_type_experience ? engineer.job_type_experience.split(",").map((s) => s.trim()).filter(Boolean) : [],
      position_experience: engineer.position_experience ? engineer.position_experience.split(",").map((s) => s.trim()).filter(Boolean) : [],
      remote_preference: engineer.remote_preference || "",
      career_desired_job_type: engineer.career_desired_job_type ? engineer.career_desired_job_type.split(",").map((s) => s.trim()).filter(Boolean) : [],
      career_desired_skills: engineer.career_desired_skills || "",
      career_notes: engineer.career_notes || "",
      birth_date: engineer.birth_date || "",
      education: engineer.education || "",
      industry_experience: engineer.industry_experience ? engineer.industry_experience.split(",").map((s) => s.trim()).filter(Boolean) : [],
      skill_proficiency: proficiency,
      certifications: engineer.certifications || "",
    });
    setEditing(true);
    setError("");
    setSuccess("");
  };

  const handleSave = async () => {
    if (!engineer) return;
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      // スキル結合
      const allSkills = [...form.skills];
      if (form.skills_other.trim()) {
        form.skills_other.split(/[;；]/).forEach((s) => {
          const trimmed = s.trim();
          if (trimmed && !allSkills.includes(trimmed)) allSkills.push(trimmed);
        });
      }
      // エリア結合
      const allAreas = [...form.preferred_areas];
      if (form.preferred_areas_other.trim()) {
        form.preferred_areas_other.split(/[,，]/).forEach((a) => {
          const trimmed = a.trim();
          if (trimmed && !allAreas.includes(trimmed)) allAreas.push(trimmed);
        });
      }

      const payload: Record<string, unknown> = {
        name: form.name,
        name_kana: form.name_kana || null,
        email: form.email || null,
        phone: form.phone || null,
        address: form.address || null,
        nearest_station: form.nearest_station || null,
        skills: allSkills,
        processes: form.processes.join(","),
        job_type_experience: form.job_type_experience.join(","),
        position_experience: form.position_experience.join(","),
        remote_preference: form.remote_preference,
        preferred_areas: allAreas.join(","),
        available_from: form.available_from || null,
        notes: form.notes,
        career_desired_job_type: form.career_desired_job_type.join(","),
        career_desired_skills: form.career_desired_skills,
        career_notes: form.career_notes,
        birth_date: form.birth_date || null,
        education: form.education,
        industry_experience: form.industry_experience.join(","),
        skill_proficiency: JSON.stringify(form.skill_proficiency),
        certifications: form.certifications,
      };

      await updateEngineer(engineer.id, payload);
      setSuccess("プロフィールを更新しました");
      setEditing(false);
      await loadProfile();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  };

  const handleChangePw = async () => {
    setError("");
    setSuccess("");
    if (newPassword.length < 6) {
      setError("パスワードは6文字以上にしてください");
      return;
    }
    if (newPassword !== pwConfirm) {
      setError("パスワードが一致しません");
      return;
    }
    setChangingPw(true);
    try {
      await changeMyPassword(newPassword);
      setSuccess("パスワードを変更しました");
      setNewPassword("");
      setPwConfirm("");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setChangingPw(false);
    }
  };

  const toggleSkill = (skill: string) => {
    setForm((prev) => {
      const has = prev.skills.includes(skill);
      const skills = has ? prev.skills.filter((s) => s !== skill) : [...prev.skills, skill];
      const proficiency = { ...prev.skill_proficiency };
      if (has) delete proficiency[skill];
      return { ...prev, skills, skill_proficiency: proficiency };
    });
  };

  const toggleArrayField = (field: keyof EngineerForm, value: string) => {
    setForm((prev) => {
      const arr = prev[field] as string[];
      const has = arr.includes(value);
      return { ...prev, [field]: has ? arr.filter((v) => v !== value) : [...arr, value] };
    });
  };

  if (loading) return <p style={{ color: "var(--muted)" }}>読み込み中...</p>;

  if (!user?.engineer_id) {
    return (
      <div>
        <h1 className="text-2xl font-bold mb-4" style={{ color: "var(--foreground)" }}>
          マイプロフィール
        </h1>
        <p style={{ color: "var(--muted)" }}>
          エンジニア情報がまだ登録されていません。管理者にお問い合わせください。
        </p>
        {/* PW変更はエンジニア紐付けがなくても可能 */}
        <PasswordSection
          newPassword={newPassword}
          setNewPassword={setNewPassword}
          pwConfirm={pwConfirm}
          setPwConfirm={setPwConfirm}
          changingPw={changingPw}
          onSubmit={handleChangePw}
          error={error}
          success={success}
        />
      </div>
    );
  }

  if (error && !engineer) return <p className="text-red-500">{error}</p>;
  if (!engineer) return <p style={{ color: "var(--muted)" }}>データが見つかりません</p>;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold" style={{ color: "var(--foreground)" }}>
          マイプロフィール
        </h1>
        {!editing && (
          <button
            onClick={startEditing}
            className="px-4 py-2 rounded-lg text-sm text-white"
            style={{ background: "var(--primary)" }}
          >
            編集
          </button>
        )}
      </div>

      {error && <div className="mb-4 p-3 rounded-lg bg-red-50 text-red-700 text-sm">{error}</div>}
      {success && <div className="mb-4 p-3 rounded-lg bg-green-50 text-green-700 text-sm">{success}</div>}

      {editing ? (
        /* ===== 編集モード ===== */
        <div
          className="rounded-xl p-6 space-y-6"
          style={{ background: "var(--card-bg)", border: "1px solid var(--border)" }}
        >
          {/* 管理者設定項目（表示のみ） */}
          <Section title="管理者設定（変更は管理者にお問い合わせください）">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <ReadOnlyField label="ステータス" value={engineer.status} />
              <ReadOnlyField label="経験年数" value={engineer.experience_years ? `${engineer.experience_years}年` : "-"} />
            </div>
          </Section>

          {/* 基本情報 */}
          <Section title="基本情報">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="text-xs block mb-1" style={{ color: "var(--muted)" }}>名前</label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg text-sm"
                  style={{ background: "var(--background)", border: "1px solid var(--border)", color: "var(--foreground)" }}
                />
              </div>
              <div>
                <label className="text-xs block mb-1" style={{ color: "var(--muted)" }}>名前（カナ）</label>
                <input
                  type="text"
                  value={form.name_kana || ""}
                  onChange={(e) => setForm({ ...form, name_kana: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg text-sm"
                  style={{ background: "var(--background)", border: "1px solid var(--border)", color: "var(--foreground)" }}
                />
              </div>
              <div>
                <label className="text-xs block mb-1" style={{ color: "var(--muted)" }}>メールアドレス</label>
                <input
                  type="email"
                  value={form.email || ""}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg text-sm"
                  style={{ background: "var(--background)", border: "1px solid var(--border)", color: "var(--foreground)" }}
                />
              </div>
              <div>
                <label className="text-xs block mb-1" style={{ color: "var(--muted)" }}>電話番号</label>
                <input
                  type="tel"
                  value={form.phone || ""}
                  onChange={(e) => setForm({ ...form, phone: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg text-sm"
                  style={{ background: "var(--background)", border: "1px solid var(--border)", color: "var(--foreground)" }}
                />
              </div>
              <div>
                <label className="text-xs block mb-1" style={{ color: "var(--muted)" }}>住所</label>
                <input
                  type="text"
                  value={form.address || ""}
                  onChange={(e) => setForm({ ...form, address: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg text-sm"
                  style={{ background: "var(--background)", border: "1px solid var(--border)", color: "var(--foreground)" }}
                />
              </div>
              <div>
                <label className="text-xs block mb-1" style={{ color: "var(--muted)" }}>最寄駅</label>
                <input
                  type="text"
                  value={form.nearest_station || ""}
                  onChange={(e) => setForm({ ...form, nearest_station: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg text-sm"
                  style={{ background: "var(--background)", border: "1px solid var(--border)", color: "var(--foreground)" }}
                />
              </div>
              <div>
                <label className="text-xs block mb-1" style={{ color: "var(--muted)" }}>稼働可能日</label>
                <input
                  type="date"
                  value={form.available_from}
                  onChange={(e) => setForm({ ...form, available_from: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg text-sm"
                  style={{ background: "var(--background)", border: "1px solid var(--border)", color: "var(--foreground)" }}
                />
              </div>
              <div>
                <label className="text-xs block mb-1" style={{ color: "var(--muted)" }}>生年月日</label>
                <input
                  type="date"
                  value={form.birth_date}
                  onChange={(e) => setForm({ ...form, birth_date: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg text-sm"
                  style={{ background: "var(--background)", border: "1px solid var(--border)", color: "var(--foreground)" }}
                />
              </div>
              <div>
                <label className="text-xs block mb-1" style={{ color: "var(--muted)" }}>最終学歴</label>
                <select
                  value={form.education}
                  onChange={(e) => setForm({ ...form, education: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg text-sm"
                  style={{ background: "var(--background)", border: "1px solid var(--border)", color: "var(--foreground)" }}
                >
                  <option value="">未選択</option>
                  {EDUCATION_OPTIONS.map((o) => (
                    <option key={o} value={o}>{o}</option>
                  ))}
                </select>
              </div>
            </div>
          </Section>

          {/* スキル */}
          <Section title="スキル">
            {SKILL_CATEGORY_ORDER.filter((cat) => cat !== "その他").map((cat) => (
              <div key={cat} className="mb-3">
                <button
                  type="button"
                  onClick={() => setOpenCategories((p) => ({ ...p, [cat]: !p[cat] }))}
                  className="text-sm font-medium mb-1 flex items-center gap-1"
                  style={{ color: "var(--foreground)" }}
                >
                  <span className={`px-1.5 py-0.5 rounded text-xs ${SKILL_CATEGORY_COLORS[cat]}`}>{cat}</span>
                  <span className="text-xs" style={{ color: "var(--muted)" }}>
                    {openCategories[cat] ? "▼" : "▶"}
                  </span>
                </button>
                {(openCategories[cat] ?? true) && (
                  <div className="flex flex-wrap gap-2 mt-1">
                    {SKILL_CHECKBOXES[cat].map((skill) => {
                      const checked = form.skills.includes(skill);
                      return (
                        <label key={skill} className="flex items-center gap-1 text-xs" style={{ color: "var(--foreground)" }}>
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={() => toggleSkill(skill)}
                            className="rounded"
                          />
                          {skill}
                          {checked && (
                            <select
                              value={form.skill_proficiency[skill] || ""}
                              onChange={(e) =>
                                setForm((p) => ({
                                  ...p,
                                  skill_proficiency: { ...p.skill_proficiency, [skill]: e.target.value },
                                }))
                              }
                              className="ml-1 px-1 py-0.5 rounded text-xs"
                              style={{ background: "var(--background)", border: "1px solid var(--border)", color: "var(--foreground)" }}
                            >
                              <option value="">-</option>
                              {PROFICIENCY_OPTIONS.map((l) => (
                                <option key={l} value={l}>{l}</option>
                              ))}
                            </select>
                          )}
                        </label>
                      );
                    })}
                  </div>
                )}
              </div>
            ))}
            <div>
              <label className="text-xs block mb-1" style={{ color: "var(--muted)" }}>
                その他スキル（セミコロン区切り）
              </label>
              <input
                type="text"
                value={form.skills_other}
                onChange={(e) => setForm({ ...form, skills_other: e.target.value })}
                className="w-full px-3 py-2 rounded-lg text-sm"
                placeholder="例: SAP; Salesforce"
                style={{ background: "var(--background)", border: "1px solid var(--border)", color: "var(--foreground)" }}
              />
            </div>
          </Section>

          {/* 経験 */}
          <Section title="経験">
            <CheckboxGroup
              label="対応工程"
              options={PROCESS_OPTIONS}
              selected={form.processes}
              onChange={(v) => toggleArrayField("processes", v)}
            />
            <CheckboxGroup
              label="職種経験"
              options={JOB_TYPE_OPTIONS}
              selected={form.job_type_experience}
              onChange={(v) => toggleArrayField("job_type_experience", v)}
            />
            <CheckboxGroup
              label="ポジション経験"
              options={POSITION_OPTIONS}
              selected={form.position_experience}
              onChange={(v) => toggleArrayField("position_experience", v)}
            />
            <CheckboxGroup
              label="業種経験"
              options={INDUSTRY_OPTIONS}
              selected={form.industry_experience}
              onChange={(v) => toggleArrayField("industry_experience", v)}
            />
            <div>
              <label className="text-xs block mb-1" style={{ color: "var(--muted)" }}>
                資格・認定（カンマ区切り）
              </label>
              <input
                type="text"
                value={form.certifications}
                onChange={(e) => setForm({ ...form, certifications: e.target.value })}
                className="w-full px-3 py-2 rounded-lg text-sm"
                placeholder="例: AWS SAA, 基本情報技術者"
                style={{ background: "var(--background)", border: "1px solid var(--border)", color: "var(--foreground)" }}
              />
            </div>
          </Section>

          {/* 勤務条件 */}
          <Section title="勤務条件">
            <div className="mb-3">
              <label className="text-xs block mb-1" style={{ color: "var(--muted)" }}>リモート希望</label>
              <div className="flex gap-3">
                {REMOTE_OPTIONS.map((opt) => (
                  <label key={opt} className="flex items-center gap-1 text-xs" style={{ color: "var(--foreground)" }}>
                    <input
                      type="radio"
                      name="remote"
                      value={opt}
                      checked={form.remote_preference === opt}
                      onChange={(e) => setForm({ ...form, remote_preference: e.target.value })}
                    />
                    {opt}
                  </label>
                ))}
                <label className="flex items-center gap-1 text-xs" style={{ color: "var(--foreground)" }}>
                  <input
                    type="radio"
                    name="remote"
                    value=""
                    checked={!form.remote_preference}
                    onChange={() => setForm({ ...form, remote_preference: "" })}
                  />
                  未選択
                </label>
              </div>
            </div>
            <CheckboxGroup
              label="希望勤務地"
              options={AREA_OPTIONS}
              selected={form.preferred_areas}
              onChange={(v) => toggleArrayField("preferred_areas", v)}
            />
            <div>
              <label className="text-xs block mb-1" style={{ color: "var(--muted)" }}>
                その他勤務地（カンマ区切り）
              </label>
              <input
                type="text"
                value={form.preferred_areas_other}
                onChange={(e) => setForm({ ...form, preferred_areas_other: e.target.value })}
                className="w-full px-3 py-2 rounded-lg text-sm"
                style={{ background: "var(--background)", border: "1px solid var(--border)", color: "var(--foreground)" }}
              />
            </div>
          </Section>

          {/* キャリア希望 */}
          <Section title="今後のキャリア">
            <CheckboxGroup
              label="希望職種"
              options={JOB_TYPE_OPTIONS}
              selected={form.career_desired_job_type}
              onChange={(v) => toggleArrayField("career_desired_job_type", v)}
            />
            <div>
              <label className="text-xs block mb-1" style={{ color: "var(--muted)" }}>習得したいスキル</label>
              <input
                type="text"
                value={form.career_desired_skills}
                onChange={(e) => setForm({ ...form, career_desired_skills: e.target.value })}
                className="w-full px-3 py-2 rounded-lg text-sm"
                style={{ background: "var(--background)", border: "1px solid var(--border)", color: "var(--foreground)" }}
              />
            </div>
            <div>
              <label className="text-xs block mb-1" style={{ color: "var(--muted)" }}>キャリアメモ</label>
              <textarea
                value={form.career_notes}
                onChange={(e) => setForm({ ...form, career_notes: e.target.value })}
                rows={3}
                className="w-full px-3 py-2 rounded-lg text-sm"
                style={{ background: "var(--background)", border: "1px solid var(--border)", color: "var(--foreground)" }}
              />
            </div>
          </Section>

          {/* 備考 */}
          <Section title="備考">
            <textarea
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
              rows={3}
              className="w-full px-3 py-2 rounded-lg text-sm"
              style={{ background: "var(--background)", border: "1px solid var(--border)", color: "var(--foreground)" }}
            />
          </Section>

          {/* 保存/キャンセル */}
          <div className="flex gap-3">
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-6 py-2 rounded-lg text-sm text-white disabled:opacity-50"
              style={{ background: "var(--primary)" }}
            >
              {saving ? "保存中..." : "保存"}
            </button>
            <button
              onClick={() => { setEditing(false); setError(""); setSuccess(""); }}
              className="px-6 py-2 rounded-lg text-sm"
              style={{ background: "var(--background)", border: "1px solid var(--border)", color: "var(--foreground)" }}
            >
              キャンセル
            </button>
          </div>
        </div>
      ) : (
        /* ===== 閲覧モード ===== */
        <div
          className="rounded-xl p-6 space-y-6"
          style={{ background: "var(--card-bg)", border: "1px solid var(--border)" }}
        >
          {/* 基本情報 */}
          <Section title="基本情報">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <InfoField label="名前" value={engineer.name} />
              <InfoField label="名前（カナ）" value={engineer.name_kana} />
              <InfoField label="メール" value={engineer.email} />
              <InfoField label="電話番号" value={engineer.phone} />
              <InfoField label="住所" value={engineer.address} />
              <InfoField label="最寄駅" value={engineer.nearest_station} />
              <InfoField label="ステータス">
                <span className={`px-2 py-0.5 rounded text-xs ${STATUS_COLORS[engineer.status] || ""}`}>
                  {engineer.status}
                </span>
              </InfoField>
              <InfoField label="経験年数" value={engineer.experience_years ? `${engineer.experience_years}年` : ""} />
              <InfoField label="稼働可能日" value={engineer.available_from} />
              <InfoField label="生年月日" value={engineer.birth_date} />
              <InfoField label="最終学歴" value={engineer.education} />
              <InfoField label="リモート希望" value={engineer.remote_preference} />
            </div>
          </Section>

          {/* スキル */}
          {engineer.skills.length > 0 && (
            <Section title="スキル">
              {(() => {
                let proficiency: Record<string, string> = {};
                try { proficiency = JSON.parse(engineer.skill_proficiency || "{}"); } catch { /* ignore */ }
                const categorized = engineer.categorized_skills || {};
                return SKILL_CATEGORY_ORDER.map((cat) => {
                  const items = categorized[cat];
                  if (!items || items.length === 0) return null;
                  return (
                    <div key={cat} className="mb-2">
                      <span className={`px-1.5 py-0.5 rounded text-xs ${SKILL_CATEGORY_COLORS[cat]}`}>{cat}</span>
                      <div className="flex flex-wrap gap-1.5 mt-1">
                        {items.map((s) => (
                          <span
                            key={s}
                            className="px-2 py-0.5 rounded text-xs"
                            style={{ background: "var(--primary)", color: "white" }}
                          >
                            {s}{proficiency[s] ? ` (${proficiency[s]})` : ""}
                          </span>
                        ))}
                      </div>
                    </div>
                  );
                });
              })()}
            </Section>
          )}

          {/* 経験 */}
          <Section title="経験">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <InfoField label="対応工程" value={engineer.processes} />
              <InfoField label="職種経験" value={engineer.job_type_experience} />
              <InfoField label="ポジション経験" value={engineer.position_experience} />
              <InfoField label="業種経験" value={engineer.industry_experience} />
              <InfoField label="資格・認定" value={engineer.certifications} />
            </div>
          </Section>

          {/* 勤務条件 */}
          <Section title="勤務条件">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <InfoField label="希望エリア" value={engineer.preferred_areas} />
              <InfoField label="リモート希望" value={engineer.remote_preference} />
            </div>
          </Section>

          {/* キャリア希望 */}
          <Section title="今後のキャリア">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <InfoField label="希望職種" value={engineer.career_desired_job_type} />
              <InfoField label="習得したいスキル" value={engineer.career_desired_skills} />
            </div>
            {engineer.career_notes && (
              <div className="mt-2">
                <InfoField label="キャリアメモ" value={engineer.career_notes} />
              </div>
            )}
          </Section>

          {/* 備考 */}
          {engineer.notes && (
            <Section title="備考">
              <p className="text-sm whitespace-pre-wrap" style={{ color: "var(--foreground)" }}>
                {engineer.notes}
              </p>
            </Section>
          )}

          {/* 担当案件 */}
          {engineer.assignments.length > 0 && (
            <Section title="担当案件">
              <div className="space-y-2">
                {engineer.assignments.map((a) => (
                  <div
                    key={a.id}
                    className="p-3 rounded-lg text-sm"
                    style={{ background: "var(--background)", border: "1px solid var(--border)" }}
                  >
                    <p style={{ color: "var(--foreground)" }}>
                      {a.company_name} - {a.project_name}
                    </p>
                    <p className="text-xs" style={{ color: "var(--muted)" }}>
                      {a.start_date} ~ {a.end_date || "現在"} | {a.status}
                      {a.unit_price ? ` | ${a.unit_price}万円` : ""}
                    </p>
                  </div>
                ))}
              </div>
            </Section>
          )}
        </div>
      )}

      {/* PW 変更セクション */}
      <PasswordSection
        newPassword={newPassword}
        setNewPassword={setNewPassword}
        pwConfirm={pwConfirm}
        setPwConfirm={setPwConfirm}
        changingPw={changingPw}
        onSubmit={handleChangePw}
        error=""
        success=""
      />
    </div>
  );
}

/* --- 共通コンポーネント --- */

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h2 className="text-sm font-semibold mb-3" style={{ color: "var(--foreground)" }}>
        {title}
      </h2>
      {children}
    </div>
  );
}

function InfoField({
  label,
  value,
  children,
}: {
  label: string;
  value?: string | number | null;
  children?: React.ReactNode;
}) {
  return (
    <div>
      <p className="text-xs" style={{ color: "var(--muted)" }}>{label}</p>
      {children || (
        <p className="text-sm" style={{ color: "var(--foreground)" }}>{value || "-"}</p>
      )}
    </div>
  );
}

function ReadOnlyField({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <label className="text-xs block mb-1" style={{ color: "var(--muted)" }}>{label}</label>
      <p
        className="px-3 py-2 rounded-lg text-sm"
        style={{ background: "var(--background)", border: "1px solid var(--border)", color: "var(--muted)" }}
      >
        {value || "-"}
      </p>
    </div>
  );
}

function CheckboxGroup({
  label,
  options,
  selected,
  onChange,
}: {
  label: string;
  options: string[];
  selected: string[];
  onChange: (value: string) => void;
}) {
  return (
    <div className="mb-3">
      <label className="text-xs block mb-1" style={{ color: "var(--muted)" }}>{label}</label>
      <div className="flex flex-wrap gap-2">
        {options.map((opt) => (
          <label key={opt} className="flex items-center gap-1 text-xs" style={{ color: "var(--foreground)" }}>
            <input
              type="checkbox"
              checked={selected.includes(opt)}
              onChange={() => onChange(opt)}
              className="rounded"
            />
            {opt}
          </label>
        ))}
      </div>
    </div>
  );
}

function PasswordSection({
  newPassword,
  setNewPassword,
  pwConfirm,
  setPwConfirm,
  changingPw,
  onSubmit,
  error,
  success,
}: {
  newPassword: string;
  setNewPassword: (v: string) => void;
  pwConfirm: string;
  setPwConfirm: (v: string) => void;
  changingPw: boolean;
  onSubmit: () => void;
  error: string;
  success: string;
}) {
  return (
    <div
      className="rounded-xl p-6 mt-6 space-y-3"
      style={{ background: "var(--card-bg)", border: "1px solid var(--border)" }}
    >
      <h2 className="text-sm font-semibold" style={{ color: "var(--foreground)" }}>
        パスワード変更
      </h2>
      {error && <p className="text-red-500 text-sm">{error}</p>}
      {success && <p className="text-green-600 text-sm">{success}</p>}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-w-lg">
        <div>
          <label className="text-xs block mb-1" style={{ color: "var(--muted)" }}>新しいパスワード</label>
          <input
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            className="w-full px-3 py-2 rounded-lg text-sm"
            style={{ background: "var(--background)", border: "1px solid var(--border)", color: "var(--foreground)" }}
          />
        </div>
        <div>
          <label className="text-xs block mb-1" style={{ color: "var(--muted)" }}>パスワード確認</label>
          <input
            type="password"
            value={pwConfirm}
            onChange={(e) => setPwConfirm(e.target.value)}
            className="w-full px-3 py-2 rounded-lg text-sm"
            style={{ background: "var(--background)", border: "1px solid var(--border)", color: "var(--foreground)" }}
          />
        </div>
      </div>
      <button
        onClick={onSubmit}
        disabled={changingPw || !newPassword}
        className="px-4 py-2 rounded-lg text-sm text-white disabled:opacity-50"
        style={{ background: "var(--primary)" }}
      >
        {changingPw ? "変更中..." : "パスワードを変更"}
      </button>
    </div>
  );
}
