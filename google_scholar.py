import time
import pyautogui
import cv2 as cv
import numpy as np
from mss import mss


def capture_screen(area):
    # Capture main screen
    with mss() as sct:
        monitor = sct.monitors[1]  # Capture the primary monitor
        # Adjust the capture area
        monitor = {
            "top": monitor["top"] + area["top"],
            "left": monitor["left"] + area["left"],
            "width": monitor["width"] - area["width"],
            "height": monitor["height"] - area["height"],
        }
        screenshot = sct.grab(monitor)
        # Convert the screenshot to a format suitable for OpenCV
        img = np.array(screenshot)

    return img


if __name__ == "__main__":
    # Scroll to the top of the page
    pyautogui.scroll(1000)
    time.sleep(1)  # Wait for the page to adjust
    # Capture top half of the screen
    area = {"top": 200, "left": 200, "width": 1300, "height": 200}
    img = capture_screen(area)
    cv.imshow("Captured Screen", img)
    cv.waitKey(0)
    cv.destroyAllWindows()
    # Scroll down
    pyautogui.scroll(-500)
    time.sleep(1)  # Wait for the page to adjust
    # Capture the bottom area of the screen
    area = {"top": 100, "left": 200, "width": 1300, "height": 100}
    img = capture_screen(area)
    cv.imshow("Captured Screen", img)
    cv.waitKey(0)
    cv.destroyAllWindows()
