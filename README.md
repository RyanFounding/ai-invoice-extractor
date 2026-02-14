# 🧾 AI-Powered Invoice Data Pipeline
**Developed by INKOS**

An automated financial engineering tool designed to transform unstructured PDF invoices into structured, analysis-ready datasets.

### 🛠️ The Problem
In supply chain and logistics, manual data entry of vendor invoices is a major bottleneck. Accounts payable teams spend hours transcribing line items, tax details, and totals into ERP systems, leading to human error and operational delays.

### 💡 The Solution
This pipeline uses **Gemini 2.5 Flash** and **Pydantic** to instantly "read" any invoice. It doesn't just extract text; it understands the context, validates the financial math, and flattens complex line items into a clean CSV for Excel or SQL databases.

### 🚀 Live Demo
**Try it here:** [https://inkos-invoices.streamlit.app](https://inkos-invoices.streamlit.app)

### 📖 How to use
1. Launch the **Live Demo** link above.
2. Drag and drop any of the sample invoices (e.g., `invoice_1.pdf`) found in this repository.
3. The AI will extract the Vendor, Date, Line Items, and Totals.
4. Click the **"Download CSV"** button to export the structured data.

### 🏗️ Technical Stack
* **Language:** Python
* **AI Engine:** Google Gemini 2.5 Flash (Generative AI)
* **Validation:** Pydantic (Strict Schema Enforcement)
* **Frontend:** Streamlit (Web UI)
* **Data Handling:** Pandas
