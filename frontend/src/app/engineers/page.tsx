"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  getEngineerStats,
  getEngineerFilters,
  getEngineers,
  getEngineerDetail,
  createEngineer,
  updateEngineer,
  deleteEngineer,
  getEngineerExportURL,
  importEngineersCsv,
  createAssignment,
  deleteAssignment,
} from "@/lib/api";
import type {
  EngineerStats,
  EngineerFilters,
  Engineer,
  EngineerDetail,
  EngineerAssignment,
  EngineerForm,
  CsvImportResult,
  CategorizedSkills,
} from "@/types";

const EMPTY_FORM: EngineerForm = {
  name: "",
  skills: [],
  skills_other: "",
  experience_years: "",
  current_price: "",
  desired_price_min: "",
  desired_price_max: "",
  status: "待機中",
  preferred_areas: [],
  preferred_areas_other: "",
  available_from: "",
  notes: "",
  processes: [],
  job_type_experience: [],
  position_experience: [],
  remote_preference: "",
  career_desired_job_type: [],
  career_desired_skills: "",
  career_notes: "",
};

const SKILL_CATEGORY_COLORS: Record<string, string> = {
  "言語": "bg-blue-100 text-blue-700",
  "FW": "bg-purple-100 text-purple-700",
  "インフラ": "bg-orange-100 text-orange-700",
  "DB": "bg-green-100 text-green-700",
  "その他": "bg-gray-100 text-gray-600",
};

const SKILL_CATEGORY_ORDER = ["言語", "FW", "インフラ", "DB", "その他"];

const SKILL_CHECKBOXES: Record<string, string[]> = {
  "言語": ["Java", "Python", "TypeScript", "JavaScript", "Go", "C#", "Ruby", "PHP", "Swift", "Kotlin", "C", "C++", "Rust", "Scala", "Perl", "R", "COBOL", "VB.NET", "Dart", "Shell"],
  "FW": ["React", "Vue.js", "Angular", "Next.js", "Spring Boot", "Django", "Flask", "Laravel", "Ruby on Rails", ".NET", "Express.js", "NestJS", "Flutter", "Unity"],
  "インフラ": ["AWS", "Azure", "GCP", "Docker", "Kubernetes", "Terraform", "Linux", "Jenkins", "Ansible"],
  "DB": ["PostgreSQL", "MySQL", "Oracle", "SQL Server", "MongoDB", "Redis", "DynamoDB", "Elasticsearch"],
};

const ALL_CHECKBOX_SKILLS = Object.values(SKILL_CHECKBOXES).flat();

const STATUS_COLORS: Record<string, string> = {
  "待機中": "bg-green-100 text-green-800",
  "稼働中": "bg-blue-100 text-blue-800",
  "面談中": "bg-yellow-100 text-yellow-800",
  "休止中": "bg-gray-100 text-gray-500",
};

export default function EngineersPage() {
  const router = useRouter();
  // データ
  const [stats, setStats] = useState<EngineerStats | null>(null);
  const [filters, setFilters] = useState<EngineerFilters | null>(null);
  const [engineers, setEngineers] = useState<Engineer[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // フィルター状態
  const [keyword, setKeyword] = useState("");
  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);
  const [selectedStatuses, setSelectedStatuses] = useState<string[]>([]);
  const [selectedAreas, setSelectedAreas] = useState<string[]>([]);
  const [priceMin, setPriceMin] = useState("");
  const [priceMax, setPriceMax] = useState("");
  const [selectedJobTypes, setSelectedJobTypes] = useState<string[]>([]);
  const [selectedPositions, setSelectedPositions] = useState<string[]>([]);
  const [selectedRemote, setSelectedRemote] = useState<string[]>([]);

  // 展開・編集
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<EngineerDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState<EngineerForm>({ ...EMPTY_FORM });
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);

  // CSVインポート
  const [showImport, setShowImport] = useState(false);
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [importResult, setImportResult] = useState<CsvImportResult | null>(null);
  const [importing, setImporting] = useState(false);

  // アサイン追加
  const [showAssignForm, setShowAssignForm] = useState(false);
  const [assignForm, setAssignForm] = useState({
    company_name: "",
    project_name: "",
    start_date: "",
    end_date: "",
    unit_price: "",
    status: "稼働中",
    notes: "",
  });

  // 初期読み込み
  useEffect(() => {
    getEngineerStats().then(setStats).catch(() => {});
    getEngineerFilters().then(setFilters).catch(() => {});
  }, []);

  const buildParams = useCallback(() => {
    const params: Record<string, string> = {};
    if (keyword) params.keyword = keyword;
    if (selectedSkills.length) params.skills = selectedSkills.join(",");
    if (selectedStatuses.length) params.statuses = selectedStatuses.join(",");
    if (selectedAreas.length) params.areas = selectedAreas.join(",");
    if (priceMin) params.price_min = priceMin;
    if (priceMax) params.price_max = priceMax;
    if (selectedJobTypes.length) params.job_types = selectedJobTypes.join(",");
    if (selectedPositions.length) params.positions = selectedPositions.join(",");
    if (selectedRemote.length) params.remote = selectedRemote.join(",");
    return params;
  }, [keyword, selectedSkills, selectedStatuses, selectedAreas, priceMin, priceMax, selectedJobTypes, selectedPositions, selectedRemote]);

  const doSearch = useCallback(() => {
    setLoading(true);
    setError("");
    getEngineers(buildParams())
      .then((res) => {
        setEngineers(res.engineers);
        setTotal(res.total);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [buildParams]);

  useEffect(() => {
    doSearch();
  }, [doSearch]);

  const reload = () => {
    doSearch();
    getEngineerStats().then(setStats).catch(() => {});
    getEngineerFilters().then(setFilters).catch(() => {});
  };

  // 展開時に詳細を取得
  const handleExpand = async (id: number) => {
    if (expandedId === id) {
      setExpandedId(null);
      setDetail(null);
      setDetailLoading(false);
      return;
    }
    setExpandedId(id);
    setDetail(null);
    setDetailLoading(true);
    try {
      const d = await getEngineerDetail(id);
      setDetail(d);
    } catch {
      setDetail(null);
    } finally {
      setDetailLoading(false);
    }
  };

  // フィルター操作
  const toggleMulti = (
    arr: string[],
    setter: React.Dispatch<React.SetStateAction<string[]>>,
    val: string
  ) => {
    setter(arr.includes(val) ? arr.filter((v) => v !== val) : [...arr, val]);
  };

  const clearFilters = () => {
    setKeyword("");
    setSelectedSkills([]);
    setSelectedStatuses([]);
    setSelectedAreas([]);
    setPriceMin("");
    setPriceMax("");
    setSelectedJobTypes([]);
    setSelectedPositions([]);
    setSelectedRemote([]);
  };

  // フォーム操作
  const openNewForm = () => {
    setEditId(null);
    setForm({ ...EMPTY_FORM });
    setFormError("");
    setShowForm(true);
  };

  const openEditForm = (eng: Engineer) => {
    setEditId(eng.id);
    const knownSkills = eng.skills.filter(s => ALL_CHECKBOX_SKILLS.includes(s));
    const otherSkills = eng.skills.filter(s => !ALL_CHECKBOX_SKILLS.includes(s));
    const areaOptions = filters?.area_options ?? [];
    const knownAreas = eng.preferred_areas
      ? eng.preferred_areas.split(",").map(s => s.trim()).filter(a => areaOptions.includes(a))
      : [];
    const otherAreas = eng.preferred_areas
      ? eng.preferred_areas.split(",").map(s => s.trim()).filter(a => a && !areaOptions.includes(a))
      : [];
    setForm({
      name: eng.name,
      skills: knownSkills,
      skills_other: otherSkills.join("; "),
      experience_years: eng.experience_years?.toString() ?? "",
      current_price: eng.current_price?.toString() ?? "",
      desired_price_min: eng.desired_price_min?.toString() ?? "",
      desired_price_max: eng.desired_price_max?.toString() ?? "",
      status: eng.status,
      preferred_areas: knownAreas,
      preferred_areas_other: otherAreas.join(", "),
      available_from: eng.available_from,
      notes: eng.notes,
      processes: eng.processes ? eng.processes.split(",").map(s => s.trim()).filter(Boolean) : [],
      job_type_experience: eng.job_type_experience ? eng.job_type_experience.split(",").map(s => s.trim()).filter(Boolean) : [],
      position_experience: eng.position_experience ? eng.position_experience.split(",").map(s => s.trim()).filter(Boolean) : [],
      remote_preference: eng.remote_preference || "",
      career_desired_job_type: eng.career_desired_job_type ? eng.career_desired_job_type.split(",").map(s => s.trim()).filter(Boolean) : [],
      career_desired_skills: eng.career_desired_skills || "",
      career_notes: eng.career_notes || "",
    });
    setFormError("");
    setShowForm(true);
  };

  const handleSave = async () => {
    if (!form.name.trim()) {
      setFormError("名前は必須です");
      return;
    }
    setSaving(true);
    setFormError("");

    const otherSkills = form.skills_other
      .split(/[;；]/)
      .map((s) => s.trim())
      .filter(Boolean);
    const allSkills = [...form.skills, ...otherSkills];
    const safeInt = (v: string) => {
      const n = parseInt(v);
      return isNaN(n) ? null : n;
    };
    const otherAreasList = form.preferred_areas_other
      .split(/[,、]/)
      .map((s) => s.trim())
      .filter(Boolean);
    const allAreas = [...form.preferred_areas, ...otherAreasList];

    const payload = {
      name: form.name.trim(),
      skills: allSkills,
      experience_years: safeInt(form.experience_years),
      current_price: safeInt(form.current_price),
      desired_price_min: safeInt(form.desired_price_min),
      desired_price_max: safeInt(form.desired_price_max),
      status: form.status,
      preferred_areas: allAreas.join(","),
      available_from: form.available_from,
      notes: form.notes,
      processes: form.processes.join(","),
      job_type_experience: form.job_type_experience.join(","),
      position_experience: form.position_experience.join(","),
      remote_preference: form.remote_preference,
      career_desired_job_type: form.career_desired_job_type.join(","),
      career_desired_skills: form.career_desired_skills,
      career_notes: form.career_notes,
    };

    try {
      if (editId) {
        await updateEngineer(editId, payload);
      } else {
        await createEngineer(payload);
      }
      setShowForm(false);
      reload();
    } catch (e) {
      setFormError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number, name: string) => {
    if (!confirm(`${name} を削除しますか？`)) return;
    try {
      await deleteEngineer(id);
      setExpandedId(null);
      reload();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  // CSVインポート
  const handleImport = async () => {
    if (!csvFile) return;
    setImporting(true);
    setImportResult(null);
    try {
      const result = await importEngineersCsv(csvFile);
      setImportResult(result);
      if (result.imported > 0) reload();
    } catch (e) {
      setImportResult({ imported: 0, errors: [(e as Error).message] });
    } finally {
      setImporting(false);
    }
  };

  // アサイン追加
  const handleAddAssignment = async () => {
    if (!expandedId) return;
    try {
      const safeInt = (v: string) => {
        const n = parseInt(v);
        return isNaN(n) ? null : n;
      };
      await createAssignment(expandedId, {
        ...assignForm,
        unit_price: safeInt(assignForm.unit_price),
      });
      const d = await getEngineerDetail(expandedId);
      setDetail(d);
      setShowAssignForm(false);
      setAssignForm({
        company_name: "",
        project_name: "",
        start_date: "",
        end_date: "",
        unit_price: "",
        status: "稼働中",
        notes: "",
      });
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const handleDeleteAssignment = async (assignId: number) => {
    if (!confirm("このアサイン履歴を削除しますか？")) return;
    try {
      await deleteAssignment(assignId);
      if (expandedId) {
        const d = await getEngineerDetail(expandedId);
        setDetail(d);
      }
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <div>
      {/* KPIバー */}
      {stats && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          {[
            { label: "総数", value: stats.total, color: "var(--primary)" },
            { label: "待機中", value: stats.waiting, color: "#22c55e" },
            { label: "稼働中", value: stats.active, color: "#3b82f6" },
            { label: "面談中", value: stats.interview, color: "#eab308" },
          ].map((kpi) => (
            <div
              key={kpi.label}
              className="rounded-xl p-4 shadow-sm border"
              style={{ background: "var(--card-bg)", borderColor: "var(--border)" }}
            >
              <p className="text-xs text-slate-500">{kpi.label}</p>
              <p className="text-2xl font-bold" style={{ color: kpi.color }}>
                {kpi.value}
              </p>
            </div>
          ))}
        </div>
      )}

      <div className="flex gap-6 h-[calc(100vh-13rem)]">
        {/* サイドバーフィルター */}
        <div
          className="w-64 shrink-0 rounded-xl p-4 shadow-sm border overflow-y-auto"
          style={{ background: "var(--card-bg)", borderColor: "var(--border)" }}
        >
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-bold">検索フィルタ</h2>
            <button onClick={clearFilters} className="text-xs text-blue-600 hover:underline">
              クリア
            </button>
          </div>

          {/* キーワード */}
          <label className="block text-xs text-slate-500 mb-1">名前・備考</label>
          <input
            type="text"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            placeholder="名前で検索"
            className="w-full mb-3 px-2 py-1.5 border rounded text-sm"
            style={{ borderColor: "var(--border)" }}
          />

          {/* ステータス */}
          <label className="block text-xs text-slate-500 mb-1">ステータス</label>
          <div className="mb-3 space-y-1">
            {(filters?.statuses ?? []).map((s) => (
              <label key={s} className="flex items-center gap-2 text-xs cursor-pointer">
                <input
                  type="checkbox"
                  checked={selectedStatuses.includes(s)}
                  onChange={() => toggleMulti(selectedStatuses, setSelectedStatuses, s)}
                />
                {s}
              </label>
            ))}
          </div>

          {/* スキル */}
          <label className="block text-xs text-slate-500 mb-1">スキル</label>
          <div className="max-h-32 overflow-y-auto mb-3 space-y-1">
            {(filters?.skills ?? []).map((s) => (
              <label key={s} className="flex items-center gap-2 text-xs cursor-pointer">
                <input
                  type="checkbox"
                  checked={selectedSkills.includes(s)}
                  onChange={() => toggleMulti(selectedSkills, setSelectedSkills, s)}
                />
                {s}
              </label>
            ))}
          </div>

          {/* エリア */}
          <label className="block text-xs text-slate-500 mb-1">希望エリア</label>
          <div className="max-h-32 overflow-y-auto mb-3 space-y-1">
            {(filters?.areas ?? []).map((a) => (
              <label key={a} className="flex items-center gap-2 text-xs cursor-pointer">
                <input
                  type="checkbox"
                  checked={selectedAreas.includes(a)}
                  onChange={() => toggleMulti(selectedAreas, setSelectedAreas, a)}
                />
                {a}
              </label>
            ))}
          </div>

          {/* 職種経験 */}
          {filters?.job_type_options && filters.job_type_options.length > 0 && (
            <>
              <label className="block text-xs text-slate-500 mb-1">職種経験</label>
              <div className="max-h-28 overflow-y-auto mb-3 space-y-1">
                {filters.job_type_options.map((jt) => (
                  <label key={jt} className="flex items-center gap-2 text-xs cursor-pointer">
                    <input type="checkbox" checked={selectedJobTypes.includes(jt)} onChange={() => toggleMulti(selectedJobTypes, setSelectedJobTypes, jt)} />
                    {jt}
                  </label>
                ))}
              </div>
            </>
          )}

          {/* ポジション */}
          {filters?.position_options && filters.position_options.length > 0 && (
            <>
              <label className="block text-xs text-slate-500 mb-1">ポジション</label>
              <div className="max-h-28 overflow-y-auto mb-3 space-y-1">
                {filters.position_options.map((pos) => (
                  <label key={pos} className="flex items-center gap-2 text-xs cursor-pointer">
                    <input type="checkbox" checked={selectedPositions.includes(pos)} onChange={() => toggleMulti(selectedPositions, setSelectedPositions, pos)} />
                    {pos}
                  </label>
                ))}
              </div>
            </>
          )}

          {/* リモート */}
          {filters?.remote_options && filters.remote_options.length > 0 && (
            <>
              <label className="block text-xs text-slate-500 mb-1">リモート希望</label>
              <div className="mb-3 space-y-1">
                {filters.remote_options.map((rem) => (
                  <label key={rem} className="flex items-center gap-2 text-xs cursor-pointer">
                    <input type="checkbox" checked={selectedRemote.includes(rem)} onChange={() => toggleMulti(selectedRemote, setSelectedRemote, rem)} />
                    {rem}
                  </label>
                ))}
              </div>
            </>
          )}

          {/* 単価範囲 */}
          <label className="block text-xs text-slate-500 mb-1">単価範囲（万円）</label>
          <div className="flex gap-2 mb-3">
            <input
              type="number"
              value={priceMin}
              onChange={(e) => setPriceMin(e.target.value)}
              placeholder="下限"
              className="w-1/2 px-2 py-1.5 border rounded text-sm"
              style={{ borderColor: "var(--border)" }}
            />
            <input
              type="number"
              value={priceMax}
              onChange={(e) => setPriceMax(e.target.value)}
              placeholder="上限"
              className="w-1/2 px-2 py-1.5 border rounded text-sm"
              style={{ borderColor: "var(--border)" }}
            />
          </div>
        </div>

        {/* メインコンテンツ */}
        <div className="flex-1 min-w-0 overflow-y-auto">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-xl font-bold">エンジニア管理</h1>
            <div className="flex items-center gap-2">
              <span className="text-sm text-slate-500">{total}名</span>
              <button
                onClick={openNewForm}
                className="px-3 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors"
              >
                新規登録
              </button>
              <button
                onClick={() => {
                  setShowImport(!showImport);
                  setImportResult(null);
                  setCsvFile(null);
                }}
                className="px-3 py-1.5 bg-orange-500 text-white text-sm rounded-lg hover:bg-orange-600 transition-colors"
              >
                CSVインポート
              </button>
              <a
                href={getEngineerExportURL(buildParams())}
                className="px-3 py-1.5 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 transition-colors"
              >
                CSV出力
              </a>
            </div>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              {error}
            </div>
          )}

          {/* CSVインポートUI */}
          {showImport && (
            <div
              className="mb-4 p-4 rounded-xl border"
              style={{ background: "var(--card-bg)", borderColor: "var(--border)" }}
            >
              <h3 className="text-sm font-bold mb-2">CSVインポート</h3>
              <p className="text-xs text-slate-500 mb-2">
                CSV形式: 名前, ステータス, スキル(セミコロン区切り), 経験年数,
                現在単価(万円), 希望単価下限(万円), 希望単価上限(万円),
                希望エリア, 稼働可能日, 備考
              </p>
              <p className="text-xs text-slate-500 mb-3">
                UTF-8またはShift_JIS対応。CSV出力でダウンロードしたファイルをテンプレートとして使えます。
              </p>
              <div className="flex items-center gap-3">
                <input
                  type="file"
                  accept=".csv"
                  onChange={(e) => setCsvFile(e.target.files?.[0] ?? null)}
                  className="text-sm"
                />
                <button
                  onClick={handleImport}
                  disabled={!csvFile || importing}
                  className="px-3 py-1.5 bg-orange-500 text-white text-sm rounded-lg hover:bg-orange-600 disabled:opacity-50 transition-colors"
                >
                  {importing ? "処理中..." : "インポート実行"}
                </button>
              </div>
              {importResult && (
                <div className="mt-3 text-sm">
                  <p className="text-green-700">
                    {importResult.imported}件インポートしました
                  </p>
                  {importResult.errors.length > 0 && (
                    <div className="mt-1 text-red-600">
                      {importResult.errors.map((e, i) => (
                        <p key={i}>{e}</p>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* 登録/編集フォーム */}
          {showForm && (
            <div
              className="mb-4 p-4 rounded-xl border"
              style={{ background: "var(--card-bg)", borderColor: "var(--border)" }}
            >
              <h3 className="text-sm font-bold mb-3">
                {editId ? "エンジニア編集" : "エンジニア新規登録"}
              </h3>
              {formError && (
                <p className="text-red-600 text-sm mb-2">{formError}</p>
              )}

              {/* セクション1: 基本情報 */}
              <div className="mb-4">
                <h4 className="text-xs font-bold text-slate-600 mb-2 border-b pb-1" style={{ borderColor: "var(--border)" }}>基本情報</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs text-slate-500 mb-1">名前 *</label>
                    <input type="text" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="w-full px-2 py-1.5 border rounded text-sm" style={{ borderColor: "var(--border)" }} />
                  </div>
                  <div>
                    <label className="block text-xs text-slate-500 mb-1">ステータス</label>
                    <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })} className="w-full px-2 py-1.5 border rounded text-sm" style={{ borderColor: "var(--border)" }}>
                      <option value="待機中">待機中</option>
                      <option value="稼働中">稼働中</option>
                      <option value="面談中">面談中</option>
                      <option value="休止中">休止中</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs text-slate-500 mb-1">経験年数</label>
                    <input type="number" value={form.experience_years} onChange={(e) => setForm({ ...form, experience_years: e.target.value })} className="w-full px-2 py-1.5 border rounded text-sm" style={{ borderColor: "var(--border)" }} />
                  </div>
                  <div>
                    <label className="block text-xs text-slate-500 mb-1">現在単価（万円）</label>
                    <input type="number" value={form.current_price} onChange={(e) => setForm({ ...form, current_price: e.target.value })} className="w-full px-2 py-1.5 border rounded text-sm" style={{ borderColor: "var(--border)" }} />
                  </div>
                  <div className="flex gap-2">
                    <div className="flex-1">
                      <label className="block text-xs text-slate-500 mb-1">希望単価 下限</label>
                      <input type="number" value={form.desired_price_min} onChange={(e) => setForm({ ...form, desired_price_min: e.target.value })} className="w-full px-2 py-1.5 border rounded text-sm" style={{ borderColor: "var(--border)" }} />
                    </div>
                    <div className="flex-1">
                      <label className="block text-xs text-slate-500 mb-1">希望単価 上限</label>
                      <input type="number" value={form.desired_price_max} onChange={(e) => setForm({ ...form, desired_price_max: e.target.value })} className="w-full px-2 py-1.5 border rounded text-sm" style={{ borderColor: "var(--border)" }} />
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs text-slate-500 mb-1">稼働可能日</label>
                    <input type="date" value={form.available_from} onChange={(e) => setForm({ ...form, available_from: e.target.value })} className="w-full px-2 py-1.5 border rounded text-sm" style={{ borderColor: "var(--border)" }} />
                  </div>
                </div>
              </div>

              {/* セクション2: スキル */}
              <div className="mb-4">
                <h4 className="text-xs font-bold text-slate-600 mb-2 border-b pb-1" style={{ borderColor: "var(--border)" }}>スキル</h4>
                {Object.entries(SKILL_CHECKBOXES).map(([cat, skillList]) => (
                  <div key={cat} className="mb-2">
                    <p className="text-xs text-slate-500 mb-1">{cat}</p>
                    <div className="flex flex-wrap gap-x-3 gap-y-1">
                      {skillList.map((sk) => (
                        <label key={sk} className="flex items-center gap-1 text-xs cursor-pointer">
                          <input type="checkbox" checked={form.skills.includes(sk)} onChange={() => {
                            const next = form.skills.includes(sk) ? form.skills.filter(s => s !== sk) : [...form.skills, sk];
                            setForm({ ...form, skills: next });
                          }} />
                          {sk}
                        </label>
                      ))}
                    </div>
                  </div>
                ))}
                <div className="mt-2">
                  <label className="block text-xs text-slate-500 mb-1">その他スキル（セミコロン区切り）</label>
                  <input type="text" value={form.skills_other} onChange={(e) => setForm({ ...form, skills_other: e.target.value })} placeholder="Nuxt.js; GraphQL" className="w-full px-2 py-1.5 border rounded text-sm" style={{ borderColor: "var(--border)" }} />
                </div>
              </div>

              {/* セクション3: 経験 */}
              <div className="mb-4">
                <h4 className="text-xs font-bold text-slate-600 mb-2 border-b pb-1" style={{ borderColor: "var(--border)" }}>経験</h4>
                <div className="space-y-3">
                  <div>
                    <label className="block text-xs text-slate-500 mb-1">職種経験</label>
                    <div className="flex flex-wrap gap-3">
                      {(filters?.job_type_options ?? []).map((jt) => (
                        <label key={jt} className="flex items-center gap-1.5 text-sm cursor-pointer">
                          <input type="checkbox" checked={form.job_type_experience.includes(jt)} onChange={() => {
                            const next = form.job_type_experience.includes(jt) ? form.job_type_experience.filter(v => v !== jt) : [...form.job_type_experience, jt];
                            setForm({ ...form, job_type_experience: next });
                          }} />
                          {jt}
                        </label>
                      ))}
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs text-slate-500 mb-1">ポジション経験</label>
                    <div className="flex flex-wrap gap-3">
                      {(filters?.position_options ?? []).map((pos) => (
                        <label key={pos} className="flex items-center gap-1.5 text-sm cursor-pointer">
                          <input type="checkbox" checked={form.position_experience.includes(pos)} onChange={() => {
                            const next = form.position_experience.includes(pos) ? form.position_experience.filter(v => v !== pos) : [...form.position_experience, pos];
                            setForm({ ...form, position_experience: next });
                          }} />
                          {pos}
                        </label>
                      ))}
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs text-slate-500 mb-1">対応工程</label>
                    <div className="flex flex-wrap gap-3">
                      {(filters?.process_options ?? ["要件定義", "基本設計", "詳細設計", "実装", "テスト", "運用保守"]).map((proc) => (
                        <label key={proc} className="flex items-center gap-1.5 text-sm cursor-pointer">
                          <input type="checkbox" checked={form.processes.includes(proc)} onChange={() => {
                            const next = form.processes.includes(proc) ? form.processes.filter(p => p !== proc) : [...form.processes, proc];
                            setForm({ ...form, processes: next });
                          }} />
                          {proc}
                        </label>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* セクション4: 勤務条件 */}
              <div className="mb-4">
                <h4 className="text-xs font-bold text-slate-600 mb-2 border-b pb-1" style={{ borderColor: "var(--border)" }}>勤務条件</h4>
                <div className="space-y-3">
                  <div>
                    <label className="block text-xs text-slate-500 mb-1">リモート希望</label>
                    <div className="flex flex-wrap gap-3">
                      {(filters?.remote_options ?? []).map((opt) => (
                        <label key={opt} className="flex items-center gap-1.5 text-sm cursor-pointer">
                          <input type="radio" name="remote_preference" value={opt} checked={form.remote_preference === opt} onChange={() => setForm({ ...form, remote_preference: opt })} />
                          {opt}
                        </label>
                      ))}
                      <label className="flex items-center gap-1.5 text-sm cursor-pointer">
                        <input type="radio" name="remote_preference" value="" checked={form.remote_preference === ""} onChange={() => setForm({ ...form, remote_preference: "" })} />
                        未選択
                      </label>
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs text-slate-500 mb-1">希望勤務地</label>
                    <div className="flex flex-wrap gap-3">
                      {(filters?.area_options ?? []).map((area) => (
                        <label key={area} className="flex items-center gap-1.5 text-sm cursor-pointer">
                          <input type="checkbox" checked={form.preferred_areas.includes(area)} onChange={() => {
                            const next = form.preferred_areas.includes(area) ? form.preferred_areas.filter(a => a !== area) : [...form.preferred_areas, area];
                            setForm({ ...form, preferred_areas: next });
                          }} />
                          {area}
                        </label>
                      ))}
                    </div>
                    <input type="text" value={form.preferred_areas_other} onChange={(e) => setForm({ ...form, preferred_areas_other: e.target.value })} placeholder="その他（カンマ区切り）" className="mt-2 w-full px-2 py-1.5 border rounded text-sm" style={{ borderColor: "var(--border)" }} />
                  </div>
                </div>
              </div>

              {/* セクション5: 今後のキャリア */}
              <div className="mb-4">
                <h4 className="text-xs font-bold text-slate-600 mb-2 border-b pb-1" style={{ borderColor: "var(--border)" }}>今後のキャリア</h4>
                <div className="space-y-3">
                  <div>
                    <label className="block text-xs text-slate-500 mb-1">希望職種</label>
                    <div className="flex flex-wrap gap-3">
                      {(filters?.job_type_options ?? []).map((jt) => (
                        <label key={jt} className="flex items-center gap-1.5 text-sm cursor-pointer">
                          <input type="checkbox" checked={form.career_desired_job_type.includes(jt)} onChange={() => {
                            const next = form.career_desired_job_type.includes(jt) ? form.career_desired_job_type.filter(v => v !== jt) : [...form.career_desired_job_type, jt];
                            setForm({ ...form, career_desired_job_type: next });
                          }} />
                          {jt}
                        </label>
                      ))}
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs text-slate-500 mb-1">習得したいスキル</label>
                    <input type="text" value={form.career_desired_skills} onChange={(e) => setForm({ ...form, career_desired_skills: e.target.value })} placeholder="Kubernetes; Go" className="w-full px-2 py-1.5 border rounded text-sm" style={{ borderColor: "var(--border)" }} />
                  </div>
                  <div>
                    <label className="block text-xs text-slate-500 mb-1">キャリアメモ</label>
                    <textarea value={form.career_notes} onChange={(e) => setForm({ ...form, career_notes: e.target.value })} rows={2} className="w-full px-2 py-1.5 border rounded text-sm" style={{ borderColor: "var(--border)" }} />
                  </div>
                </div>
              </div>

              {/* セクション6: 備考 */}
              <div className="mb-3">
                <h4 className="text-xs font-bold text-slate-600 mb-2 border-b pb-1" style={{ borderColor: "var(--border)" }}>備考</h4>
                <textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} rows={2} className="w-full px-2 py-1.5 border rounded text-sm" style={{ borderColor: "var(--border)" }} />
              </div>
              <div className="flex gap-2 mt-3">
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="px-4 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
                >
                  {saving ? "保存中..." : editId ? "更新" : "登録"}
                </button>
                <button
                  onClick={() => setShowForm(false)}
                  className="px-4 py-1.5 bg-gray-200 text-gray-700 text-sm rounded-lg hover:bg-gray-300 transition-colors"
                >
                  キャンセル
                </button>
              </div>
            </div>
          )}

          {/* エンジニア一覧 */}
          {loading ? (
            <div className="flex items-center justify-center py-20 text-slate-400">
              読み込み中...
            </div>
          ) : engineers.length === 0 ? (
            <div className="text-center py-20 text-slate-400">
              {total === 0
                ? "エンジニアが登録されていません。「新規登録」から追加してください。"
                : "条件に一致するエンジニアがいません"}
            </div>
          ) : (
            <div className="space-y-2">
              {/* テーブルヘッダー */}
              <div
                className="grid grid-cols-[1fr_80px_1fr_80px_120px_100px] gap-2 px-4 py-2 text-xs font-semibold text-slate-500 border-b"
                style={{ borderColor: "var(--border)" }}
              >
                <span>名前</span>
                <span>ステータス</span>
                <span>スキル</span>
                <span>経験年数</span>
                <span>現在単価</span>
                <span>稼働可能日</span>
              </div>

              {/* テーブル行 */}
              {engineers.map((eng) => (
                <div key={eng.id}>
                  <div
                    className="grid grid-cols-[1fr_80px_1fr_80px_120px_100px] gap-2 px-4 py-3 rounded-lg border cursor-pointer hover:bg-slate-50 transition-colors"
                    style={{
                      background: "var(--card-bg)",
                      borderColor:
                        expandedId === eng.id ? "var(--primary)" : "var(--border)",
                    }}
                    onClick={() => handleExpand(eng.id)}
                  >
                    <span className="text-sm font-medium truncate">{eng.name}</span>
                    <span>
                      <span
                        className={`inline-block px-2 py-0.5 text-xs rounded-full ${STATUS_COLORS[eng.status] ?? "bg-gray-100 text-gray-500"}`}
                      >
                        {eng.status}
                      </span>
                    </span>
                    <span className="flex flex-wrap gap-0.5 overflow-hidden max-h-6">
                      {eng.skills.map((sk) => {
                        const cat = Object.entries(eng.categorized_skills || {}).find(([, skills]) => skills.includes(sk))?.[0] || "その他";
                        return (
                          <span key={sk} className={`px-1 py-0 text-[10px] rounded ${SKILL_CATEGORY_COLORS[cat] || SKILL_CATEGORY_COLORS["その他"]}`}>
                            {sk}
                          </span>
                        );
                      })}
                    </span>
                    <span className="text-xs text-slate-600">
                      {eng.experience_years != null ? `${eng.experience_years}年` : "-"}
                    </span>
                    <span className="text-xs font-medium">
                      {eng.current_price != null ? `${eng.current_price}万` : "-"}
                      {eng.desired_price_min != null || eng.desired_price_max != null ? (
                        <span className="text-slate-400 ml-1">
                          (希望{eng.desired_price_min ?? "?"}〜{eng.desired_price_max ?? "?"})
                        </span>
                      ) : null}
                    </span>
                    <span className="text-xs text-slate-600">
                      {eng.available_from || "-"}
                    </span>
                  </div>

                  {/* 展開詳細 */}
                  {expandedId === eng.id && detailLoading && (
                    <div
                      className="mx-2 mb-2 p-6 rounded-b-lg border border-t-0 flex items-center justify-center"
                      style={{ background: "#f8fafc", borderColor: "var(--primary)" }}
                    >
                      <svg className="animate-spin h-6 w-6 text-blue-500" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                      <span className="ml-2 text-sm text-slate-500">読み込み中...</span>
                    </div>
                  )}
                  {expandedId === eng.id && detail && !detailLoading && (
                    <div
                      className="mx-2 mb-2 p-4 rounded-b-lg border border-t-0"
                      style={{
                        background: "#f8fafc",
                        borderColor: "var(--primary)",
                      }}
                    >
                      <div className="grid grid-cols-2 gap-4 text-sm mb-3">
                        <div>
                          <p>
                            <span className="font-semibold">名前:</span> {detail.name}
                          </p>
                          <p>
                            <span className="font-semibold">ステータス:</span>{" "}
                            {detail.status}
                          </p>
                          <p>
                            <span className="font-semibold">経験年数:</span>{" "}
                            {detail.experience_years != null
                              ? `${detail.experience_years}年`
                              : "未記入"}
                          </p>
                          <p>
                            <span className="font-semibold">稼働可能日:</span>{" "}
                            {detail.available_from || "未記入"}
                          </p>
                        </div>
                        <div>
                          <p>
                            <span className="font-semibold">現在単価:</span>{" "}
                            {detail.current_price != null
                              ? `${detail.current_price}万円`
                              : "未記入"}
                          </p>
                          <p>
                            <span className="font-semibold">希望単価:</span>{" "}
                            {detail.desired_price_min != null ||
                            detail.desired_price_max != null
                              ? `${detail.desired_price_min ?? "?"}〜${detail.desired_price_max ?? "?"}万円`
                              : "未記入"}
                          </p>
                          <p>
                            <span className="font-semibold">希望エリア:</span>{" "}
                            {detail.preferred_areas || "未記入"}
                          </p>
                        </div>
                      </div>

                      {/* カテゴリ別スキル表示 */}
                      <div className="mb-3">
                        <span className="font-semibold text-sm">スキル:</span>
                        {detail.categorized_skills && Object.keys(detail.categorized_skills).length > 0 ? (
                          <div className="mt-1 space-y-1">
                            {SKILL_CATEGORY_ORDER.filter(cat => detail.categorized_skills?.[cat]?.length).map(cat => (
                              <div key={cat} className="flex items-center gap-1 flex-wrap">
                                <span className="text-xs text-slate-400 w-12 shrink-0">{cat}:</span>
                                {detail.categorized_skills[cat].map(sk => (
                                  <span key={sk} className={`px-1.5 py-0.5 text-xs rounded ${SKILL_CATEGORY_COLORS[cat]}`}>
                                    {sk}
                                  </span>
                                ))}
                              </div>
                            ))}
                          </div>
                        ) : (
                          <span className="text-sm text-slate-500 ml-1">未記入</span>
                        )}
                      </div>

                      {/* 経験・勤務条件 */}
                      {detail.job_type_experience && (
                        <p className="text-sm mb-1">
                          <span className="font-semibold">職種経験:</span>{" "}
                          {detail.job_type_experience.split(",").map(s => s.trim()).filter(Boolean).join(", ")}
                        </p>
                      )}
                      {detail.position_experience && (
                        <p className="text-sm mb-1">
                          <span className="font-semibold">ポジション:</span>{" "}
                          {detail.position_experience.split(",").map(s => s.trim()).filter(Boolean).join(", ")}
                        </p>
                      )}
                      {detail.processes && (
                        <p className="text-sm mb-1">
                          <span className="font-semibold">対応工程:</span>{" "}
                          {detail.processes.split(",").map(p => p.trim()).filter(Boolean).join(", ")}
                        </p>
                      )}
                      {detail.remote_preference && (
                        <p className="text-sm mb-1">
                          <span className="font-semibold">リモート:</span>{" "}
                          {detail.remote_preference}
                        </p>
                      )}
                      {/* キャリア */}
                      {(detail.career_desired_job_type || detail.career_desired_skills || detail.career_notes) && (
                        <div className="text-sm mt-2 mb-3 p-2 rounded" style={{ background: "#f0fdf4", border: "1px solid #bbf7d0" }}>
                          <p className="font-semibold text-green-700 mb-1">今後のキャリア</p>
                          {detail.career_desired_job_type && (
                            <p><span className="text-slate-500">希望職種:</span> {detail.career_desired_job_type.split(",").map(s => s.trim()).filter(Boolean).join(", ")}</p>
                          )}
                          {detail.career_desired_skills && (
                            <p><span className="text-slate-500">習得したいスキル:</span> {detail.career_desired_skills}</p>
                          )}
                          {detail.career_notes && (
                            <p><span className="text-slate-500">メモ:</span> {detail.career_notes}</p>
                          )}
                        </div>
                      )}
                      {detail.notes && (
                        <p className="text-sm mb-3">
                          <span className="font-semibold">備考:</span> {detail.notes}
                        </p>
                      )}

                      <div className="flex gap-2 mb-4">
                        <button
                          onClick={() => openEditForm(eng)}
                          className="px-3 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700 transition-colors"
                        >
                          編集
                        </button>
                        <button
                          onClick={() => handleDelete(eng.id, eng.name)}
                          className="px-3 py-1 bg-red-500 text-white text-xs rounded hover:bg-red-600 transition-colors"
                        >
                          削除
                        </button>
                        <button
                          onClick={() =>
                            router.push(`/matching?tab=engineer&id=${eng.id}`)
                          }
                          className="px-3 py-1 bg-purple-600 text-white text-xs rounded hover:bg-purple-700 transition-colors"
                        >
                          マッチする案件を探す
                        </button>
                      </div>

                      {/* アサイン履歴 */}
                      <div
                        className="p-3 rounded-lg"
                        style={{ background: "#eef2ff", border: "1px solid #c7d2fe" }}
                      >
                        <div className="flex items-center justify-between mb-2">
                          <p className="text-sm font-semibold text-indigo-700">
                            案件アサイン履歴
                          </p>
                          <button
                            onClick={() => setShowAssignForm(!showAssignForm)}
                            className="px-2 py-0.5 bg-indigo-600 text-white text-xs rounded hover:bg-indigo-700 transition-colors"
                          >
                            追加
                          </button>
                        </div>

                        {showAssignForm && (
                          <div className="mb-3 p-3 bg-white rounded border border-indigo-200">
                            <div className="grid grid-cols-2 gap-2 text-sm">
                              <input
                                type="text"
                                placeholder="会社名"
                                value={assignForm.company_name}
                                onChange={(e) =>
                                  setAssignForm({
                                    ...assignForm,
                                    company_name: e.target.value,
                                  })
                                }
                                className="px-2 py-1 border rounded text-sm"
                                style={{ borderColor: "var(--border)" }}
                              />
                              <input
                                type="text"
                                placeholder="案件名"
                                value={assignForm.project_name}
                                onChange={(e) =>
                                  setAssignForm({
                                    ...assignForm,
                                    project_name: e.target.value,
                                  })
                                }
                                className="px-2 py-1 border rounded text-sm"
                                style={{ borderColor: "var(--border)" }}
                              />
                              <input
                                type="date"
                                placeholder="開始日"
                                value={assignForm.start_date}
                                onChange={(e) =>
                                  setAssignForm({
                                    ...assignForm,
                                    start_date: e.target.value,
                                  })
                                }
                                className="px-2 py-1 border rounded text-sm"
                                style={{ borderColor: "var(--border)" }}
                              />
                              <input
                                type="date"
                                placeholder="終了日"
                                value={assignForm.end_date}
                                onChange={(e) =>
                                  setAssignForm({
                                    ...assignForm,
                                    end_date: e.target.value,
                                  })
                                }
                                className="px-2 py-1 border rounded text-sm"
                                style={{ borderColor: "var(--border)" }}
                              />
                              <input
                                type="number"
                                placeholder="単価（万円）"
                                value={assignForm.unit_price}
                                onChange={(e) =>
                                  setAssignForm({
                                    ...assignForm,
                                    unit_price: e.target.value,
                                  })
                                }
                                className="px-2 py-1 border rounded text-sm"
                                style={{ borderColor: "var(--border)" }}
                              />
                              <select
                                value={assignForm.status}
                                onChange={(e) =>
                                  setAssignForm({
                                    ...assignForm,
                                    status: e.target.value,
                                  })
                                }
                                className="px-2 py-1 border rounded text-sm"
                                style={{ borderColor: "var(--border)" }}
                              >
                                <option value="稼働中">稼働中</option>
                                <option value="終了">終了</option>
                                <option value="中断">中断</option>
                              </select>
                            </div>
                            <div className="flex gap-2 mt-2">
                              <button
                                onClick={handleAddAssignment}
                                className="px-3 py-1 bg-indigo-600 text-white text-xs rounded hover:bg-indigo-700 transition-colors"
                              >
                                追加
                              </button>
                              <button
                                onClick={() => setShowAssignForm(false)}
                                className="px-3 py-1 bg-gray-200 text-gray-700 text-xs rounded hover:bg-gray-300 transition-colors"
                              >
                                キャンセル
                              </button>
                            </div>
                          </div>
                        )}

                        {detail.assignments.length === 0 ? (
                          <p className="text-xs text-slate-500">履歴なし</p>
                        ) : (
                          <div className="space-y-2">
                            {detail.assignments.map((a: EngineerAssignment) => (
                              <div
                                key={a.id}
                                className="flex items-center justify-between bg-white p-2 rounded border border-indigo-100 text-sm"
                              >
                                <div>
                                  <span className="font-medium">
                                    {a.company_name || "不明"}
                                  </span>
                                  {a.project_name && (
                                    <span className="text-slate-500 ml-2">
                                      {a.project_name}
                                    </span>
                                  )}
                                  <span className="text-xs text-slate-400 ml-2">
                                    {a.start_date || "?"} 〜 {a.end_date || "継続中"}
                                  </span>
                                  {a.unit_price != null && (
                                    <span className="text-xs text-blue-600 ml-2">
                                      {a.unit_price}万
                                    </span>
                                  )}
                                  <span
                                    className={`ml-2 inline-block px-1.5 py-0.5 text-xs rounded ${
                                      a.status === "稼働中"
                                        ? "bg-blue-100 text-blue-700"
                                        : a.status === "終了"
                                          ? "bg-gray-100 text-gray-600"
                                          : "bg-yellow-100 text-yellow-700"
                                    }`}
                                  >
                                    {a.status}
                                  </span>
                                </div>
                                <button
                                  onClick={() => handleDeleteAssignment(a.id)}
                                  className="text-red-400 hover:text-red-600 text-xs ml-2"
                                >
                                  削除
                                </button>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
