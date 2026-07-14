import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# ==========================================
# 1. KONFIGURASI HALAMAN DASHBOARD
# ==========================================
st.set_page_config(page_title="Dashboard Keuangan", layout="wide")
st.title("Dashboard Analisis Keuangan")
st.markdown("Analisis Tren Pendapatan, Laba, dan Efisiensi Operasional")

# ==========================================
# 2. DATA LOADING & CLEANING
# ==========================================
@st.cache_data
def load_data():
    df = pd.read_csv("dataset_astra.csv")
    df = df.fillna(0)
    
    # Cleaning koma dan karakter lain
    for col in df.columns[1:]:
        df[col] = df[col].astype(str).str.replace(',', '', regex=False)
        df[col] = df[col].astype(str).str.replace(' B', '', regex=False)
        df[col] = df[col].astype(str).str.replace('%', '', regex=False)
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
    # Set kolom pertama sebagai index
    df.set_index(df.columns[0], inplace=True)
    df_t = df.transpose()
    
    # Membalik urutan waktu (terlama ke terbaru)
    df_t = df_t.iloc[::-1] 
    
    # Menangani duplikat nama kolom (Tambahkan angka otomatis)
    kolom_baru = []
    hitungan = {}
    for nama in df_t.columns:
        nama_str = str(nama).strip()
        if nama_str not in hitungan:
            hitungan[nama_str] = 0
            kolom_baru.append(nama_str)
        else:
            hitungan[nama_str] += 1
            kolom_baru.append(f"{nama_str} ({hitungan[nama_str]})")
            
    df_t.columns = kolom_baru
    
    return df_t

# Memuat data
try:
    df_plot = load_data()
except Exception as e:
    st.error(f"Gagal memuat data. Pastikan file CSV tersedia di folder yang sama. Detail error: {e}")
    st.stop()

# ==========================================
# 3. KPI SCORECARD (KARTU INDIKATOR)
# ==========================================
st.subheader("Ringkasan Kuartal Terakhir")
latest_q = df_plot.iloc[-1]
prev_q = df_plot.iloc[-2]

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(label="Total Pendapatan", 
              value=f"{latest_q['Total Pendapatan']:,.0f} M", 
              delta=f"{latest_q['Total Pendapatan'] - prev_q['Total Pendapatan']:,.0f} M")
with col2:
    st.metric(label="Laba Kotor", 
              value=f"{latest_q['Laba Kotor']:,.0f} M", 
              delta=f"{latest_q['Laba Kotor'] - prev_q['Laba Kotor']:,.0f} M")
with col3:
    # Mencari kolom Laba Bersih yang spesifik
    laba_bersih_col = [col for col in df_plot.columns if 'Laba Bersih Tahun Berjalan' in col]
    if laba_bersih_col:
        nama_kolom = laba_bersih_col[0]
        st.metric(label="Laba Bersih", 
                  value=f"{latest_q[nama_kolom]:,.0f} M", 
                  delta=f"{latest_q[nama_kolom] - prev_q[nama_kolom]:,.0f} M")
    else:
        st.metric(label="Laba Bersih", value="Data Tidak Ditemukan")

st.divider()

# ==========================================
# 4. VISUALISASI INTERAKTIF & NARASI
# ==========================================
col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    st.subheader("Tren Pendapatan vs Beban Pokok")
    fig_line = px.line(df_plot, x=df_plot.index, y=['Total Pendapatan', 'Total Beban Pokok Penjualan'],
                       labels={'value': 'Miliar IDR', 'index': 'Kuartal'},
                       color_discrete_map={'Total Pendapatan': '#2E86C1', 'Total Beban Pokok Penjualan': '#E74C3C'})
    fig_line.update_layout(xaxis_title="Kuartal", yaxis_title="Nominal (Miliar IDR)", legend_title="Akun")
    st.plotly_chart(fig_line, use_container_width=True)

with col_chart2:
    st.subheader("Komposisi Beban Usaha")
    # Memilih kolom beban
    beban_aktual = [col for col in df_plot.columns if any(b in col for b in ['Beban Penjualan', 'Beban Umum Dan', 'Beban Usaha'])]
    
    if beban_aktual:
        fig_bar = px.bar(df_plot, x=df_plot.index, y=beban_aktual, 
                         barmode='stack',
                         color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_bar.update_layout(xaxis_title="Kuartal", yaxis_title="Nominal (Miliar IDR)", legend_title="Jenis Beban")
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.warning("Data kolom beban tidak ditemukan untuk membuat grafik ini.")
    
    # Menyisipkan kotak narasi/informasi
    st.info("""
    **Catatan Analisis Komposisi Beban:**
    * **Beban Penjualan:** Mayoritas dialokasikan untuk aktivitas pemasaran dan distribusi.
    * **Beban Umum & Administrasi:** Terdiri dari biaya operasional kantor dan administrasi rutin.
    * **Beban Usaha Lainnya:** Mencakup biaya lain di luar operasi utama.
    """)

st.divider()

# ==========================================
# 5. WATERFALL CHART (ALUR LABA RUGI)
# ==========================================
st.subheader(f"Alur Laba Rugi (Kuartal Terakhir)")

# Mengambil nilai Total Beban Usaha yang sudah dijumlahkan
total_beban_usaha = df_plot[beban_aktual].sum(axis=1).iloc[-1] if len(beban_aktual) > 0 else 0

fig_waterfall = go.Figure(go.Waterfall(
    name="Laba Rugi", orientation="v",
    measure=["absolute", "relative", "total", "relative", "total"],
    x=["Pendapatan", "Beban Pokok", "Laba Kotor", "Total Beban Usaha", "Laba Usaha"],
    textposition="outside",
    y=[
        latest_q.get('Total Pendapatan', 0), 
        latest_q.get('Total Beban Pokok Penjualan', 0), 
        0, 
        total_beban_usaha * -1 if total_beban_usaha > 0 else total_beban_usaha, 
        0
    ],
    connector={"line":{"color":"rgb(63, 63, 63)"}}
))
fig_waterfall.update_layout(plot_bgcolor='white')
st.plotly_chart(fig_waterfall, use_container_width=True)