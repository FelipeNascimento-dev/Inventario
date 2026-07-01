from datetime import date, time

# Fonte única dos locais de inventário (jul/2026).
# Usada por migrations, provisionamento e sincronização de liberação.
CRONOGRAMA_LOCAIS = [
    ("CD PAYTEC BARUERI", date(2026, 7, 6), date(2026, 7, 10), time(6, 0), time(16, 0)),
    ("Lab. Gertec", date(2026, 7, 6), date(2026, 7, 6), time(8, 0), time(18, 0)),
    ("Lab. Tectoy/PAX", date(2026, 7, 7), date(2026, 7, 8), time(7, 0), time(17, 0)),
    ("Lab. Ogea", date(2026, 7, 10), date(2026, 7, 10), time(7, 0), time(16, 0)),
    ("MT- Oires Cuiabá", date(2026, 7, 11), date(2026, 7, 11), time(7, 0), time(17, 0)),
    ("SP - MOBYPOINT - ZONA LESTE", date(2026, 7, 11), date(2026, 7, 11), time(7, 0), time(17, 0)),
    ("AG.2307_ CALHAU SÃO LUIS_CORNER", date(2026, 7, 6), date(2026, 7, 7), time(9, 0), time(16, 0)),
    ("SP - VIG CAMPINAS", date(2026, 7, 11), date(2026, 7, 11), time(7, 0), time(17, 0)),
    ("SE - FP LOGISTICA", date(2026, 7, 11), date(2026, 7, 11), time(7, 0), time(17, 0)),
    ("SP - PAYTEC FILIAL", date(2026, 7, 11), date(2026, 7, 11), time(7, 0), time(17, 0)),
]
