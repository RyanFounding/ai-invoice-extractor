import streamlit as st
import pandas as pd
import os
import json
from google import genai
from pydantic import BaseModel, Field
from typing import List

# --- 1. PAGE SETUP & STYLE (Total Sync) ---
st.set_page_config(page_title="INKOS | Invoice Pipeline", page_icon="🧾", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; } 
    div[data-testid="stMetric"] {
        background-color: #1f2937;
        border: 1px solid #374151;
        padding: 15px;
        border-radius: 10px;
    }
    h1, h2, h3, p, span, label { color: #ffffff !important; }
    .stButton>button {
        background-color: #00ffa2;
        color: #000000;
        border-radius: 8px;
        border: none;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. HEADER SECTION (Fixes Duplication) ---
col_title, col_stats = st.columns([4, 2])
with col_title:
    st.title("🧾 AI Financial Data Pipeline")
    st.caption("INKOS Intelligence Systems | Supply Chain Automation")

with col_stats:
    m1, m2 = st.columns(2)
    m1.metric("Engine", "Gemini 2.5")
    m2.metric("Status", "Active", delta="Ready")

st.divider()

# --- 2. HEADER SECTION (Separated Metrics) ---
col_title, col_stats = st.columns([4, 2])
with col_title:
    st.title("🧾 AI Financial Data Pipeline")
    st.caption("INKOS Intelligence Systems | Supply Chain Automation")

with col_stats:
    m1, m2 = st.columns(2)
    m1.metric("Engine", "Gemini 2.5")
    m2.metric("Status", "Active", delta="Ready")

st.divider()

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




