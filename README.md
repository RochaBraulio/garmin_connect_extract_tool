# garmin_connect_extract_tool
Tool for extracting workout data from Garmin Connect website. Created with Lovable.


# Running the script from Terminal
1. Run the following command in the terminal

    macOS
    ```shell
    /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222
    ```

    Windows
    ```shell
     & "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
    ```
    Linux
    ```shell
    google-chrome --remote-debugging-port=9222
    ```


2. Once the Chrome browser window has opened, go to https://connect.garmin.com

3. Log in with your credentials

4. Run the script either on the current terminal windown or open a new one. 

    - If you want to extract data from a single activity
        ```shell
        python extract.py --activity ACTIVITY ID --date YYYY-MM-DD
        ```

    - If you want to extract data from multiple activities, there are two alternatives.

        (i) Add multiple arguments to the command 
        ```shell
        python extract.py --activity ID1 --date YYYY-MM-DD --activity ID2 --date YYYY-MM-DD --activity ID3 --date YYYY-MM-DD
        ```

        (ii) Pass a text file to the commmand with all the IDs from the desired activities (Preferred)
        ```shell
        python extract.py --file activities.txt
        ```
        
        File Format for Bulk Processing:
        When using --file, create a text file with one activity per line in this format:
        activity ID1,YYYY-MM-DD activity ID2,YYYY-MM-DD
        Each line should contain the activity ID, a comma, and the date in YYYY-MM-DD format.

5. The script will extract data and save it as a .csv file in the folder where the script is located. In case of multiple activities, the script will save individual files for each activity and a file containg all the activities combined.

6. Once you are done, close the browser and the terminal session(s).

