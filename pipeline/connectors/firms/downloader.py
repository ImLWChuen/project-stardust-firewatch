"""Download management with chunking and rate limits."""
import os
from pipeline.connectors.firms.client import FIRMSClient

class FIRMSDownloader:
    def __init__(self, client: FIRMSClient, dest_dir: str):
        self.client = client
        self.dest_dir = dest_dir

    async def download_bbox(self, source: str, bbox: str, output_filename: str):
        content = await self.client.fetch_area_csv(source, bbox)
        out_path = os.path.join(self.dest_dir, output_filename)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)
        return out_path
