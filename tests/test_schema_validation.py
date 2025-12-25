from docintel.schemas import ContractSchema

def test_contract_schema_defaults():
    m = ContractSchema(counterparty="X")
    d = m.model_dump()
    assert d["counterparty"] == "X"
    assert isinstance(d["obligations"], list)
