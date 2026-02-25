import streamlit as st
import pandas as pd
import os
import json
import uuid
import time  # NEW: Imported for our rate-limit cooldown
from google import genai
from pydantic import BaseModel
from typing import List

# --- 1. PAGE SETUP & STYLE ---
st.set_page_config(page_title="INKOS | Invoice Pipeline", page_icon="🧾", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; } 
    div[data-testid="stMetric"] { background-color: #1f2937; border: 1px solid #374151; padding: 15px; border-radius: 10px; }
    .stButton>button { background-color: #00ffa2; color: #000000; border-radius: 8px; border: none; font-weight: bold; }
    section[data-testid="stSidebar"] { background-color: #111827; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. HEADER SECTION ---
col_title, col_stats = st.columns([4, 2])
with col_title:
    st.title("🧾 AI Financial Data Pipeline")
    st.write("Drag and drop vendor invoices (PDF) below to extract financial line items.")

with col_stats:
    m1, m2 = st.columns(2)
    m1.metric("Engine", "Gemini 2.5 Flash")
    m2.metric("Tier", "Free Tier", delta="Rate-Limited")

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
uploaded_files = st.file_uploader("Upload Vendor Invoices (PDF)", type=["pdf"], accept_multiple_files=True)

if uploaded_files:
    with st.sidebar:
        st.subheader("Document Status")
        st.success(f"Files queued: {len(uploaded_files)}")
        st.info("System ready for batch financial extraction.")
    
    if st.button("🚀 Process Financial Data"):
        
        master_invoice_data = [] 
        
        # Enumerate gives us the index (i) so we know when we hit the last file
        for i, uploaded_file in enumerate(uploaded_files):
            st.markdown(f"### Processing: {uploaded_file.name}")
            
            temp_path = f"temp_{uuid.uuid4().hex}.pdf" 
            gemini_file = None 
            
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
                    
                    # Tag items for the Master CSV
                    for item in data['items']:
                        item_with_context = item.copy()
                        item_with_context['Source_File'] = uploaded_file.name
                        item_with_context['Vendor_Name'] = data['vendor_name']
                        item_with_context['Invoice_Date'] = data['invoice_date']
                        item_with_context['Currency'] = data['currency']
                        master_invoice_data.append(item_with_context)
                    
                    st.success(f"Extraction Successful for {uploaded_file.name}")
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Vendor Identified", data['vendor_name'])
                    c2.metric("Total Value", f"{data['total_amount_due']} {data['currency']}")
                    c3.metric("Line Items", len(data['items']))
                    
                    df = pd.DataFrame(data['items'])
                    st.dataframe(df, use_container_width=True)
                    
                    csv = df.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        label=f"⬇️ Export {data['vendor_name']} Data",
                        data=csv,
                        file_name=f"INKOS_invoice_{data['vendor_name']}.csv",
                        mime="text/csv",
                        key=f"download_{uuid.uuid4().hex}" 
                    )

            except Exception as e:
                st.error(f"An error occurred while processing {uploaded_file.name}: {e}")
                
            finally:
                if gemini_file:
                    try:
                        client.files.delete(name=gemini_file.name)
                    except Exception:
                        pass
                if os.path.exists(temp_path):
                    os.remove(temp_path)

            # NEW: Free Tier Rate Limit Protection (15 RPM = 4 seconds per request)
            # We don't need to sleep after the very last file is processed
            if i < len(uploaded_files) - 1:
                with st.spinner("⏳ Cooling down for 4 seconds to respect API Free Tier limits..."):
                    time.sleep(4)
            
            st.divider()

        # --- 5. MASTER DATABASE EXPORT ---
        if master_invoice_data:
            st.markdown("## 📊 Master Financial Database")
            st.info(f"Successfully compiled {len(master_invoice_data)} total line items from {len(uploaded_files)} invoices.")
            
            master_df = pd.DataFrame(master_invoice_data)
            
            context_cols = ['Source_File', 'Vendor_Name', 'Invoice_Date', 'Currency']
            item_cols = [col for col in master_df.columns if col not in context_cols]
            master_df = master_df[context_cols + item_cols]
            
            st.dataframe(master_df, use_container_width=True)
            
            master_csv = master_df.to_csv(index=False).encode('utf-8-sig')
            
            st.download_button(
                label="⬇️ DOWNLOAD MASTER BATCH CSV",
                data=master_csv,
                file_name="INKOS_Master_Financial_Data.csv",
                mime="text/csv",
                type="primary",
                use_container_width=True
            )
