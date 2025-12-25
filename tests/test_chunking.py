from docintel.chunking import chunk_text

def test_chunk_text():
    text = "Hello world. " * 1000
    chunks = chunk_text(text, chunk_size=500, chunk_overlap=100)
    assert len(chunks) > 2
    assert all(c.strip() for c in chunks)

def test_chunk_overlap_guard():
    try:
        chunk_text("abc", chunk_size=10, chunk_overlap=10)
        assert False
    except ValueError:
        assert True
