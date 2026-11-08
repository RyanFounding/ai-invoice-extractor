from __future__ import annotations

import pytest

from invoice_pipeline.schemas import Adjustment, InvoiceData, LineItem


@pytest.fixture
def aura_invoice() -> InvoiceData:
    """Figures as printed on samples/invoice_aura_design.pdf (discount, tax and fee lines)."""
    return InvoiceData(
        vendor_name="Aura Design Group",
        invoice_number="8802",
        invoice_date="2026-02-13",
        currency="USD",
        items=[
            LineItem(
                description="Visual Identity & Logo Suite Expansion",
                quantity=12.0,
                unit_price=210.0,
                total_amount=2520.0,
            ),
            LineItem(
                description="UX/UI Wireframing (Mobile App Phase 2)",
                quantity=28.5,
                unit_price=185.0,
                total_amount=5272.5,
            ),
            LineItem(
                description="Motion Graphics for Social Media Ad Campaign",
                quantity=15.0,
                unit_price=225.0,
                total_amount=3375.0,
            ),
            LineItem(
                description="Consultation & Project Management Fees",
                quantity=5.0,
                unit_price=150.0,
                total_amount=750.0,
            ),
        ],
        subtotal=11917.50,
        adjustments=[
            Adjustment(label="Loyalty Discount (5%)", amount=-595.88),
            Adjustment(label="State Tax (6.5%)", amount=735.91),
            Adjustment(label="Federal Service Fee (1%)", amount=113.22),
        ],
        total_amount_due=12170.75,
    )


@pytest.fixture
def stratos_invoice() -> InvoiceData:
    """Figures as printed on samples/invoice_stratos_consulting.pdf (three tax lines)."""
    return InvoiceData(
        vendor_name="Stratos Consulting LLC",
        invoice_number="INV-2026-0043",
        invoice_date="2026-02-13",
        currency="USD",
        items=[
            LineItem(
                description="Phase 1: Advanced Systems Architecture",
                quantity=45.0,
                unit_price=275.0,
                total_amount=12375.0,
            ),
            LineItem(
                description="Custom Software Development (Module B)",
                quantity=1.0,
                unit_price=7800.0,
                total_amount=7800.0,
            ),
            LineItem(
                description="Cloud Infrastructure (AWS/Azure)",
                quantity=20.0,
                unit_price=190.0,
                total_amount=3800.0,
            ),
            LineItem(
                description="Premium Support & Maintenance",
                quantity=1.0,
                unit_price=1200.0,
                total_amount=1200.0,
            ),
        ],
        subtotal=25175.00,
        adjustments=[
            Adjustment(label="Sales Tax (State - 6.25%)", amount=1573.44),
            Adjustment(label="County Tax (1.50%)", amount=377.63),
            Adjustment(label="Local Surcharge (0.75%)", amount=188.81),
        ],
        total_amount_due=27314.88,
    )
