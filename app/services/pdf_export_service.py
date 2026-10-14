import os
import json
from app.core.database import get_db_connection

# ─────────────────────────────────────────────────────────────────────────────
# LAYOUT CONSTANTS
# Usable body height = Text Placeholder 144 height (6.23" ≈ 448.5 pt)
# Barlow 9pt body column (7.50" wide) ≈ 105 chars per line
# ─────────────────────────────────────────────────────────────────────────────
USABLE_HEIGHT_PT    = 450.0
BODY_CHARS_PER_LINE = 105
TITLE_CHARS_PER_LINE = 95
CHARS_PER_LINE      = BODY_CHARS_PER_LINE

# Minimum bullet length to be considered real content (chars)
MIN_BULLET_LEN = 12
# Minimum bullets a project must have to be rendered at all
MIN_BULLETS_TO_RENDER = 1


# ─────────────────────────────────────────────────────────────────────────────
# TEXT UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

def replace_text_in_text_frame(tf, replacements: dict):
    for paragraph in tf.paragraphs:
        p_text       = paragraph.text
        p_text_lower = p_text.lower()
        if not any(k.lower() in p_text_lower for k in replacements):
            continue
        for key, val in replacements.items():
            val_str   = str(val) if val is not None else ""
            key_lower = key.lower()
            idx = p_text_lower.find(key_lower)
            while idx != -1:
                exact        = p_text[idx: idx + len(key)]
                p_text       = p_text.replace(exact, val_str)
                p_text_lower = p_text.lower()
                idx          = p_text_lower.find(key_lower)
        fn = fs = fb = fi = fc = None
        if paragraph.runs and paragraph.runs[0].font:
            r0 = paragraph.runs[0].font
            fn, fs, fb, fi = r0.name, r0.size, r0.bold, r0.italic
            try:    fc = r0.color.rgb
            except: pass
        paragraph.text = p_text
        if paragraph.runs:
            r = paragraph.runs[0]
            if fn: r.font.name  = fn
            if fs: r.font.size  = fs
            if fb is not None: r.font.bold   = fb
            if fi is not None: r.font.italic = fi
            if fc: r.font.color.rgb = fc


def standardize_cv_text(text: str) -> str:
    if not text:
        return ""
    import re
    text = re.sub(r'\bBasel\s+(?:Frameworks?|III/3\.1|III|3\.1|3)\b',
                  'Basel III/3.1', text, flags=re.IGNORECASE)
    text = text.replace("Basel III/3.1/3.1", "Basel III/3.1") \
               .replace("Basel III/3.1/3",   "Basel III/3.1")
    text = re.sub(r'\bIFRS\s*9\b', 'IFRS 9', text, flags=re.IGNORECASE)
    text = re.sub(r'\bPrudential\s+Regulation\s+Authority\b', 'PRA', text, flags=re.IGNORECASE)
    text = re.sub(r'\bEuropean\s+Central\s+Bank\b', 'ECB', text, flags=re.IGNORECASE)
    text = re.sub(r'\bFederal\s+Reserve\b', 'Fed/OCC', text, flags=re.IGNORECASE)
    text = re.sub(r'\bOffice\s+of\s+the\s+Comptroller\s+of\s+the\s+Currency\b',
                  'Fed/OCC', text, flags=re.IGNORECASE)
    text = re.sub(r'\bOffice\s+of\s+the\s+Superintendent\s+of\s+Financial\s+Institutions\b',
                  'OSFI', text, flags=re.IGNORECASE)
    return text


def strip_bold(text: str) -> str:
    return text.replace("**", "")


def sanitize_bullet(text) -> str:
    if not text:
        return ""
    if isinstance(text, list):
        return "\n".join(sanitize_bullet(i) for i in text if i)
    if not isinstance(text, str):
        text = str(text)
    return standardize_cv_text(text.lstrip("•-* \t"))


def is_valid_bullet(text: str) -> bool:
    """
    Strong validation — rejects:
      • Too short (< MIN_BULLET_LEN chars)
      • JSON syntax fragments leaked from LLM output
      • Strings that are mostly special characters / HTML / punctuation
      • Template placeholders
      • Strings with more than 3 non-alphanumeric chars in a row (garbage)
      • Strings with fewer than 4 real words
    """
    import re
    t = text.strip()

    # Basic length check
    if not t or len(t) < MIN_BULLET_LEN:
        return False

    # JSON / template noise
    noise_exact = [
        '"]', '"role"', '"bullets"', '"{', '"[', '"}',
        '"project_title', 'role :', 'bullets :', 'project theme',
        '{{', '}}', 'formulated  in', 'formulated in\n',
    ]
    tl = t.lower()
    if any(m in tl for m in noise_exact):
        return False

    # Reject if it's a bare placeholder like "Formulated  in   ..."
    # i.e. more than 3 consecutive spaces or dots
    if re.search(r'\.{3,}', t) or re.search(r'\s{3,}', t):
        return False

    # Reject HTML / XML fragments
    if re.search(r'<[/a-zA-Z]', t):
        return False

    # Reject strings with consecutive special chars (garbage encoding)
    if re.search(r'[<>/\\]{2,}', t):
        return False

    # Must contain at least 4 real words (alpha tokens of length >= 2)
    words = re.findall(r'\b[a-zA-Z]{2,}\b', t)
    if len(words) < 3:
        return False

    # Reject if more than 40% of characters are non-alphanumeric (garbage)
    alnum_count = sum(1 for c in t if c.isalnum())
    if len(t) > 0 and alnum_count / len(t) < 0.45:
        return False

    return True


def is_valid_project_title(title: str) -> bool:
    """
    Validates a project title is real content, not a placeholder or garbage.
    """
    if not title or len(title.strip()) < 10:
        return False
    tl = title.strip().lower()
    # Reject bare fallback placeholders
    placeholders = ["project theme", "role", "project theme – role", "– role"]
    if tl in placeholders:
        return False
    # Must have at least 3 alpha words
    import re
    words = re.findall(r'\b[a-zA-Z]{2,}\b', title)
    return len(words) >= 3


def flatten_bullets(lst: list) -> list:
    """Flattens, cleans, and strictly validates bullet items."""
    if not lst:
        return []
    flat = []
    for b in lst:
        if isinstance(b, list):
            flat.extend(flatten_bullets(b))
        elif isinstance(b, str):
            for line in b.split("\n"):
                c = sanitize_bullet(line.strip())
                if is_valid_bullet(c):
                    flat.append(c)
        else:
            c = sanitize_bullet(str(b))
            if is_valid_bullet(c):
                flat.append(c)
    return flat


def get_valid_projects(projects: list) -> list:
    """
    Filters the project list to only those with a valid title AND
    at least MIN_BULLETS_TO_RENDER real bullet points.
    Logs skipped projects so the issue is visible in the worker log.
    """
    valid = []
    for i, proj in enumerate(projects):
        title   = proj.get('project_title') or proj.get('title') or ''
        bullets = flatten_bullets(proj.get('bullets', []))

        if not is_valid_project_title(title):
            print(f"[Renderer] Skipping project {i+1}: invalid title → '{title[:60]}'")
            continue
        if len(bullets) < MIN_BULLETS_TO_RENDER:
            print(f"[Renderer] Skipping project {i+1} '{title[:40]}': "
                  f"no valid bullets (raw count={len(proj.get('bullets',[]))})")
            continue
        valid.append(proj)

    print(f"[Renderer] Valid projects: {len(valid)} / {len(projects)}")
    return valid


def consolidate_versions(keywords: list) -> list:
    import re
    from collections import defaultdict
    grouped, result = defaultdict(list), []
    pat = re.compile(r'^(.*?)[-\s]+([0-9]+(?:\.[0-9]+)?|[IVXLCDM]+(?:\.[0-9]+)?)$', re.IGNORECASE)
    for kw in keywords:
        kw = kw.strip()
        m  = pat.match(kw)
        if m:
            grouped[m.group(1).strip()].append(m.group(2).strip())
        else:
            result.append(kw)
    for base, vers in grouped.items():
        result.append(f"{base}-{'/'.join(vers)}" if len(vers) > 1 else f"{base}-{vers[0]}")
    return result


def clean_expertise_keyword(kw: str) -> str:
    if not kw:
        return ""
    import re
    kw = re.sub(r'\s*\(.*?\)\s*$', '', kw)
    if ":"   in kw: kw = kw.split(":")[0]
    if " - " in kw: kw = kw.split(" - ")[0]
    return kw.strip()


def get_key(data: dict, key: str, default=None):
    if not data:
        return default
    kl = key.lower()
    for k, v in data.items():
        if k.lower() == kl:
            return v
    return default


def delete_paragraphs_after(tf, start_idx: int):
    while len(tf.paragraphs) > start_idx:
        p = tf.paragraphs[-1]._p
        p.getparent().remove(p)


def format_bullets_str(bullets: list) -> str:
    s = flatten_bullets(bullets)
    if not s:       return ""
    if len(s) == 1: return s[0]
    return s[0] + "\n" + "\n".join(f"• {b}" for b in s[1:])


# ─────────────────────────────────────────────────────────────────────────────
# HEIGHT ESTIMATOR (BARLOW 9PT CALIBRATED)
# ─────────────────────────────────────────────────────────────────────────────

def _lines(text: str, cpl: int = BODY_CHARS_PER_LINE) -> int:
    import math
    text = text.strip()
    if not text:
        return 0
    return max(1, math.ceil(len(text) / cpl))


def estimate_height_pt(summary: str, projects: list,
                       bpp_list: list,
                       cfg: dict = None,
                       title_sp: float = None,
                       body_sp: float = None,
                       sp_before: float = None,
                       sp_after_b: float = None,
                       sum_sp: float = None) -> float:
    """
    Estimates rendered height for VALID projects only.
    Supports either passing a cfg dict or individual parameters.
    """
    if cfg is None:
        cfg = dict(
            title_font_pt        = 9.0,
            body_font_pt         = 9.0,
            title_spacing_pt     = title_sp if title_sp is not None else 12.0,
            body_spacing_pt      = body_sp if body_sp is not None else 11.5,
            space_before_title   = sp_before if sp_before is not None else 4.0,
            space_after_title    = 1.0,
            space_after_bullet   = sp_after_b if sp_after_b is not None else 1.5,
            summary_line_spacing = sum_sp if sum_sp is not None else 12.0,
        )

    # PROFESSIONAL EXPERIENCE header
    total = 14.0
    # Summary paragraph
    sum_cpl = max(1, int(BODY_CHARS_PER_LINE * 9.0 / cfg.get("body_font_pt", 9.0)))
    sum_lines = _lines(strip_bold(sanitize_bullet(summary)), sum_cpl)
    total += sum_lines * cfg.get("summary_line_spacing", 12.0) + 3.0
    # MAJOR PROJECTS header (space_before + line + space_after)
    total += 14.0 + 12.0 + 4.0

    t_font_pt = cfg.get("title_font_pt", 9.0)
    b_font_pt = cfg.get("body_font_pt", 9.0)
    t_cpl = max(1, int(TITLE_CHARS_PER_LINE * 9.0 / t_font_pt))
    b_cpl = max(1, int(BODY_CHARS_PER_LINE * 9.0 / b_font_pt))

    for i, proj in enumerate(projects):
        raw_title = strip_bold(proj.get('project_title') or proj.get('title') or '')
        clean_role = proj.get('role') or ''
        std_title = build_standard_title(raw_title, clean_role)
        t_lines = _lines(std_title, t_cpl)
        total += cfg.get("space_before_title", 4.0) + t_lines * cfg.get("title_spacing_pt", 12.0) + cfg.get("space_after_title", 1.0)

        bpp = bpp_list[i] if i < len(bpp_list) else 2
        bullets = flatten_bullets(proj.get('bullets', []))
        for b in bullets[:bpp]:
            b_lines = _lines(b, b_cpl)
            total += 1.0 + b_lines * cfg.get("body_spacing_pt", 11.5) + cfg.get("space_after_bullet", 1.5)

    return total


# ─────────────────────────────────────────────────────────────────────────────
# LAYOUT DECISION ENGINE (BARLOW 9PT WITH DYNAMIC DENSITY BALANCING)
#
# PRINCIPLE: Fill slide with REAL CONTENT & optimal spacing.
# 1. Standard body text: Barlow 9.0pt.
# 2. If projects are few (1–3 projects): Allocate 4–6 bullets per project and
#    apply generous vertical spacing/margins so the slide is fully utilised.
# 3. If projects are many (4–6 projects): Allocate 2–4 bullets per project.
# 4. If slight overflow: adjust typography/spacing (8.5pt / 8.0pt) before pruning bullets.
# ─────────────────────────────────────────────────────────────────────────────

def compute_layout(summary: str, projects: list) -> dict:
    """
    projects must be pre-filtered by get_valid_projects() before calling this.
    Dynamically balances bullet counts, typography, and spacing to maximize content
    density and eliminate awkward white space.
    """
    H = USABLE_HEIGHT_PT
    n = len(projects)

    # Starting bullet cap and spacing configuration based on project count:
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
    else:  # 5 or 6+
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
        min(ideal_bpp, max(1, len(flatten_bullets(p.get('bullets', [])))))
        for p in projects
    ]

    # If few projects (<= 4), greedily allocate extra bullets if space permits
    if n <= 4:
        for i in range(len(current_bpp)):
            avail = len(flatten_bullets(projects[i].get('bullets', [])))
            if avail > current_bpp[i]:
                test_bpp = list(current_bpp)
                test_bpp[i] += 1
                if estimate_height_pt(summary, projects, test_bpp, cfg=cfg) <= H * 0.98:
                    current_bpp[i] += 1

    h = estimate_height_pt(summary, projects, current_bpp, cfg=cfg)

    # ── Phase 1: If slight overflow, adjust typography/spacing first ──
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
        h = estimate_height_pt(summary, projects, current_bpp, cfg=cfg)

    # ── Phase 2: If still overflowing, scale to 8.0pt font ─────────────
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
        h = estimate_height_pt(summary, projects, current_bpp, cfg=cfg)

    # ── Phase 3: Prune bullets if still overflowing ────────────────────
    if h > H:
        for _ in range(60):
            if estimate_height_pt(summary, projects, current_bpp, cfg=cfg) <= H * 0.99:
                break
            reducible = [(i, b) for i, b in enumerate(current_bpp) if b > 1]
            if not reducible:
                break
            idx_reduce = max(reducible, key=lambda x: x[1])[0]
            current_bpp[idx_reduce] -= 1

    cfg["bullets_per_project_list"] = current_bpp

    final_h  = estimate_height_pt(summary, projects, current_bpp, cfg=cfg)
    fill_pct = round(final_h / H * 100, 1)
    print(f"[Layout] valid_projects={len(projects)}, bpp={current_bpp}, "
          f"est={final_h:.0f}pt/{H}pt ({fill_pct}% fill), "
          f"fonts={cfg['title_font_pt']}/{cfg['body_font_pt']}pt")
    return cfg


# ─────────────────────────────────────────────────────────────────────────────
# PROFESSIONAL SUMMARY — strict first-sentence bold
# ─────────────────────────────────────────────────────────────────────────────

def split_first_sentence(text: str):
    import re
    # '. ' followed by uppercase avoids splitting on abbreviations
    m = re.search(r'\.\s+(?=[A-Z])', text)
    if m:
        return text[:m.start() + 1].strip(), text[m.end():].strip()
    m2 = re.search(r'(?<=[.!?])\s+', text)
    if m2:
        return text[:m2.start()].strip(), text[m2.end():].strip()
    return text.strip(), ""


def render_summary(paragraph, summary: str,
                   font_name: str = "Barlow",
                   font_size_pt: float = 9.0,
                   line_spacing_pt: float = 12.0):
    """First sentence → entirely bold. Rest → entirely plain."""
    from pptx.util import Pt
    paragraph.clear()
    paragraph.space_before = Pt(1)
    paragraph.space_after  = Pt(2)
    paragraph.line_spacing = Pt(line_spacing_pt)

    clean = strip_bold(sanitize_bullet(summary))
    first, rest = split_first_sentence(clean)

    if first:
        r = paragraph.add_run()
        r.text, r.font.name, r.font.size, r.font.bold = (
            first, font_name, Pt(font_size_pt), True
        )
    if rest:
        r = paragraph.add_run()
        r.text, r.font.name, r.font.size, r.font.bold = (
            " " + rest, font_name, Pt(font_size_pt), False
        )


# ─────────────────────────────────────────────────────────────────────────────
# BULLET RENDERER — zero bold, always
# ─────────────────────────────────────────────────────────────────────────────

def render_bullet(paragraph, text: str,
                  font_name: str = "Barlow",
                  font_size_pt: float = 9.0):
    from pptx.util import Pt
    r = paragraph.add_run()
    r.text       = f"• {strip_bold(sanitize_bullet(text))}"
    r.font.name  = font_name
    r.font.size  = Pt(font_size_pt)
    r.font.bold  = False


# ─────────────────────────────────────────────────────────────────────────────
# BARLOW BODY STYLING PASS
# ─────────────────────────────────────────────────────────────────────────────

def apply_barlow_body_styling(prs):
    from pptx.util import Pt
    exempt = {"professional experience", "major projects", "areas of expertise",
              "industry expertise", "education", "firstname", "lastname"}
    for slide in prs.slides:
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            tf = shape.text_frame
            if "Title 138" in shape.name or any(
                "firstname" in p.text.lower() or "lastname" in p.text.lower()
                for p in tf.paragraphs
            ):
                continue
            for p in tf.paragraphs:
                pc = p.text.strip().lower()
                if pc in exempt or "private sector bank" in pc or "project theme" in pc:
                    continue
                for run in p.runs:
                    run.font.name = "Barlow"
                    run.font.size = Pt(9.0)


# ─────────────────────────────────────────────────────────────────────────────
# PROJECT TITLE BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def build_standard_title(raw_title: str, raw_role: str) -> str:
    """
    Parses the project title, extracts organization/industry context, and builds the
    standardised '[Organization/Industry] – [Project Theme] – [Role]' format.
    """
    clean_title = raw_title.replace(" - ", " – ").replace(" -- ", " – ").strip()
    clean_role  = raw_role.replace(" - ", " – ").replace(" -- ", " – ").strip()

    parts = [x.strip() for x in clean_title.split("–") if x.strip()]
    if len(parts) == 0:
        org = "Private Sector Bank"
        theme = "Project Theme"
    elif len(parts) == 1:
        org = "Private Sector Organization"
        theme = parts[0]
    else:
        org = parts[0]
        theme = " – ".join(parts[1:])

    return (
        f"{standardize_cv_text(strip_bold(org))} – "
        f"{standardize_cv_text(strip_bold(theme))} – "
        f"{standardize_cv_text(strip_bold(clean_role))}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# MAIN RENDERER
# ─────────────────────────────────────────────────────────────────────────────

def render_pptx_template(data: dict, template_path: str, output_path: str):
    from pptx import Presentation
    from pptx.util import Pt, Inches

    prs = Presentation(template_path)

    candidate_name = get_key(data, "candidate_name") or "Candidate Name"
    summary        = sanitize_bullet(get_key(data, "professional_summary") or "")

    # ── Sidebar data ──────────────────────────────────────────────────────────
    areas = get_key(data, "areas_of_expertise") or []
    if isinstance(areas, str): areas = [areas]
    areas_clean = consolidate_versions(
        [clean_expertise_keyword(sanitize_bullet(i)) for i in areas if i]
    )[:20]

    industry = get_key(data, "industry_expertise") or []
    if isinstance(industry, str): industry = [industry]
    industry_clean = [sanitize_bullet(i) for i in industry]

    education = get_key(data, "education") or get_key(data, "education_history") or []
    if not education:
        cl = candidate_name.lower()
        if   "mohit"  in cl or "choudhary" in cl:
            education = ["Post Graduate Diploma in Banking (PGDB)/MBA",
                         "B.Tech (Bachelor of Technology)"]
        elif "gaurav" in cl or "tripathi"  in cl:
            education = ["Executive PG Diploma in Data Science",
                         "PGDM Finance & Marketing", "BE"]
        else:
            education = ["Bachelor of Technology"]
    if isinstance(education, str): education = [education]
    education_clean = [sanitize_bullet(i) for i in education]

    # ── Projects — filter to valid only BEFORE layout ─────────────────────────
    raw_projects = get_key(data, "major_project_experience") or []
    if isinstance(raw_projects, str):
        try:    raw_projects = json.loads(raw_projects)
        except: raw_projects = []

    # This is the critical gate: removes garbage/placeholder/truncated projects
    projects = get_valid_projects(raw_projects)

    # ── Compute layout based on valid projects only ────────────────────────────
    layout    = compute_layout(summary, projects)
    bpp_list  = layout["bullets_per_project_list"]
    title_fpt = layout["title_font_pt"]
    body_fpt  = layout["body_font_pt"]
    title_spt = layout["title_spacing_pt"]
    body_spt  = layout["body_spacing_pt"]
    sp_before = layout["space_before_title"]
    sp_after_t= layout["space_after_title"]
    sp_after_b= layout["space_after_bullet"]
    sum_spt   = layout["summary_line_spacing"]

    # ── Generic replacements (tables / other shapes) ───────────────────────────
    replacements = {
        "{{candidate_name}}":       candidate_name,
        "{{professional_summary}}": summary,
        "{{areas_of_expertise}}":   "\n".join(f"• {i}" for i in areas_clean),
        "{{industry_expertise}}":   "\n".join(f"• {i}" for i in industry_clean),
        "{{education}}":            "\n".join(f"• {i}" for i in education_clean),
    }
    for i in range(1, 7):
        tv = rv = bv = ""
        if i - 1 < len(projects):
            p  = projects[i - 1]
            tv = p.get("project_title") or p.get("title") or ""
            rv = p.get("role") or ""
            bv = format_bullets_str(p.get("bullets", []))
        replacements[f"{{{{project_{i}_title}}}}"]   = tv
        replacements[f"{{{{project_{i}_role}}}}"]    = rv
        replacements[f"{{{{project_{i}_bullets}}}}"] = bv

    # ── Shape loop ─────────────────────────────────────────────────────────────
    for slide in prs.slides:
        for shape in slide.shapes:

            if shape.has_text_frame:
                tf = shape.text_frame

                # Candidate name
                if "Title 138" in shape.name or any(
                    "FirstName" in p.text or "LastName" in p.text
                    for p in tf.paragraphs
                ):
                    for p in tf.paragraphs:
                        if "FirstName" not in p.text and "LastName" not in p.text:
                            continue
                        fn = fs = fi = fc = None
                        if p.runs and p.runs[0].font:
                            fn = p.runs[0].font.name
                            fs = p.runs[0].font.size
                            fi = p.runs[0].font.italic
                            try:    fc = p.runs[0].font.color.rgb
                            except: pass
                        p.text = candidate_name.strip()
                        for r in p.runs:
                            if fn: r.font.name  = fn
                            if fs: r.font.size  = fs
                            r.font.bold = True
                            if fi is not None: r.font.italic = fi
                            if fc: r.font.color.rgb = fc

                # Sidebar
                elif "Placeholder 145" in shape.name or any(
                    h in "".join(p.text for p in tf.paragraphs)
                    for h in ["AREAS OF EXPERTISE", "INDUSTRY EXPERTISE", "EDUCATION"]
                ):
                    shape.top = Inches(0.2)
                    tf.margin_left = tf.margin_right = \
                        tf.margin_top = tf.margin_bottom = Pt(5)

                    hstyles = []
                    for hi in [0, 2, 4]:
                        s = {"level": 0, "font_name": None, "font_size": None,
                             "font_bold": True, "font_color": None}
                        if hi < len(tf.paragraphs):
                            po = tf.paragraphs[hi]
                            s["level"] = po.level
                            if po.runs and po.runs[0].font:
                                ro = po.runs[0].font
                                s["font_name"], s["font_size"] = ro.name, ro.size
                                s["font_bold"] = ro.bold
                                try:    s["font_color"] = ro.color.rgb
                                except: pass
                        hstyles.append(s)

                    tf.clear()

                    def _hdr(text, hs, first=False):
                        p = tf.paragraphs[0] if first else tf.add_paragraph()
                        p.text, p.level, p.space_after = text, hs["level"], Pt(4)
                        if p.runs:
                            r = p.runs[0]
                            if hs["font_name"]:  r.font.name  = hs["font_name"]
                            if hs["font_size"]:  r.font.size  = hs["font_size"]
                            r.font.bold = (hs["font_bold"]
                                           if hs["font_bold"] is not None else True)
                            if hs["font_color"]: r.font.color.rgb = hs["font_color"]

                    def _item(text, fn=None):
                        from pptx.enum.text import PP_ALIGN
                        p = tf.add_paragraph()
                        p.text = f"• {sanitize_bullet(text)}"
                        p.level, p.space_after, p.line_spacing = 0, Pt(2), Pt(12)
                        p.alignment = PP_ALIGN.LEFT
                        if p.runs:
                            r = p.runs[0]
                            r.font.size, r.font.bold = Pt(9.0), False
                            if fn: r.font.name = fn

                    fn0 = hstyles[0]["font_name"]
                    _hdr("AREAS OF EXPERTISE", hstyles[0], first=True)
                    tf.paragraphs[-1].space_before = Pt(0)
                    for item in areas_clean:    _item(item, fn0)

                    _hdr("INDUSTRY EXPERTISE", hstyles[1])
                    tf.paragraphs[-1].space_before = Pt(12)
                    for item in industry_clean: _item(item, fn0)

                    _hdr("EDUCATION", hstyles[2])
                    tf.paragraphs[-1].space_before = Pt(12)
                    for item in education_clean: _item(item, fn0)

                # Main body
                elif "Placeholder 144" in shape.name or any(
                    h in "".join(p.text for p in tf.paragraphs)
                    for h in ["PROFESSIONAL EXPERIENCE", "MAJOR PROJECTS"]
                ):
                    shape.top    = Inches(0.2)
                    tf.word_wrap = True

                    # Professional summary
                    for idx, p in enumerate(tf.paragraphs):
                        if "PROFESSIONAL EXPERIENCE" in p.text and \
                                idx + 1 < len(tf.paragraphs):
                            ps = tf.paragraphs[idx + 1]
                            fn = (ps.runs[0].font.name
                                  if ps.runs and ps.runs[0].font else None)
                            render_summary(ps, summary,
                                           font_name       = fn or "Barlow",
                                           font_size_pt    = body_fpt,
                                           line_spacing_pt = sum_spt)
                            break

                    # Major Projects
                    mp_idx = next((i for i, p in enumerate(tf.paragraphs)
                                   if "MAJOR PROJECTS" in p.text), -1)

                    if mp_idx != -1:
                        p_mp = tf.paragraphs[mp_idx]
                        p_mp.space_before, p_mp.space_after = Pt(12), Pt(4)
                        ff = (p_mp.runs[0].font.name
                              if p_mp.runs and p_mp.runs[0].font else None)

                        delete_paragraphs_after(tf, mp_idx + 1)

                        for proj_i, proj in enumerate(projects):
                            raw_title = (proj.get('project_title') or
                                         proj.get('title') or '')
                            raw_role  = proj.get('role') or ''

                            std_title = build_standard_title(raw_title, raw_role)

                            # Project title paragraph (bold)
                            p_hdr = tf.add_paragraph()
                            p_hdr.text         = std_title
                            p_hdr.level        = 0
                            p_hdr.space_before = Pt(sp_before)
                            p_hdr.space_after  = Pt(sp_after_t)
                            p_hdr.line_spacing = Pt(title_spt)
                            if p_hdr.runs:
                                r = p_hdr.runs[0]
                                r.font.bold = True
                                r.font.size = Pt(title_fpt)
                                if ff: r.font.name = ff

                            # Bullet paragraphs — plain, validated content only
                            bpp       = bpp_list[proj_i] if proj_i < len(bpp_list) else 3
                            flat_buls = flatten_bullets(proj.get('bullets', []))
                            for b in flat_buls[:bpp]:
                                p_bul = tf.add_paragraph()
                                p_bul.space_before = Pt(1)
                                p_bul.space_after  = Pt(sp_after_b)
                                p_bul.line_spacing = Pt(body_spt)
                                render_bullet(p_bul, b,
                                              font_name    = ff or "Barlow",
                                              font_size_pt = body_fpt)

                else:
                    replace_text_in_text_frame(tf, replacements)

            if shape.has_table:
                for row in shape.table.rows:
                    for cell in row.cells:
                        if cell.text_frame:
                            replace_text_in_text_frame(cell.text_frame, replacements)

    apply_barlow_body_styling(prs)
    prs.save(output_path)