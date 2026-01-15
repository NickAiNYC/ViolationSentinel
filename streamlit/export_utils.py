"""
Export utilities for ViolationSentinel V1 Dashboard
Handles PDF and Excel report generation
"""

import pandas as pd
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from typing import Optional


def generate_pdf_report(df: pd.DataFrame, user_name: str = "User") -> BytesIO:
    """
    Generate PDF portfolio risk report
    
    Args:
        df: DataFrame with portfolio data
        user_name: Name for report header
        
    Returns:
        BytesIO object containing PDF data
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                           rightMargin=inch/2, leftMargin=inch/2,
                           topMargin=inch, bottomMargin=inch/2)
    
    # Container for PDF elements
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1E3A8A'),
        spaceAfter=12,
        alignment=TA_CENTER
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#64748B'),
        spaceAfter=20,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#1E3A8A'),
        spaceAfter=10,
        spaceBefore=20
    )
    
    # Title
    elements.append(Paragraph("🏢 ViolationSentinel", title_style))
    elements.append(Paragraph("NYC Property Compliance Risk Report", subtitle_style))
    elements.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", subtitle_style))
    elements.append(Spacer(1, 0.3*inch))
    
    # Executive Summary
    elements.append(Paragraph("Executive Summary", heading_style))
    
    total_buildings = len(df)
    high_risk = len(df[df['risk_score'] >= 80])
    urgent = len(df[df['risk_score'] >= 50]) - high_risk
    normal = total_buildings - high_risk - urgent
    total_class_c = int(df['class_c_count'].sum())
    
    # Calculate total fine risk
    total_fines = sum([int(f.replace('$', '').replace(',', '')) for f in df['fine_risk']])
    
    summary_data = [
        ['Metric', 'Value'],
        ['Total Buildings', str(total_buildings)],
        ['🔴 Immediate Action Required', str(high_risk)],
        ['🟡 Urgent Attention Needed', str(urgent)],
        ['🟢 Normal Status', str(normal)],
        ['Total Class C Violations', str(total_class_c)],
        ['Total Estimated Fine Exposure', f'${total_fines:,}']
    ]
    
    summary_table = Table(summary_data, colWidths=[3.5*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A8A')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
    ]))
    
    elements.append(summary_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # High Risk Properties
    if high_risk > 0:
        elements.append(Paragraph("⚠️ Properties Requiring Immediate Attention", heading_style))
        
        critical_df = df[df['risk_score'] >= 80].nlargest(10, 'risk_score')
        
        critical_data = [['Property', 'Risk Score', 'Priority', 'Class C', 'Fine Risk']]
        for idx, row in critical_df.iterrows():
            critical_data.append([
                str(row['name'])[:30],
                str(row['risk_score']),
                str(row['priority']),
                str(int(row['class_c_count'])),
                str(row['fine_risk'])
            ])
        
        critical_table = Table(critical_data, colWidths=[2.5*inch, 1*inch, 1*inch, 0.8*inch, 1.2*inch])
        critical_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#DC2626')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#FEE2E2')),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
        ]))
        
        elements.append(critical_table)
        elements.append(Spacer(1, 0.2*inch))
    
    # Add page break before full portfolio
    elements.append(PageBreak())
    
    # Complete Portfolio Table
    elements.append(Paragraph("Complete Portfolio Overview", heading_style))
    
    portfolio_data = [['Property', 'Address', 'Risk', 'Priority', 'Status', 'Fine Risk']]
    for idx, row in df.iterrows():
        portfolio_data.append([
            str(row['name'])[:20],
            str(row['address'])[:30],
            str(row['risk_score']),
            str(row['priority']),
            str(row['status']).replace('🔴 ', '').replace('🟡 ', '').replace('🟢 ', ''),
            str(row['fine_risk'])
        ])
    
    portfolio_table = Table(portfolio_data, colWidths=[1.3*inch, 2*inch, 0.6*inch, 0.9*inch, 0.8*inch, 1*inch])
    portfolio_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A8A')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
    ]))
    
    elements.append(portfolio_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Footer
    elements.append(Spacer(1, 0.5*inch))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#64748B'),
        alignment=TA_CENTER
    )
    elements.append(Paragraph("ViolationSentinel • NYC Property Compliance Intelligence", footer_style))
    elements.append(Paragraph("Data sources: NYC Open Data (DOB, HPD, 311) • Updated daily", footer_style))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    
    return buffer


def generate_excel_report(df: pd.DataFrame, user_name: str = "User") -> BytesIO:
    """
    Generate Excel portfolio risk report with multiple sheets
    
    Args:
        df: DataFrame with portfolio data
        user_name: Name for report header
        
    Returns:
        BytesIO object containing Excel data
    """
    buffer = BytesIO()
    
    # Create Excel writer
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        # Summary sheet
        summary_data = {
            'Metric': [
                'Total Buildings',
                'Immediate Action Required',
                'Urgent Attention Needed',
                'Normal Status',
                'Total Class C Violations',
                'Total Heat Complaints (7d)',
                'Total Fine Exposure'
            ],
            'Value': [
                len(df),
                len(df[df['risk_score'] >= 80]),
                len(df[(df['risk_score'] >= 50) & (df['risk_score'] < 80)]),
                len(df[df['risk_score'] < 50]),
                int(df['class_c_count'].sum()),
                int(df['heat_complaints_7d'].sum()),
                f"${sum([int(f.replace('$', '').replace(',', '')) for f in df['fine_risk']]):,}"
            ]
        }
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        # High Risk properties sheet
        high_risk_df = df[df['risk_score'] >= 80].sort_values('risk_score', ascending=False)
        if len(high_risk_df) > 0:
            high_risk_df.to_excel(writer, sheet_name='High Risk Properties', index=False)
        
        # Complete portfolio sheet
        df.to_excel(writer, sheet_name='Complete Portfolio', index=False)
        
        # Detailed breakdown sheet
        breakdown_df = df[['name', 'address', 'risk_score', 'class_c_count', 
                          'heat_complaints_7d', 'open_violations_90d', 
                          'complaint_311_spike', 'fine_risk']]
        breakdown_df.to_excel(writer, sheet_name='Detailed Breakdown', index=False)
    
    buffer.seek(0)
    return buffer
