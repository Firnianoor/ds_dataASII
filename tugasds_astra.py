import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

# ==========================================
# 1. KONFIGURASI HALAMAN & TEMA DARK MODE
# ==========================================
st.set_page_config(page_title="Dasbor Keuangan", layout="wide", initial_sidebar_state="expanded")
pio.templates.default = "plotly_dark"

st.markdown("""
    <style>
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
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

# ==========================================
# 2. FUNGSI PEMROSESAN DATA KEUANGAN
# ==========================================
@st.cache_data
def process_financial_data(file_obj_or_path, is_csv=True):
    if is_csv:
        df = pd.read_csv(file_obj_or_path)
    else:
        df = pd.read_excel(file_obj_or_path)
        
    df = df.fillna(0)
    
    for col in df.columns[1:]:
        df[col] = df[col].astype(str).str.replace(',', '', regex=False)
        df[col] = df[col].astype(str).str.replace(' B', '', regex=False)
        df[col] = df[col].astype(str).str.replace('%', '', regex=False)
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
    df.set_index(df.columns[0], inplace=True)
    df_t = df.transpose()
    df_t = df_t.iloc[::-1] 
    
    kolom_baru = []
    hitungan = {}
    for nama in df_t.columns:
        nama_str = str(nama).strip()
        if nama_str not in hitungan:
            hitungan[nama_str] = 0
            kolom_baru.append(nama_str)
        else:
            hitungan[nama_str] += 1
            kolom_baru.append(f"{nama_str} {hitungan[nama_str]}")
    df_t.columns = kolom_baru
    
    if 'Total Pendapatan' in df_t.columns:
        if 'Laba Kotor' in df_t.columns:
            df_t['Gross Profit Margin'] = (df_t['Laba Kotor'] / df_t['Total Pendapatan']) * 100
        
        laba_usaha_cols = [c for c in df_t.columns if 'Laba Sebelum Pajak' in c or 'Laba Usaha' in c]
        if laba_usaha_cols:
            df_t['Operating Margin'] = (df_t[laba_usaha_cols[0]] / df_t['Total Pendapatan']) * 100
            
        laba_bersih_cols = [c for c in df_t.columns if 'Laba Bersih' in c or 'Laba Bersih Tahun Berjalan' in c]
        if laba_bersih_cols:
            df_t['Net Profit Margin'] = (df_t[laba_bersih_cols[0]] / df_t['Total Pendapatan']) * 100
            
    return df_t

# ==========================================
# 3. FUNGSI RENDER DASBOR UTAMA
# ==========================================
def render_dashboard(df_plot, dashboard_title):
    st.title(dashboard_title)
    
    st.sidebar.subheader("Filter Analisis")
    daftar_kuartal = df_plot.index.tolist()
    rentang_terpilih = st.sidebar.select_slider(
        "Pilih Rentang Waktu",
        options=daftar_kuartal,
        value=(daftar_kuartal[0], daftar_kuartal[-1])
    )

    kuartal_awal, kuartal_akhir = rentang_terpilih
    idx_awal = daftar_kuartal.index(kuartal_awal)
    idx_akhir = daftar_kuartal.index(kuartal_akhir)
    df_trend = df_plot.iloc[idx_awal:idx_akhir + 1]

    laba_bersih_col = [col for col in df_plot.columns if 'Laba Bersih' in col]
    lb_nama = laba_bersih_col[0] if laba_bersih_col else None
    beban_aktual = [col for col in df_plot.columns if any(b in col for b in ['Beban Penjualan', 'Beban Umum', 'Beban Usaha', 'Beban Operasional'])]

    pend_ini = df_trend.get('Total Pendapatan', pd.Series([0])).sum()
    cogs_ini = df_trend.get('Total Beban Pokok Penjualan', pd.Series([0])).sum()
    laba_kotor_ini = df_trend.get('Laba Kotor', pd.Series([0])).sum()
    laba_bersih_ini = df_trend[lb_nama].sum() if lb_nama else 0
    npm_ini = (laba_bersih_ini / pend_ini * 100) if pend_ini != 0 else 0
    total_beban_usaha = df_trend[beban_aktual].sum().sum() if len(beban_aktual) > 0 else 0
    df_beban_pie = pd.DataFrame({'Beban': beban_aktual, 'Nilai': df_trend[beban_aktual].sum().values})

    is_single_quarter = (idx_awal == idx_akhir)

    if is_single_quarter and idx_awal > 0:
        teks_periode = f"Kuartal {kuartal_awal}"
        status_total = False
        data_q_lalu = df_plot.iloc[idx_awal - 1]
        pend_lalu = data_q_lalu.get('Total Pendapatan', 0)
        laba_kotor_lalu = data_q_lalu.get('Laba Kotor', 0)
        laba_bersih_lalu = data_q_lalu[lb_nama] if lb_nama else 0
        npm_lalu = data_q_lalu.get('Net Profit Margin', 0)
    else:
        teks_periode = f"Rentang {kuartal_awal} hingga {kuartal_akhir}" if not is_single_quarter else f"Kuartal {kuartal_awal}"
        status_total = True
        pend_lalu, laba_kotor_lalu, laba_bersih_lalu, npm_lalu = 0, 0, 0, 0

    st.markdown(f"**Ringkasan Kinerja Periode {teks_periode}**")

    def tampilkan_kpi(judul, nilai_sekarang, nilai_lalu, format_persen=False, status_total=False):
        if status_total:
            delta_str = "Total Akumulasi"
            warna_delta = "kpi-neutral"
        else:
            selisih = nilai_sekarang - nilai_lalu
            pertumbuhan = (selisih / abs(nilai_lalu)) * 100 if nilai_lalu != 0 else 0
            simbol_arah = "▲" if selisih > 0 else "▼" if selisih < 0 else "▬"
            warna_delta = "kpi-delta-up" if selisih >= 0 else "kpi-delta-down"
            delta_str = f"{simbol_arah} {abs(selisih):.2f} Bps QoQ" if format_persen else f"{simbol_arah} Rp {abs(selisih):,.0f} M {pertumbuhan:.1f}% QoQ"
                
        val_str = f"{nilai_sekarang:.2f}%" if format_persen else f"Rp {nilai_sekarang:,.0f} M"
        st.markdown(f'<div class="kpi-card"><div class="kpi-title">{judul.upper()}</div><div class="kpi-value">{val_str}</div><div class="{warna_delta}">{delta_str}</div></div>', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1: tampilkan_kpi("Total Pendapatan", pend_ini, pend_lalu, status_total=status_total)
    with col2: tampilkan_kpi("Laba Kotor", laba_kotor_ini, laba_kotor_lalu, status_total=status_total)
    with col3: tampilkan_kpi("Laba Bersih", laba_bersih_ini, laba_bersih_lalu, status_total=status_total)
    with col4: tampilkan_kpi("Net Profit Margin", npm_ini, npm_lalu, format_persen=True, status_total=status_total)

    st.write("---")

    # KESIMPULAN & INTERPRETASI DINAMIS
    st.markdown("### Kesimpulan dan Interpretasi Kinerja")
    
    if is_single_quarter and idx_awal > 0:
        pertumbuhan_pend = ((pend_ini - pend_lalu) / abs(pend_lalu)) * 100 if pend_lalu != 0 else 0
        arah_tumbuh = "meningkat" if pertumbuhan_pend > 0 else "menurun"
        kondisi_npm = "sangat sehat" if npm_ini > 10 else "cukup baik" if npm_ini > 0 else "berada pada fase rugi"
        
        narasi = f"Pada periode **{kuartal_awal}**, entitas mencatatkan total pendapatan sebesar **Rp {pend_ini:,.0f} Miliar**. "
        narasi += f"Perolehan ini **{arah_tumbuh} sebesar {abs(pertumbuhan_pend):.1f}%** jika dikomparasikan dengan kuartal sebelumnya. "
        narasi += f"Dari sisi efisiensi operasional, Margin Laba Bersih perusahaan bertengger di level **{npm_ini:.2f}%**, yang mengindikasikan profitabilitas tergolong **{kondisi_npm}**."
        st.info(narasi)
    else:
        kondisi_npm = "solid" if npm_ini > 10 else "rentan" if npm_ini < 5 else "stabil"
        narasi = f"Sepanjang observasi dari **{kuartal_awal} hingga {kuartal_akhir}**, sistem mengakumulasi total pendapatan sebesar **Rp {pend_ini:,.0f} Miliar**. "
        narasi += f"Selama rentang waktu ini, perusahaan rata-rata mampu mengonversi pendapatannya menjadi laba bersih dengan persentase **{npm_ini:.2f}%**. "
        narasi += f"Skala persentase ini menunjukkan tingkat margin keuntungan yang secara keseluruhan tergolong **{kondisi_npm}**."
        st.info(narasi)
        
    st.write("---")

    tab1, tab2, tab3 = st.tabs(["Tren Pendapatan", "Profitabilitas dan Margin", "Struktur Biaya"])

    with tab1:
        st.subheader("Historis Tren Pendapatan dan Beban Pokok")
        if 'Total Pendapatan' in df_trend.columns and 'Total Beban Pokok Penjualan' in df_trend.columns:
            fig_line = px.area(df_trend, x=df_trend.index, y=['Total Pendapatan', 'Total Beban Pokok Penjualan'],
                               labels={'value': 'Nominal IDR', 'index': 'Periode'},
                               color_discrete_map={'Total Pendapatan': '#29B6F6', 'Total Beban Pokok Penjualan': '#EF5350'})
            fig_line.update_layout(hovermode="x unified", legend_title="Komponen")
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.warning("Variabel Pendapatan atau Beban Pokok Penjualan tidak ditemukan dalam data")

    with tab2:
        st.subheader("Tingkat Efisiensi dan Margin Keuntungan")
        kolom_margin = [c for c in ['Gross Profit Margin', 'Operating Margin', 'Net Profit Margin'] if c in df_trend.columns]
        if kolom_margin:
            fig_margin = px.line(df_trend, x=df_trend.index, y=kolom_margin, markers=True, labels={'value': 'Persentase %', 'index': 'Periode'}, color_discrete_sequence=['#66BB6A', '#FFA726', '#AB47BC'])
            fig_margin.update_layout(hovermode="x unified", legend_title="Indikator Margin")
            st.plotly_chart(fig_margin, use_container_width=True)
        else:
            st.warning("Data komponen laba tidak mencukupi untuk menghitung rasio margin")

    with tab3:
        # Perbaikan Kalkulasi Waterfall agar label teks memunculkan angka yang benar
        val_pend = pend_ini
        val_cogs = -abs(cogs_ini) if cogs_ini != 0 else 0
        val_laba_kotor = val_pend + val_cogs
        val_beban = -abs(total_beban_usaha) if total_beban_usaha != 0 else 0
        val_sisa_laba = val_laba_kotor + val_beban
        
        fig_waterfall = go.Figure(go.Waterfall(
            name="Laba Rugi", orientation="v", measure=["absolute", "relative", "total", "relative", "total"],
            x=["Pendapatan", "Beban Pokok", "Laba Kotor", "Total Beban", "Sisa Laba"],
            textposition="outside", texttemplate="%{y:,.0f}",
            y=[val_pend, val_cogs, val_laba_kotor, val_beban, val_sisa_laba],
            decreasing={"marker": {"color": "#FF5252"}}, increasing={"marker": {"color": "#26A69A"}}, totals={"marker": {"color": "#29B6F6"}}
        ))
        fig_waterfall.update_layout(margin=dict(t=30, b=0, l=0, r=0))
        
        # Logika UI/UX Responsif: Jika Pie Chart kosong, Waterfall dilebarkan
        if beban_aktual and total_beban_usaha > 0:
            col_w1, col_w2 = st.columns([1.2, 1])
            with col_w1:
                st.subheader("Alur Laba Rugi")
                st.plotly_chart(fig_waterfall, use_container_width=True)
                
            with col_w2:
                st.subheader("Komposisi Beban Usaha")
                fig_pie = px.pie(df_beban_pie, values='Nilai', names='Beban', hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel1)
                fig_pie.update_layout(margin=dict(t=30, b=0, l=0, r=0), legend=dict(orientation="h", y=-0.2))
                st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.subheader("Alur Laba Rugi")
            st.plotly_chart(fig_waterfall, use_container_width=True)
            st.info("Visualisasi Komposisi Beban Usaha disembunyikan karena rincian data operasional tidak ditemukan pada dataset ini.")

# ==========================================
# 4. SISTEM NAVIGASI & ROUTING 
# ==========================================
st.sidebar.title("Navigasi Dasbor")
menu = st.sidebar.radio("Pilih Modul Data", [
    "Dasbor Laporan Astra", 
    "Unggah Laporan Mandiri"
])

st.sidebar.divider()
st.sidebar.info("Sistem ini memetakan kesehatan finansial melalui struktur komponen Laba-Rugi dan efisiensi operasional")

if menu == "Dasbor Laporan Astra":
    try:
        df_astra = process_financial_data("dataset_astra.csv", is_csv=True)
        render_dashboard(df_astra, "Dasbor Kinerja Keuangan Astra")
    except Exception as e:
        st.error(f"Gagal memuat file dataset_astra.csv. Pastikan file berada di direktori yang sama. Detail Error {e}")

elif menu == "Unggah Laporan Mandiri":
    st.title("Interaktif Dasbor Laporan Keuangan Eksternal")
    st.markdown("""
    Modul ini memfasilitasi Anda untuk mengunggah dan menganalisis laporan laba rugi entitas bisnis lain. 
    Mesin akan membaca pola data dan merangkai kesimpulan secara otomatis.
    """)
    
    with st.expander("Syarat Struktur Data dan Contoh Format", expanded=True):
        st.write("""
        Pastikan file CSV atau Excel Anda mengikuti struktur dasar berikut
        * **Kolom Pertama** Berisi nama indikator keuangan (Total Pendapatan, Laba Kotor, dll)
        * **Kolom Selanjutnya** Merupakan Periode Waktu berurutan (Q1 2023, Q2 2023, dst)
        """)
        
        st.markdown("**Pratinjau Format Ideal**")
        
        try:
            df_contoh = pd.read_csv("dataset_astra.csv")
            st.dataframe(df_contoh.head(4), use_container_width=True, hide_index=True)
        except Exception:
            st.info("Catatan File panduan format tidak ditemukan, namun Anda tetap bisa mengunggah dataset Anda")

    uploaded_file = st.file_uploader("Seret dan lepaskan file CSV atau Excel di sini", type=['csv', 'xlsx'])
    
    if uploaded_file is not None:
        try:
            is_csv = uploaded_file.name.endswith('.csv')
            
            st.success("File berhasil diunggah. Berikut cuplikan data mentah Anda")
            if is_csv:
                df_preview = pd.read_csv(uploaded_file)
            else:
                df_preview = pd.read_excel(uploaded_file)
            st.dataframe(df_preview.head(5), use_container_width=True)
            
            uploaded_file.seek(0) 
            st.divider()
            
            df_custom = process_financial_data(uploaded_file, is_csv=is_csv)
            render_dashboard(df_custom, "Dasbor Kinerja Keuangan Kustom")
            
        except Exception as e:
            st.error(f"Sistem gagal mengeksekusi perhitungan. Detail Error {e}")
