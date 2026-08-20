from fastapi import FastAPI
import sqlite3
from urllib.parse import unquote
from netex_tools.timetable import getLine, getLines

app = FastAPI()

@app.get('/')
async def root():
    return getLines()

@app.get('/line/{line_id}')
async def line(line_id):
    return getLine(unquote(line_id))



"""
    SELECT runtimes.time FROM points_in_pattern
INNER JOIN patterns ON patterns.id = points_in_pattern.pattern
INNER JOIN journeys ON journeys.pattern = patterns.id
INNER JOIN runtimes ON runtimes.time_demand_type = journeys.time_demand_type AND
runtimes.timing_link = points_in_pattern.timing_link
INNER JOIN waittimes ON waittimes.time_demand_type = journeys.time_demand_type AND
waittimes.timing_link = points_in_pattern.timing_link
WHERE journeys.id = "NL:ARR:ServiceJourney:722424:74:9031#AH:P11448"
"""
"""
SELECT journeys.id FROM journeys
INNER JOIN patterns ON patterns.id = journeys.pattern
INNER JOIN points_in_pattern ON points_in_pattern.pattern = patterns.id
INNER JOIN runtimes ON runtimes.time_demand_type = journeys.time_demand_type AND
runtimes.timing_link = points_in_pattern.timing_link
LEFT JOIN waittimes ON waittimes.time_demand_type = journeys.time_demand_type AND
waittimes.timing_link = points_in_pattern.timing_link
WHERE journeys.id = "NL:ARR:ServiceJourney:722424:74:9031#AH:P11448";
"""


"""
SELECT notices.id FROM journeys

INNER JOIN patterns ON patterns.id = journeys.pattern
INNER JOIN routes ON routes.id = patterns.route
INNER JOIN lines ON lines.id = routes.line
INNER JOIN points_in_pattern ON points_in_pattern.pattern = patterns.id
INNER JOIN rel_stoppoint_quaycode ON rel_stoppoint_quaycode.stoppoint = points_in_pattern.stoppoint
INNER JOIN scheduled_stop_points ON scheduled_stop_points.id = points_in_pattern.stoppoint
INNER JOIN notices ON (
notices.for = lines.id OR
notices.for = points_in_pattern.id OR
notices.for = scheduled_stop_points.id OR
notices.for = journeys.id
)
WHERE lines.id = "NL:CXX:Line:A036";
"""