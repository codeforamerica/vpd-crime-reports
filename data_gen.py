import json

import psycopg2

from sql import GET_CRIME_DETAILS

def data_gen():
    """
    Generate the data to be shown on the map. Bin the crimes and determine 'heat'
    """

    conn = psycopg2.connect(database='vpd_crime_reports')
    cur = conn.cursor()

    try:
        max_count = None
        geojson = {'type': 'FeatureCollection', 'features': []}

        cur.execute(GET_CRIME_DETAILS)
        for rec in cur.fetchall():
            t_id, count, geom, streets, timestamps = (rec)

            if not max_count:
                max_count = count

            details = []
            for ts, street in sorted(zip(timestamps, streets)):
                details.append([ts.strftime('%m/%d %H:%M'), street])

            geojson['features'].append({
                'type': 'Feature',
                'geometry': geom,
                'properties': {
                    'opacity': float(count) / max_count,
                    'details': details
                }
            })

        with open('./data/output.geojson', 'w') as f:
            f.write(json.dumps(geojson))

    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    data_gen()    
