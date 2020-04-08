import datetime
import os
import shutil
import subprocess
import sys
import time

import pywintypes
import win32con
import win32file

# Global Vars
LAST_COMPRESS = datetime.datetime(2020, 4, 7, 0, 3, 0)
VIDEO_PATH = r"C:\Users\kyles\Videos\Radeon ReLive"


# Changes file creation time (WINDOWS ONLY)
# From: https://stackoverflow.com/questions/4996405/how-do-i-change-the-file-creation-date-of-a-windows-file
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


# Converts seconds to formatted hh mm ss string
def convert_sec_to_hhmmss(seconds):
    seconds = seconds % (24 * 3600)
    hour = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60

    return "%dhr %02dm %02ds" % (hour, minutes, seconds)


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
    return result.returncode


# Checks to see if Windows is being used
def os_check():
    if os.name != 'nt':
        print("ERROR: This program is not supported on non-Windows operating systems.")
        sys.exit(-1)


# Checks to see if ffmpeg is installed
def ffmpeg_check():
    if shutil.which("ffmpeg") is None:
        print("ERROR: ffmpeg was not detected.")
        print("       Is it installed?")
        print("       If it is, make sure to add it to your PATH")
        sys.exit(-2)


# Main function
# Goes through files matching *.mp4 and compresses them using ffmpeg
def main():
    timestamp_list = []
    fname_list = []
    total_time = 0
    files_failed = 0

    os.chdir(VIDEO_PATH)

    # Gather files and their timestamps
    for filename in os.listdir(os.getcwd()):
        if filename.endswith(".mp4"):
            timestamp = os.path.getmtime(filename)
            file_time = datetime.datetime.fromtimestamp(timestamp)

            if file_time < LAST_COMPRESS:
                pass
            else:
                fname_list.append(filename)
                timestamp_list.append(int(timestamp))

    # Compress files
    for i in range(len(fname_list)):
        start_time = time.perf_counter()

        # Compress then modify creation, modify, and access date of file
        print("Compressing " + str(i + 1) + " out of " + str(len(fname_list)) + ": " + fname_list[i] + "... ",
              end='')
        compress_rc = compress_file(fname_list[i])

        run_time = round(time.perf_counter() - start_time)
        total_time += run_time

        if compress_rc == 0:
            change_file_creation_time(fname_list[i], timestamp_list[i])
            os.utime(fname_list[i], (timestamp_list[i], timestamp_list[i]))
            print("Success! (took " + str(run_time) + "s)")
        else:
            print("Failed. (ffmpeg returned " + str(compress_rc) + ")")
            files_failed += 1

    print("Finished! " + str(len(fname_list) - files_failed) + " files were converted in " +
          convert_sec_to_hhmmss(total_time) + "!")
    input("Press [ENTER] to exit...")


if __name__ == "__main__":
    os_check()
    ffmpeg_check()
    main()
