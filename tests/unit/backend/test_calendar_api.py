from app.api.calendar import get_burning_calendar

def test_calendar_api():
    res = get_burning_calendar("kedah", 2026)
    assert res["aoi_id"] == "kedah"
    assert res["year"] == 2026
