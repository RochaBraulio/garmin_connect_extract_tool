import time
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import sys
import argparse
import os
from datetime import datetime

class GarminConnectScraper:
    def __init__(self, debug_port=9222):
        """Initialize the scraper to connect to an already running Chrome instance"""
        try:
            options = Options()
            options.add_experimental_option("debuggerAddress", f"127.0.0.1:{debug_port}")
            
            # Initialize connection to existing Chrome browser
            self.driver = webdriver.Chrome(options=options)
            print(f"Successfully connected to Chrome on port {debug_port}")
            print(f"Current URL: {self.driver.current_url}")
            
            self.base_url = "https://connect.garmin.com"
            self.activity_dates = {}  # Dictionary to store activity dates
            
            # Check if already logged in
            self.verify_login()
            
        except Exception as e:
            print(f"Error connecting to Chrome: {str(e)}")
            print("\nMake sure Chrome is running with remote debugging enabled.")
            print("Launch Chrome with these commands before running this script:")
            print("Windows: chrome.exe --remote-debugging-port=9222")
            print("Mac: /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222")
            print("Linux: google-chrome --remote-debugging-port=9222")
            sys.exit(1)
    
    def verify_login(self):
        """Verify that the browser is logged into Garmin Connect"""
        current_url = self.driver.current_url
        
        if "connect.garmin.com/modern" in current_url and "signin" not in current_url:
            print("Already logged into Garmin Connect")
            self.logged_in = True
        else:
            print("Not logged in to Garmin Connect.")
            print("Please log in to Garmin Connect in your Chrome browser first.")
            print("Current URL:", current_url)
            user_input = input("Are you logged in now? (yes/no): ")
            if user_input.lower().startswith('y'):
                self.logged_in = True
            else:
                print("Please log in and then restart this script.")
                sys.exit(1)
    
    def get_activity_data(self, activity_id):
        """Navigate to the activity page and get the page content"""
        if not self.logged_in:
            raise Exception("Not logged in to Garmin Connect")
        
        try:
            # Navigate to the activity page
            activity_url = f"{self.base_url}/modern/activity/{activity_id}"
            print(f"Navigating to activity: {activity_url}")
            self.driver.get(activity_url)
            
            # Wait for the page to load using multiple possible selectors
            print("Waiting for activity page to load...")
            
            # List of potential elements that indicate the page has loaded
            selectors = [
                (By.CLASS_NAME, "activity-view-content"),
                (By.CLASS_NAME, "page-title"),
                (By.CLASS_NAME, "activity-name"),
                (By.TAG_NAME, "h1"),
                (By.ID, "activityViewContent")
            ]
            
            # Try each selector, stopping at the first one found
            page_loaded = False
            for selector_type, selector_value in selectors:
                try:
                    WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((selector_type, selector_value))
                    )
                    print(f"Page loaded, found element: {selector_type}={selector_value}")
                    page_loaded = True
                    break
                except:
                    continue
            
            if not page_loaded:
                print("No specific page elements found, but continuing...")
                # If no specific elements found, just wait a bit
                time.sleep(5)
            
            # Wait for potential workout data to load
            print("Looking for workout data...")
            try:
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.ID, "setsContainer"))
                )
                print("Workout sets container found")
            except:
                print("Note: setsContainer not found. This may be normal if it's not a strength workout")
            
            # Get the page source
            html_content = self.driver.page_source
            print(f"Retrieved page source ({len(html_content)} characters)")
            return html_content
            
        except Exception as e:
            print(f"Error retrieving activity data: {str(e)}")
            # Try to recover
            print("Trying to recover...")
            time.sleep(5)  # Extra wait time
            html_content = self.driver.page_source
            print(f"Retrieved page source in recovery mode ({len(html_content)} characters)")
            return html_content
    
    def extract_workout_sets(self, html_content):
        """Extract workout sets from HTML content"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find the sets container
        sets_container = soup.find(id='setsContainer')
        if not sets_container:
            print("Warning: 'setsContainer' element not found. This may not be a strength workout.")
            
            # Try to find any table that might contain the workout data
            tables = soup.find_all('table')
            if tables:
                print(f"Found {len(tables)} tables, checking for workout data...")
                # Look for tables with appropriate workout-related headers
                for i, table in enumerate(tables):
                    headers = [th.text.strip() for th in table.find_all('th')] + [td.get('data-title') for td in table.find_all('td') if td.get('data-title')]
                    headers_text = ' '.join(headers).lower()
                    print(f"Table {i} headers: {headers_text[:100]}...")
                    
                    if any(keyword in headers_text for keyword in ['exercise', 'set', 'reps', 'weight']):
                        sets_container = table
                        print(f"Found potential workout data in table {i}")
                        break
            
            if not sets_container:
                print("No workout data found in any table")
                # Save the HTML for debugging
                with open("activity_page.html", "w", encoding="utf-8") as f:
                    f.write(html_content)
                print("Saved HTML content to 'activity_page.html' for debugging")
                return []
        
        # Extract data from each set
        workout_data = []
        set_rows = sets_container.find_all('tr', attrs={'data-set-number': True})
        print(f"Found {len(set_rows)} workout sets")
        
        for set_row in set_rows:
            try:
                set_number = set_row.get('data-set-number')
                cells = set_row.find_all('td')
                
                if len(cells) < 7:
                    print(f"Skipping set {set_number} - insufficient data columns ({len(cells)})")
                    continue
                    
                exercise = cells[1].text.strip()
                time = cells[2].text.strip()
                rest = cells[3].text.strip()
                reps = cells[4].text.strip()
                
                # We're still collecting these for processing but will drop them later
                weight_cell = cells[5]
                if weight_cell.find('a') and 'Bodyweight' in weight_cell.text:
                    weight_text = "Bodyweight"
                else:
                    weight_text = weight_cell.text.strip()
                    
                volume_text = cells[6].text.strip()
                
                set_data = {
                    'set': set_number,
                    'exercise': exercise,
                    'time': time,
                    'rest': rest,
                    'reps': reps,
                    'weight': weight_text,
                    'volume': volume_text
                }
                print(f"Set {set_number}: {exercise} - {reps} reps at {weight_text}")
                workout_data.append(set_data)
            except Exception as e:
                print(f"Error processing set row: {str(e)}")
        
        return workout_data

    def create_workout_dataframe(self, workout_data):
        """Convert workout data to a pandas DataFrame with the specified columns"""
        if not workout_data:
            print("No workout data to convert to DataFrame")
            return pd.DataFrame()
            
        df = pd.DataFrame(workout_data)
        print(f"Created DataFrame with {len(df)} rows and {len(df.columns)} columns")
        
        # Process set column - convert to int and then format with leading zeros
        try:
            # First convert to integer
            df['set'] = df['set'].astype(int)
            
            # Format set numbers with leading zeros to always have 3 digits
            def format_set_number(set_num):
                # Format to always have 3 digits with leading zeros
                return f"{set_num:03d}"
                
            df['set'] = df['set'].apply(format_set_number)
            print("Converted 'set' column to formatted string with leading zeros")
        except Exception as e:
            print(f"Error processing 'set' column: {str(e)}")
        
        # Handle non-numeric reps values
        def convert_reps(reps_str):
            try:
                return int(reps_str)
            except (ValueError, TypeError):
                return reps_str
                
        df['reps'] = df['reps'].apply(convert_reps)
        print("Processed 'reps' column")
        
        # Process weight column - extract numeric values
        def extract_weight(weight_str):
            if weight_str == "Bodyweight":
                return -999
            if weight_str == "--":
                return 0
            # Extract numbers from strings like "35 kg"
            match = re.search(r'([\d,\.]+)', str(weight_str))
            if match:
                return float(match.group(1).replace(',', '.'))
            return weight_str
            
        df['weight_value'] = df['weight'].apply(extract_weight)
        print("Processed 'weight' column to 'weight_value'")
        
        # Process volume column - extract numeric values
        def extract_volume(volume_str):
            if not volume_str:
                return None
            if volume_str == "Bodyweight":
                return -999
            # Extract numbers from strings like "525 kg"
            match = re.search(r'([\d,\.]+)', str(volume_str))
            if match:
                return float(match.group(1).replace(',', '.'))
            return None
            
        df['volume_value'] = df['volume'].apply(extract_volume)
        print("Processed 'volume' column to 'volume_value'")
        
        # Process time and rest columns to seconds
        def time_to_seconds(time_str):
            if not time_str or str(time_str).strip() == '':
                return None
                
            # Convert formats like "1:04,8" to seconds
            parts = re.split(r'[:,]', str(time_str))
            if len(parts) == 2:  # Format: "ss,d"
                try:
                    return float(parts[0] + '.' + parts[1])
                except ValueError:
                    return None
            elif len(parts) == 3:  # Format: "mm:ss,d"
                try:
                    return int(parts[0]) * 60 + float(parts[1] + '.' + parts[2])
                except ValueError:
                    return None
            return None
            
        df['time_seconds'] = df['time'].apply(time_to_seconds)
        df['rest_seconds'] = df['rest'].apply(time_to_seconds)
        print("Processed time and rest columns")
        
        # Convert time_seconds and rest_seconds to ISO 8601 format for PostgreSQL interval
        def seconds_to_iso8601(seconds):
            if seconds is None:
                return None
            
            # Format according to ISO 8601 duration format: PT[hours]H[minutes]M[seconds]S
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            remaining_seconds = seconds % 60
            
            # Format with precision for partial seconds - replace comma with dot
            if remaining_seconds == int(remaining_seconds):
                seconds_str = f"{int(remaining_seconds)}S"
            else:
                seconds_str = f"{remaining_seconds:.3f}S".replace(',', '.')
            
            # Build the ISO 8601 string
            iso_time = "PT"
            if hours > 0:
                iso_time += f"{hours}H"
            if minutes > 0:
                iso_time += f"{minutes}M"
            iso_time += seconds_str
            
            return iso_time
        
        # Create new columns with ISO 8601 format
        df['time_iso8601'] = df['time_seconds'].apply(seconds_to_iso8601)
        df['rest_iso8601'] = df['rest_seconds'].apply(seconds_to_iso8601)
        print("Created ISO 8601 formatted time and rest columns")
        
        # Add activity_id to the dataframe if it's not already there
        # This is needed to create the set_uid column
        if 'activity_id' not in df.columns:
            # This is a placeholder. The actual activity_id will be added in process_activity
            print("Activity ID not in DataFrame yet. Will be added during processing_activity")
        
        # Determine which columns to drop - MODIFIED THIS SECTION
        # Only drop the specified columns, keep time_iso8601 and rest_iso8601
        columns_to_drop = ['weight', 'volume', 'time', 'rest', 'time_seconds', 'rest_seconds']
        
        for col in columns_to_drop:
            if col in df.columns:
                df = df.drop(columns=[col])
                print(f"Dropped column: {col}")
        
        return df

    def save_dataframe_to_csv(self, df, filename="workout_data.csv"):
        """Save DataFrame to a CSV file"""
        df.to_csv(filename, index=False)
        print(f"Workout data saved to {filename}")
    
    def process_activity(self, activity_id, activity_date=None):
        """Process a single activity and return the dataframe"""
        html_content = self.get_activity_data(activity_id)
        workout_data = self.extract_workout_sets(html_content)
        
        if workout_data:
            print(f"Successfully extracted {len(workout_data)} workout sets")
            df = self.create_workout_dataframe(workout_data)
            
            # Add activity_id as a column if we haven't already
            if 'activity_id' not in df.columns:
                df['activity_id'] = activity_id
                print(f"Added activity_id column with value: {activity_id}")
            
            # Add the activity date as a column
            if activity_date:
                df['activity_date'] = activity_date
                print(f"Added activity_date column with value: {activity_date}")
            else:
                df['activity_date'] = None
                print(f"No date provided for activity {activity_id}, setting to None")
            
            # Create the set_uid column by concatenating set and activity_id
            if 'set' in df.columns and 'activity_id' in df.columns:
                # Create the set_uid column
                df['set_uid'] = df['set'] + df['activity_id']
                print("Created set_uid column by concatenating set and activity_id")
                
                # Drop the 'set' column as requested
                df = df.drop(columns=['set'])
                print("Dropped 'set' column as requested")
                
                # Reorder columns to put set_uid first
                cols = list(df.columns)
                cols.remove('set_uid')
                new_cols = ['set_uid'] + cols
                df = df[new_cols]
                print("Reordered columns to place set_uid as the first column")
            
            # Rename columns according to the requested format
            column_mapping = {
                'set_uid': 'set_uid',
                'activity_id': 'set_activity_id',
                'activity_date': 'set_date',  # New column
                'exercise': 'set_exercise',
                'time_iso8601': 'set_active_time',
                'rest_iso8601': 'set_rest_time',
                'reps': 'set_repetitions',
                'weight_value': 'set_weight',
                'volume_value': 'set_load'
            }
            
            # Create a new DataFrame with only the columns we want, in the specified order
            output_cols = ['set_uid', 'set_activity_id', 'set_date', 'set_exercise', 
                           'set_active_time', 'set_rest_time', 'set_repetitions', 
                           'set_weight', 'set_load']
            
            # Create a new DataFrame with renamed columns
            renamed_df = pd.DataFrame()
            for new_col, old_col in zip(output_cols, [col for col in column_mapping if col in df.columns]):
                if old_col in df.columns:
                    renamed_df[new_col] = df[old_col]
                else:
                    # If column doesn't exist, create an empty one
                    renamed_df[new_col] = None
                    print(f"Warning: Column '{old_col}' not found in data, creating empty column '{new_col}'")
            
            print(f"Renamed and reordered columns to: {', '.join(output_cols)}")
            return renamed_df, True
        else:
            print(f"No workout data found for activity {activity_id}")
            return pd.DataFrame(), False
    
    def process_multiple_activities(self, activities_with_dates, output_dir="."):
        """Process multiple activities with their dates and save each to a separate CSV file"""
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        all_data = []
        success_count = 0
        
        for activity_id, activity_date in activities_with_dates:
            print(f"\n{'='*50}")
            print(f"Processing activity {activity_id} ({activities_with_dates.index((activity_id, activity_date)) + 1}/{len(activities_with_dates)})")
            if activity_date:
                print(f"Activity date: {activity_date}")
            print(f"{'='*50}\n")
            
            df, success = self.process_activity(activity_id, activity_date)
            
            if success:
                # Save individual activity data
                output_file = os.path.join(output_dir, f"garmin_workout_{activity_id}.csv")
                self.save_dataframe_to_csv(df, output_file)
                
                # Add to combined data
                all_data.append(df)
                success_count += 1
        
        # If we have data from multiple activities, combine and save
        if len(all_data) > 1:
            combined_df = pd.concat(all_data, ignore_index=True)
            combined_file = os.path.join(output_dir, "garmin_workouts_combined.csv")
            self.save_dataframe_to_csv(combined_df, combined_file)
            print(f"\nCombined data from {success_count} activities saved to {combined_file}")
            
            return combined_df
        elif len(all_data) == 1:
            return all_data[0]
        else:
            return pd.DataFrame()
    
    def close(self):
        """Close the browser connection without actually closing the browser"""
        if hasattr(self, 'driver'):
            # Only quit the driver, not the actual browser
            self.driver.quit()
            print("Browser connection closed (browser window remains open)")


# Process command-line arguments when run as script
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Extract workout data from Garmin Connect using an existing Chrome session')
    parser.add_argument('--port', type=int, default=9222, help='Chrome debugging port (default: 9222)')
    parser.add_argument('--activity', type=str, action='append', help='Garmin activity ID(s) to extract')
    parser.add_argument('--date', type=str, action='append', help='Date(s) for each activity in format YYYY-MM-DD')
    parser.add_argument('--output', type=str, default='.', help='Output directory for CSV files (default: current directory)')
    parser.add_argument('--file', type=str, help='File containing activity IDs and dates, format: ACTIVITY_ID,YYYY-MM-DD (one per line)')
    
    args = parser.parse_args()
    
    # Get activity IDs and dates from different sources
    activities_with_dates = []
    
    # Add activities from --activity and --date arguments
    if args.activity:
        if args.date and len(args.activity) == len(args.date):
            for activity_id, date in zip(args.activity, args.date):
                activities_with_dates.append((activity_id, date))
                print(f"Added date mapping: Activity {activity_id} -> {date}")
        else:
            if args.date:
                print(f"Warning: Number of dates ({len(args.date)}) doesn't match number of activities ({len(args.activity)})")
            for activity_id in args.activity:
                activities_with_dates.append((activity_id, None))
    
    # Add activities from file if specified
    if args.file:
        try:
            with open(args.file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        # Split line by comma to get activity_id and date
                        parts = line.split(',')
                        if len(parts) >= 2:
                            activity_id = parts[0].strip()
                            date = parts[1].strip()
                            activities_with_dates.append((activity_id, date))
                            print(f"Added from file: Activity {activity_id} -> {date}")
                        else:
                            print(f"Warning: Invalid line format in file: '{line}'. Expected format: 'ACTIVITY_ID,YYYY-MM-DD'")
                print(f"Loaded {len(activities_with_dates)} activity IDs with dates from {args.file}")
        except Exception as e:
            print(f"Error reading activity IDs from file: {str(e)}")
    
    # If no activity IDs provided, prompt the user
    if not activities_with_dates:
        while True:
            activity_input = input("Enter activity ID and date (format: ID,YYYY-MM-DD) or press Enter when done: ")
            if not activity_input:
                break
            
            parts = activity_input.split(',')
            if len(parts) >= 2:
                activity_id = parts[0].strip()
                date = parts[1].strip()
                activities_with_dates.append((activity_id, date))
            else:
                print("Invalid format. Please use: ACTIVITY_ID,YYYY-MM-DD")
    
    if not activities_with_dates:
        print("No activity IDs provided. Exiting.")
        sys.exit(1)
    
    print(f"Processing {len(activities_with_dates)} activities: {', '.join([a[0] for a in activities_with_dates[:5]])}" + 
          (f" and {len(activities_with_dates) - 5} more..." if len(activities_with_dates) > 5 else ""))
    
    try:
        # Initialize the scraper with connection to existing Chrome session
        print(f"Connecting to Chrome session on port {args.port}...")
        scraper = GarminConnectScraper(debug_port=args.port)
        
        # Process all activities
        df = scraper.process_multiple_activities(activities_with_dates, output_dir=args.output)
        
        if not df.empty:
            # Display summary of all processed data
            print("\nAll processed activities summary:")
            
            if 'set_exercise' in df.columns:
                # Group exercises across all activities
                exercise_summary = df.groupby(['set_activity_id', 'set_exercise']).agg({
                    'set_repetitions': 'sum'
                })
                
                print("\nExercise Summary by Activity:")
                print(exercise_summary)
            
        else:
            print("No workout data found across all activities.")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()  # Print detailed error information
        
    finally:
        # Always close the browser connection
        if 'scraper' in locals():
            scraper.close()
