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
COLOR_RED_MAIN = colors.HexColor("#DC2626")    # Tailwind Red 600
COLOR_BG_SIDEBAR = colors.HexColor("#F9FAFB")  # Gray 50
COLOR_TEXT_MAIN = colors.HexColor("#374151")   # Gray 700
COLOR_TEXT_SUB = colors.HexColor("#6B7280")    # Gray 500
COLOR_BORDER = colors.HexColor("#E5E7EB")      # Gray 200
COLOR_BG_LIGHT = colors.HexColor("#F3F4F6")    # Gray 100

def get_minimalist_styles():
    """Defines styles for the minimalist CV design"""
    styles = getSampleStyleSheet()
    font_sans = "Helvetica"
    font_sans_bold = "Helvetica-Bold"

    # --- HEADER STYLES ---
    styles.add(ParagraphStyle(
        name="HeaderName", 
        fontName=font_sans_bold, 
        fontSize=26, 
        leading=30, 
        textColor=COLOR_TEXT_MAIN, 
        alignment=TA_CENTER, 
        textTransform='uppercase', 
        spaceAfter=6
    ))
    
    styles.add(ParagraphStyle(
        name="HeaderContact", 
        fontName=font_sans, 
        fontSize=9, 
        leading=12, 
        textColor=COLOR_TEXT_SUB, 
        alignment=TA_CENTER
    ))

    # --- SECTION HEADERS ---
    styles.add(ParagraphStyle(
        name="SectionHeader", 
        fontName=font_sans_bold, 
        fontSize=11, 
        leading=14, 
        textColor=COLOR_RED_MAIN, 
        textTransform='uppercase',
        spaceAfter=4
    ))

    # --- TEXT STYLES ---
    styles.add(ParagraphStyle(
        name="MinimalBodyText",  
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
        textColor=COLOR_TEXT_MAIN
    ))
    
    styles.add(ParagraphStyle(
        name="JobMeta", 
        fontName=font_sans, 
        fontSize=10, 
        leading=12, 
        textColor=COLOR_RED_MAIN
    ))
    
    styles.add(ParagraphStyle(
        name="DateBadge", 
        fontName=font_sans_bold, 
        fontSize=7, 
        leading=9, 
        textColor=COLOR_TEXT_MAIN, 
        backColor=COLOR_BG_LIGHT, 
        borderPadding=3
    ))
    
    # --- SIDEBAR SPECIFIC ---
    styles.add(ParagraphStyle(
        name="SidebarTitle", 
        fontName=font_sans_bold, 
        fontSize=10, 
        leading=12, 
        textColor=COLOR_RED_MAIN
    ))
    
    styles.add(ParagraphStyle(
        name="SidebarText", 
        fontName=font_sans, 
        fontSize=9, 
        leading=11, 
        textColor=COLOR_TEXT_MAIN
    ))
    
    styles.add(ParagraphStyle(
        name="SidebarSub", 
        fontName=font_sans, 
        fontSize=8, 
        leading=10, 
        textColor=COLOR_TEXT_SUB
    ))

    return styles

# ==========================================
# 2. HELPER: CIRCULAR IMAGE
# ==========================================
def process_profile_image(path, size=28*mm):
    """Process profile image to create circular crop"""
    try:
        if path.startswith(settings.MEDIA_URL):
            path = path[len(settings.MEDIA_URL):]
        full_path = os.path.join(settings.MEDIA_ROOT, path.lstrip("/"))
        if not os.path.exists(full_path): 
            return None

        img = PILImage.open(full_path).convert("RGBA")
        mask = PILImage.new('L', img.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0) + img.size, fill=255)
        output = PILImage.new('RGBA', img.size, (0, 0, 0, 0))
        output.paste(img, (0, 0), mask=mask)
        
        img_buffer = io.BytesIO()
        output.save(img_buffer, format="PNG")
        img_buffer.seek(0)
        return Image(img_buffer, width=size, height=size)
    except Exception as e:
        print(f"Error processing profile image: {e}")
        return None

# ==========================================
# 3. BUILDER FUNCTIONS
# ==========================================

def section_header(title, styles):
    """Creates the Red Uppercase header with a bottom red border"""
    text = Paragraph(title, styles['SectionHeader'])
    # Using a table to create the bottom border effect just under the text
    t = Table([[text]], colWidths=[None])
    t.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('LINEBELOW', (0,0), (-1,-1), 2, COLOR_RED_MAIN),
    ]))
    return t

def build_header_section(data, styles):
    """Builds the header section with name, photo, and contact info"""
    flow = []
    
    # 1. Decorative Red Top Border
    flow.append(Table([['']], colWidths=['100%'], rowHeights=[2*mm], style=TableStyle([('BACKGROUND', (0,0), (-1,-1), COLOR_RED_MAIN)])))
    flow.append(Spacer(1, 8*mm))

    # 2. Profile Image
    if data.get("profile_image"):
        img = process_profile_image(data.get("profile_image"))
        if img:
            # Wrap in table to center
            t_img = Table([[img]], colWidths=[210*mm])
            t_img.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER')]))
            flow.append(t_img)
            flow.append(Spacer(1, 4*mm))

    # 3. Name
    full_name = f"{data.get('first_name', '')} {data.get('middle_name', '')} {data.get('last_name', '')}".strip().upper()
    flow.append(Paragraph(full_name, styles['HeaderName']))
    flow.append(Spacer(1, 2*mm))

    # 4. Contact Row
    parts = []
    if data.get('email'): parts.append(f"✉ {data.get('email')}")
    if data.get('phone'): parts.append(f"📞 {data.get('phone')}")
    if data.get('address'): parts.append(f"📍 {data.get('address')}")
    if data.get('linkedin'): parts.append("🔗 LinkedIn")
    if data.get('github'): parts.append("💻 GitHub")
    
    contact_str = "  &nbsp; • &nbsp;  ".join(parts)
    flow.append(Paragraph(contact_str, styles['HeaderContact']))
    
    # Bottom border for header
    flow.append(Spacer(1, 6*mm))
    flow.append(Table([['']], colWidths=['100%'], style=TableStyle([('LINEBELOW', (0,0), (-1,-1), 0.5, COLOR_BORDER)])))
    flow.append(Spacer(1, 6*mm))
    
    return flow

def build_left_content(data, styles):
    """Builds the main content area (left column)"""
    flow = []
    
    # --- Profile Summary ---
    if data.get('profile_summary'):
        flow.append(section_header("Professional Profile", styles))
        flow.append(Spacer(1, 3*mm))
        flow.append(Paragraph(data.get('profile_summary'), styles['MinimalBodyText'])) 
        flow.append(Spacer(1, 8*mm))

    # --- Work Experience ---
    exps = data.get('work_experiences', [])
    if exps:
        flow.append(section_header("Work Experience", styles))
        flow.append(Spacer(1, 4*mm))
        
        # Sort by date (newest first)
        def parse_date(d):
            try: return datetime.strptime(d, "%Y-%m-%d")
            except: return datetime.min
        exps.sort(key=lambda x: parse_date(x.get('start_date')), reverse=True)
        
        for work in exps:
            # Title Row
            title = work.get('job_title', '')
            dates = f"{work.get('start_date')} - {work.get('end_date') or 'Present'}"
            
            # Use table for Title + Date Badge float right
            t_head = Table([[
                Paragraph(title, styles['JobTitle']),
                Paragraph(dates, styles['DateBadge'])
            ]], colWidths=[None, 35*mm])
            t_head.setStyle(TableStyle([
                ('ALIGN', (1,0), (1,0), 'RIGHT'), 
                ('LEFTPADDING', (0,0), (-1,-1), 0),
                ('RIGHTPADDING', (0,0), (-1,-1), 0)
            ]))
            flow.append(t_head)
            
            # Company
            meta = f"{work.get('company')} , {work.get('location')}"
            flow.append(Paragraph(meta, styles['JobMeta']))
            flow.append(Spacer(1, 2*mm))

            # Responsibilities
            if work.get('responsibilities'):
                resps = [ListItem(Paragraph(r, styles['MinimalBodyText']), leftIndent=10, bulletColor=COLOR_TEXT_SUB) 
                         for r in work.get('responsibilities') if r]
                flow.append(ListFlowable(resps, bulletType='bullet', start='•'))
            
            flow.append(Spacer(1, 6*mm))

    # --- Projects ---
    projs = data.get('projects', [])
    if projs:
        flow.append(section_header("Key Projects", styles))
        flow.append(Spacer(1, 4*mm))
        
        for p in projs:
            p_title = p.get('title')
            p_link = f"  <a href='{p.get('link')}' color='#DC2626'>[Link]</a>" if p.get('link') else ""
            
            flow.append(Paragraph(f"<b>{p_title}</b>{p_link}", styles['JobTitle']))
            flow.append(Paragraph(p.get('description', ''), styles['MinimalBodyText']))
            
            # Tech Stack
            if p.get('technologies'):
                tech_str = " | ".join([str(t) for t in p.get('technologies', [])])
                flow.append(Paragraph(f"<font size=8 color='#6B7280'>#{tech_str}</font>", styles['MinimalBodyText']))
            
            flow.append(Table([['']], colWidths=['100%'], style=TableStyle([('LINEBELOW', (0,0), (-1,-1), 0.5, COLOR_BORDER)])))
            flow.append(Spacer(1, 4*mm))
            
    # --- Achievements ---
    achievements = data.get('achievements', [])
    if achievements:
        flow.append(section_header("Achievements", styles))
        flow.append(Spacer(1, 3*mm))
        items = [ListItem(Paragraph(a, styles['MinimalBodyText']), leftIndent=10) for a in achievements if a]
        flow.append(ListFlowable(items, bulletType='bullet', start='•'))

    return flow

def build_right_sidebar(data, styles):
    """Builds the right sidebar content"""
    flow = []
    
    # --- Education ---
    edus = data.get('educations', [])
    if edus:
        flow.append(section_header("Education", styles))
        flow.append(Spacer(1, 4*mm))
        for edu in edus:
            flow.append(Paragraph(edu.get('degree', ''), styles['SidebarTitle']))
            flow.append(Paragraph(edu.get('institution', ''), styles['SidebarText']))
            flow.append(Paragraph(f"{edu.get('start_date')} - {edu.get('end_date')}", styles['SidebarSub']))
            if edu.get('grade'):
                flow.append(Paragraph(f"Grade: {edu.get('grade')}", styles['SidebarSub']))
            flow.append(Spacer(1, 4*mm))

    # --- Skills ---
    tech_skills = data.get('technical_skills', [])
    soft_skills = data.get('soft_skills', [])
    
    if tech_skills or soft_skills:
        flow.append(section_header("Skills", styles))
        flow.append(Spacer(1, 4*mm))
        
        if tech_skills:
            flow.append(Paragraph("TECHNICAL", ParagraphStyle('Sub', fontSize=7, textColor=colors.gray)))
            flow.append(Spacer(1, 2))
            for skill in tech_skills:
                pill = Table([[Paragraph(skill, styles['SidebarText'])]], colWidths=[None])
                pill.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,-1), colors.white),
                    ('BOX', (0,0), (-1,-1), 0.5, COLOR_BORDER),
                    ('LINEBEFORE', (0,0), (0,0), 3, COLOR_RED_MAIN),
                    ('LEFTPADDING', (0,0), (-1,-1), 8),
                    ('RIGHTPADDING', (0,0), (-1,-1), 8),
                    ('TOPPADDING', (0,0), (-1,-1), 3),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 3),
                    ('ROUNDED', (0,0), (-1,-1), 4),
                ]))
                flow.append(pill)
                flow.append(Spacer(1, 2*mm))
        
        if soft_skills:
            flow.append(Spacer(1, 2*mm))
            flow.append(Paragraph("SOFT SKILLS", ParagraphStyle('Sub', fontSize=7, textColor=colors.gray)))
            flow.append(Spacer(1, 2))
            soft_str = " • ".join([str(s) for s in soft_skills])
            flow.append(Paragraph(f"<i>{soft_str}</i>", styles['SidebarSub']))
            flow.append(Spacer(1, 6*mm))

    # --- Languages ---
    langs = data.get('languages', [])
    if langs:
        flow.append(section_header("Languages", styles))
        flow.append(Spacer(1, 4*mm))
        for l in langs:
            t = Table([[
                Paragraph(l.get('language'), styles['SidebarText']),
                Paragraph(l.get('proficiency'), ParagraphStyle('Prof', fontSize=8, textColor=COLOR_RED_MAIN, alignment=TA_RIGHT))
            ]], colWidths=[40*mm, 25*mm])
            t.setStyle(TableStyle([
                ('LINEBELOW', (0,0), (-1,-1), 0.25, COLOR_BORDER),
                ('BOTTOMPADDING', (0,0), (-1,-1), 2),
                ('LEFTPADDING', (0,0), (-1,-1), 0),
            ]))
            flow.append(t)
            flow.append(Spacer(1, 2*mm))
        flow.append(Spacer(1, 4*mm))

    # --- Certifications ---
    certs = data.get('certificates', [])
    if certs:
        flow.append(section_header("Certifications", styles))
        flow.append(Spacer(1, 4*mm))
        for c in certs:
            c_content = [
                Paragraph(f"<b>{c.get('name')}</b>", styles['SidebarText']),
                Paragraph(c.get('issuer'), ParagraphStyle('Iss', fontSize=8, textColor=COLOR_RED_MAIN)),
                Paragraph(c.get('date'), styles['SidebarSub']),
            ]
            c_tbl = Table([[c_content]], colWidths=[65*mm])
            c_tbl.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.white),
                ('BOX', (0,0), (-1,-1), 0.5, COLOR_BORDER),
                ('LEFTPADDING', (0,0), (-1,-1), 6),
                ('TOPPADDING', (0,0), (-1,-1), 4),
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ]))
            flow.append(c_tbl)
            flow.append(Spacer(1, 2*mm))

    # --- References ---
    refs = data.get('references', [])
    if refs:
        flow.append(Spacer(1, 4*mm))
        flow.append(section_header("References", styles))
        flow.append(Spacer(1, 4*mm))
        for r in refs:
            flow.append(Paragraph(f"<b>{r.get('name')}</b>", styles['SidebarText']))
            flow.append(Paragraph(r.get('position'), styles['SidebarSub']))
            flow.append(Paragraph(f"{r.get('email')}<br/>{r.get('phone')}", styles['SidebarSub']))
            flow.append(Spacer(1, 3*mm))

    return flow

# ==========================================
# 4. MASTER GENERATOR
# ==========================================

def generate_minimalist_cv(data: Dict[str, Any], output_path: str) -> str:
    """Generate a minimalist CV PDF"""
    try:
        styles = get_minimalist_styles()
        
        # 0 margins because we control layout with Master Table
        doc = BaseDocTemplate(output_path, pagesize=A4, leftMargin=0, rightMargin=0, topMargin=0, bottomMargin=0)
        frame = Frame(0, 0, A4[0], A4[1], id='normal', leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        doc.addPageTemplates([PageTemplate(id='main', frames=[frame])])

        # 1. Build Header Flow
        header_flow = build_header_section(data, styles)

        # 2. Build Columns
        left_flow = build_left_content(data, styles)
        right_flow = build_right_sidebar(data, styles)

        # 3. Master Layout Table
        col_w_left = A4[0] * 0.65
        col_w_right = A4[0] * 0.35
        
        story = []
        
        # Add Header
        story.extend(header_flow)
        
        # Add Split Columns
        # We use a single row table for background colors.
        columns_table = Table(
            [[left_flow, right_flow]],
            colWidths=[col_w_left, col_w_right]
        )
        
        columns_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            
            # Left Style
            ('BACKGROUND', (0,0), (0,0), colors.white),
            ('LEFTPADDING', (0,0), (0,0), 12*mm),
            ('RIGHTPADDING', (0,0), (0,0), 8*mm),
            ('TOPPADDING', (0,0), (0,0), 10*mm),
            
            # Right Style
            ('BACKGROUND', (1,0), (1,0), COLOR_BG_SIDEBAR),
            ('LEFTPADDING', (1,0), (1,0), 8*mm),
            ('RIGHTPADDING', (1,0), (1,0), 8*mm),
            ('TOPPADDING', (1,0), (1,0), 10*mm),
            ('LINEBEFORE', (1,0), (1,0), 0.5, COLOR_BORDER), # Vertical separator
        ]))
        
        story.append(columns_table)
        
        doc.build(story)
        return output_path
    except Exception as e:
        print(f"Error generating CV: {e}")
        raise