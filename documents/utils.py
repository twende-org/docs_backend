import os
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.units import inch

def generate_unified_pdf(document):
    """
    Generate a high-quality PDF for any document type stored in the Document model.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
    styles = getSampleStyleSheet()
    
    # Custom Styles
    styles.add(ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=26,
        textColor=colors.HexColor("#B91C1C"),
        spaceAfter=20,
        alignment=1,
        fontName='Helvetica-Bold'
    ))
    
    styles.add(ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor("#1F2937"),
        spaceBefore=15,
        spaceAfter=10,
        fontName='Helvetica-Bold',
        borderPadding=(0, 0, 2, 0),
        borderWidth=0,
        borderColor=colors.HexColor("#B91C1C"),
    ))

    styles.add(ParagraphStyle(
        'EntryTitle',
        parent=styles['Normal'],
        fontSize=12,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor("#1F2937"),
    ))

    styles.add(ParagraphStyle(
        'EntrySub',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.grey,
        fontName='Helvetica-Oblique',
    ))

    elements = []
    content = document.content

    # 1. Header Logic
    if document.doc_type == 'CV':
        elements.append(Paragraph(content.get('fullName', 'RESUME').upper(), styles['DocTitle']))
        contact = f"{content.get('email', '')} | {content.get('phone', '')} | {content.get('address', '')}"
        elements.append(Paragraph(contact, ParagraphStyle('Contact', parent=styles['Normal'], alignment=1, fontSize=9, textColor=colors.grey)))
        elements.append(Spacer(1, 0.3*inch))
    else:
        elements.append(Paragraph(document.get_doc_type_display().upper(), styles['DocTitle']))
        elements.append(Spacer(1, 0.2*inch))

    # 2. Dynamic Content Rendering based on Type
    if document.doc_type == 'CV':
        # Summary
        if content.get('summary'):
            elements.append(Paragraph("PROFESSIONAL SUMMARY", styles['SectionHeader']))
            elements.append(Paragraph(content['summary'], styles['Normal']))
        
        # Experience
        exp = content.get('experience', [])
        if exp:
            elements.append(Paragraph("WORK EXPERIENCE", styles['SectionHeader']))
            for e in exp:
                elements.append(Paragraph(f"<b>{e.get('jobTitle', '')}</b> | {e.get('company', '')}", styles['EntryTitle']))
                elements.append(Paragraph(f"{e.get('startDate', '')} - {e.get('endDate', 'Present')}", styles['EntrySub']))
                elements.append(Paragraph(e.get('description', ''), styles['Normal']))
                elements.append(Spacer(1, 0.1*inch))

        # Education
        edu = content.get('education', [])
        if edu:
            elements.append(Paragraph("EDUCATION", styles['SectionHeader']))
            for ed in edu:
                elements.append(Paragraph(f"<b>{ed.get('degree', '')}</b>", styles['EntryTitle']))
                elements.append(Paragraph(f"{ed.get('institution', '')} | {ed.get('year', '')}", styles['EntrySub']))
                elements.append(Spacer(1, 0.1*inch))

    elif document.doc_type == 'LETTER' or document.doc_type == 'OFFICIAL_LETTER':
        # Block Format
        elements.append(Paragraph(f"<b>Date:</b> {document.created_at.strftime('%B %d, %Y')}", styles['Normal']))
        elements.append(Spacer(1, 0.2*inch))
        
        elements.append(Paragraph("<b>RE:</b> " + (document.title or 'Subject'), styles['EntryTitle']))
        elements.append(Spacer(1, 0.3*inch))
        
        body = content.get('body', content.get('content', ''))
        elements.append(Paragraph(body.replace('\n', '<br/>'), styles['Normal']))
        
        elements.append(Spacer(1, 0.5*inch))
        elements.append(Paragraph("Sincerely,", styles['Normal']))
        elements.append(Spacer(1, 0.2*inch))
        elements.append(Paragraph("<b>" + content.get('senderName', 'Authorized Signatory') + "</b>", styles['Normal']))

    elif document.doc_type in ['INVOICE', 'QUOTATION', 'PROFORMA']:
        # Billing details
        billing_info = [
            [Paragraph(f"<b>CLIENT:</b> {content.get('clientName', 'N/A')}", styles['Normal']),
             Paragraph(f"<b>INVOICE #:</b> {document.id}", styles['Normal'])]
        ]
        bt = Table(billing_info, colWidths=[4*inch, 2*inch])
        elements.append(bt)
        elements.append(Spacer(1, 0.3*inch))

        items = content.get('items', [])
        if items:
            table_data = [["Description", "Qty", "Price", "Total"]]
            total_sum = 0
            for item in items:
                qty = float(item.get('quantity', 0))
                price = float(item.get('unitPrice', 0))
                subtotal = qty * price
                total_sum += subtotal
                table_data.append([item.get('description', ''), str(qty), f"{price:,.2f}", f"{subtotal:,.2f}"])
            
            table_data.append(["", "", "<b>TOTAL</b>", f"<b>{total_sum:,.2f}</b>"])
            t = Table(table_data, colWidths=[3.2*inch, 0.6*inch, 1.1*inch, 1.1*inch])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1F2937")),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('ALIGN', (0,0), (0,-1), 'LEFT'),
                ('GRID', (0,0), (-1,-2), 0.5, colors.grey),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0,0), (-1,0), 12),
                ('TOPPADDING', (0,0), (-1,0), 12),
            ]))
            elements.append(t)

    else:
        # Catch-all narrative
        body = content.get('content', content.get('body', ''))
        if not body:
            body = "\n\n".join([f"<b>{k.replace('_',' ').upper()}:</b> {v}" for k, v in content.items() if isinstance(v, str)])
        elements.append(Paragraph(body.replace('\n', '<br/>'), styles['Normal']))

    # 4. Global Footer
    elements.append(Spacer(1, 1*inch))
    footer_style = ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.grey, alignment=1)
    elements.append(Paragraph("__________________________________________________________________", footer_style))
    elements.append(Paragraph("Generated by GENDOCS - High Fidelity Document Systems<br/>Precision Engineering for Professional Documentation", footer_style))

    doc.build(elements)
    buffer.seek(0)
    return buffer
