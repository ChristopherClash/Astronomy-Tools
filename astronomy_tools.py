import os
from datetime import datetime

import geocoder
import pytz
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from dotenv import load_dotenv
from skyfield.api import load, wgs84, Star
from skyfield.data import hipparcos, stellarium
from skyfield.projections import build_stereographic_projection
from timezonefinder import TimezoneFinder

# Load .env file
load_dotenv()
BING_MAPS_KEY = os.getenv("BING_MAPS_KEY")


# Gets the longitude and latitude of the user by geocoding their address using the Bing Maps API
def get_longitude_latitude():
    address = input("\nPlease enter your address (so we can find your longitude and latitude): ")
    g = geocoder.bing(address, key='Ai7RzM03xcjVLqx48S1JnCyXWz9BVMkVYb79d-TPCMgEG3C-ZFBz4KXozNZ5gKDI')
    results = g.json
    return results['lat'], results['lng']


# Gets the date and time of the user
def get_utc_dt(latitude, longitude):
    date = input("\nPlease enter the date you'd like to see in the format DD-MM-YYYY: ")
    time = input("\nPlease enter the time you'd like to see in the format HH:MM: ")
    date_and_time = date + " " + time
    formatted_date = datetime.strptime(date_and_time, '%d-%m-%Y %H:%M')
    timezonefinder = TimezoneFinder()
    timezone_str = timezonefinder.timezone_at(lng=longitude, lat=latitude)
    local = pytz.timezone(timezone_str)
    local_dt = local.localize(formatted_date, is_dst=None).astimezone(pytz.utc)
    return local_dt.astimezone(pytz.utc)


# Loads the necessary data for a sky map from hipparcos and stellarium
def load_star_data():
    eph = load('de421.bsp')
    url = ('https://raw.githubusercontent.com/Stellarium/stellarium/master'
           '/skycultures/modern_st/constellationship.fab')
    with load.open(hipparcos.URL) as f:
        stars = hipparcos.load_dataframe(f)
    with load.open(url) as f:
        constellations = stellarium.parse_constellations(f)
    return eph, stars, constellations


# Formats the data for the star map by projecting the star positions on the sky,
# returns the constellation lines as edges and the stars as an array
def format_star_data(eph, stars, constellations):
    lat, long = get_longitude_latitude()
    utc_dt = get_utc_dt(lat, long)

    earth = eph['earth']

    ts = load.timescale()
    t = ts.from_datetime(utc_dt)

    observer = wgs84.latlon(latitude_degrees=lat, longitude_degrees=long).at(t)
    observer.from_altaz(alt_degrees=90, az_degrees=0)
    ra, dec, distance = observer.radec()
    center_object = Star(ra=ra, dec=dec)

    center = earth.at(t).observe(center_object)
    projection = build_stereographic_projection(center)

    star_positions = earth.at(t).observe(Star.from_dataframe(stars))
    stars['x'], stars['y'] = projection(star_positions)

    edges = [edge for name, edges in constellations for edge in edges]
    edges_star1 = [star1 for star1, star2 in edges]
    edges_star2 = [star2 for star1, star2 in edges]

    return stars, edges_star1, edges_star2


# Draws the star map, using the stars and edges data from format_star_data
def draw_map(chart_size, max_star_size, eph, stars, constellations, save_image):
    stars, edges_star1, edges_star2 = format_star_data(eph, stars, constellations)
    limiting_magnitude = 10
    bright_stars = (stars.magnitude <= limiting_magnitude)
    magnitude = stars['magnitude'][bright_stars]
    fig, ax = plt.subplots(figsize=(chart_size, chart_size), facecolor='#041A40')

    marker_size = max_star_size * 10 ** (magnitude / -2.5)
    ax.scatter(stars['x'][bright_stars], stars['y'][bright_stars],
               s=marker_size, color='white', marker='.', linewidths=0,
               zorder=2)

    xy1 = stars[['x', 'y']].loc[edges_star1].values
    xy2 = stars[['x', 'y']].loc[edges_star2].values
    lines_xy = np.rollaxis(np.array([xy1, xy2]), 1)

    ax.add_collection(LineCollection(lines_xy, colors='#ffff', linewidths=0.15))
    ax.set_aspect('equal')
    ax.set_xlim(-1, 1)
    ax.set_ylim(-1, 1)
    plt.axis('off')

    if save_image == 'Y':
        image_path = 'StarMap.png'
        i = 0
        while os.path.exists(image_path):
            i += 1
            image_name = 'Starmap'
            image_name += repr(i)
            image_path = image_name + ".png"
        plt.savefig(image_path)
        plt.show()
    else:
        plt.show()
    plt.close()


# Generates a star map based on user input for chart size and maximum star size.
# Also allows user to save the image to a file.
def generate_star_map():
    chart_size = int(input('Enter chart size: '))
    max_star_size = int(input('Enter max star size: '))
    eph, stars, constellations = load_star_data()
    save_to_file = None
    while save_to_file != 'Y' and save_to_file != 'N':
        save_to_file = input('Do you wish to save this image? Y/N: ')
    draw_map(chart_size, max_star_size, eph, stars, constellations, save_to_file)


# Gets a list of all satellites from the Celestrak API
def get_satellites():
    stations_url = 'https://celestrak.com/NORAD/elements/stations.txt'
    satellites = load.tle_file(stations_url)
    print('Loaded', len(satellites), 'satellites')
    return satellites


# Gets a satellite by name, and returns it
def get_satellite_by_name():
    not_chosen = True
    choice = None
    satellites = get_satellites()
    for sat in satellites:
        print(sat.name)
    by_name = {sat.name: sat for sat in satellites}
    while not_chosen:
        choice = input("Please enter the name of the satellite you would like to track: ")
        if choice in by_name:
            not_chosen = False
        else:
            print("Please enter a valid satellite name")

    satellite = by_name[choice]
    return satellite


# Gets a list of all viewable satellites (i.e. satellites above the bluffton observatory)
def get_all_viewable_satellites():
    satellites = get_satellites()
    return satellites


# Gets the position of the bluffton observatory (i.e. your location)
def get_bluffton():
    longitude, latitude = get_longitude_latitude()
    return wgs84.latlon(longitude, latitude, elevation_m=0)


# Outputs the position of a satellite, formatted for readability
def output_position(position, name):
    if position[0].degrees > 0:
        print("\nThe ", name, "is above you")
    else:
        print("\nThe ", name, "is below you")
    print('Altitude:', position[0].degrees, '\u00b0')
    print('Azimuth:', position[1].degrees, '\u00b0')
    print('Distance: {:.1f} km'.format(position[2].km))


# Gets the topographic data for a specific satellite
def get_topographic_data(difference):
    ts = load.timescale()
    t = ts.now()
    return difference.at(t)


# Gets the position of a specific satellite by altitude, azimuth and distance and returns these as a tuple (position)
def get_position_data(satellite, bluffton):
    difference = satellite - bluffton
    topo = get_topographic_data(difference)
    alt, az, distance = topo.altaz()
    position = alt, az, distance
    return position


# Gets the position of a specific satellite by altitude, azimuth and distance and calls output function
def track_satellite():
    satellite = get_satellite_by_name()
    bluffton = get_bluffton()
    position = get_position_data(satellite, bluffton)
    output_position(position, name=satellite.name)


# Returns true if satellite is viewable - i.e. if altitude > 0 relative to Bluffton Observatory
def is_viewable(position):
    if position[0].degrees > 0:
        return True
    else:
        return False


# Prints all viewable satellites
def list_viewable_satellites():
    all_satellites = get_all_viewable_satellites()
    bluffton = get_bluffton()
    for sat in all_satellites:
        position = get_position_data(sat, bluffton)
        if is_viewable(position):
            print(sat.name, " is viewable (Altitude: {:.1f} \u00b0)".format(position[0].degrees))
        else:
            print(sat.name, " is not viewable (Altitude: {:.1f} \u00b0)".format(position[0].degrees))


# Prints right ascension and declination of a specific satellite
def get_ra_and_declination():
    satellites = get_satellite_by_name()
    bluffton = get_bluffton()
    difference = satellites - bluffton
    topo = get_topographic_data(difference)
    ra, dec, distance = topo.radec()
    print('\n The right ascension and declination are: ')
    print("Right Ascension: ", ra)
    print("Declination: ", dec)


# Main menu - choose an option or enter 5 to end the program
def choose_option():
    choice = int(input("\n What would you like to do? \n "
                       "1. Track a satellite \n "
                       "2. List all viewable satellites from your location \n "
                       "3. Get Right Ascension and Declination of a satellite \n "
                       "4. Show Star Map \n "
                       "5. Exit \n"))
    if choice == 1:
        track_satellite()
        return True
    elif choice == 2:
        list_viewable_satellites()
        return True
    elif choice == 3:
        get_ra_and_declination()
        return True
    elif choice == 4:
        generate_star_map()
        return True
    elif choice == 5:
        return False
    else:
        print("Please enter a valid option")
        return True


def main():
    choose = True
    while choose:
        choose = choose_option()


if __name__ == '__main__':
    main()
