"""
İçme Suyu Kalitesi Değerlendirme – Bulanık Çıkarım Sistemi
Kaynak: Barzegar et al. (2023), IJERPH 20, 6522

Streamlit arayüzü – Dönem projesi gereksinimleri:
  ✓ Slider ile giriş değerleri
  ✓ Üyelik fonksiyonları grafiksel gösterim
  ✓ Aktif kural listesi
  ✓ Durulaştırma (centroid) grafiği + sayısal sonuç
  ✓ Anlık hesaplama
  ✓ En az 3 giriş, en az 3 dilsel tanımlama

Çalıştırma: streamlit run app.py
"""

import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import streamlit as st
import warnings
warnings.filterwarnings("ignore")

# ─── Sayfa ayarları ───────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Su Kalitesi – Bulanık Mantık",
    page_icon="💧",
    layout="wide",
)

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.main { background-color: #f0f6fb; }
.metric-box {
    background: white; border-radius: 12px;
    padding: 18px; text-align: center;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}
.metric-title { font-size: 13px; color: #666; margin-bottom: 4px; }
.metric-value { font-size: 28px; font-weight: bold; color: #1a73e8; }
.quality-badge {
    font-size: 16px; font-weight: bold; padding: 8px 16px;
    border-radius: 8px; display: inline-block; margin-top: 8px;
}
</style>
""", unsafe_allow_html=True)

# ─── Üyelik fonksiyonu yardımcıları ──────────────────────────────────────────

def trimf_s(u, abc):
    return fuzz.trimf(u, abc)

def make_in(name, lo, hi, low_abc, med_abc, high_abc, n=500):
    u = np.linspace(lo, hi, n)
    v = ctrl.Antecedent(u, name)
    v["Düşük"]  = trimf_s(u, low_abc)
    v["Orta"]   = trimf_s(u, med_abc)
    v["Yüksek"] = trimf_s(u, high_abc)
    return v

def add_seven(var, u):
    pts = [0, 16.67, 33.3, 50, 66.67, 83.3, 100]
    lbs = ["ÇÇD", "ÇD", "D", "O", "Y", "ÇY", "ÇÇY"]
    for i, lb in enumerate(lbs):
        a = pts[max(i-1,0)]; b = pts[i]; c = pts[min(i+1,6)]
        var[lb] = trimf_s(u, [a, b, c])

def make_out_con(name):
    u = np.linspace(0, 100, 500)
    v = ctrl.Consequent(u, name, defuzzify_method="centroid")
    add_seven(v, u)
    return v

def make_out_ant(name):
    u = np.linspace(0, 100, 500)
    v = ctrl.Antecedent(u, name)
    add_seven(v, u)
    return v

# ─── Giriş değişkenleri ───────────────────────────────────────────────────────

@st.cache_resource
def build_all():
    pH        = make_in("pH",        0,  14,  [0,0,7],      [5.5,7.5,9.5], [7,14,14])
    alkalinite= make_in("alkalinite",0, 800,  [0,0,400],    [100,400,700], [400,800,800])
    sertlik   = make_in("sertlik",   0,1200,  [0,0,500],    [100,500,900], [500,1200,1200])
    Ca        = make_in("Ca",        0, 300,  [0,0,150],    [50,150,250],  [150,300,300])
    Mg        = make_in("Mg",        0, 120,  [0,0,60],     [20,60,100],   [60,120,120])
    Fe        = make_in("Fe",        0, 1.2,  [0,0,0.6],    [0.2,0.6,1.0], [0.6,1.2,1.2])
    florür    = make_in("florür",    0,   6,  [0,0,3],      [1,3,5],       [3,6,6])
    nitrat    = make_in("nitrat",    0, 180,  [0,0,80],     [20,80,140],   [80,180,180])
    sülfat    = make_in("sülfat",    0, 800,  [0,0,400],    [150,400,650], [400,800,800])

    wq1_out = make_out_con("SK1")
    wq2_out = make_out_con("SK2")
    wq3_out = make_out_con("SK3")
    wqf_out = make_out_con("SonSK")

    # ── Puanlama ──────────────────────────────────────────────────────────────
    def sc(param, lv):
        special = {"pH": {"Düşük":0,"Orta":2,"Yüksek":1}}
        default = {"Düşük":2,"Orta":1,"Yüksek":0}
        return special.get(param, default)[lv]

    lbs7 = ["ÇÇD","ÇD","D","O","Y","ÇY","ÇÇY"]
    def s2l(s):          # 0‒2 → 0‒6
        idx = round(s * 3); return lbs7[max(0,min(6,idx))]

    def rules3(v1,n1,v2,n2,v3,n3,out):
        rules = []
        for l1 in ["Düşük","Orta","Yüksek"]:
            for l2 in ["Düşük","Orta","Yüksek"]:
                for l3 in ["Düşük","Orta","Yüksek"]:
                    avg = (sc(n1,l1)+sc(n2,l2)+sc(n3,l3))/3*2
                    rules.append(ctrl.Rule(v1[l1]&v2[l2]&v3[l3], out[s2l(avg)]))
        return rules

    r1 = rules3(sertlik,"sertlik",pH,"pH",alkalinite,"alkalinite",wq1_out)
    r2 = rules3(Ca,"Ca",Mg,"Mg",Fe,"Fe",wq2_out)
    r3 = rules3(sülfat,"sülfat",nitrat,"nitrat",florür,"florür",wq3_out)

    # Final kurallar (7 sınıf antecedent)
    wq1a = make_out_ant("SK1_g"); wq2a = make_out_ant("SK2_g"); wq3a = make_out_ant("SK3_g")
    smpl = ["ÇD","O","ÇY"]
    sm   = {"ÇÇD":0,"ÇD":1,"D":2,"O":3,"Y":4,"ÇY":5,"ÇÇY":6}
    rf = []
    for l1 in smpl:
        for l2 in smpl:
            for l3 in smpl:
                oi = round((sm[l1]+sm[l2]+sm[l3])/3)
                rf.append(ctrl.Rule(wq1a[l1]&wq2a[l2]&wq3a[l3], wqf_out[lbs7[oi]]))
    rf += [ctrl.Rule(wq1a["ÇÇD"]&wq2a["ÇÇD"]&wq3a["ÇÇD"],wqf_out["ÇÇD"]),
           ctrl.Rule(wq1a["ÇÇY"]&wq2a["ÇÇY"]&wq3a["ÇÇY"],wqf_out["ÇÇY"]),
           ctrl.Rule(wq1a["ÇÇY"]&wq2a["O"]  &wq3a["O"],  wqf_out["Y"]),
           ctrl.Rule(wq1a["O"]  &wq2a["ÇÇY"]&wq3a["ÇÇY"],wqf_out["ÇY"])]

    s1 = ctrl.ControlSystemSimulation(ctrl.ControlSystem(r1))
    s2 = ctrl.ControlSystemSimulation(ctrl.ControlSystem(r2))
    s3 = ctrl.ControlSystemSimulation(ctrl.ControlSystem(r3))
    sf = ctrl.ControlSystemSimulation(ctrl.ControlSystem(rf))

    inps = {"pH":pH,"alkalinite":alkalinite,"sertlik":sertlik,
            "Ca":Ca,"Mg":Mg,"Fe":Fe,"florür":florür,"nitrat":nitrat,"sülfat":sülfat}
    return s1,s2,s3,sf,inps,wq1_out,wq2_out,wq3_out,wqf_out,wq1a,wq2a,wq3a

# ─── Çıkarım ──────────────────────────────────────────────────────────────────

def infer(vals, s1,s2,s3,sf):
    def cl(k,lo,hi): return float(np.clip(vals[k],lo,hi))
    s1.input["sertlik"]   = cl("sertlik",0,1200)
    s1.input["pH"]        = cl("pH",0,14)
    s1.input["alkalinite"]= cl("alkalinite",0,800)
    s1.compute(); wq1 = s1.output["SK1"]

    s2.input["Ca"] = cl("Ca",0,300)
    s2.input["Mg"] = cl("Mg",0,120)
    s2.input["Fe"] = cl("Fe",0,1.2)
    s2.compute(); wq2 = s2.output["SK2"]

    s3.input["sülfat"]= cl("sülfat",0,800)
    s3.input["nitrat"]= cl("nitrat",0,180)
    s3.input["florür"]= cl("florür",0,6)
    s3.compute(); wq3 = s3.output["SK3"]

    sf.input["SK1_g"] = float(np.clip(wq1,0,100))
    sf.input["SK2_g"] = float(np.clip(wq2,0,100))
    sf.input["SK3_g"] = float(np.clip(wq3,0,100))
    sf.compute(); wqf = sf.output["SonSK"]
    return wq1,wq2,wq3,wqf

# ─── Grafikler ────────────────────────────────────────────────────────────────

COLORS = {"Düşük":"#2ecc71","Orta":"#f39c12","Yüksek":"#e74c3c"}
COLORS7 = {"ÇÇD":"#c0392b","ÇD":"#e74c3c","D":"#e67e22",
           "O":"#f1c40f","Y":"#27ae60","ÇY":"#2ecc71","ÇÇY":"#1abc9c"}

def plot_membership(var, current_val, title, xlabel):
    fig, ax = plt.subplots(figsize=(5,2.8))
    fig.patch.set_facecolor("#f8fbff")
    ax.set_facecolor("#f8fbff")
    for lbl, color in COLORS.items():
        if lbl in var.terms:
            ax.plot(var.universe, var[lbl].mf, color=color, lw=2, label=lbl)
            ax.fill_between(var.universe, var[lbl].mf, alpha=0.12, color=color)
    ax.axvline(current_val, color="#2c3e50", lw=2, ls="--", label=f"Değer={current_val:.3g}")
    ax.set_title(title, fontsize=10, fontweight="bold")
    ax.set_xlabel(xlabel, fontsize=8)
    ax.set_ylabel("Üyelik", fontsize=8)
    ax.legend(fontsize=7, loc="upper right")
    ax.set_ylim(-0.05,1.15); ax.grid(alpha=0.25)
    plt.tight_layout()
    return fig

def plot_output_mf(out_var, score, title):
    fig, ax = plt.subplots(figsize=(6,2.8))
    fig.patch.set_facecolor("#f8fbff"); ax.set_facecolor("#f8fbff")
    lbs7 = ["ÇÇD","ÇD","D","O","Y","ÇY","ÇÇY"]
    for lb in lbs7:
        c = COLORS7[lb]
        ax.plot(out_var.universe, out_var[lb].mf, color=c, lw=2, label=lb)
        ax.fill_between(out_var.universe, out_var[lb].mf, alpha=0.10, color=c)
    ax.axvline(score, color="#2c3e50", lw=2.5, ls="--", label=f"Sonuç={score:.1f}%")
    ax.set_title(title, fontsize=10, fontweight="bold")
    ax.set_xlabel("Su Kalitesi (%)", fontsize=8); ax.set_ylabel("Üyelik", fontsize=8)
    ax.legend(fontsize=6.5, ncol=2, loc="upper left")
    ax.set_ylim(-0.05,1.15); ax.grid(alpha=0.25)
    plt.tight_layout()
    return fig

def plot_gauge(wq1,wq2,wq3,wqf):
    fig, axes = plt.subplots(1,4,figsize=(14,2.2))
    fig.patch.set_facecolor("#f8fbff")
    pairs = [(wq1,"SK1\nSertlik|pH|Alk."),(wq2,"SK2\nCa|Mg|Fe"),
             (wq3,"SK3\nSülfat|Nitrat|Florür"),(wqf,"● FİNAL SK")]
    bands = [(0,20,"#e74c3c"),(20,40,"#e67e22"),(40,60,"#f1c40f"),
             (60,80,"#2ecc71"),(80,100,"#27ae60")]
    for ax,(score,lbl) in zip(axes,pairs):
        ax.set_facecolor("#f8fbff")
        for lo,hi,c in bands:
            ax.barh(0,hi-lo,left=lo,height=0.5,color=c,alpha=0.35)
        ax.barh(0,score,height=0.28,color="#2c3e50",alpha=0.9)
        ax.axvline(score,color="#2c3e50",lw=2)
        ax.text(score,0.32,f"{score:.1f}%",ha="center",va="bottom",
                fontsize=11,fontweight="bold",color="#2c3e50")
        ax.set_xlim(0,100); ax.set_ylim(-0.4,0.8)
        ax.set_yticks([]); ax.set_title(lbl,fontsize=9,fontweight="bold")
        ax.grid(axis="x",alpha=0.3)
    plt.tight_layout()
    return fig

def get_active_rules(vals, inps):
    """Hangi kuralların ateşlendiğini (aktivasyon > 0.01) listele."""
    lbs = ["Düşük","Orta","Yüksek"]
    active = []
    groups = [
        ("SK1", ["sertlik","pH","alkalinite"]),
        ("SK2", ["Ca","Mg","Fe"]),
        ("SK3", ["sülfat","nitrat","florür"]),
    ]
    sc_map = {"pH":{"Düşük":0,"Orta":2,"Yüksek":1}}
    def_sc = {"Düşük":2,"Orta":1,"Yüksek":0}
    lbs7 = ["ÇÇD","ÇD","D","O","Y","ÇY","ÇÇY"]
    def s2l(s): return lbs7[max(0,min(6,round(s*3)))]

    for grp_name, pnames in groups:
        for l1 in lbs:
            for l2 in lbs:
                for l3 in lbs:
                    acts = []
                    for pn,lv in zip(pnames,[l1,l2,l3]):
                        v = inps[pn]
                        val = float(np.clip(vals[pn], v.universe[0], v.universe[-1]))
                        acts.append(float(fuzz.interp_membership(v.universe, v[lv].mf, val)))
                    activation = min(acts)
                    if activation > 0.01:
                        sc = [(sc_map.get(pn,def_sc))[lv]
                              for pn,lv in zip(pnames,[l1,l2,l3])]
                        out_lbl = s2l(sum(sc)/len(sc)/2*2)
                        active.append({
                            "Model": grp_name,
                            "Kural": f"EĞER {pnames[0]}={l1} VE {pnames[1]}={l2} VE {pnames[2]}={l3}",
                            "Sonuç": f"O ZAMAN {grp_name}={out_lbl}",
                            "Aktivasyon": f"{activation:.3f}"
                        })
    active.sort(key=lambda x: float(x["Aktivasyon"]), reverse=True)
    return active[:20]

# ─── Kalite etiketi ───────────────────────────────────────────────────────────
def quality_label(s):
    if s>=83.33: return "ÇOK ÇOK YÜKSEK ✅✅", "#1abc9c"
    if s>=66.67: return "ÇOK YÜKSEK ✅",        "#2ecc71"
    if s>=50:    return "YÜKSEK 🟡",              "#f39c12"
    if s>=33.33: return "ORTA 🟠",               "#e67e22"
    if s>=16.67: return "DÜŞÜK 🔴",              "#e74c3c"
    return "ÇOK DÜŞÜK ❌", "#c0392b"

# ─── Arayüz ───────────────────────────────────────────────────────────────────

def main():
    st.title("💧 İçme Suyu Kalitesi – Bulanık Çıkarım Sistemi")
    st.caption("Mamdani FIS · Centroid Durulaştırma · Barzegar ve ark. (2023) · skfuzzy")

    s1,s2,s3,sf,inps,wq1_out,wq2_out,wq3_out,wqf_out,*_ = build_all()

    # ── Yan panel: giriş sliderları ──────────────────────────────────────────
    with st.sidebar:
        st.header("🎛️ Giriş Parametreleri")
        st.markdown("**FWQ1 – Fiziksel**")
        pH_v   = st.slider("pH",            0.0, 14.0,  7.4,  0.1)
        alk_v  = st.slider("Alkalinite (mg/L)", 0, 800,  435,  1)
        ser_v  = st.slider("Sertlik (mg/L)",    0,1200,  329,  1)
        st.markdown("**FWQ2 – Mineral**")
        ca_v   = st.slider("Kalsiyum Ca (mg/L)", 0, 300, 101,  1)
        mg_v   = st.slider("Magnezyum Mg (mg/L)",0, 120,  19,  1)
        fe_v   = st.slider("Demir Fe (mg/L)",  0.0,1.2, 0.012,0.001,format="%.3f")
        st.markdown("**FWQ3 – Kimyasal**")
        su_v   = st.slider("Sülfat (mg/L)",    0, 800,   14,  1)
        ni_v   = st.slider("Nitrat (mg/L)",    0, 180,    4,  1)
        fl_v   = st.slider("Florür (mg/L)",  0.0, 6.0, 0.14, 0.01)
        st.markdown("---")
        st.markdown("**📍 Varsayılan = Roma 2018 ort.**")
        if st.button("🔄 Sıfırla (Roma 2018)"):
            st.rerun()

    vals = {"pH":pH_v,"alkalinite":alk_v,"sertlik":ser_v,
            "Ca":ca_v,"Mg":mg_v,"Fe":fe_v,
            "sülfat":su_v,"nitrat":ni_v,"florür":fl_v}

    # ── Çıkarım ──────────────────────────────────────────────────────────────
    try:
        wq1,wq2,wq3,wqf = infer(vals, s1,s2,s3,sf)
    except Exception as e:
        st.error(f"Çıkarım hatası: {e}")
        return

    lbl, badge_color = quality_label(wqf)

    # ── Sonuç kartı ──────────────────────────────────────────────────────────
    st.markdown("### 📊 Sonuçlar")
    c1,c2,c3,c4 = st.columns(4)
    for col, score, title in zip(
        [c1,c2,c3,c4],
        [wq1,wq2,wq3,wqf],
        ["SK1 – Fiziksel","SK2 – Mineral","SK3 – Kimyasal","🏁 GENEL SK"]
    ):
        col.markdown(f"""
        <div class="metric-box">
          <div class="metric-title">{title}</div>
          <div class="metric-value">{score:.1f}%</div>
        </div>""", unsafe_allow_html=True)

    st.markdown(f"""
    <div style="text-align:center;margin:16px 0">
      <span class="quality-badge" style="background:{badge_color};color:white;font-size:20px">
        {lbl}
      </span>
    </div>""", unsafe_allow_html=True)

    # ── Gösterge grafiği ─────────────────────────────────────────────────────
    st.pyplot(plot_gauge(wq1,wq2,wq3,wqf))

    # ── Tab yapısı ───────────────────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs(
        ["📈 Üyelik Fonksiyonları", "📋 Aktif Kurallar", "🔬 Durulaştırma"])

    with tab1:
        st.markdown("#### Giriş Değişkeni Üyelik Fonksiyonları")
        meta = [
            ("pH","pH","pH değeri",""),
            ("alkalinite","alkalinite","Alkalinite","mg/L"),
            ("sertlik","sertlik","Sertlik","mg/L"),
            ("Ca","Ca","Kalsiyum (Ca)","mg/L"),
            ("Mg","Mg","Magnezyum (Mg)","mg/L"),
            ("Fe","Fe","Demir (Fe)","mg/L"),
            ("sülfat","sülfat","Sülfat","mg/L"),
            ("nitrat","nitrat","Nitrat","mg/L"),
            ("florür","florür","Florür","mg/L"),
        ]
        for row_start in range(0,9,3):
            cols = st.columns(3)
            for col, (key,vname,title,unit) in zip(cols, meta[row_start:row_start+3]):
                xlabel = f"{title} ({unit})" if unit else title
                col.pyplot(plot_membership(inps[key], vals[key], title, xlabel))

        st.markdown("#### Çıkış Değişkeni Üyelik Fonksiyonları")
        o1,o2,o3,o4 = st.columns(4)
        for col, out, score, title in zip(
            [o1,o2,o3,o4],
            [wq1_out,wq2_out,wq3_out,wqf_out],
            [wq1,wq2,wq3,wqf],
            ["SK1 – Fiziksel","SK2 – Mineral","SK3 – Kimyasal","Son Su Kalitesi"]
        ):
            col.pyplot(plot_output_mf(out, score, title))

    with tab2:
        st.markdown("#### Aktif Kural Listesi (aktivasyon > 0.01)")
        st.caption("Giriş değerlerine göre ateşlenen kurallar, aktivasyon değerine göre sıralı")
        active = get_active_rules(vals, inps)
        if active:
            import pandas as pd
            df = pd.DataFrame(active)
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.success(f"Toplam **{len(active)}** aktif kural bulundu.")
        else:
            st.info("Aktif kural bulunamadı.")

    with tab3:
        st.markdown("#### Durulaştırma Çıkışları (Centroid Metodu)")
        st.caption("Bulanık çıkış kümesi ve ağırlık merkezi (centroid) gösterimi")
        fc1,fc2 = st.columns(2)
        with fc1:
            st.pyplot(plot_output_mf(wq1_out, wq1, "SK1 – Fiziksel Durulaştırma"))
            st.pyplot(plot_output_mf(wq3_out, wq3, "SK3 – Kimyasal Durulaştırma"))
        with fc2:
            st.pyplot(plot_output_mf(wq2_out, wq2, "SK2 – Mineral Durulaştırma"))
            st.pyplot(plot_output_mf(wqf_out, wqf, "Son SK Durulaştırma"))

        st.markdown("---")
        st.markdown("##### Sayısal Sonuçlar")
        df_res = {
            "Model": ["SK1 (Fiziksel)","SK2 (Mineral)","SK3 (Kimyasal)","Son Su Kalitesi"],
            "Bulanık Çıkış (%)": [f"{wq1:.2f}",f"{wq2:.2f}",f"{wq3:.2f}",f"{wqf:.2f}"],
            "Sınıflandırma": [
                quality_label(wq1)[0], quality_label(wq2)[0],
                quality_label(wq3)[0], quality_label(wqf)[0]
            ]
        }
        import pandas as pd
        st.dataframe(pd.DataFrame(df_res), use_container_width=True, hide_index=True)

    # ── Referans bilgisi ─────────────────────────────────────────────────────
    with st.expander("ℹ️ Sistem Hakkında"):
        st.markdown("""
**Model:** Hiyerarşik Mamdani Bulanık Çıkarım Sistemi

**Girişler (9 parametre):**
- FWQ1: Sertlik, pH, Alkalinite
- FWQ2: Kalsiyum (Ca), Magnezyum (Mg), Demir (Fe)
- FWQ3: Sülfat, Nitrat, Florür

**Çıkış sınıfları (7 düzey):** ÇÇD → ÇÇY (0–100%)

**Üyelik fonksiyonları:** Üçgen (Triangular MF)

**Durulaştırma:** Centroid (Ağırlık Merkezi) metodu

**Kural sayısı:** 27 kural × 3 ara model + 31 son model kuralı = 112 kural

**Kaynak:** Barzegar et al. (2023), *Int. J. Environ. Res. Public Health*, 20, 6522.
        """)

if __name__ == "__main__":
    main()
