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


# --- 会社名抽出 ---

# 法人格キーワード
_CORP_KEYWORDS = [
    "株式会社", "有限会社", "合同会社", "一般社団法人", "合資会社",
    "(株)", "（株）",
]

# 部署名サフィックス（長い順にマッチさせる）
_DEPT_SUFFIXES = sorted(
    [
        "ITパートナー営業部", "パートナー営業部", "ビジネスパートナー事業部",
        "ビジネスパートナー推進室", "パートナー推進共通", "パートナー推進室",
        "人材サービス部", "HRサービス部", "人材ソリューション部",
        "営業共通", "営業アドレス", "営業グループ", "営業本部", "営業部", "営業",
        "SES事業担当", "事業部", "技術部", "人事部", "総務部",
        "開発部", "人材部", "採用部", "採用担当", "システム部",
        "案件情報担当", "案件情報", "案件配信",
    ],
    key=len,
    reverse=True,
)

# CJK文字の正規表現クラス（漢字・ひらがな・カタカナ + 々〆〇等）
_CJK = r"\u4e00-\u9fff"
_HIRA = r"\u3040-\u309f"
_KATA = r"\u30a0-\u30ff"
_CJK_MARKS = r"\u3005-\u3007"  # 々〆〇
_JP_CHAR = rf"[{_CJK}{_HIRA}{_KATA}{_CJK_MARKS}]"
_KANJI_CHAR = rf"[{_CJK}{_CJK_MARKS}]"  # 漢字+々のみ（カタカナ含まず）


def _contains_corp_keyword(text: str) -> bool:
    """法人格キーワードを含むか"""
    return any(kw in text for kw in _CORP_KEYWORDS)


def _is_likely_person_name(text: str) -> bool:
    """テキスト全体が日本人の氏名かどうかを判定する"""
    text = text.strip()
    if not text:
        return False
    # 姓(1-3文字) + スペース + 名(1-3文字)
    if re.match(rf"^{_JP_CHAR}{{1,3}}[\s\u3000]+{_JP_CHAR}{{1,3}}$", text):
        return True
    # スペースなし漢字のみ2-5文字（木戸、田中一広、内田和希、龍門未沙）
    # ※カタカナを含まない＆法人格キーワードを含まない場合のみ
    if re.match(rf"^{_KANJI_CHAR}{{2,5}}$", text) and not _contains_corp_keyword(text):
        return True
    # 漢字姓(1-3文字) + ひらがな名(1-4文字)（大島ももね、高橋はるか）
    if re.match(rf"^{_KANJI_CHAR}{{1,3}}[{_HIRA}]{{1,4}}$", text):
        return True
    return False


def _is_likely_english_person_name(text: str) -> bool:
    """英語/ローマ字の人名パターンを判定 (FirstName LastName)"""
    text = text.strip()
    return bool(re.match(r"^[A-Z][a-z]+\s+[A-Z][a-z]+$", text))


def _remove_trailing_person_name(text: str) -> str:
    """末尾の日本人名（姓 名 or 姓のみ）を除去する"""
    # "会社名 姓 名" → "会社名"
    m = re.match(
        rf"^(.+?)[\s\u3000]+({_JP_CHAR}{{1,3}}[\s\u3000]+{_JP_CHAR}{{1,3}})$",
        text,
    )
    if m:
        prefix = m.group(1).strip()
        if prefix and not _is_likely_person_name(prefix):
            return prefix

    # "会社名 姓" → "会社名"（姓 = 1-3漢字）
    m = re.match(
        rf"^(.+?)[\s\u3000]+([{_CJK}]{{1,3}})$",
        text,
    )
    if m:
        prefix = m.group(1).strip()
        if prefix and not _is_likely_person_name(prefix):
            return prefix

    return text


def _remove_department_suffix(text: str) -> str:
    """部署名サフィックスを除去する"""
    # 案件情報（XXX）パターン: "ICD案件情報（東京）" → "ICD"
    info_cleaned = re.sub(r"案件情報[（(][^）)]*[）)]$", "", text).strip()
    if info_cleaned != text and info_cleaned:
        return info_cleaned

    # 末尾の括弧付き部署を除去: "会社名(営業)" → "会社名"
    paren_dept = re.sub(r"[（(](営業|採用|人事|技術)[）)]$", "", text).strip()
    if paren_dept != text and paren_dept:
        return paren_dept

    # アンダースコア区切り
    if "_" in text:
        parts = text.split("_", 1)
        first, second = parts[0].strip(), parts[1].strip()
        if first and second:
            # 人名_社名 → 社名（横谷拓人_Digverse → Digverse）
            if _is_likely_person_name(first) and len(second) >= 2:
                return second
            # 社名_サフィックス → 社名（ディーメイク_案件リスト → ディーメイク）
            if len(first) >= 2:
                return first

    # 通常の部署名サフィックス除去
    for suffix in _DEPT_SUFFIXES:
        if text.endswith(suffix):
            cleaned = text[: -len(suffix)].strip()
            if cleaned:
                return cleaned
    return text


def _extract_domain_company(sender: str) -> str:
    """メールアドレスのドメインから会社名を推測する（最終手段）"""
    match = re.search(r"@([^.]+)", sender)
    if match:
        domain = match.group(1)
        # gmail, yahoo, outlook 等の汎用ドメインは除外
        generic = {"gmail", "yahoo", "outlook", "hotmail", "icloud", "aol", "mail"}
        if domain.lower() not in generic:
            return domain
    return ""


def _clean_corp_result(result: str) -> str:
    """法人格キーワード抽出結果を後処理する（人名・部署除去）"""
    # スラッシュ + 人名: 株式会社Kir/大関 → 株式会社Kir
    if "/" in result:
        base, suffix = result.split("/", 1)
        base, suffix = base.strip(), suffix.strip()
        if base and _contains_corp_keyword(base) and _is_likely_person_name(suffix):
            return base

    # 法人格キーワード後の部分を検査
    for kw in ["株式会社", "有限会社", "合同会社", "一般社団法人", "合資会社"]:
        if kw not in result:
            continue
        idx = result.index(kw)
        after = result[idx + len(kw):].strip()
        if not after:
            break  # 法人格のみ → そのまま

        # after全体が明確な人名（4文字以上 or スペース含む） → 空文字
        if _is_likely_person_name(after) and (
            len(after) >= 4 or re.search(r"[\s\u3000]", after)
        ):
            return ""

        # afterが「カタカナ/英語 + 末尾漢字姓」→ 漢字姓を除去
        m = re.match(
            rf"^((?:[A-Za-z0-9\-_.]+|[{_KATA}]+)+)({_KANJI_CHAR}{{1,3}})$",
            after,
        )
        if m:
            cleaned = m.group(1).rstrip("_-. ")
            if len(cleaned) >= 2:
                return kw + cleaned
        break

    return result


def extract_company_from_sender(sender: str) -> str:
    """メール送信者のFromヘッダーから会社名のみを抽出する（担当者名・部署名は除外）

    Returns:
        会社名文字列。特定できない場合は空文字列。
    """
    if not sender:
        return ""

    # メールアドレス部分を除去: "Name <email>" → "Name"
    name_part = re.sub(r"<[^>]+>", "", sender).strip()
    name_part = name_part.strip("\"' ")

    if not name_part or "@" in name_part:
        return _extract_domain_company(sender)

    # === Step 0: 前処理（特殊区切り文字） ===

    # 0a: 全角山括弧: ＜富士ソフト＞案件情報 → 富士ソフト
    fw_bracket_m = re.search(r"[＜<]([^＞>]+)[＞>]", name_part)
    if fw_bracket_m:
        inner = fw_bracket_m.group(1).strip()
        if inner:
            return inner

    # 0b: スラッシュ区切り: 株式会社Kir/大関 → 株式会社Kir
    if "/" in name_part:
        sp0, sp1 = [p.strip() for p in name_part.split("/", 1)]
        if _contains_corp_keyword(sp0) and _is_likely_person_name(sp1):
            name_part = sp0
        elif _contains_corp_keyword(sp1) and _is_likely_person_name(sp0):
            name_part = sp1
        elif _is_likely_person_name(sp1) and not _is_likely_person_name(sp0) and len(sp0) >= 2:
            name_part = sp0
        elif _is_likely_person_name(sp0) and not _is_likely_person_name(sp1) and len(sp1) >= 2:
            name_part = sp1

    # 0c: 特殊記号区切り: アイスタンダード★小瀧 → アイスタンダード
    special_parts = re.split(r"[★☆●◆◇■□▲△▼▽]", name_part)
    if len(special_parts) == 2:
        a, b = special_parts[0].strip(), special_parts[1].strip()
        if a and b:
            if _is_likely_person_name(b) and not _is_likely_person_name(a):
                name_part = a
            elif _is_likely_person_name(a) and not _is_likely_person_name(b):
                name_part = b

    # 0d: はぐれ閉じ括弧: SI)平山 → SI
    stray_paren_m = re.match(r"^([A-Za-z0-9]+)\)(.+)$", name_part)
    if stray_paren_m:
        prefix = stray_paren_m.group(1).strip()
        suffix = stray_paren_m.group(2).strip()
        if _is_likely_person_name(suffix):
            return prefix if len(prefix) >= 2 else ""

    # 0e: アンダースコア前処理
    if "_" in name_part:
        u_first, u_second = [p.strip() for p in name_part.split("_", 1)]
        # 両方使えない: E_竹内 → ""
        if u_second and _is_likely_person_name(u_second) and len(u_first) < 2:
            return ""
        # 人名_社名: 横谷拓人_Digverse → Digverse
        if u_first and u_second and _is_likely_person_name(u_first) and len(u_second) >= 2:
            name_part = u_second
        # 社名_サフィックス: 株式会社NALU_案件配信 → 株式会社NALU
        elif u_first and len(u_first) >= 2:
            name_part = u_first

    # === Step 1: 角括弧・隅付き括弧から会社名を抽出 ===
    # [株式会社AGEST]ITパートナー営業部 → 株式会社AGEST
    # 【スキルジー】白井 → スキルジー
    bracket_m = re.search(r"[\[【\[]([^\]】\]]+)[\]】\]]", name_part)
    if bracket_m:
        inner = bracket_m.group(1).strip()
        if inner:
            return inner

    # === Step 2: 丸括弧で外が人名・中が会社名のパターン ===
    # 櫻井菜々子(IDH) → IDH
    paren_m = re.search(r"[（(]([^）)]+)[）)]", name_part)
    if paren_m:
        inner = paren_m.group(1).strip()
        outer = re.sub(r"[（(][^）)]+[）)]", "", name_part).strip()
        if inner:
            # 外が日本人名 → 中が会社名
            if _is_likely_person_name(outer):
                return inner
            # 外がCJK2-6文字で中が英数字（会社略称）
            if (
                re.match(rf"^{_JP_CHAR}{{2,6}}$", outer)
                and re.match(r"^[A-Za-z0-9\-_.&]+$", inner)
            ):
                return inner
            # 外が英語人名 → 中が会社名: Sana Nakao（OCM） → OCM
            if _is_likely_english_person_name(outer):
                return inner

    # === Step 3: 法人格キーワードによる抽出 ===
    # 株式会社レルモ 清水 → 株式会社レルモ
    # 株式会社D-Standing 本多 愛理 → 株式会社D-Standing
    corp_m = re.search(
        r"((?:株式会社|有限会社|合同会社|一般社団法人|合資会社)\s*\S+)",
        name_part,
    )
    if corp_m:
        return _clean_corp_result(corp_m.group(1).strip())

    # 後置法人格: ABC株式会社
    corp_m2 = re.search(
        r"(\S+\s*(?:株式会社|有限会社|合同会社))",
        name_part,
    )
    if corp_m2:
        return corp_m2.group(1).strip()

    # (株)パターン
    corp_m3 = re.search(r"(\S*[（(]株[）)]\S*)", name_part)
    if corp_m3:
        return corp_m3.group(1).strip()

    # === Step 4: 部署名サフィックスの除去 ===
    # Dynamix営業 → Dynamix, ICD案件情報（東京） → ICD
    dept_cleaned = _remove_department_suffix(name_part)
    if dept_cleaned != name_part:
        if not _is_likely_person_name(dept_cleaned):
            name_part = dept_cleaned  # 更新して後続Stepで追加分解

    # === Step 4b: 「の」区切りで会社名+人名を分離 ===
    # クラウドワークスコンサルティングの大柿 → クラウドワークスコンサルティング
    if "の" in name_part:
        no_parts = name_part.rsplit("の", 1)
        before_no = no_parts[0].strip()
        after_no = no_parts[1].strip()
        if (
            before_no
            and after_no
            and len(before_no) >= 3
            and _is_likely_person_name(after_no)
            and not _is_likely_person_name(before_no)
        ):
            name_part = before_no

    # === Step 5: 全体が人名ならここでは空文字を返す ===
    # （Geminiの抽出結果 or ドメインにフォールバックする）
    if _is_likely_person_name(name_part):
        return ""

    # === Step 6: 末尾の人名を除去（スペースあり） ===
    # Re-Vision 飯島 → Re-Vision, ワクト木村 陽一 → ワクト木村
    cleaned = _remove_trailing_person_name(name_part)
    if cleaned != name_part:
        name_part = cleaned  # 更新して後続Step 7/8で追加分解

    # === Step 7: カタカナ/ひらがな/英語 + 末尾漢字姓（スペースなし） ===
    # ワクト木村 → ワクト, EVERRISE齋藤 → EVERRISE, べリアント池田 → べリアント
    m = re.match(
        rf"^((?:[A-Za-z0-9\-_.]+|[{_KATA}{_HIRA}]+)+)({_KANJI_CHAR}{{1,5}})$",
        name_part,
    )
    if m:
        prefix = m.group(1).rstrip("_-. ")
        if len(prefix) >= 2:
            return prefix

    # === Step 8: 漢字姓 + カタカナ社名（スペースなし） ===
    # 小関スキルコネクト → スキルコネクト
    m = re.match(
        rf"^({_KANJI_CHAR}{{1,3}})((?:[{_KATA}]{{5,}}|[A-Za-z]{{5,}}).*)$",
        name_part,
    )
    if m:
        suffix = m.group(2).strip()
        if len(suffix) >= 3:
            return suffix

    # === Step 9: そのまま返す ===
    # conviction-inc → conviction-inc
    return name_part
