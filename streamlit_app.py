import streamlit as st
import pandas as pd
import plotly.express as px
from db_manager import DBManager

# --- Połączenie z bazą ---
DB_URL = "postgresql+psycopg2://postgres:postgres@localhost:5432/energy_prediction"
db = DBManager(DB_URL)

# --- Pobierz dane ---
df_produced = db.get_produced_energy_training_data()
df_sold = db.get_sold_energy_training_data()

# --- Filtr daty ---
min_date = pd.to_datetime(df_produced["date"]).min()
max_date = pd.to_datetime(df_produced["date"]).max()

st.sidebar.header("Filtr daty")
start_date = st.sidebar.date_input("Data początkowa", min_value=min_date, max_value=max_date, value=min_date)
end_date = st.sidebar.date_input("Data końcowa", min_value=min_date, max_value=max_date, value=max_date)

# Filtrowanie danych
mask_produced = (pd.to_datetime(df_produced["date"]) >= pd.to_datetime(start_date)) & (pd.to_datetime(df_produced["date"]) <= pd.to_datetime(end_date))
mask_sold = (pd.to_datetime(df_sold["date"]) >= pd.to_datetime(start_date)) & (pd.to_datetime(df_sold["date"]) <= pd.to_datetime(end_date))

df_produced_filtered = df_produced[mask_produced]
df_sold_filtered = df_sold[mask_sold]

# Przykładowe porównanie
df_compare = pd.DataFrame({
    "date": df_produced_filtered["date"],
    "produced_energy": df_produced_filtered["produced_energy"],
    "sold_energy": df_sold_filtered["sold_energy"] if "sold_energy" in df_sold_filtered.columns else None
})

# --- Interfejs Streamlit ---
st.set_page_config(page_title="Energia - Tabele i Wykresy", layout="wide")

st.title("Tabela godzinowa z zakładkami")

tab1, tab2, tab3 = st.tabs(["En. Wytworzona", "En. Wprowadzona", "Porównaj"])

with tab1:
    st.subheader("Energia wytworzona (historyczne)")
    st.dataframe(df_produced_filtered)

with tab2:
    st.subheader("Energia wprowadzona (historyczne)")
    st.dataframe(df_sold_filtered)
    st.line_chart(df_sold_filtered.set_index("date")["sold_energy"])

with tab3:
    st.subheader("Porównanie produkcji i sprzedaży")
    st.line_chart(df_compare.set_index("date")[["produced_energy", "sold_energy"]])

# --- Wykres dziennej produkcji energii ---
# Upewnij się, że kolumna "date" jest typu datetime
df_produced_filtered["date"] = pd.to_datetime(df_produced_filtered["date"])

# Teraz możesz agregować dziennie
df_daily = df_produced_filtered.resample('D', on='date').sum().reset_index()

fig = px.line(df_daily, x="date", y="produced_energy", title="Produkcja dzienna")
st.plotly_chart(fig)

# --- Wykres godzinowej produkcji energii ---
selected_date = st.selectbox("Wybierz dzień", df_produced_filtered["date"].unique())
df_hourly = df_produced_filtered[df_produced_filtered["date"] == selected_date]

st.line_chart(df_hourly.set_index("hour")["produced_energy"])

# --- Uruchom aplikację ---
# W terminalu: streamlit run streamlit_app.py