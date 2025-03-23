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
from datetime import datetime, timedelta

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
            self.activity_dates = {}  # Dictionary to store activity IDs and their dates
            
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
    
    def get_dates_from_activities_page(self):
        """Navigate to the activities page and extract dates for all activities"""
        if not self.logged_in:
            raise Exception("Not logged in to Garmin Connect")
        
        try:
            # Navigate to the activities page
            activities_url = f"{self.base_url}/modern/activities"
            print(f"Navigating to activities list: {activities_url}")
            self.driver.get(activities_url)
            
            # Wait for the activities to load
            print("Waiting for activities list to load...")
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.activity-list-container"))
            )
            
            # Give it a bit more time for the activities to fully load
            time.sleep(2)
            
            # Get the page source
            html_content = self.driver.page_source
            print(f"Retrieved activities page source ({len(html_content)} characters)")
            
            # Parse the page to extract activity IDs and dates
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for activities
            activity_items = soup.find_all("div", class_=lambda c: c and "ActivityListItem_activityRow" in c)
            print(f"Found {len(activity_items)} activities in the list")
            
            for item in activity_items:
                try:
                    # Extract activity ID from the activity name link
                    activity_link = item.find("a", href=True)
                    if not activity_link:
                        continue
                        
                    activity_id = activity_link.get("href").split("/")[-1]
                    
                    # Extract date parts
                    date_container = item.find("div", class_=lambda c: c and "ActivityListItem_dateListContainer" in c)
                    if not date_container:
                        continue
                        
                    date_span = date_container.find("span", class_=lambda c: c and "ActivityListItem_activityDate" in c)
                    year_span = date_container.find("span", class_=lambda c: c and "ActivityListItem_activityDateYear" in c)
                    
                    if not date_span or not year_span:
                        continue
                        
                    date_text = date_span.text.strip()  # Format: "20 Mar"
                    year_text = year_span.text.strip()  # Format: "2025"
                    
                    # Parse the date
                    try:
                        # Parse the date in "DD MMM YYYY" format
                        date_obj = datetime.strptime(f"{date_text} {year_text}", "%d %b %Y")
                        formatted_date = date_obj.strftime("%Y-%m-%d")
                        
                        # Store the activity ID and date
                        self.activity_dates[activity_id] = formatted_date
                        print(f"Activity {activity_id}: {formatted_date}")
                    except ValueError as e:
                        print(f"Error parsing date '{date_text} {year_text}': {str(e)}")
                except Exception as e:
                    print(f"Error processing activity item: {str(e)}")
            
            print(f"Extracted dates for {len(self.activity_dates)} activities")
            
            # If we need more activities (scrolling for pagination), we could add that here
            
            return self.activity_dates
        except Exception as e:
            print(f"Error retrieving activity dates: {str(e)}")
            return {}
    
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
                    'set': set_number,  # Will be dropped later
                    'exercise': exercise,
                    'time': time,
                    'rest': rest,
                    'reps': reps,
                    'weight': weight_text,  # Will be dropped later
                    'volume': volume_text  # Will be dropped later
                }
                print(f"Set {set_number}: {exercise} - {reps} reps at {weight_text}")
                workout_data.append(set_data)
            except Exception as e:
                print(f"Error processing set row: {str(e)}")
        
        return workout_data

    def create_workout_dataframe(self, workout_data, activity_date):
        """Convert workout data to a pandas DataFrame with the specified columns"""
        if not workout_data:
            print("No workout data to convert to DataFrame")
            return pd.DataFrame()
            
        df = pd.DataFrame(workout_data)
        print(f"Created DataFrame with {len(df)} rows and {len(df.columns)} columns")
        
        # Add the activity date as a column
        df['date'] = activity_date
        print(f"Added date column with value: {activity_date}")
        
        # Process remaining columns (still process set before dropping it)
        try:
            df['set'] = df['set'].astype(int)
            print("Converted 'set' column to integers")
        except Exception as e:
            print(f"Error converting 'set' column: {str(e)}")
        
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
                return weight_str
            # Extract numbers from strings like "35 kg"
            match = re.search(r'([\d,\.]+)', str(weight_str))
            if match:
                return float(match.group(1).replace(',', '.'))
            return weight_str
            
        df['weight_value'] = df['weight'].apply(extract_weight)
        print("Processed 'weight' column to 'weight_value'")
        
        # Process volume column - extract numeric values
        def extract_volume(volume_str):
            if not volume_str or volume_str == "Bodyweight":
                return None
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
        
        # Drop the requested columns: 'set', 'weight', 'volume'
        columns_to_drop = ['set', 'weight', 'volume']
        for col in columns_to_drop:
            if col in df.columns:
                df = df.drop(columns=[col])
                print(f"Dropped column: {col}")
        
        return df

    def save_dataframe_to_csv(self, df, filename="workout_data.csv"):
        """Save DataFrame to a CSV file"""
        df.to_csv(filename, index=False)
        print(f"Workout data saved to {filename}")
    
    def process_activity(self, activity_id):
        """Process a single activity and return the dataframe"""
        html_content = self.get_activity_data(activity_id)
        workout_data = self.extract_workout_sets(html_content)
        
        # Get the activity date from our dictionary
        activity_date = self.activity_dates.get(activity_id, "Unknown")
        print(f"Activity date from activities list: {activity_date}")
        
        if workout_data:
            print(f"Successfully extracted {len(workout_data)} workout sets")
            df = self.create_workout_dataframe(workout_data, activity_date)
            
            # Add activity_id as a column
            df['activity_id'] = activity_id
            
            return df, True
        else:
            print(f"No workout data found for activity {activity_id}")
            return pd.DataFrame(), False
    
    def process_multiple_activities(self, activity_ids, output_dir="."):
        """Process multiple activities and save each to a separate CSV file"""
        # First get dates for all activities
        print("\nGetting activity dates from activities list page...")
        self.get_dates_from_activities_page()
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        all_data = []
        success_count = 0
        
        for activity_id in activity_ids:
            print(f"\n{'='*50}")
            print(f"Processing activity {activity_id} ({activity_ids.index(activity_id) + 1}/{len(activity_ids)})")
            print(f"{'='*50}\n")
            
            df, success = self.process_activity(activity_id)
            
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
    parser.add_argument('--activity', type=str, action='append', help='Garmin activity ID(s) to extract (can be used multiple times)')
    parser.add_argument('--output', type=str, default='.', help='Output directory for CSV files (default: current directory)')
    parser.add_argument('--file', type=str, help='File containing activity IDs, one per line')
    
    args = parser.parse_args()
    
    # Get activity IDs from different sources
    activity_ids = []
    
    # Add activities from --activity arguments
    if args.activity:
        activity_ids.extend(args.activity)
    
    # Add activities from file if specified
    if args.file:
        try:
            with open(args.file, 'r') as f:
                file_ids = [line.strip() for line in f if line.strip()]
                activity_ids.extend(file_ids)
                print(f"Loaded {len(file_ids)} activity IDs from {args.file}")
        except Exception as e:
            print(f"Error reading activity IDs from file: {str(e)}")
    
    # If no activity IDs provided, prompt the user
    if not activity_ids:
        while True:
            activity_id = input("Enter a Garmin activity ID (or press Enter when done): ")
            if not activity_id:
                break
            activity_ids.append(activity_id)
    
    if not activity_ids:
        print("No activity IDs provided. Exiting.")
        sys.exit(1)
    
    print(f"Preparing to process {len(activity_ids)} activities: {', '.join(activity_ids[:5])}" + 
          (f" and {len(activity_ids) - 5} more..." if len(activity_ids) > 5 else ""))
    
    try:
        # Initialize the scraper with connection to existing Chrome session
        print(f"Connecting to Chrome session on port {args.port}...")
        scraper = GarminConnectScraper(debug_port=args.port)
        
        # Process all activities
        df = scraper.process_multiple_activities(activity_ids, output_dir=args.output)
        
        if not df.empty:
            # Display summary of all processed data
            print("\nAll processed activities summary:")
            
            if 'exercise' in df.columns:
                # Group exercises across all activities
                exercise_summary = df.groupby(['activity_id', 'exercise', 'date']).agg({
                    'reps': 'sum'
                })
                
                print("\nExercise Summary by Activity and Date:")
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