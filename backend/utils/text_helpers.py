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


# --- エリア正規化 ---

# 東京23区内の主要地名・駅名
_TOKYO23_NAMES = {
    "東京", "東京都",
    "千代田", "中央区", "港区", "新宿", "文京", "台東", "墨田", "江東", "品川",
    "目黒", "大田区", "世田谷", "渋谷", "中野", "杉並", "豊島", "北区", "荒川",
    "板橋", "練馬", "足立", "葛飾", "江戸川",
    "東京駅", "品川駅", "新宿駅", "渋谷駅", "池袋", "上野", "秋葉原", "六本木",
    "虎ノ門", "赤坂", "神谷町", "新橋", "浜松町", "田町", "大崎", "五反田",
    "恵比寿", "代々木", "原宿", "表参道", "青山", "麹町", "九段下", "神保町",
    "水道橋", "飯田橋", "市ヶ谷", "四ツ谷", "御茶ノ水", "神田", "日本橋",
    "茅場町", "人形町", "豊洲", "お台場", "台場", "有明", "銀座", "築地",
    "月島", "勝どき", "汐留", "中目黒", "三軒茶屋", "高田馬場", "大手町",
    "丸の内", "八重洲", "京橋", "日比谷", "霞ヶ関", "永田町", "溜池山王",
    "六本木一丁目", "麻布", "白金", "芝", "竹芝", "天王洲", "蒲田",
    "錦糸町", "清澄白河", "門前仲町", "木場", "東陽町", "西新宿", "初台",
    "北参道", "外苑前", "青山一丁目", "三越前", "小川町", "淡路町", "十条",
    "高輪ゲートウェイ", "田端", "御成門", "麻布台", "新川", "八丁堀",
    "二子玉川", "三田",
}

_KANAGAWA_NAMES = {
    "横浜", "川崎", "鎌倉", "藤沢", "相模原", "厚木", "小田原",
    "みなとみらい", "武蔵小杉", "溝の口", "桜木町", "関内", "戸塚",
    "湘南", "新横浜", "神奈川",
}

_SAITAMA_NAMES = {
    "さいたま", "浦和", "大宮", "川口", "越谷", "川越", "所沢",
    "与野", "さいたま新都心", "埼玉",
}

_CHIBA_NAMES = {
    "千葉", "船橋", "柏", "松戸", "市川", "浦安", "成田", "幕張",
    "西船橋", "稲毛",
}

_OSAKA_NAMES = {
    "大阪", "梅田", "難波", "心斎橋", "天王寺", "淀屋橋", "本町",
    "北浜", "肥後橋", "堺", "新大阪", "西淀川", "土佐堀", "野田阪神",
}

_OSAKA_KINKO_NAMES = {
    "京都", "奈良", "兵庫", "神戸", "三宮", "三ノ宮", "尼崎",
    "西宮", "和田岬", "姫路",
}

_NAGOYA_NAMES = {"名古屋", "名古屋駅"}

_AICHI_NAMES = {"愛知", "豊田", "岡崎", "一宮", "春日井", "豊橋"}

_FUKUOKA_NAMES = {"福岡", "博多", "天神", "北九州", "太宰府", "西新"}

# 東京23区外の多摩地域
_TOKYO_TAMA_NAMES = {
    "八王子", "立川", "武蔵野", "三鷹", "府中", "調布", "町田",
    "多摩", "多摩センター", "分倍河原", "北府中", "吉祥寺",
}

# 既にカテゴリ化されている値はそのまま通す
_VALID_CATEGORIES = {
    "東京23区", "埼玉", "千葉", "神奈川", "大阪", "大阪近郊（京都・奈良・兵庫）",
    "名古屋", "愛知（名古屋除く）", "福岡", "フルリモート",
}


def _detect_region(text: str) -> str:
    """テキストから地域カテゴリを判定する"""
    # 名古屋は愛知より先に判定（名古屋を含む場合は「名古屋」カテゴリ）
    for name in _NAGOYA_NAMES:
        if name in text:
            return "名古屋"
    for name in _AICHI_NAMES:
        if name in text:
            return "愛知（名古屋除く）"
    for name in _TOKYO23_NAMES:
        if name in text:
            return "東京23区"
    for name in _TOKYO_TAMA_NAMES:
        if name in text:
            return "東京23区"  # 多摩も東京23区に含める（ユーザーの分類に準拠）
    for name in _KANAGAWA_NAMES:
        if name in text:
            return "神奈川"
    for name in _SAITAMA_NAMES:
        if name in text:
            return "埼玉"
    for name in _CHIBA_NAMES:
        if name in text:
            return "千葉"
    for name in _OSAKA_KINKO_NAMES:
        if name in text:
            return "大阪近郊（京都・奈良・兵庫）"
    for name in _OSAKA_NAMES:
        if name in text:
            return "大阪"
    for name in _FUKUOKA_NAMES:
        if name in text:
            return "福岡"
    return ""


def normalize_area(area: str) -> str:
    """エリア文字列を正規化カテゴリに変換する"""
    if not area:
        return ""

    area = area.strip()

    # 既にカテゴリ化されている場合はそのまま
    if area in _VALID_CATEGORIES:
        return area

    # リモート（xxx）形式はそのまま通す
    if re.match(r"^リモート（.+）$", area):
        return area
    if re.match(r"^フルリモート$", area):
        return area

    # リモート系キーワード判定
    remote_keywords = ["フルリモート", "完全リモート", "基本リモート", "基本リモート・地方可"]
    partial_remote_keywords = ["リモート", "テレワーク", "在宅"]
    is_full_remote = any(kw in area for kw in remote_keywords)
    is_partial_remote = any(kw in area for kw in partial_remote_keywords)

    # カンマ区切りの場合、各部分を個別に解析
    parts = [p.strip() for p in re.split(r"[,、]", area)]

    # リモート以外の部分から地域を検出
    regions = []
    for part in parts:
        # リモート系の部分はスキップ
        if any(kw in part for kw in remote_keywords + partial_remote_keywords):
            # ただし「リモート（東京23区）」のような形式の場合はリモート＋地域を検出
            region = _detect_region(part)
            if region and region not in regions:
                regions.append(region)
            continue
        region = _detect_region(part)
        if region and region not in regions:
            regions.append(region)

    if is_full_remote and not regions:
        return "フルリモート"

    if is_full_remote and regions:
        # 完全リモートだが拠点がある場合
        return "フルリモート"

    if is_partial_remote and regions:
        if len(regions) == 1:
            return f"リモート（{regions[0]}）"
        return ", ".join(f"リモート（{r}）" for r in regions)

    if regions:
        return ", ".join(regions)

    if is_partial_remote or is_full_remote:
        return "フルリモート"

    return area  # マッチしなければ元の値を返す


def extract_company_from_sender(sender: str) -> str:
    """メール送信者のFromヘッダーから会社名を推測する"""
    if not sender:
        return ""

    # "株式会社ABC <abc@example.com>" → "株式会社ABC"
    name_part = re.sub(r"<[^>]+>", "", sender).strip()
    # 末尾の空白やクォートを除去
    name_part = name_part.strip("\"' ")

    # 名前部分がメールアドレスそのもの（<>なしの裸アドレス）の場合はドメインから推測
    if name_part and "@" not in name_part:
        return name_part

    # メールアドレスからドメイン名を抽出
    match = re.search(r"@([^.]+)", sender)
    if match:
        return match.group(1)

    return ""
