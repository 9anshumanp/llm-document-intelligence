from __future__ import annotations
from typing import Optional, Literal, List
from pydantic import BaseModel, Field

class ContractSchema(BaseModel):
    schema_name: Literal["contract"] = "contract"
    counterparty: Optional[str] = Field(default=None, description="Counterparty or vendor/customer name")
    effective_date: Optional[str] = Field(default=None, description="Contract effective date (ISO preferred)")
    end_date: Optional[str] = Field(default=None, description="Contract end/termination date (ISO preferred)")
    governing_law: Optional[str] = Field(default=None, description="Governing law/jurisdiction")
    payment_terms: Optional[str] = Field(default=None, description="Payment terms")
    obligations: List[str] = Field(default_factory=list, description="Key obligations/clauses")

class InvoiceSchema(BaseModel):
    schema_name: Literal["invoice"] = "invoice"
    vendor: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    currency: Optional[str] = None
    total_amount: Optional[float] = None
    tax_amount: Optional[float] = None
    line_items: List[str] = Field(default_factory=list)

SCHEMA_REGISTRY = {
    "contract": ContractSchema,
    "invoice": InvoiceSchema,
}
