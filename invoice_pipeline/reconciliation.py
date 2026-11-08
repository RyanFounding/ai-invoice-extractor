"""Arithmetic checks on extracted invoices.

The model reads the numbers; this module checks that they agree with each
other. An invoice that does not reconcile is either misprinted or misread,
and in both cases it should go to a person before it reaches the ERP system.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from invoice_pipeline.schemas import InvoiceData

DEFAULT_TOLERANCE = 0.01


class ReconciliationIssue(BaseModel):
    check: str
    expected: float | None = None
    found: float | None = None
    message: str


def _differs(a: float, b: float, tolerance: float) -> bool:
    return abs(round(a - b, 2)) > tolerance


def reconcile(
    invoice: InvoiceData, tolerance: float = DEFAULT_TOLERANCE
) -> list[ReconciliationIssue]:
    issues: list[ReconciliationIssue] = []

    for index, item in enumerate(invoice.items, start=1):
        expected = round(item.quantity * item.unit_price, 2)
        if _differs(expected, item.total_amount, tolerance):
            issues.append(
                ReconciliationIssue(
                    check="line_total",
                    expected=expected,
                    found=item.total_amount,
                    message=(
                        f"Line {index} ({item.description}): {item.quantity} x "
                        f"{item.unit_price:,.2f} = {expected:,.2f}, "
                        f"but {item.total_amount:,.2f} is printed."
                    ),
                )
            )

    line_sum = round(sum(item.total_amount for item in invoice.items), 2)
    if invoice.subtotal is not None and _differs(line_sum, invoice.subtotal, tolerance):
        issues.append(
            ReconciliationIssue(
                check="subtotal",
                expected=line_sum,
                found=invoice.subtotal,
                message=(
                    f"Line items sum to {line_sum:,.2f}, "
                    f"but the subtotal is {invoice.subtotal:,.2f}."
                ),
            )
        )

    base = invoice.subtotal if invoice.subtotal is not None else line_sum
    expected_total = round(base + sum(a.amount for a in invoice.adjustments), 2)
    if _differs(expected_total, invoice.total_amount_due, tolerance):
        issues.append(
            ReconciliationIssue(
                check="total_due",
                expected=expected_total,
                found=invoice.total_amount_due,
                message=(
                    f"Subtotal plus adjustments is {expected_total:,.2f}, "
                    f"but the amount due is {invoice.total_amount_due:,.2f}."
                ),
            )
        )

    if invoice.invoice_date is not None:
        try:
            date.fromisoformat(invoice.invoice_date)
        except ValueError:
            issues.append(
                ReconciliationIssue(
                    check="invoice_date",
                    message=f"Invoice date {invoice.invoice_date!r} is not in YYYY-MM-DD format.",
                )
            )

    return issues
