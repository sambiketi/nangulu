"""
PDF report generation utility.
Contract: Simplicity, use existing constraints, no complex formatting.
"""
import io
from datetime import datetime, date
from decimal import Decimal
from typing import List, Dict, Any, Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.legends import Legend

class PDFReportGenerator:
    """Generate PDF reports following contract simplicity."""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles."""
        # Title style
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            alignment=TA_CENTER,
            spaceAfter=30,
            textColor=colors.HexColor('#2c3e50')
        ))
        
        # Subtitle style
        self.styles.add(ParagraphStyle(
            name='ReportSubtitle',
            parent=self.styles['Heading2'],
            fontSize=14,
            alignment=TA_CENTER,
            spaceAfter=20,
            textColor=colors.HexColor('#7f8c8d')
        ))
        
        # Section header
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=16,
            spaceBefore=20,
            spaceAfter=10,
            textColor=colors.HexColor('#2980b9')
        ))
        
        # Normal text
        self.styles.add(ParagraphStyle(
            name='NormalText',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6
        ))
        
        # Table header
        self.styles.add(ParagraphStyle(
            name='TableHeader',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.white,
            alignment=TA_CENTER
        ))
        
        # Footer style
        self.styles.add(ParagraphStyle(
            name='Footer',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.gray,
            alignment=TA_CENTER
        ))
    
    def generate_stock_report(self, stock_data: List[Dict], report_title: str = "Stock Report") -> bytes:
        """
        Generate stock level PDF report.
        
        Args:
            stock_data: List of stock items with details
            report_title: Title of the report
            
        Returns:
            PDF bytes
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        story = []
        
        # Title
        story.append(Paragraph(report_title, self.styles['ReportTitle']))
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 
                              self.styles['ReportSubtitle']))
        story.append(Spacer(1, 20))
        
        # Summary section
        total_items = len(stock_data)
        critical_items = sum(1 for item in stock_data if item.get('stock_status') == 'CRITICAL')
        low_items = sum(1 for item in stock_data if item.get('stock_status') == 'LOW')
        total_value = sum(Decimal(str(item.get('stock_value', 0))) for item in stock_data)
        
        summary_text = f"""
        <b>Summary:</b><br/>
        Total Items: {total_items}<br/>
        Critical Stock: {critical_items} items<br/>
        Low Stock: {low_items} items<br/>
        Total Stock Value: ${total_value:,.2f}<br/>
        """
        story.append(Paragraph(summary_text, self.styles['NormalText']))
        story.append(Spacer(1, 20))
        
        # Stock table
        story.append(Paragraph("Current Stock Levels", self.styles['SectionHeader']))
        
        # Prepare table data
        table_data = [['Item', 'Current Stock (kg)', 'Price/kg', 'Stock Value', 'Status']]
        
        for item in stock_data:
            status = item.get('stock_status', 'NORMAL')
            status_color = {
                'CRITICAL': '🔴',
                'LOW': '🟡',
                'NORMAL': '🟢'
            }.get(status, '⚪')
            
            table_data.append([
                item.get('name', ''),
                f"{item.get('current_stock', 0):.3f}",
                f"${item.get('current_price_per_kg', 0):.2f}",
                f"${item.get('stock_value', 0):,.2f}",
                f"{status_color} {status}"
            ])
        
        # Create table
        table = Table(table_data, colWidths=[3*inch, 1.5*inch, 1*inch, 1.2*inch, 1.2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (1, 1), (3, -1), 'RIGHT'),
            ('ALIGN', (4, 1), (4, -1), 'CENTER'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ]))
        
        story.append(table)
        story.append(Spacer(1, 30))
        
        # Footer
        footer_text = f"""
        Nangulu Chicken Feed POS System - Stock Report<br/>
        Generated by Admin User | Page <page/>
        """
        story.append(Paragraph(footer_text, self.styles['Footer']))
        
        # Build PDF
        doc.build(story)
        
        buffer.seek(0)
        return buffer.getvalue()
    
    def generate_sales_report(self, sales_data: List[Dict], date_range: str = "Daily") -> bytes:
        """
        Generate sales PDF report.
        
        Args:
            sales_data: List of sales records
            date_range: Date range description
            
        Returns:
            PDF bytes
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        story = []
        
        # Title
        story.append(Paragraph(f"{date_range} Sales Report", self.styles['ReportTitle']))
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 
                              self.styles['ReportSubtitle']))
        story.append(Spacer(1, 20))
        
        # Calculate totals
        total_sales = len(sales_data)
        total_kg = sum(Decimal(str(sale.get('kg_sold', 0))) for sale in sales_data)
        total_revenue = sum(Decimal(str(sale.get('total_price', 0))) for sale in sales_data)
        avg_sale_value = total_revenue / total_sales if total_sales > 0 else Decimal('0')
        
        summary_text = f"""
        <b>Summary:</b><br/>
        Total Sales: {total_sales}<br/>
        Total KG Sold: {total_kg:.3f} kg<br/>
        Total Revenue: ${total_revenue:,.2f}<br/>
        Average Sale Value: ${avg_sale_value:,.2f}<br/>
        """
        story.append(Paragraph(summary_text, self.styles['NormalText']))
        story.append(Spacer(1, 20))
        
        # Sales table
        story.append(Paragraph("Sales Details", self.styles['SectionHeader']))
        
        # Prepare table data
        table_data = [['Sale #', 'Date', 'Item', 'KG', 'Price', 'Total', 'Cashier']]
        
        for sale in sales_data:
            table_data.append([
                sale.get('sale_number', ''),
                sale.get('created_at', '')[:10] if sale.get('created_at') else '',
                sale.get('item_name', ''),
                f"{sale.get('kg_sold', 0):.3f}",
                f"${sale.get('price_per_kg_snapshot', 0):.2f}",
                f"${sale.get('total_price', 0):.2f}",
                sale.get('cashier_name', '')
            ])
        
        # Create table
        table = Table(table_data, colWidths=[1.2*inch, 1*inch, 1.8*inch, 0.8*inch, 
                                            0.8*inch, 0.9*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#27ae60')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (3, 1), (5, -1), 'RIGHT'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ]))
        
        story.append(table)
        story.append(Spacer(1, 30))
        
        # Summary by item
        story.append(Paragraph("Summary by Item", self.styles['SectionHeader']))
        
        # Group by item
        item_summary = {}
        for sale in sales_data:
            item_name = sale.get('item_name', 'Unknown')
            if item_name not in item_summary:
                item_summary[item_name] = {
                    'count': 0,
                    'total_kg': Decimal('0'),
                    'total_revenue': Decimal('0')
                }
            
            item_summary[item_name]['count'] += 1
            item_summary[item_name]['total_kg'] += Decimal(str(sale.get('kg_sold', 0)))
            item_summary[item_name]['total_revenue'] += Decimal(str(sale.get('total_price', 0)))
        
        # Create item summary table
        summary_table_data = [['Item', 'Sales Count', 'Total KG', 'Total Revenue']]
        
        for item_name, stats in item_summary.items():
            summary_table_data.append([
                item_name,
                str(stats['count']),
                f"{stats['total_kg']:.3f}",
                f"${stats['total_revenue']:,.2f}"
            ])
        
        summary_table = Table(summary_table_data, colWidths=[2.5*inch, 1*inch, 1*inch, 1.2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ]))
        
        story.append(summary_table)
        story.append(Spacer(1, 30))
        
        # Footer
        footer_text = f"""
        Nangulu Chicken Feed POS System - Sales Report<br/>
        {date_range} Report | Page <page/>
        """
        story.append(Paragraph(footer_text, self.styles['Footer']))
        
        # Build PDF
        doc.build(story)
        
        buffer.seek(0)
        return buffer.getvalue()
    
    def generate_receipt(self, sale_data: Dict) -> bytes:
        """
        Generate customer receipt PDF.
        
        Args:
            sale_data: Sale information
            
        Returns:
            PDF bytes
        """
        buffer = io.BytesIO()
        
        # Smaller page size for receipt
        doc = SimpleDocTemplate(
            buffer,
            pagesize=(3.5*inch, 8*inch),  # Receipt size
            rightMargin=10,
            leftMargin=10,
            topMargin=10,
            bottomMargin=10
        )
        
        story = []
        
        # Header
        story.append(Paragraph("NANGULU CHICKEN FEED", 
                              ParagraphStyle(name='ReceiptHeader', 
                                           fontSize=16, 
                                           alignment=TA_CENTER,
                                           textColor=colors.HexColor('#2c3e50'),
                                           spaceAfter=10)))
        
        story.append(Paragraph("POS Receipt", 
                              ParagraphStyle(name='ReceiptSub', 
                                           fontSize=12, 
                                           alignment=TA_CENTER,
                                           textColor=colors.grey,
                                           spaceAfter=20)))
        
        # Sale info
        info_style = ParagraphStyle(name='ReceiptInfo', fontSize=10)
        
        info_text = f"""
        <b>Receipt #:</b> {sale_data.get('sale_number', '')}<br/>
        <b>Date:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}<br/>
        <b>Cashier:</b> {sale_data.get('cashier_name', '')}<br/>
        """
        
        if sale_data.get('customer_name'):
            info_text += f"<b>Customer:</b> {sale_data.get('customer_name')}<br/>"
        
        story.append(Paragraph(info_text, info_style))
        story.append(Spacer(1, 15))
        
        # Line items
        story.append(Paragraph("=" * 40, 
                              ParagraphStyle(name='Line', fontSize=8)))
        
        # Item details
        item_style = ParagraphStyle(name='ItemStyle', fontSize=10)
        
        item_text = f"""
        <b>{sale_data.get('item_name', '')}</b><br/>
        Quantity: {sale_data.get('kg_sold', 0):.3f} kg<br/>
        Price per kg: ${sale_data.get('price_per_kg_snapshot', 0):.2f}<br/>
        """
        
        story.append(Paragraph(item_text, item_style))
        story.append(Spacer(1, 10))
        
        # Total
        story.append(Paragraph("=" * 40, 
                              ParagraphStyle(name='Line', fontSize=8)))
        
        total_style = ParagraphStyle(name='TotalStyle', fontSize=12, alignment=TA_RIGHT)
        total_text = f"TOTAL: <b>${sale_data.get('total_price', 0):.2f}</b>"
        story.append(Paragraph(total_text, total_style))
        
        story.append(Spacer(1, 20))
        
        # Footer note
        footer_style = ParagraphStyle(name='FooterNote', fontSize=8, alignment=TA_CENTER)
        footer_text = """
        Thank you for your business!<br/>
        Returns require original receipt<br/>
        Contact: +255 XXX XXX XXX<br/>
        """
        story.append(Paragraph(footer_text, footer_style))
        
        # Build PDF
        doc.build(story)
        
        buffer.seek(0)
        return buffer.getvalue()

# Create global instance
pdf_generator = PDFReportGenerator()
