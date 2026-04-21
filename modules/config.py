from typing import Final

# PAGE XML
PAGE_XML_NAMESPACE: Final[str] = 'http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15'
PAGE_XML_NS: Final[dict[str, str]] = {'pc': PAGE_XML_NAMESPACE}

# Mapping: PAGE-XML-Regionstyp → EzDrama-Präfix
REGION_TYPE_PREFIX: Final[dict[str, str]] = {
    "header":         "#",
    "heading":        "##",
    "credit":         "@",
    "signature-mark": "$",
    "TOC-entry":      "",
    "paragraph":      "",
    "catch-word":     "^",
}

# Sprecher-Erkennung
SPEAKER_DOT_SEARCH_LIMIT: Final[int] = 13   # max. Zeichenindex, bis zu dem ein Punkt als Sprechermarker gilt
SPEAKER_MAX_DOTS_PER_LINE: Final[int] = 3   # max. Anzahl Punkte pro Zeile, die als Sprecher-Kandidaten gezählt werden

# Figurenextraktion
FIGURE_MAX_WORDS: Final[int] = 3            # max. Wörter pro Figurenname in der Dramatis Personae

# Ähnlichkeits-Schwellwerte für Sprecher-Validierung
SIMILARITY_THRESHOLD_HIGH: Final[float] = 0.75  # "wahrscheinlich Figur"
SIMILARITY_THRESHOLD_LOW: Final[float]  = 0.5   # "vielleicht Figur" / Schwellwert für automatisches Behalten

# Zeilengruppierung (PAGE2EzDrama)
LINE_GROUP_THRESHOLD_FACTOR: Final[float] = 0.5  # Anteil des medianen Zeilenabstands als Y-Toleranz

# TEI
TEI_NAMESPACE: Final[str] = "http://www.tei-c.org/ns/1.0"
TEI_SPECIAL_SYMBOLS: Final[str] = '@$^#<'

# Geschlechtserkennung (heuristisch)
FEMALE_SUFFIXES: Final[tuple[str, ...]] = (
    'a', 'e', 'ine', 'ene', 'ette', 'ett', 'elle',
    'ia', 'ie', 'ea', 'traud', 'gard', 'ique', 'ise',
)
