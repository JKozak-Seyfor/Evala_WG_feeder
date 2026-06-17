# Streamlit aplikace: Excel -> Make webhook

## Spuštění lokálně

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements_streamlit_make.txt
streamlit run streamlit_make_webhook_app.py
```

## Co aplikace dělá

1. Nahraje Excel soubor (`.xlsx` nebo `.xls`).
2. Načte všechny listy a dovolí vybrat konkrétní list.
3. Zobrazí náhled dat.
4. Převede vybraný list na JSON.
5. Odešle JSON metodou `POST` na Make webhook.

## Výchozí payload

Aplikace standardně posílá objekt s metadaty:

```json
{
  "source": "streamlit_excel_upload",
  "file_name": "soubor.xlsx",
  "sheet_name": "WebinarGeek",
  "row_count": 13,
  "sent_at": "2026-06-17T12:00:00Z",
  "data": [
    {"Email": "...", "First name": "...", "Surname": "...", "Phone": 123, "IČO": 456}
  ]
}
```

V postranním panelu lze vypnout metadata a poslat pouze pole záznamů.
