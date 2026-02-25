import streamlit as st
import pandas as pd
import os
import json
import uuid
from google import genai
from pydantic import BaseModel
from typing import List

# --- 1. PAGE SETUP & STYLE (Perfect Sync) ---
st.set_page_config(page_title="INKOS | Invoice Pipeline", page_icon="🧾", layout="wide")

st.markdown("""
    <style>
    /* Dark Background matching your Industrial Tool */
    .stApp { background-color: #0e1117; } 
    
    /* Uniform Grey Metric Cards */
    div[data-testid="stMetric"] {
        background-color: #1f2937;
        border: 1px solid #374151;
        padding: 15px;
        border-radius: 10px;
    }
    
    /* Green Accent Button to match industrial theme */
    .stButton>button {
        background-color: #00ffa2;
        color: #000000;
        border-radius: 8px;
        border: none;
        font-weight: bold;
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] { background-color: #111827; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. HEADER SECTION (Instructional Text) ---
col_title, col_stats = st.columns([4, 2])
with col_title:
    st.title("🧾 AI Financial Data Pipeline")
    st.write("Drag and drop vendor invoices (PDF) below to extract financial line items.")

with col_stats:
    m1, m2 = st.columns(2)
    m1.metric("Engine", "Gemini 2.5")
    m2.metric("Status", "Active", delta="Ready")

st.divider()

# --- 3. CORE LOGIC ---
if "GEMINI_API_KEY" not in os.environ:
    st.error("⚠️ GEMINI_API_KEY environment variable is not set in Secrets.")
    st.stop()

client = genai.Client()

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

# --- 4. FILE UPLOADER WORKFLOW ---
# Added accept_multiple_files=True
uploaded_files = st.file_uploader("Upload Vendor Invoices (PDF)", type=["pdf"], accept_multiple_files=True)

if uploaded_files:
    with st.sidebar:
        st.subheader("Document Status")
        st.success(f"Files queued: {len(uploaded_files)}")
        st.info("System ready for batch financial extraction.")
    
    if st.button("🚀 Process Financial Data"):
        
        # Loop through the list of uploaded files
        for uploaded_file in uploaded_files:
            st.markdown(f"### Processing: {uploaded_file.name}")
            
            # Generate a safe, random filename so the SDK doesn't crash on foreign characters
            temp_path = f"temp_{uuid.uuid4().hex}.pdf" 
            
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
                
            try:
                with st.spinner(f"AI is analyzing {uploaded_file.name}..."):
                    gemini_file = client.files.upload(file=temp_path)
                    
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=[gemini_file, "Extract all invoice details including every line item."],
                        config={
                            'response_mime_type': 'application/json',
                            'response_schema': InvoiceData,
                        }
                    )
                    
                    data = json.loads(response.text)
                    
                    # --- 5. RESULTS DISPLAY (Per File) ---
                    st.success(f"Extraction Successful for {uploaded_file.name}")
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Vendor Identified", data['vendor_name'])
                    c2.metric("Total Value", f"{data['total_amount_due']} {data['currency']}")
                    c3.metric("Line Items", len(data['items']))
                    
                    df = pd.DataFrame(data['items'])
                    st.subheader(f"Standardized Line Items: {data['vendor_name']}")
                    st.dataframe(df, use_container_width=True)
                    
                    # Encode to UTF-8-SIG so Excel handles Cyrillic/Umlauts perfectly
                    csv = df.to_csv(index=False).encode('utf-8-sig')
                    
                    # Ensure unique keys for buttons generated inside a loop
                    st.download_button(
                        label=f"⬇️ Export {data['vendor_name']} Data",
                        data=csv,
                        file_name=f"INKOS_invoice_{data['vendor_name']}.csv",
                        mime="text/csv",
                        key=f"download_{uuid.uuid4().hex}" 
                    )
                    
                    st.divider() # Adds a nice visual break between invoices

            except Exception as e:
                st.error(f"An error occurred while processing {uploaded_file.name}: {e}")
                
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
