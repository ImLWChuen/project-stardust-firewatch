from app.api.calendar import get_burning_calendar

def test_calendar_api():
    """Verify the burning calendar endpoint returns the requested AOI and year."""
    res = get_burning_calendar("kedah", 2026)
    assert res["aoi_id"] == "kedah"
    assert res["year"] == 2026
