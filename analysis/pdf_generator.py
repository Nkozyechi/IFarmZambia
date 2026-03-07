"""
PDF Generator module for IFarm Zambia.
Converts decision reports into downloadable PDF documents.
"""

from datetime import datetime
from fpdf import FPDF

class ReportPDF(FPDF):
    def header(self):
        # Logo placeholder
        self.set_font('helvetica', 'B', 20)
        self.set_text_color(16, 185, 129) # rgb(16, 185, 129) - accent-green
        self.cell(0, 10, 'IFarm Zambia', ln=True)
        
        self.set_font('helvetica', 'I', 10)
        self.set_text_color(100, 116, 139) # rgb(100, 116, 139) - text-muted
        self.cell(0, 6, 'Farm Market Analysis & Price Prediction Report', ln=True)
        self.ln(5)
        
        # Line break
        self.set_draw_color(226, 232, 240) # rgb(226, 232, 240) - border
        self.set_line_width(0.5)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.set_text_color(148, 163, 184)
        page_str = f'Page {self.page_no()}/{{nb}}'
        self.cell(0, 10, f'Generated on {datetime.now().strftime("%Y-%m-%d %H:%M")} | {page_str}', 0, 0, 'C')

def generate_report_pdf(report_data):
    """Generate a PDF document from the report data dictionary."""
    pdf = ReportPDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    # Title Section
    pdf.set_font('helvetica', 'B', 16)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 10, f"Decision Report: {report_data['crop']['name']}", ln=True)
    
    pdf.set_font('helvetica', '', 11)
    pdf.set_text_color(71, 85, 105)
    harvest_str = ", ".join(report_data['scenario']['harvest_months'])
    pdf.cell(0, 6, f"Target Harvest Period: {harvest_str} {report_data['scenario']['target_year']}", ln=True)
    pdf.cell(0, 6, f"Planting Month: {report_data['scenario']['planting_month']}", ln=True)
    if 'province' in report_data['scenario']:
        pdf.cell(0, 6, f"Region / Province: {report_data['scenario']['province']}", ln=True)
    pdf.ln(5)
    
    # Recommendation Banner
    rec_val = report_data['recommendation']['verdict']
    if rec_val == 'Strongly Recommend' or rec_val == 'Recommend':
        fill_color = (209, 250, 229)
        text_color = (6, 95, 70)
    elif rec_val == 'Proceed with Caution' or rec_val == 'Consider Alternatives':
        fill_color = (254, 243, 199)
        text_color = (146, 64, 14)
    else:
        fill_color = (254, 226, 226)
        text_color = (153, 27, 27)
        
    pdf.set_fill_color(*fill_color)
    pdf.set_text_color(*text_color)
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 12, f"  Final Recommendation: {rec_val} (Score: {report_data['recommendation']['score']}/100)", 0, 1, 'L', fill=True)
    pdf.ln(5)
    
    # Price Prediction Section
    pdf.set_font('helvetica', 'B', 14)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 10, "Price Analysis & Prediction", ln=True)
    
    pdf.set_font('helvetica', '', 11)
    pdf.set_text_color(51, 65, 85)
    pdf.cell(0, 6, f"Expected Price: ZMW {report_data['price_analysis']['avg_expected_price']:.2f} per kg", ln=True)
    pdf.cell(0, 6, f"Per 50kg Bag: ZMW {report_data['price_analysis']['price_per_50kg_bag']:.2f}", ln=True)
    
    pdf.set_font('helvetica', 'I', 10)
    pdf.multi_cell(0, 6, f"Best selling month: {report_data['price_analysis']['best_selling_month']['month']}")
    pdf.ln(5)
    
    # Profitability Forecast
    if 'profitability' in report_data:
        prof = report_data['profitability']
        pdf.set_font('helvetica', 'B', 14)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(0, 10, "Profitability Forecast", ln=True)
        pdf.set_font('helvetica', '', 11)
        pdf.set_text_color(51, 65, 85)
        pdf.multi_cell(0, 6, f"Cost Basis: {prof.get('cost_source_label', 'Database average production costs per hectare')}")
        pdf.cell(0, 6, f"Farm Size: {prof['farm_size_ha']} hectares", ln=True)
        pdf.cell(0, 6, f"Seed Cost: ZMW {prof['breakdown']['seed']:.2f} /ha", ln=True)
        pdf.cell(0, 6, f"Fertilizer Cost: ZMW {prof['breakdown']['fertilizer']:.2f} /ha", ln=True)
        pdf.cell(0, 6, f"Chemicals Cost: ZMW {prof['breakdown']['chemicals']:.2f} /ha", ln=True)
        pdf.cell(0, 6, f"Labor Cost: ZMW {prof['breakdown']['labor']:.2f} /ha", ln=True)
        pdf.cell(0, 6, f"Other Costs: ZMW {prof['breakdown']['other']:.2f} /ha", ln=True)
        pdf.cell(0, 6, f"Gross Revenue: ZMW {prof['projected_revenue']:.2f}", ln=True)
        pdf.cell(0, 6, f"Total Costs: ZMW {prof['total_cost']:.2f}", ln=True)
        
        pdf.set_font('helvetica', 'B', 12)
        pdf.set_text_color(16, 185, 129) if prof['is_profitable'] else pdf.set_text_color(220, 38, 38)
        pdf.cell(0, 6, f"Net Profit: ZMW {prof['projected_profit']:.2f}", ln=True)
        pdf.cell(0, 6, f"Return on Investment (ROI): {prof['roi_pct']}%", ln=True)
        pdf.ln(5)

    # Risk Assessment Section
    pdf.set_font('helvetica', 'B', 14)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 10, "Risk Assessment", ln=True)
    
    individual_risks = report_data['risk_assessment'].get('individual_risks', [])
    if len(individual_risks) == 0:
        pdf.set_font('helvetica', '', 11)
        pdf.set_text_color(51, 65, 85)
        pdf.cell(0, 6, "No major risks identified for this planting window.", ln=True)
    else:
        for risk in individual_risks:
            if risk['severity'] == 'High':
                pdf.set_text_color(220, 38, 38)
            elif risk['severity'] == 'Medium':
                pdf.set_text_color(217, 119, 6)
            else:
                pdf.set_text_color(5, 150, 105)
                
            pdf.set_font('helvetica', 'B', 11)
            severity_text = f"[{risk['severity']}]"
            pdf.cell(25, 6, severity_text, ln=0)
            
            pdf.set_font('helvetica', 'B', 11)
            pdf.set_text_color(15, 23, 42)
            pdf.cell(0, 6, risk.get('type', ''), ln=1)
            
            pdf.set_x(10)
            pdf.set_font('helvetica', '', 10)
            pdf.set_text_color(71, 85, 105)
            pdf.multi_cell(0, 5, risk.get('description', ''))
            
            if risk.get('mitigation'):
                pdf.set_x(10)
                pdf.set_font('helvetica', 'I', 10)
                pdf.multi_cell(0, 5, f"Suggested Mitigation: {risk['mitigation']}")
            
            pdf.set_x(10)
            pdf.ln(2)
            
    # Normalize output for both pyfpdf (str) and fpdf2 (bytes-like).
    pdf_output = pdf.output(dest='S')
    return pdf_output.encode('latin-1') if isinstance(pdf_output, str) else bytes(pdf_output)
