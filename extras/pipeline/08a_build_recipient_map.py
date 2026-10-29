"""One-off builder for data/usg_recipient_map.csv (F4). Decisions are hand-made, by org and exact USAspending recipient name.
attribution: direct/partial = DPG is the org's (main) product; parent/host = DPG is a minor part of a large org or a host;
implementer = named related org that built/delivered the DPG for a funder. parent/host/implementer are pulled for foreign-aid agencies only.
"""
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
cand = pd.read_csv(ROOT / "data/usg_recipient_candidates.csv")

H, M, L = "high", "medium", "low"
# (org, role, attribution, recipient_name as in USAspending, confidence, reason)
ROWS = [
    # --- direct / partial: DPG is the org's product -> all agencies
    ("Medic (Medic Mobile Inc)", "owner", "direct", "MEDIC MOBILE, INC.", H, "legal name; HHS/USAID subawards fit global health work"),
    ("Dimagi Inc", "owner", "direct", "DIMAGI INC", H, "legal name; USAID/NIH awards fit CommCare"),
    ("Humanitarian OpenStreetMap Team", "owner", "direct", "HUMANITARIAN OPENSTREETMAP TEAM UNITED STATES INC", H, "exact legal name (EIN map); State/USAID awards fit"),
    ("Ushahidi", "owner", "direct", "USHAHIDI INC", H, "exact legal name; USAID/State awards fit"),
    ("VillageReach", "owner", "direct", "VILLAGEREACH", H, "exact legal name; USAID/State awards fit"),
    ("Jembi Health Systems NPC", "owner", "direct", "JEMBI HEALTH SYSTEMS", H, "legal name less NPC suffix; USAID/HHS awards fit"),
    ("The Tor Project", "owner", "direct", "THE TOR PROJECT INC.", H, "exact legal name; USAID/State/DoD awards fit"),
    ("Zenysis Technologies", "owner", "direct", "ZENYSIS TECHNOLOGIES INC.", H, "exact legal name; USAID subaward fits"),
    ("Piramal Swasthya Management and Research Institute", "owner", "direct", "PIRAMAL SWASTHYA MANAGEMENT AND RESEARCH INSTITUTE", H, "exact legal name; USAID awards fit"),
    ("National Institute of Urban Affairs (NIUA)", "owner", "direct", "NATIONAL INSTITUTE OF URBAN AFFAIRS", H, "exact name; USAID prime fits urban programme"),
    ("OpenMRS Inc", "owner", "direct", "OPENMRS INC.", H, "exact legal name; NSF subaward"),
    ("Open Source Hardware Association", "owner", "direct", "OPEN SOURCE HARDWARE ASSOCIATION", H, "exact legal name; NSF award"),
    ("Creative Commons", "owner", "direct", "CREATIVE COMMONS CORPORATION", H, "exact legal name (EIN map); IMLS award"),
    ("OpenMined Foundation", "owner", "direct", "OPENMINED FOUNDATION", H, "exact name; DHS award"),
    ("Open Knowledge Foundation", "owner", "direct", "OPEN KNOWLEDGE FOUNDATION", H, "exact name; USAID subaward"),
    ("The Alan Turing Institute", "owner", "direct", "THE ALAN TURING INSTITUTE", H, "exact name; DoD award"),
    ("WSO2 LLC", "owner", "direct", "WSO2 LLC", H, "exact legal name; DoD/Treasury awards are product sales, scored 1 at most"),
    ("iXsystems Inc", "owner", "direct", "IXSYSTEMS, INC.", H, "exact legal name; Commerce/DoD awards are product sales, scored 1 at most"),
    ("Wikimedia Foundation", "owner", "direct", "WIKIMEDIA FOUNDATION, INC.", H, "exact legal name (EIN map); HHS award"),
    ("Development Gateway", "owner", "partial", "DEVELOPMENT GATEWAY INC", H, "exact legal name (EIN map); USAID/USDA awards fit"),
    ("Digital Green", "owner", "partial", "DIGITAL GREEN FOUNDATION", H, "exact legal name (EIN map); USAID awards fit"),
    ("Digital Green Trust (India)", "related", "partial", "DIGITAL GREEN TRUST", M, "Indian affiliate named in owner map; USAID subawards fit"),
    ("DrivenData Inc", "owner", "direct", "DRIVENDATA, LLC", M, "Inc vs LLC suffix differs from owner map; NASA awards"),
    ("Ona Systems", "owner", "direct", "ONA SYSTEMS LLC", M, "suffix differs (LLC); State subaward"),
    ("Human Rights Measurement Initiative", "owner", "direct", "HUMAN RIGHTS MEASUREMENT INITIATIVE CHARITABLE TRUST", M, "legal form added to owner name; State awards fit"),
    # --- parent / host: minor part of a large org -> foreign-aid agencies only, sensitivity version
    ("IntraHealth International", "owner", "parent", "INTRAHEALTH INTERNATIONAL, INC.", H, "exact legal name (EIN map); USAID/CDC"),
    ("IntraHealth International", "owner", "parent", "INTRAHEALTH INTERNATIONAL INC.", H, "same org, punctuation variant, no UEI"),
    ("Management Sciences for Health", "owner", "parent", "MANAGEMENT SCIENCES FOR HEALTH, INC.", H, "exact legal name (EIN map)"),
    ("Management Sciences for Health", "owner", "parent", "MANAGEMENT SCIENCES FOR HEALTH, INC. (MSH)", H, "same org, variant"),
    ("PATH", "owner", "parent", "PATH", H, "exact legal name (EIN map)"),
    ("World Resources Institute", "owner", "parent", "WORLD RESOURCES INSTITUTE", H, "exact legal name (EIN map)"),
    ("MITRE Corporation", "owner", "parent", "THE MITRE CORPORATION", H, "exact legal name (EIN map)"),
    ("Mozilla Foundation", "owner", "parent", "MOZILLA FOUNDATION", H, "exact legal name (EIN map)"),
    ("Linux Foundation (Janssen Project)", "owner", "host", "LINUX FOUNDATION, THE", H, "exact legal name (EIN map)"),
    ("LF Charities (Linux Foundation)", "owner", "host", "LINUX FOUNDATION, THE", M, "LF Charities is a separate legal entity; parent Linux Foundation record used"),
    ("United Nations Foundation (host of Digital Impact Alliance)", "owner", "host", "UNITED NATIONS FOUNDATION INC", M, "UN Foundation is the legal host of DIAL (EIN map, D38)"),
    ("Emory University", "owner", "parent", "EMORY UNIVERSITY", H, "exact name"),
    ("University of Washington (I-TECH / DIGI)", "owner", "parent", "UNIVERSITY OF WASHINGTON", H, "exact name"),
    ("University of Texas at Austin (Intelligent Environments Lab)", "owner", "parent", "UNIVERSITY OF TEXAS AT AUSTIN", H, "exact name"),
    ("Stanford University (Digital Medic)", "owner", "parent", "THE LELAND STANFORD JUNIOR UNIVERSITY", M, "legal name of Stanford University"),
    ("Stanford University (Digital Medic)", "owner", "parent", "STANFORD UNIVERSITY", M, "trading name"),
    ("Columbia University (Columbia International eHealth Laboratory)", "owner", "parent", "THE TRUSTEES OF COLUMBIA UNIVERSITY IN THE CITY OF NEW YORK", M, "legal name of Columbia University"),
    ("University of Oslo (HISP Centre)", "owner", "parent", "UNIVERSITETET I OSLO", M, "Norwegian name of the University of Oslo"),
    ("Indian Institute of Science (IISc)", "owner", "parent", "INDIAN INSTITUTE OF SCIENCE", H, "exact name"),
    ("UNICEF", "owner", "parent", "UNICEF", H, "exact name"),
    ("UNICEF (Eastern Caribbean Area Office)", "owner", "parent", "UNICEF", H, "exact name; regional office of UNICEF"),
    ("UNICEF (Europe & Central Asia Regional Office)", "owner", "parent", "UNICEF", H, "exact name; regional office of UNICEF"),
    ("World Health Organization", "owner", "parent", "WORLD HEALTH ORGANIZATION", H, "exact name"),
    ("UNDP", "owner", "parent", "UNITED NATIONS DEVELOPMENT PROGRAMME", H, "full name"),
    ("UNDP", "owner", "parent", "UNITED NATIONS DEVELOPMENT PROGRAMME (UNDP)", H, "full name, variant"),
    ("UNIDO", "owner", "parent", "UNITED NATIONS INDUSTRIAL DEVELOPMENT ORGANIZATION (UNIDO)", H, "full name"),
    ("FAO", "owner", "parent", "FOOD AND AGRICULTURE ORGANIZATION OF THE UNITED NATIONS", H, "full legal name of FAO"),
    ("World Food Programme", "owner", "parent", "UNITED NATIONS WORLD FOOD PROGRAMME", M, "USAspending name variant of WFP"),
    ("World Food Programme", "owner", "parent", "WORLD FOOD PROGRAM", M, "name variant of WFP, no UEI"),
    ("WMO Regional Office for Africa", "owner", "parent", "WORLD METEOROLOGICAL ORGANIZATION", M, "regional office of WMO; recipient is the parent body"),
    ("Humanity & Inclusion", "owner", "parent", "HANDICAP INTERNATIONAL FRANCE", M, "former name of HI, French branch"),
    ("Humanity & Inclusion", "owner", "parent", "ASSOCIATION FEDERATION HANDICAP INTERNATIONAL", M, "former name of HI, federation"),
    ("Humanity & Inclusion", "owner", "parent", "HANDICAP INTERNATIONAL ASBL", M, "former name of HI, Belgian entity"),
    ("HI US", "related", "implementer", "HANDICAP INTERNATIONAL INC A/K/A HANDICAP INTERNATIONAL", M, "US entity of HI, named in owner map"),
    ("Asian Development Bank", "owner", "parent", "ASIAN DEVELOPMENT BANK", H, "exact name"),
    ("Inter-American Development Bank", "owner", "parent", "INTER-AMERICAN DEVELOPMENT BANK", H, "exact name"),
    ("Google", "owner", "parent", "GOOGLE LLC", H, "exact legal name; large for-profit, foreign-aid scope only"),
    ("Red Hat", "owner", "parent", "RED HAT, LLC", H, "exact legal name; large for-profit, foreign-aid scope only"),
    ("Johnson & Johnson", "owner", "parent", "JOHNSON & JOHNSON, INC.", H, "exact name; large for-profit, foreign-aid scope only"),
    # --- implementers named in the owner map (foreign-aid scope)
        ("Chemonics International", "owner", "parent", "CHEMONICS INTERNATIONAL, INC.", H, "declared owner of the Quantification Analytics Tool (D38); exact legal name; Quantification Analytics Tool is a small part of Chemonics, so foreign-aid scope"),
    ("Vital Strategies", "related", "implementer", "VITAL STRATEGIES, INC.", M, "named partner of Resolve to Save Lives; award total is org-wide"),
    ("Norwegian Refugee Council (NORCAP)", "related", "implementer", "NORWEGIAN REFUGEE COUNCIL (NRC) - STIFTELSEN FLYKTNINGHJELPEN", M, "NORCAP is NRC's deployment arm; award total is org-wide"),
    ("World Bank", "related", "implementer", "WORLD BANK, THE", M, "exact name; funder of Climate Action Data Trust"),
    ("GIZ (openIMIS Initiative)", "owner", "parent", "DEUTSCHE GESELLSCHAFT FUER INTERNATIONALE ZUSAMMENARBEIT (GIZ) GMBH", H, "exact legal name (umlaut spelling FUER); UEI WUJ5L1ULCJH9; 4 USAID prime awards (checked, missed by the earlier search)"),
    ("GIZ", "related", "implementer", "DEUTSCHE GESELLSCHAFT FUER INTERNATIONALE ZUSAMMENARBEIT (GIZ) GMBH", H, "exact legal name; GIZ is named as an implementer for OpenSPP, Prospect, SYSPIN and SORMAS"),
    # --- rejected: kept in the map as low so the decision is visible (never used)
    ("Acquia", "related", "implementer", "ACQUIA INC", L, "large for-profit tech related org; not searched (DESIGN B3)"),
    ("Microsoft", "related", "implementer", "MICROSOFT CORPORATION", L, "large for-profit tech related org; not searched (DESIGN B3)"),
    ("Thoughtworks", "related", "implementer", "THOUGHTWORKS, INC.", L, "large for-profit tech related org; not searched (DESIGN B3)"),
    ("Columbia University (Columbia International eHealth Laboratory)", "owner", "parent", "COLUMBIA UNIVERSITY", L, "ambiguous short name, one tiny State award; legal-name rows used instead"),
    ("UN Foundation", "related", "implementer", "SEAOHUN FOUNDATION", L, "different organisation (name overlap only)"),
    ("Element (New Vector Ltd)", "owner", "direct", "ELEMENT 84, INC", L, "different company"),
    ("Ona Systems", "owner", "direct", "AKONA SYSTEMS INC", L, "different company (name similarity only)"),
    ("Ona Systems", "owner", "direct", "SEDONA SYSTEMS", L, "different company (name similarity only)"),
    ("Pix (GIP)", "owner", "direct", "IPIX CORPORATION", L, "different company (name similarity only)"),
    ("SUSE", "owner", "direct", "ASUSE INCORPORATED", L, "different company (name similarity only)"),
    ("LibreCode (cooperative)", "owner", "direct", "LW COOPERATIVE", L, "different organisation (name similarity only)"),
    ("Infocomm Media Development Authority (IMDA)", "owner", "direct", "IMDAAD(LLC)", L, "different organisation (name similarity only)"),
    ("BMZ", "related", "implementer", "BMZK, INC", L, "different organisation (name similarity only)"),
]
rm = pd.DataFrame(ROWS, columns=["org", "role", "attribution", "recipient_name", "confidence", "reason"])

# attach evidence from the discovery run: UEI with most dollars for this exact name, plus totals
ev = (cand.groupby(["recipient_name", "uei"], dropna=False)
      .agg(n=("n_awards_seen", "sum"), amt=("amount_seen", "max"), agencies=("agencies", "first")).reset_index()
      .sort_values("amt", ascending=False).drop_duplicates("recipient_name"))
rm = rm.merge(ev.rename(columns={"n": "n_awards_seen", "amt": "amount_seen"}), on="recipient_name", how="left")
missing = rm[rm.n_awards_seen.isna() & rm.confidence.ne("low")]
if len(missing): print("NOT FOUND in candidates:", missing[["org", "recipient_name"]].to_string())
rm["uei"] = rm.uei.fillna("")
rm["reviewed"] = ""
rm.to_csv(ROOT / "data/usg_recipient_map.csv", index=False)
print(rm.confidence.value_counts().to_string())
print("orgs with a usable match:", rm[rm.confidence.isin([H, M])].org.nunique())
