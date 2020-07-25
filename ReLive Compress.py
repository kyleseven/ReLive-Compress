import os
import shutil
import subprocess
import sys
import time

import pywintypes
import win32con
import win32file


def change_file_creation_time(filename: str, new_time: int) -> None:
    """
    Changes file creation time (for WINDOWS ONLY)

    Taken from: https://stackoverflow.com/questions/4996405/how-do-i-change-the-file-creation-date-of-a-windows-file

    :param filename: the name of the file
    :param new_time: the timestamp to apply to the file
    :return:
    """
    wintime = pywintypes.Time(new_time)  # pylint: disable=no-member
    winfile = win32file.CreateFile(
        filename, win32con.GENERIC_WRITE,
        win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE | win32con.FILE_SHARE_DELETE,
        None, win32con.OPEN_EXISTING,
        win32con.FILE_ATTRIBUTE_NORMAL, None)

    win32file.SetFileTime(winfile, wintime, None, None)

    winfile.close()


def convert_sec_to_hhmmss(seconds: int) -> str:
    """
    Converts seconds to a string that contains hours, minutes, seconds.
    A unit of time is not output if it is not needed.

    :param seconds:
    :return: a string that represents hours, minutes, and seconds
    """
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


def bytes_to_readable(num_bytes: float) -> str:
    """
    Converts bytes to a human readable file size.

    :param num_bytes: number of bytes to convert
    :return: a human readable file size string
    """
    for unit in [" B", " KB", " MB", " GB", " TB", " PB", " EB", " ZB"]:
        if abs(num_bytes) < 1024.0:
            return "%3.1f%s" % (num_bytes, unit)
        num_bytes /= 1024.0
    return "%.1f%s" % (num_bytes, " YB")


def compress_file(filename: str) -> int:
    """
    Compresses a file with ffmpeg and replaces the old one.

    :param filename: name of the file
    :return: return code of ffmpeg run
    """
    temp_output_fname = filename.rstrip(".mp4") + "_temp_out.mp4"

    result = subprocess.run(["ffmpeg", "-i", filename, "-c:v", "h264_amf", "-b:v", "10M", "-minrate", "2M",
                             "-maxrate", "15M", "-bufsize", "10M", "-map", "0", "-metadata",
                             "creation_time=\"\"", temp_output_fname], capture_output=True)

    if result.returncode != 0:
        if os.path.exists(temp_output_fname):
            os.remove(temp_output_fname)
        return result.returncode

    os.remove(filename)
    os.rename(temp_output_fname, filename)
    return result.returncode


def os_check() -> None:
    """
    Checks to see if Windows is being used and exits if it is not.

    :return: None
    """
    if os.name != "nt":
        print("ERROR: This program is not supported on non-Windows operating systems.")
        sys.exit(-1)


def ffmpeg_check() -> None:
    """
    Checks if ffmpeg is installed on the system and exits if it is not.

    :return: None
    """
    if shutil.which("ffmpeg") is None:
        print("ERROR: ffmpeg was not detected. Is it installed? Is it in your PATH?")
        print("If you don't have ffmpeg, you can download it at https://www.ffmpeg.org/download.html and install it "
              "one of two ways:")
        print("1. (Easier) Unzip and place the 3 ffmpeg exe files in the same folder as your videos. However, "
              "you will not be able to use ffmpeg outside this program.")
        print("2. (Recommended) Unzip and place the 3 ffmpeg exe files in C:\\Program Files\\ffmpeg\\bin and add the "
              "directory to your PATH. See: https://stackoverflow.com/questions/24219627/how-to-update-system-path-"
              "variable-permanently-from-cmd")
        input("Press [ENTER] to exit...")
        sys.exit(-2)


def update_last_compress(timestamp: int) -> None:
    """
    Updates the .lastcompress file with the specified timestamp.

    :param timestamp: the timestamp to be written to the .lastcompress file
    :return: None
    """
    # Opening with "a+" here because Windows doesn't like it when I open a hidden file with "w"
    lc_file = open(".lastcompress", "a+")
    lc_file.truncate(0)
    lc_file.write(str(int(timestamp)))
    lc_file.close()
    subprocess.run(["attrib", "+H", ".lastcompress"])


def get_last_compress() -> int:
    """
    Gets the last compress timestamp from the .lastcompress file

    :return: the .lastcompress timestamp or 0 if not found
    """
    if not os.path.exists(".lastcompress"):
        print("A .lastcompress file was not detected. Is this your first time using this program?")
        print("All mp4 files in " + os.getcwd() +
              " will be compressed and OVERWRITTEN.")
        print("Your CPU will likely be at 100% on all cores through the duration of this program.")
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
    else:
        lc_file = open(".lastcompress", "r")
        timestamp = lc_file.readline().rstrip()
        lc_file.close()

    if not timestamp.isnumeric():
        print("Corrupted .lastcompress file! Removing it...")
        os.remove(".lastcompress")
        get_last_compress()
    else:
        return int(timestamp)


# Gets the path of the video replays folder
def get_video_path() -> str:
    """
    Gets the path of the video replays folder and asks the user if it is not found.

    :return: path to video replays
    """
    home = os.path.expanduser("~")
    path = home + "\\Videos\\Radeon ReLive"

    while not os.path.exists(path):
        print("Not able to find a Radeon ReLive folder. Please specify it.")
        path = input("Videos Folder: " + home)
        if not os.path.exists(path):
            print("That directory doesn't exist!")

    return path


def main() -> None:
    """
    Main function

    Goes through all files matching *.mp4 and compresses them using ffmpeg.

    :return:
    """
    os_check()
    os.chdir(get_video_path())
    ffmpeg_check()

    timestamp_list = []
    fname_list = []
    total_time = 0
    old_size_total = 0
    new_size_total = 0
    files_failed = 0
    last_compress = get_last_compress()

    # Gather files and their timestamps
    for filename in os.listdir(os.getcwd()):
        if filename.endswith(".mp4"):
            timestamp = int(os.path.getmtime(filename))

            if timestamp > last_compress:
                fname_list.append(filename)
                timestamp_list.append(int(timestamp))

    if len(fname_list) > 0:
        print("Found " + str(len(fname_list)) + " files to compress.")
    else:
        print("No files needed to be compressed.")

    # Compress files
    for i, (filename, timestamp) in enumerate(zip(fname_list, timestamp_list)):
        start_time = time.perf_counter()
        old_size = os.path.getsize(filename)
        old_size_total += old_size

        # Compress then modify creation, modify, and access date of file
        print("Compressing " + str(i + 1) + " out of " + str(len(fname_list)) + ": " + filename + "... ",
              end="", flush=True)
        compress_rc = compress_file(filename)

        run_time = round(time.perf_counter() - start_time)
        total_time += run_time
        new_size = os.path.getsize(filename)
        new_size_total += new_size

        if compress_rc == 0:
            change_file_creation_time(filename, timestamp)
            os.utime(filename, (timestamp, timestamp))
            print("Success! (took " + convert_sec_to_hhmmss(run_time) + ") (" + bytes_to_readable(old_size) + " -> " +
                  bytes_to_readable(new_size) + ")", flush=True)
        else:
            print("Failed. (ffmpeg returned " + str(compress_rc) + ")", flush=True)
            files_failed += 1

    if len(fname_list) != 0:
        avg_time_per_file = round(total_time / len(fname_list))
        total_size_saved = old_size_total - new_size_total
        percent_decrease = round((total_size_saved / old_size_total) * 100)
        update_last_compress(max(timestamp_list))
        print("Finished! " + str(len(fname_list) - files_failed) + " files were compressed in " +
              convert_sec_to_hhmmss(total_time) + "! (" + convert_sec_to_hhmmss(avg_time_per_file) + " per file) You "
              "reclaimed " + bytes_to_readable(total_size_saved) + " of disk space! (" + str(percent_decrease) +
              "% decrease)")

    input("Press [ENTER] to exit...")


if __name__ == "__main__":
    main()
