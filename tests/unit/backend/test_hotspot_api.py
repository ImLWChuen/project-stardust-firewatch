from app.api.hotspots import get_hotspots

def test_hotspot_api():
    res = get_hotspots()
    assert res["count"] == 0
