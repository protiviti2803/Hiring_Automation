import math

BODY_CHARS_PER_LINE = 105
TITLE_CHARS_PER_LINE = 95
USABLE_HEIGHT_PT = 450.0

def _lines(text: str, cpl: int = BODY_CHARS_PER_LINE) -> int:
    text = text.strip()
    if not text:
        return 0
    return max(1, math.ceil(len(text) / cpl))

def build_std_title(org, theme, role):
    return f"{org} – {theme} – {role}"

def est_height(summary: str, projects: list, bpp_list: list, cfg: dict) -> float:
    total = 14.0  # Header
    sum_cpl = max(1, int(BODY_CHARS_PER_LINE * 9.0 / cfg.get("body_font_pt", 9.0)))
    sum_lines = _lines(summary, sum_cpl)
    total += sum_lines * cfg.get("summary_line_spacing", 12.0) + 3.0
    total += 14.0 + 12.0 + 4.0  # Major projects header

    t_font_pt = cfg.get("title_font_pt", 9.0)
    b_font_pt = cfg.get("body_font_pt", 9.0)
    t_cpl = max(1, int(TITLE_CHARS_PER_LINE * 9.0 / t_font_pt))
    b_cpl = max(1, int(BODY_CHARS_PER_LINE * 9.0 / b_font_pt))

    for i, proj in enumerate(projects):
        title = proj.get("title", "")
        t_lines = _lines(title, t_cpl)
        total += cfg.get("space_before_title", 4.0) + t_lines * cfg.get("title_spacing_pt", 12.0) + cfg.get("space_after_title", 1.0)

        bpp = bpp_list[i] if i < len(bpp_list) else 2
        bullets = proj.get("bullets", [])
        for b in bullets[:bpp]:
            b_lines = _lines(b, b_cpl)
            total += 1.0 + b_lines * cfg.get("body_spacing_pt", 11.5) + cfg.get("space_after_bullet", 1.5)

    return total

def compute_layout(summary: str, projects: list) -> dict:
    H = USABLE_HEIGHT_PT
    n = len(projects)

    if n <= 1:
        ideal_bpp = 6
        cfg = dict(
            title_font_pt        = 9.0,
            body_font_pt         = 9.0,
            title_spacing_pt     = 13.0,
            body_spacing_pt      = 13.0,
            space_before_title   = 10.0,
            space_after_title    = 3.0,
            space_after_bullet   = 3.5,
            summary_line_spacing = 13.0,
        )
    elif n == 2:
        ideal_bpp = 5
        cfg = dict(
            title_font_pt        = 9.0,
            body_font_pt         = 9.0,
            title_spacing_pt     = 12.5,
            body_spacing_pt      = 12.5,
            space_before_title   = 8.0,
            space_after_title    = 2.0,
            space_after_bullet   = 2.5,
            summary_line_spacing = 12.5,
        )
    elif n == 3:
        ideal_bpp = 4
        cfg = dict(
            title_font_pt        = 9.0,
            body_font_pt         = 9.0,
            title_spacing_pt     = 12.0,
            body_spacing_pt      = 12.0,
            space_before_title   = 6.0,
            space_after_title    = 1.5,
            space_after_bullet   = 2.0,
            summary_line_spacing = 12.0,
        )
    elif n == 4:
        ideal_bpp = 3
        cfg = dict(
            title_font_pt        = 9.0,
            body_font_pt         = 9.0,
            title_spacing_pt     = 12.0,
            body_spacing_pt      = 11.5,
            space_before_title   = 4.0,
            space_after_title    = 1.0,
            space_after_bullet   = 1.5,
            summary_line_spacing = 12.0,
        )
    else: # 5 or 6+
        ideal_bpp = 2
        cfg = dict(
            title_font_pt        = 9.0,
            body_font_pt         = 9.0,
            title_spacing_pt     = 11.5,
            body_spacing_pt      = 11.0,
            space_before_title   = 3.0,
            space_after_title    = 0.5,
            space_after_bullet   = 1.0,
            summary_line_spacing = 11.5,
        )

    current_bpp = [
        min(ideal_bpp, max(1, len(p.get("bullets", []))))
        for p in projects
    ]

    # If few projects, try greedily adding extra bullets if available & fits
    if n <= 4:
        for i in range(len(current_bpp)):
            avail = len(projects[i].get("bullets", []))
            if avail > current_bpp[i]:
                test_bpp = list(current_bpp)
                test_bpp[i] += 1
                if est_height(summary, projects, test_bpp, cfg) <= H * 0.98:
                    current_bpp[i] += 1

    h = est_height(summary, projects, current_bpp, cfg)

    # Phase 1: Adjust typography if slight overflow
    if h > H:
        cfg.update(dict(
            title_font_pt        = 8.5,
            body_font_pt         = 8.5,
            title_spacing_pt     = 11.0,
            body_spacing_pt      = 10.5,
            space_before_title   = 2.5,
            space_after_title    = 0.5,
            space_after_bullet   = 1.0,
            summary_line_spacing = 11.0,
        ))
        h = est_height(summary, projects, current_bpp, cfg)

    # Phase 2: If still overflowing, scale font to 8.0pt
    if h > H:
        cfg.update(dict(
            title_font_pt        = 8.0,
            body_font_pt         = 8.0,
            title_spacing_pt     = 10.5,
            body_spacing_pt      = 10.0,
            space_before_title   = 2.0,
            space_after_bullet   = 0.8,
            summary_line_spacing = 10.5,
        ))
        h = est_height(summary, projects, current_bpp, cfg)

    # Phase 3: Prune bullets if still overflowing
    if h > H:
        for _ in range(60):
            if est_height(summary, projects, current_bpp, cfg) <= H * 0.99:
                break
            reducible = [(i, b) for i, b in enumerate(current_bpp) if b > 1]
            if not reducible:
                break
            idx_reduce = max(reducible, key=lambda x: x[1])[0]
            current_bpp[idx_reduce] -= 1

    cfg["bullets_per_project_list"] = current_bpp
    final_h = est_height(summary, projects, current_bpp, cfg)
    print(f"Projects: {n} -> bpp: {current_bpp} (Total {sum(current_bpp)}), est_h: {final_h:.1f}/{H}pt ({final_h/H*100:.1f}%), fonts: {cfg['title_font_pt']}/{cfg['body_font_pt']}pt")
    return cfg

# Test various scenarios:
dummy_summary = "Gaurav Tripathi has 9 years of experience as a Senior Business Analyst specializing in Credit Risk and Regulatory Capital within the Banking and Financial Services industry. He leverages advanced analytical tools such as Python, SQL, Excel, Tableau, and R to build and validate risk models, including CECL, IFRS-9, and Basel-IV frameworks. His expertise spans stress testing (CCAR, ICAAP), IRB-to-IFRS-9 model linkages, and climate risk modelling, ensuring robust regulatory compliance across multiple jurisdictions. Gaurav has led collaborations with regulators (PRA, ECB, Fed/OCC, OSFI), business stakeholders, and technology teams."

sample_bullet = "Developed and validated Linear Regression models aligned with CECL guidelines, performing extensive backtesting, sensitivity analysis, and stress scenario forecasting to ensure model robustness."

for count in [1, 2, 3, 4, 6]:
    projs = []
    for i in range(count):
        # 6 bullets available per project
        projs.append({
            "title": f"Banking – Project Number {i+1} Transformation – Lead Analyst",
            "bullets": [sample_bullet] * 6
        })
    compute_layout(dummy_summary, projs)
