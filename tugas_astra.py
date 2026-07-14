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
    # Membaca file Excel
    df = pd.read_excel("dataset_astra.xlsx")
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
    
    # Mengubah nama kolom 'Others' agar lebih deskriptif
    df_t = df_t.rename(columns={
        'Others': 'Beban Usaha Lainnya',
        'Others (1)': 'Penghasilan/Beban Lain-Lain',
        'Others (2)': 'Laba Bersih Lainnya'
    })
    
    return df_t

df_plot = load_data()

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
    laba_bersih_col = [col for col in df_plot.columns if 'Laba Bersih Tahun Berjalan' in col][0]
    st.metric(label="Laba Bersih", 
              value=f"{latest_q[laba_bersih_col]:,.0f} M", 
              delta=f"{latest_q[laba_bersih_col] - prev_q[laba_bersih_col]:,.0f} M")

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
    # Memilih kolom beban (termasuk yang sudah di-rename)
    beban_aktual = [col for col in df_plot.columns if any(b in col for b in ['Beban Penjualan', 'Beban Umum Dan', 'Beban Usaha Lainnya'])]
    
    fig_bar = px.bar(df_plot, x=df_plot.index, y=beban_aktual, 
                     barmode='stack',
                     color_discrete_sequence=px.colors.qualitative.Pastel)
    fig_bar.update_layout(xaxis_title="Kuartal", yaxis_title="Nominal (Miliar IDR)", legend_title="Jenis Beban")
    st.plotly_chart(fig_bar, use_container_width=True)
    
    # Menyisipkan kotak narasi/informasi
    st.info("""
    **Catatan Analisis Komposisi Beban:**
    * **Beban Penjualan:** Mayoritas dialokasikan untuk aktivitas pemasaran dan distribusi.
    * **Beban Umum & Administrasi:** Terdiri dari biaya operasional kantor dan administrasi rutin.
    * **Beban Usaha Lainnya:** Mencakup biaya lain di luar operasi utama yang telah disesuaikan (sebelumnya dikategorikan sebagai *Others*).
    """)

st.divider()

# ==========================================
# 5. WATERFALL CHART (ALUR LABA RUGI)
# ==========================================
st.subheader(f"Alur Laba Rugi (Kuartal {df_plot.index[-1]})")

# Mengambil nilai Total Beban Usaha yang sudah dijumlahkan
total_beban_usaha = df_plot[beban_aktual].sum(axis=1).iloc[-1] if len(beban_aktual) > 0 else 0

fig_waterfall = go.Figure(go.Waterfall(
    name="Laba Rugi", orientation="v",
    measure=["absolute", "relative", "total", "relative", "total"],
    x=["Pendapatan", "Beban Pokok", "Laba Kotor", "Total Beban Usaha", "Laba Usaha"],
    textposition="outside",
    y=[
        latest_q['Total Pendapatan'], 
        latest_q['Total Beban Pokok Penjualan'], 
        0, 
        total_beban_usaha * -1 if total_beban_usaha > 0 else total_beban_usaha, # Dipastikan minus agar grafiknya turun
        0
    ],
    connector={"line":{"color":"rgb(63, 63, 63)"}}
))
fig_waterfall.update_layout(plot_bgcolor='white')
st.plotly_chart(fig_waterfall, use_container_width=True)
