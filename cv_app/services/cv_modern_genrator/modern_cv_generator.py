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
from typing import Dict, Any, List
from datetime import datetime

# ==========================================
# 1. CONFIGURATION & COLORS
# ==========================================

# Color Palette
COLOR_BG_SIDEBAR = colors.HexColor("#0f172a")      # Slate 900 (Dark Blue/Black)
COLOR_TEXT_SIDEBAR = colors.HexColor("#f8fafc")     # Slate 50 (White/Off-White)
COLOR_TEXT_SIDEBAR_MUTED = colors.HexColor("#cbd5e1") # Slate 300 (Light Gray)
COLOR_BG_MAIN = colors.white
COLOR_RED_MAIN = colors.HexColor("#DC2626")         # Red 600 (Accent)
COLOR_TEXT_MAIN = colors.HexColor("#374151")        # Gray 700 (Primary Text)
COLOR_TEXT_SUB = colors.HexColor("#4B5563")         # Gray 600 (Secondary Text)
COLOR_BORDER_LIGHT = colors.HexColor("#e5e7eb")      # Gray 200 (Light Border)
COLOR_BG_LIGHT = colors.HexColor("#f9fafb")         # Gray 50 (Light Background)

def get_modern_styles():
    """Defines styles specific to the Modern Sidebar design"""
    styles = getSampleStyleSheet()
    
    # Use Helvetica for a clean, modern look
    font_sans = "Helvetica"
    font_sans_bold = "Helvetica-Bold"

    # --- SIDEBAR STYLES ---
    styles.add(ParagraphStyle(
        name="SidebarHeader",
        fontName=font_sans_bold,
        fontSize=10,
        leading=14,
        textColor=COLOR_RED_MAIN,
        textTransform='uppercase',
        spaceAfter=6
    ))
    
    styles.add(ParagraphStyle(
        name="SidebarText",
        fontName=font_sans,
        fontSize=9,
        leading=12,
        textColor=COLOR_TEXT_SIDEBAR_MUTED,
        wordWrap='CJK' # Helps wrap long emails/links
    ))

    styles.add(ParagraphStyle(
        name="SidebarLabel",
        fontName=font_sans_bold,
        fontSize=7,
        leading=10,
        textColor=colors.HexColor("#64748b"), # Slate 500
        textTransform='uppercase'
    ))

    # --- MAIN CONTENT STYLES ---
    styles.add(ParagraphStyle(
        name="MainName",
        fontName=font_sans_bold,
        fontSize=32,
        leading=34,
        textColor=COLOR_RED_MAIN,
        spaceAfter=4
    ))
    
    styles.add(ParagraphStyle(
        name="MainNameSub",
        fontName=font_sans,
        fontSize=32,
        leading=34,
        textColor=COLOR_TEXT_MAIN,
    ))

    styles.add(ParagraphStyle(
        name="MainSectionHeader",
        fontName=font_sans_bold,
        fontSize=14,
        leading=18,
        textColor=COLOR_TEXT_MAIN,
        textTransform='uppercase',
        spaceBefore=12,
        spaceAfter=8,
        borderLeftWidth=3,
        borderLeftColor=COLOR_RED_MAIN,
        leftIndent=6,
    ))

    styles.add(ParagraphStyle(
        name="MainText",
        fontName=font_sans,
        fontSize=10,
        leading=14,
        textColor=COLOR_TEXT_SUB,
        alignment=TA_JUSTIFY
    ))

    styles.add(ParagraphStyle(
        name="JobTitle",
        fontName=font_sans_bold,
        fontSize=11,
        leading=13,
        textColor=COLOR_TEXT_MAIN,
    ))

    styles.add(ParagraphStyle(
        name="JobMeta",
        fontName=font_sans_bold,
        fontSize=9,
        leading=11,
        textColor=COLOR_RED_MAIN,
    ))

    return styles

# ==========================================
# 2. IMAGE PROCESSING (CIRCULAR CROP)
# ==========================================
def process_profile_image(path, size=35*mm):
    """Loads an image and crops it into a circle"""
    try:
        if path.startswith(settings.MEDIA_URL):
            path = path[len(settings.MEDIA_URL):]
        full_path = os.path.join(settings.MEDIA_ROOT, path.lstrip("/"))

        if not os.path.exists(full_path):
            return None

        # Open and convert
        img = PILImage.open(full_path).convert("RGBA")
        
        # Create circular mask
        mask = PILImage.new('L', img.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0) + img.size, fill=255)
        
        # Apply mask
        output = PILImage.new('RGBA', img.size, (0, 0, 0, 0))
        output.paste(img, (0, 0), mask=mask)
        
        img_buffer = io.BytesIO()
        output.save(img_buffer, format="PNG")
        img_buffer.seek(0)
        
        return Image(img_buffer, width=size, height=size)
    except Exception as e:
        print(f"Image Error: {e}")
        return None

# ==========================================
# 3. BUILDERS (LEFT & RIGHT)
# ==========================================

def build_left_column(data: Dict[str, Any], styles) -> List:
    """Builds the dark sidebar content: Photo, Contact, Skills, Languages"""
    flow = []
    
    # --- Profile Image ---
    if data.get("profile_image"):
        img = process_profile_image(data.get("profile_image"))
        if img:
            # Add padding below image
            t = Table([[img]], colWidths=[40*mm])
            t.setStyle(TableStyle([
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('BOTTOMPADDING', (0,0), (-1,-1), 20),
            ]))
            flow.append(t)
    else:
        # Placeholder Initials if no image
        full_name = data.get("full_name", "")
        initial = full_name[0] if full_name else "?"
        flow.append(Paragraph(f"<b>{initial}</b>", ParagraphStyle('Init', fontName='Helvetica-Bold', fontSize=40, textColor=colors.gray, alignment=TA_CENTER)))
        flow.append(Spacer(1, 20))

    # --- Contact Info ---
    flow.append(Paragraph("Contact", styles['SidebarHeader']))
    # Decorative underline
    flow.append(Table([['']], colWidths=[10*mm], rowHeights=[1], style=TableStyle([('LINEBELOW', (0,0), (-1,-1), 1, colors.HexColor("#334155"))])))
    flow.append(Spacer(1, 8))

    contacts = [
        ("Email", data.get("email")),
        ("Phone", data.get("phone")),
        ("Address", data.get("address")),
        ("LinkedIn", data.get("linkedin")),
        ("GitHub", data.get("github"))
    ]

    for label, value in contacts:
        if value:
            flow.append(Paragraph(label, styles['SidebarLabel']))
            flow.append(Paragraph(value, styles['SidebarText']))
            flow.append(Spacer(1, 6))
    
    flow.append(Spacer(1, 15))

    # --- Skills (Pills) ---
    tech_skills = data.get('technical_skills', [])
    soft_skills = data.get('soft_skills', [])
    all_skills = tech_skills + soft_skills

    if all_skills:
        flow.append(Paragraph("Skills", styles['SidebarHeader']))
        flow.append(Table([['']], colWidths=[10*mm], rowHeights=[1], style=TableStyle([('LINEBELOW', (0,0), (-1,-1), 1, colors.HexColor("#334155"))])))
        flow.append(Spacer(1, 8))
        
        for skill in all_skills:
            if not skill: continue
            # Darker Pill Background for sidebar
            p = Table([[Paragraph(skill, ParagraphStyle('S', fontName='Helvetica', fontSize=8, textColor=colors.white))]], 
                      colWidths=[None], # Auto width
                      style=TableStyle([
                          ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#1e293b")),
                          ('ROUNDED', (0,0), (-1,-1), 4),
                          ('LEFTPADDING', (0,0), (-1,-1), 8),
                          ('RIGHTPADDING', (0,0), (-1,-1), 8),
                          ('TOPPADDING', (0,0), (-1,-1), 3),
                          ('BOTTOMPADDING', (0,0), (-1,-1), 3),
                          ('BORDERCOLOR', (0,0), (-1,-1), colors.HexColor("#334155")),
                          ('BORDERWIDTH', (0,0), (-1,-1), 0.5),
                      ]))
            flow.append(p)
            flow.append(Spacer(1, 4))
        flow.append(Spacer(1, 15))

    # --- Languages ---
    if data.get('languages'):
        flow.append(Paragraph("Languages", styles['SidebarHeader']))
        flow.append(Table([['']], colWidths=[10*mm], rowHeights=[1], style=TableStyle([('LINEBELOW', (0,0), (-1,-1), 1, colors.HexColor("#334155"))])))
        flow.append(Spacer(1, 8))
        
        for lang in data.get('languages'):
            if lang.get('language'):
                row = Table([[
                    Paragraph(lang.get('language'), styles['SidebarText']),
                    Paragraph(lang.get('proficiency', ''), ParagraphStyle('P', fontName='Helvetica', fontSize=7, textColor=colors.HexColor("#94a3b8"), alignment=TA_RIGHT))
                ]], colWidths=[35*mm, 20*mm])
                flow.append(row)
                flow.append(Spacer(1, 4))

    # --- Certifications (Sidebar) ---
    if data.get('certificates'):
        flow.append(Spacer(1, 10))
        flow.append(Paragraph("Certificates", styles['SidebarHeader']))
        flow.append(Table([['']], colWidths=[10*mm], rowHeights=[1], style=TableStyle([('LINEBELOW', (0,0), (-1,-1), 1, colors.HexColor("#334155"))])))
        flow.append(Spacer(1, 8))
        
        for c in data.get('certificates'):
            if c.get('name'):
                flow.append(Paragraph(c.get('name'), ParagraphStyle('CB', fontName='Helvetica-Bold', fontSize=8, textColor=colors.white)))
                issuer_date = f"{c.get('issuer', '')}"
                if c.get('date'):
                    issuer_date += f" ({c.get('date')})"
                flow.append(Paragraph(issuer_date, styles['SidebarText']))
                flow.append(Spacer(1, 6))

    return flow

def build_right_column(data: Dict[str, Any], styles) -> List:
    """Builds the main content: Name, Profile, Exp, Projects, Edu, Refs"""
    flow = []
    
    # --- Header Name ---
    first = data.get("first_name", "").upper()
    last = data.get("last_name", "").upper()
    
    # Using a single paragraph with font tag for color change
    name_text = f"{first} <font color='#374151'>{last}</font>"
    flow.append(Paragraph(name_text, styles['MainName']))
    
    # Header Divider
    flow.append(Spacer(1, 4))
    flow.append(Table([['']], colWidths=[130*mm], rowHeights=[1], style=TableStyle([('LINEBELOW', (0,0), (-1,-1), 2, colors.HexColor("#f3f4f6"))])))
    flow.append(Spacer(1, 12))

    # --- Profile Summary ---
    if data.get('profile_summary'):
        flow.append(Paragraph("Profile", styles['MainSectionHeader']))
        # Light gray box with red left border
        t = Table([[Paragraph(data.get('profile_summary'), styles['MainText'])]], colWidths=[130*mm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), COLOR_BG_LIGHT),
            ('LEFTPADDING', (0,0), (-1,-1), 10),
            ('RIGHTPADDING', (0,0), (-1,-1), 10),
            ('TOPPADDING', (0,0), (-1,-1), 10),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
            ('LINEBEFORE', (0,0), (-1,-1), 4, colors.HexColor("#fee2e2")),
            ('ROUNDED', (0,0), (-1,-1), 4),
        ]))
        flow.append(t)
        flow.append(Spacer(1, 10))

    # --- Work Experience ---
    exps = data.get('work_experiences', [])
    if exps:
        flow.append(Paragraph("Experience", styles['MainSectionHeader']))
        
        # Sort by date (newest first)
        def parse_date(d):
            try: return datetime.strptime(d, "%Y-%m-%d")
            except: return datetime.min
        exps.sort(key=lambda x: parse_date(x.get('start_date')), reverse=True)

        for work in exps:
            # Row 1: Job Title (Left) | Date Badge (Right)
            title = work.get('job_title', '')
            dates = f"{work.get('start_date')} - {work.get('end_date') or 'Present'}"
            
            # Date Badge Table
            date_badge = Table([[Paragraph(dates, ParagraphStyle('D', fontName='Helvetica-Bold', fontSize=8, textColor=COLOR_RED_MAIN))]], 
                               style=TableStyle([
                                   ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#fef2f2")),
                                   ('ROUNDED', (0,0), (-1,-1), 4),
                                   ('LEFTPADDING', (0,0), (-1,-1), 6),
                                   ('RIGHTPADDING', (0,0), (-1,-1), 6),
                               ]))
            
            row1 = Table([[
                Paragraph(title, styles['JobTitle']),
                date_badge
            ]], colWidths=[95*mm, 30*mm])
            row1.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
            
            # Row 2: Company • Location
            meta = f"{work.get('company')} • {work.get('location')}"
            
            # Row 3: Responsibilities (Bullet List)
            resps = []
            if work.get('responsibilities'):
                resps = [
                    ListItem(Paragraph(r, styles['MainText']), 
                             bulletColor=COLOR_RED_MAIN, 
                             bulletType='bullet', 
                             bulletFontSize=6) 
                    for r in work.get('responsibilities') if r
                ]
            
            # Combine into one block
            items = [row1, Paragraph(meta, styles['MainText']), Spacer(1,4)]
            if resps:
                items.append(ListFlowable(resps, bulletType='bullet', start='circle', leftIndent=10))
            
            # Wrap in container with Left Line (Timeline effect)
            container = Table([[items]], colWidths=[130*mm])
            container.setStyle(TableStyle([
                ('LEFTPADDING', (0,0), (-1,-1), 12),
                ('LINEBEFORE', (0,0), (0,0), 2, colors.HexColor("#fca5a5")), # Light red line
                ('BOTTOMPADDING', (0,0), (-1,-1), 12),
            ]))
            flow.append(KeepTogether(container))

    # --- Projects ---
    projs = data.get('projects', [])
    if projs:
        flow.append(Paragraph("Projects", styles['MainSectionHeader']))
        for p in projs:
            title = p.get('title')
            link = p.get('link')
            
            header_items = [Paragraph(f"<b>{title}</b>", styles['JobTitle'])]
            if link: 
                header_items.append(Paragraph(f'<a href="{link}" color="#DC2626">Link ↗</a>', 
                                              ParagraphStyle('L', fontName='Helvetica', fontSize=8, textColor=COLOR_RED_MAIN, alignment=TA_RIGHT)))
            
            # Header Table
            h_tbl = Table([header_items], colWidths=[100*mm, 20*mm])
            
            content = [h_tbl, Paragraph(p.get('description', ''), styles['MainText'])]
            
            if p.get('technologies'):
                techs = p.get('technologies', [])
                if isinstance(techs, list):
                    tech_str = ", ".join([str(t) for t in techs])
                else:
                    tech_str = str(techs)
                content.append(Spacer(1, 2))
                content.append(Paragraph(f"<i>Stack: {tech_str}</i>", ParagraphStyle('T', fontName='Helvetica-Oblique', fontSize=8, textColor=colors.gray)))
            
            # Boxed Project Card
            card = Table([[content]], colWidths=[130*mm])
            card.setStyle(TableStyle([
                ('BOX', (0,0), (-1,-1), 0.5, COLOR_BORDER_LIGHT),
                ('ROUNDED', (0,0), (-1,-1), 4),
                ('LEFTPADDING', (0,0), (-1,-1), 8),
                ('RIGHTPADDING', (0,0), (-1,-1), 8),
                ('TOPPADDING', (0,0), (-1,-1), 6),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ]))
            flow.append(KeepTogether(card))
            flow.append(Spacer(1, 6))

    # --- Education ---
    edus = data.get('educations', [])
    if edus:
        flow.append(Paragraph("Education", styles['MainSectionHeader']))
        for edu in edus:
            text = f"<b>{edu.get('degree')}</b><br/>{edu.get('institution')}"
            date = f"{edu.get('start_date')} - {edu.get('end_date')}"
            
            t = Table([[
                Paragraph(text, styles['MainText']),
                Paragraph(date, ParagraphStyle('D', fontName='Helvetica-Bold', fontSize=9, textColor=COLOR_RED_MAIN, alignment=TA_RIGHT))
            ]], colWidths=[90*mm, 40*mm])
            
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), COLOR_BG_LIGHT),
                ('LEFTPADDING', (0,0), (-1,-1), 8),
                ('RIGHTPADDING', (0,0), (-1,-1), 8),
                ('TOPPADDING', (0,0), (-1,-1), 6),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ('LINEBEFORE', (0,0), (0,0), 3, colors.gray) # Gray accent
            ]))
            flow.append(KeepTogether(t))
            flow.append(Spacer(1, 6))

    # --- References ---
    refs = data.get('references', [])
    if refs:
        flow.append(Paragraph("References", styles['MainSectionHeader']))
        for ref in refs:
            name = ref.get('name', '')
            pos = ref.get('position', '')
            contact = f"{ref.get('email')} | {ref.get('phone')}"
            
            ref_text = f"<b>{name}</b> — {pos}<br/><font size=9 color='#64748b'>{contact}</font>"
            flow.append(Paragraph(ref_text, styles['MainText']))
            flow.append(Spacer(1, 4))

    return flow

# ==========================================
# 4. PAGE CANVAS DRAWING (The Background)
# ==========================================
def on_page_draw(canvas, doc):
    """
    Draws the persistent Sidebar Background on EVERY page.
    Draws the Sidebar CONTENT (Left Column) only on Page 1.
    """
    canvas.saveState()
    
    # 1. Draw Dark Sidebar Background (Left 32%)
    sidebar_width = 68*mm
    page_width, page_height = A4
    
    canvas.setFillColor(COLOR_BG_SIDEBAR)
    canvas.rect(0, 0, sidebar_width, page_height, fill=1, stroke=0)
    
    # 2. Draw Left Content ONLY on Page 1
    # This solves the "Flowable too large" error by separating the sidebar content 
    # from the main document flow.
    if doc.page == 1 and hasattr(doc, 'left_flowables'):
        # Create a Frame that matches the visual sidebar area
        # Padding: Left 10mm, Right 5mm, Top 10mm, Bottom 10mm
        frame_x = 10*mm
        frame_y = 10*mm
        frame_w = sidebar_width - 15*mm
        frame_h = page_height - 20*mm
        
        sidebar_frame = Frame(frame_x, frame_y, frame_w, frame_h, id='sidebar', showBoundary=0)
        
        # Copy list to avoid consuming the original if re-render happens
        story_copy = doc.left_flowables[:]
        sidebar_frame.addFromList(story_copy, canvas)
        
    canvas.restoreState()

# ==========================================
# 5. MAIN GENERATOR FUNCTION
# ==========================================
def generate_modern_sidebar_cv(data: Dict[str, Any], output_path: str) -> str:
    """Generate a modern sidebar CV PDF"""
    styles = get_modern_styles()
    
    # Layout Dimensions
    col_width_left = 68*mm
    right_margin = 18*mm
    top_margin = 18*mm
    bottom_margin = 18*mm
    
    # The main content frame starts AFTER the sidebar width + padding
    frame_x = col_width_left + 10*mm 
    frame_w = A4[0] - frame_x - right_margin
    frame_h = A4[1] - top_margin - bottom_margin
    
    # Define Document
    doc = BaseDocTemplate(
        output_path, 
        pagesize=A4, 
        leftMargin=0, 
        rightMargin=0, 
        topMargin=0, 
        bottomMargin=0
    )
    
    # Define the Main Content Frame (Right Side)
    main_frame = Frame(frame_x, bottom_margin, frame_w, frame_h, id='main_content', showBoundary=0)
    
    # Attach 'on_page_draw' to handle the sidebar background & content
    template = PageTemplate(id='modern_layout', frames=[main_frame], onPage=on_page_draw)
    doc.addPageTemplates([template])
    
    # 1. Build Left Data (stored in doc for callback)
    doc.left_flowables = build_left_column(data, styles)
    
    # 2. Build Right Data (main flow)
    right_flowables = build_right_column(data, styles)
    
    # 3. Build PDF
    doc.build(right_flowables)
    return output_path