import io
import os
import sys
import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="Tablas Pasivas Cooperativas y Bancos",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
        footer {visibility: hidden;}
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 8rem !important;
            padding-left: 0.8rem !important;
            padding-right: 0.8rem !important;
        }
    </style>
""",
    unsafe_allow_html=True,
)

st.title("Tablas Pasivas Cooperativas y Bancos")

if st.button("🔄 Refrescar Información", use_container_width=True):
  st.cache_data.clear()
  st.rerun()


@st.cache_data(ttl=300)
def cargar_datos_drive():
  file_id = "1DPASEKWo7lTbu8tug041iK5lMXLlyJvG"
  url = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx"

  response = requests.get(url)
  response.raise_for_status()

  excel_bytes = io.BytesIO(response.content)
  xls = pd.ExcelFile(excel_bytes)

  datos_instituciones = {}

  for sheet in xls.sheet_names:
    if sheet == "Tasas Referenciales":
      continue

    df = pd.read_excel(xls, sheet_name=sheet)
    if df.empty:
      continue

    cols = list(df.columns)
    table_starts = []
    for idx, c in enumerate(cols):
      if not str(c).startswith("Unnamed:"):
        table_starts.append((idx, str(c).strip()))

    productos = {}
    for i, (start_col, prod_name) in enumerate(table_starts):
      end_col = (
          table_starts[i + 1][0] - 1
          if i + 1 < len(table_starts)
          else len(cols)
      )

      sub_df = df.iloc[:, start_col:end_col].dropna(how="all")

      if not sub_df.empty and len(sub_df) > 1:
        sub_headers = list(sub_df.iloc[0])
        sub_data = sub_df.iloc[1:].copy()
        sub_data.columns = sub_headers
        sub_data = sub_data.dropna(how="all", axis=1).dropna(how="all", axis=0)

        cleaned_cols = []
        for col in sub_data.columns:
          col_str = str(col).replace("_", " ").title()
          col_str = col_str.replace("Porcentaje", "(%)").replace(
              "Dias", "Días"
          )
          col_str = col_str.replace("$", "").strip()
          cleaned_cols.append(col_str)

        sub_data.columns = cleaned_cols
        productos[prod_name] = sub_data

    if productos:
      datos_instituciones[sheet] = productos

  return datos_instituciones


def generar_tabla_html(df):
  df_display = df.copy()

  for col in df_display.columns:
    df_display[col] = df_display[col].apply(
        lambda x: (
            ""
            if pd.isna(x)
            else (
                f"{x:.2f}"
                if isinstance(x, float) and not x.is_integer()
                else (
                    str(int(x)) if isinstance(x, float) and x.is_integer() else str(x)
                )
            )
        )
    )

  headers_html = ""
  for idx, col in enumerate(df_display.columns):
    if idx == 0:
      sticky_style = (
          "position: -webkit-sticky !important; position: sticky !important; "
          "top: 0 !important; left: 0 !important; z-index: 50 !important; "
          "background-color: #2b3035 !important; color: #ffffff !important; "
          "background-clip: padding-box !important; "
          "box-shadow: 2px 2px 5px rgba(0,0,0,0.3);"
      )
    else:
      sticky_style = (
          "position: -webkit-sticky !important; position: sticky !important; "
          "top: 0 !important; z-index: 20 !important; "
          "background-color: #2b3035 !important; color: #ffffff !important; "
          "background-clip: padding-box !important;"
      )
    headers_html += f'<th style="padding: 10px 14px; border: 1px solid #444c56; white-space: nowrap; width: max-content; min-width: 110px; text-align: center; font-weight: bold; font-size: 13px; {sticky_style}">{col}</th>'

  rows_html = ""
  for r_idx, (_, row) in enumerate(df_display.iterrows()):
    bg_color = "#1e2227" if r_idx % 2 == 0 else "#252a30"
    cells_html = ""
    for c_idx, val in enumerate(row):
      if c_idx == 0:
        sticky_cell = (
            "position: -webkit-sticky !important; position: sticky !important;"
            " left: 0 !important; z-index: 30 !important; "
            f"background-color: {bg_color} !important; color: #f0f6fc"
            " !important; background-clip: padding-box !important; box-shadow:"
            " 2px 0 5px -2px rgba(0,0,0,0.4);"
        )
      else:
        sticky_cell = (
            "position: static !important; z-index: auto !important; "
            f"background-color: {bg_color} !important; color: #f0f6fc"
            " !important;"
        )
      cells_html += f'<td style="padding: 10px 14px; border: 1px solid #373e47; white-space: nowrap; width: max-content; text-align: center; font-size: 13px; {sticky_cell}">{val}</td>'
    rows_html += f"<tr>{cells_html}</tr>"

  table_html = f"""
    <div style="overflow-x: auto !important; overflow-y: auto !important; max-height: 480px; width: 100%; padding: 0px; border: 1px solid #373e47; border-radius: 8px; margin-top: 10px; margin-bottom: 25px;">
        <table style="width: 100%; border-collapse: separate !important; border-spacing: 0 !important; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
            <thead>
                <tr>{headers_html}</tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
    </div>
    """
  return table_html


try:
  datos = cargar_datos_drive()

  if not datos:
    st.error("No se pudieron extraer tablas de instituciones en el archivo.")
  else:
    instituciones = sorted(list(datos.keys()))

    inst_seleccionada = st.selectbox(
        "🏛️ Seleccione o busque la Entidad Financiera:",
        options=instituciones,
        index=0,
    )

    if inst_seleccionada:
      productos_dict = datos[inst_seleccionada]
      lista_productos = list(productos_dict.keys())

      prod_seleccionado = st.selectbox(
          "📊 Seleccione el Producto Financiero:",
          options=lista_productos,
          index=0,
      )

      if prod_seleccionado:
        df_tabla = productos_dict[prod_seleccionado]

        st.markdown(
            f"#### {inst_seleccionada} - {prod_seleccionado}",
            unsafe_allow_html=True,
        )

        tabla_html = generar_tabla_html(df_tabla)
        st.markdown(tabla_html, unsafe_allow_html=True)
        st.markdown(
            "<div style='height: 100px;'></div>", unsafe_allow_html=True
        )

except Exception as e:
  st.error(f"Error al conectar con Google Drive o procesar el archivo: {e}")

if __name__ == "__main__":
  if "streamlit" not in sys.argv[0]:
    os.system(f'streamlit run "{__file__}" --server.port 8501')