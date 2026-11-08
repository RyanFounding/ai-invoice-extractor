"""Streamlit front end for the invoice pipeline."""

from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from invoice_pipeline.extraction import GeminiInvoiceExtractor
from invoice_pipeline.pipeline import (
    InvoiceResult,
    line_items_frame,
    process_invoices,
    to_csv_bytes,
)

st.set_page_config(page_title="INKOS | Invoice Pipeline", layout="wide")
st.title("Invoice Data Pipeline")
st.write(
    "Upload vendor invoices as PDF. Each one is extracted into structured line items "
    "and checked for arithmetic consistency before export."
)

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    st.error("GEMINI_API_KEY is not set. Add it to the environment or to Streamlit secrets.")
    st.stop()

model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
interval = float(os.environ.get("REQUEST_INTERVAL_SECONDS", "4"))


@st.cache_resource
def get_extractor(key: str, model_name: str) -> GeminiInvoiceExtractor:
    return GeminiInvoiceExtractor(api_key=key, model=model_name)


def render_result(result: InvoiceResult) -> None:
    st.markdown(f"#### {result.source_file}")
    if result.invoice is None:
        st.error(f"Extraction failed: {result.error}")
        return

    inv = result.invoice
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Vendor", inv.vendor_name)
    c2.metric("Invoice", inv.invoice_number or "not found")
    c3.metric("Amount due", f"{inv.total_amount_due:,.2f} {inv.currency}")
    c4.metric("Line items", len(inv.items))

    if result.reconciled:
        st.success("Reconciled: line items, subtotal, adjustments and total agree.")
    else:
        st.warning("Needs review:\n\n" + "\n".join(f"- {i.message}" for i in result.issues))

    st.dataframe(pd.DataFrame([i.model_dump() for i in inv.items]), hide_index=True)
    if inv.adjustments:
        st.caption("Taxes, fees and discounts")
        st.dataframe(pd.DataFrame([a.model_dump() for a in inv.adjustments]), hide_index=True)


uploaded = st.file_uploader("Vendor invoices (PDF)", type=["pdf"], accept_multiple_files=True)

if uploaded and st.button("Process invoices", type="primary"):
    extractor = get_extractor(api_key, model)
    results: list[InvoiceResult] = []
    progress = st.progress(0.0, text="Starting...")

    files = ((f.name, f.getvalue()) for f in uploaded)
    for done, result in enumerate(process_invoices(files, extractor, interval), start=1):
        results.append(result)
        render_result(result)
        progress.progress(done / len(uploaded), text=f"Processed {done} of {len(uploaded)}")
    progress.empty()

    master = line_items_frame(results)
    st.divider()
    st.subheader("Combined line items")
    reconciled = sum(r.reconciled for r in results)
    st.write(
        f"{len(master)} line items from {sum(r.ok for r in results)} of {len(results)} invoices. "
        f"{reconciled} reconciled without issues."
    )
    if master.empty:
        st.error("No invoices were extracted successfully.")
    else:
        st.dataframe(master, hide_index=True)
        st.download_button(
            "Download combined CSV",
            data=to_csv_bytes(master),
            file_name="invoice_line_items.csv",
            mime="text/csv",
            type="primary",
        )
