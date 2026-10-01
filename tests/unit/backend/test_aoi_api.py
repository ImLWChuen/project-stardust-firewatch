from app.api.aoi import list_aois

def test_aoi_api():
    aois = list_aois()
    assert len(aois) > 0
