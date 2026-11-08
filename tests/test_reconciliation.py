from __future__ import annotations

import pytest

from invoice_pipeline.reconciliation import reconcile
from invoice_pipeline.schemas import InvoiceData, LineItem


@pytest.mark.parametrize("fixture", ["aura_invoice", "stratos_invoice"])
def test_sample_invoices_reconcile(fixture: str, request: pytest.FixtureRequest) -> None:
    invoice: InvoiceData = request.getfixturevalue(fixture)

    assert reconcile(invoice) == []


def test_misread_line_total_is_flagged(aura_invoice: InvoiceData) -> None:
    aura_invoice.items[1].total_amount = 5722.50  # transposed digits

    checks = [issue.check for issue in reconcile(aura_invoice)]

    assert checks == ["line_total", "subtotal"]


def test_missing_adjustment_breaks_total(stratos_invoice: InvoiceData) -> None:
    stratos_invoice.adjustments.pop()  # model skipped the local surcharge

    [issue] = reconcile(stratos_invoice)

    assert issue.check == "total_due"
    assert issue.expected == 27126.07
    assert issue.found == 27314.88


def test_total_is_checked_from_line_items_when_no_subtotal() -> None:
    invoice = InvoiceData(
        vendor_name="Vendor",
        currency="EUR",
        items=[LineItem(description="Bolt", quantity=100, unit_price=0.25, total_amount=25.0)],
        total_amount_due=30.0,
    )

    [issue] = reconcile(invoice)

    assert issue.check == "total_due"
    assert issue.expected == 25.0


def test_rounding_within_a_cent_is_accepted(aura_invoice: InvoiceData) -> None:
    aura_invoice.total_amount_due = 12170.76

    assert reconcile(aura_invoice) == []


def test_non_iso_date_is_flagged(aura_invoice: InvoiceData) -> None:
    aura_invoice.invoice_date = "Feb 13, 2026"

    assert [i.check for i in reconcile(aura_invoice)] == ["invoice_date"]
