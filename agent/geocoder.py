import requests
import time

def geocode_address(address):
    """
    Convert an address to lat/lng using Nominatim (free, no API key needed).
    Rate limited to 1 request/second.
    """
    try:
        # Append county and state if not present
        if "maryland" not in address.lower() and "md" not in address.lower():
            address = f"{address}, Anne Arundel County, Maryland"

        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": address,
            "format": "json",
            "limit": 1,
            "countrycodes": "us"
        }
        headers = {"User-Agent": "TitleIntelligenceAgent/1.0"}
        response = requests.get(url, params=params, headers=headers, timeout=10)
        data = response.json()

        time.sleep(1)  # Respect Nominatim rate limit

        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
        else:
            # Default to Anne Arundel County center if geocoding fails
            return 38.9784, -76.5926
    except Exception as e:
        print(f"Geocoding failed for {address}: {e}")
        return 38.9784, -76.5926  # Anne Arundel County center
