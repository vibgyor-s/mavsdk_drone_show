"""
Swarm Global Coordinate Calculator
Calculates follower positions in global coordinates using offset configurations
"""
import logging
import math
import navpy
from smart_swarm_src.utils import transform_body_to_nea

logger = logging.getLogger(__name__)

def calculate_formation_origin(leader_trajectories):
    """
    Calculate formation origin as center of all leader trajectories
    Returns: {'lat': center_lat, 'lon': center_lon, 'alt': center_alt}
    """
    if not leader_trajectories:
        raise ValueError("No leader trajectories provided")
    
    all_lats, all_lons, all_alts = [], [], []
    
    for leader_id, trajectory in leader_trajectories.items():
        all_lats.extend(trajectory['Latitude'].values)
        all_lons.extend(trajectory['Longitude'].values) 
        all_alts.extend(trajectory['Altitude_MSL_m'].values)
    
    origin = {
        'lat': sum(all_lats) / len(all_lats),
        'lon': sum(all_lons) / len(all_lons),
        'alt': sum(all_alts) / len(all_alts)
    }
    
    logger.info(f"Formation origin: {origin['lat']:.6f}, {origin['lon']:.6f}, {origin['alt']:.1f}m")
    return origin

def calculate_follower_global_position(leader_lat, leader_lon, leader_alt, leader_yaw, 
                                     offset_config, formation_origin):
    """
    Calculate follower position in global coordinates
    Uses local NED for offset calculations, returns global lat/lon/alt
    
    Args:
        leader_lat, leader_lon, leader_alt: Leader's global position
        leader_yaw: Leader's yaw angle in degrees
        offset_config: Dict with offset_x, offset_y, offset_z, frame
        formation_origin: Formation center point for NED calculations
    """
    try:
        # Convert leader position to local NED for offset calculations
        leader_ned = navpy.lla2ned(
            leader_lat, leader_lon, leader_alt,
            formation_origin['lat'], formation_origin['lon'], formation_origin['alt'],
            latlon_unit='deg', alt_unit='m', model='wgs84'
        )
        
        # Apply offset based on coordinate frame
        if offset_config['frame'] == "body":
            # Body coordinate mode: offset_x=Forward, offset_y=Right
            offset_x_ned, offset_y_ned = transform_body_to_nea(
                offset_config['offset_x'], offset_config['offset_y'], leader_yaw
            )
            logger.debug(f"Body offset: Forward={offset_config['offset_x']}, Right={offset_config['offset_y']} -> N={offset_x_ned:.2f}, E={offset_y_ned:.2f}")
        else:
            # NED coordinate mode: offset_x=North, offset_y=East
            offset_x_ned = offset_config['offset_x']
            offset_y_ned = offset_config['offset_y']
            logger.debug(f"NED offset: N={offset_x_ned}, E={offset_y_ned}")

        # Calculate follower NED position
        follower_ned = [
            leader_ned[0] + offset_x_ned,  # North
            leader_ned[1] + offset_y_ned,  # East
            leader_ned[2] + offset_config['offset_z']  # Down (altitude offset)
        ]
        
        # Convert back to global coordinates
        follower_lla = navpy.ned2lla(
            follower_ned,
            formation_origin['lat'], formation_origin['lon'], formation_origin['alt'],
            latlon_unit='deg', alt_unit='m', model='wgs84'
        )
        
        return follower_lla[0], follower_lla[1], follower_lla[2]  # lat, lon, alt
        
    except Exception as e:
        logger.error(f"Failed to calculate follower position: {e}")
        raise

def calculate_follower_yaw(leader_yaw, offset_config):
    """
    Calculate follower yaw angle
    For now, simply copy leader's yaw (can be enhanced later)
    """
    return leader_yaw