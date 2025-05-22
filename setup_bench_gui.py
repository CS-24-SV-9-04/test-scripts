#!/usr/bin/python3
import os
from re import search
from subprocess import PIPE, Popen
from tkinter import *
from tkinter import ttk
from tkinter import filedialog
from typing import Iterable, Optional, Tuple

class StagingFolderInfo:
    def __init__(self, branch: str, commit_hash: str):
        self.branch = branch
        self.commit_hash = commit_hash

QUERY_CATEGORIES = ["ReachabilityCardinality", "ReachabilityFireability", "ReachabilityDeadlock", "LTLCardinality", "LTLFireability"]
BASELINE_SETTINGS = [
    ("-r 0", "Structural reductions"),
    ("-R 0", "Colored structural reductions"),
    ("--interval-timeout 0", "interval?"),
    ("-l 0", "Linear programming"),
    ("-p", "Partial order reduction"),
    ("--disable-cfp", "CFP"),
    ("--disable-partitioning", "Color partitioning"),
    ("--disable-symmetry-vars", "Symmetric variables")
]
SUCCESSOR_GENERATORS = ["fixed", "even"]
STRATEGIES = ["RDFS", "DFS", "BFS", "BestFS", "RPFS"]

master = Tk()


staging_folder_var = StringVar()
staging_info_text = StringVar(value="No folder selected")
bench_name = StringVar(value="bench")
extra_bench_options = StringVar(value="-g")
enabled_categories = set(QUERY_CATEGORIES)
enabled_baseline_settings = set(map(lambda s: s[0], BASELINE_SETTINGS))
enable_baseline = BooleanVar()
strategy = StringVar(value="RDFS")
successor_generator = StringVar(value="even")
staging_folder_info: Optional[StagingFolderInfo] = None
query_simplification_timeout = None

current_row = 0

def staging_folder_changed(a,b,c):
    update_staging_info()

def promptStagingFolder():
    directoryPath = filedialog.askdirectory(initialdir = "/", title = "Select a staging folder")
    if (directoryPath == ()):
        return
    staging_folder_var.set(directoryPath)

def command(arguments, cwd):
    process = Popen(arguments, stdout=PIPE, cwd=cwd)
    (output, err) = process.communicate()
    exit_code = process.wait()
    return (exit_code, output.decode('utf-8'), err.decode('utf-8') if err is not None else "")

def command_non_capture(arguments, cwd):
    process = Popen(arguments, cwd=cwd)
    return process.wait()

def update_staging_info():
    set_create_control_state(DISABLED)
    staging_folder_info = None
    try:
        (exit_code, output, err) = command(["git", "status", "--porcelain=v1", "-b"], staging_folder_var.get())
        if (exit_code != 0):
            staging_info_text.set("Invalid staging folder")
            return
        (exit_code, output, err) = command(["git", "branch", "--show-current"], staging_folder_var.get())
        branchMatch = search("^([^\n]+)\n", output)
        if (branchMatch is None or exit_code != 0):
            staging_info_text.set("Could not find branch")
            return
        (exit_code, commitHash, err) = command(["git", "log", "--pretty=format:'%H'", "-n", "1"], staging_folder_var.get())
        if (exit_code != 0):
            print(output)
            staging_info_text.set("Could not find commit hash")
            return
        staging_folder_info = StagingFolderInfo(branchMatch.group(1), commitHash[1:8])
        staging_info_text.set(f"Branch: {staging_folder_info.branch}, commit hash: {staging_folder_info.commit_hash}")
        bench_name.set(f"{staging_folder_info.branch}.{staging_folder_info.commit_hash}")
        set_create_control_state(NORMAL)
        save_settings()
    except:
        staging_info_text.set("Invalid folder")

def upload_bench_action():
    create_bench_with_gui_options(True)

def create_bench_action():
    create_bench_with_gui_options(False)

def create_bench_with_gui_options(upload: bool):
    try:
        create_bench(upload, bench_name.get(), staging_folder_var.get(), extra_bench_options.get(), strategy.get(), enabled_categories, successor_generator.get(), enable_baseline.get(), query_simplification_timeout)
    except Exception as e:
        print("error")
        print(e)


def restore_settings():
    try:
        with open('.setup_bench_gui.rc', 'r') as f:
            staging_folder_var.set(f.read())
    except:
        pass

def save_settings():
    with open('.setup_bench_gui.rc', 'w') as f:
        f.write(staging_folder_var.get())

def create_bench(upload: bool, bench_name: str, staging_folder: str, extra_options: str, strategy: str, categories: Iterable[str], successor_generator: str, use_baseline: bool, query_simplification_timeout: Optional[int]):
    print("building")
    if command_non_capture(["make", "-j", "18", "verifypn-linux64"], staging_folder + "/build-release") != 0:
        raise Exception("Make returned non 0 exit code")
    bin_file_name = f"verifypn-linux64-{bench_name}"
    script_file_name = f"run-{bench_name}.sh"
    print(enabled_baseline_settings)
    with open(script_file_name, "w") as f:
        f.write("#!/bin/sh\n")
        command = [
            './create_big_jobs.py ',
            '-v',
            f'./staging/{bin_file_name}',
            '-o',
            bench_name,
            '-S',
            strategy,
            '-c',
            ','.join(categories),
            '--colored-successor-generator',
            successor_generator
        ]

        bypass_options = []
        command = command + extra_options.split(" ")
        if (use_baseline):
            command.append('-b')
            if len(enabled_baseline_settings) > 0:
                bypass_options = list(enabled_baseline_settings)

        if query_simplification_timeout is not None:
            bypass_options.append('-q')
            bypass_options.append(str(query_simplification_timeout))

        if (len(bypass_options) > 0):
            command.append('--')
            command = command + bypass_options

        f.write(' '.join(command))
    os.chmod(script_file_name, 0o775)
    if (upload):
        if command_non_capture(["scp", staging_folder + "/build-release/verifypn/bin/verifypn-linux64", f"mcc3:staging/{bin_file_name}"], os.getcwd()) != 0:
            raise Exception("Failed to upload binary")
        if command_non_capture(["scp", script_file_name, f"mcc3:staging/{script_file_name}"], os.getcwd()) != 0:
            raise Exception("Failed to upload script")
        os.unlink(script_file_name)
    print("finished")


def add_staging_folder_control(master: Misc):
    global current_row
    Label(master, text='Staging folder:').grid(row=current_row)
    staging_folder_var.trace_add(['write'], staging_folder_changed)
    Entry(master, textvariable=staging_folder_var).grid(row=current_row, column=1)
    Button(master, text = "Browse Files", command = promptStagingFolder).grid(row=current_row, column=2)
    current_row += 1
    def refresh_staging_info_action():
        update_staging_info()
    Button(master, text="Refresh staging info", command=refresh_staging_info_action).grid(row=current_row, column=0, columnspan=3)
    current_row += 1
    Label(master, textvariable=staging_info_text).grid(row=current_row, column=0, columnspan=3)
    current_row += 1

def add_category_control(master: Misc):
    global current_row
    def on_change_closure(query_category: str, enabled: BooleanVar):
        def closure(a,b,c):
            if enabled.get():
                enabled_categories.add(query_category)
            else:
                enabled_categories.remove(query_category)
        return closure

    category_wrapper = ttk.LabelFrame(master, text='Categories')
    category_wrapper.grid(column=0, row=current_row, columnspan=3, sticky=EW, padx=10)
    category_row = 0
    for query_category in QUERY_CATEGORIES:
        enabled = BooleanVar(value=query_category in enabled_categories)
        enabled.trace_add(['write'], on_change_closure(query_category, enabled))
        Checkbutton(category_wrapper, text=query_category, variable=enabled).grid(row=category_row, column=0, columnspan=3, sticky=W)
        category_row = category_row + 1
    current_row += 1

def add_baseline_control(master: Misc):
    global current_row
    Checkbutton(master, text="baseline", variable=enable_baseline).grid(row=current_row, column=0, columnspan=3, sticky='W')
    current_row += 1

    def on_change_baseline_setting(baseline_setting: Tuple[str, str], enabled: BooleanVar):
        def closure(a,b,c):
            if enabled.get():
                enabled_baseline_settings.remove(baseline_setting[0])
            else:
                enabled_baseline_settings.add(baseline_setting[0])
        return closure
    baseline_options_frame = LabelFrame(master, text="baseline options")
    baseline_options_frame.grid(column=0, columnspan=3, row=current_row, sticky=EW, padx=10)
    baseline_options_frame.grid_remove()
    def baseline_changed(a, b, c):
        if enable_baseline.get():
            baseline_options_frame.grid()
        else:
            baseline_options_frame.grid_remove()
    enable_baseline.trace_add(['write'], baseline_changed)
    baseline_option_row = 0
    for baseline_setting in BASELINE_SETTINGS:
        enabled = BooleanVar(value=False)
        enabled.trace_add(['write'], on_change_baseline_setting(baseline_setting, enabled))
        Checkbutton(baseline_options_frame, text=baseline_setting[1], variable=enabled).grid(row=baseline_option_row, column=0, sticky=W)
        baseline_option_row = baseline_option_row + 1
    current_row += 1

def add_search_strategy_control(master: Misc):
    global current_row
    Label(master, text='Search strategy:').grid(row=current_row, sticky='W')
    OptionMenu(master, strategy, *STRATEGIES).grid(row=current_row, column=1, columnspan=2, sticky="W")
    current_row += 1

def add_successor_generator_control(master: Misc):
    global current_row
    Label(master, text='Successor generator:').grid(row=current_row, sticky='W')
    OptionMenu(master, successor_generator, *SUCCESSOR_GENERATORS).grid(row=current_row, column=1, columnspan=2, sticky='W')
    current_row += 1

def add_query_simplification_control(master: Misc):
    global current_row
    Label(master, text="Query simplification timeout:").grid(row=current_row, sticky='W')
    raw_input = StringVar(master, value='(default)')
    def input_update(a,b,c):
        global query_simplification_timeout
        text = raw_input.get()
        timeout_input['fg'] = 'black'
        if (text == "(default)"):
            query_simplification_timeout = None
            return
        try:
            parsed = int(text)
            query_simplification_timeout = parsed
        except:
            timeout_input['fg'] = 'red'
            query_simplification_timeout = None
            
    raw_input.trace_add(['write'], input_update)
    timeout_input = Entry(master, textvariable=raw_input)
    timeout_input.grid(row=current_row, column=1, columnspan=2, sticky='W')
    current_row += 1

def add_bench_name_control(master: Misc):
    global current_row
    Label(master, text='Bench name:').grid(row=current_row, sticky='W')
    Entry(master, textvariable=bench_name).grid(row=current_row, column=1, columnspan=2, sticky="W")
    current_row += 1

def add_extra_options_control(master: Misc):
    global current_row
    Label(master, text='Extra options:').grid(row=current_row, sticky='W')
    Entry(master, textvariable=extra_bench_options).grid(row=current_row, column=1, columnspan=2, sticky='W')
    current_row += 1

def add_create_control(master: Misc):
    global current_row
    global upload_bench_button
    global create_bench_button
    upload_bench_button = Button(master, text="Create", command=create_bench_action, state=['disabled'])
    upload_bench_button.grid(row=current_row, column=0)
    create_bench_button = Button(master, text="Create and upload", command=upload_bench_action, state=['disabled'])
    create_bench_button.grid(row=current_row, column=1, columnspan=2)
    current_row += 1

def set_create_control_state(state: str):
    global upload_bench_button
    global create_bench_button
    upload_bench_button['state'] = state
    create_bench_button['state'] = state


def createUi(master: Tk):
    master.wm_title("Setup bench")
    add_staging_folder_control(master)
    add_category_control(master)
    add_baseline_control(master)
    add_search_strategy_control(master)
    add_successor_generator_control(master)
    add_query_simplification_control(master)
    add_bench_name_control(master)
    add_extra_options_control(master)
    add_create_control(master)


def main():
    createUi(master)
    restore_settings()
    mainloop()


main()