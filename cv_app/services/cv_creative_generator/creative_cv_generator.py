from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, 
    Spacer, Table, TableStyle, ListFlowable, ListItem, Image, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY, TA_RIGHT, TA_CENTER
from PIL import Image as PILImage, ImageDraw
import os
import io
from django.conf import settings
from typing import Dict, Any
from datetime import datetime

# ==========================================
# 1. CONFIGURATION & COLORS
# ==========================================

COLOR_SLATE_900 = colors.HexColor("#0f172a") 
COLOR_RED_MAIN  = colors.HexColor("#DC2626")
COLOR_GRAY_50   = colors.HexColor("#F9FAFB")
COLOR_GRAY_200  = colors.HexColor("#E5E7EB")
COLOR_TEXT_MAIN = colors.HexColor("#334155") # Slate 700
COLOR_TEXT_SUB  = colors.HexColor("#64748b") # Slate 500
COLOR_WHITE     = colors.white

def get_creative_styles():
    styles = getSampleStyleSheet()
    font_sans = "Helvetica"
    font_sans_bold = "Helvetica-Bold"

    # --- HEADER STYLES ---
    styles.add(ParagraphStyle(
        name="HeaderFirst", 
        fontName=font_sans_bold, 
        fontSize=28, 
        leading=28, 
        textColor=COLOR_WHITE, 
        textTransform='uppercase'
    ))
    styles.add(ParagraphStyle(
        name="HeaderLast", 
        fontName=font_sans_bold, 
        fontSize=28, 
        leading=32, 
        textColor=COLOR_RED_MAIN, 
        textTransform='uppercase'
    ))

    # --- SIDEBAR STYLES ---
    styles.add(ParagraphStyle(
        name="SidebarHeader", 
        fontName=font_sans_bold, 
        fontSize=9, 
        leading=11, 
        textColor=COLOR_SLATE_900, 
        textTransform='uppercase',
        spaceAfter=4
    ))
    styles.add(ParagraphStyle(name="SidebarText", fontName=font_sans, fontSize=8, leading=11, textColor=COLOR_TEXT_SUB))
    styles.add(ParagraphStyle(name="SidebarBold", fontName=font_sans_bold, fontSize=8, leading=11, textColor=COLOR_RED_MAIN))
    styles.add(ParagraphStyle(name="SidebarDate", fontName=font_sans, fontSize=7, leading=9, textColor=colors.gray))

    # --- MAIN CONTENT STYLES ---
    styles.add(ParagraphStyle(
        name="MainHeader", 
        fontName=font_sans_bold, 
        fontSize=14, 
        leading=18, 
        textColor=COLOR_SLATE_900, 
        textTransform='uppercase'
    ))
    styles.add(ParagraphStyle(name="Slash", fontName=font_sans_bold, fontSize=18, leading=18, textColor=COLOR_RED_MAIN))
    styles.add(ParagraphStyle(name="BodyText", fontName=font_sans, fontSize=10, leading=14, textColor=COLOR_TEXT_SUB, alignment=TA_JUSTIFY))
    
    styles.add(ParagraphStyle(name="JobTitle", fontName=font_sans_bold, fontSize=12, leading=14, textColor=COLOR_SLATE_900))
    styles.add(ParagraphStyle(name="JobCompany", fontName=font_sans_bold, fontSize=9, leading=11, textColor=COLOR_TEXT_SUB))
    styles.add(ParagraphStyle(name="JobDate", fontName=font_sans_bold, fontSize=8, leading=10, textColor=COLOR_RED_MAIN))

    return styles

# ==========================================
# 2. IMAGE PROCESSING
# ==========================================
def process_profile_image(path, size=35*mm):
    try:
        if path.startswith(settings.MEDIA_URL):
            path = path[len(settings.MEDIA_URL):]
        full_path = os.path.join(settings.MEDIA_ROOT, path.lstrip("/"))
        if not os.path.exists(full_path): return None

        img = PILImage.open(full_path).convert("RGBA")
        # Resize
        img.thumbnail((size*3, size*3)) # high res
        img_buffer = io.BytesIO()
        img.save(img_buffer, format="PNG")
        img_buffer.seek(0)
        return Image(img_buffer, width=size, height=size)
    except:
        return None

# ==========================================
# 3. BUILDER FUNCTIONS
# ==========================================

def build_header_text(data, styles):
    """Builds the First/Last Name for the header."""
    first = data.get("first_name", "").upper()
    last = data.get("last_name", "").upper()
    
    # The header text is drawn inside the dark header area.
    # We position it using a Frame later, but here we build the flowable.
    return [
        Paragraph(first, styles['HeaderFirst']),
        Paragraph(last, styles['HeaderLast'])
    ]

def build_left_sidebar(data, styles):
    """Builds Sidebar Content (Contact, Edu, Skills, Lang)"""
    flow = []
    
    # Spacer to clear the overlapping image area
    # Image is ~32mm, plus top margin 10mm = ~42mm down. 
    # We want sidebar to start below that.
    flow.append(Spacer(1, 35*mm))
    
    # --- Contact ---
    contacts = []
    if data.get('email'): contacts.append(f"✉ {data.get('email')}")
    if data.get('phone'): contacts.append(f"📞 {data.get('phone')}")
    if data.get('address'): contacts.append(f"📍 {data.get('address')}")
    if data.get('linkedin'): contacts.append(f"🔗 LinkedIn")
    
    if contacts:
        flow.append(Paragraph("CONTACT", styles['SidebarHeader']))
        c_items = []
        for c in contacts:
            c_items.append(Paragraph(c, styles['SidebarText']))
            c_items.append(Spacer(1, 2))
        
        c_tbl = Table([[c_items]], colWidths=[60*mm])
        c_tbl.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), COLOR_GRAY_50),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('RIGHTPADDING', (0,0), (-1,-1), 8),
            ('TOPPADDING', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('LINEBEFORE', (0,0), (0,0), 3, COLOR_RED_MAIN),
            ('ROUNDED', (0,0), (-1,-1), 4),
        ]))
        flow.append(c_tbl)
        flow.append(Spacer(1, 10*mm))

    # --- Education ---
    edus = data.get('educations', [])
    if edus:
        flow.append(Paragraph("EDUCATION", styles['SidebarHeader']))
        flow.append(Table([['']], colWidths=[60*mm], style=TableStyle([('LINEBELOW', (0,0), (-1,-1), 0.5, COLOR_GRAY_200)])))
        flow.append(Spacer(1, 3*mm))
        for edu in edus:
            flow.append(Paragraph(edu.get('degree', ''), styles['SidebarBold']))
            flow.append(Paragraph(edu.get('institution', ''), styles['SidebarText']))
            flow.append(Paragraph(f"{edu.get('start_date')} - {edu.get('end_date')}", styles['SidebarDate']))
            flow.append(Spacer(1, 4*mm))

    # --- Skills ---
    tech = data.get('technical_skills', [])
    soft = data.get('soft_skills', [])
    all_skills = tech + soft
    if all_skills:
        flow.append(Paragraph("EXPERTISE", styles['SidebarHeader']))
        flow.append(Table([['']], colWidths=[60*mm], style=TableStyle([('LINEBELOW', (0,0), (-1,-1), 0.5, COLOR_GRAY_200)])))
        flow.append(Spacer(1, 3*mm))
        
        # Dark Slate Pills
        pill_style = ParagraphStyle('Pill', fontName='Helvetica-Bold', fontSize=7, textColor=colors.white)
        for skill in all_skills:
            if not skill: continue
            p = Table([[Paragraph(skill, pill_style)]], style=TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), COLOR_SLATE_900),
                ('ROUNDED', (0,0), (-1,-1), 4),
                ('LEFTPADDING', (0,0), (-1,-1), 6),
                ('RIGHTPADDING', (0,0), (-1,-1), 6),
                ('TOPPADDING', (0,0), (-1,-1), 2),
                ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ]))
            flow.append(p)
            flow.append(Spacer(1, 2))
        flow.append(Spacer(1, 10*mm))

    # --- Languages ---
    langs = data.get('languages', [])
    if langs:
        flow.append(Paragraph("LANGUAGES", styles['SidebarHeader']))
        flow.append(Table([['']], colWidths=[60*mm], style=TableStyle([('LINEBELOW', (0,0), (-1,-1), 0.5, COLOR_GRAY_200)])))
        flow.append(Spacer(1, 3*mm))
        for l in langs:
            row = Table([[
                Paragraph(l.get('language'), styles['SidebarText']),
                Paragraph(l.get('proficiency'), ParagraphStyle('Prof', fontSize=7, textColor=COLOR_RED_MAIN, alignment=TA_RIGHT))
            ]], colWidths=[35*mm, 25*mm])
            flow.append(row)
            flow.append(Spacer(1, 2*mm))

    return flow

def build_main_content(data, styles):
    """Builds Right Content: Profile, Exp, Projects, Certs"""
    flow = []
    
    # Push content down below Header (55mm) + some gap
    # Note: The Frame itself will start below the header, but let's add a small spacer
    flow.append(Spacer(1, 5*mm))

    def make_section_head(text):
        t = Table([[
            Paragraph("/", styles['Slash']),
            Paragraph(text, styles['MainHeader'])
        ]], colWidths=[6*mm, None])
        t.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
        return t

    # --- Profile ---
    if data.get('profile_summary'):
        flow.append(make_section_head("About Me"))
        flow.append(Spacer(1, 2*mm))
        flow.append(Paragraph(data.get('profile_summary'), styles['BodyText']))
        flow.append(Spacer(1, 8*mm))

    # --- Experience ---
    exps = data.get('work_experiences', [])
    if exps:
        flow.append(make_section_head("Experience"))
        flow.append(Spacer(1, 4*mm))
        
        # Sort
        def parse_date(d):
            try: return datetime.strptime(d, "%Y-%m-%d")
            except: return datetime.min
        exps.sort(key=lambda x: parse_date(x.get('start_date')), reverse=True)

        for work in exps:
            title = work.get('job_title', '')
            company = work.get('company', '')
            dates = f"{work.get('start_date')} - {work.get('end_date') or 'Present'}"
            
            content_cell = [
                Table([[Paragraph(title, styles['JobTitle'])]], colWidths=['100%']),
                Table([[
                    Paragraph(company, styles['JobCompany']),
                    Paragraph(dates, ParagraphStyle('JD', fontSize=8, textColor=COLOR_RED_MAIN, backColor=colors.HexColor("#FEF2F2"), borderPadding=2))
                ]], colWidths=[80*mm, 35*mm]),
                Spacer(1, 2*mm)
            ]
            
            if work.get('responsibilities'):
                resps = [ListItem(Paragraph(r, styles['BodyText']), leftIndent=8, bulletColor=COLOR_TEXT_SUB) for r in work.get('responsibilities') if r]
                content_cell.append(ListFlowable(resps, bulletType='bullet', start='•', leftIndent=0))

            t_exp = Table([[content_cell]], colWidths=[115*mm])
            t_exp.setStyle(TableStyle([
                ('LEFTPADDING', (0,0), (-1,-1), 6*mm),
                ('LINEBEFORE', (0,0), (0,0), 0.5, COLOR_GRAY_200),
            ]))
            flow.append(KeepTogether(t_exp))
            flow.append(Spacer(1, 6*mm))

    # --- Projects ---
    projs = data.get('projects', [])
    if projs:
        flow.append(make_section_head("Projects"))
        flow.append(Spacer(1, 4*mm))
        for p in projs:
            title = p.get('title')
            link = p.get('link')
            
            header_items = [Paragraph(f"<b>{title}</b>", styles['JobTitle'])]
            if link: header_items.append(Paragraph(f'<a href="{link}" color="#DC2626">Link ↗</a>', ParagraphStyle('L', fontSize=8, textColor=COLOR_RED_MAIN, alignment=TA_RIGHT)))
            
            content = [
                Table([header_items], colWidths=[90*mm, 20*mm]),
                Paragraph(p.get('description', ''), styles['BodyText'])
            ]
            if p.get('technologies'):
                tech_str = ", ".join(p.get('technologies'))
                content.append(Paragraph(f"<i>{tech_str}</i>", ParagraphStyle('T', fontSize=8, textColor=colors.gray)))
                
            p_tbl = Table([[content]], colWidths=[115*mm])
            p_tbl.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), COLOR_GRAY_50),
                ('LEFTPADDING', (0,0), (-1,-1), 10),
                ('RIGHTPADDING', (0,0), (-1,-1), 10),
                ('TOPPADDING', (0,0), (-1,-1), 8),
                ('BOTTOMPADDING', (0,0), (-1,-1), 8),
                ('LINEBEFORE', (0,0), (0,0), 3, COLOR_SLATE_900),
                ('ROUNDED', (0,0), (-1,-1), 4),
            ]))
            flow.append(KeepTogether(p_tbl))
            flow.append(Spacer(1, 4*mm))

    # --- Certifications (Main Content Grid) ---
    certs = data.get('certificates', [])
    if certs:
        flow.append(make_section_head("Certifications"))
        flow.append(Spacer(1, 4*mm))
        
        cert_rows = []
        current_row = []
        for c in certs:
            cell = [
                Paragraph(c.get('name'), styles['JobCompany']),
                Paragraph(f"{c.get('issuer')} • {c.get('date')}", ParagraphStyle('CMeta', fontSize=8, textColor=colors.gray))
            ]
            c_tbl = Table([[cell]], colWidths=[55*mm])
            c_tbl.setStyle(TableStyle([
                ('BOX', (0,0), (-1,-1), 0.5, COLOR_GRAY_200),
                ('LEFTPADDING', (0,0), (-1,-1), 6),
                ('TOPPADDING', (0,0), (-1,-1), 4),
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                ('ROUNDED', (0,0), (-1,-1), 4),
            ]))
            
            current_row.append(c_tbl)
            if len(current_row) == 2:
                cert_rows.append(current_row)
                current_row = []
        
        if current_row: cert_rows.append(current_row + [''] * (2-len(current_row)))
        if cert_rows:
            flow.append(Table(cert_rows, colWidths=[58*mm, 58*mm]))

    return flow

# ==========================================
# 5. PAGE CANVAS (The Background)
# ==========================================
def on_page_draw(canvas, doc):
    """
    Draws the static header background and profile image on Page 1.
    Draws the Sidebar CONTENT only on Page 1.
    """
    canvas.saveState()
    page_width, page_height = A4
    
    # --- 1. Draw Header Background (Page 1 Only) ---
    if doc.page == 1:
        header_height = 55*mm
        canvas.setFillColor(COLOR_SLATE_900)
        # Draw rect at top
        canvas.rect(0, page_height - header_height, page_width, header_height, fill=1, stroke=0)
        
        # --- 2. Draw Profile Image (Overlapping) ---
        if hasattr(doc, 'profile_image_obj') and doc.profile_image_obj:
            img_size = 32*mm
            # Position: Left 10mm, straddling the header line
            x_pos = 10*mm
            # Bottom of header is at (page_height - 55mm)
            # We want image centered on that line: y = (page_height - 55mm) - (size/2)
            y_pos = (page_height - header_height) - (img_size / 2) + 5*mm # Adjust up slightly
            
            # White Border Box
            canvas.setFillColor(colors.white)
            canvas.roundRect(x_pos - 1*mm, y_pos - 1*mm, img_size + 2*mm, img_size + 2*mm, 2*mm, fill=1, stroke=0)
            
            # Image
            doc.profile_image_obj.drawOn(canvas, x_pos, y_pos)

        # --- 3. Draw Header TEXT (Name) ---
        # We draw the name flowable manually here so it sits on top of the dark background
        if hasattr(doc, 'header_text_flowables'):
            # Create a temporary frame for the header text area
            # Area: To right of image (10mm + 32mm + padding) -> 50mm start
            text_x = 50*mm
            text_y = page_height - header_height
            text_w = page_width - text_x - 10*mm
            text_h = header_height
            
            header_frame = Frame(text_x, text_y, text_w, text_h, id='header_text', showBoundary=0)
            # Vertical alignment trick: Spacer
            story = [Spacer(1, 15*mm)] + doc.header_text_flowables[:] 
            header_frame.addFromList(story, canvas)

        # --- 4. Draw Left Sidebar Content ---
        # The main document flow handles the RIGHT column.
        # We manually pour the LEFT column content here.
        if hasattr(doc, 'left_sidebar_flowables'):
            sidebar_width = 73*mm # ~35% width
            sidebar_x = 10*mm
            sidebar_y = 10*mm
            sidebar_w = sidebar_width - 15*mm
            # Start below the overlapping image area
            # Image bottom is at approx (page_height - 55mm - 16mm) = page_height - 71mm
            sidebar_h = page_height - 80*mm 
            
            sidebar_frame = Frame(sidebar_x, sidebar_y, sidebar_w, sidebar_h, id='sidebar', showBoundary=0)
            sidebar_frame.addFromList(doc.left_sidebar_flowables[:], canvas)

    canvas.restoreState()

# ==========================================
# 6. MAIN GENERATOR
# ==========================================
def generate_creative_cv(data: Dict[str, Any], output_path: str):
    styles = get_creative_styles()
    
    # Frame Layout
    # Left Sidebar is ~35% (73mm), Right is ~65% (137mm)
    # We reserve the Left Area. The DocTemplate will only fill the RIGHT area.
    
    col_width_left = 73*mm
    right_margin = 10*mm
    bottom_margin = 10*mm
    header_height = 55*mm
    
    # Main Content Frame (Right Side)
    # Starts after sidebar width
    frame_x = col_width_left + 5*mm
    frame_w = A4[0] - frame_x - right_margin
    # Starts below header
    frame_y = bottom_margin
    frame_h = A4[1] - header_height - bottom_margin - 5*mm # small gap
    
    doc = BaseDocTemplate(output_path, pagesize=A4, 
                          leftMargin=0, rightMargin=0, topMargin=0, bottomMargin=0)
    
    main_frame = Frame(frame_x, frame_y, frame_w, frame_h, id='main_content', showBoundary=0)
    
    template = PageTemplate(id='creative', frames=[main_frame], onPage=on_page_draw)
    doc.addPageTemplates([template])
    
    # 1. Prepare Data for Callback (Left Side + Header)
    doc.profile_image_obj = None
    if data.get('profile_image'):
        doc.profile_image_obj = process_profile_image(data.get('profile_image'))
        
    doc.header_text_flowables = build_header_text(data, styles)
    doc.left_sidebar_flowables = build_left_sidebar(data, styles)
    
    # 2. Build Main Content (Right Side) - This drives the document flow
    story = build_main_content(data, styles)
    
    doc.build(story)
    return output_path