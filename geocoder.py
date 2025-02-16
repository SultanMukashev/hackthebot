from decouple import config
import requests

API_KEY = config('GOOGLE_API_KEY')

def geocode_address(address):
    """Gets geocoded data from Google Maps API for a given address."""
    url = f"https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "address": address,
        "key": API_KEY,
        "components": f"country:KZ"
    }
    
    response = requests.get(url, params=params)
    data = response.json()
    
    if data["status"] == "OK":
        formatted_address = data["results"][0]["formatted_address"]
        lat = data["results"][0]["geometry"]["location"]["lat"]
        lng = data["results"][0]["geometry"]["location"]["lng"]
        return {"corrected_address": formatted_address, "latitude": lat, "longitude": lng}
    else:
        return {"error": data.get("error_message", "Invalid address or API issue.")}