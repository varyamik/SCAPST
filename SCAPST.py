import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from astroquery.gaia import Gaia
from astroquery.vizier import Vizier
import astropy.units as u
from astropy.coordinates import SkyCoord

# Page configuration
st.set_page_config(
    page_title="Star Cluster Astrometry Parameters Selection Tool",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# UI Styles
st.markdown("""
    <style>
    .stApp { 
        background-color: #AEC0FC; 
        color: #000000; 
    }

    /* Отключаем эффект полупрозрачности/затемнения при пересчете */
    .stApp {
        opacity: 1 !important;
    }
    /* Скрываем плавающий индикатор загрузки в правом верхнем углу */
    [data-testid="stStatusWidget"] {
        display: none !important;
    }

    div.stSelectbox div[data-baseweb="select"] {
        background-color: #FFFFFF;     
        border-radius: 8px;            
        border: 1px solid #000000;     
        min-height: 32px; 
        font-size: 14px;
    }
    div.stSelectbox div[data-baseweb="select"] span {
        color: #000000;
    }
    div[data-baseweb="select"] ul li:hover {
        background-color: #CED9FD !important;
        color: #000000 !important;            
    }
    div[role="listbox"] div {
        background-color: #FFFFFF;
        color: #000000;
    }
    
    .stat-card {
        background-color: #CED9FD;
        border: 1px solid #95A4D7;
        padding: 10px;
        border-radius: 8px;
        text-align: center;
        font-size: 14px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        min-height: 60px;
        margin-bottom: 20px;
    }
    .coord-info {
        background-color: #CED9FD;
        border: 1px solid #95A4D7;
        padding: 10px;
        border-radius: 8px;
        font-size: 14px;
        text-align: center;
        height: 40px;
        margin-top: 27px;
    }
    
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #CED9FD !important;
        border: 1px solid #95A4D7 !important;
        border-radius: 8px;
        margin-bottom: 10px;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] > div {
        padding: 10px !important;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stVerticalBlock"] {
        gap: 10px !important;
    }

    /* Кнопка Calculate (Primary) */
    div.st-key-calc_btn button {
        background-color: #00A150 !important;
        border: none !important;
        box-shadow: none !important;
    }
    div.st-key-calc_btn button p, 
    div.st-key-calc_btn button span {
        color: #FFFFFF !important;
        font-size: 18px !important;
        font-weight: bold !important;
    }
    div.st-key-calc_btn button:hover {
        background-color: #008240 !important;
    }

    /* Кнопка Reset (Secondary) */
    div.st-key-reset_btn button {
        background-color: #A10051 !important;
        border: none !important;
        box-shadow: none !important;
    }
    div.st-key-reset_btn button p, 
    div.st-key-reset_btn button span {
        color: #FFFFFF !important;
        font-size: 18px !important;
        font-weight: bold !important;
    }
    div.st-key-reset_btn button:hover {
        background-color: #820041 !important;
    }

    /* Кнопка Save table */
    div.st-key-save_csv_btn button {
        background-color: #00A150 !important;
        border: none !important;
        box-shadow: none !important;
    }
    div.st-key-save_csv_btn button p, 
    div.st-key-save_csv_btn button span {
        color: #FFFFFF !important;
        font-size: 18px !important;
        font-weight: bold !important;
    }
    div.st-key-save_csv_btn button:hover {
        background-color: #008240 !important;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center;'>Star Cluster Astrometry Parameters Selection Tool</h1>", unsafe_allow_html=True)
st.markdown("<div style='text-align: center; font-size: 20px;'>Web-version of the research application for open star clusters analysis in the browser</div>", unsafe_allow_html=True)

# Detailed Instructions Panel
st.markdown("""
<div style="background-color: #CED9FD; border: 1px solid #95A4D7; padding: 17px; border-radius: 8px; margin-top: 17px; margin-bottom: 20px; font-size: 16px; line-height: 1.5;">
    <b>Short Guide:</b><br><br>
    This tool helps determine the optimal astrometric parameter ranges to separate a star cluster from Galactic field stars using Gaia data.<br><br>
    <b>First, use the left panel</b> (Select Parameters) to configure the astrometric intervals and collect statistics. By default, the application is loaded with the NGC 6124 cluster as an introductory example, but you can select any cluster from the Dias et al. (2021) catalog via the <b>Cluster</b> dropdown, and its parameters will load automatically. When setting up your initial parameters, it is strongly recommended to <b>start with the widest</b> possible intervals (<b>&plusmn3-5 mas/yr</b> for proper motion and <b>&plusmn0.5-0.8 mas</b> for parallax) and narrow them down gradually. This approach ensures correct performance during the statistical analysis stage and saves time, as expanding intervals triggers a re-query to the Gaia catalog.<br><br>
    Once your statistics are gathered, you can proceed to the right panel (Search for Plateau & Completeness) to analyze the optimal parameter corridors.
</div>
""", unsafe_allow_html=True)


# ==========================================
# 1. HELPER FUNCTIONS AND CLASSES
# ==========================================

class LinDens:
    def __init__(self, d):
        self.outer_min, self.inner_min, self.inner_max, self.outer_max = [float(x) for x in d]

    def count_ibdens(self):
        self.ibound = int((self.outer_max - self.outer_min) / self.step)
        if self.ibound <= 0:
            self.ibound = 1
        self.dens = np.zeros((2, self.ibound))

    def count_densstep(self):
        for i in range(self.ibound):
            self.dens[0][i] = self.outer_min + i * self.step

    def interval(self):
        if self.r < self.delta:
            self.imin = 0
        else:
            self.imin = int((self.r - self.delta) / self.step)
        if self.imin > self.ibound:
            raise ValueError('Out of bounds')
        self.imax = int((self.r + self.delta) / self.step)
        if self.imax > self.ibound:
            self.imax = self.ibound

    def calculate_dens(self):
        for i in range(self.imin, self.imax):
            ri = i * self.step
            bracket = 1.0 - (self.r - ri)**2 / self.delta**2
            if bracket < 0.0:
                bracket = 0.0
            self.dens[1][i] += 15.0 * bracket**2 / 16.0 / self.delta

    def is_between(self):
        return self.inner_min <= self.dot <= self.inner_max


def findcentres(inarr, maglim, delta, step, a, d, z):
    muald, mudld, plxld = LinDens(a), LinDens(d), LinDens(z)
    muald.delta = delta 
    muald.step = step
    mudld.delta, mudld.step = muald.delta, muald.step
    plxld.delta, plxld.step = muald.delta, muald.step
    
    for ld in (muald, mudld, plxld):
        ld.count_ibdens()
        ld.count_densstep()
    
    for plxld.dot, muald.dot, mudld.dot, mag in inarr:
        if mag > maglim:
            continue
        try:
            for ld in (muald, mudld, plxld):
                ld.r = ld.dot - ld.outer_min
                ld.interval()
        except ValueError:
            continue
        if mudld.is_between():
            muald.calculate_dens()
        if muald.is_between():
            mudld.calculate_dens()
        if plxld.is_between():
            plxld.calculate_dens()
    
    for ld in (muald, mudld, plxld):
        if ld.ibound > 0 and np.max(ld.dens[1]) > 0:
            ld.maxim = ld.dens[0][np.argmax(ld.dens[1])]
        else:
            ld.maxim = np.nan

    return muald.maxim, mudld.maxim, plxld.maxim


@st.cache_data(show_spinner=False)
def fetch_dias_clusters():
    try:
        v = Vizier(row_limit=2000)
        result = v.get_catalogs('J/MNRAS/504/356')
        if result and len(result) > 0:
            for table_key in result.keys():
                df_c = result[table_key].to_pandas()
                for col in ['Cl*', 'Name', 'Cluster']:
                    if col in df_c.columns:
                        sample = df_c[col].dropna().iloc[0] if not df_c[col].dropna().empty else ''
                        if isinstance(sample, bytes):
                            df_c['Name'] = df_c[col].str.decode('utf-8', errors='ignore').str.strip()
                        else:
                            df_c['Name'] = df_c[col].astype(str).str.strip()
                        return df_c
            df_c = result[0].to_pandas()
            for col in df_c.columns:
                if 'cl' in col.lower() or 'name' in col.lower():
                    df_c['Name'] = df_c[col].astype(str).str.strip()
                    return df_c
    except Exception as e:
        st.error(f"Error loading Dias clusters: {e}")
    return None


@st.cache_data(show_spinner=True)
def fetch_gaia_data_adql(table_name, 
                         l_center, b_center, 
                         pmra_min, pmra_max, 
                         pmdec_min, pmdec_max, 
                         plx_min, plx_max, 
                         radius_am, mag_limit, max_rows):
    
    if max_rows == "Unlimited (it will take loooong...)":
        top_str = "" 
        st.warning(f"You chose \"Unlimited\". High risk of server timeout (Error 500) for dense sky regions.")
    else:
        top_str = f"TOP {max_rows}"
        
    r_deg = radius_am * 3 / 60.0
    query = f"""
    SELECT TOP {max_rows} 
    source_id, ra, ra_error, dec, dec_error, l, b, 
    parallax, parallax_error, pmra, pmra_error, pmdec, pmdec_error, 
    phot_g_mean_mag, phot_bp_mean_mag, phot_rp_mean_mag, bp_rp
    FROM {table_name}
    WHERE l BETWEEN {l_center-r_deg} and {l_center+r_deg} AND b BETWEEN {b_center-r_deg} and {b_center+r_deg}
    AND pmra BETWEEN {pmra_min} and {pmra_max} AND pmdec BETWEEN {pmdec_min} and {pmdec_max}
    AND parallax BETWEEN {plx_min} and {plx_max}
    AND phot_g_mean_mag <= {mag_limit}
    """
    # Создаем виджет прогресс-бара внутри функции
    progress_bar = st.progress(0, text="Initializing query...")
    
    try:
        if max_rows == "Unlimited (it will take loooong...)":
            Gaia.ROW_LIMIT = -1
        else:
            Gaia.ROW_LIMIT = int(max_rows)

        # Шаг 1: Отправка асинхронной задачи на сервер Gaia
        progress_bar.progress(25, text="Sending query to Gaia archive...")
        job = Gaia.launch_job_async(query, dump_to_file=False)
        
        # Шаг 2: Получение и скачивание результатов
        progress_bar.progress(60, text="Downloading dataset from server...")
        r = job.get_results()
        
        # Шаг 3: Конвертация в Pandas DataFrame
        progress_bar.progress(85, text="Processing data into DataFrame...")
        df = r.to_pandas()

        if 'bp_rp' not in df.columns or df['bp_rp'].isna().all():
            if 'phot_bp_mean_mag' in df.columns and 'phot_rp_mean_mag' in df.columns:
                df['bp_rp'] = df['phot_bp_mean_mag'] - df['phot_rp_mean_mag']
            else:
                df['bp_rp'] = 0.0
                
        cleaned_df = df.dropna(subset=['parallax', 'pmra', 'pmdec', 'phot_g_mean_mag', 'l', 'b'])
        
        # Успешное завершение
        progress_bar.progress(100, text=f"Done! Successfully loaded {len(cleaned_df):,} sources.")
        return cleaned_df
        
    except Exception as e:
        progress_bar.empty() # Убираем прогресс-бар при ошибке
        st.error(f"ADQL Query Error (Large dataset timeout/SSL): {e}")
        return None


def get_tap_table_name(gaia_release_str):
    if "EDR3" in gaia_release_str: return "gaiaedr3.gaia_source"
    elif "DR2" in gaia_release_str: return "gaiadr2.gaia_source"
    else: return "gaiadr3.gaia_source"


def plotting_diagramms(a, x, y, xval, yval):
    a.clear()
    a.scatter(x, y, s=0.1, c='k', alpha=0.6)
    a.set_xlabel(xval, fontsize=12)
    a.set_ylabel(yval, fontsize=12)
    a.set_xlim(min(x), max(x))
    a.set_ylim(min(y), max(y))


def plot_cluster_diagrams(df_sel, df, radius_am, l_med, b_med):
    bg_color = 'None'#"#AEC0FC"
    fig1 = plt.figure(figsize=(8, 4), facecolor=bg_color, dpi=300, constrained_layout=True)
    
    ax1 = fig1.add_subplot(1, 2, 1)
    if 'bp_rp' in df_sel.columns and len(df_sel) > 0:
        plotting_diagramms(ax1, df_sel['bp_rp'], df_sel['phot_g_mean_mag'], r"$BP - RP$", r"$M_G$")
        ax1.set_box_aspect(1)
        ax1.invert_yaxis()

    ax2 = fig1.add_subplot(1, 2, 2)
    if len(df) > 0:
        plotting_diagramms(ax2, df_sel['l'], df_sel['b'], r"$l, deg$", r"$b, deg$")
        R_cl = radius_am
        if R_cl != ' ':
            circle = Circle((l_med, b_med), float(R_cl)/60, clip_on=False, zorder=10, linewidth=1.2, edgecolor='k', facecolor=(0, 0, 0, .0125))
            ring = Circle((l_med, b_med), float(R_cl)*np.sqrt(2)/60, clip_on=False, zorder=10, linewidth=1.2, edgecolor='k', facecolor=(0, 0, 0, .0125))
        ax2.add_artist(circle)
        ax2.add_artist(ring)
        ax2.set_box_aspect(1)

    fig2 = plt.figure(figsize=(8, 2), facecolor=bg_color, dpi=300, constrained_layout=True)
    
    ax3 = fig2.add_subplot(1, 3, 1)
    if len(df_sel) > 0:
        plotting_diagramms(ax3, df_sel['phot_g_mean_mag'], df_sel['pmra'], r"$G, mag$", r"$\mu_\alpha, mas/yr$")

    ax4 = fig2.add_subplot(1, 3, 2)
    if len(df_sel) > 0:
        plotting_diagramms(ax4, df_sel['phot_g_mean_mag'], df_sel['pmdec'], r"$G, mag$", r"$\mu_\delta, mas/yr$")

    ax5 = fig2.add_subplot(1, 3, 3)
    if len(df_sel) > 0:
        plotting_diagramms(ax5, df_sel['phot_g_mean_mag'], df_sel['parallax'], r"$G, mag$", r"$\varpi, mas$")
        
    plt.tight_layout()
    return fig1, fig2


# ==========================================
# 2. UI AND APPLICATION CLASS
# ==========================================

class ClusterAppUI:
    def __init__(self):
        self.dias_df = fetch_dias_clusters()
        raw_names = list(self.dias_df['Name'].values) if self.dias_df is not None and 'Name' in self.dias_df.columns else []
        filtered_names = sorted([n for n in raw_names if "NGC 6124" not in n])
        self.all_cluster_options = ["NGC 6124 (example)"] + filtered_names

    def render_interface(self):
        left_half, right_half = st.columns(2, gap="large")

        with left_half:
            st.subheader("Select Parameters")

            col1, col2 = st.columns([1,2])
            
            with col1:
                raw_cluster_preset = st.selectbox(
                    "**Cluster** (type to search)", 
                    self.all_cluster_options, 
                    index=0,
                    key="cluster_preset_widget"
                )

            # Проверяем, изменилось ли скопление, и сбрасываем состояние при смене
            if "last_cluster" not in st.session_state:
                st.session_state["last_cluster"] = raw_cluster_preset
            elif st.session_state["last_cluster"] != raw_cluster_preset:
                st.session_state["last_cluster"] = raw_cluster_preset
                st.session_state["calculated"] = False
                st.session_state.pop("results", None)
                st.session_state.pop("calc_params", None)
                st.session_state.pop("fig_r", None)
                st.session_state.pop("raw_gaia_df", None)
                st.session_state.pop("last_queried_params", None)

            cluster_preset = st.session_state["last_cluster"]

            # Вычисляем дефолтные параметры в зависимости от выбранного скопления
            def_l, def_b = 0.0, 0.0
            def_rad, def_mag = 60.0, 18.0
            def_pmra_min, def_pmra_max = 0.0, 0.0
            def_pmdec_min, def_pmdec_max = 0.0, 0.0 
            def_plx_min, def_plx_max = 1.0, 1.0

            coord_display_html = ""

            if "NGC 6124 (example)" in cluster_preset:
                def_l, def_b = 340.73, +5.98
                def_rad, def_mag = 116.0, 18.0
                def_pmra_min, def_pmra_max = -1.3, 0.9
                def_pmdec_min, def_pmdec_max = -3.2, -1.0 
                def_plx_min, def_plx_max = 1.05, 2.15
                def_dist = 617

                coord_display_html = f"""
                    <div class="coord-info" style="color: #0054A3;">
                    <b>Galactic coordinates:</b>&nbsp; l = {def_l:.2f}&deg, b = {def_b:.2f}&deg &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <b>Distance:</b>&nbsp;{def_dist:.0f}&nbsp;pc
                    </div>
                """
                    
            elif self.dias_df is not None and cluster_preset in self.dias_df['Name'].values:
                row = self.dias_df[self.dias_df['Name'] == cluster_preset].iloc[0]
                if 'RA_ICRS' in row and 'DE_ICRS' in row and not pd.isna(row['RA_ICRS']) and not pd.isna(row['DE_ICRS']):
                    coord = SkyCoord(ra=row['RA_ICRS'], dec=row['DE_ICRS'], unit=(u.deg, u.deg), frame='icrs')
                    def_l = coord.galactic.l.deg
                    def_b = coord.galactic.b.deg
                    
                def_rad = 60.0
                def_mag = 18.0
                def_pmra_min = float(row.get('pmRA', 0.0)) if 'pmRA' in row and not pd.isna(row.get('pmRA')) else 0.0
                def_pmra_max = def_pmra_min
                def_pmdec_min = float(row.get('pmDE', 0.0)) if 'pmDE' in row and not pd.isna(row.get('pmDE')) else 0.0
                def_pmdec_max = def_pmdec_min
                def_plx_min = float(row.get('Plx', 1.0)) if 'Plx' in row and not pd.isna(row.get('Plx')) else 1.0
                def_plx_max = def_plx_min
                def_dist = int(row.get('Dist', 0.0)) if 'Dist' in row and not pd.isna(row.get('Dist')) else 0.0

                coord_display_html = f"""
                    <div class="coord-info">
                        <b>Galactic coordinates:</b>&nbsp;l = {def_l:.2f}°, b = {def_b:.2f}° &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <b>Distance:</b>&nbsp;{def_dist:.0f}&nbsp;pc
                    </div>
                """

            with col2:
                st.markdown(coord_display_html, unsafe_allow_html=True)

            with st.container(border=True):
                st.markdown("##### Astrometric Parameters")
                col1_f, col2_f, col3_f = st.columns(3)
                with col1_f:
                    pmra_min = st.number_input(r"**min $\mu_{\alpha}$**", value=def_pmra_min, format="%.2f")
                    pmra_max = st.number_input(r"**max $\mu_{\alpha}$**", value=def_pmra_max, format="%.2f")
                with col2_f:
                    pmdec_min = st.number_input(r"**min $\mu_{\delta}$**", value=def_pmdec_min, format="%.2f")
                    pmdec_max = st.number_input(r"**max $\mu_{\delta}$**", value=def_pmdec_max, format="%.2f")
                with col3_f:
                    plx_min = st.number_input(r"**min $\varpi$**", value=def_plx_min, format="%.2f")
                    plx_max = st.number_input(r"**max $\varpi$**", value=def_plx_max, format="%.2f")

                col_r1, col_r2, col_r3 = st.columns(3)
                with col_r1:
                    radius_am = st.number_input("**Radius, arcmin**", value=def_rad)
                with col_r2:
                    maglim = st.number_input("**Magnitude Limit**", value=def_mag)
                with col_r3:
                    max_rows = st.selectbox("**Max Number of Sources**", options=[25000, 50000, 100000, 500000, "Unlimited (it will take loooong...)"])

                gaia_release = st.selectbox("**Gaia Release**", ["Gaia DR3 (Gaia Collaboration, 2022), Ep=2016.0",
                                                                 "Gaia EDR3 (Gaia Collaboration, 2020), Ep=2016.0", 
                                                                 "Gaia DR2 (Gaia Collaboration, 2018), Ep=2015.5"
                                                                 ])
                selected_catalog_table = get_tap_table_name(gaia_release)

                btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                calc_clicked = st.button("**Calculate**", type="primary", use_container_width=True, key="calc_btn")
            with btn_col2:
                reset_clicked = st.button("**Reset**", type="secondary", use_container_width=True, key="reset_btn")

            if reset_clicked:
                st.cache_data.clear()
                st.session_state.clear()
                st.session_state["reset_performed"] = True
                st.rerun()

            if calc_clicked:
                st.session_state["calculated"] = True
                p = {
                    "def_l": def_l,
                    "def_b": def_b,
                    "pmra_min": pmra_min,
                    "pmra_max": pmra_max,
                    "pmdec_min": pmdec_min,
                    "pmdec_max": pmdec_max,
                    "plx_min": plx_min,
                    "plx_max": plx_max,
                    "radius_am": radius_am,
                    "maglim": maglim,
                    "max_rows": max_rows,
                    "selected_catalog_table": selected_catalog_table,
                    "cluster_preset": cluster_preset
                }
                st.session_state["calc_params"] = p

                last_q_p = st.session_state.get("last_queried_params", None)
                need_query = True

                if last_q_p is not None:
                    expanded = (
                        p["pmra_min"] < last_q_p["pmra_min"] or p["pmra_max"] > last_q_p["pmra_max"] or
                        p["pmdec_min"] < last_q_p["pmdec_min"] or p["pmdec_max"] > last_q_p["pmdec_max"] or
                        p["plx_min"] < last_q_p["plx_min"] or p["plx_max"] > last_q_p["plx_max"] or
                        p["radius_am"] > last_q_p["radius_am"] or
                        p["maglim"] > last_q_p["maglim"] or
                        p["selected_catalog_table"] != last_q_p["selected_catalog_table"]
                    )
                    if not expanded:
                        need_query = False

                df = None
                if need_query:
                    with st.status("Executing TAP query...", expanded=True) as status:
                        st.write("Connecting to TAP server and running query... It may take a couple of minutes...")
                        
                        df = fetch_gaia_data_adql(
                            table_name=p["selected_catalog_table"],
                            l_center=p["def_l"],
                            b_center=p["def_b"],
                            pmra_min=p["pmra_min"],
                            pmra_max=p["pmra_max"],
                            pmdec_min=p["pmdec_min"],
                            pmdec_max=p["pmdec_max"],
                            plx_min=p["plx_min"],
                            plx_max=p["plx_max"],
                            radius_am=p["radius_am"],
                            mag_limit=p["maglim"],
                            max_rows=p["max_rows"]
                        )
                        
                        if df is not None and not df.empty:
                            st.write("Data successfully retrieved from TAP server.")
                            status.update(label="Data loaded from TAP successfully", state="complete", expanded=False)
                        else:
                            status.update(label="Failed to retrieve data from TAP", state="error", expanded=False)

                    if df is not None and not df.empty:
                        st.session_state["raw_gaia_df"] = df
                        st.session_state["last_queried_params"] = p
                else:
                    df = st.session_state.get("raw_gaia_df", None)
                    if df is not None:
                        st.info("Using cached data from previous query (intervals are narrower or equal). No TAP request made.")
                    else:
                        df = fetch_gaia_data_adql(
                            table_name=p["selected_catalog_table"],
                            l_center=p["def_l"],
                            b_center=p["def_b"],
                            pmra_min=p["pmra_min"],
                            pmra_max=p["pmra_max"],
                            pmdec_min=p["pmdec_min"],
                            pmdec_max=p["pmdec_max"],
                            plx_min=p["plx_min"],
                            plx_max=p["plx_max"],
                            radius_am=p["radius_am"],
                            mag_limit=p["maglim"],
                            max_rows=p["max_rows"]
                        )
                        if df is not None and not df.empty:
                            st.session_state["raw_gaia_df"] = df
                            st.session_state["last_queried_params"] = p

                if df is not None and not df.empty:
                    mask = (
                        (df['pmra'] >= p["pmra_min"]) & (df['pmra'] <= p["pmra_max"]) &
                        (df['pmdec'] >= p["pmdec_min"]) & (df['pmdec'] <= p["pmdec_max"]) &
                        (df['parallax'] >= p["plx_min"]) & (df['parallax'] <= p["plx_max"])
                    )
                    df_sel = df[mask]

                    inarr_data = df_sel[['parallax', 'pmra', 'pmdec', 'phot_g_mean_mag']].to_numpy()
                    a_range = [p["pmra_min"], p["pmra_min"], p["pmra_max"], p["pmra_max"]]
                    d_range = [p["pmdec_min"], p["pmdec_min"], p["pmdec_max"], p["pmdec_max"]]
                    z_range = [p["plx_min"], p["plx_min"], p["plx_max"], p["plx_max"]]
                    
                    c_mua, c_mud, c_plx = findcentres(inarr_data, p["maglim"], delta=0.3, step=0.1, a=a_range, d=d_range, z=z_range)
                    
                    dist_mean = 1000.0 / c_plx if (c_plx is not None and not np.isnan(c_plx) and c_plx > 0) else 0
                    v_a = 4.74 * c_mua / c_plx if (c_mua is not None and c_plx is not None and not np.isnan(c_mua) and not np.isnan(c_plx) and c_plx > 0) else 0
                    v_d = 4.74 * c_mud / c_plx if (c_mud is not None and c_plx is not None and not np.isnan(c_mud) and not np.isnan(c_plx) and c_plx > 0) else 0

                    l_med, b_med = def_l, def_b 
                    dist_c = np.sqrt((df_sel['l'] - l_med)**2 + (df_sel['b'] - b_med)**2)
                    r_deg = p["radius_am"] / 60.0
                    n_circle = len(df_sel[dist_c <= r_deg])
                    n_ring = len(df_sel[(dist_c > r_deg) & (dist_c <= r_deg * np.sqrt(2))])
                    cluster_n = max(0, n_circle - n_ring)

                    fig1, fig2 = plot_cluster_diagrams(df_sel, df, p["radius_am"], l_med, b_med)

                    st.session_state["results"] = {
                        "df_sel": df_sel,
                        "c_mua": c_mua,
                        "c_mud": c_mud,
                        "c_plx": c_plx,
                        "dist_mean": dist_mean,
                        "v_a": v_a,
                        "v_d": v_d,
                        "cluster_n": cluster_n,
                        "fig1": fig1,
                        "fig2": fig2,
                        "n_circle": n_circle,
                        "n_ring": n_ring,
                        "cluster_n": cluster_n
                    }

                    # Добавление строки в накопительную историю для текущего скопления
                    if "cluster_history" not in st.session_state:
                        st.session_state["cluster_history"] = {}
                    if cluster_preset not in st.session_state["cluster_history"]:
                        st.session_state["cluster_history"][cluster_preset] = []
                    
                    interval_width = (p['pmra_max'] - p['pmra_min']) + (p['pmdec_max'] - p['pmdec_min']) + (p['plx_max'] - p['plx_min'])
                    step_index = len(st.session_state["cluster_history"][cluster_preset]) + 1
                    
                    st.session_state["cluster_history"][cluster_preset].append({
                        "Iteration": step_index,
                        "Width": interval_width,
                        "Number of stars": cluster_n,
                        "μα interval": f"[{p['pmra_min']:.2f}, {p['pmra_max']:.2f}]",
                        "μδ interval": f"[{p['pmdec_min']:.2f}, {p['pmdec_max']:.2f}]",
                        "ϖ interval": f"[{p['plx_min']:.2f}, {p['plx_max']:.2f}]",
                        "μα mode": f"{c_mua:.2f}" if not np.isnan(c_mua) else "N/A",
                        "μδ mode": f"{c_mud:.2f}" if not np.isnan(c_mud) else "N/A",
                        "ϖ mode": f"{c_plx:.2f}" if not np.isnan(c_plx) else "N/A"
                    })
                    
                    st.session_state.pop("fig_r", None)
                else:
                    st.session_state["results"] = None

            # Вывод результатов в контейнере слева
            if st.session_state.get("calculated", False) and st.session_state.get("results") is not None:
                res = st.session_state["results"]

                with st.container(border=True):
                    st.markdown("**Modes of Astrometric Parameters' Distributions**")
                    st1, st2, st3, st4 = st.columns(4)
                    st1.markdown(f"<div class='stat-card'><b> &mu;<sub>&alpha;</sub> = {res['c_mua']:.2f}<br>V<sub>&alpha;</sub> = {res['v_a']:.2f} km/s </b></div>", unsafe_allow_html=True)
                    st2.markdown(f"<div class='stat-card'><b> &mu;<sub>&delta;</sub> = {res['c_mud']:.2f}<br>V<sub>&delta;</sub> = {res['v_d']:.2f} km/s </b></div>", unsafe_allow_html=True)
                    st3.markdown(f"<div class='stat-card'><b> &varpi; = {res['c_plx']:.2f} mas </b></div>", unsafe_allow_html=True)
                    st4.markdown(f"<div class='stat-card'><b> dist = {res['dist_mean']:.0f} pc </b></div>", unsafe_allow_html=True)

                with st.container(border=True):
                    dbg_col1, dbg_col2, dbg_col3 = st.columns(3)
                    dbg_col1.markdown(f"""<div class="stat-card" style="min-height: 100px;">
                                         <div style="font-weight: normal; font-size: 14px; color: #000000; min-height: 50px; align-items: center;">
                                         Number of stars in the inner circle
                                         </div><div style="font-size: 28px; font-weight: normal; color: #000000;">
                                            {res['n_circle']:.0f}
                                         </div>
                                         </div>""", unsafe_allow_html=True)
                    dbg_col2.markdown(f"""<div class="stat-card" style="min-height: 100px;">
                                         <div style="font-weight: normal; font-size: 14px; color: #000000; min-height: 50px; align-items: center;">
                                         Number of stars in the ring
                                         </div><div style="font-size: 28px; font-weight: normal; color: #000000;">
                                            {res['n_ring']:.0f}
                                         </div>
                                         </div>""", unsafe_allow_html=True)
                    dbg_col3.markdown(f"""<div class="stat-card" style="min-height: 100px;">
                                         <div style="font-weight: normal; font-size: 14px; color: #000000; min-height: 50px; align-items: center;">
                                         Nubmer of stars in the cluster, <br>background-adjusted
                                         </div><div style="font-size: 28px; font-weight: normal; color: #000000;">
                                            {res['cluster_n']:.0f}
                                         </div>
                                         </div>""", unsafe_allow_html=True)
                        
                with st.container(border=True):
                    st.pyplot(res['fig1'], use_container_width=True)
                    st.pyplot(res['fig2'], use_container_width=True)
                
            elif st.session_state.get("calculated", False) and st.session_state.get("results") is None:
                st.warning("No data retrieved via ADQL.")
            else:
                st.info("Set your parameters and click **Calculate**.")

        # ==========================================
        # RIGHT PANEL: SEARCH FOR PLATEAU & COMPLETENESS
        # ==========================================
        with right_half:
            st.subheader("Search for Plateau & Completeness")
            
            if "cluster_history" not in st.session_state:
                st.session_state["cluster_history"] = {}

            ngc_key = "NGC 6124 (example)"
            if ngc_key not in st.session_state["cluster_history"] and not st.session_state.get("reset_performed", False):
                raw_table_data = [
                    (1, -1.90, 1.50, -3.80, -0.40, 0.60, 2.60, 291),
                    (2, -1.78, 1.38, -3.68, -0.52, 0.69, 2.51, 944),
                    (3, -1.66, 1.26, -3.56, -0.64, 0.78, 2.42, 1194),
                    (4, -1.54, 1.14, -3.44, -0.76, 0.87, 2.33, 1366),
                    (5, -1.42, 1.02, -3.32, -0.88, 0.96, 2.24, 1385),
                    (6, -1.30, 0.90, -3.20, -1.00, 1.05, 2.15, 1369),
                    (7, -1.18, 0.78, -3.08, -1.12, 1.14, 2.06, 1354),
                    (8, -1.06, 0.66, -2.96, -1.24, 1.23, 1.97, 1338),
                    (9, -0.94, 0.54, -2.84, -1.36, 1.32, 1.88, 1286),
                    (10, -0.82, 0.42, -2.72, -1.48, 1.41, 1.79, 1133),
                    (11, -0.70, 0.30, -2.60, -1.60, 1.50, 1.70, 877),
                    (12, -0.58, 0.18, -2.48, -1.72, 1.55, 1.65, 519)
                ]
                st.session_state["cluster_history"][ngc_key] = [
                    {
                    "Iteration": row[0],
                    "Width": (row[2] - row[1]) + (row[4] - row[3]) + (row[6] - row[5]),
                    "Number of stars": row[7],
                    "μα interval": f"[{row[1]:.2f}, {row[2]:.2f}]",
                    "μδ interval": f"[{row[3]:.2f}, {row[4]:.2f}]",
                    "ϖ interval": f"[{row[5]:.2f}, {row[6]:.2f}]"} 
                    for row in raw_table_data
                ]

            history_list = st.session_state["cluster_history"].get(cluster_preset, [])

            # CONTAINER 1: Table with Intervals & Statistics
            with st.container(border=True):
                st.markdown("**Intervals & Statistics per Iteration**")
                
                if len(history_list) == 0:
                    st.info(f"No iterations calculated yet for {cluster_preset}. Click **Calculate** on the left to add rows.")
                else:
                    df_iterations = pd.DataFrame(history_list)

                    # Кнопка сортировки по ширине интервалов (сначала широкие, потом узкие)
                    sort_btn_label = "Sort: wide ➔ narrow (intervals)" if st.session_state.get("sort_wide_to_narrow", False) else "Sort by Interval Width (wide ➔ narrow)"
                    if st.button(sort_btn_label, key="sort_intervals_btn"):
                        st.session_state["sort_wide_to_narrow"] = not st.session_state.get("sort_wide_to_narrow", False)
                        st.rerun()

                    if st.session_state.get("sort_wide_to_narrow", False):
                        df_iterations = df_iterations.sort_values(by="Width", ascending=False).reset_index(drop=True)
                        df_iterations["Iteration"] = range(1, len(df_iterations) + 1)
                    else:
                        df_iterations["Iteration"] = range(1, len(df_iterations) + 1)

                    display_df = df_iterations.drop(columns=["Width"], errors="ignore")
                    st.dataframe(display_df, use_container_width=True, hide_index=True)

                    col_dl, col_cl = st.columns(2)
                    with col_dl:
                        csv_data = display_df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="Save table to CSV",
                            data=csv_data,
                            file_name=f"{cluster_preset.split()[0]}_iterations_analysis.csv",
                            mime="text/csv",
                            key="save_csv_btn"
                        )
                    with col_cl:
                        if st.button("Clear History Table", key="clear_history_btn"):
                            st.session_state["cluster_history"][cluster_preset] = []
                            st.rerun()

            # CONTAINER 2: Graph (Stars vs. Iteration, points only)
            with st.container(border=True):
                st.markdown("**Cluster Star Count vs. Iteration**")
                
                if len(history_list) > 0:
                    df_plot = pd.DataFrame(history_list)
                    if st.session_state.get("sort_wide_to_narrow", False):
                        df_plot = df_plot.sort_values(by="Width", ascending=False).reset_index(drop=True)
                        df_plot["Iteration"] = range(1, len(df_plot) + 1)
                    else:
                        df_plot["Iteration"] = range(1, len(df_plot) + 1)

                    fig_r, ax_r = plt.subplots(figsize=(6, 4), facecolor='None', dpi=300, constrained_layout=True) #"#AEC0FC"
                    # График заполняется ТОЛЬКО точками без линий (используем ax_r.scatter)
                    ax_r.scatter(df_plot["Iteration"], df_plot["Number of stars"], color='black', s=50, zorder=3)
                    ax_r.set_xlabel("Iteration", fontsize=10)
                    ax_r.set_ylabel(r"Number of Cluster Stars", fontsize=10)
                    ax_r.grid(True, linestyle='--', alpha=0.6)
                    st.pyplot(fig_r, use_container_width=True)
                else:
                    st.info("Graph will appear after the first calculation.")


# ==========================================
# APP EXECUTION
# ==========================================
app = ClusterAppUI()
app.render_interface()
