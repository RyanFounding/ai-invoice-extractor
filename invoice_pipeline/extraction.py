"""Model-backed invoice extraction."""

from __future__ import annotations

from typing import Protocol

from pydantic import ValidationError

from invoice_pipeline.schemas import InvoiceData

EXTRACTION_PROMPT = (
    "Extract the invoice details, including every line item and every tax, fee, "
    "discount or surcharge listed between the subtotal and the amount due. "
    "Copy amounts exactly as printed."
)

MAX_PDF_BYTES = 20 * 1024 * 1024  # Gemini's limit for inline request data


class ExtractionError(RuntimeError):
    pass


class InvoiceExtractor(Protocol):
    def extract(self, pdf_bytes: bytes) -> InvoiceData: ...


class GeminiInvoiceExtractor:
    """Sends the PDF inline with the request.

    Inline data is not stored in Gemini's file service, so there is nothing to
    clean up afterwards and no copy of the invoice is left behind.
    """

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash") -> None:
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self._model = model

    def extract(self, pdf_bytes: bytes) -> InvoiceData:
        from google.genai import types

        if len(pdf_bytes) > MAX_PDF_BYTES:
            raise ExtractionError("PDF is larger than the 20 MB request limit.")
        contents: list[types.PartUnionDict] = [
            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
            types.Part.from_text(text=EXTRACTION_PROMPT),
        ]
        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=InvoiceData,
                    temperature=0.0,
                ),
            )
        except Exception as exc:
            raise ExtractionError(f"Model request failed: {exc}") from exc

        if not response.text:
            raise ExtractionError("Model returned an empty response.")
        try:
            return InvoiceData.model_validate_json(response.text)
        except ValidationError as exc:
            raise ExtractionError("Model output did not match the invoice schema.") from exc
