import calendar
import datetime
import os
import random
import shutil
import subprocess
import sys
import time

import pytz
import pywintypes
import win32con
import win32file

# Global Var - Last Compress datetime
LAST_COMPRESS = datetime.datetime(2020, 4, 7, 0, 3, 0)
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


def convert_sec_to_hhmmss(seconds):
    seconds = seconds % (24 * 3600)
    hour = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60

    return "%d:%02d:%02d" % (hour, minutes, seconds)


# Compresses a file with ffmpeg and replaces it
def compress_file(fname):
    temp_output_fname = fname.rstrip(".mp4") + "_temp_out.mp4"

    result = subprocess.run("ffmpeg -i \"" + fname + "\" -vcodec libx264 -map 0 -metadata creation_time=\"\" " +
                            temp_output_fname,
                            capture_output=True, shell=True)

    if result.returncode != 0:
        if os.path.exists(temp_output_fname):
            os.remove(temp_output_fname)
        return result.returncode

    os.remove(fname)
    os.rename(temp_output_fname, fname)
    return 0


def os_check():
    if os.name != 'nt':
        print("ERROR: This program is not supported on non-Windows operating systems.")
        sys.exit(-1)


def ffmpeg_check():
    if shutil.which("ffmpeg") is None:
        print("ERROR: ffmpeg was not detected.")
        print("       Is it installed?")
        print("       If it is, make sure to add it to your PATH")
        sys.exit(-2)


# This does the stuff!
# Goes through the current working directory and modifies:
#   - Creation time
#   - Modification time
#   - Access time
# of mp4 and m4v files based on the date on the file name.
def main():
    os.chdir(VIDEO_PATH)
    timestamp_data_list = []
    fname_list = []
    total_time = 0
    files_failed = 0

    for filename in os.listdir(os.getcwd()):
        if filename.endswith(".mp4"):
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

            local = pytz.timezone("America/Chicago")
            naive = datetime.datetime(year, month, day, hour, minute, random.randint(0, 59))
            local_dt = local.localize(naive, is_dst=is_dst(naive, local))
            utc_dt = local_dt.astimezone(pytz.utc)
            timestamp = calendar.timegm(utc_dt.timetuple())

            if naive < LAST_COMPRESS:
                pass
            else:
                fname_list.append(filename)
                timestamp_data_list.append(timestamp)

    for i in range(len(fname_list)):
        filename = fname_list[i]
        timestamp = timestamp_data_list[i]

        start_time = time.clock()
        # Compress then modify creation, modify, and access date of file
        print("Compressing " + str(i + 1) + " out of " + str(len(fname_list)) + ": " + filename + "... ",
              end='')

        run_time = time.clock() - start_time
        total_time += run_time

        compress_rc = compress_file(filename)

        if compress_rc == 0:
            change_file_creation_time(filename, timestamp)
            os.utime(filename, (timestamp, timestamp))
            print("Success! (took " + str(round(run_time)) + " seconds)")
        else:
            print("Failed. ffmpeg returned " + str(compress_rc))
            files_failed += 1

    print("Finished! " + str(len(fname_list) - files_failed) + " files converted in " + convert_sec_to_hhmmss(total_time) + "!")
    input("Press enter to exit...")


if __name__ == "__main__":
    os_check()
    ffmpeg_check()
    main()
