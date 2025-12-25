from docintel.postprocess import extract_json_object

def test_extract_json_object():
    s = 'noise {\n "a": 1, "b": [2,3] \n} tail'
    obj = extract_json_object(s)
    assert obj["a"] == 1
    assert obj["b"] == [2,3]
