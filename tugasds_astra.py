import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

# ==========================================
# 1. KONFIGURASI HALAMAN & TEMA DARK MODE
# ==========================================
st.set_page_config(page_title="Astra Financial Dashboard", layout="wide", initial_sidebar_state="expanded")

# Memaksa tema grafik Plotly menjadi Dark Mode
pio.templates.default = "plotly_dark"

# Kustomisasi CSS untuk menaikkan Judul ke atas dan mempercantik Metrik Card
st.markdown("""
    <style>
    /* Mengurangi jarak kosong di bagian atas halaman */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .kpi-card {
        background-color: #1E1E2E;
        border-radius: 10px;
        padding: 20px;
        border-left: 5px solid #00E676;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.5);
    }
    .kpi-title { color: #A6ACCD; font-size: 14px; font-weight: bold; margin-bottom: 5px; }
    .kpi-value { color: #FFFFFF; font-size: 28px; font-weight: bold; margin-bottom: 5px; }
    .kpi-delta-up { color: #00E676; font-size: 14px; font-weight: bold; }
    .kpi-delta-down { color: #FF5252; font-size: 14px; font-weight: bold; }
    .kpi-neutral { color: #A6ACCD; font-size: 14px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# Judul Dashboard diposisikan paling atas sebelum elemen lain
st.title("Financial Performance Dashboard")

# ==========================================
# 2. DATA LOADING, CLEANING & FEATURE ENGINEERING
# ==========================================
@st.cache_data
def load_data():
    df = pd.read_csv("dataset_astra.csv")
    df = df.fillna(0)
    
    # Cleaning koma dan karakter teks lainnya
    for col in df.columns[1:]:
        df[col] = df[col].astype(str).str.replace(',', '', regex=False)
        df[col] = df[col].astype(str).str.replace(' B', '', regex=False)
        df[col] = df[col].astype(str).str.replace('%', '', regex=False)
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
    # Set kolom pertama sebagai index dan transpose
    df.set_index(df.columns[0], inplace=True)
    df_t = df.transpose()
    
    # Membalik urutan waktu (terlama ke terbaru)
    df_t = df_t.iloc[::-1] 
    
    # Menangani duplikat nama kolom
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
    
    # Feature Engineering: Menghitung Rasio Profitabilitas (Margin)
    if 'Total Pendapatan' in df_t.columns:
        if 'Laba Kotor' in df_t.columns:
            df_t['Gross Profit Margin (%)'] = (df_t['Laba Kotor'] / df_t['Total Pendapatan']) * 100
        
        # Mencari kolom laba operasional/usaha
        laba_usaha_cols = [c for c in df_t.columns if 'Laba Sebelum Pajak' in c or 'Laba Usaha' in c]
        if laba_usaha_cols:
            df_t['Operating Margin (%)'] = (df_t[laba_usaha_cols[0]] / df_t['Total Pendapatan']) * 100
            
        # Mencari kolom laba bersih
        laba_bersih_cols = [c for c in df_t.columns if 'Laba Bersih' in c]
        if laba_bersih_cols:
            df_t['Net Profit Margin (%)'] = (df_t[laba_bersih_cols[0]] / df_t['Total Pendapatan']) * 100
            
    return df_t

try:
    df_plot = load_data()
except Exception as e:
    st.error(f"Gagal memuat data dataset_astra.csv. Detail error: {e}")
    st.stop()

# ==========================================
# 3. SIDEBAR & SISTEM FILTER DINAMIS
# ==========================================
st.sidebar.title("Filter Analisis")

# Membuat opsi dropdown dengan "Keseluruhan" di urutan pertama
daftar_kuartal = df_plot.index.tolist()
opsi_filter = ["Keseluruhan"] + daftar_kuartal
kuartal_terpilih = st.sidebar.selectbox("Pilih Kuartal Analisis:", opsi_filter)

# Dinamika Kalkulasi Data Berdasarkan Pilihan Filter
laba_bersih_col = [col for col in df_plot.columns if 'Laba Bersih Tahun Berjalan' in col]
lb_nama = laba_bersih_col[0] if laba_bersih_col else None
beban_aktual = [col for col in df_plot.columns if any(b in col for b in ['Beban Penjualan', 'Beban Umum', 'Beban Usaha'])]

if kuartal_terpilih == "Keseluruhan":
    is_keseluruhan = True
    teks_periode = "Seluruh Periode Pencatatan"
    
    # Data trend utuh
    df_trend = df_plot.copy()
    
    pend_ini = df_plot.get('Total Pendapatan', pd.Series([0])).sum()
    cogs_ini = df_plot.get('Total Beban Pokok Penjualan', pd.Series([0])).sum()
    laba_kotor_ini = df_plot.get('Laba Kotor', pd.Series([0])).sum()
    laba_bersih_ini = df_plot[lb_nama].sum() if lb_nama else 0
    npm_ini = (laba_bersih_ini / pend_ini * 100) if pend_ini != 0 else 0
    total_beban_usaha = df_plot[beban_aktual].sum().sum() if len(beban_aktual) > 0 else 0
    
    pend_lalu, laba_kotor_lalu, laba_bersih_lalu, npm_lalu = 0, 0, 0, 0
    df_beban_pie = pd.DataFrame({'Beban': beban_aktual, 'Nilai': df_plot[beban_aktual].sum().values})

else:
    is_keseluruhan = False
    teks_periode = f"Kuartal: {kuartal_terpilih}"
    
    idx_terpilih = daftar_kuartal.index(kuartal_terpilih)
    
    # Data trend dipotong (difilter) dari awal HINGGA kuartal yang dipilih
    df_trend = df_plot.iloc[:idx_terpilih + 1]
    
    data_q_ini = df_plot.iloc[idx_terpilih]
    data_q_lalu = df_plot.iloc[idx_terpilih - 1] if idx_terpilih > 0 else data_q_ini
    
    pend_ini = data_q_ini.get('Total Pendapatan', 0)
    pend_lalu = data_q_lalu.get('Total Pendapatan', 0)
    cogs_ini = data_q_ini.get('Total Beban Pokok Penjualan', 0)
    
    laba_kotor_ini = data_q_ini.get('Laba Kotor', 0)
    laba_kotor_lalu = data_q_lalu.get('Laba Kotor', 0)
    
    laba_bersih_ini = data_q_ini[lb_nama] if lb_nama else 0
    laba_bersih_lalu = data_q_lalu[lb_nama] if lb_nama else 0
    
    npm_ini = data_q_ini.get('Net Profit Margin (%)', 0)
    npm_lalu = data_q_lalu.get('Net Profit Margin (%)', 0)
    
    total_beban_usaha = data_q_ini[beban_aktual].sum() if len(beban_aktual) > 0 else 0
    df_beban_pie = pd.DataFrame({'Beban': beban_aktual, 'Nilai': data_q_ini[beban_aktual].values})

# Subjudul diposisikan di bawah Judul Utama
st.markdown(f"**Analisis Kinerja Keuangan | Periode: {teks_periode}**")

# ==========================================
# 4. KPI SCORECARD
# ==========================================
def tampilkan_kpi(judul, nilai_sekarang, nilai_lalu, format_persen=False, status_total=False):
    if status_total:
        delta_str = "Total Seluruh Periode"
        warna_delta = "kpi-neutral"
    else:
        selisih = nilai_sekarang - nilai_lalu
        pertumbuhan = (selisih / abs(nilai_lalu)) * 100 if nilai_lalu != 0 else 0
        simbol_arah = "▲" if selisih > 0 else "▼" if selisih < 0 else "▬"
        warna_delta = "kpi-delta-up" if selisih >= 0 else "kpi-delta-down"
        
        if format_persen:
            delta_str = f"{simbol_arah} {abs(selisih):.2f}% (Bps) QoQ"
        else:
            delta_str = f"{simbol_arah} Rp {abs(selisih):,.0f} M ({pertumbuhan:.1f}%) QoQ"
            
    val_str = f"{nilai_sekarang:.2f}%" if format_persen else f"Rp {nilai_sekarang:,.0f} M"
        
    st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">{judul.upper()}</div>
            <div class="kpi-value">{val_str}</div>
            <div class="{warna_delta}">{delta_str}</div>
        </div>
    """, unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)

with col1:
    tampilkan_kpi("Total Pendapatan", pend_ini, pend_lalu, status_total=is_keseluruhan)
with col2:
    tampilkan_kpi("Laba Kotor", laba_kotor_ini, laba_kotor_lalu, status_total=is_keseluruhan)
with col3:
    tampilkan_kpi("Laba Bersih", laba_bersih_ini, laba_bersih_lalu, status_total=is_keseluruhan)
with col4:
    tampilkan_kpi("Net Profit Margin", npm_ini, npm_lalu, format_persen=True, status_total=is_keseluruhan)

st.write("---")

# ==========================================
# 5. SISTEM TAB UNTUK ANALISIS MENDALAM
# ==========================================
tab1, tab2, tab3 = st.tabs(["Tren & Pertumbuhan", "Analisis Profitabilitas (Margin)", "Struktur Biaya & Alur Laba"])

# ----------------- TAB 1: TREN PENDAPATAN -----------------
with tab1:
    st.subheader(f"Historis Tren Pendapatan vs Beban Pokok ({teks_periode})")
    fig_line = px.area(df_trend, x=df_trend.index, y=['Total Pendapatan', 'Total Beban Pokok Penjualan'],
                       labels={'value': 'Miliar IDR', 'index': 'Kuartal'},
                       color_discrete_map={'Total Pendapatan': '#29B6F6', 'Total Beban Pokok Penjualan': '#EF5350'})
    fig_line.update_layout(xaxis_title="Kuartal Historis", yaxis_title="Nominal (Miliar IDR)", legend_title="Komponen", hovermode="x unified")
    
    st.plotly_chart(fig_line, use_container_width=True)
    st.info("Insight: Area grafik menunjukkan jarak antara Pendapatan dan Beban Pokok. Semakin lebar jarak warna biru di atas warna merah, semakin besar Laba Kotor yang dihasilkan perusahaan pada rentang waktu terpilih.")

# ----------------- TAB 2: ANALISIS MARGIN -----------------
with tab2:
    st.subheader(f"Analisis Tingkat Efisiensi & Margin Keuntungan ({teks_periode})")
    kolom_margin = [c for c in ['Gross Profit Margin (%)', 'Operating Margin (%)', 'Net Profit Margin (%)'] if c in df_trend.columns]
    
    if kolom_margin:
        fig_margin = px.line(df_trend, x=df_trend.index, y=kolom_margin, markers=True,
                             labels={'value': 'Persentase (%)', 'index': 'Kuartal'},
                             color_discrete_sequence=['#66BB6A', '#FFA726', '#AB47BC'])
        fig_margin.update_layout(yaxis_title="Margin (%)", legend_title="Rasio Keuangan", hovermode="x unified")
        
        st.plotly_chart(fig_margin, use_container_width=True)
        st.markdown("""
        **Panduan Membaca Margin:**
        * **Gross Profit Margin (Hijau):** Mengukur efisiensi produksi. Semakin tinggi, semakin murah biaya dasar untuk membuat/mendistribusikan produk.
        * **Net Profit Margin (Ungu):** Persentase laba murni perusahaan dari total pendapatan, setelah dipotong operasional, bunga, dan pajak.
        """)
    else:
        st.warning("Data komponen laba tidak mencukupi untuk menghitung margin.")

# ----------------- TAB 3: WATERFALL & BEBAN -----------------
with tab3:
    col_w1, col_w2 = st.columns([1.2, 1])
    
    with col_w1:
        st.subheader(f"Alur Laba Rugi ({teks_periode})")
        
        fig_waterfall = go.Figure(go.Waterfall(
            name="Laba Rugi", orientation="v",
            measure=["absolute", "relative", "total", "relative", "total"],
            x=["Pendapatan", "Beban Pokok", "Laba Kotor", "Total Beban Usaha", "Laba Sblm Pajak/Lainnya"],
            textposition="outside",
            texttemplate="%{y:,.0f}",
            y=[pend_ini, cogs_ini * -1 if cogs_ini > 0 else cogs_ini, 0, 
               total_beban_usaha * -1 if total_beban_usaha > 0 else total_beban_usaha, 0],
            decreasing={"marker": {"color": "#FF5252"}},
            increasing={"marker": {"color": "#26A69A"}},
            totals={"marker": {"color": "#29B6F6"}}
        ))
        fig_waterfall.update_layout(margin=dict(t=30, b=0, l=0, r=0))
        st.plotly_chart(fig_waterfall, use_container_width=True)
        
    with col_w2:
        st.subheader("Komposisi Beban Usaha")
        if beban_aktual:
            fig_pie = px.pie(df_beban_pie, values='Nilai', names='Beban', hole=0.5, 
                             color_discrete_sequence=px.colors.qualitative.Pastel1)
            fig_pie.update_layout(margin=dict(t=30, b=0, l=0, r=0), legend=dict(orientation="h", y=-0.2))
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.warning("Data kolom beban spesifik tidak ditemukan.")