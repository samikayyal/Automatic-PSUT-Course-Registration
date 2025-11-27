import time
from dataclasses import dataclass
from typing import List

from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
)
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC  # noqa: F401
from selenium.webdriver.support.ui import WebDriverWait


@dataclass
class CourseInfo:
    name: str
    course_number: int
    section_number: int
    is_registered: bool = False


def wait_until_not_stale_element(browser, by, value, multiple_elements=False):
    max_retries: int = 20
    retries: int = 0
    while True:
        try:
            if multiple_elements:
                return browser.find_elements(by=by, value=value)
            return browser.find_element(by=by, value=value)
        except StaleElementReferenceException:
            print("StaleElementReferenceException caught. Retrying element searching.")
        retries += 1
        if retries >= max_retries:
            raise Exception("Max retries reached while trying to find element.")


def close_notifications(browser):
    """Close the notification box if it exists"""
    try:
        notification_close = WebDriverWait(browser, 5).until(
            EC.presence_of_element_located(
                (By.XPATH, "/html/body/div[3]/div/div[5]/div/div/div[1]/button/span")
            )
        )

        notification_close.click()
    except NoSuchElementException:
        print("No notification close button found, continuing...")


def login(browser, USERNAME: str, PASSWORD: str):
    username_box = browser.find_element(by="id", value="UserID")
    username_box.send_keys(USERNAME)
    password_box = browser.find_element(by="id", value="loginPass")
    password_box.send_keys(PASSWORD)
    password_box.submit()


def go_to_drop_add_page(browser):
    # Navigate to registration page
    regnew = browser.find_element(
        by="xpath", value="/html/body/div[3]/div/div[1]/div/div/div/div/a[1]/div"
    )
    regnew.click()

    # switch window and language selection
    browser.switch_to.window(browser.window_handles[1])
    lang_box = browser.find_element(by="id", value="lbtnLanguage")
    lang_box.click()

    regist = browser.find_element(
        by="xpath",
        value="/html/body/form/div[3]/table/tbody/tr[2]/td[1]/div/ul/li[7]/h3",
    )
    regist.click()

    # Go to drop and add page and accept terms
    drop_add = browser.find_element(
        by="xpath",
        value="/html/body/form/div[3]/table/tbody/tr[2]/td[1]/div/ul/li[7]/ul/li[2]/a",
    )
    drop_add.click()

    accept_box = browser.find_element(
        by="xpath", value="/html/body/form/div[3]/table/tbody/tr[2]/td[2]/div[2]/a"
    )
    accept_box.click()


def perform_registration(browser, userInfo: List[CourseInfo], TIMEOUT, START_TIME):
    while True:
        for course in userInfo:
            if course.is_registered:
                print("*" * 2, f"{course.name} is already registered.", "*" * 2)
                continue
            print(f"Attempting to register for {course.name}...")

            try:
                course_id_box = wait_until_not_stale_element(
                    browser, By.ID, "ContentPlaceHolder1_TxtCourseNo"
                )
                course_id_box.clear()
                course_id_box.send_keys(f"{course.course_number}")

                search = wait_until_not_stale_element(
                    browser, By.ID, "ContentPlaceHolder1_btnSearch"
                )
                search.click()

                time.sleep(0.75)  # wait for search results to load

                # get course info
                # wait until the rows are present
                # they might take a while to load so we keep checking until some are present
                # note if incorrect course number is entered or the course is not available,
                # this will be an infinite loop
                while True:
                    try:
                        rows = wait_until_not_stale_element(
                            browser,
                            By.CLASS_NAME,
                            "GridViewRowStyle",
                            multiple_elements=True,
                        )
                        # Add the courses availaible to add to a list,
                        # since the GridViewRowStyle includes courses that are already registered
                        courses = [
                            course_to_add
                            for course_to_add in rows
                            if course_to_add.text.split()[0]
                            == str(course.course_number)
                        ]

                        if len(courses) > 0:
                            break
                    except StaleElementReferenceException:
                        print(
                            "StaleElementReferenceException caught. Retrying element searching."
                        )

                print("Found courses:", len(courses))

                # Loop through the sections
                for index, section in enumerate(courses):
                    section_info = section.text.split()
                    course_num = section_info[0]

                    if course_num != str(course.course_number):
                        continue

                    # Check if this is the desired section
                    try:
                        section_number = WebDriverWait(browser, 5).until(
                            EC.presence_of_element_located(
                                (
                                    By.ID,
                                    f"ContentPlaceHolder1_gvRegistrationCoursesSchedule_lblGvSections_{index}",
                                )
                            )
                        )
                        if int(section_number.text) != course.section_number:
                            continue
                    except NoSuchElementException:
                        print(
                            f"Error locating section number element for {course.name}. Skipping.\n"
                        )

                    # Register
                    try:
                        print(
                            "*" * 8,
                            f"Found Matching Course: {course.name}",
                        )
                        add_button = browser.find_element(
                            By.ID,
                            f"ContentPlaceHolder1_gvRegistrationCoursesSchedule_lbtnAddCourse_{index}",
                        )
                        add_button.click()
                        course.is_registered = True
                        print("*" * 8, f"Added {course.name}", "*" * 8)
                        break
                    except NoSuchElementException:
                        print(
                            f"Error locating add button for {course.name}. Skipping.\n"
                        )
                    time.sleep(0.3)

            except Exception as e:
                print(
                    f"An error occurred while attempting to register for {course.name}: {e}"
                )
                continue

        if all(info.is_registered for info in userInfo):
            print("All courses added successfully.")
            break

        # Break out if timeout is reached
        if time.time() - START_TIME > TIMEOUT:
            print("Registration timed out. Not all courses were added.")
            break


def main(
    TIMEOUT: int,
    START_TIME: float,
    USERNAME: str,
    PASSWORD: str,
    userInfo: List[CourseInfo],
):
    service = Service()
    browser = webdriver.Chrome(service=service)
    browser.maximize_window()
    browser.get("https://portal.psut.edu.jo/")

    browser.implicitly_wait(10)

    try:
        # Perform login
        login(browser, USERNAME, PASSWORD)

        # Wait for potential notifications and close them
        close_notifications(browser)

        # Navigate to drop/add page
        go_to_drop_add_page(browser)

        print("Starting...")
        perform_registration(browser, userInfo, TIMEOUT, START_TIME)
    finally:
        browser.quit()


if __name__ == "__main__":
    TIMEOUT: int = 60  # Maximum time to attempt registration (seconds)
    START_TIME: float = time.time()
    USERNAME: str = ""
    PASSWORD: str = ""

    userInfo: List[CourseInfo] = []

    main(TIMEOUT, START_TIME, USERNAME, PASSWORD, userInfo)
