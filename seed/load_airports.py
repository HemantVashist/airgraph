"""
seed/load_airports.py
---------------------
Downloads global airport, route, airline, and plane data from OpenFlights,
filters it to keep India-centric connections + selective global transit hubs,
and seeds a rich, multi-node aviation GraphRAG database in Neo4j.
"""

import os
import sys
import csv
import httpx
from math import radians, sin, cos, sqrt, atan2
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Resolve project root dynamically to ensure portability across different machines
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, ".."))
os.chdir(project_root)
sys.path.append(project_root)

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

AIRPORTS_URL = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat"
ROUTES_URL = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/routes.dat"
AIRLINES_URL = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airlines.dat"
PLANES_URL = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/planes.dat"


def check_config():
    missing = [k for k, v in {
        "NEO4J_URI": NEO4J_URI,
        "NEO4J_USERNAME": NEO4J_USERNAME,
        "NEO4J_PASSWORD": NEO4J_PASSWORD,
    }.items() if not v]
    if missing:
        print(f"❌ Missing env vars: {', '.join(missing)}")
        sys.exit(1)


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in kilometers between two lat/lon coordinates."""
    R = 6371.0  # Earth radius in km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return round(R * c, 1)


# Selected major international hubs by region to connect India to the world
GLOBAL_HUBS = {
    # Middle East
    "DXB", "AUH", "DOH", "MCT", "RUH", "SHJ", "KWI", "IST",
    # Asia Pacific
    "SIN", "BKK", "HKG", "KUL", "NRT", "HND", "SYD", "MEL", "ICN",
    # Europe
    "LHR", "CDG", "FRA", "AMS", "ZRH", "MUC",
    # North America
    "JFK", "ORD", "LAX", "SFO", "YYZ", "EWR"
}


# ── OpenFlights Data Ingestion ────────────────────────────────────────────────

def fetch_data():
    check_config()
    print("📥 Downloading global airports database from OpenFlights…")
    airports_resp = httpx.get(AIRPORTS_URL, timeout=30)
    airports_resp.raise_for_status()

    print("📥 Downloading global flight routes database from OpenFlights…")
    routes_resp = httpx.get(ROUTES_URL, timeout=30)
    routes_resp.raise_for_status()

    print("📥 Downloading global airlines database from OpenFlights…")
    airlines_resp = httpx.get(AIRLINES_URL, timeout=30)
    airlines_resp.raise_for_status()

    print("📥 Downloading global aircraft/planes database from OpenFlights…")
    planes_resp = httpx.get(PLANES_URL, timeout=30)
    planes_resp.raise_for_status()

    return (
        airports_resp.text.splitlines(),
        routes_resp.text.splitlines(),
        airlines_resp.text.splitlines(),
        planes_resp.text.splitlines()
    )


def parse_data(airports_raw, routes_raw, airlines_raw, planes_raw):
    print("🧹 Parsing and filtering multi-node aviation network data (centered around India)…")

    # 1. Parse Planes
    # Format: Name, IATA, ICAO
    planes = {}
    reader = csv.reader(planes_raw)
    for row in reader:
        if not row or len(row) < 2:
            continue
        name = row[0]
        iata = row[1].strip()
        if iata and iata != "\\N":
            planes[iata] = name

    # 2. Parse Airlines
    # Format: Airline ID, Name, Alias, IATA, ICAO, Callsign, Country, Active
    airlines = {}
    reader = csv.reader(airlines_raw)
    for row in reader:
        if not row or len(row) < 8:
            continue
        name = row[1]
        iata = row[3].strip()
        country = row[6].strip()
        active = row[7].strip()
        
        # Keep active airlines with a valid 2 or 3-letter IATA code
        if active == "Y" and iata and iata != "\\N" and len(iata) in [2, 3]:
            airlines[iata] = {
                "name": name,
                "country": country
            }

    # 3. Parse Airports
    # Format: id, name, city, country, iata, icao, lat, lon, alt, tz...
    all_airports = {}
    reader = csv.reader(airports_raw)
    for row in reader:
        if not row or len(row) < 8:
            continue
        iata = row[4].strip()
        if not iata or len(iata) != 3 or iata == "\\N":
            continue

        all_airports[iata] = {
            "name": row[1],
            "city": row[2],
            "country": row[3],
            "lat": float(row[6]),
            "lon": float(row[7]),
        }

    # Keep Indian airports + defined global hubs
    kept_airports = {}
    for code, info in all_airports.items():
        is_india = info["country"].lower().strip() == "india"
        is_global_hub = code in GLOBAL_HUBS
        if is_india or is_global_hub:
            kept_airports[code] = info

    # 4. Parse Routes and map referenced entities to build high connectivity
    # Format: airline, airline_id, source, source_id, dest, dest_id, codeshare, stops, equipment
    raw_routes = []
    referenced_airlines = set()
    referenced_planes = set()
    referenced_countries = set()

    # Add all kept airport countries
    for info in kept_airports.values():
        referenced_countries.add(info["country"])

    reader = csv.reader(routes_raw)
    for row in reader:
        if not row or len(row) < 9:
            continue
        airline_code = row[0].strip()
        src = row[2].strip()
        dst = row[4].strip()
        equipment = row[8].strip()

        # Check if source and destination are in our kept set
        if src in kept_airports and dst in kept_airports:
            if src == dst:
                continue

            # Take the first plane model in the equipment string (e.g. "738 320" -> "738")
            equipment_list = equipment.split()
            plane_code = equipment_list[0] if equipment_list else ""

            # Ensure airline and plane exist in our parsed data; otherwise fallback
            if airline_code not in airlines:
                airlines[airline_code] = {"name": f"Airline {airline_code}", "country": ""}
            
            if plane_code and plane_code not in planes:
                planes[plane_code] = f"Aircraft {plane_code}"

            dist = haversine(
                kept_airports[src]["lat"], kept_airports[src]["lon"],
                kept_airports[dst]["lat"], kept_airports[dst]["lon"]
            )

            raw_routes.append({
                "src": src,
                "dst": dst,
                "airline": airline_code,
                "plane": plane_code,
                "distance": dist
            })

            referenced_airlines.add(airline_code)
            if plane_code:
                referenced_planes.add(plane_code)

    # Collect countries of referenced airlines
    for al_code in referenced_airlines:
        country = airlines[al_code]["country"]
        if country and country != "\\N" and country != "":
            referenced_countries.add(country)

    print(f"📊 Filtered Network Summary:")
    print(f"   - Airports: {len(kept_airports)}")
    print(f"   - Countries: {len(referenced_countries)}")
    print(f"   - Airlines: {len(referenced_airlines)}")
    print(f"   - Planes: {len(referenced_planes)}")
    print(f"   - Direct Route Connections: {len(raw_routes)}")

    return kept_airports, raw_routes, airlines, planes, referenced_airlines, referenced_planes, referenced_countries


def clear_database(session):
    print("🗑️  Clearing existing data (nodes and relationships)…")
    session.run("MATCH (n) DETACH DELETE n")

    print("🗑️  Dropping database constraints if they exist…")
    constraints = [
        "DROP CONSTRAINT FOR (a:Airport) REQUIRE a.code IS UNIQUE IF EXISTS",
        "DROP CONSTRAINT FOR (c:Country) REQUIRE c.name IS UNIQUE IF EXISTS",
        "DROP CONSTRAINT FOR (al:Airline) REQUIRE al.code IS UNIQUE IF EXISTS",
        "DROP CONSTRAINT FOR (pl:Plane) REQUIRE pl.code IS UNIQUE IF EXISTS",
    ]
    for c in constraints:
        try:
            session.run(c)
        except Exception as e:
            pass


def seed_neo4j(airports, routes, airlines, planes, ref_airlines, ref_planes, ref_countries):
    print("🔌 Connecting to Neo4j…")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    driver.verify_connectivity()
    print("   Connected!\n")

    with driver.session() as session:
        clear_database(session)

        print("🔑 Creating uniqueness constraints…")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (a:Airport) REQUIRE a.code IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (c:Country) REQUIRE c.name IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (al:Airline) REQUIRE al.code IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (pl:Plane) REQUIRE pl.code IS UNIQUE")

        # 1. Load Countries
        countries_list = list(ref_countries)
        print(f"📤 Loading {len(countries_list)} Countries into Neo4j…")
        session.run(
            """
            UNWIND $countries AS c_name
            MERGE (c:Country {name: c_name})
            """,
            countries=countries_list
        )

        # 2. Load Airports and connect to Country
        airports_list = [{"code": k, **v} for k, v in airports.items()]
        print(f"📤 Loading {len(airports_list)} Airports into Neo4j…")
        session.run(
            """
            UNWIND $airports AS port
            MERGE (a:Airport {code: port.code})
            SET a.name = port.name,
                a.city = port.city,
                a.lat  = port.lat,
                a.lon  = port.lon
            WITH a, port
            MERGE (c:Country {name: port.country})
            MERGE (a)-[:IN_COUNTRY]->(c)
            """,
            airports=airports_list
        )

        # 3. Load Airlines and connect to Country
        airlines_list = [
            {"code": k, "name": airlines[k]["name"], "country": airlines[k]["country"]}
            for k in ref_airlines
        ]
        print(f"📤 Loading {len(airlines_list)} Airlines into Neo4j…")
        session.run(
            """
            UNWIND $airlines AS al
            MERGE (a:Airline {code: al.code})
            SET a.name = al.name
            WITH a, al
            WHERE al.country IS NOT NULL AND al.country <> "" AND al.country <> "\\N"
            MERGE (c:Country {name: al.country})
            MERGE (a)-[:IN_COUNTRY]->(c)
            """,
            airlines=airlines_list
        )

        # 4. Load Planes
        planes_list = [{"code": k, "name": planes[k]} for k in ref_planes]
        print(f"📤 Loading {len(planes_list)} Planes into Neo4j…")
        session.run(
            """
            UNWIND $planes AS pl
            MERGE (p:Plane {code: pl.code})
            SET p.name = pl.name
            """,
            planes=planes_list
        )

        # 5. Load Route Edges
        print(f"📤 Loading {len(routes)} Routes into Neo4j…")
        session.run(
            """
            UNWIND $routes AS route
            MATCH (src:Airport {code: route.src})
            MATCH (dst:Airport {code: route.dst})
            MERGE (src)-[r:FLIGHT_TO {airline: route.airline}]->(dst)
            SET r.distance_km = route.distance,
                r.plane = route.plane
            """,
            routes=routes
        )

    driver.close()
    print(f"\n🎉 Done! Rich multi-node AirGraph successfully seeded.")
    print("   Run backend and frontend to visualize the fully connected flight network.")


def main():
    airports_raw, routes_raw, airlines_raw, planes_raw = fetch_data()
    (
        airports,
        routes,
        airlines,
        planes,
        ref_airlines,
        ref_planes,
        ref_countries
    ) = parse_data(airports_raw, routes_raw, airlines_raw, planes_raw)
    
    seed_neo4j(
        airports,
        routes,
        airlines,
        planes,
        ref_airlines,
        ref_planes,
        ref_countries
    )


if __name__ == "__main__":
    main()
