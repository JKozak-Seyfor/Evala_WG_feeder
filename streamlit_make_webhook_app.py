import json
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List

import pandas as pd
import requests
import streamlit as st


# Expected Streamlit secrets:
# MAKE_WEBHOOK_URL = "https://hook.eu2.make.com/..."
# MAKE_API_KEY = "..."                          # optional, sent as a header
# MAKE_API_KEY_HEADER = "X-API-Key"              # optional, defaults to X-API-Key


def get_secret(name: str, default: str | None = None) -> str | None:
    """Read a value from Streamlit secrets without exposing it in the UI."""
    try:
        value = st.secrets.get(name, default)
    except Exception:
        value = default

    if value is None:
        return None

    value = str(value).strip()
    return value or None


def json_safe(value: Any) -> Any:
    """Convert pandas/numpy/python values into JSON-safe values."""
    if pd.isna(value):
        return None

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, Decimal):
        return float(value)

    if hasattr(value, "item"):
        return value.item()

    return value


def dataframe_to_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    cleaned = df.copy()
    cleaned.columns = [str(col).strip() for col in cleaned.columns]

    records: List[Dict[str, Any]] = []

    for row in cleaned.to_dict(orient="records"):
        records.append({str(key): json_safe(value) for key, value in row.items()})

    return records


def load_excel(uploaded_file) -> Dict[str, pd.DataFrame]:
    sheets = pd.read_excel(uploaded_file, sheet_name=None)
    return {sheet_name: df for sheet_name, df in sheets.items()}


def build_payload(
    file_name: str,
    selected_sheet: str,
    records: List[Dict[str, Any]],
    include_metadata: bool,
) -> Dict[str, Any] | List[Dict[str, Any]]:
    if not include_metadata:
        return records

    return {
        "source": "streamlit_excel_upload",
        "file_name": file_name,
        "sheet_name": selected_sheet,
        "row_count": len(records),
        "sent_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "data": records,
    }


def build_headers(api_key: str | None, api_key_header: str | None) -> Dict[str, str]:
    headers = {"Content-Type": "application/json"}

    if api_key:
        headers[api_key_header or "X-API-Key"] = api_key

    return headers


def send_to_make(
    webhook_url: str,
    payload: Dict[str, Any] | List[Dict[str, Any]],
    api_key: str | None = None,
    api_key_header: str | None = None,
) -> requests.Response:
    response = requests.post(
        webhook_url,
        json=payload,
        timeout=30,
        headers=build_headers(api_key, api_key_header),
    )
    response.raise_for_status()
    return response


st.set_page_config(
    page_title="Excel -> Make webhook",
    page_icon="📤",
    layout="wide",
)

st.title("Excel -> Make webhook")
st.write("Nahrajte Excel, zkontrolujte data a odešlete je jako JSON na webhook v Make.")

webhook_url = get_secret("MAKE_WEBHOOK_URL")
api_key = get_secret("MAKE_API_KEY")
api_key_header = get_secret("MAKE_API_KEY_HEADER", "X-API-Key")

with st.sidebar:
    st.header("Nastavení")

    include_metadata = st.checkbox(
        "Zabalit data do objektu s metadaty",
        value=True,
    )

    send_only_previewed_rows = st.checkbox(
        "Odeslat pouze prvních N řádků",
        value=False,
    )

    preview_limit = st.number_input(
        "Počet řádků pro náhled/test",
        min_value=1,
        max_value=10_000,
        value=20,
        step=1,
    )

    st.divider()
    st.caption("Webhook a API klíč se načítají ze Streamlit Secrets a v aplikaci se nezobrazují.")
    st.write("Webhook:", "✅ načten" if webhook_url else "❌ chybí")
    st.write("API klíč:", "✅ načten" if api_key else "ℹ️ nepoužívá se")

if not webhook_url:
    st.error(
        "Chybí `MAKE_WEBHOOK_URL` ve Streamlit Secrets. "
        "Doplňte jej v nastavení aplikace nebo lokálně do `.streamlit/secrets.toml`."
    )
    st.stop()

uploaded_file = st.file_uploader(
    "Vyberte Excel soubor",
    type=["xlsx", "xls"],
)

if uploaded_file is None:
    st.info("Nahrajte Excel soubor. Aplikace následně zobrazí listy a připraví payload pro Make.")
    st.stop()

try:
    sheets = load_excel(uploaded_file)
except Exception as exc:
    st.error(f"Excel se nepodařilo načíst: {exc}")
    st.stop()

sheet_names = list(sheets.keys())

selected_sheet = st.selectbox(
    "List v Excelu",
    sheet_names,
)

df = sheets[selected_sheet]

st.subheader("Náhled dat")
st.caption(f"List: {selected_sheet} | Řádky: {len(df)} | Sloupce: {len(df.columns)}")
st.dataframe(df.head(int(preview_limit)), use_container_width=True)

records = dataframe_to_records(df)

if send_only_previewed_rows:
    records = records[: int(preview_limit)]

payload = build_payload(
    file_name=uploaded_file.name,
    selected_sheet=selected_sheet,
    records=records,
    include_metadata=include_metadata,
)

with st.expander("Zobrazit JSON payload"):
    st.code(
        json.dumps(payload, ensure_ascii=False, indent=2),
        language="json",
    )

col1, col2 = st.columns([1, 3])

with col1:
    send_clicked = st.button(
        "Odeslat na Make",
        type="primary",
    )

if send_clicked:
    if not records:
        st.warning("Vybraný list neobsahuje žádné řádky k odeslání.")
    else:
        try:
            response = send_to_make(
                webhook_url=webhook_url,
                payload=payload,
                api_key=api_key,
                api_key_header=api_key_header,
            )

            st.success(f"Odesláno. Make vrátil HTTP {response.status_code}.")

            if response.text:
                st.caption("Odpověď webhooku:")
                st.code(response.text[:5000])

        except requests.exceptions.RequestException as exc:
            st.error(f"Odeslání selhalo: {exc}")
