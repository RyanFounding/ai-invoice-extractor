import streamlit as st
import pandas as pd
import os
import json
from google import genai
from pydantic import BaseModel, Field
from typing import List

# --- 1. PAGE SETUP & STYLE (FinTech Theme) ---
st.set_page_config(page_title="INKOS | Invoice Pipeline", page_icon="🧾", layout="wide")

# Custom CSS for a professional Banking/Finance aesthetic
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; } /* Clean, light finance background */
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-left: 5px solid #0052cc; }
    .stButton>button { background-color: #0052cc; color: white; border-radius: 8px; width: 100%; height: 3em; font-weight: bold; }
    div[data-testid="stExpander"] { border: 1px solid #e0e0e0; background-color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. HEADER SECTION ---
col_t, col_s = st.columns([3, 1])
with col_t:
    st.title("🧾 AI Financial Data Pipeline")
    st.caption("INKOS Intelligence Systems | Supply Chain Automation")

with col_s:
    st.metric("Model", "Gemini 2.5 Flash", delta="Optimized")

st.divider()

# API Check
if "GEMINI_API_KEY" not in os.environ:
    st.error("⚠️ API Key missing in Streamlit Secrets.")
    st.stop()

client = genai.Client()

# --- 3. THE DATA BLUEPRINT ---
class InvoiceItem(BaseModel):
    description: str
    quantity: float
    unit_price: float
    total_amount: float

class InvoiceData(BaseModel):
    vendor_name: str
    invoice_date: str
    total_amount_due: float
    currency: str
    items: List[InvoiceItem]

# --- 4. WORKFLOW ---
uploaded_file = st.file_uploader("Upload Vendor Invoice (PDF)", type=["pdf"])

if uploaded_file:
    # Sidebar for PDF Preview
    with st.sidebar:
        st.subheader("Document Preview")
        st.info("The AI is scanning this document for financial data points.")
    
    if st.button("Process Financial Data"):
        # Save temp file
        temp_path = f"temp_{uploaded_file.name}"
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
            
        # AI Logic
        gemini_file = client.files.upload(file=temp_path)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[gemini_file, "Extract all invoice data including line items."],
            config={'response_mime_type': 'application/json', 'response_schema': InvoiceData}
        )
        
        data = json.loads(response.text)
        
        # --- 5. SMART VISUALS ---
        st.success("Extraction Complete!")
        
        # Summary Row
        c1, c2, c3 = st.columns(3)
        c1.metric("Vendor", data['vendor_name'])
        c2.metric("Total Amount", f"{data['total_amount_due']} {data['currency']}")
        c3.metric("Line Items Found", len(data['items']))
        
        # Flatten and Display
        df = pd.DataFrame(data['items'])
        st.subheader("Standardized Data Output")
        st.dataframe(df, use_container_width=True)
        
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("⬇️ Export to ERP (CSV)", data=csv, file_name=f"processed_{data['vendor_name']}.csv")
        
        os.remove(temp_path)
