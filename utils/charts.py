from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

BG = "#0d0f12"
PLOT = "#090d12"
TEXT = "#f2f4f7"
MUTED = "#98a2b3"
GRID = "#1e2a38"
CYAN = "#00e5ff"
BLUE = "#2f80ed"
GREEN = "#00c48c"
ORANGE = "#f59e0b"
RED = "#ff3b6b"
PANEL = "#151922"


def base_figure(height: int = 320) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=PLOT,
        font=dict(family="Inter, Segoe UI, Arial, sans-serif", color=TEXT, size=12),
        margin=dict(l=44, r=20, t=18, b=38),
        hoverlabel=dict(bgcolor="#1d2432", bordercolor="#314055", font_color=TEXT),
        showlegend=False,
    )
    return fig


def overall_distribution_chart(dist):
    fig = base_figure(330)
    color_by_score = {5: GREEN, 4: BLUE, 3: CYAN, 2: ORANGE, 1: RED}
    fig.add_trace(
        go.Bar(
            x=dist["pct"],
            y=dist["label"],
            orientation="h",
            marker_color=[color_by_score[int(s)] for s in dist["score"]],
            text=[f"{int(n)} responses ({pct:.1f}%)" for n, pct in zip(dist["count"], dist["pct"])],
            textposition="outside",
            textfont=dict(color=MUTED, size=11),
            cliponaxis=False,
            hovertemplate="%{y}<br>%{x:.1f}%<extra></extra>",
        )
    )
    fig.update_xaxes(range=[0, max(35, float(dist["pct"].max()) + 8) if not dist.empty else 35], visible=False)
    fig.update_yaxes(showgrid=False, tickfont=dict(color=TEXT, size=12), autorange="reversed")
    return fig


def heatmap_chart(matrix):
    fig = base_figure(340)
    if matrix.empty:
        return fig
    z = matrix.values.astype(float)
    x = list(matrix.columns)
    y = list(matrix.index)
    text = [[f"{v:.1f}" if np.isfinite(v) else "—" for v in row] for row in z]
    fig.add_trace(
        go.Heatmap(
            z=z,
            x=x,
            y=y,
            text=text,
            texttemplate="%{text}",
            colorscale=[[0, "#0e1520"], [0.45, "#20364d"], [0.72, "#2d4f70"], [0.9, "#0f7080"], [1, "#00e5ff"]],
            zmin=1,
            zmax=5,
            hovertemplate="%{y} · %{x}: %{z:.2f}/5<extra></extra>",
            xgap=5,
            ygap=5,
            colorbar=dict(title=dict(text="/5", side="right", font=dict(color=MUTED)), tickfont=dict(color=MUTED), thickness=10),
        )
    )
    fig.update_xaxes(side="top", tickfont=dict(color=MUTED, size=10), showgrid=False, zeroline=False)
    fig.update_yaxes(tickfont=dict(color=TEXT, size=11), showgrid=False, zeroline=False)
    return fig


def means_chart(means):
    fig = base_figure(430)
    if means.empty:
        return fig
    means = means.sort_values("mean")
    fig.add_trace(
        go.Bar(
            x=means["mean"],
            y=means["label"],
            orientation="h",
            marker_color=[CYAN if i == len(means)-1 else BLUE for i in range(len(means))],
            text=[f"{v:.2f}" for v in means["mean"]],
            textposition="outside",
            textfont=dict(color=MUTED, size=11),
            cliponaxis=False,
            hovertemplate="%{y}<br>Mean: %{x:.2f}/5<extra></extra>",
        )
    )
    fig.update_xaxes(range=[0, 5.2], dtick=1, tickfont=dict(color=MUTED), gridcolor=GRID, zeroline=False, title="Mean score")
    fig.update_yaxes(tickfont=dict(color=TEXT, size=11), gridcolor="rgba(0,0,0,0)")
    return fig


def programme_chart(programmes):
    fig = base_figure(300)
    if programmes.empty:
        return fig
    fig.add_trace(
        go.Bar(
            x=programmes["programme"],
            y=programmes["mean"],
            marker_color=BLUE,
            text=[f"{v:.2f}" for v in programmes["mean"]],
            textposition="outside",
            textfont=dict(color=MUTED, size=10),
            hovertemplate="%{x}<br>Mean overall: %{y:.2f}/5<extra></extra>",
        )
    )
    fig.update_yaxes(range=[0, 5.2], dtick=1, gridcolor=GRID, tickfont=dict(color=MUTED), title="Mean overall experience")
    fig.update_xaxes(tickfont=dict(color=MUTED), gridcolor="rgba(0,0,0,0)")
    return fig


def visit_chart(visits):
    fig = base_figure(300)
    if visits.empty:
        return fig
    fig.add_trace(
        go.Bar(
            x=visits["visit_frequency"],
            y=visits["mean"],
            marker_color=CYAN,
            text=[f"{v:.2f}" for v in visits["mean"]],
            textposition="outside",
            textfont=dict(color=MUTED, size=10),
            hovertemplate="%{x}<br>Mean overall: %{y:.2f}/5<extra></extra>",
        )
    )
    fig.update_yaxes(range=[0, 5.2], dtick=1, gridcolor=GRID, tickfont=dict(color=MUTED), title="Mean overall experience")
    fig.update_xaxes(tickfont=dict(color=MUTED, size=9), gridcolor="rgba(0,0,0,0)")
    return fig


def issue_chart(issues, top_n=10):
    fig = base_figure(390)
    if issues.empty:
        return fig
    view = issues.head(top_n).sort_values("responses")
    fig.add_trace(
        go.Bar(
            x=view["responses"],
            y=view["area"],
            orientation="h",
            marker_color=[CYAN if i == len(view)-1 else BLUE for i in range(len(view))],
            text=[f"{int(n)} ({pct:.1f}%)" for n, pct in zip(view["responses"], view["pct"])],
            textposition="outside",
            textfont=dict(color=MUTED, size=11),
            cliponaxis=False,
            hovertemplate="%{y}<br>%{x} respondents<extra></extra>",
        )
    )
    fig.update_xaxes(showgrid=True, gridcolor=GRID, tickfont=dict(color=MUTED), title="Respondents selecting area")
    fig.update_yaxes(tickfont=dict(color=TEXT, size=10), gridcolor="rgba(0,0,0,0)")
    return fig


def mobile_reason_chart(reasons, top_n=8):
    fig = base_figure(350)
    if reasons.empty:
        return fig
    view = reasons.head(top_n).sort_values("responses")
    fig.add_trace(
        go.Bar(
            x=view["responses"],
            y=view["reason"],
            orientation="h",
            marker_color=ORANGE,
            text=[f"{int(n)}" for n in view["responses"]],
            textposition="outside",
            textfont=dict(color=MUTED, size=10),
            cliponaxis=False,
            hovertemplate="%{y}<br>%{x} respondents<extra></extra>",
        )
    )
    fig.update_xaxes(showgrid=True, gridcolor=GRID, tickfont=dict(color=MUTED), title="Respondents selecting reason")
    fig.update_yaxes(tickfont=dict(color=TEXT, size=10), gridcolor="rgba(0,0,0,0)")
    return fig


def scatter_chart(result):
    fig = base_figure(360)
    data = result["data"]
    if data.empty:
        return fig
    x = data["x"].astype(float).to_numpy()
    y = data["y"].astype(float).to_numpy()
    fig.add_trace(
        go.Scatter(
            x=x,
            y=y,
            mode="markers",
            marker=dict(size=7, color=BLUE, line=dict(color="#dce9ff", width=0.7), opacity=0.9),
            hovertemplate="Factor: %{x}/5<br>Overall: %{y}/5<extra></extra>",
        )
    )
    if len(np.unique(x)) > 1:
        coef = np.polyfit(x, y, 1)
        xx = np.linspace(1, 5, 100)
        yy = coef[0] * xx + coef[1]
        fig.add_trace(go.Scatter(x=xx, y=yy, mode="lines", line=dict(color=CYAN, width=2), hoverinfo="skip"))
    fig.update_xaxes(range=[0.7, 5.3], dtick=1, title=result["factor"] + " (1–5)", gridcolor=GRID, tickfont=dict(color=MUTED))
    fig.update_yaxes(range=[0.7, 5.3], dtick=1, title="Overall campus experience (1–5)", gridcolor=GRID, tickfont=dict(color=MUTED))
    return fig
