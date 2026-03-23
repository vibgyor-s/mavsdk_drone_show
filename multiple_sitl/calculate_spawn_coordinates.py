#!/usr/bin/env python3
"""Compute PX4 home coordinates from local north/east offsets.

This helper exists because processed swarm trajectories can contain very small
scientific-notation values, which `bc` does not parse reliably. Python's float
parser handles those values natively and keeps the startup shell thin.
"""

from __future__ import annotations

import argparse
import math
import sys

EARTH_RADIUS_M = 6_371_000.0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert north/east meter offsets into lat/lon coordinates."
    )
    parser.add_argument("--lat", type=float, required=True, help="Base latitude in degrees")
    parser.add_argument("--lon", type=float, required=True, help="Base longitude in degrees")
    parser.add_argument(
        "--offset-north",
        type=float,
        required=True,
        help="Northward offset in meters",
    )
    parser.add_argument(
        "--offset-east",
        type=float,
        required=True,
        help="Eastward offset in meters",
    )
    return parser


def calculate_coordinates(lat: float, lon: float, offset_north: float, offset_east: float) -> tuple[float, float]:
    lat_rad = math.radians(lat)
    new_lat = lat + math.degrees(offset_north / EARTH_RADIUS_M)

    meters_per_degree_lon = math.radians(1.0) * EARTH_RADIUS_M * math.cos(lat_rad)
    if math.isclose(meters_per_degree_lon, 0.0, abs_tol=1e-12):
        raise ValueError("meters_per_degree_lon is too close to zero for a stable longitude conversion")

    new_lon = lon + (offset_east / meters_per_degree_lon)
    return new_lat, new_lon


def main() -> int:
    args = build_parser().parse_args()

    try:
        new_lat, new_lon = calculate_coordinates(
            lat=args.lat,
            lon=args.lon,
            offset_north=args.offset_north,
            offset_east=args.offset_east,
        )
    except ValueError as exc:
        print(f"ERROR={exc}", file=sys.stderr)
        return 1

    print(f"NEW_LAT={new_lat:.12f}")
    print(f"NEW_LON={new_lon:.12f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
