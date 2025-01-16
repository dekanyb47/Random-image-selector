import os, shelve, random, io, pathlib
import tkinter as tk
from tkinter import filedialog
from datetime import date, datetime, timedelta
from PIL import Image, ImageTk
import _pickle

shelve_dir = pathlib.Path("data")
shelve_dir.mkdir(exist_ok=True)

shelve_file = shelve.open(str(shelve_dir / "shelve_data"))

# shelve_file contents:
#   - "days_generated" : {}
#   - "folder_path" : selected folder path


# Converts time data into a human readable format.
def human_readable_format(time):  # (time var here has the type timedelta.)

    # Gets days and seconds.
    days, seconds = time.days, time.seconds

    # Converts seconds into hours, minutes and seconds.
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    time_parts = {"day": days,
                  "hour": hours,
                  "minute": minutes,
                  "second": seconds}

    parts = [f"{value} {key}{'s' if value > 1 else ''}" for key, value in time_parts.items() if value != 0]

    if len(parts) > 1:
        return ', '.join(parts[:-1]) + f" and {parts[-1]}"

    return parts[0] if parts else "0 seconds"

# Clears existing image attribute of a label.
def clear_image_attr(label):
    label.image = None
    label.config(image=None)
    return


# Determines if user has already generated an image today or not, and configures labels
def generated_today(time_label, image_label):
    # print(f"Current date: {date.today()}")

    # Checks if user has already generated an image this day. If not, it returns.
    if date.today() not in shelve_file.get("days_generated", {}).keys():
        return date.today(), False

    else:
        # Checks if file path is valid (it might have been deleted)
        file_path = shelve_file["days_generated"][date.today()]

        # Displays image of the day if it has been generated prior, and is still valid.
        if os.path.isfile(file_path):
            already_generated_image = make_and_validate_image(file_path)

            image_label.config(image=already_generated_image)
            image_label.image = already_generated_image

        # If path doesn't exist anymore, will display a message to the user
        else:
            clear_image_attr(image_label)
            show_error("Unfortunately, an image couldn't be found.\n\n"
                       "Please configure the selected folder, as it might have been\n"
                       "moved or deleted.\n\n")

        # Checks which is the next possible generation
        next_generation = date.today() + timedelta(days=1)
        while True:
            if next_generation not in shelve_file["days_generated"].keys():
                break
            else:
                next_generation = next_generation + timedelta(days=1)

        # Calculate the amount of time that needs to pass until the next generation.
        next_generation = datetime.combine(next_generation, datetime.min.time())
        time_difference = next_generation - datetime.now()

        # Shows the user the amount of time that they need to wait.
        readable_time = human_readable_format(time_difference)
        time_label.config(text=f"You already generated an image today! \nTime until you can generate again:"
                               f" {readable_time}.")

        return date.today(), True


# Creates an image from its given path using the pillow module, and converts it to a PNG, then to a PhotoImage.
def make_and_validate_image(image_path):
    # Create image with pillow module
    try:
        image = Image.open(image_path)
    except Exception as e:
        show_error("An unexpected error occurred. Please try again.")
        return ""

    # Resizing
    width, height = image.size

    if width > height:
        ratio = 430 / width
        image = image.resize((430, round(ratio * height)))
    else:
        ratio = 430 / height
        image = image.resize((round(ratio * width), 430))

    # Changing the extension to png (if possible)
    try:
        with io.BytesIO() as output:
            image.save(output, format="PNG")
            png_data = output.getvalue()

    except Exception:
        return

    # Convert to PhotoImage
    final = ImageTk.PhotoImage(data=png_data)
    image.close()
    return final

# Validating the contents of the given folder path, and generating the files which will be used during generation.
def generate_and_validate_files(folder_path, files):
    valid_extensions = {".png", ".jpeg", ".jpg", ".gif", ".webp", ".bmp"}

    # Generates the files.
    files_local = [f for f in os.listdir(folder_path) if not os.path.isdir(os.path.join(folder_path, f))]

    # Displays an error if folder contains no files.
    if not files_local:
        show_error("The selected directory contains no files!\n\n"
                    "Please select a different folder!")
        return False

    # If there is at least one file with a correct extension, it returns True and the files list.
    for file in files_local:
        if any(file.endswith(extension) for extension in valid_extensions):
            files[0] = files_local
            return True

    # If no valid files were found, shows the user a message.
    show_error("The selected directory contains no files\nwith valid extensions!\n\n"
               "Please select a different folder!")
    return False

# Gets folder_path from within the shelve file. If not found, it will display an error message.
def get_folder_path_from_shelve_file():
    try:
        folder_path = shelve_file["folder_path"]
        return folder_path

    # Handle missing key
    except KeyError:
        show_error("You haven't selected a folder yet!\n"
                   "Please use the \"Select folder\" button to do so!")
        return ""

    # Handle file corruption
    except _pickle.UnpicklingError:
        show_error("Unfortunately the file path for the directory \nyou selected was corrupted and cannot be found.\n\n"
                   "Please select a folder again!")
        return ""

    # Handle everything else
    except Exception:
        show_error("An unexpected error occurred. Please try again.")
        return ""

# Generates a new image if one hasn't already been generated today.
def select_and_display_image(image_label, time_label, files, daily_generations_var):
    # Returns if user already has generated an image today.

    # Continues if daily generations are off, calls different function otherwise.
    if daily_generations_var.get():
        current_day, bool_generated_today = generated_today(time_label, image_label)
        if bool_generated_today:
            return

    # If daily generations are turned off, and time_label already contains text, it will be erased.
    else:
        time_label.config(text="")

    # Gets the folder path from the shelve_file. Displays an error message from within the function if not found.
    folder_path = get_folder_path_from_shelve_file()
    if not folder_path:
        return

    # Before generation, check if files have been generated already. (If there are no files, an error message would have popped
    # up during validation.
    if not files[0]:
        if not generate_and_validate_files(folder_path, files):
            return

    # Selects a random picture, and sends it to validation. If it's valid, it breaks from the loop and continues.
    image = ""
    for _ in range(5000):
        image_path = os.path.join(folder_path, random.choice(files[0]))

        image = make_and_validate_image(image_path)
        if image:
            break

    # If no valid file was found in the 5000 tries, it shows an error to the user.
    if not image:
        show_error("No files with valid extensions were found in\nthe given directory after 5000 files were checked.\n\n"
                   "Please consider selecting a different folder!")

    # Adds current date along with image path into the shelve file, if validation was correct.
    if daily_generations_var.get():
        days_generated = shelve_file.get("days_generated", {})
        days_generated[current_day] = image_path
        shelve_file["days_generated"] = days_generated

    # Updates image label.
    image_label.config(image=image)
    image_label.image = image  # Required because automatic garbage collection


def get_folder_path(image_label, files):
    # Makes a window pop up, asking the user to select a directory.
    folder_path = filedialog.askdirectory()

    if not folder_path:
        return

    # Directory and inner file validation - messages to the user are displayed from within the function(s).
    valid = generate_and_validate_files(folder_path, files)

    if not valid:
        return

    # If folder was valid, adding it to the shelve_file.
    shelve_file["folder_path"] = folder_path
    return


# Handles creating the tkinter window, its labels, buttons etc.
def main():
    window.geometry("650x680")
    window.resizable(False, False)

    title = tk.Label(text="Daily image selector", font=("Impact", 30))
    title.pack(side='top', pady=5)

    sub_title = tk.Label(text="Today's image:", font=("Times new roman", 20, "bold"))
    sub_title.pack(side="top", pady=5)

    image_label = tk.Label(window, fg="#7d0905")
    image_label.pack(pady=5)

    files = [[]]

    select_folder_button = tk.Button(text="Select folder", font=("Times new roman", 16),
                                     command=lambda: get_folder_path(image_label, files))
    select_folder_button.place(anchor="sw", relx=0.005, rely=0.995)

    # Displays the amount of time the user has to wait in case they already generated an image today.
    time_label = tk.Label(font=("Times new roman", 14), fg="#7d0905")

    daily_generations_var = tk.IntVar(value=1)
    checkbox_daily_generations = tk.Checkbutton(window, variable=daily_generations_var, text="Daily generations",
                                                font=("Times new roman", 16), state="active",)
    checkbox_daily_generations.place(anchor="sw", relx=0.005, rely=0.935)

    generate_button = tk.Button(text="Generate!", font=("Times new roman", 16),
                                command=lambda: select_and_display_image(image_label, time_label, files, daily_generations_var))
    generate_button.place(anchor="s", relx=0.5, rely=0.995)

    time_label.pack(side='top')

    window.mainloop()


def show_error(message):
    error_window = tk.Toplevel(window)
    error_window.title("Error")
    error_window.geometry("-600-600")

    label_error = tk.Label(error_window, text=message, fg="red", font=("Times new roman", 18, "bold"))
    label_error.pack(pady=10)

    button_close = tk.Button(error_window, text="Close", command=error_window.destroy)
    button_close.pack(pady=5)


if __name__ == "__main__":
    window = tk.Tk()
    main()
