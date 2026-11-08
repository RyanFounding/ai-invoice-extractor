from __future__ import annotations

import pandas as pd

from invoice_pipeline.extraction import ExtractionError
from invoice_pipeline.pipeline import (
    LINE_ITEM_COLUMNS,
    line_items_frame,
    process_invoices,
    to_csv_bytes,
)
from invoice_pipeline.schemas import InvoiceData


class FakeExtractor:
    def __init__(self, results: dict[bytes, InvoiceData | ExtractionError]) -> None:
        self.results = results

    def extract(self, pdf_bytes: bytes) -> InvoiceData:
        result = self.results[pdf_bytes]
        if isinstance(result, ExtractionError):
            raise result
        return result


def test_batch_continues_after_a_failure(
    aura_invoice: InvoiceData, stratos_invoice: InvoiceData
) -> None:
    extractor = FakeExtractor(
        {b"a": aura_invoice, b"bad": ExtractionError("schema mismatch"), b"s": stratos_invoice}
    )
    sleeps: list[float] = []

    results = list(
        process_invoices(
            [("a.pdf", b"a"), ("bad.pdf", b"bad"), ("s.pdf", b"s")],
            extractor,
            interval_seconds=4,
            sleep=sleeps.append,
        )
    )

    assert [r.ok for r in results] == [True, False, True]
    assert results[1].error == "schema mismatch"
    assert sleeps == [4, 4]  # between requests only, not before the first


def test_line_items_frame_tags_context_and_reconciliation(
    aura_invoice: InvoiceData, stratos_invoice: InvoiceData
) -> None:
    stratos_invoice.total_amount_due = 1.0
    extractor = FakeExtractor({b"a": aura_invoice, b"s": stratos_invoice})

    frame = line_items_frame(process_invoices([("a.pdf", b"a"), ("s.pdf", b"s")], extractor))

    assert list(frame.columns) == LINE_ITEM_COLUMNS
    assert len(frame) == 8
    by_file = frame.groupby("source_file")["invoice_reconciled"].all().to_dict()
    assert by_file == {"a.pdf": True, "s.pdf": False}
    assert frame.loc[0, "invoice_number"] == "8802"


def test_empty_batch_gives_empty_frame_with_columns() -> None:
    frame = line_items_frame([])

    assert frame.empty
    assert list(frame.columns) == LINE_ITEM_COLUMNS


def test_csv_has_excel_bom() -> None:
    csv = to_csv_bytes(pd.DataFrame({"vendor_name": ["Müller GmbH"]}))

    assert csv.startswith(b"\xef\xbb\xbf")
    assert "Müller GmbH" in csv.decode("utf-8-sig")
