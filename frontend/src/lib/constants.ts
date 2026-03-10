/* 共有定数 — engineers/page.tsx と my-profile/page.tsx で共通利用 */

import type { EngineerForm } from "@/types";

export const EMPTY_FORM: EngineerForm = {
  name: "",
  name_kana: "",
  email: "",
  phone: "",
  address: "",
  nearest_station: "",
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
  birth_date: "",
  education: "",
  industry_experience: [],
  skill_proficiency: {},
  certifications: "",
};

export const SKILL_CATEGORY_COLORS: Record<string, string> = {
  "WEB": "bg-blue-100 text-blue-700",
  "FW": "bg-purple-100 text-purple-700",
  "インフラ": "bg-orange-100 text-orange-700",
  "DB": "bg-green-100 text-green-700",
  "ネットワーク": "bg-cyan-100 text-cyan-700",
  "その他": "bg-gray-100 text-gray-600",
};

export const SKILL_CATEGORY_ORDER = ["WEB", "FW", "インフラ", "DB", "ネットワーク", "その他"];

export const SKILL_CHECKBOXES: Record<string, string[]> = {
  "WEB": ["Java", "Python", "TypeScript", "JavaScript", "Go", "C#", "Ruby", "PHP", "Swift", "Kotlin", "C", "C++", "Rust", "Scala", "Perl", "R", "COBOL", "VB.NET", "Dart", "Shell"],
  "FW": ["React", "Vue.js", "Angular", "Next.js", "Spring Boot", "Django", "Flask", "Laravel", "Ruby on Rails", ".NET", "Express.js", "NestJS", "Flutter", "Unity"],
  "インフラ": ["AWS", "Azure", "GCP", "Docker", "Kubernetes", "Terraform", "Linux", "Jenkins", "Ansible"],
  "DB": ["PostgreSQL", "MySQL", "Oracle", "SQL Server", "MongoDB", "Redis", "DynamoDB", "Elasticsearch"],
  "ネットワーク": ["Cisco", "CCNA", "CCNP", "Juniper", "Fortinet", "Palo Alto", "F5", "VMware NSX", "Aruba", "Wireshark"],
};

export const ALL_CHECKBOX_SKILLS = Object.values(SKILL_CHECKBOXES).flat();

export const STATUS_COLORS: Record<string, string> = {
  "待機中": "bg-green-100 text-green-800",
  "稼働中": "bg-blue-100 text-blue-800",
  "面談中": "bg-yellow-100 text-yellow-800",
  "休止中": "bg-gray-100 text-gray-500",
};

export const PROCESS_OPTIONS = [
  "要件定義", "基本設計", "詳細設計", "実装", "テスト", "運用保守",
];

export const JOB_TYPE_OPTIONS = [
  "Webアプリ開発", "業務系開発", "インフラ構築", "データ分析",
  "モバイルアプリ開発", "組込み", "PM/PMO", "コンサル",
];

export const POSITION_OPTIONS = [
  "メンバー", "リーダー", "サブリーダー", "PM", "PL", "PMO",
];

export const REMOTE_OPTIONS = ["フルリモート", "一部リモート", "出社"];

export const AREA_OPTIONS = [
  "東京", "神奈川", "千葉", "埼玉", "大阪", "愛知", "福岡", "北海道", "リモート",
];

export const EDUCATION_OPTIONS = [
  "大学院卒", "大学卒", "専門卒", "高卒", "その他",
];

export const INDUSTRY_OPTIONS = [
  "金融", "通信", "製造", "流通・小売", "医療・ヘルスケア",
  "公共・官公庁", "エンタメ・メディア", "不動産・建設", "IT・Web",
];

export const PROFICIENCY_OPTIONS = ["初級", "中級", "上級"];
