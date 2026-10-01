import httpx

class FIRMSClient:
    """Client for interacting with the NASA FIRMS API."""
    def __init__(self, map_key: str, base_url: str = "https://firms.modaps.eosdis.nasa.gov/api"):
        self.map_key = map_key
        self.base_url = base_url

    async def fetch_area_csv(self, source: str, bbox: str, day_range: int = 1) -> str:
        url = f"{self.base_url}/area/csv/{self.map_key}/{source}/{bbox}/{day_range}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.text
