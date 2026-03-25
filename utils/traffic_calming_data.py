"""
==============================================================================
TRAFFIC CALMING DATA — Street Lists, Classification Constants, Scoring Criteria
==============================================================================
File: utils/traffic_calming_data.py
Policy Authority: Resolution 2026-12, City of Brentwood, TN (adopted 02/09/2026)
                  Municipal Code — Arterial & Collector Designations

This file is the single source of truth for:
  - All arterial street names (from Municipal Code §XX-XX)
  - All collector street names (from Municipal Code §XX-XX)
  - Street classification options and policy routing
  - Application type options
  - Tier 2 strategy list (Part V–b Tier 2)
  - Prioritization scoring criteria (Part V–b–3)
  - Resolution adoption date for moratorium transition rule (Res. 2026-12 §3)
==============================================================================
"""

# Resolution adoption date — used for the moratorium transition rule.
# Per Resolution 2026-12 Section 3, petitions with votes within 12 months
# PRIOR to this date are subject to a 12-month moratorium only (not 24).
RESOLUTION_DATE = "2026-02-09"

# ==============================================================================
# ARTERIAL STREETS
# Source: City of Brentwood Municipal Code — Arterial Road Designations
# These streets use MUTCD warrants for multi-way stop signs (Part I of policy).
# Standard traffic calming policy does NOT apply to arterials.
# ==============================================================================
ARTERIAL_STREETS = [
    "Carothers Parkway North (Moores Lane to southern city boundary)",
    "Church Street East (Franklin Road to eastern city limits)",
    "Concord Road / S.R. 253 (Franklin Road to eastern city limits)",
    "Crockett Road (Wilson Pike to Concord Road)",
    "Edmondson Pike (northern city limits to Concord Road)",
    "Franklin Road / S.R. 6 (northern city boundary to Moores Lane)",
    "Granny White Pike (northern city boundary to Murray Lane)",
    "Green Hill Boulevard (Crockett Road to Old Smyrna Road terminus)",
    "Hillsboro Road / S.R. 106 (within city limits)",
    "Holly Tree Gap Road (within city limits)",
    "Mallory Lane (Old Mallory Station Road to Moores Lane / S.R. 441)",
    "Maryland Way (Franklin Road to Granny White Pike)",
    "Moores Lane / S.R. 441 (Franklin Road to Wilson Pike)",
    "Murray Lane (Franklin Road to western city boundary)",
    "Old Smyrna Road (Wilson Pike to eastern city limits, west of Edmondson Pike)",
    "Ragsdale Road (Sunset Road to Split Log Road)",
    "Raintree Parkway (Crockett Road to Wilson Pike)",
    "Split Log Road (within city limits)",
    "Sunset Road (Concord Road to eastern city boundary)",
    "Waller Road (Concord Road to southern city boundary)",
    "Wilson Pike / S.R. 252 (Church Street East to southern city boundary)",
]

# ==============================================================================
# COLLECTOR STREETS
# Source: City of Brentwood Municipal Code — Collector Road Designations
# Residential collectors use Traffic Calming Policy (Part V) — 100% City funded.
# Non-residential collectors are NOT eligible for standard traffic calming.
# ==============================================================================
COLLECTOR_STREETS = [
    "Arrowhead Drive",
    "Belle Rive Drive",
    "Bluff Road",
    "Brentwood Boulevard",
    "Cadillac Drive",
    "Carriage Hills Drive",
    "Charity Drive",
    "Concord Pass",
    "Eastpark Drive",
    "General George Patton Drive",
    "Gordon Petty Road",
    "Johnson Chapel Road West",
    "Jones Parkway",
    "Knox Valley Drive",
    "Lipscomb Drive",
    "Mallory Lane (north of Moores Lane)",
    "Manley Lane",
    "McGavock Road",
    "Paddock Village Court",
    "Pinkerton Road",
    "Powell Place South",
    "Service Merchandise Boulevard",
    "Service Merchandise Drive",
    "Stanfield Road",
    "Steeplechase Drive",
    "Sunset Road (north of Concord Road)",
    "Virginia Way",
    "Walnut Hills Drive",
    "Ward Circle",
    "Westpark Drive",
    "Westwood Place (south of Maryland Way)",
    "Wilson Pike Circle",
    "Winners Circle South",
]

# Residential collectors specifically identified in Resolution 2026-12 Part V
# (subset of COLLECTOR_STREETS — these are eligible for traffic calming under Part V)
RESIDENTIAL_COLLECTOR_STREETS = [
    "Arrowhead Drive",
    "Belle Rive Drive",
    "Bluff Road",
    "Carriage Hills Drive",
    "Charity Drive",
    "Concord Pass",
    "General George Patton Drive",
    "Gordon Petty Road",
    "Johnson Chapel Road West",
    "Jones Parkway",
    "Knox Valley Drive",
    "Lipscomb Drive",
    "Manley Lane",
    "McGavock Road",
    "Pinkerton Road",
    "Stanfield Road",
    "Steeplechase Drive",
    "Sunset Road (north of Concord Road)",
    "Walnut Hills Drive",
]

# ==============================================================================
# STREET CLASSIFICATION OPTIONS
# Maps the user-facing label to an internal code used for policy routing.
# ==============================================================================
STREET_CLASSIFICATIONS = {
    "Arterial Street":                       "arterial",   # Part I/II stop sign warrants only
    "Collector Street":                      "collector",  # Part V calming — 100% City funded
    "Local Residential Street":              "local",      # Part VII speed humps — 60% cost-share
}

# ==============================================================================
# APPLICATION TYPE OPTIONS
# ==============================================================================
APPLICATION_TYPES = {
    "Traffic Calming (Collector Street)": "calming",
    "Speed Humps (Local Street)":         "humps",
    "Multi-Way Stop Sign":                "stop",
}

# ==============================================================================
# TIER 2 STRATEGIES
# Source: Resolution 2026-12, Part V–b Tier 2
# Note: Speed humps are NOT eligible on collector roads (Part V–b Tier 2 Note)
# ==============================================================================
TIER2_STRATEGIES = [
    ("Medians or median islands (must fit within ROW)",      "Part V–b Tier 2"),
    ("Traffic circles or roundabouts (subject to ROW)",      "Part V–b Tier 2"),
    ("Curb extensions / bulb-outs",                          "Part V–b Tier 2"),
    ("Chicanes",                                             "Part V–b Tier 2"),
    ("Speed tables / raised crosswalks",                     "Part V–b Tier 2"),
    ("Textured pavements",                                   "Part V–b Tier 2"),
    ("Speed humps - LOCAL STREETS ONLY, not collectors",     "Part V–b Tier 2 Note; Part VII"),
    ("Other strategy (requires City Commission approval)",   "Part V–b Tier 2"),
]

# ==============================================================================
# PRIORITIZATION SCORING CRITERIA
# Source: Resolution 2026-12, Part V–b–3
# Used when multiple Tier 2 requests exist simultaneously.
# Total possible points: 100
# ==============================================================================
SCORING_CRITERIA = [
    {
        "id":    "speed",
        "label": "Speed",
        "max":   40,
        "basis": "5 pts per mph that 85th %ile speed exceeds 8 mph above posted limit (max 40 pts)",
        "cite":  "Part V–b–3",
    },
    {
        "id":    "volume",
        "label": "Volume",
        "max":   20,
        "basis": "ADT ÷ 250, up to a maximum of 20 pts",
        "cite":  "Part V–b–3",
    },
    {
        "id":    "crashes",
        "label": "Accident History",
        "max":   20,
        "basis": "5 pts per accident per year, up to a maximum of 20 pts",
        "cite":  "Part V–b–3",
    },
    {
        "id":    "school",
        "label": "School Route",
        "max":   10,
        "basis": "0 pts if NOT on school walking route; 10 pts if ON school walking route",
        "cite":  "Part V–b–3",
    },
    {
        "id":    "sidewalk",
        "label": "Sidewalks",
        "max":   10,
        "basis": "0 pts if continuous sidewalk EXISTS; 10 pts if NO continuous sidewalk",
        "cite":  "Part V–b–3",
    },
]
