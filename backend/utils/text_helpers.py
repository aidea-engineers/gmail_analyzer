import re
from bs4 import BeautifulSoup


def strip_html(html: str) -> str:
    """HTMLタグを除去してプレーンテキストを返す"""
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def clean_email_body(text: str) -> str:
    """メール本文をクリーニング（引用・署名除去、空白正規化）"""
    if not text:
        return ""
    lines = text.splitlines()
    cleaned = []
    for line in lines:
        # 引用行を除去
        if line.strip().startswith(">"):
            continue
        # 署名区切り以降を除去
        if line.strip() == "--" or line.strip() == "-- ":
            break
        cleaned.append(line)

    result = "\n".join(cleaned)
    # 連続する空行を1つに
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


def truncate_for_gemini(text: str, max_chars: int = 30000) -> str:
    """Geminiのコンテキストウィンドウに収まるようにテキストを切り詰める"""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[...以下省略...]"


# スキル名の正規化マッピング
SKILL_NORMALIZATION = {
    "js": "JavaScript",
    "javascript": "JavaScript",
    "ts": "TypeScript",
    "typescript": "TypeScript",
    "py": "Python",
    "python": "Python",
    "ジャバ": "Java",
    "java": "Java",
    "リアクト": "React",
    "react": "React",
    "react.js": "React",
    "reactjs": "React",
    "ビュー": "Vue.js",
    "vue": "Vue.js",
    "vue.js": "Vue.js",
    "vuejs": "Vue.js",
    "アンギュラー": "Angular",
    "angular": "Angular",
    "ノード": "Node.js",
    "node": "Node.js",
    "node.js": "Node.js",
    "nodejs": "Node.js",
    "go": "Go",
    "golang": "Go",
    "ルビー": "Ruby",
    "ruby": "Ruby",
    "php": "PHP",
    "c#": "C#",
    "シーシャープ": "C#",
    "swift": "Swift",
    "kotlin": "Kotlin",
    "aws": "AWS",
    "azure": "Azure",
    "gcp": "GCP",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "k8s": "Kubernetes",
    "spring": "Spring Boot",
    "spring boot": "Spring Boot",
    "springboot": "Spring Boot",
    "rails": "Ruby on Rails",
    "ruby on rails": "Ruby on Rails",
    "django": "Django",
    "flask": "Flask",
    "laravel": "Laravel",
    "next.js": "Next.js",
    "nextjs": "Next.js",
    "nuxt": "Nuxt.js",
    "nuxt.js": "Nuxt.js",
    "sql": "SQL",
    "mysql": "MySQL",
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "oracle": "Oracle",
    "mongodb": "MongoDB",
    "redis": "Redis",
    "terraform": "Terraform",
    "linux": "Linux",
    "git": "Git",
}


def normalize_skill_name(skill: str) -> str:
    """スキル名を正規化する"""
    if not skill:
        return skill
    key = skill.strip().lower()
    return SKILL_NORMALIZATION.get(key, skill.strip())
