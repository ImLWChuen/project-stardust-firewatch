from app.api.hotspots import get_hotspots

def test_hotspot_api():
    """Verify the hotspots endpoint returns a count field."""
    res = get_hotspots()
    assert res["count"] == 0
