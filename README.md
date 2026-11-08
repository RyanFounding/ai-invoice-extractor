# Invoice Data Pipeline

Turns vendor invoice PDFs into structured line-item data and checks that each invoice adds up before it's exported.

Live demo: [insan-invoice-pipeline.streamlit.app](https://insan-invoice-pipeline.streamlit.app)

## Problem

Accounts payable teams retype invoice line items, taxes and totals into ERP systems by hand. It's slow, and the errors that matter most, like a transposed digit or a missing surcharge, are hard to spot by eye. Using an LLM to read invoices speeds this up, but it introduces a new risk: the model can misread a number, and nothing downstream catches it.

## Solution

Each invoice goes through two steps:

1. **Extraction.** Gemini reads the PDF and returns a strict schema: vendor, invoice number, date, currency, line items, subtotal, every tax, fee or discount, and the amount due.
2. **Reconciliation.** Python checks that the numbers agree: quantity times price equals each line total, line totals sum to the subtotal, and subtotal plus adjustments equals the amount due. Any invoice that fails is marked "needs review", with the exact discrepancy.

The result is one combined CSV of line items. Each row is tagged with its source invoice and whether that invoice reconciled, so it can go straight into Excel, SQL or an ERP import.

## Architecture

```
PDF uploads
    |
    v
extraction.py       PDF sent inline to Gemini with a response schema -> InvoiceData (validated)
    |
    v
reconciliation.py   line totals, subtotal, adjustments, total due, date format -> issues
    |
    v
pipeline.py         batch loop with per-file error isolation and rate limiting
    |               -> InvoiceResult per file -> combined line-item DataFrame -> CSV
    v
app.py              Streamlit UI
```

| Module | Responsibility |
|---|---|
| `schemas.py` | The invoice data contract. Field descriptions double as extraction instructions. |
| `extraction.py` | The model call, behind an `InvoiceExtractor` protocol so it can be replaced in tests or swapped for another provider. |
| `reconciliation.py` | Arithmetic checks. Pure functions, no I/O. |
| `pipeline.py` | Batch processing and export. Doesn't depend on Streamlit. |
| `app.py` | UI only. |

## Tech stack

| Choice | Why |
|---|---|
| Gemini 2.5 Flash | Reads PDFs directly, including layout, and supports a JSON response schema. Temperature 0 for repeatable output. |
| Pydantic v2 | One model defines the response schema, validates the model's output, and drives the export columns. |
| pandas | Flattens nested invoices into one row per line item. |
| Streamlit | Interactive UI with file upload and download, hosted for free on Community Cloud. |
| pytest, ruff, mypy (strict) | CI runs lint, type checks and tests on every push. |

## Key technical decisions

- **Model adjustments explicitly.** Real invoices have discounts, several tax lines and fees between the subtotal and the total. Both sample invoices would fail a naive "sum of lines equals total" check. Capturing each adjustment as a signed amount makes the arithmetic checkable.
- **Flag, don't fix.** When an invoice doesn't reconcile, the pipeline reports both the expected and the printed values. It never adjusts a number to make the totals agree.
- **Send PDFs inline.** An earlier version uploaded each PDF to Gemini's file storage and then deleted it. Sending the bytes with the request means no stored copy and no cleanup step to forget.
- **Isolate errors per file.** One unreadable invoice is reported and skipped; the rest of the batch still completes.
- **Testable without an API key.** The UI depends on the `InvoiceExtractor` protocol, and tests use a fake that returns the real figures from the sample invoices.

## Running locally

Requires Python 3.11 or newer.

```bash
git clone https://github.com/insan-sll/ai-invoice-extractor.git
cd ai-invoice-extractor
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env               # set GEMINI_API_KEY
export $(grep -v '^#' .env | xargs)
streamlit run app.py
```

Upload the PDFs in `samples/` to try it. Both should reconcile.

### Configuration

| Variable | Default | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | none | Required. On Streamlit Cloud, set it in the app's secrets. |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Model used for extraction. |
| `REQUEST_INTERVAL_SECONDS` | `4` | Pause between requests, which keeps the free tier under 15 requests per minute. |

## Testing

```bash
pytest           # reconciliation, batch pipeline and UI smoke tests; no API key needed
ruff check .
mypy
```

## Limitations

- One currency per invoice. There is no currency conversion.
- Reconciliation proves the extracted numbers agree with each other, not that they match the PDF. A misread that happens to stay consistent would pass. In practice that's rare, because one wrong digit usually breaks at least one check.
- Invoices over 20 MB exceed Gemini's inline request limit.
