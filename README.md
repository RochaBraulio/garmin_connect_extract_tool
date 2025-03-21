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
    chrome.exe --remote-debugging-port=9222
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
        python extract.py --activity YOUR_ACTIVITY_ID
        ```

    - If you want to extract data from multiple activities, there are two alternatives.

        (i) Add multiple arguments to the command 
        ```shell
        python extract.py --activity ID1 --activity ID2 --activity ID3
        ```

        (ii) Pass a text file to the commmand with all the IDs from the desired activities (Preferred)
        ```shell
        python extract.py --file activity_ids.txt
        ```
5. The script will extract data and save it as a .csv file in the folder where the script is located. In case of multiple activities, the script will save individual files for each activity and a file containg all the activities combined.

6. Once you are done, close the browser and the terminal session(s).

