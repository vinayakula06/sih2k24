from flask import Flask, render_template, request, jsonify
import folium
import sqlite3
from geopy.distance import geodesic
import googlemaps
import requests

app = Flask(__name__)

gmaps = googlemaps.Client(key='AIzaSyBMQPryqr_OhPX4lUtLBjB4YADGKJtUXkA')  # Replace with your actual API key

def query_db(query, args=(), one=False):
    conn = sqlite3.connect('bo_po_data.db')
    cur = conn.cursor()
    cur.execute(query, args)
    rv = cur.fetchall()
    conn.close()
    return (rv[0] if rv else None) if one else rv

def geocode_address_google(address):
    geocode_result = gmaps.geocode(address)
    
    if not geocode_result:
        return None, None

    location = geocode_result[0]['geometry']['location']
    lat, lng = location['lat'], location['lng']

    if -90 <= lat <= 90 and -180 <= lng <= 180:
        return lat, lng
    else:
        return None, None

def parse_address(address):
    geocode_result = gmaps.geocode(address)
    
    if not geocode_result:
        return None

    components = geocode_result[0]['address_components']

    address_parts = {
        'Flat No.': '',
        'Floor': '',
        'Building Number': '',
        'Street': '',
        'City': '',
        'State': '',
        'Pincode': ''
    }

    for component in components:
        if 'street_number' in component['types']:
            address_parts['Building Number'] = component['long_name']
        elif 'route' in component['types']:
            address_parts['Street'] = component['long_name']
        elif 'locality' in component['types']:
            address_parts['City'] = component['long_name']
        elif 'administrative_area_level_1' in component['types']:
            address_parts['State'] = component['long_name']
        elif 'postal_code' in component['types']:
            address_parts['Pincode'] = component['long_name']

    return address_parts

def find_nearest_po(lat, lon):
    nearest_po = None
    min_distance = float('inf')
    pos = query_db("SELECT * FROM postal_data WHERE OfficeType='PO'")
    if not pos:
        print("No POs found in the database.")
        return None, None  # No POs available

    for po in pos:
        try:
            # Ensure the correct index is used for latitude (index 9) and longitude (index 10)
            po_lat = float(po[9])  # Latitude at index 9
            po_lon = float(po[10])  # Longitude at index 10

            po_location = (po_lat, po_lon)
            distance = geodesic((lat, lon), po_location).km

            if distance < min_distance:
                min_distance = distance
                nearest_po = po

        except (ValueError, TypeError):
            print(f"Skipping PO with invalid coordinates: {po}")
            continue

    if nearest_po:
        print(f"Nearest PO: {nearest_po[3]}, Distance: {min_distance:.2f} km")
    else:
        print("No valid PO found.")

    return nearest_po, min_distance



def find_nearest_bo(lat, lon):
    nearest_bo = None
    min_distance = float('inf')
    bos = query_db("SELECT * FROM postal_data WHERE OfficeType='BO'")
    if not bos:
        print("No BOs found in the database.")
        return None, None  # No BOs available

    for bo in bos:
        try:
            bo_lat = float(bo[9])  # Latitude at index 9
            bo_lon = float(bo[10])  # Longitude at index 10

            bo_location = (bo_lat, bo_lon)
            distance = geodesic((lat, lon), bo_location).km

            if distance < min_distance:
                min_distance = distance
                nearest_bo = bo

        except (ValueError, TypeError):
            print(f"Skipping BO with invalid coordinates: {bo}")
            continue

    if nearest_bo:
        print(f"Nearest BO: {nearest_bo[3]}, Distance: {min_distance:.2f} km")
    else:
        print("No valid BO found.")

    return nearest_bo, min_distance

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_map', methods=['POST'])
def get_map():
    full_address = request.form['address']
    address_parts = parse_address(full_address)
    
    if not address_parts:
        return jsonify({'error': 'Address not found or invalid.'}), 400

    formatted_address = f"{address_parts.get('Flat No', '')}, {address_parts.get('Street', '')}, {address_parts.get('City', '')}, {address_parts.get('State', '')}, {address_parts.get('Pincode', '')}"
    user_lat, user_lon = geocode_address_google(formatted_address)

    if user_lat is not None and user_lon is not None:
        map_center = [user_lat, user_lon]
        mymap = folium.Map(location=map_center, zoom_start=12)
        folium.Marker(
            location=[user_lat, user_lon],
            popup=f"Your Location",
            icon=folium.Icon(color='blue', icon='info-sign')
        ).add_to(mymap)
        nearest_bo, distance_to_bo = find_nearest_bo(user_lat, user_lon)

        if nearest_bo is not None:
            nearest_bo_details = (f"Nearest BO: {nearest_bo[3]}<br>"  # BO Name at index 3
                                  f"Division: {nearest_bo[2]}<br>"   # DivisionName at index 2
                                  f"Circle: {nearest_bo[1]}<br>"     # CircleName at index 1
                                  f"District: {nearest_bo[7]}<br>"   # District at index 7
                                  f"State: {nearest_bo[8]}<br>"      # StateName at index 8
                                  f"Pincode: {nearest_bo[5]}<br>"    # Pincode at index 5
                                  f"Distance: {distance_to_bo:.2f} km")
            try:
                bo_lat = float(nearest_bo[9])
                bo_lon = float(nearest_bo[10])

                folium.Marker(
                    location=[bo_lat, bo_lon],
                    popup=nearest_bo_details,
                    icon=folium.Icon(color='red', icon='info-sign')
                ).add_to(mymap)
            except ValueError:
                print(f"Skipping BO marker due to invalid coordinates: {nearest_bo}")
        nearest_po, distance_to_po = find_nearest_po(user_lat, user_lon)

        if nearest_po is not None:
            nearest_po_details = (f"Nearest PO: {nearest_po[3]}<br>"  # PO Name at index 3
                                  f"Division: {nearest_po[2]}<br>"   # DivisionName at index 2
                                  f"Circle: {nearest_po[1]}<br>"     # CircleName at index 1
                                  f"District: {nearest_po[7]}<br>"   # District at index 7
                                  f"State: {nearest_po[8]}<br>"      # StateName at index 8
                                  f"Pincode: {nearest_po[5]}<br>"    # Pincode at index 5
                                  f"Distance: {distance_to_po:.2f} km")

            try:
                po_lat = float(nearest_po[9])
                po_lon = float(nearest_po[10])

                folium.Marker(
                    location=[po_lat, po_lon],
                    popup=nearest_po_details,
                    icon=folium.Icon(color='green', icon='info-sign')
                ).add_to(mymap)
            except ValueError:
                print(f"Skipping PO marker due to invalid coordinates: {nearest_po}")

        mymap.save('templates/map.html')
        return render_template('map.html')
    else:
        return jsonify({'error': 'Address not found or invalid coordinates.'}), 400

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
