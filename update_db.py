import os
import re
import csv
import sys
import math
import json
import urllib
from datetime import datetime

import requests
import psycopg2

from geo import haversine, EARTH_CIRCUMFERENCE
from sql import INSERT_TILE_SQL


def update_incidents():
    """
    Iterate through .csv files and import the data into postgres
    """

    conn = psycopg2.connect(database='vpd_crime_reports')
    cur = conn.cursor()

    try:
        cur.execute('create table if not exists incident (id integer primary key, location_id integer, ts timestamp);')

        for fp in os.listdir(os.path.join(os.getcwd(), 'crime_data')):
            with open(os.path.join('crime_data', fp)) as f:
                reader = csv.reader(f)
                next(reader)

                i = 0
                for row in reader:
                    [rms_id, timestamp, crime_type, address, narrative] = row
                    rms_id = int(rms_id)
                    ts = datetime.strptime(timestamp, '%m/%d/%Y %H:%M')

                    cur.execute('select 1 from incident where id = %s;', (rms_id,))
                    if not cur.fetchone():

                        street = re.sub('VALLEJO( )*CA( )*(\d+)*', '', address).strip()

                        cur.execute('select id from location where street = %s;', (street,))
                        ret = cur.fetchone()
                        if not ret:
                            cur.execute('insert into location (street) values (%s) returning id;', (street,))
                            location_id = cur.fetchone()[0]
                        else:
                            location_id = ret[0]

                        cur.execute('insert into incident (id, location_id, ts) values (%s, %s, %s)', (rms_id, location_id, ts))
                        conn.commit()

    finally:
        cur.close()
        conn.close()

def update_locations():
    """
    Geocode any addresses with null `geom` field
    """

    conn = psycopg2.connect(database='vpd_crime_reports')
    cur = conn.cursor()

    try:
        cur.execute('create table if not exists location (id serial primary key, geom geometry, street varchar(64));')
        cur.execute('select id, street from location where geom is null;')

        for row in cur.fetchall():
            location_id, street = row[0], row[1]

            street = street.replace('.5', '')  # geocoder isn't always happy with '1/2' street addresses

            lat, lon = None, None
            data = {'address': street + ' Vallejo, CA'}
            url = 'https://maps.googleapis.com/maps/api/geocode/json?%s' % urllib.urlencode(data)

            r = requests.get(url) 
            if r.status_code == 200:
                response = r.json()
                status = response.get('status')
                if status == 'OK':
                    results = response.get('results')
                    if results:
                        point = results[0]['geometry']['location']
                        lat = point['lat']
                        lon = point['lng']

            print lat, lon
            if lat and lon:
                cur.execute("update location set geom = ST_GeomFromText('POINT(%s %s)') where id = %s;", (lon, lat, location_id))
                conn.commit()

    finally:
        cur.close()
        conn.close()

def update_tiles():
    """
    Create tiles for binning incident counts
    """

    node_spacing = int(sys.argv[1])

    conn = psycopg2.connect(database='vpd_crime_reports')
    cur = conn.cursor()

    try:
        cur.execute('drop table if exists tile;');
        cur.execute('create table tile (id serial primary key, geom geometry);')

        cur.execute('select min(st_y(geom)), min(st_x(geom)), max(st_y(geom)), max(st_x(geom)) from location;')
        ret = cur.fetchone()
        if ret:
            min_lat, min_lon, max_lat, max_lon = ret

        mid_lat = (max_lat + min_lat) / 2

        meters_per_degree_lat = EARTH_CIRCUMFERENCE / 360
        meters_per_degree_lon = haversine([mid_lat, 0.0], [mid_lat, 1.0])

        lat_node_spacing = node_spacing * (1. / meters_per_degree_lat)
        lon_node_spacing = node_spacing * (1. / meters_per_degree_lon)

        num_y_nodes = int(math.ceil((max_lat - min_lat) / lat_node_spacing))
        num_x_nodes = int(math.ceil((max_lon - min_lon) / lon_node_spacing))

        overlap_lat = (num_y_nodes * lat_node_spacing + min_lat) - max_lat
        start_lat = min_lat - (overlap_lat / 2)

        overlap_lon = (num_x_nodes * lon_node_spacing + min_lon) - max_lon
        start_lon = min_lon - (overlap_lon / 2)

        # start from SW corner
        for j in xrange(0, num_y_nodes):
            for i in xrange(0, num_x_nodes):
                # the bounds for this tile
                n = (j + 1) * lat_node_spacing + start_lat
                s = j * lat_node_spacing + start_lat
                e = (i + 1) * lon_node_spacing + start_lon
                w = i * lon_node_spacing + start_lon

                cur.execute(INSERT_TILE_SQL, (w, n, e, n, e, s, w, s, w, n));
                conn.commit()

        cur.execute('select t.id, ST_AsGeoJSON(t.geom), count(*) from tile t, location l, incident i where i.location_id = l.id and st_contains(t.geom, l.geom) = true group by t.id;')

    finally:
        cur.close()
        conn.close()


if __name__ == '__main__':
    update_incidents()
    update_locations()
    update_tiles()
