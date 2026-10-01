import httpx

class FIRMSClient:
    def __init__(self, map_key: str, base_url: str = "https://firms.modaps.eosdis.nasa.gov/api"):
        self.map_key = map_key
        self.base_url = base_url

    async def fetch_area(self, source: str, bbox: str, days: int = 1):
        url = f"{self.base_url}/area/csv/{self.map_key}/{source}/{bbox}/{days}"
        async with httpx.AsyncClient() as client:
            return await client.get(url)
