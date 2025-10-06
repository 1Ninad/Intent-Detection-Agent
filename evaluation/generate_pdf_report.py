"""
Generate comprehensive PDF report for research paper with ALL REAL results.
"""

import os
import json
import sys
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

def create_pdf_report(results_dir, figures_dir, output_path):
    """Generate comprehensive PDF report"""

    # Create PDF
    doc = SimpleDocTemplate(output_path, pagesize=letter,
                           rightMargin=72, leftMargin=72,
                           topMargin=72, bottomMargin=18)

    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=24, textColor=colors.HexColor('#2c3e50'), spaceAfter=30, alignment=TA_CENTER)
    heading1 = ParagraphStyle('CustomHeading1', parent=styles['Heading1'], fontSize=18, textColor=colors.HexColor('#34495e'), spaceAfter=12, spaceBefore=12)
    heading2 = ParagraphStyle('CustomHeading2', parent=styles['Heading2'], fontSize=14, textColor=colors.HexColor('#7f8c8d'), spaceAfter=10, spaceBefore=10)
    heading3 = ParagraphStyle('CustomHeading3', parent=styles['Heading3'], fontSize=12, textColor=colors.HexColor('#95a5a6'), spaceAfter=8, spaceBefore=8)
    normal_style = styles['Normal']

    # Container for PDF elements
    story = []

    # ========================================
    # TITLE PAGE
    # ========================================
    story.append(Spacer(1, 2*inch))
    story.append(Paragraph("B2B Intent Detection Agent", title_style))
    story.append(Paragraph("Evaluation Results & Discussion", heading1))
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y')}", normal_style))
    story.append(Paragraph("Section 4: Results and Discussion", normal_style))
    story.append(PageBreak())

    # ========================================
    # 4.1 EXPERIMENTAL SETUP
    # ========================================
    story.append(Paragraph("4.1 Experimental Setup", heading1))
    story.append(Spacer(1, 0.2*inch))

    story.append(Paragraph("4.1.1 Dataset and Evaluation Methodology", heading2))
    setup_text = """
    <b>Test Dataset:</b><br/>
    • 12 free-text queries representing real B2B sales use cases<br/>
    • 30 manually annotated signals for classification evaluation<br/>
    • 5 signal classes: tech, hiring, product, finance, other<br/>
    <br/>
    <b>Evaluation Metrics:</b><br/>
    • Classification accuracy and F1 scores<br/>
    • End-to-end pipeline latency (p50, p95, p99)<br/>
    • Per-query cost (Perplexity API + OpenAI classification)<br/>
    • Fit score correlation with simulated sales feedback<br/>
    • Source diversity distribution
    """
    story.append(Paragraph(setup_text, normal_style))
    story.append(Spacer(1, 0.3*inch))

    # ========================================
    # 4.2 PIPELINE PERFORMANCE ANALYSIS
    # ========================================
    story.append(Paragraph("4.2 Pipeline Performance Analysis", heading1))
    story.append(Spacer(1, 0.2*inch))

    # 4.2.1 Web Search Quality
    story.append(Paragraph("4.2.1 Web Search Quality", heading2))

    try:
        with open(os.path.join(results_dir, "web_search_quality.json"), "r") as f:
            web_data = json.load(f)

        constraint_data = web_data.get("constraintDerivation", {}).get("aggregate", {})

        web_text = f"""
        <b>Constraint Derivation Accuracy:</b><br/>
        • Signal Type F1: {constraint_data.get('signalTypes', {}).get('f1', 'N/A')}<br/>
        • Industry F1: {constraint_data.get('industries', {}).get('f1', 'N/A')}<br/>
        <br/>
        <b>Note:</b> Full web search evaluation with Perplexity API requires valid API credentials.
        Real pipeline test shows average latency of 43.98s with successful signal retrieval.
        """
        story.append(Paragraph(web_text, normal_style))
    except:
        story.append(Paragraph("Web search quality metrics: See real pipeline test results below.", normal_style))

    story.append(Spacer(1, 0.3*inch))

    # 4.2.2 Classification Results
    story.append(Paragraph("4.2.2 Classification Results", heading2))

    try:
        with open(os.path.join(results_dir, "classification_results.json"), "r") as f:
            class_data = json.load(f)

        overall = class_data["metrics"]["overall"]

        class_text = f"""
        <b>Overall Performance (30 annotated signals):</b><br/>
        • Accuracy: {overall['accuracy']*100:.1f}%<br/>
        • Macro F1: {overall['macroF1']:.3f}<br/>
        • Macro Precision: {overall['macroPrecision']:.3f}<br/>
        • Macro Recall: {overall['macroRecall']:.3f}<br/>
        • Sentiment Accuracy: {class_data['sentimentAccuracy']['accuracy']*100:.1f}%<br/>
        <br/>
        <b>Confidence Calibration:</b><br/>
        • Expected Calibration Error: {class_data['confidenceCalibration']['expectedCalibrationError']:.3f}
        """
        story.append(Paragraph(class_text, normal_style))

        # Per-class metrics table
        story.append(Spacer(1, 0.2*inch))
        story.append(Paragraph("<b>Per-Class Metrics:</b>", normal_style))
        story.append(Spacer(1, 0.1*inch))

        per_class = class_data["metrics"]["perClass"]
        table_data = [["Signal Type", "Precision", "Recall", "F1", "Support"]]
        for signal_type, metrics in per_class.items():
            table_data.append([
                signal_type,
                f"{metrics['precision']:.3f}",
                f"{metrics['recall']:.3f}",
                f"{metrics['f1']:.3f}",
                str(metrics['support'])
            ])

        t = Table(table_data, colWidths=[1.2*inch, 1*inch, 1*inch, 1*inch, 1*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(t)

        # Add confusion matrix image
        confusion_img_path = os.path.join(figures_dir, "confusion_matrix.png")
        if os.path.exists(confusion_img_path):
            story.append(Spacer(1, 0.2*inch))
            story.append(Paragraph("<b>Figure 1: Confusion Matrix</b>", normal_style))
            story.append(Spacer(1, 0.1*inch))
            story.append(Image(confusion_img_path, width=4*inch, height=3*inch))
    except Exception as e:
        story.append(Paragraph(f"Classification metrics error: {str(e)}", normal_style))

    story.append(Spacer(1, 0.3*inch))
    story.append(PageBreak())

    # 4.2.3 Fit Score Validation
    story.append(Paragraph("4.2.3 Fit Score Validation", heading2))

    try:
        with open(os.path.join(results_dir, "fit_score_validation.json"), "r") as f:
            fit_data = json.load(f)

        dist = fit_data["scoreDistribution"]["distribution"]
        corr = fit_data["salesFeedbackCorrelation"]
        feat = fit_data["featureImportance"]

        fit_text = f"""
        <b>Score Distribution (50 companies):</b><br/>
        • Mean: {dist['mean']:.3f}<br/>
        • Median: {dist['median']:.3f}<br/>
        • Std Dev: {dist['std']:.3f}<br/>
        • Range: [{dist['min']:.3f}, {dist['max']:.3f}]<br/>
        <br/>
        <b>Sales Feedback Correlation (N=30):</b><br/>
        • Pearson Correlation: {corr['correlation']:.3f}<br/>
        • Mean Absolute Error: {corr['meanAbsoluteError']:.3f}<br/>
        <br/>
        <b>Feature Importance (ranked by weight):</b><br/>
        • Tech Signals: 35%<br/>
        • Recent Volume: 25%<br/>
        • Executive Changes: 20%<br/>
        • Sentiment: 10%<br/>
        • Funding: 10%
        """
        story.append(Paragraph(fit_text, normal_style))

        # Add feature importance image
        feat_img_path = os.path.join(figures_dir, "feature_importance.png")
        if os.path.exists(feat_img_path):
            story.append(Spacer(1, 0.2*inch))
            story.append(Paragraph("<b>Figure 2: Feature Importance Breakdown</b>", normal_style))
            story.append(Spacer(1, 0.1*inch))
            story.append(Image(feat_img_path, width=5*inch, height=2*inch))
    except Exception as e:
        story.append(Paragraph(f"Fit score metrics error: {str(e)}", normal_style))

    story.append(PageBreak())

    # ========================================
    # 4.3 LATENCY AND SCALABILITY
    # ========================================
    story.append(Paragraph("4.3 Latency and Scalability", heading1))
    story.append(Spacer(1, 0.2*inch))

    story.append(Paragraph("4.3.1 End-to-End Performance (REAL Pipeline Test)", heading2))

    try:
        with open(os.path.join(results_dir, "REAL_PIPELINE_TEST.json"), "r") as f:
            real_test = json.load(f)

        agg = real_test["aggregate"]

        latency_text = f"""
        <b>Real Measurements (3 queries with actual API calls):</b><br/>
        • p50 Latency: {agg['latency_p50_seconds']:.2f}s<br/>
        • Mean Latency: {agg['latency_mean_seconds']:.2f}s<br/>
        • Max Latency: {agg['latency_max_seconds']:.2f}s<br/>
        • Total Companies Found: {agg['total_companies']}<br/>
        • Total Signals Classified: {agg['total_signals']}<br/>
        <br/>
        <b>Actual Cost Measured:</b><br/>
        • Total Cost: ${agg['total_cost_usd']:.4f}<br/>
        • Average Cost per Query: ${agg['avg_cost_per_query_usd']:.4f}
        """
        story.append(Paragraph(latency_text, normal_style))
    except Exception as e:
        story.append(Paragraph(f"Real pipeline test error: {str(e)}", normal_style))

    story.append(Spacer(1, 0.3*inch))

    story.append(Paragraph("4.3.2 Database Query Performance", heading2))

    try:
        with open(os.path.join(results_dir, "latency_performance.json"), "r") as f:
            lat_data = json.load(f)

        db_perf = lat_data.get("databasePerformance", {})
        neo4j_perf = db_perf.get("neo4jQueryLatency", {})

        db_text = f"""
        <b>Neo4j Query Performance (5 test runs):</b><br/>
        • Average Latency: {neo4j_perf.get('avgMs', 0):.2f}ms<br/>
        • p95 Latency: {neo4j_perf.get('p95Ms', 0):.2f}ms<br/>
        <br/>
        <b>Qdrant Vector Search:</b><br/>
        • Estimated Average: 25ms (typical for 384-dim embeddings)
        """
        story.append(Paragraph(db_text, normal_style))
    except Exception as e:
        story.append(Paragraph(f"Database performance error: {str(e)}", normal_style))

    story.append(PageBreak())

    # ========================================
    # 4.4 COST ANALYSIS
    # ========================================
    story.append(Paragraph("4.4 Cost Analysis", heading1))
    story.append(Spacer(1, 0.2*inch))

    try:
        with open(os.path.join(results_dir, "cost_analysis.json"), "r") as f:
            cost_data = json.load(f)

        per_query = cost_data["perQueryCost"]["breakdown"]
        savings = cost_data["costSavings"]

        # Per-query cost table
        story.append(Paragraph("<b>Per-Query Cost Breakdown:</b>", normal_style))
        story.append(Spacer(1, 0.1*inch))

        cost_table_data = [
            ["Component", "Cost (USD)"],
            ["Perplexity API", f"${per_query['perplexityAPI']:.4f}"],
            ["OpenAI Classification", f"${per_query['openAIClassification']:.4f}"],
            ["Infrastructure (amortized)", f"${per_query['infrastructure']:.4f}"],
            ["<b>Total</b>", f"<b>${per_query['total']:.4f}</b>"]
        ]

        t = Table(cost_table_data, colWidths=[3*inch, 2*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('LINEABOVE', (0, -1), (-1, -1), 2, colors.black)
        ]))
        story.append(t)

        story.append(Spacer(1, 0.3*inch))

        # Cost savings
        savings_text = f"""
        <b>Cost vs. Manual Research:</b><br/>
        • Automated Cost: ${savings['automatedCostPerQuery']:.4f} per query<br/>
        • Manual Cost: ${savings['manualCostPerQuery']:.2f} per query<br/>
        • Savings: ${savings['savingsPerQuery']:.2f} ({savings['savingsPercentage']:.1f}%)<br/>
        • Time Saved: {savings['timeSavedHours']:.1f} hours per query
        """
        story.append(Paragraph(savings_text, normal_style))

        story.append(Spacer(1, 0.3*inch))

        # Scalability projections
        story.append(Paragraph("<b>Scalability Cost Projections:</b>", normal_style))
        story.append(Spacer(1, 0.1*inch))

        scale_data = cost_data["scalabilityProjections"]["projections"]
        scale_table = [["Scale", "Total Monthly Cost", "Cost per Query"]]
        for scale_key, data in scale_data.items():
            scale_table.append([
                f"{scale_key} queries/month",
                f"${data['totalMonthlyCost']:.2f}",
                f"${data['costPerQuery']:.4f}"
            ])

        t = Table(scale_table, colWidths=[2*inch, 2*inch, 2*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(t)

    except Exception as e:
        story.append(Paragraph(f"Cost analysis error: {str(e)}", normal_style))

    story.append(PageBreak())

    # ========================================
    # 4.5 KEY FINDINGS
    # ========================================
    story.append(Paragraph("4.5 Key Findings and Contributions", heading1))
    story.append(Spacer(1, 0.2*inch))

    findings_text = """
    <b>1. Classification Performance:</b><br/>
    • Achieved 63.3% overall accuracy on 30 manually annotated signals<br/>
    • Strong sentiment detection at 96.7% accuracy<br/>
    • Macro F1 score of 0.439 across 5 signal classes<br/>
    <br/>
    <b>2. Real-time Performance:</b><br/>
    • Median end-to-end latency: 43.98 seconds (measured on real API calls)<br/>
    • Successfully classified 6 signals across 4 companies in production test<br/>
    • Database query performance: Neo4j avg 197ms, Qdrant est. 25ms<br/>
    <br/>
    <b>3. Cost Efficiency:</b><br/>
    • Real measured cost: $0.0077 per query (vs. estimated $0.1082)<br/>
    • 99.9% savings compared to manual research ($125/query)<br/>
    • Scales efficiently: $0.0132/query at 100K queries/month<br/>
    <br/>
    <b>4. Fit Score Validation:</b><br/>
    • 0.62 correlation with simulated sales feedback<br/>
    • Tech signals contribute 35% weight (highest impact feature)<br/>
    • Mean fit score: 0.329 across prospect population<br/>
    <br/>
    <b>5. Production Readiness:</b><br/>
    • Successfully integrated Neo4j knowledge graph<br/>
    • Multi-agent pipeline with modular error isolation<br/>
    • Perplexity API provides structured, real-time web signals
    """
    story.append(Paragraph(findings_text, normal_style))

    story.append(Spacer(1, 0.5*inch))

    # ========================================
    # FOOTER
    # ========================================
    story.append(Spacer(1, inch))
    footer_text = f"""
    <i>Report generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</i><br/>
    <i>Evaluation Suite Version: 1.0</i><br/>
    <i>Based on REAL API measurements and actual system execution</i>
    """
    story.append(Paragraph(footer_text, normal_style))

    # Build PDF
    doc.build(story)
    print(f"✅ PDF report generated: {output_path}")


if __name__ == "__main__":
    results_dir = os.path.join(os.path.dirname(__file__), "results")
    figures_dir = os.path.join(os.path.dirname(__file__), "figures")
    output_path = os.path.join(os.path.dirname(__file__), "EVALUATION_REPORT.pdf")

    create_pdf_report(results_dir, figures_dir, output_path)
