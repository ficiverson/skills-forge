#!/usr/bin/env python3
"""
AI Engineering Code Challenge -- Competency Matrix PDF Generator
Reads a structured JSON file and produces a landscape A4 evaluation report.

Scores 14 code-verifiable competencies. Seven behavioural/social competencies
(Stakeholder, Mentoring, Ambassador, Collaboration, Emotional Intelligence,
People Impact) are shown as N/A rows in the matrix but excluded from the score.

Usage:
    pip install reportlab --break-system-packages -q
    python generate_eval_pdf.py --input eval_data.json --output report.pdf
"""

import argparse
import json
import sys
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether,
)
from reportlab.lib.colors import HexColor

# -- Palette -------------------------------------------------------------------
DARK        = HexColor("#1A1A1A")
NAVY        = HexColor("#0D1B2A")
BLUE        = HexColor("#1565C0")
LIGHT_BLUE  = HexColor("#DDEEFF")
CANDIDATE   = HexColor("#FF6F00")
GREEN       = HexColor("#2E7D32")
GREY_DARK   = HexColor("#37474F")
GREY_MID    = HexColor("#90A4AE")
GREY_LIGHT  = HexColor("#F5F5F5")
NA_BG       = HexColor("#EEEEEE")
NA_TEXT     = HexColor("#999999")
WHITE       = colors.white
BLACK       = colors.black

LEVEL_COLORS_9 = [
    HexColor("#C62828"), HexColor("#D32F2F"), HexColor("#EF5350"),
    HexColor("#E65100"), HexColor("#F57C00"), HexColor("#FFA726"),
    HexColor("#2E7D32"), HexColor("#388E3C"), HexColor("#66BB6A"),
]
LEVEL_COLORS_3 = [HexColor("#D32F2F"), HexColor("#F57C00"), HexColor("#43A047")]
LEVEL_LABELS_9 = ["Junior 1","Junior 2","Junior 3",
                   "Medior 1","Medior 2","Medior 3",
                   "Senior 1","Senior 2","Senior 3"]
LEVEL_LABELS_3 = ["Junior","Medior","Senior"]


LA4_W, LA4_H = landscape(A4)
LM = 1.2 * cm

# -- Styles --------------------------------------------------------------------
base = getSampleStyleSheet()

def sty(name, parent="Normal", **kw):
    return ParagraphStyle(name, parent=base[parent], **kw)

S = {
    "cover_title": sty("cover_title","Title",  fontSize=32,textColor=WHITE,alignment=TA_LEFT,leading=38),
    "cover_sub":   sty("cover_sub",  "Normal", fontSize=11,textColor=HexColor("#CCCCCC"),alignment=TA_LEFT,leading=16),
    "cover_meta":  sty("cover_meta", "Normal", fontSize=9, textColor=GREY_MID, alignment=TA_LEFT),
    "section_lbl": sty("section_lbl","Normal", fontSize=9, textColor=WHITE,fontName="Helvetica-Bold",alignment=TA_CENTER),
    "band_lbl":    sty("band_lbl",   "Normal", fontSize=8, textColor=WHITE,fontName="Helvetica-Bold",alignment=TA_CENTER),
    "col_head":    sty("col_head",   "Normal", fontSize=7, textColor=WHITE,fontName="Helvetica-Bold",alignment=TA_CENTER),
    "row_head":    sty("row_head",   "Normal", fontSize=7, textColor=WHITE,fontName="Helvetica-Bold",leading=10),
    "row_head_na": sty("row_head_na","Normal", fontSize=7, textColor=NA_TEXT,fontName="Helvetica",leading=10),
    "cell":        sty("cell",       "Normal", fontSize=6.5,textColor=GREY_DARK,leading=9),
    "cell_hi":     sty("cell_hi",    "Normal", fontSize=6.5,textColor=WHITE,fontName="Helvetica-Bold",leading=9),
    "cell_b":      sty("cell_b",     "Normal", fontSize=7, textColor=NAVY,fontName="Helvetica-Bold",leading=10),
    "cell_na":     sty("cell_na",    "Normal", fontSize=7, textColor=NA_TEXT,fontName="Helvetica-Oblique",leading=10,alignment=TA_CENTER),
    "body":        sty("body",       "Normal", fontSize=8, textColor=GREY_DARK,leading=12,alignment=TA_JUSTIFY),
    "body_b":      sty("body_b",     "Normal", fontSize=8, textColor=NAVY,fontName="Helvetica-Bold",leading=12),
    "verdict":     sty("verdict",    "Normal", fontSize=12,textColor=WHITE,fontName="Helvetica-Bold",alignment=TA_CENTER,leading=16),
    "big_score":   sty("big_score",  "Normal", fontSize=36,textColor=WHITE,fontName="Helvetica-Bold",alignment=TA_CENTER),
    "vs":          sty("vs",         "Normal", fontSize=28,textColor=WHITE,fontName="Helvetica-Bold",alignment=TA_CENTER),
    "vr":          sty("vr",         "Normal", fontSize=11,textColor=WHITE,fontName="Helvetica",alignment=TA_CENTER,leading=16),
    "footer":      sty("footer",     "Normal", fontSize=6.5,textColor=GREY_MID,alignment=TA_CENTER),
    "bullet":      sty("bullet",     "Normal", fontSize=8, textColor=GREY_DARK,leading=12,leftIndent=12),
    "h2":          sty("h2",         "Heading2",fontSize=10,textColor=BLUE,spaceBefore=10,spaceAfter=3),
    "cell_ev":     sty("cell_ev",    "Normal", fontSize=7, textColor=GREY_DARK,leading=11),
    # Engineering Practices Audit page
    "ep_cat_name":    sty("ep_cat_name",   "Normal", fontSize=9,   textColor=WHITE,     fontName="Helvetica-Bold", leading=12),
    "ep_rating":      sty("ep_rating",     "Normal", fontSize=7.5, textColor=WHITE,     fontName="Helvetica-Bold", alignment=TA_CENTER),
    "ep_impact":      sty("ep_impact",     "Normal", fontSize=9,   textColor=WHITE,     fontName="Helvetica-Bold", alignment=TA_CENTER),
    "ep_summary":     sty("ep_summary",    "Normal", fontSize=8,   textColor=GREY_DARK, leading=11),
    "ep_find_type":   sty("ep_find_type",  "Normal", fontSize=6.5, textColor=WHITE,     fontName="Helvetica-Bold", alignment=TA_CENTER),
    "ep_find_label":  sty("ep_find_label", "Normal", fontSize=7.5, textColor=NAVY,      fontName="Helvetica-Bold", leading=10),
    "ep_find_loc":    sty("ep_find_loc",   "Normal", fontSize=6.5, textColor=GREY_DARK, fontName="Courier",        leading=9),
    "ep_find_desc":   sty("ep_find_desc",  "Normal", fontSize=7.5, textColor=GREY_DARK, leading=11),
    "ep_find_sug":    sty("ep_find_sug",   "Normal", fontSize=7.5, textColor=HexColor("#1B5E20"), leading=11),
    "ep_adj_note":    sty("ep_adj_note",   "Normal", fontSize=9,   textColor=WHITE,     fontName="Helvetica-Bold", alignment=TA_CENTER),
    "ep_none":        sty("ep_none",       "Normal", fontSize=9,   textColor=HexColor("#2E7D32"), fontName="Helvetica-Bold", alignment=TA_CENTER),
}

def P(text, s="body"):
    return Paragraph(str(text), S[s])

def sp(h=6):
    return Spacer(1, h)

def hr(c=GREY_MID, t=0.5):
    return HRFlowable(width="100%", thickness=t, color=c, spaceAfter=4, spaceBefore=4)

def bullet_item(text):
    return Paragraph(f"&#x2022;  {text}", S["bullet"])

# -- Matrix content ------------------------------------------------------------
# skipped=True rows are shown as N/A in the matrix and excluded from score calc.

CREATION_ROWS = [
    {"key": "code_quality",    "label": "CODE\nQUALITY",    "skipped": False,
     "cells9": [
        "Produces clean, readable code following team style guides. Understands naming and basic refactoring.",
        "Writes unit tests for own features. Uses code reviews as learning. Begins addressing technical debt.",
        "Implements missing plan parts autonomously. Follows TDD. Understands basic anti-patterns.",
        "Applies TDD consistently. Ensures coverage targets. Keeps dependencies updated. Flags quality risks.",
        "Creates or maintains TDD suites. Understands clean-code deeply and applies across team contributions.",
        "Drives quality culture. Designs strategies for non-deterministic APIs. Implements telemetry.",
        "Enforces clean architecture. Proposes and implements solutions that reduce long-term debt.",
        "Creates and enforces architectural standards. Conducts system-wide quality audits.",
        "Designs solutions in complex domains. Defines team-wide quality benchmarks.",
    ]},
    {"key": "documentation",   "label": "DOCU-\nMENTATION",  "skipped": False,
     "cells9": [
        "Documents own tasks to a usable standard. Understands how the team organises documentation.",
        "Fills gaps in existing docs. Documents own features clearly without prompting.",
        "Creates simple, complete docs for each feature including usage examples.",
        "Creates and updates project docs. Produces code docs with diagrams for team members.",
        "Oversees and documents technical processes and test strategies. Documents complex flows.",
        "Produces full sub-system documentation before implementation. Sets doc standards.",
        "Researches, documents, and justifies design decisions. Proposes evidence-backed solutions.",
        "Identifies bottlenecks proactively; documents mitigation strategies before incidents.",
        "Establishes a documentation-first culture. Produces org-wide reference documentation.",
    ]},
    {"key": "conv_tooling",    "label": "CONVEN-\nTIONAL\nTOOLING", "skipped": False,
     "cells9": [
        "Uses and contributes to the team's standard tools, IDEs, linters, and version control workflows.",
        "Learns and applies the technology stack. Uses branching strategies and PR conventions.",
        "Understands CI basics (linting, branch protection, PR flows). Aligns to team tooling.",
        "Uses Docker, pytest, FastAPI, or equivalent. Configures CI steps for own features.",
        "Configures full CI pipelines. Uses Docker Compose for local dev. Writes integration and E2E tests.",
        "Implements CI/CD end-to-end. Introduces observability tooling (logging, tracing, alerts).",
        "Designs and owns the CI/CD strategy. Multi-stage builds, canary deploys, rollback plans.",
        "Defines tooling standards for the team. Selects and justifies infrastructure decisions.",
        "Pioneers new tooling practices. Drives org-wide DevOps maturity improvements.",
    ]},
    {"key": "ai_tooling",      "label": "AI\nTOOLING",       "skipped": False,
     "cells9": [
        "Applies pre-trained models via APIs. Understands prompt basics. Integrates simple AI features.",
        "Interacts with AI models for low-risk cases. Writes basic prompts and evaluates outputs.",
        "Uses public AI frameworks (LangChain, OpenAI SDK) for simple single-agent tasks.",
        "Builds multi-step pipelines using LangGraph or equivalent. Uses structured output and tool calling.",
        "Designs multi-agent systems with guardrails, state management, and intent classification.",
        "Integrates RAG, embeddings, and evaluation frameworks. Builds production-ready agent pipelines.",
        "Designs multi-agent, multi-modal architectures. Builds custom evaluation and observability layers.",
        "Optimises prompt/chain performance. Applies fine-tuning. Builds client-facing AI products.",
        "Pioneers new AI engineering patterns. Defines org-wide AI tooling strategy and roadmap.",
    ]},
    {"key": "learning",        "label": "LEARNING\n& INNOVA-\nTION", "skipped": False,
     "cells9": [
        "Stays up to date with team learnings. Actively participates in recommended training.",
        "Self-studies AI-related news and trends relevant to the team's work.",
        "Experiments with new tools and techniques. Shares findings informally with the team.",
        "Experiments with and evaluates AI/LLM tools proactively. Proposes adoption of useful new tools.",
        "Aligns AI research with business needs. Benchmarks new approaches and presents findings.",
        "Leads exploration of new AI techniques. Runs internal research spikes and documents outcomes.",
        "Publishes articles, delivers talks, or runs workshops. Proficient in skills training.",
        "Drives planning and design sessions. Mentors others in innovation methodology.",
        "Drives roadmap sessions with clients. Explores new frontiers. Identifies new opportunities.",
    ]},
    {"key": "stakeholder",     "label": "STAKE-\nHOLDER\nRELATIONS", "skipped": True,
     "cells9": [
        "Builds positive relations with teammates. Has basic stakeholder mapping awareness.",
        "Stays proactive with teammates. Manages trust-building during sprint cycles.",
        "Able to present increments to stakeholders during sprint reviews.",
        "Helps business mitigate failures. Manages stakeholder expectations on timeline changes.",
        "Helps business improve development cycles by facilitating discovery.",
        "Helps business plan for valuable features. Champions data-informed prioritisation.",
        "Helps clients understand the team's AI capabilities. Manages project complexity.",
        "Drives planning and design sessions with clients to align on strategy.",
        "Drives roadmap sessions. Explores new business frontiers with senior stakeholders.",
    ]},
    {"key": "shaping",         "label": "SHAPING",           "skipped": False,
     "cells9": [
        "Understands user stories and acceptance criteria. Can contribute to backlog refinement.",
        "Plans the basics of own user stories for sprint planning.",
        "Plans own user stories. Collaborates on new items in the backlog.",
        "Collaborates with UX and tech leads in shaping. Ensures new items meet business expectations.",
        "Supports the team or PMs/BAs to ensure expectations align with the long-term plan.",
        "Documents any rejected backlog items with justification. Guides team on scope decisions.",
        "Suggests the right pattern of technical tasks in a backlog. Takes the lead on feature definition.",
        "Identifies where acceptance criteria are too broad and structures contributions clearly.",
        "Defines the ways of working for the AI engineering team. Sets shaping standards.",
    ]},
    {"key": "ways_of_working", "label": "WAYS OF\nWORKING",   "skipped": False,
     "cells9": [
        "Proposes and influences adoption of modern working methods. Attends stand-ups and ceremonies.",
        "Learns Ways of Working methodology. Uses branching and commits following conventions.",
        "Learns to ask questions to understand tasks. Attends ceremonies before starting development.",
        "Aims for clear task requirements. Makes small PRs. Follows development processes accurately.",
        "Has technical knowledge of agile ceremonies. Understands conflicting priorities. Makes suggestions.",
        "Understands the importance of scope and makes accurate estimates. Confronts blockers constructively.",
        "Articulates trade-offs clearly. Sets quality-driven contribution expectations for the team.",
        "Identifies situations where accepted norms are costly and articulates better alternatives.",
        "Defines the ways of working for the whole engineering team.",
    ]},
    {"key": "mentoring",       "label": "MENTOR-\nING",       "skipped": True,
     "cells9": [
        "Imparts basic knowledge and guidance to other beginners in the knowledge domain.",
        "Builds foundational awareness of peer support.",
        "Shares best experiences in team settings.",
        "Assists peers with simple guidance and feedback on code reviews.",
        "Knows how to share experience effectively. Helps to guide teams and individuals.",
        "Consistently shares knowledge with assigned team members. Coaches junior contributors.",
        "Mentors one specialised cross-domain colleague. Boosts team performance through structured mentoring.",
        "Successfully mentors others in the project and across the department.",
        "Referenced as a great mentor. Mentors at least 2 people simultaneously.",
    ]},
    {"key": "teaching",        "label": "TEACH-\nING",        "skipped": False,
     "cells9": [
        "Imparts the right knowledge at the right time. Contributes to the team wiki or FAQs.",
        "Builds foundational awareness of knowledge delivery.",
        "Observes teaching sessions from seniors.",
        "Knows the basics of how to teach teams and individuals.",
        "Can support a teaching session led by another colleague.",
        "Is able to lead a session to teach the team on a specific topic.",
        "Manages audience. Teaches complex topics to the team effectively.",
        "Manages audiences of 5+. Addresses misunderstandings and provides implicit feedback.",
        "A practised presence; always where innovation is taught. Key person for technical education.",
    ]},
]

INTEGRITY_ROWS = [
    {"key": "task_complexity", "label": "TASK\nCOMPLEXITY", "skipped": False,
     "cells3": [
        "Handles straightforward, well-defined tasks with guidance. Demonstrates the ability to problem-solve and execute basic processes.",
        "Manages moderately complex tasks. Analyses options independently and makes informed decisions. Shows deep analytical and problem-solving skill.",
        "Handles highly complex tasks and projects. Ensures deep analysis, strategic thinking, and the ability to drive innovative solutions.",
    ]},
    {"key": "ownership",       "label": "OWNER-\nSHIP",      "skipped": False,
     "cells3": [
        "Takes responsibility for own tasks. Follows instructions. Seeks guidance when unclear and delivers reliably on defined commitments.",
        "Proactive team management. Independent decisions enabling delivery of projects with accountability and adaptability.",
        "Strong ownership of projects. Ensures accountability for complex initiatives. Anticipates risks and makes timely, impactful decisions.",
    ]},
    {"key": "planning",        "label": "PLANNING\n& ORGAN-\nISATION", "skipped": False,
     "cells3": [
        "Basic task scheduling, organising notes, following established procedures. Learning to prioritise based on importance.",
        "Efficient time management. Coordinates tasks. Independently prioritises tasks based on importance and deadlines.",
        "Strategic planning, resource allocation, advanced task prioritisation. Focuses on critical projects and delegates effectively.",
    ]},
]

CURIOSITY_ROWS = [
    {"key": "ambassador",      "label": "AMBASS-\nADOR /\nADVOCATE", "skipped": True,
     "cells3": [
        "Open to participating in internal and external events. Actively contributes to guild work.",
        "Writes posts about industry events and derives talks about relevant topics. Identifies potential benefits within their network.",
        "Identifies and champions initiatives for external teams. Continuously contributes and encourages community connection.",
    ]},
    {"key": "business_impact", "label": "BUSINESS\nIMPACT",   "skipped": False,
     "cells3": [
        "Seeks personal challenges and opportunities for improvement and growth of the business.",
        "Analyses and assesses the impact of strategies on the business. Challenges peers with new business proposals.",
        "Drives initiatives that significantly impact the business. Provides strategic insights that can most positively benefit the business.",
    ]},
]

COLLAB_ROWS = [
    {"key": "communication",   "label": "COMMUN-\nICATION",   "skipped": False,
     "cells3": [
        "Clear expression of ideas in English. Active listening and open-mindedness.",
        "Demonstrates ability to relay and manage communications. Practices communication style with different audiences.",
        "Expert communicator in complex professional environments. Presents ideas and influences others through well-reasoned arguments.",
    ]},
    {"key": "collaboration",   "label": "COLLAB-\nORATION",   "skipped": True,
     "cells3": [
        "Participates in group problem-solving discussions. Offers suggestions and asks questions.",
        "Takes the lead in resolving conflicts. Promotes a respectful and productive environment.",
        "Leads resolution of complex dilemmas. Mentors junior team members in decision-making. Creates a psychologically safe culture.",
    ]},
    {"key": "company_match",   "label": "COMPANY\nMATCH",     "skipped": False,
     "cells3": [
        "Adheres to company values and understands policies and procedures.",
        "Acts as an advocate for company values among disciplines.",
        "Actively promotes an organic, values-led culture within the organisation.",
    ]},
    {"key": "proactivity",     "label": "PROAC-\nTIVITY",    "skipped": False,
     "cells3": [
        "Shares simple ideas and suggestions within the team.",
        "Contributes innovative ideas and solutions that enhance team performance.",
        "Demonstrates agility in dynamic environments. Leads through change. Embraces a culture of innovation.",
    ]},
    {"key": "emotional_intel", "label": "EMOTIONAL\nINTELL-\nIGENCE", "skipped": True,
     "cells3": [
        "Handles simple stressful situations. Shows basic respect for cultural differences.",
        "Clear understanding of own strengths and weaknesses. Manages pressure and handles setbacks constructively.",
        "Handles high-pressure situations as a role model. Cultivates inclusivity and diversity.",
    ]},
    {"key": "people_impact",   "label": "PEOPLE\nIMPACT",    "skipped": True,
     "cells3": [
        "Receives feedback openly. Shows eagerness to learn and contribute.",
        "Participates in recruitment. Provides constructive feedback. Contributes to D&I initiatives.",
        "Leads and empowers others. Provides coaching for performance. Leads hiring practices.",
    ]},
]


# -- Helpers -------------------------------------------------------------------
def section_banner(label):
    tbl = Table([[P(label, "section_lbl")]],
                colWidths=[LA4_W - 2*LM],
                style=TableStyle([
                    ("BACKGROUND",    (0,0), (-1,-1), DARK),
                    ("TOPPADDING",    (0,0), (-1,-1), 6),
                    ("BOTTOMPADDING", (0,0), (-1,-1), 6),
                    ("LEFTPADDING",   (0,0), (-1,-1), 10),
                ]))
    return tbl


def build_9col_table(rows_data, scores_dict):
    usable = LA4_W - 2*LM
    row_w  = 1.8*cm
    cell_w = (usable - row_w) / 9

    band_row = [[P("", "col_head")] +
                [P("JUNIOR", "band_lbl")]*3 +
                [P("MEDIOR", "band_lbl")]*3 +
                [P("SENIOR", "band_lbl")]*3]
    band_style = [
        ("BACKGROUND", (1,0),(3,0), HexColor("#C62828")),
        ("BACKGROUND", (4,0),(6,0), HexColor("#E65100")),
        ("BACKGROUND", (7,0),(9,0), HexColor("#2E7D32")),
        ("BACKGROUND", (0,0),(0,0), DARK),
        ("SPAN",(1,0),(3,0)), ("SPAN",(4,0),(6,0)), ("SPAN",(7,0),(9,0)),
        ("TOPPADDING",(0,0),(-1,-1),2),("BOTTOMPADDING",(0,0),(-1,-1),2),
        ("LEFTPADDING",(0,0),(-1,-1),2),("RIGHTPADDING",(0,0),(-1,-1),2),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("BOX",(0,0),(-1,-1),0.5,BLACK),
        ("INNERGRID",(0,0),(-1,-1),0.3,HexColor("#555")),
    ]
    band_tbl = Table(band_row, colWidths=[row_w]+[cell_w]*9, style=TableStyle(band_style))

    lev_row = [[P("",  "col_head")] + [P(l, "col_head") for l in LEVEL_LABELS_9]]
    lev_style = [("BACKGROUND",(0,0),(0,0),DARK)]
    for i,c in enumerate(LEVEL_COLORS_9):
        lev_style.append(("BACKGROUND",(i+1,0),(i+1,0),c))
    lev_style += [
        ("TOPPADDING",(0,0),(-1,-1),2),("BOTTOMPADDING",(0,0),(-1,-1),2),
        ("LEFTPADDING",(0,0),(-1,-1),2),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("BOX",(0,0),(-1,-1),0.5,BLACK),("INNERGRID",(0,0),(-1,-1),0.3,HexColor("#777")),
    ]
    lev_tbl = Table(lev_row, colWidths=[row_w]+[cell_w]*9, style=TableStyle(lev_style))

    all_rows, all_styles = [], [
        ("BOX",(0,0),(-1,-1),0.5,GREY_DARK),
        ("INNERGRID",(0,0),(-1,-1),0.3,HexColor("#DDD")),
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),3),
        ("LEFTPADDING",(0,0),(-1,-1),3),("RIGHTPADDING",(0,0),(-1,-1),3),
    ]
    for ri, row in enumerate(rows_data):
        if row.get("skipped"):
            # N/A row: dark header + single grey spanned cell
            na_cells = [P(row["label"], "row_head_na"),
                        P("N/A  \u2014  Not assessable from code alone", "cell_na")]
            # pad to 10 columns with empty strings (we'll span cols 1-9)
            na_cells += [""] * 8
            all_rows.append(na_cells)
            all_styles.append(("BACKGROUND",(0,ri),(0,ri),HexColor("#CCCCCC")))
            all_styles.append(("BACKGROUND",(1,ri),(9,ri),NA_BG))
            all_styles.append(("SPAN",(1,ri),(9,ri)))
        else:
            cand_col = scores_dict.get(row["key"], {}).get("level9", -1)
            cells = [P(row["label"], "row_head")]
            for ci, txt in enumerate(row["cells9"]):
                cells.append(P(f"\u2605 {txt}", "cell_hi") if ci == cand_col else P(txt, "cell"))
            all_rows.append(cells)
            row_bg = HexColor("#F9F9F9") if ri % 2 == 0 else WHITE
            hdr_bg = HexColor("#2C2C2C") if ri % 2 == 0 else HexColor("#3A3A3A")
            all_styles.append(("BACKGROUND",(0,ri),(0,ri),hdr_bg))
            for ci in range(9):
                bg = CANDIDATE if ci == cand_col else row_bg
                all_styles.append(("BACKGROUND",(ci+1,ri),(ci+1,ri),bg))

    content_tbl = Table(all_rows, colWidths=[row_w]+[cell_w]*9, style=TableStyle(all_styles))
    return [band_tbl, lev_tbl, content_tbl]


def build_3col_table(rows_data, scores_dict):
    usable = LA4_W - 2*LM
    row_w  = 2.5*cm
    cell_w = (usable - row_w) / 3

    band_row = [[P("","col_head"), P("JUNIOR","band_lbl"), P("MEDIOR","band_lbl"), P("SENIOR","band_lbl")]]
    band_style = [
        ("BACKGROUND",(0,0),(0,0),DARK),
        ("BACKGROUND",(1,0),(1,0),HexColor("#C62828")),
        ("BACKGROUND",(2,0),(2,0),HexColor("#E65100")),
        ("BACKGROUND",(3,0),(3,0),HexColor("#2E7D32")),
        ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
        ("LEFTPADDING",(0,0),(-1,-1),4),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("BOX",(0,0),(-1,-1),0.5,BLACK),("INNERGRID",(0,0),(-1,-1),0.3,HexColor("#555")),
    ]
    band_tbl = Table(band_row, colWidths=[row_w,cell_w,cell_w,cell_w], style=TableStyle(band_style))

    all_rows, all_styles = [], [
        ("BOX",(0,0),(-1,-1),0.5,GREY_DARK),
        ("INNERGRID",(0,0),(-1,-1),0.3,HexColor("#DDD")),
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("LEFTPADDING",(0,0),(-1,-1),5),("RIGHTPADDING",(0,0),(-1,-1),5),
    ]
    for ri, row in enumerate(rows_data):
        if row.get("skipped"):
            na_cells = [P(row["label"], "row_head_na"),
                        P("N/A  \u2014  Not assessable from code alone", "cell_na"), "", ""]
            all_rows.append(na_cells)
            all_styles.append(("BACKGROUND",(0,ri),(0,ri),HexColor("#CCCCCC")))
            all_styles.append(("BACKGROUND",(1,ri),(3,ri),NA_BG))
            all_styles.append(("SPAN",(1,ri),(3,ri)))
        else:
            cand_col = scores_dict.get(row["key"], {}).get("level3", -1)
            cells = [P(row["label"], "row_head")]
            for ci, txt in enumerate(row["cells3"]):
                cells.append(P(f"\u2605 {txt}", "cell_hi") if ci == cand_col else P(txt, "cell"))
            all_rows.append(cells)
            row_bg = HexColor("#F9F9F9") if ri % 2 == 0 else WHITE
            hdr_bg = HexColor("#2C2C2C") if ri % 2 == 0 else HexColor("#3A3A3A")
            all_styles.append(("BACKGROUND",(0,ri),(0,ri),hdr_bg))
            for ci in range(3):
                bg = CANDIDATE if ci == cand_col else row_bg
                all_styles.append(("BACKGROUND",(ci+1,ri),(ci+1,ri),bg))

    content_tbl = Table(all_rows, colWidths=[row_w,cell_w,cell_w,cell_w], style=TableStyle(all_styles))
    return [band_tbl, content_tbl]


def mini_bar(filled, total, col_w=0.8*cm, cell_h=8):
    cells = [[Paragraph("", S["body"])] * total]
    style = [
        ("ROWHEIGHT",(0,0),(-1,-1),cell_h),
        ("BOX",(0,0),(-1,-1),0.3,GREY_MID),
        ("INNERGRID",(0,0),(-1,-1),0.3,WHITE),
    ]
    for i in range(total):
        style.append(("BACKGROUND",(i,0),(i,0), CANDIDATE if i < filled else HexColor("#EEEEEE")))
    return Table(cells, colWidths=[col_w]*total, style=TableStyle(style))


# -- Engineering Practices Audit colours -------------------------------------
EP_PASS = HexColor("#2E7D32")   # green  -- PASS rating
EP_WARN = HexColor("#E65100")   # orange -- WARN rating
EP_FAIL = HexColor("#C62828")   # red    -- FAIL rating

EP_TYPE_VIOLATION = HexColor("#C62828")   # finding type: violation
EP_TYPE_WARNING   = HexColor("#F57C00")   # finding type: warning
EP_TYPE_GOOD      = HexColor("#2E7D32")   # finding type: good practice

EP_IMP_POS = HexColor("#2E7D32")   # impact +1 badge
EP_IMP_NEU = HexColor("#78909C")   # impact  0 badge
EP_IMP_NEG = HexColor("#C62828")   # impact -1 badge


def build_engineering_practices_page(ep_data):
    """Build the Engineering Practices Audit page.

    ep_data keys:
        summary           -- str, one-line overview
        score_adjustment  -- int  (-2 … +2), positive = upgrade, negative = downgrade
        adjustment_reason -- str, human-readable reason shown in the adjustment banner
        categories        -- list of category dicts:
          {
            id, name, rating (PASS|WARN|FAIL), impact (-1|0|+1),
            summary,
            findings: [{type (VIOLATION|WARNING|GOOD_PRACTICE), label, location,
                        description, suggestion}]
          }

    Layout (no nested tables -- avoids all ReportLab height-calculation overlap):
        Adjustment banner (if score_adjustment != 0)
        For each category:
            Category header table  [Name | PASS/WARN/FAIL | impact | summary]
            Findings table         [TYPE | Rule/Pattern   | Location | Description | Suggestion]
            Spacer
    """
    usable = LA4_W - 2 * LM
    flowables = []

    summary = ep_data.get("summary", "")
    adj     = int(ep_data.get("score_adjustment", 0))
    adj_rsn = ep_data.get("adjustment_reason", "")
    cats    = ep_data.get("categories", [])

    if summary:
        flowables.append(sp(4))
        flowables.append(P(summary, "body_b"))

    # Score-adjustment banner ------------------------------------------------
    if adj != 0:
        flowables.append(sp(6))
        sign      = f"▲ +{adj}" if adj > 0 else f"▼ {adj}"
        adj_text  = f"{sign} level adjustment  ·  {adj_rsn}"
        adj_col   = EP_IMP_POS if adj > 0 else EP_IMP_NEG
        adj_tbl   = Table(
            [[P(adj_text, "ep_adj_note")]],
            colWidths=[usable],
            style=TableStyle([
                ("BACKGROUND",    (0, 0), (-1, -1), adj_col),
                ("TOPPADDING",    (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING",   (0, 0), (-1, -1), 14),
            ]),
        )
        flowables.append(adj_tbl)

    if not cats:
        flowables.append(sp(8))
        flowables.append(Table(
            [[P("✅  No engineering practices categories defined.", "ep_none")]],
            colWidths=[usable],
            style=TableStyle([
                ("BACKGROUND",    (0, 0), (-1, -1), HexColor("#E8F5E9")),
                ("BOX",           (0, 0), (-1, -1), 0.5, HexColor("#A5D6A7")),
                ("TOPPADDING",    (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ]),
        ))
        return flowables

    # Finding-table column widths (flat -- no inner tables)
    W_FTYPE = 2.0 * cm
    W_FLBL  = 3.2 * cm
    W_FLOC  = 4.2 * cm
    rem     = usable - W_FTYPE - W_FLBL - W_FLOC
    W_FDESC = rem * 0.55
    W_FSUG  = rem * 0.45
    find_cols = [W_FTYPE, W_FLBL, W_FLOC, W_FDESC, W_FSUG]

    # Category header column widths
    W_CNAME = 5.8 * cm
    W_CRATE = 2.0 * cm
    W_CIMP  = 1.8 * cm
    W_CSUM  = usable - W_CNAME - W_CRATE - W_CIMP
    cat_cols = [W_CNAME, W_CRATE, W_CIMP, W_CSUM]

    for cat in cats:
        cat_name = cat.get("name", "")
        rating   = cat.get("rating", "WARN")
        impact   = int(cat.get("impact", 0))
        cat_sum  = cat.get("summary", "")
        findings = cat.get("findings", [])

        r_col = {"PASS": EP_PASS, "WARN": EP_WARN, "FAIL": EP_FAIL}.get(rating, EP_WARN)
        i_col = EP_IMP_POS if impact > 0 else (EP_IMP_NEG if impact < 0 else EP_IMP_NEU)
        i_lbl = f"▲ +{impact}" if impact > 0 else (f"▼ {impact}" if impact < 0 else "─ 0")

        flowables.append(sp(8))

        # Category header row (plain 4-column table, zero nesting)
        cat_hdr = Table(
            [[P(cat_name, "ep_cat_name"),
              P(rating,   "ep_rating"),
              P(i_lbl,    "ep_impact"),
              P(cat_sum,  "ep_summary")]],
            colWidths=cat_cols,
            style=TableStyle([
                ("BACKGROUND",    (0, 0), (0, 0), r_col),
                ("BACKGROUND",    (1, 0), (1, 0), r_col),
                ("BACKGROUND",    (2, 0), (2, 0), i_col),
                ("BACKGROUND",    (3, 0), (3, 0), HexColor("#F5F5F5")),
                ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING",    (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LEFTPADDING",   (0, 0), (-1, -1), 8),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
                ("BOX",           (0, 0), (-1, -1), 0.8, r_col),
                ("INNERGRID",     (0, 0), (-1, -1), 0.3, HexColor("#DDDDDD")),
            ]),
        )
        flowables.append(cat_hdr)

        # Only show violations and warnings -- filter out good practices
        visible_findings = [f for f in findings if f.get("type") in ("VIOLATION", "WARNING")]
        if not visible_findings:
            continue

        # Findings table (all data rows in one flat Table -- no nesting)
        f_hdr = [
            P("TYPE",        "col_head"),
            P("RULE / PATTERN", "col_head"),
            P("LOCATION",    "col_head"),
            P("DESCRIPTION", "col_head"),
            P("SUGGESTION",  "col_head"),
        ]
        f_rows  = [f_hdr]
        f_style = [
            ("BACKGROUND",    (0, 0), (-1, 0), DARK),
            ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
            ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, 0), 6.5),
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING",   (0, 0), (-1, -1), 5),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
            ("BOX",           (0, 0), (-1, -1), 0.5, HexColor("#BBBBBB")),
            ("INNERGRID",     (0, 0), (-1, -1), 0.3, HexColor("#EEEEEE")),
        ]

        _TYPE_COL = {
            "VIOLATION":    EP_TYPE_VIOLATION,
            "WARNING":      EP_TYPE_WARNING,
            "GOOD_PRACTICE": EP_TYPE_GOOD,
        }
        _TYPE_LBL = {
            "VIOLATION":    "VIOLATION",
            "WARNING":      "WARNING",
            "GOOD_PRACTICE": "GOOD",
        }

        for fi, fd in enumerate(visible_findings):
            ri    = fi + 1
            ftype = fd.get("type", "WARNING")
            t_col = _TYPE_COL.get(ftype, EP_TYPE_WARNING)
            t_lbl = _TYPE_LBL.get(ftype, ftype)
            sug   = fd.get("suggestion") or "—"

            f_rows.append([
                P(t_lbl,                  "ep_find_type"),
                P(fd.get("label", ""),    "ep_find_label"),
                P(fd.get("location", ""), "ep_find_loc"),
                P(fd.get("description", ""), "ep_find_desc"),
                P(sug,                    "ep_find_sug"),
            ])
            row_bg = HexColor("#FAFAFA") if fi % 2 == 0 else WHITE
            f_style.append(("BACKGROUND", (0, ri), (-1, ri), row_bg))
            # Colour the TYPE cell directly (no badge table)
            f_style.append(("BACKGROUND", (0, ri), (0, ri), t_col))
            f_style.append(("TEXTCOLOR",  (0, ri), (0, ri), WHITE))
            f_style.append(("FONTNAME",   (0, ri), (0, ri), "Helvetica-Bold"))
            f_style.append(("VALIGN",     (0, ri), (0, ri), "MIDDLE"))

        flowables.append(Table(f_rows, colWidths=find_cols,
                               style=TableStyle(f_style), repeatRows=1))

    return flowables


def compute_overall(data):
    """Normalise scored competencies to 0-8 scale then convert to 0-10.
    Skipped competencies (skipped=True) are excluded from the calculation."""
    scores = []
    for rd in CREATION_ROWS:
        if not rd.get("skipped"):
            v = data["creation_mastery"].get(rd["key"], {}).get("level9", 0)
            scores.append(v)
    for rd in INTEGRITY_ROWS:
        if not rd.get("skipped"):
            v = data["integrity_autonomy"].get(rd["key"], {}).get("level3", 0)
            scores.append(v * 4)
    for rd in CURIOSITY_ROWS:
        if not rd.get("skipped"):
            v = data["curiosity_evangelism"].get(rd["key"], {}).get("level3", 0)
            scores.append(v * 4)
    for rd in COLLAB_ROWS:
        if not rd.get("skipped"):
            v = data["collaboration_humanity"].get(rd["key"], {}).get("level3", 0)
            scores.append(v * 4)
    avg_08 = sum(scores) / len(scores)
    return round(avg_08 / 8 * 10, 2)


_LEVEL_LABELS_DASHED = [
    "Junior-1", "Junior-2", "Junior-3",
    "Medior-1", "Medior-2", "Medior-3",
    "Senior-1", "Senior-2", "Senior-3",
]


def score_to_level(s10):
    if   s10 >= 9.3: return "Senior-3",  LEVEL_COLORS_9[8]
    elif s10 >= 8.7: return "Senior-2",  LEVEL_COLORS_9[7]
    elif s10 >= 8.0: return "Senior-1",  LEVEL_COLORS_9[6]
    elif s10 >= 7.3: return "Medior-3",  LEVEL_COLORS_9[5]
    elif s10 >= 6.5: return "Medior-2",  LEVEL_COLORS_9[4]
    elif s10 >= 5.7: return "Medior-1",  LEVEL_COLORS_9[3]
    elif s10 >= 4.8: return "Junior-3",  LEVEL_COLORS_9[2]
    elif s10 >= 3.8: return "Junior-2",  LEVEL_COLORS_9[1]
    else:            return "Junior-1",  LEVEL_COLORS_9[0]


def level_to_idx(s10):
    """Same thresholds as score_to_level but returns 0-8 integer index."""
    if   s10 >= 9.3: return 8
    elif s10 >= 8.7: return 7
    elif s10 >= 8.0: return 6
    elif s10 >= 7.3: return 5
    elif s10 >= 6.5: return 4
    elif s10 >= 5.7: return 3
    elif s10 >= 4.8: return 2
    elif s10 >= 3.8: return 1
    else:            return 0


def idx_to_level(idx):
    """Convert a 0-8 index to (label, colour)."""
    idx = max(0, min(8, idx))
    return _LEVEL_LABELS_DASHED[idx], LEVEL_COLORS_9[idx]


def on_page(canvas, doc):
    canvas.saveState()
    w = doc.pagesize[0]
    h = doc.pagesize[1]
    if doc.page == 1:
        canvas.restoreState()
        return
    canvas.setFillColor(DARK)
    canvas.rect(0, h - 0.9*cm, w, 0.9*cm, fill=1, stroke=0)
    canvas.setFont("Helvetica-Bold", 7)
    canvas.setFillColor(WHITE)
    canvas.drawString(1.2*cm, h - 0.6*cm, "AI Engineer \u2014 Competency Matrix Evaluation")
    canvas.setFont("Helvetica", 7)
    canvas.drawRightString(w - 1.2*cm, h - 0.6*cm, "CONFIDENTIAL")
    canvas.setFillColor(GREY_MID)
    canvas.setFont("Helvetica", 6.5)
    canvas.drawCentredString(w/2, 0.5*cm, f"Page {doc.page}  |  AI Engineering Challenge Evaluation  |  {doc._EVAL_DATE}")
    canvas.restoreState()


# -- Main builder --------------------------------------------------------------
def build_pdf(data: dict, output_path: str):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=landscape(A4),
        leftMargin=LM, rightMargin=LM,
        topMargin=1.4*cm, bottomMargin=1.2*cm,
    )
    doc._EVAL_DATE = data.get("date", "")

    cm_scores  = data.get("creation_mastery", {})
    int_scores = data.get("integrity_autonomy", {})
    cur_scores = data.get("curiosity_evangelism", {})
    col_scores = data.get("collaboration_humanity", {})

    overall = compute_overall(data)

    # Engineering practices adjustment (shifts the level index up or down)
    eng_practices = data.get("engineering_practices", {})
    score_adj  = int(eng_practices.get("score_adjustment", 0))
    adj_reason = eng_practices.get("adjustment_reason", "")
    base_idx   = level_to_idx(overall)
    adj_idx    = max(0, min(8, base_idx + score_adj))
    base_lv,  base_col  = idx_to_level(base_idx)
    final_lv, final_col = idx_to_level(adj_idx)

    # Count scored vs skipped
    n_scored  = sum(1 for r in CREATION_ROWS + INTEGRITY_ROWS + CURIOSITY_ROWS + COLLAB_ROWS
                    if not r.get("skipped"))
    n_skipped = sum(1 for r in CREATION_ROWS + INTEGRITY_ROWS + CURIOSITY_ROWS + COLLAB_ROWS
                    if r.get("skipped"))

    story = []

    # -- COVER -----------------------------------------------------------------
    cover_rows = [
        [P("Growth Framework", "cover_meta"), P("Scope of Work", "cover_meta")],
        [P("AI Engineer", "cover_title"),
         P("Research &amp; Discovery  \u00b7  Ideation &amp; Conceptualisation  \u00b7  Design Interactions  \u00b7  Technical Development  \u00b7  Test &amp; Evaluation", "cover_sub")],
        [P(data.get("repo_summary", ""), "cover_sub"), P("", "body")],
        [P(f"Candidate: <b>{data.get('candidate_name','Anonymous')}</b>  \u00b7  Project: <b>{data.get('project_name','')}</b>  \u00b7  {data.get('date','')}", "cover_meta"),
         P(f"Stack: {data.get('tech_stack','')}", "cover_meta")],
    ]
    cover_tbl = Table(cover_rows,
                      colWidths=[(LA4_W-2*LM)*0.55, (LA4_W-2*LM)*0.45],
                      style=TableStyle([
                          ("BACKGROUND",(0,0),(-1,-1),DARK),
                          ("TOPPADDING",(0,0),(-1,-1),10),("BOTTOMPADDING",(0,0),(-1,-1),10),
                          ("LEFTPADDING",(0,0),(-1,-1),20),("RIGHTPADDING",(0,0),(-1,-1),20),
                          ("VALIGN",(0,0),(-1,-1),"TOP"),
                          ("SPAN",(0,2),(1,2)),("SPAN",(0,3),(1,3)),
                      ]))
    story.append(sp(0.5*cm))
    story.append(cover_tbl)
    story.append(sp(0.5*cm))

    legend_note = (f"\u2605  Orange = candidate level  \u00b7  "
                   f"Grey rows = N/A (not assessable from code)  \u00b7  "
                   f"Score based on {n_scored} scored competencies ({n_skipped} excluded)")
    legend = Table([[
        P(legend_note, "body_b"),
    ]], colWidths=[LA4_W-2*LM],
    style=TableStyle([
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("BACKGROUND",(0,0),(-1,-1),HexColor("#F5F5F5")),
        ("BOX",(0,0),(-1,-1),0.5,GREY_MID),
        ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),
        ("LEFTPADDING",(0,0),(-1,-1),10),
    ]))
    story.append(legend)
    story.append(PageBreak())

    # -- CREATION / MASTERY pt.1 -----------------------------------------------
    story.append(section_banner("CREATION / MASTERY"))
    story.append(sp(4))
    story += build_9col_table(CREATION_ROWS[:5], cm_scores)
    story.append(PageBreak())

    # -- CREATION / MASTERY pt.2 -----------------------------------------------
    story.append(section_banner("CREATION / MASTERY  (continued)"))
    story.append(sp(4))
    story += build_9col_table(CREATION_ROWS[5:], cm_scores)
    story.append(PageBreak())

    # Integrity / Curiosity / Collaboration pages intentionally omitted from
    # the printed report -- scores are still computed and shown in the Summary.

    # -- SCORE SUMMARY ---------------------------------------------------------
    story.append(section_banner("CANDIDATE SCORE SUMMARY"))
    story.append(sp(8))

    sum_hdr = [P("Competency", "col_head"), P("Section", "col_head"),
               P("Evidence / Notes", "col_head")]
    sum_rows = [sum_hdr]

    def sum_row_9(rd, section_label, scores):
        if rd.get("skipped"):
            return [P(rd["label"].replace("\n"," "), "cell_na"),
                    P(section_label, "cell_na"),
                    P("Not assessable from code alone", "cell_na")]
        ev  = scores.get(rd["key"], {}).get("evidence", "")
        return [P(rd["label"].replace("\n"," "), "cell_b"),
                P(section_label, "cell"),
                P(ev, "cell_ev")]

    def sum_row_3(rd, section_label, scores):
        if rd.get("skipped"):
            return [P(rd["label"].replace("\n"," "), "cell_na"),
                    P(section_label, "cell_na"),
                    P("Not assessable from code alone", "cell_na")]
        ev  = scores.get(rd["key"], {}).get("evidence", "")
        return [P(rd["label"].replace("\n"," "), "cell_b"),
                P(section_label, "cell"),
                P(ev, "cell_ev")]

    for rd in CREATION_ROWS:
        sum_rows.append(sum_row_9(rd, "Creation / Mastery", cm_scores))
    for rd in INTEGRITY_ROWS:
        sum_rows.append(sum_row_3(rd, "Integrity / Autonomy", int_scores))
    for rd in CURIOSITY_ROWS:
        sum_rows.append(sum_row_3(rd, "Curiosity / Evangelism", cur_scores))
    for rd in COLLAB_ROWS:
        sum_rows.append(sum_row_3(rd, "Collaboration / Humanity", col_scores))

    sum_w = LA4_W - 2*LM
    sum_tbl = Table(sum_rows,
                    colWidths=[5.5*cm, 4.5*cm, sum_w - 5.5*cm - 4.5*cm - 0.5*cm],
                    style=TableStyle([
                        ("BACKGROUND",(0,0),(-1,0),DARK),("TEXTCOLOR",(0,0),(-1,0),WHITE),
                        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
                        ("FONTSIZE",(0,0),(-1,-1),7.5),
                        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
                        ("VALIGN",(2,1),(2,-1),"TOP"),   # evidence column: TOP so long text doesn't clip
                        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
                        ("LEFTPADDING",(0,0),(-1,-1),5),
                        ("BOX",(0,0),(-1,-1),0.5,GREY_DARK),
                        ("INNERGRID",(0,0),(-1,-1),0.3,HexColor("#DDDDDD")),
                    ] + [("BACKGROUND",(0,i),(1,i),HexColor("#F5F5F5")) for i in range(2,len(sum_rows),2)]))
    sum_tbl.hAlign = 'CENTER'
    story.append(sum_tbl)
    story.append(PageBreak())

    # -- ENGINEERING PRACTICES AUDIT ------------------------------------------
    story.append(section_banner("ENGINEERING PRACTICES AUDIT"))
    story += build_engineering_practices_page(eng_practices)
    story.append(PageBreak())

    # -- FINAL VERDICT ---------------------------------------------------------
    story.append(section_banner("FINAL VERDICT & HIRING RECOMMENDATION"))
    story.append(sp(12))

    # Build recommendation text; prepend adjustment note when level was shifted
    rec_default = (f"Based on {n_scored} code-verifiable competencies. "
                   f"({n_skipped} behavioural dimensions excluded — see matrix for N/A rows.)")
    rec_text = data.get("hiring_recommendation", rec_default)
    if score_adj != 0:
        sign     = f"+{score_adj}" if score_adj > 0 else str(score_adj)
        adj_note = (f"Base level: {base_lv}  {'▲' if score_adj > 0 else '▼'}  "
                    f"Engineering practices adjustment ({sign})  →  Final: {final_lv}\n\n")
        rec_text = adj_note + rec_text

    verdict_data = [[
        P(final_lv, "big_score"),
        P(f"{overall:.1f} / 10", "vs"),
        P(rec_text, "vr"),
    ]]
    v_tbl = Table(verdict_data, colWidths=[8*cm, 7*cm, LA4_W-2*LM-15*cm],
                  style=TableStyle([
                      ("BACKGROUND",(0,0),(0,0),final_col),
                      ("BACKGROUND",(1,0),(1,0),DARK),
                      ("BACKGROUND",(2,0),(2,0),NAVY),
                      ("TOPPADDING",(0,0),(-1,-1),14),("BOTTOMPADDING",(0,0),(-1,-1),14),
                      ("LEFTPADDING",(0,0),(-1,-1),16),
                      ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
                      ("BOX",(0,0),(-1,-1),1,DARK),
                  ]))
    story.append(v_tbl)
    story.append(sp(16))

    ep_cats = eng_practices.get("categories", [])

    story.append(P("Key Strengths", "h2"))
    for rd in CREATION_ROWS:
        if not rd.get("skipped"):
            for s in cm_scores.get(rd["key"], {}).get("strengths", []):
                story.append(bullet_item(f"<b>{rd['label'].replace(chr(10),' ')}:</b> {s}"))
                story.append(sp(2))
    # Engineering practices good findings → strengths
    for cat in ep_cats:
        for fd in cat.get("findings", []):
            if fd.get("type") == "GOOD_PRACTICE":
                story.append(bullet_item(
                    f"<b>{cat.get('name', 'Engineering')}:</b> {fd.get('description', '')}"))
                story.append(sp(2))

    story.append(sp(8))
    story.append(P("Growth Areas", "h2"))
    for rd in CREATION_ROWS:
        if not rd.get("skipped"):
            for g in cm_scores.get(rd["key"], {}).get("gaps", []):
                story.append(bullet_item(f"<b>{rd['label'].replace(chr(10),' ')}:</b> {g}"))
                story.append(sp(2))
    # Engineering practices violations/warnings → growth areas
    for cat in ep_cats:
        for fd in cat.get("findings", []):
            if fd.get("type") in ("VIOLATION", "WARNING"):
                story.append(bullet_item(
                    f"<b>{cat.get('name', 'Engineering')}:</b> {fd.get('description', '')}"))
                story.append(sp(2))

    story.append(sp(16))
    story.append(hr())
    story.append(P(
        f"Generated by the AI Engineering Code Challenge Evaluator. "
        f"Score reflects {n_scored} code-verifiable competencies; "
        f"{n_skipped} behavioural dimensions are shown as N/A and excluded from the score. "
        f"For internal use only.",
        "footer"))

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print(f"PDF written to: {output_path}")


# -- CLI -----------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate competency matrix evaluation PDF.")
    parser.add_argument("--input",  required=True, help="Path to eval_data.json")
    parser.add_argument("--output", required=True, help="Path for output PDF")
    args = parser.parse_args()

    with open(args.input) as f:
        data = json.load(f)

    build_pdf(data, args.output)
