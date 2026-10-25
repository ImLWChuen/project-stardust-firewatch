from app.api.aoi import list_aois

def test_aoi_api():
    """Verify the AOI listing endpoint returns at least one area of interest."""
    aois = list_aois()
    assert len(aois) > 0
