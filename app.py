"""
Aplicación web interactiva para el análisis de mortalidad en Colombia (2019)
Actividad 4 — Maestría en Inteligencia Artificial, Universidad de La Salle
Autor: Martín Gracia Socha
"""

import json
import os

import dash
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import dash_table, dcc, html
from dash.dependencies import Input, Output

# ─────────────────────────────────────────────────────────────────────────────
# CARGA Y PREPROCESAMIENTO DE DATOS
# ─────────────────────────────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")


def cargar_datos():
    """Carga, une y preprocesa todos los conjuntos de datos."""

    # 1. Datos de mortalidad
    df = pd.read_excel(os.path.join(DATA_DIR, "NoFetal2019.xlsx"))

    # 2. División político-administrativa
    div = pd.read_excel(os.path.join(DATA_DIR, "Divipola.xlsx"))
    div = div[["COD_DANE", "COD_DEPARTAMENTO", "DEPARTAMENTO", "MUNICIPIO"]]

    # 3. Códigos de causa de muerte (CIE-10)
    cod4 = pd.read_excel(
        os.path.join(DATA_DIR, "CodigosDeMuerte.xlsx"),
        skiprows=8,
        header=0,
        usecols=[4, 5],
    )
    cod4.columns = ["COD_MUERTE", "DESCRIPCION"]
    cod4 = cod4.dropna(subset=["COD_MUERTE"]).copy()
    cod4["COD_MUERTE"] = cod4["COD_MUERTE"].astype(str).str.strip()

    # Códigos de 3 caracteres (para los que no tienen descripción a 4)
    cod3 = pd.read_excel(
        os.path.join(DATA_DIR, "CodigosDeMuerte.xlsx"),
        skiprows=8,
        header=0,
        usecols=[2, 3],
    )
    cod3.columns = ["COD_3", "DESC_3"]
    cod3 = cod3.dropna(subset=["COD_3"]).drop_duplicates(subset="COD_3").copy()
    cod3["COD_3"] = cod3["COD_3"].astype(str).str.strip()

    # Unión principal — se excluye COD_DEPARTAMENTO de div para evitar conflicto de columnas
    div_join = div.drop(columns=["COD_DEPARTAMENTO"], errors="ignore")
    datos = df.merge(div_join, on="COD_DANE", how="left")

    # Limpieza de COD_MUERTE
    datos["COD_MUERTE"] = datos["COD_MUERTE"].astype(str).str.strip()

    return datos, div, cod4, cod3


DATOS, DIV, COD4, COD3 = cargar_datos()

# Centroides de departamentos para el mapa
with open(os.path.join(DATA_DIR, "dept_centroids.json")) as f:
    _centroids_raw = json.load(f)

CENTROIDS = {int(k): v for k, v in _centroids_raw.items()}


# ─────────────────────────────────────────────────────────────────────────────
# DATOS PARA CADA GRÁFICO
# ─────────────────────────────────────────────────────────────────────────────

# 1. Muertes por departamento
muertes_dept = (
    DATOS.groupby(["COD_DEPARTAMENTO", "DEPARTAMENTO"])
    .size()
    .reset_index(name="TOTAL_MUERTES")
)
muertes_dept["LAT"] = muertes_dept["COD_DEPARTAMENTO"].map(
    lambda c: CENTROIDS.get(c, [None, None, ""])[0]
)
muertes_dept["LON"] = muertes_dept["COD_DEPARTAMENTO"].map(
    lambda c: CENTROIDS.get(c, [None, None, ""])[1]
)
muertes_dept = muertes_dept.dropna(subset=["LAT", "LON"])

# 2. Muertes por mes
MESES = {
    1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr",
    5: "May", 6: "Jun", 7: "Jul", 8: "Ago",
    9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic",
}
muertes_mes = DATOS.groupby("MES").size().reset_index(name="TOTAL")
muertes_mes["MES_NOMBRE"] = muertes_mes["MES"].map(MESES)

# 3. Top 5 ciudades más violentas (homicidios con X95)
homicidios = DATOS[DATOS["COD_MUERTE"].str.startswith("X95", na=False)]
ciudades_violentas = (
    homicidios.groupby("MUNICIPIO")
    .size()
    .reset_index(name="HOMICIDIOS")
    .sort_values("HOMICIDIOS", ascending=False)
    .head(5)
)

# 4. Top 10 ciudades con menor mortalidad
muertes_ciudad = (
    DATOS.groupby("MUNICIPIO")
    .size()
    .reset_index(name="TOTAL_MUERTES")
    .sort_values("TOTAL_MUERTES")
    .head(10)
)

# 5. Top 10 causas de muerte
top_causas_raw = DATOS["COD_MUERTE"].value_counts().head(10).reset_index()
top_causas_raw.columns = ["COD_MUERTE", "TOTAL"]
top_causas = top_causas_raw.merge(COD4.rename(columns={"DESCRIPCION": "DESC_4"}), on="COD_MUERTE", how="left")
# Rellenar con descripción de 3 caracteres donde falte
top_causas["COD_3"] = top_causas["COD_MUERTE"].str[:3]
top_causas = top_causas.merge(COD3.rename(columns={"COD_3": "COD_3", "DESC_3": "DESC_3"}), on="COD_3", how="left")
top_causas["DESCRIPCION"] = top_causas["DESC_4"].fillna(top_causas["DESC_3"])
top_causas = top_causas[["COD_MUERTE", "DESCRIPCION", "TOTAL"]].copy()

# 6. Muertes por sexo y departamento (barras apiladas)
SEXO_MAP = {1: "Masculino", 2: "Femenino", 3: "Indeterminado"}
datos_sexo = DATOS.copy()
datos_sexo["SEXO_NOMBRE"] = datos_sexo["SEXO"].map(SEXO_MAP).fillna("Indeterminado")
muertes_sexo = (
    datos_sexo.groupby(["DEPARTAMENTO", "SEXO_NOMBRE"])
    .size()
    .reset_index(name="TOTAL")
)

# 7. Histograma por grupo de edad
GRUPOS_EDAD = {
    (0, 4):   "Neonatal\n(<1 mes)",
    (5, 6):   "Infantil\n(1-11 m)",
    (7, 8):   "Primera infancia\n(1-4 a)",
    (9, 10):  "Niñez\n(5-14 a)",
    (11, 11): "Adolescencia\n(15-19 a)",
    (12, 13): "Juventud\n(20-29 a)",
    (14, 16): "Adultez temprana\n(30-44 a)",
    (17, 19): "Adultez intermedia\n(45-59 a)",
    (20, 24): "Vejez\n(60-84 a)",
    (25, 28): "Longevidad\n(85-100+ a)",
    (29, 29): "Desconocida",
}


def asignar_grupo(codigo):
    for (lo, hi), nombre in GRUPOS_EDAD.items():
        if lo <= codigo <= hi:
            return nombre
    return "Otro"


datos_edad = DATOS.copy()
datos_edad["GRUPO"] = datos_edad["GRUPO_EDAD1"].apply(asignar_grupo)
ORDEN_GRUPOS = [v for v in GRUPOS_EDAD.values()]
muertes_edad = (
    datos_edad.groupby("GRUPO")
    .size()
    .reset_index(name="TOTAL")
)
muertes_edad["ORD"] = muertes_edad["GRUPO"].apply(
    lambda g: ORDEN_GRUPOS.index(g) if g in ORDEN_GRUPOS else 99
)
muertes_edad = muertes_edad.sort_values("ORD")


# ─────────────────────────────────────────────────────────────────────────────
# PALETA DE COLORES
# ─────────────────────────────────────────────────────────────────────────────

AZUL_OSCURO = "#003366"
AZUL_MEDIO = "#1565C0"
AZUL_CLARO = "#42A5F5"
ROJO_ACENTO = "#E53935"
VERDE_ACENTO = "#43A047"
FONDO = "#F4F6F9"
FONDO_TARJETA = "#FFFFFF"
TEXTO_TITULO = "#1A237E"
TEXTO_GRIS = "#546E7A"

COLOR_SEXO = {
    "Masculino": "#1565C0",
    "Femenino": "#E91E63",
    "Indeterminado": "#78909C",
}


def estilo_figura(fig, titulo="", alto=420):
    """Aplica estilos comunes a todas las figuras."""
    fig.update_layout(
        plot_bgcolor=FONDO_TARJETA,
        paper_bgcolor=FONDO_TARJETA,
        font=dict(family="Inter, Segoe UI, sans-serif", size=12, color="#37474F"),
        title=dict(
            text=titulo,
            font=dict(size=15, color=TEXTO_TITULO, family="Inter, Segoe UI, sans-serif"),
            x=0.02,
            xanchor="left",
        ),
        margin=dict(l=50, r=30, t=55, b=50),
        height=alto,
        legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# CONSTRUCCIÓN DE FIGURAS
# ─────────────────────────────────────────────────────────────────────────────

def fig_mapa():
    fig = go.Figure(
        go.Scattergeo(
            lat=muertes_dept["LAT"],
            lon=muertes_dept["LON"],
            text=muertes_dept["DEPARTAMENTO"] + "<br>" +
                 muertes_dept["TOTAL_MUERTES"].apply(lambda x: f"{x:,}") + " muertes",
            hoverinfo="text",
            mode="markers",
            marker=dict(
                size=muertes_dept["TOTAL_MUERTES"] / 900,
                sizemin=6,
                sizemode="area",
                color=muertes_dept["TOTAL_MUERTES"],
                colorscale=[
                    [0, "#B3D1F5"],
                    [0.2, "#6BAED6"],
                    [0.5, "#2171B5"],
                    [0.8, "#084594"],
                    [1, ROJO_ACENTO],
                ],
                showscale=True,
                colorbar=dict(
                    title=dict(text="Muertes", font=dict(size=11)),
                    thickness=14,
                    len=0.7,
                ),
                line=dict(color="white", width=0.5),
                opacity=0.85,
            ),
        )
    )
    fig.update_geos(
        scope="south america",
        showcountries=True,
        countrycolor="#CFD8DC",
        showcoastlines=True,
        coastlinecolor="#B0BEC5",
        showland=True,
        landcolor="#ECEFF1",
        showocean=True,
        oceancolor="#E3F2FD",
        showlakes=True,
        lakecolor="#E3F2FD",
        center=dict(lat=4.5, lon=-74.0),
        projection_scale=5,
    )
    fig.update_layout(
        plot_bgcolor=FONDO_TARJETA,
        paper_bgcolor=FONDO_TARJETA,
        title=dict(
            text="Distribución total de muertes por departamento — Colombia 2019",
            font=dict(size=15, color=TEXTO_TITULO),
            x=0.02,
        ),
        margin=dict(l=10, r=10, t=50, b=10),
        height=520,
        font=dict(family="Inter, Segoe UI, sans-serif", size=12),
    )
    return fig


def fig_lineas():
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=muertes_mes["MES_NOMBRE"],
            y=muertes_mes["TOTAL"],
            mode="lines+markers",
            line=dict(color=AZUL_MEDIO, width=3),
            marker=dict(size=9, color=AZUL_MEDIO, line=dict(color="white", width=2)),
            fill="tozeroy",
            fillcolor="rgba(21, 101, 192, 0.12)",
            hovertemplate="<b>%{x}</b><br>Muertes: %{y:,.0f}<extra></extra>",
        )
    )
    fig.update_xaxes(
        title_text="Mes",
        showgrid=False,
        linecolor="#CFD8DC",
    )
    fig.update_yaxes(
        title_text="Total de muertes",
        showgrid=True,
        gridcolor="#ECEFF1",
        zeroline=False,
    )
    return estilo_figura(fig, "Total de muertes por mes — Colombia 2019")


def fig_barras_violencia():
    fig = go.Figure(
        go.Bar(
            x=ciudades_violentas["MUNICIPIO"],
            y=ciudades_violentas["HOMICIDIOS"],
            marker=dict(
                color=ciudades_violentas["HOMICIDIOS"],
                colorscale=[[0, "#FF8A80"], [1, ROJO_ACENTO]],
                showscale=False,
                line=dict(color="white", width=0.5),
            ),
            text=ciudades_violentas["HOMICIDIOS"].apply(lambda x: f"{x:,}"),
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>Homicidios (X95): %{y:,}<extra></extra>",
        )
    )
    fig.update_xaxes(
        title_text="Ciudad",
        showgrid=False,
        linecolor="#CFD8DC",
    )
    fig.update_yaxes(
        title_text="Número de homicidios",
        showgrid=True,
        gridcolor="#ECEFF1",
        zeroline=False,
    )
    fig.update_layout(plot_bgcolor=FONDO_TARJETA, paper_bgcolor=FONDO_TARJETA)
    return estilo_figura(
        fig,
        "Top 5 ciudades con mayor número de homicidios por arma de fuego (código X95) — 2019",
    )


def fig_circular():
    fig = go.Figure(
        go.Pie(
            labels=muertes_ciudad["MUNICIPIO"],
            values=muertes_ciudad["TOTAL_MUERTES"],
            hole=0.45,
            textinfo="percent+label",
            hovertemplate="<b>%{label}</b><br>Muertes: %{value}<br>%{percent}<extra></extra>",
            marker=dict(
                colors=px.colors.sequential.Blues_r[:10],
                line=dict(color="white", width=1.5),
            ),
        )
    )
    fig.update_layout(
        plot_bgcolor=FONDO_TARJETA,
        paper_bgcolor=FONDO_TARJETA,
        title=dict(
            text="10 municipios con menor índice de mortalidad — Colombia 2019",
            font=dict(size=15, color=TEXTO_TITULO),
            x=0.02,
        ),
        height=460,
        margin=dict(l=20, r=20, t=55, b=20),
        font=dict(family="Inter, Segoe UI, sans-serif", size=12),
        legend=dict(
            orientation="v",
            x=1.0,
            y=0.5,
            font=dict(size=11),
            bgcolor="rgba(0,0,0,0)",
        ),
        annotations=[
            dict(
                text="Menor<br>mortalidad",
                x=0.5, y=0.5,
                font_size=13,
                font_color=TEXTO_GRIS,
                showarrow=False,
            )
        ],
    )
    return fig


def fig_tabla():
    top = top_causas.copy()
    top["RANK"] = range(1, len(top) + 1)
    top = top[["RANK", "COD_MUERTE", "DESCRIPCION", "TOTAL"]]
    top["TOTAL_FMT"] = top["TOTAL"].apply(lambda x: f"{x:,}")
    return top


def fig_barras_apiladas():
    # Para legibilidad, usar solo los 15 departamentos con más muertes
    top_depts = (
        DATOS.groupby("DEPARTAMENTO").size()
        .nlargest(15)
        .index.tolist()
    )
    data_filtrada = muertes_sexo[muertes_sexo["DEPARTAMENTO"].isin(top_depts)]

    fig = px.bar(
        data_filtrada,
        x="DEPARTAMENTO",
        y="TOTAL",
        color="SEXO_NOMBRE",
        color_discrete_map=COLOR_SEXO,
        barmode="stack",
        labels={"TOTAL": "Total de muertes", "DEPARTAMENTO": "Departamento", "SEXO_NOMBRE": "Sexo"},
        custom_data=["SEXO_NOMBRE"],
    )
    fig.update_traces(
        hovertemplate="<b>%{x}</b><br>Sexo: %{customdata[0]}<br>Muertes: %{y:,}<extra></extra>"
    )
    fig.update_xaxes(
        tickangle=-40,
        showgrid=False,
        linecolor="#CFD8DC",
        title_text="Departamento",
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor="#ECEFF1",
        zeroline=False,
        title_text="Total de muertes",
    )
    return estilo_figura(
        fig,
        "Total de muertes por sexo en los 15 departamentos con mayor mortalidad — 2019",
        alto=460,
    )


def fig_histograma():
    fig = go.Figure(
        go.Bar(
            x=muertes_edad["GRUPO"],
            y=muertes_edad["TOTAL"],
            marker=dict(
                color=muertes_edad["TOTAL"],
                colorscale=[[0, "#B3D1F5"], [0.5, AZUL_MEDIO], [1, AZUL_OSCURO]],
                showscale=False,
                line=dict(color="white", width=0.5),
            ),
            text=muertes_edad["TOTAL"].apply(lambda x: f"{x:,}"),
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>Muertes: %{y:,}<extra></extra>",
        )
    )
    fig.update_xaxes(
        title_text="Grupo de edad",
        showgrid=False,
        linecolor="#CFD8DC",
        tickfont=dict(size=10),
    )
    fig.update_yaxes(
        title_text="Total de muertes",
        showgrid=True,
        gridcolor="#ECEFF1",
        zeroline=False,
    )
    return estilo_figura(
        fig,
        "Distribución de muertes por grupo de edad (GRUPO_EDAD1) — Colombia 2019",
        alto=440,
    )


# ─────────────────────────────────────────────────────────────────────────────
# LAYOUT DE LA APLICACIÓN
# ─────────────────────────────────────────────────────────────────────────────

app = dash.Dash(
    __name__,
    title="Mortalidad Colombia 2019",
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
    suppress_callback_exceptions=True,
)
server = app.server  # Para despliegue con Gunicorn


def tarjeta(titulo, contenido_id, contenido, alto_extra=None):
    estilo = {
        "background": FONDO_TARJETA,
        "borderRadius": "12px",
        "boxShadow": "0 2px 12px rgba(0,0,0,0.07)",
        "padding": "8px 16px 16px",
        "marginBottom": "24px",
    }
    return html.Div(
        children=[
            html.H3(
                titulo,
                style={
                    "fontSize": "13px",
                    "fontWeight": "600",
                    "color": TEXTO_GRIS,
                    "textTransform": "uppercase",
                    "letterSpacing": "0.08em",
                    "marginBottom": "4px",
                    "padding": "4px 0",
                    "borderBottom": f"2px solid {AZUL_CLARO}",
                },
            ),
            contenido,
        ],
        style=estilo,
    )


# KPIs resumen
total_muertes = len(DATOS)
total_depts = DATOS["COD_DEPARTAMENTO"].nunique()
total_homicidios = int(homicidios.shape[0])
principal_causa = top_causas.iloc[0]["DESCRIPCION"] if not top_causas.empty else "-"


def kpi_box(valor, etiqueta, color=AZUL_MEDIO):
    return html.Div(
        [
            html.Div(
                valor,
                style={
                    "fontSize": "32px",
                    "fontWeight": "800",
                    "color": color,
                    "lineHeight": "1.1",
                },
            ),
            html.Div(
                etiqueta,
                style={"fontSize": "12px", "color": TEXTO_GRIS, "marginTop": "4px"},
            ),
        ],
        style={
            "background": FONDO_TARJETA,
            "borderRadius": "12px",
            "boxShadow": "0 2px 12px rgba(0,0,0,0.07)",
            "padding": "20px 24px",
            "flex": "1",
            "minWidth": "160px",
            "borderTop": f"4px solid {color}",
        },
    )


tabla_datos = fig_tabla()

app.layout = html.Div(
    style={"background": FONDO, "minHeight": "100vh", "fontFamily": "Inter, Segoe UI, sans-serif"},
    children=[
        # ── Encabezado ──────────────────────────────────────────────────────
        html.Div(
            style={
                "background": f"linear-gradient(135deg, {AZUL_OSCURO} 0%, {AZUL_MEDIO} 100%)",
                "padding": "28px 40px 24px",
                "color": "white",
                "marginBottom": "28px",
            },
            children=[
                html.Div(
                    [
                        html.H1(
                            "Análisis de Mortalidad en Colombia 2019",
                            style={"margin": "0", "fontSize": "26px", "fontWeight": "700", "letterSpacing": "-0.5px"},
                        ),
                        html.P(
                            "Fuente: DANE — Estadísticas Vitales EEVV 2019  |  Maestría en Inteligencia Artificial — Universidad de La Salle",
                            style={"margin": "6px 0 0", "fontSize": "13px", "opacity": "0.8"},
                        ),
                    ]
                )
            ],
        ),

        # ── Contenido principal ─────────────────────────────────────────────
        html.Div(
            style={"maxWidth": "1380px", "margin": "0 auto", "padding": "0 24px 48px"},
            children=[

                # KPIs
                html.Div(
                    [
                        kpi_box(f"{total_muertes:,}", "Total de muertes registradas", AZUL_MEDIO),
                        kpi_box(f"{total_depts}", "Departamentos con registros", VERDE_ACENTO),
                        kpi_box(f"{total_homicidios:,}", "Homicidios por arma de fuego (X95)", ROJO_ACENTO),
                        kpi_box(
                            "Infarto agudo", "Primera causa de muerte (I219)",
                            "#6A1B9A",
                        ),
                    ],
                    style={
                        "display": "flex",
                        "gap": "16px",
                        "flexWrap": "wrap",
                        "marginBottom": "28px",
                    },
                ),

                # Mapa
                tarjeta(
                    "1. Distribución geográfica de muertes por departamento",
                    "mapa-dept",
                    dcc.Graph(
                        id="mapa-dept",
                        figure=fig_mapa(),
                        config={"displayModeBar": True, "displaylogo": False},
                    ),
                ),

                # Líneas + Barras violencia
                html.Div(
                    style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "20px", "marginBottom": "24px"},
                    children=[
                        tarjeta(
                            "2. Muertes por mes",
                            "grafico-mes",
                            dcc.Graph(
                                id="grafico-mes",
                                figure=fig_lineas(),
                                config={"displayModeBar": False},
                            ),
                        ),
                        tarjeta(
                            "3. Ciudades más violentas (homicidios X95)",
                            "grafico-violencia",
                            dcc.Graph(
                                id="grafico-violencia",
                                figure=fig_barras_violencia(),
                                config={"displayModeBar": False},
                            ),
                        ),
                    ],
                ),

                # Circular + Tabla
                html.Div(
                    style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "20px", "marginBottom": "24px"},
                    children=[
                        tarjeta(
                            "4. Municipios con menor mortalidad (top 10)",
                            "grafico-circular",
                            dcc.Graph(
                                id="grafico-circular",
                                figure=fig_circular(),
                                config={"displayModeBar": False},
                            ),
                        ),
                        tarjeta(
                            "5. Top 10 causas de muerte en Colombia",
                            "tabla-causas",
                            dash_table.DataTable(
                                id="tabla-causas",
                                columns=[
                                    {"name": "#", "id": "RANK"},
                                    {"name": "Código CIE-10", "id": "COD_MUERTE"},
                                    {"name": "Descripción", "id": "DESCRIPCION"},
                                    {"name": "Total casos", "id": "TOTAL_FMT"},
                                ],
                                data=tabla_datos.to_dict("records"),
                                style_table={"overflowX": "auto", "borderRadius": "8px"},
                                style_header={
                                    "backgroundColor": AZUL_OSCURO,
                                    "color": "white",
                                    "fontWeight": "600",
                                    "fontSize": "12px",
                                    "padding": "10px 14px",
                                    "border": "none",
                                },
                                style_cell={
                                    "fontSize": "12px",
                                    "padding": "10px 14px",
                                    "textAlign": "left",
                                    "fontFamily": "Inter, Segoe UI, sans-serif",
                                    "border": "none",
                                    "borderBottom": "1px solid #ECEFF1",
                                    "whiteSpace": "normal",
                                    "height": "auto",
                                    "maxWidth": "220px",
                                    "overflow": "hidden",
                                    "textOverflow": "ellipsis",
                                },
                                style_data_conditional=[
                                    {
                                        "if": {"row_index": "odd"},
                                        "backgroundColor": "#F8FAFC",
                                    },
                                    {
                                        "if": {"row_index": 0},
                                        "fontWeight": "700",
                                        "color": AZUL_OSCURO,
                                    },
                                ],
                                style_cell_conditional=[
                                    {"if": {"column_id": "RANK"}, "width": "40px", "textAlign": "center"},
                                    {"if": {"column_id": "COD_MUERTE"}, "width": "100px", "fontWeight": "600"},
                                    {"if": {"column_id": "TOTAL_FMT"}, "width": "100px", "textAlign": "right", "fontWeight": "600"},
                                ],
                                page_size=10,
                                sort_action="native",
                            ),
                        ),
                    ],
                ),

                # Barras apiladas (sexo × departamento)
                tarjeta(
                    "6. Muertes por sexo en los principales departamentos",
                    "grafico-sexo",
                    dcc.Graph(
                        id="grafico-sexo",
                        figure=fig_barras_apiladas(),
                        config={"displayModeBar": False},
                    ),
                ),

                # Histograma grupo de edad
                tarjeta(
                    "7. Distribución de muertes por grupo de edad",
                    "grafico-edad",
                    dcc.Graph(
                        id="grafico-edad",
                        figure=fig_histograma(),
                        config={"displayModeBar": False},
                    ),
                ),

                # Pie de página
                html.Div(
                    [
                        html.Hr(style={"borderColor": "#CFD8DC", "margin": "8px 0 16px"}),
                        html.P(
                            "Actividad 4 — Aplicación web interactiva para el análisis de mortalidad en Colombia  |  "
                            "Maestría en Inteligencia Artificial — Universidad de La Salle  |  2025",
                            style={"fontSize": "11px", "color": TEXTO_GRIS, "textAlign": "center", "margin": "0"},
                        ),
                    ]
                ),
            ],
        ),
    ],
)


# ─────────────────────────────────────────────────────────────────────────────
# PUNTO DE ENTRADA
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True, port=8050)
