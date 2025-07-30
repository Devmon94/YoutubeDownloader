# IMPORTS
from pytubefix import YouTube
from pytubefix.cli import on_progress
from pytubefix.exceptions import VideoUnavailable, RegexMatchError
from tkinter.filedialog import askdirectory
from threading import Thread
from pathlib import Path
import json
import subprocess
import sys
import os
import tkinter as tk
import customtkinter
import ffmpeg
import json
import traceback

# CONSTANTS
MP3 = ".MP3"
MP4 = ".MP4"

"""
    --- CODE LOGIC ---

BELOW IS ALL THE LOGIC FOR THE APP TO WORK

"""
# INITIALIZE GLOBALS
def init_globals():
    global APP_DIR, CONFIG_FILE
    APP_DIR = ''
    CONFIG_FILE = ''

# GET THE APP DIRECTORY
def get_app_dir():
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS).parent
    else:
        return Path(__file__).parent
    
# SAVE CONFIG FILE
def save_config(theme_name=None, save_path=None):
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)

    except (FileNotFoundError, json.JSONDecodeError):
        print("Archivo corrupto o no encontrado, se crera uno nuevo.")
        config = {}
        
    if theme_name:
        config["theme"] = theme_name
        
    if save_path:
        config["path"] = save_path

    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

# LOAD CONFIG FILE
def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            global selectedOutputPath

            config = json.load(f)
            change_theme(config.get("theme"))  
            selectedOutputPath = config.get("path")    
            entry_output.configure(placeholder_text = selectedOutputPath)
    
# CHECKS IF CONFIG FILE EXIST AND CREATES OR LOADS IT
def check_config_file():
    global APP_DIR, CONFIG_FILE

    try:
        APP_DIR = get_app_dir()
        CONFIG_FILE = APP_DIR / "config.json"

        if CONFIG_FILE.exists():
            load_config()
        else:
            save_config(theme_name="dark", save_path=str(APP_DIR))

    except Exception:
        traceback.print_exc()

# (NO TOCAR) CHANGE APP THEME
def change_theme(style):
    if (style == "dark"):
        customtkinter.set_appearance_mode("dark")
        save_config(theme_name="dark")
    elif (style == "light"):
        customtkinter.set_appearance_mode("light")
        save_config(theme_name="light")
    else:
        customtkinter.set_appearance_mode("system")
        save_config(theme_name="system")

# (NO TOCAR) THREAD FPR WRITTING LOG AS TKINTER DOES NOT ALLOW MULTIPLE TASKS 
def start_download_thread():
    thread = Thread(target=download_youtube_video, daemon=True)
    thread.start()

# (NO TOCAR) DOWNLOAD LOGIC
def download_youtube_video():
    try:
        youtube = YouTube(entry_input.get(), on_progress_callback = on_progress)
    
        extension = combobox.get()
    
        if (extension not in (MP3, MP4)):
            raise ValueError("Formato no seleccionado")
        
        if (extension == MP3):
            youtube_stream = youtube.streams.filter(only_audio=True, subtype='mp4').first()

        else:
            youtube_stream = (youtube.streams.filter(progressive=True, file_extension="mp4")
                            .filter(resolution=lambda r: int(r.replace('p', '')) <= 1080)
                            .order_by("resolution")
                            .desc()
                            .first())      

        youtube_stream.download(output_path=selectedOutputPath)

        change_textbox_status("Title: " + youtube.title)
        change_textbox_status("Output path: " + selectedOutputPath)
        change_textbox_status("Download completed.")

        if (extension == MP3):
            change_format(youtube)

    except ValueError as ve:
        print(f"Error de formato: {ve}")
    
    except VideoUnavailable:
        change_textbox_status("El video no está disponible o fue eliminado.")

    except RegexMatchError:
        change_textbox_status("URL inválida.")
        
    except Exception:
            traceback.print_exc()

# (NO TOCAR) CHOOSES WHICH FORMAT AND PREPARE THE CONVERSION (ESTO ESTA ARREGLADO - USAR PARA LO DEMAS)
def change_format(youtube):
    change_textbox_status("Converting to .MP3")

    # Add extension to file name to generate the complete path
    downloaded_file_name = youtube.title + ".m4a" 
    downloaded_file_path = os.path.join(selectedOutputPath, downloaded_file_name)

    # Command to get the file length and calculate the % completation information
    command_getlength = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json",
        downloaded_file_path
    ]

    processMD = subprocess.run(command_getlength, capture_output=True, text=True)
    file_info = json.loads(processMD.stdout)

    file_length = (float(file_info["format"]["duration"]))  
    minutes = int(file_length // 60)
    seconds = int(file_length % 60)
    total = f"{minutes:02d}{seconds:02d}"
    
    converted_file_path = os.path.splitext(downloaded_file_path)[0] + ".mp3"
    command_conversion = [
         "ffmpeg",
         "-i", downloaded_file_path,
         "-y",
         "-vn",
         "-ab","192k",
         "-ar","44100",
         converted_file_path
    ]

    process = subprocess.Popen(command_conversion,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT,
                               universal_newlines=True)
    
    for line in iter(process.stdout.readline, ''):
            if "time=" in line:
                percentage = line[25:30].lstrip().replace(":","")
                percentage_value = (int(percentage)/int(total)) * 100
                formated = f"{percentage_value:6.2f} %"
                change_textbox_status(formated)

    change_textbox_status("Conversion completed.")
    change_textbox_status("Deleting .M4A file.")
    os.remove(downloaded_file_path)
    print(downloaded_file_path)
    change_textbox_status("File .M4A has been deleted.")

# (NO TOCAR) CHOOSES OUTPUT PATH
def browse_output():
    global selectedOutputPath
    selectedOutputPath = askdirectory(initialdir = APP_DIR)

    if(selectedOutputPath != ""):
        entry_output.configure(placeholder_text = selectedOutputPath)
        save_config(save_path=selectedOutputPath)

# (NO TOCAR) DISABLES / ENABLES TEXTBOX FOR LOG WRITTING
def change_textbox_status(text):
    tb_Status.configure(state="normal")
    tb_Status.insert("end", text + "\n")
    tb_Status.configure(state="disabled")

"""
    --- SCREEN LOGIC ---

BELOW IS ALL THE CONFIGURATION OF THE GUI:
    - WINDOW
    - MENU
    - FRAME
    - ELEMENTS (MENU, BUTTONS, ETC...)
    - APP START

"""

# INITIALIZE GLOBALS
init_globals()

# SCREEN CONFIGURATION
customtkinter.set_appearance_mode("dark")
customtkinter.set_default_color_theme("dark-blue")
app = customtkinter.CTk()
app.title("Youtube downloader")
app.geometry("530x650")
app.resizable(False, False)

# MENU
menu = tk.Menu(app)

app_menu = tk.Menu(menu, tearoff = False)
app_menu.add_command(label = "Close", command = lambda: exit())
menu.add_cascade(label = "Application", menu = app_menu)

config_menu = tk.Menu(menu, tearoff = False)
theme_menu = tk.Menu(config_menu, tearoff = False)
theme_menu.add_command(label="Light Theme", command = lambda:change_theme("light"))
theme_menu.add_command(label="Dark Theme", command = lambda:change_theme("dark"))
theme_menu.add_command(label="System Theme", command = lambda:change_theme("system"))

config_menu.add_cascade(label="Themes", menu=theme_menu)
menu.add_cascade(label = "Configutarion", menu = config_menu)

help_menu = tk.Menu(menu, tearoff = False)
menu.add_cascade(label = "Help", menu = help_menu)

app.configure(menu = menu)

# FRAME TITLE
label = customtkinter.CTkLabel(master=app, text=" Youtube Downloader", font=("Roboto", 24, "bold"), text_color="#2596be")
label.grid(pady=20, padx=10)

# FRAME CONTAINER
framePaths = customtkinter.CTkFrame(master=app)
framePaths.grid(pady=20, padx=60)

# URL LABEL & TEXTBOX
label_input = customtkinter.CTkLabel(master=framePaths, text="Video URL:", font=("Roboto", 12, "bold"), text_color="#2596be")
label_input.grid(column=0, row=0, sticky="w", pady=0, padx=5)

entry_input = customtkinter.CTkEntry(master=framePaths, placeholder_text="URL", width=400)                      
entry_input.grid(column=0, row=1, pady=0, padx=5)

# OUTPUT LABEL & TEXTBOX
label_output = customtkinter.CTkLabel(master=framePaths, text="Output path:", font=("Roboto", 12, "bold"), text_color="#2596be")
label_output.grid(column=0, row=2, sticky="w", pady=0, padx=5)

entry_output = customtkinter.CTkEntry(master=framePaths, placeholder_text="Output Path", width=400)
entry_output.grid(column=0, row=3, pady=0, padx=4) 

# BUTTON BROWSE
bt_Output = customtkinter.CTkButton(master=framePaths, text="Browse", width=400, command=browse_output)
bt_Output.grid(column=0, row=4, pady=5, padx=4) 

# FORMAT LABEL & COMBOBOX
label_format = customtkinter.CTkLabel(master=framePaths, text="Format:", font=("Roboto", 12, "bold"), text_color="#2596be")
label_format.grid(column=0, row=5, sticky="w", pady=0, padx=5)

combobox = customtkinter.CTkComboBox(master=framePaths, values=[".MP3", ".MP4"], width=400)
combobox.set(".MP3")
combobox.grid(column=0, row=6, pady=5, padx=4)

# BUTTON DOWNLOAD
bt_Download = customtkinter.CTkButton(master=framePaths, text="Download", width=400, command=start_download_thread)
bt_Download.grid(column=0, row=7, pady=5, padx=4) 

# STATUS TEXTBOX
tb_Status = customtkinter.CTkTextbox(master=framePaths, width=400, height=220, state="disabled", text_color="white")
tb_Status.grid(column=0, row=8, pady=4, padx=4) 

# LOADS APP CONFIG
check_config_file()

# STARTS APP
app.mainloop()