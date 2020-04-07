import os

import pywintypes
import win32con
import win32file
import datetime
import calendar
import pytz
import random
import subprocess

# Global Var - Last Compress datetime
LAST_COMPRESS = datetime.datetime(2020, 4, 7, 0, 2)
VIDEO_PATH = r"C:\Users\kyles\Videos\Radeon ReLive"


# Changes file creation time (WINDOWS ONLY)
def change_file_creation_time(fname, newtime):
    wintime = pywintypes.Time(newtime)
    winfile = win32file.CreateFile(
        fname, win32con.GENERIC_WRITE,
        win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE | win32con.FILE_SHARE_DELETE,
        None, win32con.OPEN_EXISTING,
        win32con.FILE_ATTRIBUTE_NORMAL, None)

    win32file.SetFileTime(winfile, wintime, None, None)

    winfile.close()


# Checks if a datetime is DST or not
def is_dst(dt, tz):
    aware_dt = tz.localize(dt)
    return aware_dt.dst() != datetime.timedelta(0, 0)


# Removes a specified prefix from a string
def remove_prefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix):]
    return text


# Compresses a file with ffmpeg and replaces it
def compress_file(fname):
    subprocess.run("ffmpeg -i \"" + fname + "\" -vcodec libx264 -map 0 -metadata creation_time=\"\" out.mp4",
                   capture_output=True, shell=True)
    os.remove(fname)
    os.rename("out.mp4", fname)


# This does the stuff!
# Goes through the current working directory and modifies:
#   - Creation time
#   - Modification time
#   - Access time
# of mp4 and m4v files based on the date on the file name.
def main():
    os.chdir(VIDEO_PATH)
    number_of_files = 0
    current_file = 0

    for filename in os.listdir(os.getcwd()):
        dateString = filename
        if filename.startswith("Replay_"):
            dateString = remove_prefix(filename, "Replay_")

        dateString = dateString.replace("-", ".")
        dateString = dateString.replace("_", ".")
        dateArr = dateString.split(".")
        if len(dateArr) < 5:
            print("Skipped: " + filename + "(incorrect file name)")
            continue

        # Pop unnecessary elements
        while len(dateArr) > 5:
            dateArr.pop()

        # Save date from date array
        year = int(dateArr[0])
        month = int(dateArr[1])
        day = int(dateArr[2])
        hour = int(dateArr[3])
        minute = int(dateArr[4])

        naive = datetime.datetime(year, month, day, hour, minute, random.randint(0, 59))

        if naive < LAST_COMPRESS:
            pass
        else:
            number_of_files += 1

    for filename in os.listdir(os.getcwd()):
        if filename.endswith(".m4v") or filename.endswith(".mp4"):
            dateString = filename
            if filename.startswith("Replay_"):
                dateString = remove_prefix(filename, "Replay_")

            dateString = dateString.replace("-", ".")
            dateString = dateString.replace("_", ".")
            dateArr = dateString.split(".")
            if len(dateArr) < 5:
                continue

            # Pop unnecessary elements
            while len(dateArr) > 5:
                dateArr.pop()

            # Save date from date array
            year = int(dateArr[0])
            month = int(dateArr[1])
            day = int(dateArr[2])
            hour = int(dateArr[3])
            minute = int(dateArr[4])

            # Convert US Central timezone to UTC and save timestamp
            local = pytz.timezone("America/Chicago")
            naive = datetime.datetime(year, month, day, hour, minute, random.randint(0, 59))
            local_dt = local.localize(naive, is_dst=is_dst(naive, local))
            utc_dt = local_dt.astimezone(pytz.utc)
            timestamp = calendar.timegm(utc_dt.timetuple())

            if naive < LAST_COMPRESS:
                continue

            # Compress then modify creation, modify, and access date of file
            print("Compressing " + str(current_file + 1) + " out of " + str(number_of_files) + ": " + filename + "... ",
                  end='')
            compress_file(filename)
            change_file_creation_time(filename, timestamp)
            os.utime(filename, (timestamp, timestamp))

            current_file += 1

            print("Success!")

    print("Finished!")
    input("Press enter to exit...")


if __name__ == "__main__":
    main()
