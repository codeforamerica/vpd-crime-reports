INSERT_TILE_SQL = """
insert into tile (geom) values (st_geomfromtext('polygon((%s %s, %s %s, %s %s, %s %s, %s %s))'));
"""

GET_CRIME_DETAILS = """
select t.id, count(*), st_asgeojson(t.geom)::json, array_agg(l.street), array_agg(i.ts)
from tile t, location l, incident i
where i.ts > now() - interval '30 days'
and l.id = i.location_id
and st_contains(t.geom, l.geom) = true
group by t.id
order by count desc;
"""
