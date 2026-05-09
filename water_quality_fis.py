"""
Hierarchical Mamdani FIS with 3 intermediate models + 1 final model.
9 input parameters → 3 sub-scores → Final Water Quality (0–100%)

Usage:
    python water_quality_fis.py                  
    python water_quality_fis.py --interactive    # prompts for custom input values
"""

import argparse
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import warnings
warnings.filterwarnings("ignore")


# ──────────────────────────────────────────────────────────────────────────────
# 1. UNIVERSE RANGES  
# ──────────────────────────────────────────────────────────────────────────────

RANGES = {
    "pH":        (0,    14),
    "alkalinity":(0,   800),
    "hardness":  (0,  1200),
    "Ca":        (0,   300),
    "Mg":        (0,   120),
    "Fe":        (0,   1.2),
    "fluoride":  (0,     6),
    "nitrate":   (0,   180),
    "sulphate":  (0,   800),
    # intermediate outputs and final output all on 0–100
    "WQ1":       (0,   100),
    "WQ2":       (0,   100),
    "WQ3":       (0,   100),
    "WQf":       (0,   100),
}

ROME_DEFAULTS = {
    "pH":        7.4,
    "alkalinity":435,
    "hardness":  329,
    "Ca":        100.6,
    "Mg":        19.0,
    "Fe":        0.0118,
    "fluoride":  0.14,
    "nitrate":   3.5,
    "sulphate":  13.7,
}

DESIRABLE = {
    "pH":        (6.5, 8.5),
    "alkalinity": 200,
    "hardness":   300,
    "Ca":          75,
    "Mg":          30,
    "Fe":         0.3,
    "fluoride":   1.5,
    "nitrate":     45,
    "sulphate":   200,
}

# ──────────────────────────────────────────────────────────────────────────────
# 2. HELPER: build triangular MFs
# ──────────────────────────────────────────────────────────────────────────────

def trimf_safe(universe, abc):
    """Triangular MF; clips abc values to universe bounds."""
    a, b, c = abc
    return fuzz.trimf(universe, [a, b, c])


def build_input_var(name, lo, hi, low_abc, med_abc, high_abc):
    """Return an Antecedent with Low/Medium/High triangular MFs."""
    res = 500
    universe = np.linspace(lo, hi, res)
    var = ctrl.Antecedent(universe, name)
    var["Low"]    = trimf_safe(universe, low_abc)
    var["Medium"] = trimf_safe(universe, med_abc)
    var["High"]   = trimf_safe(universe, high_abc)
    return var


def build_output_sub(name):
    """Intermediate output (0–100), 7 classes."""
    universe = np.linspace(0, 100, 500)
    var = ctrl.Consequent(universe, name, defuzzify_method="centroid")
    _add_seven_classes(var, universe)
    return var


def build_output_antecedent(name):
    """Intermediate output used *as* antecedent in final model."""
    universe = np.linspace(0, 100, 500)
    var = ctrl.Antecedent(universe, name)
    _add_seven_classes(var, universe)
    return var


def build_final_output():
    universe = np.linspace(0, 100, 500)
    var = ctrl.Consequent(universe, "FinalWQ", defuzzify_method="centroid")
    _add_seven_classes(var, universe)
    return var


def _add_seven_classes(var, universe):
    """VVL, VL, L, M, H, VH, VVH – triangular, evenly spaced."""
    pts = [0, 16.67, 33.3, 50, 66.67, 83.3, 100]
    labels = ["VVL", "VL", "L", "M", "H", "VH", "VVH"]
    for i, label in enumerate(labels):
        a = pts[max(i-1, 0)]
        b = pts[i]
        c = pts[min(i+1, 6)]
        var[label] = trimf_safe(universe, [a, b, c])


# ──────────────────────────────────────────────────────────────────────────────
# 3. INPUT VARIABLE DEFINITIONS  (from Table 1)
# ──────────────────────────────────────────────────────────────────────────────

def make_inputs():
    """
    Returns dict of Antecedent objects with Low/Medium/High MFs.

    For parameters where Low = Good, MF peak is at 0 (lowest),
    so increasing concentration → worse quality.
    For pH the mapping is special (Medium = Good).
    """

    # pH: Low=Poor(0-7), Medium=Good(5.5-9.5), High=Moderate(7-14)
    pH = build_input_var("pH", 0, 14,
                         low_abc   =[0,    0,    7],
                         med_abc   =[5.5,  7.5,  9.5],
                         high_abc  =[7,   14,   14])

    # Alkalinity: Low=Good(0-400), Medium=Moderate(100-700), High=Poor(400-800)
    alkalinity = build_input_var("alkalinity", 0, 800,
                                 low_abc  =[0,   0,  400],
                                 med_abc  =[100, 400, 700],
                                 high_abc =[400, 800, 800])

    # Hardness: Low=Good(0-500), Medium=Moderate(100-900), High=Poor(500-1200)
    hardness = build_input_var("hardness", 0, 1200,
                               low_abc  =[0,   0,   500],
                               med_abc  =[100, 500, 900],
                               high_abc =[500, 1200, 1200])

    # Ca: Low=Good(0-150), Medium=Moderate(50-250), High=Poor(150-300)
    Ca = build_input_var("Ca", 0, 300,
                         low_abc  =[0,   0,  150],
                         med_abc  =[50,  150, 250],
                         high_abc =[150, 300, 300])

    # Mg: Low=Good(0-60), Medium=Moderate(20-100), High=Poor(60-120)
    Mg = build_input_var("Mg", 0, 120,
                         low_abc  =[0,  0,   60],
                         med_abc  =[20, 60,  100],
                         high_abc =[60, 120, 120])

    # Fe: Low=Good(0-0.6), Medium=Moderate(0.2-1), High=Poor(0.6-1.2)
    Fe = build_input_var("Fe", 0, 1.2,
                         low_abc  =[0,   0,   0.6],
                         med_abc  =[0.2, 0.6, 1.0],
                         high_abc =[0.6, 1.2, 1.2])

    # Fluoride: Low=Good(0-3), Medium=Moderate(1-5), High=Poor(3-6)
    fluoride = build_input_var("fluoride", 0, 6,
                               low_abc  =[0, 0, 3],
                               med_abc  =[1, 3, 5],
                               high_abc =[3, 6, 6])

    # Nitrate: Low=Good(0-80), Medium=Moderate(20-140), High=Poor(80-180)
    nitrate = build_input_var("nitrate", 0, 180,
                              low_abc  =[0,  0,   80],
                              med_abc  =[20, 80,  140],
                              high_abc =[80, 180, 180])

    # Sulphate: Low=Good(0-400), Medium=Moderate(150-650), High=Poor(400-800)
    sulphate = build_input_var("sulphate", 0, 800,
                               low_abc  =[0,   0,   400],
                               med_abc  =[150, 400, 650],
                               high_abc =[400, 800, 800])

    return {
        "pH": pH, "alkalinity": alkalinity, "hardness": hardness,
        "Ca": Ca, "Mg": Mg, "Fe": Fe,
        "fluoride": fluoride, "nitrate": nitrate, "sulphate": sulphate,
    }


# ──────────────────────────────────────────────────────────────────────────────
# 4. RULE GENERATION  (27 rules per model, all combinations of Low/Med/High)
# ──────────────────────────────────────────────────────────────────────────────

# Mapping logic:
#   For alkalinity, hardness, Ca, Mg, Fe, fluoride, nitrate, sulphate:
#       Low input  → HIGH quality output (good)
#       High input → LOW quality output  (bad)
#   For pH:
#       Medium input → HIGH quality output (good)
#       Low or High  → LOW quality output  (bad)

# Quality level for each combination is scored 0(VVL)–6(VVH)
# based on the "goodness" of each input level.

QUALITY_LABELS = ["VVL", "VL", "L", "M", "H", "VH", "VVH"]

# Input goodness scores (0=bad, 1=medium, 2=good)
INPUT_SCORE = {
    # param_name: {level: score}
    "default": {"Low": 2, "Medium": 1, "High": 0},   # lower=better params
    "pH":       {"Low": 0, "Medium": 2, "High": 1},   # medium=best
}

def level_score(param_name, level):
    if param_name == "pH":
        return INPUT_SCORE["pH"][level]
    return INPUT_SCORE["default"][level]


def score_to_label(score):
    """Map average goodness score (0–2) to quality label."""
    mapping = {
        6: "VVH", 5: "VH", 4: "H", 3: "M", 2: "L", 1: "VL", 0: "VVL"
    }
    # Scale [0,2] → [0,6]
    idx = round(score * 3)
    idx = max(0, min(6, idx))
    return QUALITY_LABELS[idx]


def make_rules_3(v1, n1, v2, n2, v3, n3, output):
    """Generate all 3^3=27 if-then rules for 3 inputs → 1 output."""
    rules = []
    levels = ["Low", "Medium", "High"]
    for l1 in levels:
        for l2 in levels:
            for l3 in levels:
                s = (level_score(n1, l1) + level_score(n2, l2) + level_score(n3, l3))
                lbl = score_to_label(s / 3 * 2)  # normalise to [0,2]
                rule = ctrl.Rule(
                    v1[l1] & v2[l2] & v3[l3],
                    output[lbl]
                )
                rules.append(rule)
    return rules


# ──────────────────────────────────────────────────────────────────────────────
# 5. BUILD THE FOUR FIS SYSTEMS
# ──────────────────────────────────────────────────────────────────────────────

def make_rules_7(v1, v2, v3, output):
    """
    Final model rules: inputs are the 7-class sub-quality outputs.
    Higher sub-scores → higher final quality. We sample a subset of
    representative rules (27) covering low/mid/high regions of 7 classes.
    """
    levels_7 = ["VVL", "VL", "L", "M", "H", "VH", "VVH"]
    # Map label → numeric score 0–6
    score_map = {l: i for i, l in enumerate(levels_7)}

    # Sample 3 representative levels from 7 (low/mid/high region)
    sampled = ["VL", "M", "VH"]
    rules = []
    for l1 in sampled:
        for l2 in sampled:
            for l3 in sampled:
                avg_idx = (score_map[l1] + score_map[l2] + score_map[l3]) / 3.0
                out_idx = round(avg_idx)
                out_lbl = levels_7[out_idx]
                rules.append(ctrl.Rule(
                    v1[l1] & v2[l2] & v3[l3],
                    output[out_lbl]
                ))
    # Add extreme corner rules
    rules.append(ctrl.Rule(v1["VVL"] & v2["VVL"] & v3["VVL"], output["VVL"]))
    rules.append(ctrl.Rule(v1["VVH"] & v2["VVH"] & v3["VVH"], output["VVH"]))
    rules.append(ctrl.Rule(v1["VVH"] & v2["M"]   & v3["M"],   output["H"]))
    rules.append(ctrl.Rule(v1["M"]   & v2["VVH"] & v3["VVH"], output["VH"]))
    return rules


def build_systems():
    inputs = make_inputs()

    # Intermediate outputs (Consequent)
    wq1_out = build_output_sub("WQ1")
    wq2_out = build_output_sub("WQ2")
    wq3_out = build_output_sub("WQ3")
    wqf_out = build_final_output()

    # FWQ1: hardness, pH, alkalinity
    rules1 = make_rules_3(
        inputs["hardness"],   "hardness",
        inputs["pH"],         "pH",
        inputs["alkalinity"], "alkalinity",
        wq1_out
    )
    sys1 = ctrl.ControlSystem(rules1)
    sim1 = ctrl.ControlSystemSimulation(sys1)

    # FWQ2: Ca, Mg, Fe
    rules2 = make_rules_3(
        inputs["Ca"], "Ca",
        inputs["Mg"], "Mg",
        inputs["Fe"], "Fe",
        wq2_out
    )
    sys2 = ctrl.ControlSystem(rules2)
    sim2 = ctrl.ControlSystemSimulation(sys2)

    # FWQ3: sulphate, nitrate, fluoride
    rules3 = make_rules_3(
        inputs["sulphate"],  "sulphate",
        inputs["nitrate"],   "nitrate",
        inputs["fluoride"],  "fluoride",
        wq3_out
    )
    sys3 = ctrl.ControlSystem(rules3)
    sim3 = ctrl.ControlSystemSimulation(sys3)

    # Final model: WQ1, WQ2, WQ3 → FinalWQ
    wq1_ant = build_output_antecedent("WQ1_in")
    wq2_ant = build_output_antecedent("WQ2_in")
    wq3_ant = build_output_antecedent("WQ3_in")

    rules_f = make_rules_7(wq1_ant, wq2_ant, wq3_ant, wqf_out)
    sys_f = ctrl.ControlSystem(rules_f)
    sim_f = ctrl.ControlSystemSimulation(sys_f)

    return sim1, sim2, sim3, sim_f, inputs, wq1_out, wq2_out, wq3_out, wqf_out


# ──────────────────────────────────────────────────────────────────────────────
# 6. INFERENCE
# ──────────────────────────────────────────────────────────────────────────────

def compute_wq(vals, sim1, sim2, sim3, sim_f):
    """
    vals: dict with keys matching ROME_DEFAULTS.
    Returns wq1, wq2, wq3, wq_final (all 0–100).
    """
    # FWQ1
    sim1.input["hardness"]   = np.clip(vals["hardness"],   0, 1200)
    sim1.input["pH"]         = np.clip(vals["pH"],         0,   14)
    sim1.input["alkalinity"] = np.clip(vals["alkalinity"], 0,  800)
    sim1.compute()
    wq1 = sim1.output["WQ1"]

    # FWQ2
    sim2.input["Ca"] = np.clip(vals["Ca"], 0, 300)
    sim2.input["Mg"] = np.clip(vals["Mg"], 0, 120)
    sim2.input["Fe"] = np.clip(vals["Fe"], 0, 1.2)
    sim2.compute()
    wq2 = sim2.output["WQ2"]

    # FWQ3
    sim3.input["sulphate"]  = np.clip(vals["sulphate"],  0, 800)
    sim3.input["nitrate"]   = np.clip(vals["nitrate"],   0, 180)
    sim3.input["fluoride"]  = np.clip(vals["fluoride"],  0,   6)
    sim3.compute()
    wq3 = sim3.output["WQ3"]

    # Final
    sim_f.input["WQ1_in"] = np.clip(wq1, 0, 100)
    sim_f.input["WQ2_in"] = np.clip(wq2, 0, 100)
    sim_f.input["WQ3_in"] = np.clip(wq3, 0, 100)
    sim_f.compute()
    wqf = sim_f.output["FinalWQ"]

    return wq1, wq2, wq3, wqf


def quality_label(score):
    if score >= 83.33: return "Very Very High ✅✅"
    if score >= 66.67: return "Very High ✅"
    if score >= 50:    return "High 🟡"
    if score >= 33.33: return "Medium 🟠"
    if score >= 16.67: return "Low 🔴"
    return "Very Low / Very Very Low ❌"


# ──────────────────────────────────────────────────────────────────────────────
# 7. VISUALISATION
# ──────────────────────────────────────────────────────────────────────────────

def plot_membership_functions(inputs, outpath="/mnt/user-data/outputs/wq_membership_functions.png"):
    params = ["pH", "alkalinity", "hardness", "Ca", "Mg", "Fe", "fluoride", "nitrate", "sulphate"]
    fig, axes = plt.subplots(3, 3, figsize=(15, 10))
    fig.suptitle("Membership Functions – All Input Parameters", fontsize=14, fontweight="bold")

    colors = {"Low": "#2ecc71", "Medium": "#f39c12", "High": "#e74c3c"}
    for ax, name in zip(axes.flatten(), params):
        v = inputs[name]
        for lbl, color in colors.items():
            ax.plot(v.universe, v[lbl].mf, label=lbl, color=color, linewidth=2)
        ax.set_title(name.capitalize(), fontsize=11)
        ax.set_xlabel("Concentration" if name != "pH" else "pH value")
        ax.set_ylabel("Membership")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.set_ylim(-0.05, 1.1)

    plt.tight_layout()
    plt.savefig(outpath, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {outpath}")


def plot_results(vals, wq1, wq2, wq3, wqf,
                 outpath="/mnt/user-data/outputs/wq_results_dashboard.png"):
    fig = plt.figure(figsize=(16, 10))
    fig.patch.set_facecolor("#f8f9fa")
    gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.45, wspace=0.35)

    # ── Gauge-style bar for each sub-model ──
    def gauge(ax, score, title, subtitle):
        colors_grad = ["#e74c3c", "#e67e22", "#f1c40f", "#2ecc71", "#27ae60"]
        thresholds  = [0, 20, 40, 60, 80, 100]
        for i in range(len(colors_grad)):
            ax.barh(0, thresholds[i+1]-thresholds[i],
                    left=thresholds[i], height=0.4,
                    color=colors_grad[i], alpha=0.35)
        ax.barh(0, score, height=0.25, color="#2c3e50", alpha=0.9, label=f"{score:.1f}%")
        ax.axvline(score, color="#2c3e50", linewidth=2.5)
        ax.set_xlim(0, 100)
        ax.set_ylim(-0.5, 0.8)
        ax.set_yticks([])
        ax.set_xlabel("Water Quality Score (%)")
        ax.set_title(f"{title}\n{subtitle}", fontsize=10, fontweight="bold")
        ax.text(score, 0.35, f"{score:.1f}%", ha="center", va="bottom",
                fontsize=12, fontweight="bold", color="#2c3e50")
        ax.grid(axis="x", alpha=0.3)

    gauge(fig.add_subplot(gs[0, 0]), wq1,
          "FWQ1", "Hardness | pH | Alkalinity")
    gauge(fig.add_subplot(gs[0, 1]), wq2,
          "FWQ2", "Ca | Mg | Fe")
    gauge(fig.add_subplot(gs[0, 2]), wq3,
          "FWQ3", "Sulphate | Nitrate | Fluoride")

    # ── Final score big gauge ──
    ax_main = fig.add_subplot(gs[1, :2])
    gauge(ax_main, wqf, "🏁 FINAL WATER QUALITY SCORE",
          quality_label(wqf))
    ax_main.set_xlabel("Final Water Quality (%)", fontsize=11)

    # ── Parameter table ──
    ax_tab = fig.add_subplot(gs[1, 2])
    ax_tab.axis("off")
    param_names = list(vals.keys())
    param_vals  = [f"{vals[k]:.4g}" for k in param_names]
    units = {
        "pH": "—", "alkalinity": "mg/L", "hardness": "mg/L",
        "Ca": "mg/L", "Mg": "mg/L", "Fe": "mg/L",
        "fluoride": "mg/L", "nitrate": "mg/L", "sulphate": "mg/L"
    }
    rows = [[p, param_vals[i], units[p]] for i, p in enumerate(param_names)]
    tbl = ax_tab.table(
        cellText=rows,
        colLabels=["Parameter", "Value", "Unit"],
        loc="center", cellLoc="center"
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(9)
    tbl.scale(1, 1.3)
    for (r, c), cell in tbl.get_celld().items():
        if r == 0:
            cell.set_facecolor("#2c3e50")
            cell.set_text_props(color="white", fontweight="bold")
        elif r % 2 == 0:
            cell.set_facecolor("#ecf0f1")
    ax_tab.set_title("Input Parameters", fontsize=10, fontweight="bold", pad=10)

    fig.suptitle("Drinking Water Quality Assessment – Fuzzy Inference System\n"
                 "(Mamdani FIS · Centroid Defuzzification · Barzegar et al., 2023)",
                 fontsize=12, fontweight="bold", y=1.01)

    plt.savefig(outpath, dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close()
    print(f"  Saved: {outpath}")


def plot_sensitivity(sim1, sim2, sim3, sim_f,
                     base_vals,
                     outpath="/mnt/user-data/outputs/wq_sensitivity.png"):
    """Show how each parameter affects the final WQ when varied ±50% of desirable."""
    params = list(ROME_DEFAULTS.keys())
    sensitivities = []

    _, _, _, base_final = compute_wq(base_vals, sim1, sim2, sim3, sim_f)

    for p in params:
        lo_vals = dict(base_vals)
        hi_vals = dict(base_vals)
        lo_vals[p] = max(0, base_vals[p] * 0.5)
        hi_vals[p] = base_vals[p] * 1.5
        _, _, _, wq_lo = compute_wq(lo_vals, sim1, sim2, sim3, sim_f)
        _, _, _, wq_hi = compute_wq(hi_vals, sim1, sim2, sim3, sim_f)
        sensitivities.append((p, wq_lo - base_final, wq_hi - base_final))

    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor("#f8f9fa")
    x = np.arange(len(params))
    w = 0.35
    lo_deltas = [s[1] for s in sensitivities]
    hi_deltas = [s[2] for s in sensitivities]
    ax.bar(x - w/2, lo_deltas, w, label="−50% value", color="#2ecc71", alpha=0.8)
    ax.bar(x + w/2, hi_deltas, w, label="+50% value", color="#e74c3c", alpha=0.8)
    ax.axhline(0, color="black", linewidth=0.8, linestyle="--")
    ax.set_xticks(x)
    ax.set_xticklabels(params, rotation=30, ha="right")
    ax.set_ylabel("ΔFinal WQ (%)")
    ax.set_title("Sensitivity Analysis – Effect of ±50% Change in Each Parameter\non Final Water Quality Score",
                 fontsize=11, fontweight="bold")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(outpath, dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close()
    print(f"  Saved: {outpath}")


# ──────────────────────────────────────────────────────────────────────────────
# 8. INTERACTIVE INPUT
# ──────────────────────────────────────────────────────────────────────────────

def prompt_inputs():
    print("\n" + "="*60)
    print("  Enter water quality parameter values")
    print("  (press Enter to use defaults)")
    print("="*60)
    vals = {}
    prompts = {
        "pH":        ("pH",             "",      ROME_DEFAULTS["pH"]),
        "alkalinity":("Alkalinity",     "mg/L",  ROME_DEFAULTS["alkalinity"]),
        "hardness":  ("Hardness",       "mg/L",  ROME_DEFAULTS["hardness"]),
        "Ca":        ("Calcium (Ca)",   "mg/L",  ROME_DEFAULTS["Ca"]),
        "Mg":        ("Magnesium (Mg)", "mg/L",  ROME_DEFAULTS["Mg"]),
        "Fe":        ("Iron (Fe)",      "mg/L",  ROME_DEFAULTS["Fe"]),
        "fluoride":  ("Fluoride",       "mg/L",  ROME_DEFAULTS["fluoride"]),
        "nitrate":   ("Nitrate",        "mg/L",  ROME_DEFAULTS["nitrate"]),
        "sulphate":  ("Sulphate",       "mg/L",  ROME_DEFAULTS["sulphate"]),
    }
    for key, (label, unit, default) in prompts.items():
        unit_str = f" {unit}" if unit else ""
        raw = input(f"  {label}{unit_str} [default={default}]: ").strip()
        vals[key] = float(raw) if raw else default
    return vals


# ──────────────────────────────────────────────────────────────────────────────
# 9. MAIN
# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Drinking Water Quality FIS")
    parser.add_argument("--interactive", action="store_true",
                        help="Prompt for custom input values")
    args = parser.parse_args()

    print("\n🔧 Building fuzzy inference systems …")
    sim1, sim2, sim3, sim_f, inputs, *_ = build_systems()
    print("   ✓ FWQ1 (Hardness, pH, Alkalinity)")
    print("   ✓ FWQ2 (Ca, Mg, Fe)")
    print("   ✓ FWQ3 (Sulphate, Nitrate, Fluoride)")
    print("   ✓ Final FWQ")

    if args.interactive:
        vals = prompt_inputs()
    else:
        vals = dict(ROME_DEFAULTS)
        print("\n📍 Using average values")

    print("\n⚙️  Running inference …")
    wq1, wq2, wq3, wqf = compute_wq(vals, sim1, sim2, sim3, sim_f)

    print("\n" + "="*60)
    print("  RESULTS")
    print("="*60)
    print(f"  FWQ1 (Hardness | pH | Alkalinity) : {wq1:.1f}%")
    print(f"  FWQ2 (Ca | Mg | Fe)               : {wq2:.1f}%")
    print(f"  FWQ3 (Sulphate | Nitrate | Fluoride): {wq3:.1f}%")
    print(f"  ──────────────────────────────────────")
    print(f"  Final Water Quality (FWQ)          : {wqf:.1f}%")
    print(f"  Classification                     : {quality_label(wqf)}")
    print("="*60)

    if not args.interactive:
        print(f"\n  📄 Paper reports: FWQ1≈69.7%, FWQ2≈84.5%, FWQ3≈94.5%, Final≈86.9%")
        print(f"     Our model    : FWQ1={wq1:.1f}%, FWQ2={wq2:.1f}%, FWQ3={wq3:.1f}%, Final={wqf:.1f}%")

    print("\n📊 Generating plots …")
    plot_membership_functions(inputs)
    plot_results(vals, wq1, wq2, wq3, wqf)
    plot_sensitivity(sim1, sim2, sim3, sim_f, vals)
    print("\n✅ Done.")


if __name__ == "__main__":
    main()
