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

# Kustomisasi CSS untuk Metrik Card agar rapi dan elegan (Dark Theme)
st.markdown("""
    <style>
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
    </style>
""", unsafe_allow_html=True)

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
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/2830/2830284.png", width=100) # Placeholder logo
st.sidebar.title("Filter Analisis")

# Membuat dropdown untuk memilih periode kuartal spesifik
daftar_kuartal = df_plot.index.tolist()
kuartal_terpilih = st.sidebar.selectbox("Pilih Kuartal Analisis:", daftar_kuartal, index=len(daftar_kuartal)-1)

# Mencari index dari kuartal yang dipilih untuk perbandingan (QoQ)
idx_terpilih = daftar_kuartal.index(kuartal_terpilih)
data_q_ini = df_plot.iloc[idx_terpilih]

# Data kuartal sebelumnya (jika ada) untuk hitung Growth/Delta
if idx_terpilih > 0:
    data_q_lalu = df_plot.iloc[idx_terpilih - 1]
else:
    data_q_lalu = data_q_ini # Jika data paling awal, delta = 0

# ==========================================
# 4. KPI SCORECARD (BERDASARKAN FILTER)
# ==========================================
st.title("📊 Financial Performance Dashboard")
st.markdown(f"**Analisis Kinerja Keuangan | Periode: {kuartal_terpilih}**")

def tampilkan_kpi(judul, nilai_sekarang, nilai_lalu, format_persen=False):
    selisih = nilai_sekarang - nilai_lalu
    if nilai_lalu != 0:
        pertumbuhan = (selisih / abs(nilai_lalu)) * 100
    else:
        pertumbuhan = 0
        
    simbol_arah = "▲" if selisih > 0 else "▼" if selisih < 0 else "▬"
    warna_delta = "kpi-delta-up" if selisih >= 0 else "kpi-delta-down"
    
    if format_persen:
        val_str = f"{nilai_sekarang:.2f}%"
        delta_str = f"{simbol_arah} {abs(selisih):.2f}% (Bps)"
    else:
        val_str = f"Rp {nilai_sekarang:,.0f} M"
        delta_str = f"{simbol_arah} Rp {abs(selisih):,.0f} M ({pertumbuhan:.1f}%) QoQ"
        
    st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">{judul.upper()}</div>
            <div class="kpi-value">{val_str}</div>
            <div class="{warna_delta}">{delta_str}</div>
        </div>
    """, unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)

with col1:
    tampilkan_kpi("Total Pendapatan", data_q_ini.get('Total Pendapatan', 0), data_q_lalu.get('Total Pendapatan', 0))
with col2:
    tampilkan_kpi("Laba Kotor", data_q_ini.get('Laba Kotor', 0), data_q_lalu.get('Laba Kotor', 0))
with col3:
    laba_bersih_col = [col for col in df_plot.columns if 'Laba Bersih Tahun Berjalan' in col]
    lb_nama = laba_bersih_col[0] if laba_bersih_col else None
    val_lb_ini = data_q_ini[lb_nama] if lb_nama else 0
    val_lb_lalu = data_q_lalu[lb_nama] if lb_nama else 0
    tampilkan_kpi("Laba Bersih", val_lb_ini, val_lb_lalu)
with col4:
    tampilkan_kpi("Net Profit Margin", data_q_ini.get('Net Profit Margin (%)', 0), data_q_lalu.get('Net Profit Margin (%)', 0), format_persen=True)

st.write("---")

# ==========================================
# 5. SISTEM TAB UNTUK ANALISIS MENDALAM
# ==========================================
tab1, tab2, tab3 = st.tabs(["📈 Tren & Pertumbuhan", "💰 Analisis Profitabilitas (Margin)", "🏢 Struktur Biaya & Alur Laba"])

# ----------------- TAB 1: TREN PENDAPATAN -----------------
with tab1:
    st.subheader("Historis Tren Pendapatan vs Beban Pokok")
    fig_line = px.area(df_plot, x=df_plot.index, y=['Total Pendapatan', 'Total Beban Pokok Penjualan'],
                       labels={'value': 'Miliar IDR', 'index': 'Kuartal'},
                       color_discrete_map={'Total Pendapatan': '#29B6F6', 'Total Beban Pokok Penjualan': '#EF5350'})
    fig_line.update_layout(xaxis_title="Kuartal Historis", yaxis_title="Nominal (Miliar IDR)", legend_title="Komponen", hovermode="x unified")
    
    # Menambahkan garis vertikal penanda kuartal yang dipilih
    fig_line.add_vline(x=kuartal_terpilih, line_width=2, line_dash="dash", line_color="#00E676", annotation_text="Periode Terpilih", annotation_position="top left")
    
    st.plotly_chart(fig_line, use_container_width=True)
    
    st.info("💡 **Insight:** Area grafik menunjukkan jarak antara Pendapatan dan Beban Pokok. Semakin lebar jarak warna biru di atas warna merah, semakin besar Laba Kotor yang dihasilkan perusahaan.")

# ----------------- TAB 2: ANALISIS MARGIN -----------------
with tab2:
    st.subheader("Analisis Tingkat Efisiensi & Margin Keuntungan")
    kolom_margin = [c for c in ['Gross Profit Margin (%)', 'Operating Margin (%)', 'Net Profit Margin (%)'] if c in df_plot.columns]
    
    if kolom_margin:
        fig_margin = px.line(df_plot, x=df_plot.index, y=kolom_margin, markers=True,
                             labels={'value': 'Persentase (%)', 'index': 'Kuartal'},
                             color_discrete_sequence=['#66BB6A', '#FFA726', '#AB47BC'])
        fig_margin.update_layout(yaxis_title="Margin (%)", legend_title="Rasio Keuangan", hovermode="x unified")
        fig_margin.add_vline(x=kuartal_terpilih, line_width=1, line_dash="dash", line_color="white")
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
    
    # Kiri: Waterfall khusus untuk Kuartal yang difilter
    with col_w1:
        st.subheader(f"Alur Laba Rugi ({kuartal_terpilih})")
        
        beban_aktual = [col for col in df_plot.columns if any(b in col for b in ['Beban Penjualan', 'Beban Umum', 'Beban Usaha'])]
        total_beban_usaha = data_q_ini[beban_aktual].sum() if len(beban_aktual) > 0 else 0
        
        # Ambil nilai dengan default 0 jika kolom tidak ada
        pend_val = data_q_ini.get('Total Pendapatan', 0)
        cogs_val = data_q_ini.get('Total Beban Pokok Penjualan', 0)
        
        fig_waterfall = go.Figure(go.Waterfall(
            name="Laba Rugi", orientation="v",
            measure=["absolute", "relative", "total", "relative", "total"],
            x=["Pendapatan", "Beban Pokok", "Laba Kotor", "Total Beban Usaha", "Laba Sblm Pajak/Lainnya"],
            textposition="outside",
            texttemplate="%{y:,.0f}",
            y=[pend_val, cogs_val * -1 if cogs_val > 0 else cogs_val, 0, 
               total_beban_usaha * -1 if total_beban_usaha > 0 else total_beban_usaha, 0],
            decreasing={"marker": {"color": "#FF5252"}},
            increasing={"marker": {"color": "#26A69A"}},
            totals={"marker": {"color": "#29B6F6"}}
        ))
        fig_waterfall.update_layout(margin=dict(t=30, b=0, l=0, r=0))
        st.plotly_chart(fig_waterfall, use_container_width=True)
        
    # Kanan: Komposisi Beban
    with col_w2:
        st.subheader("Komposisi Beban Usaha")
        if beban_aktual:
            # Tampilkan bar chart hanya untuk kuartal terpilih agar lebih relevan dengan waterfall
            df_beban_pie = pd.DataFrame({'Beban': beban_aktual, 'Nilai': data_q_ini[beban_aktual].values})
            fig_pie = px.pie(df_beban_pie, values='Nilai', names='Beban', hole=0.5, 
                             color_discrete_sequence=px.colors.qualitative.Pastel1)
            fig_pie.update_layout(margin=dict(t=30, b=0, l=0, r=0), legend=dict(orientation="h", y=-0.2))
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.warning("Data kolom beban spesifik tidak ditemukan.")