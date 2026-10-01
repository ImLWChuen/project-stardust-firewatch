from backend.app.integrations.firms.parser import parse_firms_csv

def test_parse_firms():
    csv_sample = "latitude,longitude,brightness,scan,track,acq_date,acq_time,satellite,confidence,version,bright_t31,frp,daynight\n5.1,100.2,312.4,1.0,1.0,2026-03-01,0630,Terra,85,6.1NRT,295.1,15.2,D"
    df = parse_firms_csv(csv_sample)
    assert len(df) == 1
    assert df.iloc[0]["latitude"] == 5.1
