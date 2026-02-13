import time
import pyautogui
import pyperclip
import cv2 as cv
import numpy as np
from mss import mss

paper_links = []


def capture_screen():
    # Capture main screen
    with mss() as sct:
        monitor = sct.monitors[1]  # Capture the primary monitor
        screenshot = sct.grab(monitor)
        # Convert the screenshot to a format suitable for OpenCV
        img = np.array(screenshot)
        # convert from BGRA to BGR
        img = cv.cvtColor(img, cv.COLOR_BGRA2BGR)
    return img, monitor


def get_link_address() -> str:
    # Right click on the mouse
    pyautogui.rightClick()
    # Wait for the context menu to appear
    time.sleep(0.5)
    # Move the mouse to the "Copy link address" option
    pyautogui.move(40, 190)
    # Click to copy the link address
    pyautogui.click()
    # Get clipboard content
    link_address = pyperclip.paste()
    return link_address


def detect_mark(img, template, threshold=0.8):
    # Perform template matching
    result = cv.matchTemplate(
        cv.cvtColor(img, cv.COLOR_BGR2GRAY), template, cv.TM_CCOEFF_NORMED
    )
    # Set a threshold for detection
    loc = np.where(result >= threshold)
    # If the points are less than 20 pixels apart, consider them as the same point
    unique_points = []
    for pt in zip(*loc[::-1]):
        if all(
            np.linalg.norm(np.array(pt) - np.array(up)) > 20 for up in unique_points
        ):
            unique_points.append(pt)

    # # Draw rectangles around detected marks
    # for pt in unique_points:
    #     cv.rectangle(
    #         img,
    #         pt,
    #         (pt[0] + template.shape[1], pt[1] + template.shape[0]),
    #         (0, 255, 0),
    #         2,
    #     )
    # cv.imshow("Detected Marks", img)
    # cv.waitKey(0)
    # cv.destroyAllWindows()

    return unique_points


def process_mark_locations(location, monitor, page):
    # Move to the paper title location
    time.sleep(0.5)
    pyautogui.moveTo(
        location[0] + monitor["left"] + 45, location[1] + monitor["top"] - 70
    )
    time.sleep(0.5)
    # Get the link address
    link_address = get_link_address()
    if len(paper_links) > 0:
        if link_address == paper_links[-1] and link_address != "javascript:void(0)":
            print(f"Found error at page {page + 1}")
            # Capture the screen for debugging
            img, monitor = capture_screen()
            # Mark the location of the error
            cv.rectangle(
                img,
                (location[0] - 50, location[1] - 100),
                (location[0] + 1000, location[1] + 20),
                (0, 0, 255),
                2,
            )
            # Save the image for debugging
            cv.imwrite(
                f"./temp/error_page_{page + 1}_{location[0]}_{location[1]}.png", img
            )
            return

    paper_links.append(link_address)


def process_a_page(template, page):
    # Scroll to the top of the page
    pyautogui.scroll(1000)
    time.sleep(1)  # Wait for the page to adjust
    # Capture top half of the screen
    img, monitor = capture_screen()
    locations = detect_mark(img, template)
    # Process paper 1 - 6
    for location in locations[:6]:
        process_mark_locations(location, monitor, page)
        time.sleep(0.5)
    # Go to center
    pyautogui.moveTo(
        monitor["left"] + monitor["width"] / 2, monitor["top"] + monitor["height"] / 2
    )
    time.sleep(1)
    # Scroll to the bottom of the page
    pyautogui.scroll(-600)
    time.sleep(1)  # Wait for the page to adjust
    # Capture the bottom area of the screen
    img, monitor = capture_screen()
    # Process paper 7 - 10
    locations = detect_mark(img, template)[-4:]
    for location in locations:
        process_mark_locations(location, monitor, page)
        time.sleep(0.5)


def next_page():
    # Scroll down
    pyautogui.scroll(-500)
    time.sleep(1)  # Wait for the page to adjust
    with mss() as sct:
        monitor = sct.monitors[1]  # Capture the primary monitor
    pyautogui.moveTo(
        monitor["left"] + monitor["width"] / 2 - 410,
        monitor["top"] + monitor["height"] - 135,
    )
    time.sleep(0.5)
    pyautogui.click()
    time.sleep(2)  # Wait for the page to load


if __name__ == "__main__":
    template = cv.imread("google_scholar_mark.png", cv.IMREAD_GRAYSCALE)
    with mss() as sct:
        monitor = sct.monitors[1]  # Capture the primary monitor
    # Go to center of the screen
    pyautogui.moveTo(
        monitor["left"] + monitor["width"] / 2, monitor["top"] + monitor["height"] / 2
    )
    for page in range(50):
        process_a_page(template, page)
        next_page()
    # Save the links to a file
    with open("paper_links.txt", "w+") as f:
        for link in paper_links:
            f.write(link + "\n")
