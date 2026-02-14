import streamlit as st
import pandas as pd
import os
import json
from google import genai
from pydantic import BaseModel, Field
from typing import Optional, List

# --- 1. PAGE SETUP ---
st.set_page_config(page_title="AI Invoice Pipeline", page_icon="🧾")
st.title("🧾 AI-Powered Invoice Extractor")
st.write("Drag and drop a vendor invoice below. The AI will extract the data and flatten it for Excel/SQL analysis.")

# Check for API Key
if "GEMINI_API_KEY" not in os.environ:
    st.error("⚠️ GEMINI_API_KEY environment variable is not set. Please set it in your terminal.")
    st.stop()

client = genai.Client()

# --- 2. THE BLUEPRINT (Same as before!) ---
class LineItem(BaseModel):
    description: str = Field(description="The name or description of the product/service")
    quantity: Optional[float] = Field(default=None, description="Number of units purchased")
    unit_price: Optional[float] = Field(default=None, description="Price per single unit")
    line_total: Optional[float] = Field(default=None, description="Total price for this specific line item")

class InvoiceData(BaseModel):
    vendor_name: str = Field(description="The name of the company issuing the invoice")
    invoice_number: Optional[str] = Field(default=None, description="The unique invoice ID or number")
    date_issued: Optional[str] = Field(default=None, description="The date the invoice was created")
    items_purchased: List[LineItem] = Field(description="A list of all the individual items billed")
    tax_amount: Optional[float] = Field(default=None, description="The total tax applied")
    total_amount_due: Optional[float] = Field(default=None, description="The final total amount charged")
    currency: Optional[str] = Field(default="USD", description="The currency used")

# --- 3. THE USER INTERFACE ---
# Create a drag-and-drop file uploader on the website
uploaded_file = st.file_uploader("Upload a PDF Invoice", type=["pdf"])

if uploaded_file is not None:
    # Show a loading spinner while the AI thinks
    with st.spinner("Uploading and extracting data with Gemini 2.5 Flash..."):
        
        # Streamlit holds files in memory. We temporarily save it to disk so Gemini can read it.
        temp_pdf_path = "temp_upload.pdf"
        with open(temp_pdf_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
            
        # Send to AI
        gemini_file = client.files.upload(file=temp_pdf_path)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[gemini_file, "Extract the billing and financial information from this invoice. If a field is missing, leave it as null."],
            config={
                'response_mime_type': 'application/json',
                'response_schema': InvoiceData,
            },
        )
        
        # --- 4. FLATTEN & DISPLAY DATA ---
        data_dict = json.loads(response.text)
        flattened_data = []
        
        base_info = {
            "Vendor": data_dict.get("vendor_name"),
            "Invoice #": data_dict.get("invoice_number"),
            "Date": data_dict.get("date_issued"),
            "Tax": data_dict.get("tax_amount"),
            "Total": data_dict.get("total_amount_due"),
            "Currency": data_dict.get("currency")
        }
        
        items = data_dict.get("items_purchased", [])
        if len(items) > 0:
            for item in items:
                row = base_info.copy()
                row.update(item)
                flattened_data.append(row)
        else:
            row = base_info.copy()
            row.update({"description": None, "quantity": None, "unit_price": None, "line_total": None})
            flattened_data.append(row)
            
        # Clean up the temporary file
        os.remove(temp_pdf_path)
        
        st.success("Extraction Complete!")
        
        # Turn the data into a beautiful Pandas table and display it on the website!
        df = pd.DataFrame(flattened_data)
        st.dataframe(df, use_container_width=True)
        
        # --- 5. DOWNLOAD BUTTON ---
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="⬇️ Download Data as CSV",
            data=csv,
            file_name="extracted_invoice.csv",
            mime="text/csv",
        )