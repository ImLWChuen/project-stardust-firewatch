"""Download all satellite fire feeds."""
from pipeline.ingestion.download_modis import download_modis_data
from pipeline.ingestion.download_viirs import download_viirs_data

def download_all():
    download_modis_data()
    download_viirs_data()

if __name__ == "__main__":
    download_all()
