#!/usr/bin/env python3
"""
Flight summary functions for IGC to FDR converter
"""

from igc_utils import toYMD, toHM

def flightSummary(flightMeta) -> str:
    """Generate a summary string for the flight"""
    pilot = f' by {flightMeta.Pilot}' if flightMeta.Pilot else ''
    distance = f" {flightMeta.TotalDistance:.2f} miles" if flightMeta.TotalDistance else ""
    
    # Format duration as hours:minutes
    duration_str = "N/A"
    if flightMeta.TotalDuration:
        total_seconds = flightMeta.TotalDuration.total_seconds()
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        duration_str = f"{hours} hours and {minutes} minutes"
    
    origin = flightMeta.DerivedOrigin or "N/A"
    destination = flightMeta.DerivedDestination or "N/A"
    waypoints = flightMeta.RouteWaypoints or "N/A"

    clientLine = ''
    deviceInfo = flightMeta.DeviceDetails or flightMeta.DeviceModel
    if deviceInfo:
        clientLine = f"\n  Client: {deviceInfo}"
        if flightMeta.DeviceVersion:
            clientLine += f" v{flightMeta.DeviceVersion}"

    importedLine = ''
    if flightMeta.ImportedFrom:
        importedLine = f"\nImported: {flightMeta.ImportedFrom}"

    # Format coordinates with proper precision
    start_lat = f"{flightMeta.StartLatitude:.6f}" if flightMeta.StartLatitude is not None else "N/A"
    start_lon = f"{flightMeta.StartLongitude:.6f}" if flightMeta.StartLongitude is not None else "N/A"
    end_lat = f"{flightMeta.EndLatitude:.6f}" if flightMeta.EndLatitude is not None else "N/A"
    end_lon = f"{flightMeta.EndLongitude:.6f}" if flightMeta.EndLongitude is not None else "N/A"
    
    # Format timestamps in Zulu time
    start_time = toHM(flightMeta.StartTime) + "Z" if flightMeta.StartTime else "N/A"
    end_time = toHM(flightMeta.EndTime) + "Z" if flightMeta.EndTime else "N/A"
    
    # Create heading with tail number and date
    date_str = toYMD(flightMeta.StartTime) if flightMeta.StartTime else "Unknown Date"
    heading = f"{flightMeta.TailNumber or 'Unknown'} - {date_str}{distance}{pilot} ({duration_str})"
    underline = '\n'+ ('-' * len(heading))

    return f'''{heading}{underline}
    From: {start_time} {origin} ({start_lat}, {start_lon})
      To: {end_time} {destination} ({end_lat}, {end_lon})
 Planned: {waypoints}
GPS/AHRS: {flightMeta.GPSSource or 'Unknown'}''' + clientLine + importedLine
