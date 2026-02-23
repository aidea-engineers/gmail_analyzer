import plotly.graph_objects as go
import plotly.express as px

# 共通カラーパレット
COLORS = px.colors.qualitative.Set2


def build_skill_bar_chart(data: list[dict], top_n: int = 15) -> go.Figure:
    """スキル別案件数の横棒グラフ"""
    if not data:
        return _empty_figure("スキル別案件数 - データなし")

    sorted_data = sorted(data, key=lambda x: x["count"], reverse=True)[:top_n]
    # 横棒グラフは下から上に表示されるので逆順に
    sorted_data.reverse()

    skills = [d["skill_name"] for d in sorted_data]
    counts = [d["count"] for d in sorted_data]

    fig = go.Figure(
        go.Bar(
            x=counts,
            y=skills,
            orientation="h",
            marker_color=COLORS[0],
            text=counts,
            textposition="outside",
        )
    )
    fig.update_layout(
        title="スキル別案件数 (Top {})".format(top_n),
        xaxis_title="案件数",
        yaxis_title="",
        margin=dict(l=10, r=10, t=40, b=10),
        height=max(400, len(skills) * 28),
    )
    return fig


def build_price_histogram(data: list[dict]) -> go.Figure:
    """単価分布のヒストグラム"""
    if not data:
        return _empty_figure("単価分布 - データなし")

    # 中央値を使用
    prices = []
    for d in data:
        p_min = d.get("unit_price_min")
        p_max = d.get("unit_price_max")
        if p_min is not None and p_max is not None:
            prices.append((p_min + p_max) / 2)
        elif p_min is not None:
            prices.append(p_min)
        elif p_max is not None:
            prices.append(p_max)

    if not prices:
        return _empty_figure("単価分布 - データなし")

    fig = go.Figure(
        go.Histogram(
            x=prices,
            nbinsx=20,
            marker_color=COLORS[1],
            opacity=0.85,
        )
    )
    fig.update_layout(
        title="単価分布",
        xaxis_title="単価（万円/月）",
        yaxis_title="案件数",
        margin=dict(l=10, r=10, t=40, b=10),
        bargap=0.05,
    )
    return fig


def build_area_pie_chart(data: list[dict], top_n: int = 10) -> go.Figure:
    """エリア別案件数のドーナツチャート"""
    if not data:
        return _empty_figure("エリア別案件数 - データなし")

    sorted_data = sorted(data, key=lambda x: x["count"], reverse=True)
    top = sorted_data[:top_n]
    others_count = sum(d["count"] for d in sorted_data[top_n:])

    labels = [d["work_area"] for d in top]
    values = [d["count"] for d in top]

    if others_count > 0:
        labels.append("その他")
        values.append(others_count)

    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.4,
            marker=dict(colors=COLORS),
            textinfo="label+percent",
            textposition="outside",
        )
    )
    fig.update_layout(
        title="エリア別案件数",
        margin=dict(l=10, r=10, t=40, b=10),
        showlegend=False,
    )
    return fig


def build_trend_line_chart(data: list[dict], granularity: str = "日別") -> go.Figure:
    """日別・週別トレンドの折れ線グラフ"""
    if not data:
        return _empty_figure("案件トレンド - データなし")

    periods = [d["period"] for d in data]
    counts = [d["count"] for d in data]

    fig = go.Figure(
        go.Scatter(
            x=periods,
            y=counts,
            mode="lines+markers",
            marker=dict(color=COLORS[2], size=8),
            line=dict(color=COLORS[2], width=2),
            fill="tozeroy",
            fillcolor="rgba(102,194,165,0.15)",
        )
    )
    fig.update_layout(
        title=f"新着案件トレンド（{granularity}）",
        xaxis_title="期間",
        yaxis_title="案件数",
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


def _empty_figure(title: str) -> go.Figure:
    """データがない場合の空グラフ"""
    fig = go.Figure()
    fig.update_layout(
        title=title,
        annotations=[
            dict(
                text="データがありません",
                xref="paper",
                yref="paper",
                showarrow=False,
                font=dict(size=16, color="gray"),
                x=0.5,
                y=0.5,
            )
        ],
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig
