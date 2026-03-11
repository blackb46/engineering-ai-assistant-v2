"""
==============================================================================
DOCUMENT REGISTRY
==============================================================================
File: utils/document_registry.py
Purpose: Master registry of every document in the corpus.

This is the single source of truth for all document metadata.
Every other component in the system references this registry to:
  - Know what documents exist
  - Format proper legal/policy citations
  - Classify content type (municipal code vs internal policy)
  - Assign relevance tiers for retrieval weighting

HOW TO ADD A NEW DOCUMENT:
  1. Add a new entry to DOCUMENT_REGISTRY below
  2. Upload the file to Google Drive source_documents folder
  3. Re-run the corpus builder in Colab
  4. The entire system automatically picks up the new document

CONTENT TYPES:
  - municipal_code      : Official Brentwood Municipal Code chapters
  - engineering_policy  : Internal Engineering Department policy/guidance
  - subdivision_regs    : Subdivision regulations (Appendix A)
  - external_reference  : Referenced external standards (TDEC, AASHTO, etc.)

RELEVANCE TIERS:
  - primary      : Core engineering documents - always retrieved first
  - secondary    : Supporting regulatory documents - retrieved when relevant
  - supplemental : Complete code coverage - retrieved only when directly relevant

CITATION FORMATS:
  Municipal Code:
    "Brentwood Municipal Code, Chapter 56 — Stormwater Management, Sec. 56-43"

  Engineering Policy:
    "City of Brentwood Engineering Dept. Policy Manual — Foundation Surveys"

  Subdivision Regulations:
    "Brentwood Subdivision Regulations, Appendix A, Article IV — Design Standards"
==============================================================================
"""

# ==============================================================================
# MASTER DOCUMENT REGISTRY
# ==============================================================================
# Each entry contains:
#   filename        : Exact filename in Google Drive source_documents folder
#   doc_id          : Short unique identifier used internally
#   display_name    : Human-readable name for citations and UI display
#   short_name      : Abbreviated name for inline footnote citations
#   content_type    : Classification of document type
#   relevance_tier  : primary / secondary / supplemental
#   chapter_num     : Numeric chapter for sorting (0 = non-chapter docs)
#   chapter_title   : Full chapter title as it appears in the code
#   citation_prefix : Beginning of every citation from this document
#   subfolder       : Which subfolder in source_documents/ this file lives in
#   description     : Brief description of what this document covers

DOCUMENT_REGISTRY = {

    # ==========================================================================
    # ENGINEERING POLICY MANUAL (Internal)
    # ==========================================================================
    "engineering_policy_manual": {
        "filename":         "Engineering_Policy_Manual.docx",
        "doc_id":           "EPM",
        "display_name":     "City of Brentwood Engineering Dept. Policy Manual",
        "short_name":       "Engineering Policy Manual",
        "content_type":     "engineering_policy",
        "relevance_tier":   "primary",
        "chapter_num":      0,
        "chapter_title":    "Engineering Department Policy Manual",
        "citation_prefix":  "City of Brentwood Engineering Dept. Policy Manual",
        "subfolder":        "engineering_manual",
        "description":      "Internal engineering department policies, procedures, "
                            "and gap-filling guidance where the Municipal Code does "
                            "not specifically address a topic."
    },

    # ==========================================================================
    # PRIMARY ENGINEERING CHAPTERS
    # These are the chapters most directly relevant to engineering review,
    # site development, stormwater, zoning, and subdivision work.
    # ==========================================================================

    "ch56_stormwater": {
        "filename":         "Chapter_56___STORMWATER_MANAGEMENT__EROSION_CONTROL_AND_FLOOD_DAMAGE_PREVENTION.docx",
        "doc_id":           "CH56",
        "display_name":     "Brentwood Municipal Code, Chapter 56 — Stormwater Management, Erosion Control and Flood Damage Prevention",
        "short_name":       "Municipal Code Ch. 56",
        "content_type":     "municipal_code",
        "relevance_tier":   "primary",
        "chapter_num":      56,
        "chapter_title":    "Stormwater Management, Erosion Control and Flood Damage Prevention",
        "citation_prefix":  "Brentwood Municipal Code, Chapter 56 — Stormwater Management",
        "subfolder":        "municipal_code",
        "description":      "Stormwater management standards, erosion control requirements, "
                            "flood damage prevention, detention/retention requirements, "
                            "illicit discharge prohibitions, and long-term maintenance agreements."
    },

    "ch78_zoning": {
        "filename":         "Chapter_78___ZONING.docx",
        "doc_id":           "CH78",
        "display_name":     "Brentwood Municipal Code, Chapter 78 — Zoning",
        "short_name":       "Municipal Code Ch. 78",
        "content_type":     "municipal_code",
        "relevance_tier":   "primary",
        "chapter_num":      78,
        "chapter_title":    "Zoning",
        "citation_prefix":  "Brentwood Municipal Code, Chapter 78 — Zoning",
        "subfolder":        "municipal_code",
        "description":      "Zoning districts, setback requirements, lot coverage, building "
                            "envelopes, overlay districts (HP Hillside Protection), use "
                            "regulations, residential driveway standards, fence regulations, "
                            "tree management, retaining walls, and site development standards."
    },

    "ch58_streets": {
        "filename":         "Chapter_58___STREETS__SIDEWALKS_AND_OTHER_PUBLIC_PLACES.docx",
        "doc_id":           "CH58",
        "display_name":     "Brentwood Municipal Code, Chapter 58 — Streets, Sidewalks and Other Public Places",
        "short_name":       "Municipal Code Ch. 58",
        "content_type":     "municipal_code",
        "relevance_tier":   "primary",
        "chapter_num":      58,
        "chapter_title":    "Streets, Sidewalks and Other Public Places",
        "citation_prefix":  "Brentwood Municipal Code, Chapter 58 — Streets, Sidewalks and Other Public Places",
        "subfolder":        "municipal_code",
        "description":      "Right-of-way standards, easement obstruction rules, driveway "
                            "culvert requirements, sidewalk standards, sight distance "
                            "requirements, and public place regulations."
    },

    "appendix_a": {
        "filename":         "APPENDIX_A___SUBDIVISION_REGULATIONS.docx",
        "doc_id":           "APPA",
        "display_name":     "Brentwood Subdivision Regulations, Appendix A",
        "short_name":       "Subdivision Regulations",
        "content_type":     "subdivision_regs",
        "relevance_tier":   "primary",
        "chapter_num":      0,
        "chapter_title":    "Subdivision Regulations",
        "citation_prefix":  "Brentwood Subdivision Regulations, Appendix A",
        "subfolder":        "municipal_code",
        "description":      "Subdivision design standards, plat requirements, street design, "
                            "lot layout, infrastructure standards, drainage easements, "
                            "and development approval procedures."
    },

    # ==========================================================================
    # SECONDARY ENGINEERING CHAPTERS
    # Supporting regulatory documents retrieved when relevant to the query.
    # ==========================================================================

    "ch14_buildings": {
        "filename":         "Chapter_14___BUILDINGS_AND_BUILDING_REGULATIONS.docx",
        "doc_id":           "CH14",
        "display_name":     "Brentwood Municipal Code, Chapter 14 — Buildings and Building Regulations",
        "short_name":       "Municipal Code Ch. 14",
        "content_type":     "municipal_code",
        "relevance_tier":   "secondary",
        "chapter_num":      14,
        "chapter_title":    "Buildings and Building Regulations",
        "citation_prefix":  "Brentwood Municipal Code, Chapter 14 — Buildings and Building Regulations",
        "subfolder":        "municipal_code",
        "description":      "Building permits, construction standards, inspections, "
                            "certificates of occupancy, and building code requirements."
    },

    "ch24_emergency": {
        "filename":         "Chapter_24___EMERGENCY_SERVICES.docx",
        "doc_id":           "CH24",
        "display_name":     "Brentwood Municipal Code, Chapter 24 — Emergency Services",
        "short_name":       "Municipal Code Ch. 24",
        "content_type":     "municipal_code",
        "relevance_tier":   "secondary",
        "chapter_num":      24,
        "chapter_title":    "Emergency Services",
        "citation_prefix":  "Brentwood Municipal Code, Chapter 24 — Emergency Services",
        "subfolder":        "municipal_code",
        "description":      "Emergency vehicle access requirements, fire lane standards, "
                            "and emergency services infrastructure requirements."
    },

    "ch26_fire": {
        "filename":         "Chapter_26___FIRE_PREVENTION_AND_PROTECTION.docx",
        "doc_id":           "CH26",
        "display_name":     "Brentwood Municipal Code, Chapter 26 — Fire Prevention and Protection",
        "short_name":       "Municipal Code Ch. 26",
        "content_type":     "municipal_code",
        "relevance_tier":   "secondary",
        "chapter_num":      26,
        "chapter_title":    "Fire Prevention and Protection",
        "citation_prefix":  "Brentwood Municipal Code, Chapter 26 — Fire Prevention and Protection",
        "subfolder":        "municipal_code",
        "description":      "Fire flow requirements, sprinkler system mandates, fire "
                            "access road standards, and fire prevention requirements "
                            "affecting site and building design."
    },

    "ch30_health": {
        "filename":         "Chapter_30___HEALTH_AND_SANITATION.docx",
        "doc_id":           "CH30",
        "display_name":     "Brentwood Municipal Code, Chapter 30 — Health and Sanitation",
        "short_name":       "Municipal Code Ch. 30",
        "content_type":     "municipal_code",
        "relevance_tier":   "secondary",
        "chapter_num":      30,
        "chapter_title":    "Health and Sanitation",
        "citation_prefix":  "Brentwood Municipal Code, Chapter 30 — Health and Sanitation",
        "subfolder":        "municipal_code",
        "description":      "On-site sewage disposal, septic system standards for lots "
                            "outside sewer service area, and sanitation requirements."
    },

    "ch50_planning": {
        "filename":         "Chapter_50___PLANNING.docx",
        "doc_id":           "CH50",
        "display_name":     "Brentwood Municipal Code, Chapter 50 — Planning",
        "short_name":       "Municipal Code Ch. 50",
        "content_type":     "municipal_code",
        "relevance_tier":   "secondary",
        "chapter_num":      50,
        "chapter_title":    "Planning",
        "citation_prefix":  "Brentwood Municipal Code, Chapter 50 — Planning",
        "subfolder":        "municipal_code",
        "description":      "Development review procedures, planning commission authority, "
                            "board of zoning appeals, variance procedures, concept plans, "
                            "preliminary plat requirements, and plan submittal standards."
    },

    "ch66_traffic": {
        "filename":         "Chapter_66___TRAFFIC_AND_VEHICLES.docx",
        "doc_id":           "CH66",
        "display_name":     "Brentwood Municipal Code, Chapter 66 — Traffic and Vehicles",
        "short_name":       "Municipal Code Ch. 66",
        "content_type":     "municipal_code",
        "relevance_tier":   "secondary",
        "chapter_num":      66,
        "chapter_title":    "Traffic and Vehicles",
        "citation_prefix":  "Brentwood Municipal Code, Chapter 66 — Traffic and Vehicles",
        "subfolder":        "municipal_code",
        "description":      "Traffic impact standards, road access requirements, sight "
                            "distance regulations, traffic control devices, and vehicle "
                            "access standards affecting site development."
    },

    "ch70_utilities": {
        "filename":         "Chapter_70___UTILITIES.docx",
        "doc_id":           "CH70",
        "display_name":     "Brentwood Municipal Code, Chapter 70 — Utilities",
        "short_name":       "Municipal Code Ch. 70",
        "content_type":     "municipal_code",
        "relevance_tier":   "secondary",
        "chapter_num":      70,
        "chapter_title":    "Utilities",
        "citation_prefix":  "Brentwood Municipal Code, Chapter 70 — Utilities",
        "subfolder":        "municipal_code",
        "description":      "Water and sewer line standards, utility easement requirements, "
                            "service connection standards, and infrastructure requirements "
                            "affecting site plan approval."
    },

    # ==========================================================================
    # SUPPLEMENTAL CHAPTERS
    # Complete code coverage. Retrieved only when directly relevant to a query.
    # Low retrieval weight - will not interfere with engineering-focused queries.
    # ==========================================================================

    "ch1_general": {
        "filename":         "Chapter_1___GENERAL_PROVISIONS.docx",
        "doc_id":           "CH01",
        "display_name":     "Brentwood Municipal Code, Chapter 1 — General Provisions",
        "short_name":       "Municipal Code Ch. 1",
        "content_type":     "municipal_code",
        "relevance_tier":   "supplemental",
        "chapter_num":      1,
        "chapter_title":    "General Provisions",
        "citation_prefix":  "Brentwood Municipal Code, Chapter 1 — General Provisions",
        "subfolder":        "municipal_code",
        "description":      "General code provisions, definitions, and administrative rules."
    },

    "ch2_administration": {
        "filename":         "Chapter_2___ADMINISTRATION.docx",
        "doc_id":           "CH02",
        "display_name":     "Brentwood Municipal Code, Chapter 2 — Administration",
        "short_name":       "Municipal Code Ch. 2",
        "content_type":     "municipal_code",
        "relevance_tier":   "supplemental",
        "chapter_num":      2,
        "chapter_title":    "Administration",
        "citation_prefix":  "Brentwood Municipal Code, Chapter 2 — Administration",
        "subfolder":        "municipal_code",
        "description":      "City administration, departments, and organizational structure."
    },

    "ch6_alcohol": {
        "filename":         "Chapter_6___ALCOHOLIC_BEVERAGES.docx",
        "doc_id":           "CH06",
        "display_name":     "Brentwood Municipal Code, Chapter 6 — Alcoholic Beverages",
        "short_name":       "Municipal Code Ch. 6",
        "content_type":     "municipal_code",
        "relevance_tier":   "supplemental",
        "chapter_num":      6,
        "chapter_title":    "Alcoholic Beverages",
        "citation_prefix":  "Brentwood Municipal Code, Chapter 6 — Alcoholic Beverages",
        "subfolder":        "municipal_code",
        "description":      "Alcoholic beverage licensing and regulations."
    },

    "ch10_animals": {
        "filename":         "Chapter_10___ANIMALS.docx",
        "doc_id":           "CH10",
        "display_name":     "Brentwood Municipal Code, Chapter 10 — Animals",
        "short_name":       "Municipal Code Ch. 10",
        "content_type":     "municipal_code",
        "relevance_tier":   "supplemental",
        "chapter_num":      10,
        "chapter_title":    "Animals",
        "citation_prefix":  "Brentwood Municipal Code, Chapter 10 — Animals",
        "subfolder":        "municipal_code",
        "description":      "Animal control regulations."
    },

    "ch18_businesses": {
        "filename":         "Chapter_18___BUSINESSES.docx",
        "doc_id":           "CH18",
        "display_name":     "Brentwood Municipal Code, Chapter 18 — Businesses",
        "short_name":       "Municipal Code Ch. 18",
        "content_type":     "municipal_code",
        "relevance_tier":   "supplemental",
        "chapter_num":      18,
        "chapter_title":    "Businesses",
        "citation_prefix":  "Brentwood Municipal Code, Chapter 18 — Businesses",
        "subfolder":        "municipal_code",
        "description":      "Business licensing and commercial regulations."
    },

    "ch20_cable": {
        "filename":         "Chapter_20___CABLE_COMMUNICATIONS.docx",
        "doc_id":           "CH20",
        "display_name":     "Brentwood Municipal Code, Chapter 20 — Cable Communications",
        "short_name":       "Municipal Code Ch. 20",
        "content_type":     "municipal_code",
        "relevance_tier":   "supplemental",
        "chapter_num":      20,
        "chapter_title":    "Cable Communications",
        "citation_prefix":  "Brentwood Municipal Code, Chapter 20 — Cable Communications",
        "subfolder":        "municipal_code",
        "description":      "Cable communications franchise and regulations."
    },

    "ch22_court": {
        "filename":         "Chapter_22___COURT.docx",
        "doc_id":           "CH22",
        "display_name":     "Brentwood Municipal Code, Chapter 22 — Court",
        "short_name":       "Municipal Code Ch. 22",
        "content_type":     "municipal_code",
        "relevance_tier":   "supplemental",
        "chapter_num":      22,
        "chapter_title":    "Court",
        "citation_prefix":  "Brentwood Municipal Code, Chapter 22 — Court",
        "subfolder":        "municipal_code",
        "description":      "Municipal court procedures and regulations."
    },

    "ch34_law_enforcement": {
        "filename":         "Chapter_34___LAW_ENFORCEMENT.docx",
        "doc_id":           "CH34",
        "display_name":     "Brentwood Municipal Code, Chapter 34 — Law Enforcement",
        "short_name":       "Municipal Code Ch. 34",
        "content_type":     "municipal_code",
        "relevance_tier":   "supplemental",
        "chapter_num":      34,
        "chapter_title":    "Law Enforcement",
        "citation_prefix":  "Brentwood Municipal Code, Chapter 34 — Law Enforcement",
        "subfolder":        "municipal_code",
        "description":      "Law enforcement regulations and police department standards."
    },

    "ch38_library": {
        "filename":         "Chapter_38___LIBRARY.docx",
        "doc_id":           "CH38",
        "display_name":     "Brentwood Municipal Code, Chapter 38 — Library",
        "short_name":       "Municipal Code Ch. 38",
        "content_type":     "municipal_code",
        "relevance_tier":   "supplemental",
        "chapter_num":      38,
        "chapter_title":    "Library",
        "citation_prefix":  "Brentwood Municipal Code, Chapter 38 — Library",
        "subfolder":        "municipal_code",
        "description":      "Public library regulations."
    },

    "ch42_offenses": {
        "filename":         "Chapter_42___OFFENSES_AND_MISCELLANEOUS_PROVISIONS.docx",
        "doc_id":           "CH42",
        "display_name":     "Brentwood Municipal Code, Chapter 42 — Offenses and Miscellaneous Provisions",
        "short_name":       "Municipal Code Ch. 42",
        "content_type":     "municipal_code",
        "relevance_tier":   "supplemental",
        "chapter_num":      42,
        "chapter_title":    "Offenses and Miscellaneous Provisions",
        "citation_prefix":  "Brentwood Municipal Code, Chapter 42 — Offenses and Miscellaneous Provisions",
        "subfolder":        "municipal_code",
        "description":      "General offenses, nuisance provisions, and miscellaneous regulations."
    },

    "ch46_parks": {
        "filename":         "Chapter_46___PARKS_AND_RECREATION.docx",
        "doc_id":           "CH46",
        "display_name":     "Brentwood Municipal Code, Chapter 46 — Parks and Recreation",
        "short_name":       "Municipal Code Ch. 46",
        "content_type":     "municipal_code",
        "relevance_tier":   "supplemental",
        "chapter_num":      46,
        "chapter_title":    "Parks and Recreation",
        "citation_prefix":  "Brentwood Municipal Code, Chapter 46 — Parks and Recreation",
        "subfolder":        "municipal_code",
        "description":      "Parks and recreation facility regulations."
    },

    "ch54_solid_waste": {
        "filename":         "Chapter_54___SOLID_WASTE.docx",
        "doc_id":           "CH54",
        "display_name":     "Brentwood Municipal Code, Chapter 54 — Solid Waste",
        "short_name":       "Municipal Code Ch. 54",
        "content_type":     "municipal_code",
        "relevance_tier":   "supplemental",
        "chapter_num":      54,
        "chapter_title":    "Solid Waste",
        "citation_prefix":  "Brentwood Municipal Code, Chapter 54 — Solid Waste",
        "subfolder":        "municipal_code",
        "description":      "Solid waste collection and disposal regulations."
    },

    "ch62_taxation": {
        "filename":         "Chapter_62___TAXATION.docx",
        "doc_id":           "CH62",
        "display_name":     "Brentwood Municipal Code, Chapter 62 — Taxation",
        "short_name":       "Municipal Code Ch. 62",
        "content_type":     "municipal_code",
        "relevance_tier":   "supplemental",
        "chapter_num":      62,
        "chapter_title":    "Taxation",
        "citation_prefix":  "Brentwood Municipal Code, Chapter 62 — Taxation",
        "subfolder":        "municipal_code",
        "description":      "Local taxation regulations."
    },

    "ch74_vehicles_hire": {
        "filename":         "Chapter_74___VEHICLES_FOR_HIRE.docx",
        "doc_id":           "CH74",
        "display_name":     "Brentwood Municipal Code, Chapter 74 — Vehicles for Hire",
        "short_name":       "Municipal Code Ch. 74",
        "content_type":     "municipal_code",
        "relevance_tier":   "supplemental",
        "chapter_num":      74,
        "chapter_title":    "Vehicles for Hire",
        "citation_prefix":  "Brentwood Municipal Code, Chapter 74 — Vehicles for Hire",
        "subfolder":        "municipal_code",
        "description":      "Taxi, rideshare, and vehicle for hire regulations."
    },
}


# ==============================================================================
# REGISTRY HELPER FUNCTIONS
# ==============================================================================
# These functions are used by the corpus builder and RAG engine to look up
# document metadata without having to search through the registry manually.

def get_document_by_filename(filename):
    """
    Look up a document registry entry by its filename.

    Args:
        filename (str): The exact filename to look up

    Returns:
        dict: The registry entry, or None if not found
    """
    for doc_key, doc_info in DOCUMENT_REGISTRY.items():
        if doc_info["filename"] == filename:
            return doc_info
    return None


def get_document_by_id(doc_id):
    """
    Look up a document registry entry by its short doc_id.

    Args:
        doc_id (str): The doc_id to look up (e.g. 'CH56', 'EPM')

    Returns:
        dict: The registry entry, or None if not found
    """
    for doc_key, doc_info in DOCUMENT_REGISTRY.items():
        if doc_info["doc_id"] == doc_id:
            return doc_info
    return None


def get_documents_by_tier(tier):
    """
    Get all documents in a given relevance tier.

    Args:
        tier (str): 'primary', 'secondary', or 'supplemental'

    Returns:
        list: List of registry entries matching the tier
    """
    return [
        doc_info for doc_info in DOCUMENT_REGISTRY.values()
        if doc_info["relevance_tier"] == tier
    ]


def get_documents_by_content_type(content_type):
    """
    Get all documents of a given content type.

    Args:
        content_type (str): 'municipal_code', 'engineering_policy',
                            'subdivision_regs', or 'external_reference'

    Returns:
        list: List of registry entries matching the content type
    """
    return [
        doc_info for doc_info in DOCUMENT_REGISTRY.values()
        if doc_info["content_type"] == content_type
    ]


def format_citation(doc_info, section_number=None, section_title=None):
    """
    Format a complete citation string for a document.

    This is called by the RAG engine when building footnotes.
    The section_number and section_title come from chunk metadata.

    Args:
        doc_info (dict)       : Registry entry for the document
        section_number (str)  : Section number e.g. '56-43' (optional)
        section_title (str)   : Section title e.g. 'Long-term maintenance' (optional)

    Returns:
        str: Formatted citation string ready for display

    Examples:
        Municipal code with section:
            "Brentwood Municipal Code, Chapter 56 — Stormwater Management, Sec. 56-43"

        Municipal code without section:
            "Brentwood Municipal Code, Chapter 56 — Stormwater Management"

        Engineering policy with section title:
            "City of Brentwood Engineering Dept. Policy Manual — Foundation Surveys"

        Engineering policy without section title:
            "City of Brentwood Engineering Dept. Policy Manual"
    """
    base = doc_info["citation_prefix"]

    # For municipal code and subdivision regs, append section number if available
    if doc_info["content_type"] in ("municipal_code", "subdivision_regs"):
        if section_number:
            citation = f"{base}, Sec. {section_number}"
            if section_title:
                citation += f" — {section_title}"
        else:
            citation = base

    # For engineering policy, append section title if available
    elif doc_info["content_type"] == "engineering_policy":
        if section_title:
            citation = f"{base} — {section_title}"
        else:
            citation = base

    # For external references, just use the prefix
    else:
        citation = base

    return citation


def get_all_filenames():
    """
    Get a list of all filenames in the registry.
    Used by the corpus builder to know which files to process.

    Returns:
        list: List of (filename, subfolder, doc_id) tuples
    """
    return [
        (
            doc_info["filename"],
            doc_info["subfolder"],
            doc_info["doc_id"]
        )
        for doc_info in DOCUMENT_REGISTRY.values()
    ]


def print_registry_summary():
    """
    Print a formatted summary of all registered documents.
    Used for verification and debugging.
    """
    print("=" * 70)
    print("DOCUMENT REGISTRY SUMMARY")
    print("=" * 70)

    tiers = ["primary", "secondary", "supplemental"]
    for tier in tiers:
        docs = get_documents_by_tier(tier)
        print(f"\n{tier.upper()} DOCUMENTS ({len(docs)}):")
        print("-" * 50)
        for doc in sorted(docs, key=lambda x: x["chapter_num"]):
            print(f"  [{doc['doc_id']}] {doc['short_name']}")
            print(f"       File: {doc['filename']}")
            print(f"       Type: {doc['content_type']}")
            print()

    total = len(DOCUMENT_REGISTRY)
    primary = len(get_documents_by_tier("primary"))
    secondary = len(get_documents_by_tier("secondary"))
    supplemental = len(get_documents_by_tier("supplemental"))

    print("=" * 70)
    print(f"TOTAL: {total} documents")
    print(f"  Primary:      {primary}")
    print(f"  Secondary:    {secondary}")
    print(f"  Supplemental: {supplemental}")
    print("=" * 70)


# ==============================================================================
# QUICK VERIFICATION
# Run this file directly to verify the registry is correct:
#   python utils/document_registry.py
# ==============================================================================
if __name__ == "__main__":
    print_registry_summary()

    # Verify all filenames are unique
    filenames = [d["filename"] for d in DOCUMENT_REGISTRY.values()]
    if len(filenames) != len(set(filenames)):
        print("⚠️  WARNING: Duplicate filenames detected in registry!")
    else:
        print(f"\n✅ All {len(filenames)} filenames are unique")

    # Verify all doc_ids are unique
    doc_ids = [d["doc_id"] for d in DOCUMENT_REGISTRY.values()]
    if len(doc_ids) != len(set(doc_ids)):
        print("⚠️  WARNING: Duplicate doc_ids detected in registry!")
    else:
        print(f"✅ All {len(doc_ids)} doc_ids are unique")

    # Test citation formatting
    print("\n=== CITATION FORMAT EXAMPLES ===")
    ch56 = get_document_by_id("CH56")
    epm = get_document_by_id("EPM")
    appa = get_document_by_id("APPA")

    print(format_citation(ch56, "56-43", "Stormwater system long-term operation and maintenance"))
    print(format_citation(epm, section_title="Foundation Surveys"))
    print(format_citation(appa, "IV-B", "Street Design Standards"))
    print(format_citation(ch56))
