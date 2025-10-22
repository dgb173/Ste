"""
Panel Streamlit que replica la funcionalidad de Descarga_Todo usando data.json
y los scrapers originales.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from html import escape

import streamlit as st
import streamlit.components.v1 as components
from jinja2 import Environment, FileSystemLoader, TemplateNotFound, select_autoescape

PROJECT_ROOT = Path(__file__).resolve().parent
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(PROJECT_ROOT / ".playwright-browsers"))
sys.path.append(str(PROJECT_ROOT / "Descarga_Todo"))
sys.path.append(str(PROJECT_ROOT / "Descarga_Todo" / "muestra_sin_fallos"))

from modules.estudio_scraper import (  # type: ignore  # noqa: E402
    format_ah_as_decimal_string_of,
    generar_analisis_mercado_simplificado,
    obtener_datos_completos_partido,
    obtener_datos_preview_ligero,
)
from app_utils import normalize_handicap_to_half_bucket_str  # type: ignore  # noqa: E402
from Descarga_Todo.muestra_sin_fallos.app import app as flask_app  # type: ignore  # noqa: E402

st.set_page_config(layout="wide", page_title="Analisis de Partidos", page_icon=":soccer:")

flask_app.config["TESTING"] = True

DATA_FILE_CANDIDATES = [
    PROJECT_ROOT / "Descarga_Todo" / "data.json",
    PROJECT_ROOT / "data.json",
]
for candidate in DATA_FILE_CANDIDATES:
    if candidate.exists():
        DATA_FILE = candidate
        break
else:
    DATA_FILE = DATA_FILE_CANDIDATES[0]

SCRAPER_SCRIPT = PROJECT_ROOT / "Descarga_Todo" / "run_scraper.py"
TEMPLATES_DIR = PROJECT_ROOT / "Descarga_Todo" / "muestra_sin_fallos" / "templates"
FUTURE_FALLBACK = datetime.max.replace(tzinfo=timezone.utc)
PAST_FALLBACK = datetime.min.replace(tzinfo=timezone.utc)

JINJA_ENV: Optional[Environment] = None
if TEMPLATES_DIR.exists():
    JINJA_ENV = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )

HTML_WRAPPER_START = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<style>
    :root {
        color-scheme: light;
    }
    body { background-color: #f5f7fb; margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    .preview-wrapper { padding: 16px; }
    .match-header { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 12px; margin-bottom: 16px; align-items: baseline; }
    .match-header h2 { margin: 0; font-size: 1.4rem; color: #212529; }
    .match-meta { color: #495057; font-size: 0.95rem; }
    .card-grid { display: grid; gap: 14px; margin-bottom: 16px; }
    .grid-4 { grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); }
    .grid-3 { grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); }
    .grid-2 { grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); }
    .preview-card { background-color: #ffffff; border-radius: 10px; border: 1px solid #d9dde5; padding: 16px; box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08); height: 100%; }
    .preview-card h4, .preview-card h5, .preview-card h6 { margin: 0 0 8px 0; color: #0d6efd; font-weight: 600; font-size: 1.05rem; }
    .score { font-size: 1.8rem; font-weight: 700; text-align: center; margin: 6px 0; color: #212529; }
    .teams-line { text-align: center; font-weight: 500; margin-bottom: 6px; }
    .meta-line { font-size: 0.9rem; color: #495057; margin: 2px 0; }
    .meta-pill { display: inline-block; padding: 2px 8px; background-color: #f1f3f5; border-radius: 999px; font-size: 0.8rem; margin-right: 6px; margin-bottom: 4px; }
    .status-cover { font-weight: 600; }
    .status-cover.cover { color: #16a34a; }
    .status-cover.not-cover { color: #dc2626; }
    .status-cover.push { color: #2563eb; }
    .status-cover.neutral { color: #6b7280; }
    .analysis-text { font-size: 0.9rem; color: #374151; margin-top: 8px; }
    table.stat-table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 0.83rem; }
    table.stat-table thead th { background-color: #f1f3f5; color: #495057; padding: 6px; }
    table.stat-table tbody td { padding: 6px; border-top: 1px solid #e2e8f0; text-align: center; }
    table.stat-table tbody td:first-child { text-align: left; }
    table.stat-table tbody td:last-child { text-align: right; }
    .analysis-card { background: linear-gradient(135deg, #1e3a8a 0%, #0ea5e9 100%); color: white; border: none; box-shadow: 0 8px 18px rgba(14, 165, 233, 0.28); }
    .analysis-card h4 { color: white; }
    .analysis-card a { color: #f8fafc; text-decoration: underline; }
    .empty-hint { font-style: italic; color: #6b7280; }
</style>
</head>
<body>
<div class="preview-wrapper">
"""
HTML_WRAPPER_END = "</div></body></html>"

PW_FLAG = PROJECT_ROOT / ".playwright_ready"


GLOBAL_STYLES = """
<style>
div[data-testid="stAppViewContainer"] {
    background: linear-gradient(180deg, #eef2ff 0%, #f8fafc 60%);
}
div[data-testid="stHeader"] {
    background: transparent;
}
.match-grid {
    display: flex;
    flex-direction: column;
    gap: 18px;
    margin-top: 8px;
}
.match-card {
    background: #ffffff;
    border: 1px solid #dee4f3;
    border-radius: 14px;
    padding: 18px 22px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    box-shadow: 0 14px 30px rgba(15, 23, 42, 0.08);
}
.match-card__header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.85rem;
    font-weight: 600;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}
.match-card__teams {
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 1.1rem;
    font-weight: 600;
    color: #0f172a;
}
.match-card__vs {
    font-size: 0.9rem;
    color: #94a3b8;
}
.match-card__score {
    font-size: 1.8rem;
    font-weight: 700;
    color: #0f172a;
}
.match-card__tags {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 4px;
}
.match-card__tag {
    background: #0f172a;
    color: #ffffff;
    padding: 2px 10px;
    font-size: 0.75rem;
    border-radius: 999px;
    letter-spacing: 0.02em;
}
.match-card__meta {
    font-size: 0.85rem;
    color: #475569;
}
.match-actions {
    display: flex;
    flex-direction: column;
    gap: 8px;
}
.match-action-link {
    display: inline-flex;
    justify-content: center;
    align-items: center;
    padding: 8px 12px;
    border-radius: 8px;
    border: 1px solid #cbd5f5;
    color: #0f172a;
    font-weight: 600;
    text-decoration: none;
    background: #f1f5ff;
    transition: all 0.2s ease-in-out;
}
.match-action-link:hover {
    background: #e0e9ff;
    border-color: #94a3ff;
}
</style>
"""


def inject_global_styles() -> None:
    st.markdown(GLOBAL_STYLES, unsafe_allow_html=True)


def safe_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return escape(str(value))


def ensure_playwright() -> None:
    if PW_FLAG.exists():
        return
    cmd = [sys.executable, "-m", "playwright", "install", "chromium"]
    if sys.platform.startswith("linux"):
        cmd.insert(-1, "--with-deps")
    try:
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except Exception as exc:
        st.warning(f"No se pudo preparar Playwright automáticamente ({exc}). Si hay errores en scraping, instala los navegadores con `playwright install chromium`.")
    else:
        PW_FLAG.touch()

def parse_datetime(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        dt = datetime.fromisoformat(text)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        pass
    for fmt in ("%d/%m %H:%M", "%d-%m %H:%M"):
        try:
            dt = datetime.strptime(text, fmt)
            now = datetime.utcnow()
            return dt.replace(year=now.year, tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def prepare_matches(raw_matches: List[Any], mode: str) -> List[Dict[str, Any]]:
    prepared: List[Dict[str, Any]] = []
    seen: set[str] = set()
    now_utc = datetime.utcnow().replace(tzinfo=timezone.utc)
    for item in raw_matches:
        if not isinstance(item, dict):
            continue
        match = dict(item)
        match_id = str(match.get("id") or "").strip()
        if not match_id or match_id in seen:
            continue
        seen.add(match_id)
        dt = parse_datetime(
            match.get("time_obj")
            or match.get("match_datetime")
            or (
                f"{match.get('match_date')} {match.get('match_time')}"
                if match.get("match_date") and match.get("match_time")
                else None
            )
        )
        match["id"] = match_id
        match["handicap"] = str(match.get("handicap", "N/A"))
        match["goal_line"] = str(match.get("goal_line", "N/A"))
        match["time_utc"] = dt
        match["_time_sort"] = dt
        if not match.get("time") and dt:
            match["time"] = dt.strftime("%d/%m %H:%M") if mode == "finished" else dt.strftime("%H:%M")
        prepared.append(match)

    if mode == "upcoming":
        prepared = [m for m in prepared if not m.get("time_utc") or m["time_utc"] >= now_utc]
        prepared.sort(key=lambda m: (m.get("_time_sort") is None, m.get("_time_sort") or FUTURE_FALLBACK))
    else:
        prepared.sort(
            key=lambda m: (m.get("_time_sort") is None, m.get("_time_sort") or PAST_FALLBACK),
            reverse=True,
        )
    return prepared


@st.cache_data(show_spinner=False)
def load_data_from_file() -> Dict[str, List[Dict[str, Any]]]:
    if not DATA_FILE.exists():
        return {"upcoming_matches": [], "finished_matches": []}
    try:
        raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"upcoming_matches": [], "finished_matches": []}
    return {
        "upcoming_matches": prepare_matches(raw.get("upcoming_matches", []), "upcoming"),
        "finished_matches": prepare_matches(raw.get("finished_matches", []), "finished"),
    }


def extract_handicap_options(matches: List[Dict[str, Any]]) -> List[str]:
    options: set[str] = set()
    for match in matches:
        normalized = normalize_handicap_to_half_bucket_str(match.get("handicap"))
        if normalized is not None:
            options.add(normalized)
    return sorted(options, key=lambda val: float(val))


def ensure_filter_state(mode: str) -> None:
    filter_key = f"{mode}_handicap_filter_value"
    input_key = f"{mode}_handicap_filter_input"
    if filter_key not in st.session_state:
        st.session_state[filter_key] = ""
    if input_key not in st.session_state:
        st.session_state[input_key] = st.session_state[filter_key]


def apply_handicap_filter(matches: List[Dict[str, Any]], mode: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    filter_key = f"{mode}_handicap_filter_value"
    needle = st.session_state.get(filter_key, "").strip()
    if not needle:
        return matches, None
    normalized = normalize_handicap_to_half_bucket_str(needle)
    if normalized is None:
        return matches, f"No se reconoce el handicap '{needle}'."
    filtered = [
        match
        for match in matches
        if normalize_handicap_to_half_bucket_str(match.get("handicap")) == normalized
    ]
    return filtered, None


def format_cover_status(status: Optional[str]) -> str:
    if not status:
        return ""
    value = str(status).upper()
    if value == "CUBIERTO":
        return '<span class="status-cover cover">CUBIERTO</span>'
    if value == "NO CUBIERTO":
        return '<span class="status-cover not-cover">NO CUBIERTO</span>'
    if value in {"NULO", "PUSH"}:
        cls = "push" if value == "PUSH" else "neutral"
        return f'<span class="status-cover {cls}">{value}</span>'
    return f'<span class="status-cover neutral">{value}</span>'


def render_stats_table_html(rows: Optional[List[Dict[str, Any]]]) -> str:
    if not rows:
        return ""
    parts = [
        '<table class="stat-table">',
        "<thead><tr><th>Local</th><th>Estadística</th><th>Visitante</th></tr></thead>",
        "<tbody>",
    ]
    for row in rows:
        parts.append(
            "<tr>"
            f"<td>{row.get('home', '')}</td>"
            f"<td>{row.get('label', '')}</td>"
            f"<td>{row.get('away', '')}</td>"
            "</tr>"
        )
    parts.append("</tbody></table>")
    return "".join(parts)


def render_recent_card(title: str, block: Optional[Dict[str, Any]]) -> str:
    if not block:
        return ""
    score = block.get("score") or block.get("score_line")
    meta_bits = []
    if block.get("date"):
        meta_bits.append(f'<span class="meta-pill">{block["date"]}</span>')
    if block.get("ah"):
        meta_bits.append(f'<span class="meta-pill">AH: {block["ah"]}</span>')
    if block.get("ou"):
        meta_bits.append(f'<span class="meta-pill">O/U: {block["ou"]}</span>')
    cover_html = format_cover_status(block.get("cover_status"))
    analysis = block.get("analysis")
    teams = ""
    if block.get("home") and block.get("away"):
        teams = f'<div class="teams-line">{block["home"]} vs {block["away"]}</div>'
    html: List[str] = ['<div class="preview-card">', f"<h6>{title}</h6>"]
    if score:
        html.append(f'<div class="score">{score.replace(":", " - ")}</div>')
    if teams:
        html.append(teams)
    if meta_bits:
        html.append(f"<div>{''.join(meta_bits)}</div>")
    if cover_html:
        html.append(f'<div class="meta-line">Estado: {cover_html}</div>')
    stats_html = render_stats_table_html(block.get("stats_rows"))
    if stats_html:
        html.append(stats_html)
    if analysis:
        html.append(f'<div class="analysis-text">{analysis}</div>')
    html.append("</div>")
    return "".join(html)


def render_comparativa_card(
    card: Optional[Dict[str, Any]],
    fallback_title: str,
) -> str:
    title = fallback_title
    html: List[str] = ['<div class="preview-card">']
    if card:
        home_title = safe_text(card.get("title_home_name", ""))
        away_title = safe_text(card.get("title_away_name", ""))
        if home_title or away_title:
            title = f"{home_title or 'Local'} vs. Ult. rival de {away_title or 'Visitante'}"
        html.append(f"<h6>{title}</h6>")
        score = card.get("score")
        if score:
            safe_score = safe_text(score).replace(":", " - ")
            html.append(f'<div class="score">{safe_score}</div>')
        teams = ""
        home_team = card.get("home_team")
        away_team = card.get("away_team")
        if home_team and away_team:
            teams = f'<div class="teams-line">{safe_text(home_team)} vs {safe_text(away_team)}</div>'
        if teams:
            html.append(teams)
        pills = []
        if card.get("localia"):
            pills.append(f'<span class="meta-pill">Localia: {safe_text(card["localia"])}</span>')
        if card.get("ah"):
            pills.append(f'<span class="meta-pill">AH: {safe_text(card["ah"])}</span>')
        if card.get("ou"):
            pills.append(f'<span class="meta-pill">O/U: {safe_text(card["ou"])}</span>')
        if pills:
            html.append(f"<div>{''.join(pills)}</div>")
        cover_html = format_cover_status(card.get("cover_status"))
        if cover_html:
            html.append(f'<div class="meta-line">Estado: {cover_html}</div>')
        stats_html = render_stats_table_html(card.get("stats_rows"))
        if stats_html:
            html.append(stats_html)
        analysis = card.get("analysis")
        if analysis:
            html.append(f'<div class="analysis-text">{safe_text(analysis)}</div>')
    else:
        html.append(f"<h6>{title}</h6>")
        html.append('<p class="empty-hint">Sin datos disponibles para este cruce.</p>')
    html.append("</div>")
    return "".join(html)


def build_analysis_html(payload: Dict[str, Any], match: Dict[str, Any]) -> str:
    home = payload.get("home_team", match.get("home_team", "Local"))
    away = payload.get("away_team", match.get("away_team", "Visitante"))
    match_date = payload.get("match_date") or match.get("match_date") or ""
    match_time = payload.get("match_time") or match.get("match_time") or match.get("time", "")
    final_score = payload.get("final_score") or match.get("score")
    handicap = match.get("handicap") or payload.get("handicap", {}).get("ah_line")
    goal_line = match.get("goal_line")

    parts: List[str] = [HTML_WRAPPER_START]
    header = [
        '<div class="match-header">',
        f"<h2>{home} vs {away}</h2>",
        "<div class=\"match-meta\">",
    ]
    if match_date or match_time:
        header.append(f"{match_date} {match_time}".strip())
    if handicap and handicap != "N/A":
        header.append(f" · AH: {handicap}")
    if goal_line and goal_line != "N/A":
        header.append(f" · O/U: {goal_line}")
    if final_score:
        header.append(f" · Resultado: {final_score}")
    header.append("</div></div>")
    parts.append("".join(header))

    recent = payload.get("recent_indirect_full") or {}
    top_cards: List[str] = []
    top_cards.append(render_recent_card(f"Último {home} (Casa)", recent.get("last_home")))
    top_cards.append(render_recent_card(f"Último {away} (Fuera)", recent.get("last_away")))
    top_cards.append(render_recent_card("Rivales comunes", recent.get("h2h_col3") or recent.get("h2h_general")))
    simplified_html = payload.get("simplified_html")
    if simplified_html:
        top_cards.append(
            '<div class="preview-card analysis-card"><h6>📊 Análisis Mercado vs. H2H</h6>'
            f"{simplified_html}</div>"
        )
    top_cards = [card for card in top_cards if card]
    if top_cards:
        grid_class = "grid-4" if len(top_cards) >= 4 else "grid-3"
        parts.append(f'<div class="card-grid {grid_class}">{"".join(top_cards)}</div>')

    comparativas = payload.get("comparativas_indirectas") or {}
    left_title = f"{home} vs Ult. rival de {away}"
    right_title = f"{away} vs Ult. rival de {home}"
    left_card = render_comparativa_card(comparativas.get("left"), left_title)
    right_card = render_comparativa_card(comparativas.get("right"), right_title)
    parts.append(f'<div class="card-grid grid-2">{left_card}{right_card}</div>')

    if not top_cards and not simplified_html and all(
        "Sin datos disponibles" in card for card in (left_card, right_card)
    ):
        parts.append('<div class="preview-card"><p class="empty-hint">No se encontraron datos para este partido.</p></div>')

    parts.append(HTML_WRAPPER_END)
    return "".join(parts)


def build_light_preview_html(data: Dict[str, Any], match: Dict[str, Any]) -> str:
    home = data.get("home_team", match.get("home_team", "Local"))
    away = data.get("away_team", match.get("away_team", "Visitante"))
    parts: List[str] = [HTML_WRAPPER_START]
    parts.append(
        "<div class='match-header'>"
        f"<h2>{home} vs {away}</h2>"
        "<div class='match-meta'>Vista previa ligera (datos reducidos)</div>"
        "</div>"
    )
    parts.append('<div class="preview-card">')
    recent_form = data.get("recent_form") or {}
    parts.append("<h6>Resumen de forma reciente</h6>")
    parts.append(
        f"<div class='meta-line'>{home}: {recent_form.get('home', {}).get('wins', 0)} victorias / "
        f"{recent_form.get('home', {}).get('total', 0)} partidos</div>"
    )
    parts.append(
        f"<div class='meta-line'>{away}: {recent_form.get('away', {}).get('wins', 0)} victorias / "
        f"{recent_form.get('away', {}).get('total', 0)} partidos</div>"
    )
    recent_indirect = data.get("recent_indirect") or {}
    cards = [
        render_recent_card(f"Último {home} (Casa)", recent_indirect.get("last_home")),
        render_recent_card(f"Último {away} (Fuera)", recent_indirect.get("last_away")),
        render_recent_card("Rivales comunes", recent_indirect.get("h2h_col3")),
    ]
    cards = [card for card in cards if card]
    if cards:
        parts.append("</div>")
        parts.append(f'<div class="card-grid grid-3">{"".join(cards)}</div>')
    else:
        parts.append("<p class='empty-hint'>No hay más datos disponibles en la vista previa ligera.</p></div>")
    parts.append(HTML_WRAPPER_END)
    return "".join(parts)


@st.cache_data(show_spinner=False, ttl=600)
def get_analysis_payload(match_id: str) -> Dict[str, Any]:
    ensure_playwright()
    with flask_app.app_context():
        with flask_app.test_client() as client:
            response = client.get(f"/api/analisis/{match_id}")
    if response.status_code != 200:
        raise RuntimeError(f"El servidor devolvió {response.status_code}")
    data = response.get_json()
    if not isinstance(data, dict):
        raise RuntimeError("Respuesta inesperada del analizador.")
    return data


@st.cache_data(show_spinner=False, ttl=600)
def get_light_preview_data(match_id: str) -> Dict[str, Any]:
    ensure_playwright()
    return obtener_datos_preview_ligero(str(match_id))


def render_preview_for_match(match: Dict[str, Any]) -> None:
    match_id = str(match["id"])
    try:
        payload = get_analysis_payload(match_id)
        preview_html = build_analysis_html(payload, match)
        height = 900
    except Exception as exc:  # pragma: no cover - fallback defensivo
        st.warning(f"No se pudo generar el análisis avanzado ({exc}). Se muestra la vista previa ligera.")
        fallback = get_light_preview_data(match_id)
        if not fallback or "error" in fallback:
            st.error(f"No se pudo generar ningún análisis: {fallback.get('error', 'sin datos') if isinstance(fallback, dict) else 'Error desconocido'}")
            return
        preview_html = build_light_preview_html(fallback, match)
        height = 520
    components.html(preview_html, height=height, scrolling=True)


def render_filters(matches: List[Dict[str, Any]], mode: str) -> None:
    ensure_filter_state(mode)
    options = extract_handicap_options(matches)
    filter_key = f"{mode}_handicap_filter_value"
    input_key = f"{mode}_handicap_filter_input"
    expanded = bool(st.session_state.get(filter_key))
    with st.expander("Filtrar por handicap", expanded=expanded):
        st.write("Introduce handicaps separados por comas. Ejemplo: `0, 0.25, -0.5`.")
        st.text_input(
            "Valores de handicap",
            key=input_key,
            placeholder="Ej. 0.25, -0.75",
        )
        if options:
            st.caption("Valores detectados en la tabla: " + ", ".join(options))
        action_cols = st.columns(2)
        if action_cols[0].button("Aplicar filtro", key=f"{mode}_apply_filter"):
            st.session_state[filter_key] = st.session_state.get(input_key, "").strip()
            st.rerun()
        if action_cols[1].button("Limpiar filtro", key=f"{mode}_clear_filter"):
            st.session_state[filter_key] = ""
            st.session_state[input_key] = ""
            st.rerun()



def build_match_card_html(match: Dict[str, Any], mode: str) -> str:
    home = safe_text(match.get("home_team", "Local"))
    away = safe_text(match.get("away_team", "Visitante"))
    competition = safe_text(match.get("league") or match.get("competition") or match.get("country") or "Partido")
    kickoff_parts: List[str] = []
    for key in ("match_date", "date", "kickoff"):
        value = match.get(key)
        if value:
            kickoff_parts.append(safe_text(value))
            break
    time_value = match.get("time") or match.get("match_time")
    if time_value:
        kickoff_parts.append(safe_text(time_value))
    kickoff = " · ".join([token for token in kickoff_parts if token])
    handicap = safe_text(match.get("handicap", "N/A"))
    goal_line = safe_text(match.get("goal_line", "N/A"))
    match_id = safe_text(match.get("id"))
    score_block = ""
    if mode == "finished":
        score = safe_text(match.get("score", "-"))
        if score:
            score_block = f'<div class="match-card__score">{score.replace(":", " - ")}</div>'
    tags: List[str] = []
    if handicap and handicap.upper() != "N/A":
        tags.append(f'<span class="match-card__tag">AH {handicap}</span>')
    if goal_line and goal_line.upper() != "N/A":
        tags.append(f'<span class="match-card__tag">O/U {goal_line}</span>')
    if match_id:
        tags.append(f'<span class="match-card__tag">ID {match_id}</span>')
    league_round = match.get("round") or match.get("stage")
    if league_round:
        tags.append(f'<span class="match-card__tag">{safe_text(league_round)}</span>')
    meta_line = ""
    venue = match.get("venue") or match.get("stadium")
    if venue:
        meta_line = f'<div class="match-card__meta">Sede: {safe_text(venue)}</div>'
    html_parts = [
        '<div class="match-card">',
        '<div class="match-card__header">',
        f"<span>{competition}</span>",
        f"<span>{kickoff or 'Horario por confirmar'}</span>",
        "</div>",
        '<div class="match-card__teams">',
        f'<span class="match-card__team">{home}</span>',
        '<span class="match-card__vs">vs</span>',
        f'<span class="match-card__team">{away}</span>',
        "</div>",
    ]
    if score_block:
        html_parts.append(score_block)
    if tags:
        html_parts.append(f'<div class="match-card__tags">{"".join(tags)}</div>')
    if meta_line:
        html_parts.append(meta_line)
    html_parts.append("</div>")
    return "".join(html_parts)

def render_actions(container, match: Dict[str, Any], mode: str, idx: int) -> None:
    match_id = str(match["id"])
    with container:
        st.markdown(
            f'<a class="match-action-link" href="?estudio_id={match_id}" target="_blank" title="Abrir estudio completo">Estudio completo</a>',
            unsafe_allow_html=True,
        )
        if st.button(
            "Vista previa",
            key=f"preview_button_{mode}_{match_id}_{idx}",
            help="Mostrar vista previa dentro del panel",
            use_container_width=True,
        ):
            current = st.session_state.get("active_preview_id")
            st.session_state["active_preview_id"] = None if current == match_id else match_id
            st.rerun()

def render_mode_section(matches: List[Dict[str, Any]], mode: str) -> None:
    render_filters(matches, mode)
    filtered_matches, filter_error = apply_handicap_filter(matches, mode)
    if filter_error:
        st.warning(filter_error)
    total = len(matches)
    count = len(filtered_matches)
    st.write(f"Mostrando {count} de {total} partidos")

    if count == 0:
        st.info("No se encontraron partidos con los criterios seleccionados.")
        return

    st.markdown('<div class="match-grid">', unsafe_allow_html=True)
    for idx, match in enumerate(filtered_matches):
        with st.container():
            card_col, actions_col = st.columns([4, 1])
            card_col.markdown(build_match_card_html(match, mode), unsafe_allow_html=True)
            with actions_col:
                st.markdown('<div class="match-actions">', unsafe_allow_html=True)
                render_actions(st.container(), match, mode, idx)
                st.markdown('</div>', unsafe_allow_html=True)
        if st.session_state.get("active_preview_id") == match["id"]:
            with st.container():
                render_preview_for_match(match)
        st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def render_manual_analysis_form() -> None:
    st.divider()
    st.subheader("Analizar partido finalizado por ID")
    with st.form("manual_analysis_form"):
        match_id = st.text_input("ID del partido", key="manual_analysis_id")
        submitted = st.form_submit_button("Abrir estudio")
        if submitted:
            cleaned = match_id.strip()
            if not cleaned:
                st.warning("Introduce un ID válido.")
            else:
                st.query_params.update({"estudio_id": cleaned})
                st.rerun()


def run_main_page() -> None:
    global DATA_FILE
    data = load_data_from_file()
    upcoming = data.get("upcoming_matches", [])
    finished = data.get("finished_matches", [])

    header_col, action_col = st.columns([3, 1])
    with header_col:
        st.title("Panel Descarga_Todo en Streamlit")
        st.caption("Monitoriza los partidos y actualiza el dataset original cuando lo necesites.")
    with action_col:
        trigger_scraper = st.button("Actualizar datos", key="scraper_button", use_container_width=True)

    if trigger_scraper:
        with st.spinner("Ejecutando run_scraper.py..."):
            ensure_playwright()
            try:
                result = subprocess.run(
                    [sys.executable, str(SCRAPER_SCRIPT)],
                    capture_output=True,
                    text=True,
                    check=True,
                    cwd=str(SCRAPER_SCRIPT.parent),
                )
            except subprocess.CalledProcessError as exc:
                st.error("El scraping falló. Revisa la salida mostrada.")
                if exc.stdout:
                    st.text_area("Salida del scraping", exc.stdout, height=220)
                if exc.stderr:
                    st.text_area("Errores", exc.stderr, height=220)
            else:
                st.success("Scraping completado. data.json actualizado.")
                if result.stdout.strip():
                    st.text_area("Salida del scraping", result.stdout, height=200)
                desc_data = SCRAPER_SCRIPT.parent / "data.json"
                root_data = PROJECT_ROOT / "data.json"
                if desc_data.exists():
                    DATA_FILE = desc_data
                    try:
                        shutil.copy2(desc_data, root_data)
                    except Exception as copy_exc:
                        st.warning(f"No se pudo sincronizar data.json en la raíz: {copy_exc}")
        st.cache_data.clear()
        st.rerun()

    kpi_cols = st.columns(3)
    kpi_cols[0].metric("Próximos", len(upcoming))
    kpi_cols[1].metric("Finalizados", len(finished))
    try:
        updated_dt = datetime.fromtimestamp(DATA_FILE.stat().st_mtime).astimezone()
        kpi_cols[2].metric("Última actualización", updated_dt.strftime("%d/%m %H:%M"))
    except FileNotFoundError:
        kpi_cols[2].metric("Última actualización", "Sin datos")

    st.divider()

    tab_upcoming, tab_finished = st.tabs([
        f"Próximos partidos ({len(upcoming)})",
        f"Resultados finalizados ({len(finished)})",
    ])
    with tab_upcoming:
        render_mode_section(upcoming, "upcoming")
    with tab_finished:
        render_mode_section(finished, "finished")
        render_manual_analysis_form()

def build_estudio_html(datos: Dict[str, Any]) -> Optional[str]:
    if JINJA_ENV is None:
        return None
    try:
        template = JINJA_ENV.get_template("estudio.html")
    except TemplateNotFound:
        return None

    analisis_html = ""
    try:
        main_odds = datos.get("main_match_odds_data")
        h2h_data = datos.get("h2h_data")
        home_name = datos.get("home_name")
        away_name = datos.get("away_name")
        if main_odds and h2h_data and home_name and away_name:
            analisis_html = generar_analisis_mercado_simplificado(main_odds, h2h_data, home_name, away_name)
    except Exception as exc:  # pragma: no cover - defensivo
        print(f"[streamlit_app] Error al generar analisis simplificado: {exc}")

    try:
        return template.render(
            data=datos,
            format_ah=format_ah_as_decimal_string_of,
            analisis_simplificado_html=analisis_html or "",
        )
    except Exception as exc:  # pragma: no cover - defensivo
        print(f"[streamlit_app] Error al renderizar plantilla estudio: {exc}")
        return None


def render_estudio_view(match_id: str) -> None:

    with st.spinner("Cargando estudio completo..."):
        data = obtener_datos_completos_partido(match_id)

    if not data or "error" in data:
        st.error(data.get("error", "No se pudo cargar el estudio."))
        if st.button("Regresar al panel", key="back_button_error"):
            st.query_params.clear()
            st.session_state["active_preview_id"] = None
            st.rerun()
        return

    estudio_html = build_estudio_html(data)
    if estudio_html:
        components.html(estudio_html, height=1300, scrolling=True)
    else:
        st.info("No fue posible renderizar la plantilla completa. Se muestran los datos sin formato.")
        st.json(data)

    if st.button("Volver al panel principal", key="back_button_bottom"):
        st.query_params.clear()
        st.session_state["active_preview_id"] = None
        st.rerun()


def main() -> None:
    inject_global_styles()
    if "active_preview_id" not in st.session_state:
        st.session_state["active_preview_id"] = None

    query_params = st.query_params
    raw_estudio = query_params.get("estudio_id")
    if isinstance(raw_estudio, list):
        estudio_id = raw_estudio[0] if raw_estudio else None
    else:
        estudio_id = raw_estudio

    if estudio_id:
        render_estudio_view(str(estudio_id))
    else:
        run_main_page()


main()






