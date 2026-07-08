"""Template HTML executivo para relatórios por e-mail — visual, focado em status e progresso."""

from __future__ import annotations

import html
import math
from typing import Any

from report_template import (
    KPI_BUCKETS,
    _count_buckets,
    _render_visual_project_card,
)

FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"
BLUE = "#1e4b7a"
BLUE_LIGHT = "#e8f1fa"
GRAY = "#86868b"
TEXT = "#1d1d1f"
BORDER = "#e5e5ea"

_DONUT_RADIUS = 12
_DONUT_CIRC = 2 * math.pi * _DONUT_RADIUS
_KPI_CARD_MIN_HEIGHT = "108px"
_KPI_TITLE_MIN_HEIGHT = "34px"


def _esc(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def _ring_dasharray(pct: float, circumference: float) -> str:
    pct = max(0.0, min(100.0, pct))
    filled = pct / 100 * circumference
    return f"{filled:.2f} {circumference:.2f}"


def _donut_svg(pct: float, color: str = BLUE) -> str:
    pct = max(0.0, min(100.0, pct))
    dash = _ring_dasharray(pct, _DONUT_CIRC)
    return (
        f'<svg width="32" height="32" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">'
        f'<circle cx="16" cy="16" r="{_DONUT_RADIUS}" fill="none" stroke="#e8e8ed" stroke-width="3"/>'
        f'<circle cx="16" cy="16" r="{_DONUT_RADIUS}" fill="none" stroke="{color}" stroke-width="3" '
        f'stroke-dasharray="{dash}" stroke-linecap="round" transform="rotate(-90 16 16)"/>'
        f'<text x="16" y="17" text-anchor="middle" font-size="7" font-weight="700" fill="{BLUE}">'
        f"{pct:.0f}%</text></svg>"
    )


def _render_kpi_cell(title: str, count: int, pct: float) -> str:
    return f"""
    <td width="25%" style="padding:5px;vertical-align:top;height:1px;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
             style="background:#ffffff;border:1px solid {BORDER};border-radius:12px;min-height:{_KPI_CARD_MIN_HEIGHT};height:100%;box-shadow:0 3px 10px rgba(0,0,0,0.06);">
        <tr>
          <td style="padding:12px 10px;font-family:{FONT};height:100%;vertical-align:top;">
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
              <tr>
                <td style="vertical-align:top;">
                  <p style="margin:0;font-size:10px;font-weight:700;color:{GRAY};line-height:1.25;min-height:{_KPI_TITLE_MIN_HEIGHT};">{_esc(title)}</p>
                  <p style="margin:6px 0 0;font-size:30px;font-weight:800;color:{BLUE};line-height:1;">{count}</p>
                </td>
                <td width="42" align="right" style="vertical-align:middle;">{_donut_svg(pct, BLUE)}</td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    </td>"""


def _render_kpi_buckets(cards: list[dict[str, Any]]) -> str:
    if not cards:
        return ""

    total = len(cards) or 1
    counts = _count_buckets(cards)
    cells = ""
    for key, title in KPI_BUCKETS:
        count = counts[key]
        pct = (count / total) * 100
        cells += _render_kpi_cell(title, count, pct)

    return f"""
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
           style="table-layout:fixed;margin:8px 0 6px;">
      <tr>{cells}</tr>
    </table>
    """


def _render_project_card(index: int, card: dict[str, Any]) -> str:
    return _render_visual_project_card(index, card, layout="list")


def _icon_badge(symbol: str, bg: str, color: str, size: int = 26) -> str:
    return (
        f'<div style="width:{size}px;height:{size}px;border-radius:50%;background:{bg};color:{color};'
        f'font-size:{size - 11}px;font-weight:700;text-align:center;line-height:{size}px;">'
        f"{symbol}</div>"
    )


def _render_highlight_item(text: str, *, symbol: str, bg: str, icon_bg: str, icon_color: str, border: str) -> str:
    return f"""
    <tr>
      <td style="padding:0 0 8px;font-family:{FONT};">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
               style="background:{bg};border:1px solid {border};border-radius:8px;">
          <tr>
            <td width="38" align="center" style="padding:8px 0 8px 10px;vertical-align:top;">
              {_icon_badge(symbol, icon_bg, icon_color)}
            </td>
            <td style="padding:8px 10px 8px 6px;vertical-align:middle;">
              <p style="margin:0;font-size:11px;line-height:1.45;color:{TEXT};">{_esc(text)}</p>
            </td>
          </tr>
        </table>
      </td>
    </tr>"""


def _render_highlights_section(weekly_highlights: dict[str, str] | None) -> str:
    if not weekly_highlights:
        return ""

    positive = weekly_highlights.get("positive", "").strip()
    negative = weekly_highlights.get("negative", "").strip()
    if not positive and not negative:
        return ""

    items = ""
    if positive:
        items += _render_highlight_item(
            positive,
            symbol="&#10003;",
            bg="#edf9f0",
            icon_bg="#34c759",
            icon_color="#ffffff",
            border="#c8ebd2",
        )
    if negative:
        items += _render_highlight_item(
            negative,
            symbol="&#10005;",
            bg="#fff1f0",
            icon_bg="#ff3b30",
            icon_color="#ffffff",
            border="#ffd4d1",
        )

    return f"""
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
           style="margin-top:14px;background:#ffffff;border:1px solid {BORDER};border-radius:10px;overflow:hidden;">
      <tr>
        <td style="padding:10px 12px;background:linear-gradient(180deg,#edf9f0 0%,#ffffff 100%);border-bottom:1px solid #c8ebd2;font-family:{FONT};">
          <p style="margin:0;font-size:11px;font-weight:700;letter-spacing:0.04em;text-transform:uppercase;color:#1f7a3f;">
            Destaques da Semana
          </p>
        </td>
      </tr>
      <tr>
        <td style="padding:8px 10px 6px;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
            {items}
          </table>
        </td>
      </tr>
    </table>
    """


def _render_attention_section(attention_points: list[str] | None) -> str:
    points = [point.strip() for point in (attention_points or []) if point.strip()]
    if not points:
        return ""

    items = "".join(
        _render_highlight_item(
            point,
            symbol="&#9888;",
            bg="#fff9ec",
            icon_bg="#ff9500",
            icon_color="#ffffff",
            border="#ffe3a8",
        )
        for point in points
    )

    return f"""
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
           style="margin-top:14px;background:#ffffff;border:1px solid {BORDER};border-radius:10px;overflow:hidden;">
      <tr>
        <td style="padding:10px 12px;background:linear-gradient(180deg,#fff9ec 0%,#ffffff 100%);border-bottom:1px solid #ffe3a8;font-family:{FONT};">
          <p style="margin:0;font-size:11px;font-weight:700;letter-spacing:0.04em;text-transform:uppercase;color:#9a6700;">
            Pontos de atenção
          </p>
        </td>
      </tr>
      <tr>
        <td style="padding:8px 10px 6px;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
            {items}
          </table>
        </td>
      </tr>
    </table>
    """


def build_email_html(
    *,
    report_title: str,
    generated_at: str,
    total_cards: int,
    impeditive_count: int,
    cards: list[dict[str, Any]],
    kpi_cards: list[dict[str, Any]] | None = None,
    parent_label: str | None = None,
    mode: str = "full",
    weekly_highlights: dict[str, str] | None = None,
    attention_points: list[str] | None = None,
) -> str:
    squad = parent_label or report_title.replace("RELATÓRIO JIRA — ", "").split("(")[0].strip()
    kpi_source = kpi_cards if kpi_cards is not None else cards

    projects_html = "".join(
        _render_project_card(index, card) for index, card in enumerate(cards, start=1)
    )

    empty_state = ""
    if not cards:
        empty_state = f"""
        <p style="margin:12px 0;padding:14px;background:#ffffff;border:1px solid {BORDER};
                  border-radius:10px;text-align:center;font-size:12px;color:{GRAY};font-family:{FONT};">
          Nenhum card encontrado para os filtros selecionados.
        </p>
        """

    summary_line = f"{total_cards} projeto{'s' if total_cards != 1 else ''}"
    if impeditive_count:
        summary_line += f" · {impeditive_count} com impeditivo"

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta name="color-scheme" content="light" />
  <title>{_esc(report_title)}</title>
</head>
<body style="margin:0;padding:0;background:#f2f4f8;-webkit-font-smoothing:antialiased;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f2f4f8;">
    <tr>
      <td align="center" style="padding:20px 10px;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;">

          <tr>
            <td style="padding:14px 16px;background:#ffffff;border:1px solid {BORDER};border-radius:12px;font-family:{FONT};">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td>
                    <p style="margin:0 0 1px;font-size:10px;font-weight:800;letter-spacing:0.14em;color:{BLUE};">UISA</p>
                    <h1 style="margin:0 0 3px;font-size:14px;font-weight:700;color:{BLUE};letter-spacing:-0.01em;line-height:1.2;">
                      Status Report Executivo — Squad {_esc(squad)}
                    </h1>
                    <p style="margin:0;font-size:10px;color:{GRAY};">
                      Governança operacional · {_esc(generated_at)}
                    </p>
                  </td>
                  <td align="right" style="vertical-align:top;">
                    <p style="margin:0;padding:5px 9px;background:{BLUE_LIGHT};border-radius:8px;
                               font-size:9px;font-weight:600;color:{BLUE};white-space:nowrap;">
                      {_esc(summary_line)}
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <tr>
            <td style="font-family:{FONT};">
              {_render_kpi_buckets(kpi_source)}
            </td>
          </tr>

          <tr>
            <td style="font-family:{FONT};">
              {_render_highlights_section(weekly_highlights)}
              {_render_attention_section(attention_points)}
            </td>
          </tr>

          <tr>
            <td style="padding:8px 0 4px;font-family:{FONT};">
              <p style="margin:0 0 8px;font-size:10px;font-weight:700;letter-spacing:0.08em;
                         text-transform:uppercase;color:{GRAY};">
                Projetos
              </p>
              {projects_html}
              {empty_state}
            </td>
          </tr>

          <tr>
            <td style="padding:16px 4px 0;text-align:center;font-family:{FONT};">
              <p style="margin:0;font-size:10px;color:#aeaeb2;">
                Quality Software · Relatório automático Jira
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""
