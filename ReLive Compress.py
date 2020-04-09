import os
import shutil
import subprocess
import sys
import time

import pywintypes
import win32con
import win32file


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


# Converts seconds to a string that contains hours, minutes, seconds. A unit of time is not output if it is not needed.
def convert_sec_to_hhmmss(seconds):
    time_str = ""

    if seconds >= 3600:
        hours = int(seconds // 3600)
        time_str += str(hours) + "h "
        seconds -= hours * 3600

    if seconds >= 60:
        minutes = int(seconds // 60)
        time_str += str(minutes) + "m "
        seconds -= minutes * 60

    if seconds > 0:
        time_str += str(seconds) + "s "

    return time_str.rstrip()


# Compresses a file with ffmpeg and replaces it
def compress_file(fname):
    temp_output_fname = fname.rstrip(".mp4") + "_temp_out.mp4"

    result = subprocess.run(["ffmpeg", "-i", fname, "-vcodec", "libx264", "-map", "0", "-metadata",
                             "creation_time=\"\"", temp_output_fname], capture_output=True)

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
        print("ERROR: ffmpeg was not detected. Is it installed? Is it in your PATH?")
        print("If you don't have ffmpeg, you can download it at https://www.ffmpeg.org/download.html and install it "
              "one of two ways:")
        print("1. (Easier) Unzip and place the 3 ffmpeg exe files in the same folder as your videos. However, "
              "you will not be able to use ffmpeg outside this program.")
        print("2. (Recommended) Unzip and place the 3 ffmpeg exe files in C:\\Program Files\\ffmpeg\\bin and add the "
              "directory to your PATH.")
        input("Press [ENTER] to exit...")
        sys.exit(-2)


# Updates the .lastcompress file with the specified timestamp.
def update_last_compress(timestamp):
    # Opening with "a+" here because Windows doesn't like it when I open a hidden file with "w"
    lc_file = open(".lastcompress", "a+")
    lc_file.truncate(0)
    lc_file.write(str(int(timestamp)))
    lc_file.close()
    subprocess.run(["attrib", "+H", ".lastcompress"])


# Gets the last compress timestamp from the .lastcompress file or returns 0 if it does not exist.
def get_last_compress():
    if not os.path.exists(".lastcompress"):
        print("This is the first time you're running this program.")
        print("All mp4 files in " + os.getcwd() + " will be compressed and OVERWRITTEN.")
        while True:
            choice = input("Continue? [y/n] ")
            if choice.casefold() == "y".casefold():
                break
            elif choice.casefold() == "n".casefold():
                print("Exiting...")
                sys.exit(1)
            else:
                print("That is not a valid option. Try again")
                continue
        return 0

    lc_file = open(".lastcompress", "r")
    timestamp = lc_file.readline().rstrip()
    lc_file.close()

    if not timestamp.isnumeric():
        print("Corrupted .lastcompress file! Remove it and restart the program.")
        sys.exit(-4)
    else:
        return int(timestamp)


# Gets the path of the video replays folder
def get_video_path():
    home = os.path.expanduser("~")
    path = home + "\\Videos\\Radeon ReLive"

    while not os.path.exists(path):
        print("Not able to find a Radeon ReLive folder. Please specify it.")
        path = input("Videos Folder: " + home)
        if not os.path.exists(home):
            print("That directory doesn't exist!")

    return path


# Main function
# Goes through files matching *.mp4 and compresses them using ffmpeg
def main():
    os_check()
    os.chdir(get_video_path())
    ffmpeg_check()

    timestamp_list = []
    fname_list = []
    total_time = 0
    files_failed = 0
    last_compress = get_last_compress()

    # Gather files and their timestamps
    for filename in os.listdir(os.getcwd()):
        if filename.endswith(".mp4"):
            timestamp = int(os.path.getmtime(filename))

            if timestamp <= last_compress:
                pass
            else:
                fname_list.append(filename)
                timestamp_list.append(int(timestamp))

    # Compress files
    for i, (fname, timestamp) in enumerate(zip(fname_list, timestamp_list)):
        start_time = time.perf_counter()

        # Compress then modify creation, modify, and access date of file
        print("Compressing " + str(i + 1) + " out of " + str(len(fname_list)) + ": " + fname + "... ",
              end='')
        compress_rc = compress_file(fname)

        run_time = round(time.perf_counter() - start_time)
        total_time += run_time

        if compress_rc == 0:
            change_file_creation_time(fname, timestamp)
            os.utime(fname, (timestamp, timestamp))
            print("Success! (took " + str(run_time) + "s)")
        else:
            print("Failed. (ffmpeg returned " + str(compress_rc) + ")")
            files_failed += 1

    if len(fname_list) != 0:
        update_last_compress(max(timestamp_list))
        print("Finished! " + str(len(fname_list) - files_failed) + " files were converted in " +
              convert_sec_to_hhmmss(total_time) + "!")
    else:
        print("No files needed to be compressed.")

    input("Press [ENTER] to exit...")


if __name__ == "__main__":
    main()
