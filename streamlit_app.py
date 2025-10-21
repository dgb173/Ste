'''
# streamlit_app.py - Versión de la aplicación con Streamlit (CORREGIDA)
'''
import streamlit as st
import streamlit.components.v1 as components
import json
import os
import re
import math
import subprocess

# --- Importar la lógica de scraping ---
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'muestra_sin_fallos'))
from modules.estudio_scraper import obtener_datos_preview_ligero

# --- Configuración de la página ---
st.set_page_config(layout="wide", page_title="Análisis de Partidos")

# --- Estilos CSS (para inyectar en el HTML) ---
# Se inyectará dentro del body del componente HTML para asegurar que se aplique
HTML_WRAPPER_START = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body { background-color: #f8f9fa !important; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; }
        .team-name { font-weight: 500; }
        .match-time { font-style: italic; color: #6c757d; }
        .odds-badge { font-size: 0.9em; padding: 0.3em 0.6em; border-radius: 0.25rem; }
        .handicap { background-color: #17a2b8; color: white; }
        .goal-line { background-color: #28a745; color: white; }
        .study-link { font-size: 1.5em; text-decoration: none; color: #343a40; }
        .study-link:hover { color: #007bff; }
        .card { margin-bottom: 1rem; }
        .stat-table { width: 100%; margin-top: 8px; }
        .stat-table td { padding: 4px 8px; text-align: center; }
        .stat-table .stat-label { font-weight: 500; }
        .stat-table .stat-value-home { font-weight: bold; text-align: left; }
        .stat-table .stat-value-away { font-weight: bold; text-align: right; }
        .home-color { color: #007bff; font-weight: bold; }
        .away-color { color: #fd7e14; font-weight: bold; }
        .ah-value { font-weight: bold; color: #6f42c1; }
    </style>
</head>
<body>
'''
HTML_WRAPPER_END = '''
</body>
</html>
'''

# --- Lógica de Normalización ---
def normalize_handicap_to_half_bucket_str(text: str):
    def _parse_number_clean(s: str):
        if s is None: return None
        txt = str(s).strip().replace('−', '-').replace(',', '.').replace('+', '').replace(' ', '')
        m = re.search(r"^[+-]?\d+(?:\.\d+)?$", txt)
        if m: 
            try: return float(m.group(0))
            except ValueError: return None
        return None
    def _parse_handicap_to_float(text: str):
        if text is None: return None
        t = str(text).strip()
        if '/' in t:
            parts = [p for p in re.split(r"/", t) if p]
            nums = [_parse_number_clean(p) for p in parts]
            if any(n is None for n in nums) or not nums: return None
            return sum(nums) / len(nums)
        return _parse_number_clean(t.replace('+', ''))
    def _bucket_to_half(value: float):
        if value is None: return None
        if value == 0: return 0.0
        sign = -1.0 if value < 0 else 1.0
        av = abs(value)
        base = math.floor(av + 1e-9)
        frac = av - base
        def close(a, b): return abs(a - b) < 1e-6
        if close(frac, 0.0): bucket = float(base)
        elif close(frac, 0.5) or close(frac, 0.25) or close(frac, 0.75): bucket = base + 0.5
        else:
            bucket = round(av * 2) / 2.0
            f = bucket - math.floor(bucket)
            if close(f, 0.0) and (abs(av - (math.floor(bucket) + 0.25)) < 0.26 or abs(av - (math.floor(bucket) + 0.75)) < 0.26):
                bucket = math.floor(bucket) + 0.5
        return sign * bucket
    v = _parse_handicap_to_float(text)
    if v is None: return None
    b = _bucket_to_half(v)
    if b is None: return None
    return f"{b:.1f}"

# --- Carga de Datos ---
DATA_FILE = 'data.json'
@st.cache_data
def load_data_from_file():
    if not os.path.exists(DATA_FILE):
        return {"upcoming_matches": [], "finished_matches": []}
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {"upcoming_matches": [], "finished_matches": []}

# --- Funciones de renderizado ---
def display_matches_table_component(matches, page_mode):
    header_cols = ['Hora', 'Partido']
    if page_mode == 'finished': header_cols.append('Resultado')
    header_cols.extend(['Hándicap', 'Línea de Goles', 'Análisis'])
    header_html = "".join(f"<th>{col}</th>" for col in header_cols)
    rows_html = ""
    if not matches:
        colspan = len(header_cols)
        rows_html = f'<tr><td colspan="{colspan}" class="text-center p-5">No se encontraron partidos con los filtros seleccionados.</td></tr>'
    else:
        for m in matches:
            score_cell = f'<td class="align-middle"><span class="badge bg-dark">{m.get("score", "N/A")}</span></td>' if page_mode == 'finished' else ''
            rows_html += f'''
            <tr>
                <td class="align-middle match-time">{m.get("time", "")}</td>
                <td class="align-middle text-start"><span class="team-name">{m.get("home_team", "N/A")}</span> <small>vs</small> <span class="team-name">{m.get("away_team", "N/A")}</span></td>
                {score_cell}
                <td class="align-middle text-center"><span class="badge odds-badge handicap">{m.get("handicap", "N/A")}</span></td>
                <td class="align-middle text-center"><span class="badge odds-badge goal-line">{m.get("goal_line", "N/A")}</span></td>
                <td class="align-middle text-center"><a href="#" class="study-link" title="Use la sección de Vista Previa Rápida de abajo"><i class="fa-solid fa-chart-simple"></i></a></td>
            </tr>
            '''
    table_html = f'''
    <div class="table-responsive">
        <table class="table table-striped table-bordered text-center">
            <thead><tr>{header_html}</tr></thead>
            <tbody>{rows_html}</tbody>
        </table>
    </div>
    '''
    # Envolvemos la tabla en el HTML completo y la renderizamos con components.html
    full_html = f"{HTML_WRAPPER_START}{table_html}{HTML_WRAPPER_END}"
    components.html(full_html, height=400, scrolling=True)

def display_preview_data_component(data):
    home_team = data.get('home_team', 'Local')
    away_team = data.get('away_team', 'Visitante')
    def render_stats_table(rows):
        if not rows: return ''
        tr = ''.join(f'<tr><td class="stat-value-home">{r.get("home",'-')}</td><td class="stat-label">{r.get("label",'-')}</td><td class="stat-value-away">{r.get("away",'-')}</td></tr>' for r in rows)
        return f'<table class="stat-table"><tbody>{tr}</tbody></table>'
    def render_card(title, match_data, card_class=""):
        if not match_data: return ""
        score = match_data.get('score', '-').replace(':', ' - ')
        date = match_data.get('date', '-');
        if date and len(date) > 10: date = date[:10]
        home_card_team = match_data.get('home', '-'); away_card_team = match_data.get('away', '-')
        stats_html = render_stats_table(match_data.get('stats_rows', []))
        return f'''
        <div class="col-md-4 mb-3">
            <div class="card h-100 {card_class}">
                <div class="card-header"><h6 class="mb-0"><strong>{title}</strong></h6></div>
                <div class="card-body">
                    <p class="text-center"><font size="5">{score}</font></p>
                    <p class="text-center"><span class="home-color">{home_card_team}</span> vs <span class="away-color">{away_card_team}</span></p>
                    <p class="mb-1"><span class="text-muted small">{date}</span></p>
                    <p class="mb-1"><strong>AH:</strong> <span class="ah-value">{match_data.get("ah", "-")}</span></p>
                    {stats_html}
                </div>
            </div>
        </div>
        '''
    ri = data.get('recent_indirect', {})
    card1_html = render_card(f"Último {home_team} (Casa)", ri.get('last_home'))
    card2_html = render_card(f"Último {away_team} (Fuera)", ri.get('last_away'), "bg-light")
    card3_html = render_card("Rivales Comunes (H2H)", ri.get('h2h_col3'))
    cards_html = f'<div class="row">{card1_html}{card2_html}{card3_html}</div>'
    full_html = f"{HTML_WRAPPER_START}{cards_html}{HTML_WRAPPER_END}"
    components.html(full_html, height=350)

# --- Lógica Principal de la App ---
st.title("Visor de Partidos")
if st.button("Actualizar Datos (Ejecutar Scraper)"):
    with st.spinner("Iniciando el proceso de scraping... Esto puede tardar unos minutos."):
        try:
            process = subprocess.run(["py", "run_scraper.py"], capture_output=True, text=True, check=True, encoding='utf-8')
            st.success("¡Scraping completado con éxito!")
            with st.expander("Ver registro del scraper"): st.code(process.stdout)
            st.cache_data.clear(); st.rerun()
        except FileNotFoundError: st.error("Error: No se encontró el comando 'py'. Asegúrate de que Python esté instalado y en el PATH.")
        except subprocess.CalledProcessError as e:
            st.error(f"Error durante la ejecución del scraper (código de salida {e.returncode}):");
            with st.expander("Ver detalles del error"): st.code(e.stderr)
        except Exception as e: st.error(f"Ocurrió un error inesperado: {e}")

all_data = load_data_from_file()

def run_app_for_mode(matches, mode):
    if not matches:
        st.warning(f"No se encontraron partidos en la sección de {mode}."); return

    st.subheader("Filtros")
    col1, col2 = st.columns(2)
    handicap_options = sorted({normalize_handicap_to_half_bucket_str(m.get('handicap')) for m in matches if m and normalize_handicap_to_half_bucket_str(m.get('handicap')) is not None}, key=lambda x: float(x))
    handicap_options.insert(0, "Todos")
    selected_handicap = col1.selectbox("Filtrar por hándicap", options=handicap_options, key=f"handicap_{mode}")
    goal_line_options = sorted({str(m.get('goal_line')) for m in matches if m and m.get('goal_line') is not None})
    goal_line_options.insert(0, "Todos")
    selected_goal_line = col2.selectbox("Filtrar por línea de goles", options=goal_line_options, key=f"goal_line_{mode}")

    filtered_matches = matches
    if selected_handicap != "Todos":
        filtered_matches = [m for m in filtered_matches if normalize_handicap_to_half_bucket_str(m.get('handicap')) == selected_handicap]
    if selected_goal_line != "Todos":
        filtered_matches = [m for m in filtered_matches if str(m.get('goal_line')) == selected_goal_line]

    display_matches_table_component(filtered_matches, page_mode=mode)

    st.markdown("---")
    st.subheader("🔍 Vista Previa Rápida")
    if not filtered_matches:
        st.info("No hay partidos para mostrar en la vista previa.")
    else:
        match_options = {f"{m['home_team']} vs {m['away_team']} ({m['time']})": m['id'] for m in filtered_matches}
        selected_match_label = st.selectbox("Selecciona un partido para ver su análisis:", options=["-"] + list(match_options.keys()), key=f"preview_select_{mode}")
        if selected_match_label != "-":
            match_id = match_options[selected_match_label]
            with st.spinner("Obteniendo análisis detallado..."):
                preview_data = obtener_datos_preview_ligero(match_id)
                if preview_data and "error" not in preview_data:
                    display_preview_data_component(preview_data)
                elif preview_data and "error" in preview_data:
                    st.error(f"Error al obtener el análisis: {preview_data['error']}")
                else:
                    st.error("Ocurrió un error desconocido al obtener el análisis.")

# --- Pestañas de Navegación ---
tabs = st.tabs([f"Próximos Partidos ({len(all_data.get('upcoming_matches', []))})", f"Resultados Finalizados ({len(all_data.get('finished_matches', []))})"])
with tabs[0]:
    st.header("Próximos Partidos")
    run_app_for_mode(all_data.get('upcoming_matches', []), mode='upcoming')
with tabs[1]:
    st.header("Resultados Finalizados")
    run_app_for_mode(all_data.get('finished_matches', []), mode='finished')