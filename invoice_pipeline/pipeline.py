"""Batch processing and tabular export, independent of the UI."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass

import pandas as pd

from invoice_pipeline.extraction import ExtractionError, InvoiceExtractor
from invoice_pipeline.reconciliation import ReconciliationIssue, reconcile
from invoice_pipeline.schemas import InvoiceData

LINE_ITEM_COLUMNS = [
    "source_file",
    "vendor_name",
    "invoice_number",
    "invoice_date",
    "currency",
    "description",
    "quantity",
    "unit_price",
    "total_amount",
    "invoice_reconciled",
]


@dataclass(frozen=True)
class InvoiceResult:
    source_file: str
    invoice: InvoiceData | None = None
    issues: tuple[ReconciliationIssue, ...] = ()
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.invoice is not None

    @property
    def reconciled(self) -> bool:
        return self.ok and not self.issues


def process_invoices(
    files: Iterable[tuple[str, bytes]],
    extractor: InvoiceExtractor,
    interval_seconds: float = 0.0,
    sleep: Callable[[float], None] = time.sleep,
) -> Iterator[InvoiceResult]:
    """Extract and reconcile each file, yielding results as they complete.

    One bad file never stops the batch: its error is recorded and processing
    continues. ``interval_seconds`` spaces out requests to stay within API
    rate limits.
    """
    for index, (name, pdf_bytes) in enumerate(files):
        if index and interval_seconds > 0:
            sleep(interval_seconds)
        try:
            invoice = extractor.extract(pdf_bytes)
        except ExtractionError as exc:
            yield InvoiceResult(source_file=name, error=str(exc))
            continue
        yield InvoiceResult(source_file=name, invoice=invoice, issues=tuple(reconcile(invoice)))


def line_items_frame(results: Iterable[InvoiceResult]) -> pd.DataFrame:
    """One row per line item, tagged with its invoice's context, ready for Excel or SQL."""
    rows: list[dict[str, object]] = []
    for result in results:
        if result.invoice is None:
            continue
        inv = result.invoice
        for item in inv.items:
            rows.append(
                {
                    "source_file": result.source_file,
                    "vendor_name": inv.vendor_name,
                    "invoice_number": inv.invoice_number,
                    "invoice_date": inv.invoice_date,
                    "currency": inv.currency,
                    **item.model_dump(),
                    "invoice_reconciled": result.reconciled,
                }
            )
    return pd.DataFrame(rows, columns=LINE_ITEM_COLUMNS)


def to_csv_bytes(frame: pd.DataFrame) -> bytes:
    # utf-8-sig adds a BOM so Excel opens accented vendor names correctly
    return frame.to_csv(index=False).encode("utf-8-sig")
