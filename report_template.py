"""Template HTML do Report visual — foco em etapa, impeditivo, responsável e progresso."""

from __future__ import annotations

import html
import math
from typing import Any

FONT = "-apple-system,BlinkMacSystemFont,'SF Pro Text','SF Pro Display','Helvetica Neue',sans-serif"
BLUE = "#007aff"
GRAY = "#6e6e73"
TEXT = "#1d1d1f"
BORDER = "#e5e5ea"
BG = "#e8e8ed"
BG_DESKTOP = "linear-gradient(180deg, #d7dce8 0%, #e7e9f0 35%, #f5f5f7 100%)"
WINDOW_BG = "#ffffff"
SURFACE_2 = "#f5f5f7"
RED = "#ff3b30"
GREEN = "#34c759"
ORANGE = "#ff9500"
PURPLE = "#af52de"
SHADOW = "0 22px 70px rgba(0,0,0,0.12), 0 2px 10px rgba(0,0,0,0.06)"

KPI_BUCKETS = (
    ("backlog", "Backlog"),
    ("mapeamento", "Mapeamento"),
    ("desenvolvimento", "Desenvolvimento"),
    ("entregues", "Entregue"),
)

_PROGRESS_RING_RADIUS = 20
_PROGRESS_RING_CIRC = 2 * math.pi * _PROGRESS_RING_RADIUS
_DONUT_RADIUS = 18
_DONUT_CIRC = 2 * math.pi * _DONUT_RADIUS
_HERO_RING_RADIUS = 34
_HERO_RING_CIRC = 2 * math.pi * _HERO_RING_RADIUS
_KPI_SEGMENT_MIN_HEIGHT = "84px"

# Estimativa de altura uniforme dos cards em grade (equalização pelo maior card)
_GRID_CARD_PADDING = 14
_GRID_TITLE_CHARS_PER_LINE = 26
_GRID_TITLE_LINE_HEIGHT = 18
_GRID_TITLE_BASE_HEIGHT = 26
_GRID_TITLE_MAX_LINES = 6
_GRID_CONTENT_BASE = 248


def _esc(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def _normalize_status(status: str) -> str:
    return " ".join(str(status or "").lower().split())


def is_entregue_status(status: str) -> bool:
    """Status concluído/entregue — não confundir com 'pronto para entrega' etc."""
    n = _normalize_status(status)
    if "itens conclu" in n:
        return True
    if "conclu" in n:
        return True
    if n in ("entregue", "entregues", "entregue ao cliente"):
        return True
    if n.startswith("entregue") and "para" not in n:
        return True
    return False


def _bucket_for_status(status: str) -> str:
    n = _normalize_status(status)
    if "backlog" in n:
        return "backlog"
    if "mapeamento" in n:
        return "mapeamento"
    if any(x in n for x in ("desenvolv", "pronto para", "teste", "homolog")):
        return "desenvolvimento"
    if is_entregue_status(status):
        return "entregues"
    return "desenvolvimento"


def _active_report_cards(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Projetos em andamento — exclui entregues da grade do relatório."""
    return [card for card in cards if _bucket_for_status(card.get("status", "")) != "entregues"]


def _count_buckets(cards: list[dict[str, Any]]) -> dict[str, int]:
    counts = {key: 0 for key, _ in KPI_BUCKETS}
    for card in cards:
        counts[_bucket_for_status(card.get("status", ""))] += 1
    return counts


def _impeditivo_display(impeditivo: str) -> tuple[str, str, str]:
    if impeditivo == "Sim":
        return RED, "Sim", "#fff1f0"
    return GREEN, "Não", "#edf9f0"


def _is_desenvolvimento_etapa(status: str) -> bool:
    n = _normalize_status(status)
    return n == "desenvolvimento"


def _ring_dasharray(pct: float, circumference: float) -> str:
    pct = max(0.0, min(100.0, pct))
    filled = pct / 100 * circumference
    return f"{filled:.2f} {circumference:.2f}"


def _progress_ring_svg(pct: int, *, size: int = 48, radius: int | None = None, color: str = BLUE) -> str:
    pct = max(0, min(100, pct))
    if radius is None:
        radius = size // 2 - 4
    circ = 2 * math.pi * radius
    dash = _ring_dasharray(pct, circ)
    center = size // 2
    font_size = max(9, size // 5)
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" xmlns="http://www.w3.org/2000/svg">'
        f'<circle cx="{center}" cy="{center}" r="{radius}" fill="none" stroke="#e8e8ed" stroke-width="6"/>'
        f'<circle cx="{center}" cy="{center}" r="{radius}" fill="none" stroke="{color}" stroke-width="6" '
        f'stroke-dasharray="{dash}" stroke-linecap="round" transform="rotate(-90 {center} {center})"/>'
        f'<text x="{center}" y="{center + font_size // 3}" text-anchor="middle" font-size="{font_size}" '
        f'font-weight="700" fill="{BLUE}">{pct}%</text>'
        f"</svg>"
    )


def _donut_svg(pct: float, color: str) -> str:
    pct = max(0.0, min(100.0, pct))
    dash = _ring_dasharray(pct, _DONUT_CIRC)
    return (
        f'<svg width="44" height="44" viewBox="0 0 44 44" xmlns="http://www.w3.org/2000/svg">'
        f'<circle cx="22" cy="22" r="{_DONUT_RADIUS}" fill="none" stroke="#e8e8ed" stroke-width="5"/>'
        f'<circle cx="22" cy="22" r="{_DONUT_RADIUS}" fill="none" stroke="{color}" stroke-width="5" '
        f'stroke-dasharray="{dash}" stroke-linecap="round" transform="rotate(-90 22 22)"/>'
        f'<text x="22" y="24" text-anchor="middle" font-size="9" font-weight="700" fill="{BLUE}">'
        f"{pct:.0f}%</text></svg>"
    )


def _status_pill(status: str) -> str:
    normalized = _normalize_status(status)
    if "backlog" in normalized:
        bg, color = SURFACE_2, "#515154"
    elif "mapeamento" in normalized:
        bg, color = "#eef8ff", "#4a90e2"
    elif "desenvolv" in normalized or "pronto para" in normalized:
        bg, color = "#e8f4ff", "#0063d6"
    elif "homolog" in normalized:
        bg, color = "#eaf9ef", "#248a3d"
    elif "teste" in normalized:
        bg, color = "#f3e8ff", PURPLE
    elif is_entregue_status(status):
        bg, color = "#eaf9ef", "#248a3d"
    else:
        bg, color = SURFACE_2, "#515154"
    return (
        f'<span style="display:inline-block;padding:4px 10px;border-radius:8px;'
        f"font-size:11px;font-weight:700;background:{bg};color:{color};letter-spacing:-0.01em;\">"
        f"{_esc(status)}</span>"
    )


def _render_progress_hero(
    progress: int,
    done: int | None = None,
    total: int | None = None,
    *,
    compact: bool = False,
) -> str:
    pct = max(0, min(100, int(progress)))
    pct_color = BLUE if pct < 100 else GREEN
    fraction = ""
    if done is not None and total is not None and total > 0:
        fraction = (
            f'<p style="margin:4px 0 0;font-size:10px;'
            f'font-weight:600;color:{GRAY};">{done} de {total} subtarefas</p>'
        )

    bar_width = f"{pct}%"
    number_size = "18px" if compact else "20px"
    bar_max = "88px" if compact else "108px"
    bar_height = "6px"
    padding = "4px 0 2px" if compact else "6px 0 4px"
    return f"""
    <div style="text-align:center;padding:{padding};">
      <p style="margin:0 0 4px;font-size:{number_size};font-weight:800;color:{BLUE};line-height:1;">{pct}%</p>
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
             style="max-width:{bar_max};margin:0 auto;border:1px solid #dfe6f2;border-radius:5px;overflow:hidden;">
        <tr>
          <td style="background:{pct_color};height:{bar_height};width:{bar_width};font-size:1px;line-height:{bar_height};">&nbsp;</td>
          <td style="background:#e8e8ed;height:{bar_height};font-size:1px;line-height:{bar_height};">&nbsp;</td>
        </tr>
      </table>
      {fraction}
    </div>"""


def _render_progress_placeholder() -> str:
    return f"""
    <div style="text-align:center;padding:2px 0;">
      <div style="display:inline-flex;align-items:center;justify-content:center;width:40px;height:40px;
                  border-radius:50%;background:#f5f5f7;border:2px dashed #d1d1d6;">
        <span style="font-size:9px;font-weight:600;color:{GRAY};">N/A</span>
      </div>
      <p style="margin:2px 0 0;font-size:10px;color:{GRAY};line-height:1.2;">Sem subtarefas</p>
    </div>"""


def _render_last_update_section(card: dict[str, Any]) -> str:
    text = _esc(
        card.get("ultima_atualizacao_exibicao")
        or card.get("ultima_atualizacao")
        or "Nenhuma atualização encontrada."
    )
    date = card.get("ultima_atualizacao_data") or ""
    date_html = (
        f'<p style="margin:3px 0 0;font-size:10px;line-height:1.2;color:{GRAY};">{_esc(date)}</p>'
        if date
        else ""
    )
    return f"""
    <div style="margin-top:8px;padding-top:8px;border-top:1px solid {BORDER};">
      <p style="margin:0 0 4px;font-size:10px;font-weight:700;color:{GRAY};text-transform:uppercase;letter-spacing:0.06em;">Última Atualização</p>
      <p style="margin:0;font-size:11px;line-height:1.4;color:{TEXT};">{text}</p>
      {date_html}
    </div>"""


def _render_impeditivo_semaphore(impeditivo: str) -> str:
    is_blocked = impeditivo == "Sim"
    light = RED if is_blocked else GREEN
    legend = "Com impeditivo" if is_blocked else "Sem impeditivo"
    return f"""
    <div style="text-align:center;min-width:72px;">
      <div style="width:16px;height:16px;border-radius:50%;background:{light};margin:0 auto;
                  border:2px solid #ffffff;box-shadow:0 0 0 1px {BORDER}, 0 1px 3px rgba(0,0,0,0.12);"></div>
      <p style="margin:5px 0 0;font-size:9px;font-weight:600;color:{GRAY};line-height:1.2;">{legend}</p>
    </div>"""


def _title_lines_needed(summary: str, *, chars_per_line: int = _GRID_TITLE_CHARS_PER_LINE) -> int:
    length = len(str(summary or ""))
    if length <= 0:
        return 1
    return max(1, min(_GRID_TITLE_MAX_LINES, math.ceil(length / chars_per_line)))


def _estimate_grid_card_height(cards: list[dict[str, Any]]) -> int:
    if not cards:
        return 0
    title_lines = max(_title_lines_needed(card.get("summary", "")) for card in cards)
    header_extra = max(0, title_lines - 1) * _GRID_TITLE_LINE_HEIGHT
    return _GRID_CONTENT_BASE + header_extra + (_GRID_CARD_PADDING * 2)


def _render_visual_project_card(
    index: int,
    card: dict[str, Any],
    *,
    layout: str = "grid",
    fixed_height: int | None = None,
) -> str:
    impeditivo = card.get("impeditivo", "Não")
    is_blocked = impeditivo == "Sim"
    status = card.get("status", "")
    idx = f"{index:02d}"
    progress = card.get("progresso_subtarefas")
    progress_done = card.get("progresso_subtarefas_concluidas")
    progress_total = card.get("progresso_subtarefas_total")
    border_accent = RED if is_blocked else BORDER

    if progress is not None:
        progress_html = _render_progress_hero(
            progress, progress_done, progress_total, compact=layout == "list"
        )
    else:
        progress_html = _render_progress_placeholder()

    dev = _esc(card.get("dev_responsavel", "Não atribuído"))
    summary = _esc(card.get("summary", ""))

    if layout == "list":
        last_update_html = _render_last_update_section(card)
        height_style = f"height:{fixed_height}px;" if fixed_height else ""
        return f"""
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
           style="margin-bottom:10px;background:#ffffff;border:1px solid {BORDER};border-left:4px solid {border_accent};
                  border-radius:12px;box-shadow:0 1px 4px rgba(0,0,0,0.04);{height_style}">
      <tr>
        <td style="padding:14px 16px;font-family:{FONT};">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
            <tr>
              <td width="36" style="vertical-align:top;">
                <div style="width:28px;height:28px;border-radius:8px;background:{BLUE};background-image:linear-gradient(180deg,#3b9cff 0%,{BLUE} 100%);color:#fff;
                            font-size:11px;font-weight:700;text-align:center;line-height:28px;">{idx}</div>
              </td>
              <td style="vertical-align:top;padding:0 12px;">
                <p style="margin:0 0 8px;font-size:14px;font-weight:700;color:{TEXT};line-height:1.3;letter-spacing:-0.02em;">
                  {_esc(card.get("summary", ""))}
                </p>
                <p style="margin:0 0 8px;">{_status_pill(status)}</p>
                <p style="margin:0;font-size:12px;color:{GRAY};">
                  <span style="font-weight:700;color:{TEXT};">Responsável</span> · {dev}
                </p>
                {last_update_html}
              </td>
              <td width="88" align="center" style="vertical-align:top;">
                {_render_impeditivo_semaphore(impeditivo)}
              </td>
              <td width="100" align="center" style="vertical-align:middle;">
                {progress_html}
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>"""

    last_update_html = _render_last_update_section(card)
    height_style = f"min-height:{fixed_height}px;" if fixed_height else ""
    pad = _GRID_CARD_PADDING
    return f"""
    <td width="33.33%" style="padding:8px;vertical-align:top;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
             class="project-card-eq"
             style="background:#ffffff;border:1px solid {BORDER};border-top:4px solid {border_accent};
                    border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,0.06),0 0 0 0.5px rgba(0,0,0,0.04);{height_style}">
        <tr>
          <td style="padding:{pad}px;font-family:{FONT};vertical-align:top;">
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
              <tr>
                <td width="32" style="vertical-align:top;">
                  <div style="width:26px;height:26px;border-radius:8px;background:{BLUE};background-image:linear-gradient(180deg,#3b9cff 0%,{BLUE} 100%);color:#fff;
                              font-size:10px;font-weight:700;text-align:center;line-height:26px;">{idx}</div>
                </td>
                <td style="vertical-align:top;padding:0 8px;">
                  <p style="margin:0;font-size:13px;font-weight:700;color:{TEXT};line-height:1.35;letter-spacing:-0.02em;">
                    {summary}
                  </p>
                </td>
                <td width="76" align="right" style="vertical-align:top;">
                  {_render_impeditivo_semaphore(impeditivo)}
                </td>
              </tr>
            </table>
            <p style="margin:10px 0 8px;">{_status_pill(status)}</p>
            <p style="margin:0 0 2px;font-size:11px;color:{GRAY};">
              <span style="font-weight:700;color:{TEXT};">Responsável</span>
            </p>
            <p style="margin:0 0 6px;font-size:13px;font-weight:600;color:{TEXT};">{dev}</p>
            {progress_html}
            {last_update_html}
          </td>
        </tr>
      </table>
    </td>"""


def _render_progress_block(progress: int, done: int | None = None, total: int | None = None) -> str:
    """Compatibilidade com email_template — delega ao hero."""
    return _render_progress_hero(progress, done, total, compact=True)


def _render_kpi_strip(
    counts: dict[str, int],
    *,
    entregues_mes: int = 0,
    entregues_total: int = 0,
) -> str:
    segment_styles = {
        "backlog": ("#515154", "#ffffff", SURFACE_2),
        "mapeamento": ("#4a90e2", "#eef8ff", "#dcefff"),
        "desenvolvimento": ("#0063d6", "#eef5ff", "#d6e8ff"),
        "entregues": ("#248a3d", "#eaf9ef", "#d4f0dc"),
    }
    segments = ""
    for key, title in KPI_BUCKETS:
        count = counts.get(key, 0)
        color, bg, active_bg = segment_styles.get(key, (BLUE, "#ffffff", SURFACE_2))
        title_html = _esc(title)
        if key == "entregues":
            count = entregues_mes
            title_html = (
                f'{_esc(title)} '
                f'<span style="display:inline-block;margin-left:2px;padding:1px 7px;border-radius:999px;'
                f"font-size:9px;font-weight:700;color:#248a3d;background:#d4f0dc;"
                f'border:1px solid #b8e6c6;vertical-align:middle;">Σ {entregues_total}</span>'
            )
        segments += f"""
        <td width="25%" style="padding:2px;vertical-align:top;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
                 style="background:{active_bg};border-radius:7px;min-height:{_KPI_SEGMENT_MIN_HEIGHT};height:100%;">
            <tr>
              <td style="padding:12px 10px;text-align:center;font-family:{FONT};vertical-align:middle;">
                <p style="margin:0;font-size:10px;font-weight:700;color:{GRAY};letter-spacing:0.05em;text-transform:uppercase;">{title_html}</p>
                <p style="margin:6px 0 0;font-size:30px;font-weight:800;color:{color};line-height:1;">{count}</p>
              </td>
            </tr>
          </table>
        </td>"""

    return f"""
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
           style="background:rgba(0,0,0,0.06);border:1px solid rgba(0,0,0,0.05);border-radius:9px;padding:2px;">
      <tr>{segments}</tr>
    </table>"""


def _render_mac_toolbar(generated_at: str, active_count: int, client_label: str) -> str:
    client = _esc(client_label) if client_label else "Cliente"
    return f"""
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
           style="border-bottom:1px solid {BORDER};background:rgba(255,255,255,0.55);">
      <tr>
        <td style="padding:12px 18px;font-family:{FONT};">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
            <tr>
              <td style="vertical-align:middle;">
                <p style="margin:0;font-size:15px;font-weight:700;letter-spacing:-0.02em;color:{TEXT};">Status Report</p>
                <p style="margin:3px 0 0;font-size:11px;color:{GRAY};">Governança Operacional — {client}</p>
              </td>
              <td align="right" style="vertical-align:middle;">
                <span style="display:inline-block;padding:5px 10px;border-radius:999px;font-size:11px;font-weight:600;background:#ffffff;border:1px solid {BORDER};color:#48484a;margin-left:6px;">{active_count} projetos ativos</span>
                <span style="display:inline-block;padding:5px 10px;border-radius:999px;font-size:11px;font-weight:600;background:#ffffff;border:1px solid {BORDER};color:#48484a;margin-left:6px;">{_esc(generated_at)}</span>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>"""


def _render_project_card(index: int, card: dict[str, Any]) -> str:
    return _render_visual_project_card(index, card, layout="grid")


def _render_project_rows(cards: list[dict[str, Any]]) -> str:
    if not cards:
        return f'<p style="font-family:{FONT};color:{GRAY};font-size:12px;">Nenhum projeto em andamento encontrado.</p>'
    metrics = _estimate_grid_card_height(cards)
    rows = ""
    for i in range(0, len(cards), 3):
        chunk = cards[i : i + 3]
        cells = "".join(
            _render_visual_project_card(
                i + j + 1,
                card,
                layout="grid",
                fixed_height=metrics,
            )
            for j, card in enumerate(chunk)
        )
        if len(chunk) < 3:
            cells += "<td></td>" * (3 - len(chunk))
        rows += f"<tr>{cells}</tr>"
    return f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">{rows}</table>'


def _icon_badge(symbol: str, bg: str, color: str, size: int = 28) -> str:
    return (
        f'<div style="width:{size}px;height:{size}px;border-radius:50%;background:{bg};color:{color};'
        f'font-size:{size - 12}px;font-weight:700;text-align:center;line-height:{size}px;flex-shrink:0;">'
        f"{symbol}</div>"
    )


def _render_highlight_item(text: str, *, symbol: str, bg: str, icon_bg: str, icon_color: str, border: str) -> str:
    return f"""
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
           style="margin-bottom:8px;background:{bg};border:1px solid {border};border-radius:10px;">
      <tr>
        <td width="40" align="center" style="padding:10px 0 10px 12px;vertical-align:top;">
          {_icon_badge(symbol, icon_bg, icon_color)}
        </td>
        <td style="padding:10px 12px 10px 8px;font-family:{FONT};vertical-align:middle;">
          <p style="margin:0;font-size:12px;line-height:1.45;color:{TEXT};">{_esc(text)}</p>
        </td>
      </tr>
    </table>"""


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
    <td width="50%" style="padding:8px;vertical-align:top;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
             style="background:#ffffff;border:1px solid {BORDER};border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
        <tr>
          <td style="padding:12px 14px;background:linear-gradient(180deg,#edf9f0 0%,#ffffff 100%);border-bottom:1px solid #d8f0de;font-family:{FONT};">
            <p style="margin:0;font-size:13px;font-weight:700;color:#1f7a3f;">Destaques da Semana</p>
          </td>
        </tr>
        <tr>
          <td style="padding:12px 12px 10px;">{items}</td>
        </tr>
      </table>
    </td>"""


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
    <td width="50%" style="padding:8px;vertical-align:top;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
             style="background:#ffffff;border:1px solid {BORDER};border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
        <tr>
          <td style="padding:12px 14px;background:linear-gradient(180deg,#fff9ec 0%,#ffffff 100%);border-bottom:1px solid #ffe3a8;font-family:{FONT};">
            <p style="margin:0;font-size:13px;font-weight:700;color:#9a6700;">Pontos de Atenção</p>
          </td>
        </tr>
        <tr>
          <td style="padding:12px 12px 10px;">{items}</td>
        </tr>
      </table>
    </td>"""


def build_status_report_html(
    *,
    report_title: str,
    generated_at: str,
    cards: list[dict[str, Any]],
    parent_label: str = "",
    client_label: str = "",
    weekly_highlights: dict[str, str] | None = None,
    attention_points: list[str] | None = None,
    entregues_mes: int = 0,
    entregues_total: int = 0,
) -> str:
    active_cards = _active_report_cards(cards)
    counts = _count_buckets(active_cards)
    kpi_html = _render_kpi_strip(
        counts,
        entregues_mes=entregues_mes,
        entregues_total=entregues_total,
    )

    report_client = client_label or parent_label

    highlights_html = _render_highlights_section(weekly_highlights)
    attention_html = _render_attention_section(attention_points)
    bottom_row = ""
    if highlights_html or attention_html:
        if not highlights_html:
            highlights_html = '<td width="50%" style="padding:8px;"></td>'
        if not attention_html:
            attention_html = '<td width="50%" style="padding:8px;"></td>'
        bottom_row = f"""
          <tr>
            <td style="padding-top:18px;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>{highlights_html}{attention_html}</tr>
              </table>
            </td>
          </tr>"""

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{_esc(report_title)}</title>
</head>
<body style="margin:0;padding:28px 20px;background:{BG_DESKTOP};font-family:{FONT};-webkit-font-smoothing:antialiased;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:1100px;margin:0 auto;">
    <tr>
      <td>
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
               style="background:{WINDOW_BG};border:1px solid rgba(255,255,255,0.65);border-radius:18px;box-shadow:{SHADOW};overflow:hidden;">
          <tr><td>{_render_mac_toolbar(generated_at, len(active_cards), report_client)}</td></tr>
          <tr>
            <td style="padding:16px 18px 20px;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr><td style="padding-bottom:14px;">{kpi_html}</td></tr>
                <tr>
                  <td>
                    <p style="margin:0 0 12px;font-size:11px;font-weight:700;letter-spacing:0.04em;text-transform:uppercase;color:{GRAY};">Projetos em andamento</p>
                    {_render_project_rows(active_cards)}
                  </td>
                </tr>
                {bottom_row}
              </table>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
  <script>
    (function () {{
      function equalizeCards() {{
        const cards = Array.from(document.querySelectorAll(".project-card-eq"));
        if (!cards.length) return;
        cards.forEach((card) => {{
          card.style.height = "auto";
          card.style.minHeight = "";
        }});
        const maxHeight = cards.reduce((max, card) => Math.max(max, card.offsetHeight), 0);
        if (!maxHeight) return;
        cards.forEach((card) => {{
          card.style.height = `${{maxHeight}}px`;
          card.style.minHeight = `${{maxHeight}}px`;
        }});
      }}
      window.addEventListener("load", equalizeCards);
      window.addEventListener("resize", equalizeCards);
      setTimeout(equalizeCards, 50);
    }})();
  </script>
</body>
</html>"""
