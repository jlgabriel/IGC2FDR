#!/usr/bin/env python3
"""
FDR File Analyzer - Discontinuity Detection Tool

This standalone tool analyzes FDR files to detect discontinuities,
anomalies, and potential problems in the flight data.

Usage:
    python fdr_analyzer.py input_file.fdr
"""

import argparse
import csv
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import statistics


class FDRDataPoint:
    """Represents a single data point from an FDR file"""
    
    def __init__(self, line_number: int, timestamp: str, longitude: float, latitude: float, 
                 altitude: float, heading: float, pitch: float, roll: float, speed: float = 0.0):
        self.line_number = line_number
        self.timestamp = timestamp
        self.longitude = longitude
        self.latitude = latitude
        self.altitude = altitude
        self.heading = heading
        self.pitch = pitch
        self.roll = roll
        self.speed = speed
        self.time_obj = None
        
        # Parse timestamp
        try:
            self.time_obj = datetime.strptime(timestamp.split('.')[0], "%H:%M:%S")
        except:
            pass


class FDRAnalyzer:
    """Analyzes FDR files for discontinuities and anomalies"""
    
    def __init__(self):
        self.data_points = []
        self.issues = []
        
        # Thresholds for anomaly detection
        self.max_heading_change = 45.0  # degrees per second
        self.max_speed_change = 30.0    # knots per second
        self.max_altitude_change = 500.0  # feet per second
        self.max_time_gap = 2.0         # seconds
        self.min_realistic_speed = 0.0  # knots
        self.max_realistic_speed = 200.0  # knots for gliders
        self.max_pitch = 45.0           # degrees
        self.max_roll = 60.0            # degrees
    
    def parse_fdr_file(self, filename: str) -> bool:
        """Parse FDR file and extract data points"""
        try:
            # Check if file exists
            import os
            if not os.path.exists(filename):
                print(f"❌ File not found: {filename}")
                print(f"Current directory: {os.getcwd()}")
                print("Files in current directory:")
                for f in os.listdir('.'):
                    if f.endswith('.fdr'):
                        print(f"  - {f}")
                return False
            
            with open(filename, 'r', encoding='utf-8') as file:
                lines = file.readlines()
            
            print(f"📁 File found: {len(lines)} lines total")
            
            line_number = 0
            data_started = False
            header_lines = []
            
            for line in lines:
                line_number += 1
                line = line.strip()
                
                if not line:
                    continue
                
                # Store first 10 lines for debugging
                if line_number <= 10:
                    header_lines.append(f"Line {line_number}: {line}")
                
                # Skip comments and headers
                if line.startswith('COMM,') or line.startswith('ACFT,') or \
                   line.startswith('TAIL,') or line.startswith('DATE,') or \
                   line.startswith('DREF,') or line.startswith('A'):
                    continue
                
                # Check if this is the column header line
                if 'Longitude' in line and 'Latitude' in line:
                    data_started = True
                    print(f"✅ Found column headers at line {line_number}")
                    continue
                
                # If we haven't found headers yet, check if this looks like a data line
                if not data_started:
                    # Check if line looks like timestamp data (HH:MM:SS format)
                    if ':' in line and ',' in line:
                        parts = line.split(',')
                        if len(parts) >= 7:
                            try:
                                # Try to parse as timestamp
                                timestamp = parts[0].strip()
                                if ':' in timestamp and len(timestamp.split(':')) >= 3:
                                    # This looks like data, start processing
                                    data_started = True
                                    print(f"✅ Auto-detected data start at line {line_number} (no explicit headers)")
                            except:
                                pass
                
                if not data_started:
                    continue
                
                # Parse data line
                try:
                    parts = [part.strip() for part in line.split(',')]
                    if len(parts) >= 7:
                        timestamp = parts[0]
                        longitude = float(parts[1])
                        latitude = float(parts[2])
                        altitude = float(parts[3])
                        heading = float(parts[4])
                        pitch = float(parts[5])
                        roll = float(parts[6])
                        
                        # Extract speed if available (usually in 8th column)
                        speed = 0.0
                        if len(parts) >= 8:
                            try:
                                speed = float(parts[7])
                            except:
                                pass
                        
                        point = FDRDataPoint(line_number, timestamp, longitude, latitude,
                                           altitude, heading, pitch, roll, speed)
                        self.data_points.append(point)
                        
                except ValueError as e:
                    self.add_issue("PARSE_ERROR", f"Line {line_number}: Could not parse data - {e}")
            
            # Debug output if no data found
            if len(self.data_points) == 0:
                print("\n🔍 DEBUG INFORMATION:")
                print("First 10 lines of file:")
                for line in header_lines:
                    print(f"  {line}")
                print(f"\nData started flag: {data_started}")
                print("Looking for lines that start with timestamp format like '17:02:43.123456,'")
                
                # Try to find any data-like lines
                print("\nLines that might be data (first 5):")
                count = 0
                for i, line in enumerate(lines):
                    line = line.strip()
                    if line and not line.startswith(('COMM,', 'ACFT,', 'TAIL,', 'DATE,', 'DREF,', 'A')) and ',' in line:
                        print(f"  Line {i+1}: {line}")
                        count += 1
                        if count >= 5:
                            break
                            
            return len(self.data_points) > 0
            
        except Exception as e:
            print(f"Error reading file: {e}")
            return False
    
    def add_issue(self, issue_type: str, description: str, line_number: int = None):
        """Add an issue to the issues list"""
        self.issues.append({
            'type': issue_type,
            'description': description,
            'line_number': line_number
        })
    
    def analyze_heading_discontinuities(self):
        """Detect heading discontinuities"""
        print("Analyzing heading discontinuities...")
        
        for i in range(1, len(self.data_points)):
            prev_point = self.data_points[i-1]
            curr_point = self.data_points[i]
            
            # Calculate heading change
            heading_diff = abs(curr_point.heading - prev_point.heading)
            
            # Handle wrap-around (359° to 1°)
            if heading_diff > 180:
                heading_diff = 360 - heading_diff
            
            # Calculate time difference
            time_diff = self.calculate_time_diff(prev_point, curr_point)
            
            if time_diff > 0:
                heading_rate = heading_diff / time_diff
                
                if heading_rate > self.max_heading_change:
                    self.add_issue("HEADING_DISCONTINUITY", 
                                 f"Abrupt heading change: {prev_point.heading:.1f}° → {curr_point.heading:.1f}° "
                                 f"({heading_diff:.1f}° in {time_diff:.1f}s = {heading_rate:.1f}°/s)",
                                 curr_point.line_number)
    
    def analyze_time_gaps(self):
        """Detect time gaps in the data"""
        print("Analyzing time gaps...")
        
        for i in range(1, len(self.data_points)):
            prev_point = self.data_points[i-1]
            curr_point = self.data_points[i]
            
            time_diff = self.calculate_time_diff(prev_point, curr_point)
            
            if time_diff > self.max_time_gap:
                self.add_issue("TIME_GAP",
                             f"Time gap: {prev_point.timestamp} → {curr_point.timestamp} "
                             f"({time_diff:.1f} seconds)",
                             curr_point.line_number)
            elif time_diff <= 0:
                self.add_issue("TIME_BACKWARDS",
                             f"Time goes backwards or duplicate: {prev_point.timestamp} → {curr_point.timestamp}",
                             curr_point.line_number)
    
    def analyze_speed_anomalies(self):
        """Detect speed anomalies"""
        print("Analyzing speed anomalies...")
        
        for i, point in enumerate(self.data_points):
            # Check for unrealistic speeds
            if point.speed < self.min_realistic_speed or point.speed > self.max_realistic_speed:
                self.add_issue("UNREALISTIC_SPEED",
                             f"Unrealistic speed: {point.speed:.1f} kts",
                             point.line_number)
            
            # Check for abrupt speed changes
            if i > 0:
                prev_point = self.data_points[i-1]
                speed_diff = abs(point.speed - prev_point.speed)
                time_diff = self.calculate_time_diff(prev_point, point)
                
                if time_diff > 0:
                    speed_rate = speed_diff / time_diff
                    
                    if speed_rate > self.max_speed_change:
                        self.add_issue("SPEED_DISCONTINUITY",
                                     f"Abrupt speed change: {prev_point.speed:.1f} → {point.speed:.1f} kts "
                                     f"({speed_diff:.1f} kts in {time_diff:.1f}s = {speed_rate:.1f} kts/s)",
                                     point.line_number)
    
    def analyze_attitude_anomalies(self):
        """Detect attitude anomalies (pitch and roll)"""
        print("Analyzing attitude anomalies...")
        
        for point in self.data_points:
            # Check for extreme attitudes
            if abs(point.pitch) > self.max_pitch:
                self.add_issue("EXTREME_PITCH",
                             f"Extreme pitch: {point.pitch:.1f}°",
                             point.line_number)
            
            if abs(point.roll) > self.max_roll:
                self.add_issue("EXTREME_ROLL",
                             f"Extreme roll: {point.roll:.1f}°",
                             point.line_number)
    
    def analyze_position_anomalies(self):
        """Detect position anomalies"""
        print("Analyzing position anomalies...")
        
        for i in range(1, len(self.data_points)):
            prev_point = self.data_points[i-1]
            curr_point = self.data_points[i]
            
            # Calculate distance between points (simplified)
            lat_diff = abs(curr_point.latitude - prev_point.latitude)
            lon_diff = abs(curr_point.longitude - prev_point.longitude)
            
            # Rough distance calculation (degrees to approximate distance)
            distance_deg = (lat_diff**2 + lon_diff**2)**0.5
            
            time_diff = self.calculate_time_diff(prev_point, curr_point)
            
            if time_diff > 0 and distance_deg > 0.01:  # Large position jump
                self.add_issue("POSITION_JUMP",
                             f"Large position jump: {distance_deg:.6f}° in {time_diff:.1f}s",
                             curr_point.line_number)
    
    def calculate_time_diff(self, point1: FDRDataPoint, point2: FDRDataPoint) -> float:
        """Calculate time difference between two points in seconds"""
        try:
            # Parse timestamps
            time1 = datetime.strptime(point1.timestamp.split('.')[0], "%H:%M:%S")
            time2 = datetime.strptime(point2.timestamp.split('.')[0], "%H:%M:%S")
            
            # Handle day rollover
            if time2 < time1:
                time2 += timedelta(days=1)
            
            diff = (time2 - time1).total_seconds()
            
            # Add fractional seconds if present
            if '.' in point1.timestamp:
                frac1 = float('0.' + point1.timestamp.split('.')[1])
            else:
                frac1 = 0.0
                
            if '.' in point2.timestamp:
                frac2 = float('0.' + point2.timestamp.split('.')[1])
            else:
                frac2 = 0.0
            
            diff += (frac2 - frac1)
            
            return diff
            
        except:
            return 1.0  # Default to 1 second if parsing fails
    
    def generate_statistics(self):
        """Generate statistics about the flight data"""
        if not self.data_points:
            return
        
        print("\n" + "="*60)
        print("FLIGHT DATA STATISTICS")
        print("="*60)
        
        # Basic stats
        print(f"Total data points: {len(self.data_points)}")
        print(f"Time span: {self.data_points[0].timestamp} → {self.data_points[-1].timestamp}")
        
        # Heading stats
        headings = [p.heading for p in self.data_points]
        print(f"\nHeading range: {min(headings):.1f}° to {max(headings):.1f}°")
        print(f"Heading std dev: {statistics.stdev(headings):.1f}°")
        
        # Speed stats
        speeds = [p.speed for p in self.data_points if p.speed > 0]
        if speeds:
            print(f"\nSpeed range: {min(speeds):.1f} to {max(speeds):.1f} kts")
            print(f"Average speed: {statistics.mean(speeds):.1f} kts")
        
        # Altitude stats
        altitudes = [p.altitude for p in self.data_points]
        print(f"\nAltitude range: {min(altitudes):.0f} to {max(altitudes):.0f} ft")
        print(f"Altitude gain: {max(altitudes) - min(altitudes):.0f} ft")
        
        # Attitude stats
        pitches = [p.pitch for p in self.data_points]
        rolls = [p.roll for p in self.data_points]
        print(f"\nPitch range: {min(pitches):.1f}° to {max(pitches):.1f}°")
        print(f"Roll range: {min(rolls):.1f}° to {max(rolls):.1f}°")
    
    def print_issues_summary(self):
        """Print summary of found issues"""
        print("\n" + "="*60)
        print("ISSUES SUMMARY")
        print("="*60)
        
        if not self.issues:
            print("✅ No issues found! The FDR file looks clean.")
            return
        
        # Group issues by type
        issue_types = {}
        for issue in self.issues:
            issue_type = issue['type']
            if issue_type not in issue_types:
                issue_types[issue_type] = []
            issue_types[issue_type].append(issue)
        
        # Print summary
        for issue_type, issues in issue_types.items():
            print(f"\n🔴 {issue_type}: {len(issues)} occurrences")
            
            # Show first few examples
            for i, issue in enumerate(issues[:5]):
                line_info = f" (Line {issue['line_number']})" if issue['line_number'] else ""
                print(f"  {i+1}. {issue['description']}{line_info}")
            
            if len(issues) > 5:
                print(f"  ... and {len(issues) - 5} more")
    
    def export_issues_csv(self, filename: str):
        """Export issues to CSV file for detailed analysis"""
        if not self.issues:
            print("No issues to export.")
            return
        
        try:
            with open(filename, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Issue Type', 'Description', 'Line Number'])
                
                for issue in self.issues:
                    writer.writerow([
                        issue['type'],
                        issue['description'],
                        issue['line_number'] or ''
                    ])
            
            print(f"\n📊 Issues exported to: {filename}")
            
        except Exception as e:
            print(f"Error exporting issues: {e}")
    
    def analyze_all(self):
        """Run all analysis methods"""
        print("Starting comprehensive FDR analysis...\n")
        
        self.analyze_time_gaps()
        self.analyze_heading_discontinuities()
        self.analyze_speed_anomalies()
        self.analyze_attitude_anomalies()
        self.analyze_position_anomalies()
        
        self.generate_statistics()
        self.print_issues_summary()


def main():
    parser = argparse.ArgumentParser(description='Analyze FDR files for discontinuities and anomalies')
    parser.add_argument('input_file', help='FDR file to analyze')
    parser.add_argument('--export-csv', help='Export issues to CSV file')
    parser.add_argument('--heading-threshold', type=float, default=45.0, 
                       help='Max heading change per second (default: 45°)')
    parser.add_argument('--speed-threshold', type=float, default=30.0,
                       help='Max speed change per second (default: 30 kts)')
    
    args = parser.parse_args()
    
    # Create analyzer
    analyzer = FDRAnalyzer()
    
    # Set custom thresholds if provided
    analyzer.max_heading_change = args.heading_threshold
    analyzer.max_speed_change = args.speed_threshold
    
    # Parse and analyze file
    print(f"Analyzing FDR file: {args.input_file}")
    
    if not analyzer.parse_fdr_file(args.input_file):
        print("❌ Failed to parse FDR file or no data found.")
        sys.exit(1)
    
    print(f"✅ Successfully parsed {len(analyzer.data_points)} data points\n")
    
    # Run analysis
    analyzer.analyze_all()
    
    # Export to CSV if requested
    if args.export_csv:
        analyzer.export_issues_csv(args.export_csv)
    
    print(f"\n🔍 Analysis complete!")


if __name__ == "__main__":
    main()