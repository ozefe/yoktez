"""URL constants for every YOK NTC endpoint the library calls."""

BASE = "https://tez.yok.gov.tr/UlusalTezMerkezi"

# Search endpoints
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
SEARCH = f"{BASE}/SearchTez"
RESULT = f"{BASE}/tezSorguSonucYeni.jsp"
RECENT = f"{BASE}/TezIslemleri"

# Per-thesis endpoints
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
METADATA = f"{BASE}/tezBilgiDetay.jsp"
ASSETS = f"{BASE}/getTezPdf.jsp"
PDF = f"{BASE}/TezGoster"
APPENDIX = f"{BASE}/EkGoster"

# Lookup endpoints (modern)
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
UNIVERSITIES = f"{BASE}/getUniversities.jsp"

# `tarama.jsp?ajax=getEnstitu|getABD|getAllEnstitu|getAllABD`
# The `ajax` query parameter on this base distinguishes queries.
TARAMA_AJAX = f"{BASE}/tarama.jsp"

# Lookup endpoints (legacy bulk dumps)
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
ALL_UNIVERSITIES_OLD = f"{BASE}/uniEkle.jsp"
ALL_INSTITUTES_OLD = f"{BASE}/ensEkle.jsp"
ALL_DIVISIONS_OLD = f"{BASE}/abdEkle.jsp"
ALL_SUBJECTS = f"{BASE}/konuEkle.jsp"
ALL_DEPARTMENTS = f"{BASE}/bolEkle.jsp"
ALL_SECTIONS = f"{BASE}/bilimDaliEkle.jsp"

# Keyword search
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
KEYWORDS_SEARCH = f"{BASE}/SearchDizin"
