import os
import cv2
import flet as ft
from subprocess import Popen, PIPE, run
import threading
import asyncio


def source_setup_env(script_path):
    """
    Source a shell script and return the environment variables as a dictionary.
    """
    command = f"bash -c 'source {script_path} && env'"
    process = Popen(command, stdout=PIPE, shell=True, text=True)
    env_vars = {}
    for line in process.stdout:
        key, _, value = line.strip().partition("=")
        env_vars[key] = value
    process.communicate()
    return env_vars


def get_usb_video_devices():
    """
    Get a list of USB video devices connected to the system.
    """
    devices = []
    for device in os.listdir("/dev"):
        if "video" in device:
            device_path = f"/dev/{device}"
            try:
                # Use udevadm to check if the device is a USB device
                result = run(
                    ["udevadm", "info", "--query=all", "--name=" + device_path],
                    stdout=PIPE,
                    stderr=PIPE,
                    text=True,
                )
                output = result.stdout
                if "ID_BUS=usb" in output:
                    # Verify if the device is functional as a camera
                    cap = cv2.VideoCapture(device_path)
                    if cap.isOpened():
                        devices.append(device_path)
                    cap.release()
            except Exception as e:
                print(f"Error checking device {device_path}: {e}")
    return devices


async def main(page: ft.Page):
    # Source the setup_env.sh script
    script_path = "./setup_env.sh"  # Replace with the actual path
    env_vars = source_setup_env(script_path)
    os.environ.update(env_vars)  # Apply the environment variables to the script

    # Verify TAPPAS_POST_PROC_DIR environment variable
    if "TAPPAS_POST_PROC_DIR" not in os.environ:
        print("Error: TAPPAS_POST_PROC_DIR is not set. Check the setup_env.sh script.")
        return

    # Set page properties
    page.title = "USB Camera Detection"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 650  # กำหนดความกว้างเริ่มต้นเป็น 800px
    page.window_height = 380  # กำหนดความสูงเริ่มต้นเป็น 600px    

    process = None  # Global variable to store the process
    stop_thread_event = threading.Event()  # Event to manage thread stop

    # Components for the UI
    pipeline_status = ft.Text(
        value="Pipeline Status: Not Started",
        size=16,
        weight=ft.FontWeight.NORMAL,
        color="white",
    )
    logs_output = ft.TextField(
        value="",
        read_only=True,
        multiline=True,
        width=250,
        height=150,
        text_style=ft.TextStyle(color="white"),
        filled=True,
        bgcolor="#333333",
    )
    device_dropdown = ft.Dropdown(
        label="Select USB Camera",
        options=[ft.dropdown.Option(device) for device in get_usb_video_devices()],
        hint_text="Select a USB camera (e.g., /dev/video0)",
        bgcolor="#333333",
        text_style=ft.TextStyle(color="white"),
        label_style=ft.TextStyle(color="white"),
    )
# Function to read logs dynamically
    def read_logs(process):
        while not stop_thread_event.is_set() and process.poll() is None:
            line = process.stdout.readline()
            if line:
                logs_output.value += line
                page.update()

    # Run pipeline function
    def run_pipeline(e):
        nonlocal process
        if not device_dropdown.value:
            pipeline_status.value = "Error: Please select a USB camera."
            page.update()
            return

        if process and process.poll() is None:
            pipeline_status.value = "Error: Pipeline already running."
            page.update()
            return

        stop_thread_event.clear()  # Reset the stop event for the thread
        selected_device = device_dropdown.value
        pipeline_status.value = f"Pipeline Status: Running on {selected_device}..."
        page.update()

        try:
            # Command to run the detection pipeline
            process = Popen(
                [
                    "python3",
                    "basic_pipelines/detection.py",
                    "--input", selected_device,
                    "--show-fps",
                    "--use-frame",  # Added this argument
                ],
                stdout=PIPE,
                stderr=PIPE,
                text=True,
                bufsize=1,
            )

            threading.Thread(target=read_logs, args=(process,), daemon=True).start()
        except Exception as ex:
            pipeline_status.value = f"Error: {str(ex)}"
            page.update()
    # Stop pipeline function
    def stop_pipeline(e):
        nonlocal process
        if process and process.poll() is None:  # Check if the process is running
            stop_thread_event.set()  # Signal the thread to stop
            process.terminate()  # Gracefully stop the process
            try:
                process.wait(timeout=2)  # Wait for process to terminate
            except:
                process.kill()  # Force kill if termination fails
            process = None  # Reset the process variable
            pipeline_status.value = "Pipeline process stopped."
        else:
            pipeline_status.value = "No running pipeline to stop."

        # Find and kill the process using /dev/hailo0
        try:
            result = run(["lsof", "/dev/hailo0"], stdout=PIPE, stderr=PIPE, text=True)
            if result.returncode == 0:  # If there are processes using /dev/hailo0
                for line in result.stdout.splitlines()[1:]:  # Skip the header line
                    parts = line.split()
                    pid = parts[1]  # The PID is the second column
                    run(["sudo", "kill", "-9", pid])  # Force kill the process
                pipeline_status.value += " Hailo device process killed."
            else:
                pipeline_status.value += " No process found using /dev/hailo0."
        except Exception as ex:
            pipeline_status.value = f"Error stopping Hailo device: {str(ex)}"
        
        page.update()


    # Refresh the dropdown with available devices
    def refresh_devices(e):
        available_devices = get_usb_video_devices()
        if available_devices:
            device_dropdown.options = [
                ft.dropdown.Option(device) for device in available_devices
            ]
            pipeline_status.value = "Device list refreshed."
        else:
            device_dropdown.options = []
            pipeline_status.value = "No USB cameras found."
        page.update()

    # New function to clear logs
    def clear_logs(e):
        logs_output.value = ""
        pipeline_status.value = "Logs cleared."
        page.update()

    # Minimalist Buttons
    run_button = ft.ElevatedButton(
        text="Run Pipeline",
        on_click=run_pipeline,
        bgcolor="#1f1f1f",
        color="white",
    )
    stop_button = ft.ElevatedButton(
        text="Stop Pipeline",
        on_click=stop_pipeline,
        bgcolor="#1f1f1f",
        color="white",
    )
    refresh_button = ft.ElevatedButton(
        text="Refresh Devices",
        on_click=refresh_devices,
        bgcolor="#1f1f1f",
        color="white",
    )
    clear_logs_button = ft.ElevatedButton(
        text="Clear Logs",
        on_click=clear_logs,
        bgcolor="#1f1f1f",
        color="white",
    )

    # Add components to the page
    page.add(
        ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        value="USB Camera Detection",
                        size=24,
                        weight=ft.FontWeight.BOLD,
                        color="white",
                    ),
                    device_dropdown,
                    ft.Row(
                        [run_button, stop_button, refresh_button,clear_logs_button],
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    pipeline_status,
                    logs_output,
                ],
                spacing=10,
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=20,
            bgcolor="#121212",
            border_radius=10,
            alignment=ft.alignment.center,
        )
    )

# Run the Flet app
ft.app(target=main)