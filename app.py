import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import io

# ==========================================
# CONFIGURAZIONE PAGINA
# ==========================================
st.set_page_config(page_title="Material Data Hub", layout="wide", initial_sidebar_state="expanded")

# Stile custom minimalista (nasconde header superflui di Streamlit per pulizia visiva)
hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# ==========================================
# DATABASE MATERIALI FITTIZIO (Simulazione)
# ==========================================
# Struttura ottimizzata per valvole, componenti meccanici e o-ring
MATERIAL_DB = {
    "Acciai Austenitici": {
        "AISI 316L (Corpo Valvola a Y)": {
            "Codice": "MAT-VAL-316L",
            "Norma": "ASTM A182 / EN 1.4404",
            "Densita_kgm3": 7990,
            "Poisson": 0.3,
            "Temperature_C": [20, 100, 200, 300, 400],
            "Snervamento_MPa": [170, 145, 118, 105, 95],
            "Rottura_MPa": [485, 450, 400, 380, 370],
            "Modulo_E_GPa": [193, 189, 182, 175, 168]
        }
    },
    "Acciai al Carbonio": {
        "ASTM A105 (Flange/Raccordi)": {
            "Codice": "MAT-FLG-A105",
            "Norma": "ASTM A105 / EN 1.0460",
            "Densita_kgm3": 7850,
            "Poisson": 0.29,
            "Temperature_C": [20, 100, 200, 300, 400],
            "Snervamento_MPa": [250, 220, 195, 170, 140],
            "Rottura_MPa": [485, 470, 450, 420, 390],
            "Modulo_E_GPa": [210, 205, 195, 185, 175]
        }
    },
    "Elastomeri": {
        "FKM - Viton 75 Shore A (O-Ring)": {
            "Codice": "MAT-ORG-FKM75",
            "Norma": "ASTM D1418",
            "Densita_kgm3": 1850,
            "Poisson": 0.49,
            "Temperature_C": [20, 50, 100, 150, 200], # Range termico limitato per elastomeri
            "Snervamento_MPa": [14, 11, 8, 5, 3],     # Approssimato a stress al 100% di allungamento
            "Rottura_MPa": [18, 15, 12, 8, 5],
            "Modulo_E_GPa": [0.008, 0.007, 0.005, 0.003, 0.002]
        }
    }
}

# ==========================================
# LOGICA DI CALCOLO (Interpolazione Lineare)
# ==========================================
def linear_interpolation(x, x_values, y_values):
    """
    Applica l'interpolazione lineare y = y1 + ((y2 - y1) / (x2 - x1)) * (x - x1).
    Gestisce automaticamente l'extrapolazione limitando ai valori minimi/massimi (clamping).
    """
    # Clamping se fuori range
    if x <= x_values[0]: return y_values[0]
    if x >= x_values[-1]: return y_values[-1]
    
    # Ricerca dell'intervallo [x1, x2]
    for i in range(len(x_values) - 1):
        if x_values[i] <= x <= x_values[i+1]:
            x1, x2 = x_values[i], x_values[i+1]
            y1, y2 = y_values[i], y_values[i+1]
            # Formula matematica di interpolazione lineare
            y = y1 + ((y2 - y1) / (x2 - x1)) * (x - x1)
            return y
    return None

# ==========================================
# GENERAZIONE CURVE (Sforzo-Deformazione)
# ==========================================
def generate_stress_strain_curve(E_gpa, Sy_mpa, Su_mpa):
    """Genera una curva ingegneristica sintetica per visualizzazione."""
    E_mpa = E_gpa * 1000
    if E_mpa == 0: return [0], [0]
    
    # Fase Elastica (Legge di Hooke)
    strain_yield = Sy_mpa / E_mpa
    strains_el = np.linspace(0, strain_yield, 20)
    stresses_el = strains_el * E_mpa
    
    # Fase Plastica (approssimazione parabolica semplice fino a deformazione arbitraria per rottura)
    strain_ultimate = strain_yield + 0.15 
    strains_pl = np.linspace(strain_yield, strain_ultimate, 30)
    stresses_pl = Sy_mpa + (Su_mpa - Sy_mpa) * np.sqrt((strains_pl - strain_yield) / (strain_ultimate - strain_yield))
    
    return np.concatenate((strains_el, strains_pl)), np.concatenate((stresses_el, stresses_pl))

# ==========================================
# SEZIONE 1: MOTORE DI RICERCA (Sidebar)
# ==========================================
st.sidebar.title("🔍 Motore di Ricerca")
st.sidebar.markdown("---")

family_list = list(MATERIAL_DB.keys())
selected_family = st.sidebar.selectbox("Famiglia Materiale", family_list)

material_list = list(MATERIAL_DB[selected_family].keys())
selected_material = st.sidebar.selectbox("Materiale Specifico", material_list)

mat_data = MATERIAL_DB[selected_family][selected_material]
max_temp = mat_data["Temperature_C"][-1]

st.sidebar.markdown("### Condizioni Operative")
temp_op = st.sidebar.number_input(
    f"Temperatura Operativa (°C) [Max {max_temp}°C]", 
    value=20, min_value=-50, max_value=int(max_temp), step=1
)

# Calcolo dati nominali e interpolati
t_arr = mat_data["Temperature_C"]
sy_arr = mat_data["Snervamento_MPa"]
su_arr = mat_data["Rottura_MPa"]
e_arr = mat_data["Modulo_E_GPa"]

sy_op = linear_interpolation(temp_op, t_arr, sy_arr)
su_op = linear_interpolation(temp_op, t_arr, su_arr)
e_op = linear_interpolation(temp_op, t_arr, e_arr)

# ==========================================
# SEZIONE 2: OUTPUT NUMERICO (Area Centrale)
# ==========================================
st.title("⚙️ Material Data Hub")
st.markdown("Dashboard di validazione proprietà termo-meccaniche per calcolo FEM e anagrafica PDM.")

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("Anagrafica Componente")
    st.write(f"**Codice PDM:** `{mat_data['Codice']}`")
    st.write(f"**Norma di Riferimento:** {mat_data['Norma']}")
    st.write(f"**Densità:** {mat_data['Densita_kgm3']} kg/m³")
    st.write(f"**Coef. di Poisson (ν):** {mat_data['Poisson']}")

with col2:
    st.subheader("Comparazione Proprietà (20°C vs Operativa)")
    # Tabella di confronto rigorosa
    df_compare = pd.DataFrame({
        "Proprietà": ["Snervamento / R_{p0.2} (MPa)", "Carico di Rottura / R_m (MPa)", "Modulo di Young (GPa)"],
        "Nominale (20°C)": [sy_arr[0], su_arr[0], e_arr[0]],
        f"Operativa ({temp_op}°C)": [round(sy_op, 1), round(su_op, 1), round(e_op, 3)]
    })
    st.dataframe(df_compare, use_container_width=True, hide_index=True)

st.markdown("---")

# ==========================================
# SEZIONE 3: VISUALIZZAZIONE GRAFICA
# ==========================================
st.subheader("Analisi Grafica del Comportamento")
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    # Grafico 1: Sforzo Deformazione
    strains, stresses = generate_stress_strain_curve(e_op, sy_op, su_op)
    fig_ss = go.Figure()
    fig_ss.add_trace(go.Scatter(x=strains, y=stresses, mode='lines', name=f'Curva a {temp_op}°C', line=dict(color='blue', width=2)))
    fig_ss.update_layout(
        title=f"Curva Sforzo-Deformazione (Stimata a {temp_op}°C)",
        xaxis_title="Deformazione (ε)",
        yaxis_title="Sforzo (σ) [MPa]",
        template="plotly_white",
        margin=dict(l=40, r=40, t=40, b=40)
    )
    st.plotly_chart(fig_ss, use_container_width=True)

with chart_col2:
    # Grafico 2: Decadimento Termico
    fig_deg = go.Figure()
    fig_deg.add_trace(go.Scatter(x=t_arr, y=sy_arr, mode='lines+markers', name='Snervamento (MPa)', yaxis='y1'))
    fig_deg.add_trace(go.Scatter(x=t_arr, y=e_arr, mode='lines+markers', name='Modulo Young (GPa)', yaxis='y2', line=dict(dash='dot')))
    
    # Linea indicatore Temperatura Operativa
    fig_deg.add_vline(x=temp_op, line_width=1, line_dash="dash", line_color="red", annotation_text=f"T_op ({temp_op}°C)")
    
    fig_deg.update_layout(
        title="Curve di Degrado Termico",
        xaxis_title="Temperatura (°C)",
        yaxis=dict(title="Snervamento (MPa)", side='left'),
        yaxis2=dict(title="Modulo Young (GPa)", side='right', overlaying='y'),
        template="plotly_white",
        margin=dict(l=40, r=40, t=40, b=40),
        legend=dict(x=0.01, y=0.01)
    )
    st.plotly_chart(fig_deg, use_container_width=True)

# ==========================================
# SEZIONE 4: MODULO DI ESPORTAZIONE
# ==========================================
st.sidebar.markdown("---")
st.sidebar.markdown("### Esportazione PDM")

# Prepara i dati in un formato tabellare piatto per l'export
export_data = {
    "Codice": mat_data["Codice"],
    "Materiale": selected_material,
    "Norma": mat_data["Norma"],
    "Temperatura_C": temp_op,
    "Snervamento_MPa": round(sy_op, 2),
    "Rottura_MPa": round(su_op, 2),
    "Modulo_E_GPa": round(e_op, 3),
    "Densita": mat_data["Densita_kgm3"],
    "Poisson": mat_data["Poisson"]
}

df_export = pd.DataFrame([export_data])

# Generazione file Excel in memoria
buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
    df_export.to_excel(writer, index=False, sheet_name="Export_PDM")
    
    # Auto-adattamento larghezza colonne per una visualizzazione pulita del file
    worksheet = writer.sheets['Export_PDM']
    for idx, col in enumerate(df_export.columns):
        series = df_export[col]
        max_len = max(series.astype(str).map(len).max(), len(str(col))) + 2
        worksheet.set_column(idx, idx, max_len)

st.sidebar.download_button(
    label="📥 Esporta Dati Materiale (Excel)",
    data=buffer.getvalue(),
    file_name=f"Anagrafica_{mat_data['Codice']}_{temp_op}C.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    help="Genera un file .xlsx con colonne standardizzate per il caricamento su Fogli Google o importazione massiva PDM."
)\