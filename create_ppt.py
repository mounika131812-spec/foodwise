import sys
import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

def create_presentation():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_slide_layout = prs.slide_layouts[6]

    BG_DARK = RGBColor(15, 23, 42)
    TEXT_LIGHT = RGBColor(248, 250, 252)
    TEXT_MUTED = RGBColor(148, 163, 184)
    ACCENT_GREEN = RGBColor(16, 185, 129)
    ACCENT_BLUE = RGBColor(59, 130, 246)
    CARD_BG = RGBColor(30, 41, 59)
    CARD_BORDER = RGBColor(51, 65, 85)

    def add_background(slide, color):
        shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
        shape.fill.solid()
        shape.fill.fore_color.rgb = color
        shape.line.fill.background()

    def add_header(slide, title_text, subtitle_text):
        tb = slide.shapes.add_textbox(Inches(0.8), Inches(0.6), Inches(11.7), Inches(1.2))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    # ==================== SLIDE 1 ====================
    slide1 = prs.slides.add_slide(blank_slide_layout)
    add_background(slide1, BG_DARK)
    bar = slide1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(1.2), Inches(2.2), Inches(1.5), Inches(0.1))
    bar.fill.solid()
    bar.fill.fore_color.rgb = ACCENT_GREEN
    bar.line.fill.background()

    tb = slide1.shapes.add_textbox(Inches(1.2), Inches(2.6), Inches(10.5), Inches(3.5))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Smart Food Waste\\nManagement Platform"
    p.font.size = Pt(44)
    p.font.bold = True
    p.font.color.rgb = TEXT_LIGHT
    p.font.name = "Arial"

    p2 = tf.add_paragraph()
    p2.text = "A Full-Stack Web Application for Inventory Tracking, Waste Analytics, & AI Recipes"
    p2.font.size = Pt(18)
    p2.font.color.rgb = ACCENT_GREEN
    p2.font.name = "Arial"
    p2.space_before = Pt(16)

    p3 = tf.add_paragraph()
    p3.text = "College Internship Project  |  Python Flask, SQLite, Vanilla JS & Gemini AI"
    p3.font.size = Pt(13)
    p3.font.color.rgb = TEXT_MUTED
    p3.font.name = "Arial"
    p3.space_before = Pt(24)

    # ==================== SLIDE 2 ====================
    slide2 = prs.slides.add_slide(blank_slide_layout)
    add_background(slide2, BG_DARK)
    add_header(slide2, "Problem Statement & Solution", "Why food waste management matters and how our platform addresses it")

    c1 = slide2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(2.0), Inches(5.6), Inches(4.5))
    c1.fill.solid()
    c1.fill.fore_color.rgb = CARD_BG
    c1.line.color.rgb = CARD_BORDER
    tf1 = c1.text_frame
    tf1.word_wrap = True
    tf1.margin_left = tf1.margin_right = tf1.margin_top = tf1.margin_bottom = Inches(0.4)
    p = tf1.paragraphs[0]
    p.text = "The Problem"
    p.font.size = Pt(20)
    p.font.bold = True
    p.font.color.rgb = RGBColor(239, 68, 68)

    for b in ["Massive global food waste in households and restaurants.",
              "Lack of visibility into pantry inventory and exact expiry dates.",
              "Unplanned grocery purchases leading to spoiled perishables.",
              "Difficulty tracking waste patterns and financial loss over time."]:
        p = tf1.add_paragraph()
        p.text = "• " + b
        p.font.size = Pt(14)
        p.font.color.rgb = TEXT_LIGHT
        p.space_before = Pt(8)

    c2 = slide2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.9), Inches(2.0), Inches(5.6), Inches(4.5))
    c2.fill.solid()
    c2.fill.fore_color.rgb = CARD_BG
    c2.line.color.rgb = CARD_BORDER
    tf2 = c2.text_frame
    tf2.word_wrap = True
    tf2.margin_left = tf2.margin_right = tf2.margin_top = tf2.margin_bottom = Inches(0.4)
    p = tf2.paragraphs[0]
    p.text = "The Solution"
    p.font.size = Pt(20)
    p.font.bold = True
    p.font.color.rgb = ACCENT_GREEN

    for b in ["Smart pantry inventory tracking with auto-computed status badges.",
              "Automated waste logging tied directly to pantry items.",
              "AI-powered recipe generator utilizing soon-to-expire ingredients.",
              "Bento analytics dashboard with SVG charts for deep waste insights."]:
        p = tf2.add_paragraph()
        p.text = "• " + b
        p.font.size = Pt(14)
        p.font.color.rgb = TEXT_LIGHT
    # ==================== SLIDE 3 ====================
    slide3 = prs.slides.add_slide(blank_slide_layout)
    add_background(slide3, BG_DARK)
    add_header(slide3, "Core Application Features", "Comprehensive toolset for efficient kitchen and restaurant inventory management")

    features = [
        ("Authentication & Roles", "Secure JWT authentication with bcrypt-hashed passwords. Supports Household, Restaurant, and Admin roles."),
        ("Smart Pantry Inventory", "Track food items by category, quantity, unit, purchase/expiry dates, location, and notes. Auto-computed Fresh, Expiring, Expired badges."),
        ("Waste Logging", "Log waste from pantry items or manual entries. Track exact quantities, units, dates, and reasons (expired, spoiled, leftovers)."),
        ("AI Recipe Generator", "Google Gemini AI integration generates creative recipes specifically targeting soon-to-expire ingredients to prevent waste.")
    ]

    for i, (title, desc) in enumerate(features):
        row = i // 2
        col = i % 2
        left = Inches(0.8 + col * 6.0)
        top = Inches(2.0 + row * 2.3)
        box = slide3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, Inches(5.6), Inches(2.1))
        box.fill.solid()
        box.fill.fore_color.rgb = CARD_BG
        box.line.color.rgb = CARD_BORDER
        tf = box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = Inches(0.3)
        p = tf.paragraphs[0]
        p.text = title
        p.font.size = Pt(16)
        p.font.bold = True
        p.font.color.rgb = ACCENT_BLUE
        p2 = tf.add_paragraph()
        p2.text = desc
        p2.font.size = Pt(13)
        p2.font.color.rgb = TEXT_LIGHT
        p2.space_before = Pt(6)

        p.space_before = Pt(8)
    # ==================== SLIDE 4 ====================
    slide4 = prs.slides.add_slide(blank_slide_layout)
    add_background(slide4, BG_DARK)
    add_header(slide4, "Advanced Bento Analytics", "Hand-drawn SVG charting engine delivering actionable waste intelligence without external bloat")

    analytics_cards = [
        ("30-Day Waste Trend", "Tracks daily waste volume with trend deltas, total comparisons, and entry frequency over the last 30 days."),
        ("Pantry Inventory Waves", "Visualizes usable vs. past-expiry item fluctuations over a 14-day window to monitor kitchen health."),
        ("Category Treemap", "Hierarchical category breakdown across weekly, monthly, and all-time periods with comparative percentages."),
        ("Seasonality Radar", "Compares current year vs. previous year monthly waste totals, active months, and top waste drivers.")
    ]

    for i, (title, desc) in enumerate(analytics_cards):
        row = i // 2
        col = i % 2
        left = Inches(0.8 + col * 6.0)
        top = Inches(2.0 + row * 2.3)
        box = slide4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, Inches(5.6), Inches(2.1))
        box.fill.solid()
        box.fill.fore_color.rgb = CARD_BG
        box.line.color.rgb = CARD_BORDER
        tf = box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = Inches(0.3)
        p = tf.paragraphs[0]
        p.text = title
        p.font.size = Pt(16)
        p.font.bold = True
        p.font.color.rgb = ACCENT_GREEN
        p2 = tf.add_paragraph()
        p2.text = desc
        p2.font.size = Pt(13)
        p2.font.color.rgb = TEXT_LIGHT
        p2.space_before = Pt(6)


    # ==================== SLIDE 5 ====================
    slide5 = prs.slides.add_slide(blank_slide_layout)
    add_background(slide5, BG_DARK)
    add_header(slide5, "Technical Stack & Architecture", "Clean, lightweight, production-ready full-stack architecture")

    layers = [
        ("Backend", "Python + Flask", "RESTful API routes structured in modular blueprints (food, waste, recipes, analytics, AI)."),
        ("Database", "SQLite (Python built-in)", "Robust relational schema (users, food_items, waste_log, recipes) with WAL mode & foreign keys."),
        ("Security", "JWT & Bcrypt", "Stateless authentication with 7-day tokens, password hashing, and user-isolated data scopes."),
        ("Frontend", "Vanilla HTML/CSS/JS", "Modern CSS Grid/Flexbox UI with SPA routing, custom SVG bento charts, and responsive mobile-first layout.")
    ]

    for i, (layer, tech, desc) in enumerate(layers):
        left = Inches(0.8 + i * 2.9)
        top = Inches(2.0)
        width = Inches(2.7)
        height = Inches(4.5)
        box = slide5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        box.fill.solid()
        box.fill.fore_color.rgb = CARD_BG
        box.line.color.rgb = CARD_BORDER
        tf = box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = Inches(0.3)
        p = tf.paragraphs[0]
        p.text = layer
        p.font.size = Pt(14)
        p.font.bold = True
        p.font.color.rgb = ACCENT_BLUE
        p2 = tf.add_paragraph()
        p2.text = tech
        p2.font.size = Pt(16)
        p2.font.bold = True
        p2.font.color.rgb = TEXT_LIGHT
        p2.space_before = Pt(8)
        p3 = tf.add_paragraph()
        p3.text = desc
        p3.font.size = Pt(13)
        p3.font.color.rgb = TEXT_MUTED
        p3.space_before = Pt(12)

    # ==================== SLIDE 6 ====================
    slide6 = prs.slides.add_slide(blank_slide_layout)
    add_background(slide6, BG_DARK)
    add_header(slide6, "Project Summary & Future Roadmap", "Impact and next-generation enhancements")

    c1 = slide6.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(2.0), Inches(5.6), Inches(4.5))
    c1.fill.solid()
    c1.fill.fore_color.rgb = CARD_BG
    c1.line.color.rgb = CARD_BORDER
    tf1 = c1.text_frame
    tf1.word_wrap = True
    tf1.margin_left = tf1.margin_right = tf1.margin_top = tf1.margin_bottom = Inches(0.4)
    p = tf1.paragraphs[0]
    p.text = "Project Summary"
    p.font.size = Pt(20)
    p.font.bold = True
    p.font.color.rgb = ACCENT_GREEN

    for b in ["Successfully built and tested a complete food waste management platform.",
              "21 automated unit/integration tests passing (100% success rate).",
              "Empowers users to reduce household/restaurant waste and save money.",
              "Demonstrates strong full-stack proficiency in Python, Flask, SQLite, and Vanilla JS."]:
        p = tf1.add_paragraph()
        p.text = "• " + b
        p.font.size = Pt(14)
        p.font.color.rgb = TEXT_LIGHT
        p.space_before = Pt(8)

    c2 = slide6.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.9), Inches(2.0), Inches(5.6), Inches(4.5))
    c2.fill.solid()
    c2.fill.fore_color.rgb = CARD_BG
    c2.line.color.rgb = CARD_BORDER
    tf2 = c2.text_frame
    tf2.word_wrap = True
    tf2.margin_left = tf2.margin_right = tf2.margin_top = tf2.margin_bottom = Inches(0.4)
    p = tf2.paragraphs[0]
    p.text = "Future Roadmap"
    p.font.size = Pt(20)
    p.font.bold = True
    p.font.color.rgb = ACCENT_BLUE

    for b in ["Email & Push Reminders for items about to expire.",
              "Community Donations feature to redirect surplus food to nearby people.",
              "Barcode Scanning integration for lightning-fast grocery logging.",
              "Advanced Machine Learning models for predictive waste forecasting."]:
        p = tf2.add_paragraph()
        p.text = "• " + b
        p.font.size = Pt(14)
        p.font.color.rgb = TEXT_LIGHT
        p.space_before = Pt(8)

    output_path = os.path.abspath("Smart_Food_Waste_Management.pptx")
    prs.save(output_path)
    print(f"Presentation saved successfully at: {output_path}")

if __name__ == "__main__":
    create_presentation()

