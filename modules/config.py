# PAGE XML
PAGE_XML_NAMESPACE = 'http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15'
PAGE_XML_NS = {'pc': PAGE_XML_NAMESPACE}

# Mapping: PAGE-XML-Regionstyp → EzDrama-Präfix
REGION_TYPE_PREFIX = {
    "header":         "#",
    "heading":        "##",
    "credit":         "@",
    "signature-mark": "$",
    "TOC-entry":      "",
    "paragraph":      "",
    "catch-word":     "^",
}

# Sprecher-Erkennung
SPEAKER_DOT_SEARCH_LIMIT = 13   # max. Zeichenindex, bis zu dem ein Punkt als Sprechermarker gilt
SPEAKER_MAX_DOTS_PER_LINE = 3   # max. Anzahl Punkte pro Zeile, die als Sprecher-Kandidaten gezählt werden

# Figurenextraktion
FIGURE_MAX_WORDS = 3            # max. Wörter pro Figurenname in der Dramatis Personae

# Ähnlichkeits-Schwellwerte für Sprecher-Validierung
SIMILARITY_THRESHOLD_HIGH = 0.75  # "wahrscheinlich Figur"
SIMILARITY_THRESHOLD_LOW  = 0.5   # "vielleicht Figur" / Schwellwert für automatisches Behalten

# Zeilengruppierung (PAGE2EzDrama)
LINE_GROUP_THRESHOLD_FACTOR = 0.5  # Anteil des medianen Zeilenabstands als Y-Toleranz

# TEI
TEI_NAMESPACE = "http://www.tei-c.org/ns/1.0"
TEI_SPECIAL_SYMBOLS = '@$^#<'

# Geschlechtserkennung (heuristisch)
FEMALE_SUFFIXES = (
    'a', 'e', 'ine', 'ene', 'ette', 'ett', 'elle',
    'ia', 'ie', 'ea', 'traud', 'gard', 'ique', 'ise',
)
