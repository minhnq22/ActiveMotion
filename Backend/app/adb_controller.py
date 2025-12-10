"""
ADB Controller Module
Handles Android device interactions via either `adbutils` (if installed)
or falls back to the system `adb` CLI when `adbutils` is unavailable.
"""

import os
import time
import subprocess
import shlex
from typing import Optional, Tuple, List
from pathlib import Path

# Configuration
BASE_DIR = Path(__file__).parent.parent
SCREENSHOT_DIR = BASE_DIR.parent / "Data" / "screenshots"


# Try to import adbutils (preferred). If missing, provide a lightweight
# fallback using the `adb` CLI so the app can still function without
# the `adbutils` Python package installed.
USE_ADBUTILS = False
try:
    from adbutils import adb  # type: ignore
    USE_ADBUTILS = True
except Exception:
    adb = None


class CLIAdbDevice:
    """Lightweight wrapper around the adb CLI for a single device."""

    def __init__(self, serial: str):
        self.serial = serial

    def _adb_cmd(self, cmd: str) -> bytes:
        # Do NOT quote the command string; quoting causes 'adb: unknown command ...' errors
        full = f"adb -s {self.serial} {cmd}"
        proc = subprocess.run(full, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            raise Exception(proc.stderr.decode(errors="ignore") or "adb command failed")
        return proc.stdout

    def shell(self, cmd: str) -> str:
        # Do NOT quote the command here; quoting causes 'adb: unknown command ...' errors
        out = self._adb_cmd(f"shell {cmd}")
        return out.decode(errors="ignore")

    def screenshot(self) -> bytes:
        # Use exec-out + screencap to get PNG bytes
        proc = subprocess.run([
            "adb", "-s", self.serial, "exec-out", "screencap", "-p"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            raise Exception(proc.stderr.decode(errors="ignore") or "screencap failed")
        return proc.stdout


class CLIAdb:
    """Minimal adb-like interface exposing `device_list` and `server_version`."""

    @staticmethod
    def server_version() -> Optional[str]:
        proc = subprocess.run(["adb", "version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            raise Exception("adb not found or not working")
        return proc.stdout.decode(errors="ignore")

    @staticmethod
    def device_list() -> List[CLIAdbDevice]:
        proc = subprocess.run(["adb", "devices"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            raise Exception(proc.stderr.decode(errors="ignore") or "adb devices failed")
        text = proc.stdout.decode(errors="ignore")
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        devices = []
        for line in lines[1:]:  # skip header
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "device":
                devices.append(CLIAdbDevice(parts[0]))
        return devices


class ADBController:
    """Manages ADB connection and device interactions."""

    def __init__(self):
        self.device = None
        self.connect()

    def connect(self):
        """Connect to the first available ADB device."""
        try:
            source = adb if USE_ADBUTILS else CLIAdb
            devices = source.device_list()
            if not devices:
                raise Exception("No ADB devices found. Please connect a device.")

            self.device = devices[0]
            print(f"✅ Connected to device: {self.device.serial}")
            return True
        except Exception as e:
            print(f"❌ ADB Connection Error: {e}")
            self.device = None
            return False
    
    def get_status(self) -> dict:
        """
        Get detailed ADB status.
        Returns:
            dict: {
                "status": "connected" | "disconnected" | "unauthorized" | "adb_missing" | "error",
                "message": "...",
                "device": serial or None
            }
        """
        try:
            # Check if ADB server is running/available
            source = adb if USE_ADBUTILS else CLIAdb
            try:
                source.server_version()
            except Exception:
                return {"status": "adb_missing", "message": "ADB not installed or server not running", "device": None}

            current_devices = source.device_list()
            
            if not current_devices:
                 self.device = None
                 return {"status": "disconnected", "message": "No devices found", "device": None}

            # We have devices. Check if our stored device is still there, or pick the first one.
            target_device = None
            if self.device:
                # Check if stored device is in current list
                if any(d.serial == self.device.serial for d in current_devices):
                    target_device = self.device
                else:
                    self.device = None # Stored device lost
            
            # If no stored device (or lost), pick first available
            if not target_device:
                target_device = current_devices[0]
                self.device = target_device
                print(f"✅ Connected to device: {self.device.serial}")

            # Check if authorized by trying a simple shell command
            try:
                # This will fail if unauthorized
                target_device.shell("echo test")
                return {"status": "connected", "message": "Connected", "device": target_device.serial}
            except Exception as e:
                error_msg = str(e).lower()
                if "unauthorized" in error_msg:
                     return {"status": "unauthorized", "message": "Device unauthorized", "device": target_device.serial}
                elif "offline" in error_msg:
                     return {"status": "offline", "message": "Device offline", "device": target_device.serial}
                
                return {"status": "error", "message": f"Connection error: {str(e)}", "device": target_device.serial}

        except Exception as e:
             self.device = None
             return {"status": "error", "message": str(e), "device": None}

    def is_connected(self) -> bool:
        """Check if device is connected and authorized."""
        status = self.get_status()
        return status["status"] == "connected"
    
    def take_screenshot(self, filename: str) -> str:
        """
        Capture screenshot and save to data/screenshots.
        
        Args:
            filename: Name of the screenshot file (e.g., 'screen1.png')
        
        Returns:
            Path to the saved screenshot (relative to screenshots dir)
        """
        if not self.is_connected():
            raise Exception("Device not connected")
        
        # Ensure screenshots directory exists
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        
        # Capture screenshot
        screenshot_path = SCREENSHOT_DIR / filename
        image_data = self.device.screenshot()

        # If CLI fallback returns raw bytes, write them directly.
        try:
            # If object has .save (e.g., PIL Image from adbutils), use it.
            save_method = getattr(image_data, "save", None)
            if callable(save_method):
                image_data.save(str(screenshot_path))
            else:
                # Assume bytes
                with open(screenshot_path, "wb") as f:
                    if isinstance(image_data, bytes):
                        f.write(image_data)
                    else:
                        # Fallback: convert to str then bytes
                        f.write(str(image_data).encode())

            print(f"📸 Screenshot saved: {screenshot_path}")
            return filename
        except Exception as e:
            raise Exception(f"Failed to save screenshot: {e}")
    
    def dump_hierarchy(self) -> str:
        """
        Get the current UI hierarchy as XML.
        
        Returns:
            XML string of the current screen hierarchy
        """
        if not self.is_connected():
            raise Exception("Device not connected")
        
        # Dump UI hierarchy to a temp file on device
        # Note: 'uiautomator dump' defaults to /sdcard/window_dump.xml
        # We use a specific path to avoid conflicts or permission issues if possible, 
        # but /sdcard/window_dump.xml is the standard default.
        temp_path = "/sdcard/window_dump.xml"
        
        # Run dump command
        # It might output "UI hierchary dumped to: ..." to stdout, so we ignore the return string of this command
        self.device.shell(f"uiautomator dump {temp_path}")
        
        # Read the file content using cat
        xml_data = self.device.shell(f"cat {temp_path}")
        
        # Optional: Clean up
        # self.device.shell(f"rm {temp_path}")
        
        return xml_data
    
    def tap(self, x: int, y: int):
        """
        Simulate a tap at coordinates (x, y).
        
        Args:
            x: X coordinate
            y: Y coordinate
        """
        if not self.is_connected():
            raise Exception("Device not connected")
        
        self.device.shell(f"input tap {x} {y}")
        print(f"👆 Tapped at ({x}, {y})")
        time.sleep(0.5)  # Small delay to let UI update
    
    def input_text(self, text: str):
        """
        Send text input to the device.
        
        Args:
            text: Text to input
        """
        if not self.is_connected():
            raise Exception("Device not connected")
        
        # Escape special characters
        escaped_text = text.replace(' ', '%s')
        self.device.shell(f"input text {escaped_text}")
        print(f"⌨️  Input text: {text}")
    
    def press_key(self, keycode: str):
        """
        Press a key (e.g., 'KEYCODE_BACK', 'KEYCODE_HOME').
        
        Args:
            keycode: Android keycode
        """
        if not self.is_connected():
            raise Exception("Device not connected")
        
        self.device.shell(f"input keyevent {keycode}")
        print(f"🔑 Pressed: {keycode}")
    
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300):
        """
        Perform a swipe gesture.
        
        Args:
            x1, y1: Start coordinates
            x2, y2: End coordinates
            duration_ms: Duration of the swipe in milliseconds
        """
        if not self.is_connected():
            raise Exception("Device not connected")
        
        self.device.shell(f"input swipe {x1} {y1} {x2} {y2} {duration_ms}")
        print(f"👉 Swiped from ({x1},{y1}) to ({x2},{y2})")
    
    def get_screen_size(self) -> Tuple[int, int]:
        """
        Get device screen size.
        
        Returns:
            (width, height) tuple
        """
        if not self.is_connected():
            raise Exception("Device not connected")
        
        result = self.device.shell("wm size")
        # Parse: "Physical size: 1080x2400"
        size_str = result.split(":")[-1].strip()
        width, height = map(int, size_str.split("x"))
        return (width, height)
    
    def get_current_package(self) -> str:
        """
        Get the currently running app package name.
        
        Returns:
            Package name (e.g., 'com.android.chrome')
        """
        info = self.get_current_activity_info()
        return info["package"]

    def get_current_activity_info(self) -> dict:
        """
        Get the currently running app package and activity name.
        
        Returns:
            dict: {"package": str, "activity": str}
        """
        if not self.is_connected():
            raise Exception("Device not connected")
        
        # Run dumpsys window (broader than 'windows' subcommand on some devices)
        try:
            result = self.device.shell("dumpsys window")
        except Exception:
            # Fallback or retry
            return {"package": "unknown", "activity": "unknown"}
        
        package = "unknown"
        activity = "unknown"
        
        # Parse output for mCurrentFocus
        # Expected line: mCurrentFocus=Window{... u0 com.package/com.package.Activity}
        for line in result.splitlines():
            if "mCurrentFocus" in line and "Window{" in line:
                # Clean up the string
                clean_line = line.strip().rstrip('}')
                parts = clean_line.split()
                for part in parts:
                    if "/" in part:
                        try:
                            # Split package/activity
                            comp = part.split("/")
                            if len(comp) >= 2:
                                package = comp[0]
                                activity = comp[1]
                                
                                # Handle relative activity names (starting with .)
                                if activity.startswith("."):
                                    activity = package + activity
                                
                                # Sometimes the part might have a closing brace
                                if "}" in activity:
                                    activity = activity.replace("}", "")
                                
                                break
                        except Exception:
                            pass
                break
        
        return {"package": package, "activity": activity}

    def save_device_info_snapshot(self, output_filename: Optional[str] = None, xml_data: Optional[str] = None, activity_info: Optional[dict] = None) -> str:
        """
        Retrieves Package Name, Activity Name, and XML Hierarchy, 
        and saves them to a log file in the Data directory.
        
        Args:
            output_filename: Optional filename. If None, generates one with timestamp.
            xml_data: Optional pre-fetched XML hierarchy string.
            activity_info: Optional pre-fetched activity info dict.
        
        Returns:
            str: Path to the saved log file.
        """
        try:
            if activity_info:
                info = activity_info
            else:
                info = self.get_current_activity_info()
            
            if xml_data:
                xml_hierarchy = xml_data
            else:
                xml_hierarchy = self.dump_hierarchy()
            
            # Define log directory: ActiveMotion/Data/logs
            log_dir = BASE_DIR.parent / "Data" / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)

            if output_filename:
                filename = output_filename
            else:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"device_snapshot_{timestamp}.log"
            
            file_path = log_dir / filename
            
            content = f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            content += f"Package Name: {info['package']}\n"
            content += f"Activity Name: {info['activity']}\n\n"
            content += "--- XML Hierarchy ---\n"
            content += xml_hierarchy
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
                
            print(f"📝 Device info saved to: {file_path}")
            return str(file_path)
            
        except Exception as e:
            print(f"❌ Failed to save device info snapshot: {e}")
            raise e


# Singleton instance
_adb_controller = None

def get_adb_controller() -> ADBController:
    """Get or create the singleton ADB controller instance."""
    global _adb_controller
    if _adb_controller is None:
        _adb_controller = ADBController()
    return _adb_controller
