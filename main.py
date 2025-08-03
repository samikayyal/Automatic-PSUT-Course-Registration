import time as t
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
    days: str
    time: str
    is_registered: bool = False


def wait_until_not_stale_element(browser, by, value, multiple_elements=False):
    while True:
        try:
            if multiple_elements:
                return browser.find_elements(by=by, value=value)
            return browser.find_element(by=by, value=value)
        except StaleElementReferenceException:
            print("StaleElementReferenceException caught. Retrying element searching.")


TIMEOUT: int = 60  # Maximum time to attempt registration (seconds)
START_TIME: float = t.time()
USERNAME: str = ""
PASSWORD: str = ""
userInfo: List[CourseInfo] = [
    
]

service = Service()
browser = webdriver.Chrome(service=service)
browser.maximize_window()
browser.get("https://portal.psut.edu.jo/")

browser.implicitly_wait(10)

username_box = browser.find_element(by="id", value="UserID")
username_box.send_keys(USERNAME)
password_box = browser.find_element(by="id", value="loginPass")
password_box.send_keys(PASSWORD)
password_box.submit()

t.sleep(2)  # click x
wait = WebDriverWait(browser, 10)

try:
    notification_close = browser.find_element(
        by="xpath", value="/html/body/div[3]/div/div[5]/div/div/div[1]/button/span"
    )
    t.sleep(1)
    notification_close.click()
except NoSuchElementException:
    print("No notification close button found, continuing...")

regnew = browser.find_element(
    by="xpath", value="/html/body/div[3]/div/div[1]/div/div/div/div/a[1]/div"
)
regnew.click()


browser.switch_to.window(browser.window_handles[1])
lang_box = browser.find_element(by="id", value="lbtnLanguage")
lang_box.click()
regist = browser.find_element(
    by="xpath", value="/html/body/form/div[3]/table/tbody/tr[2]/td[1]/div/ul/li[7]/h3"
)
regist.click()
drop_add = browser.find_element(
    by="xpath",
    value="/html/body/form/div[3]/table/tbody/tr[2]/td[1]/div/ul/li[7]/ul/li[2]/a",
)
drop_add.click()

accept_box = browser.find_element(
    by="xpath", value="/html/body/form/div[3]/table/tbody/tr[2]/td[2]/div[2]/a"
)
accept_box.click()

rows = []


print("Starting...")
wait = WebDriverWait(browser, 20)
while True:
    for course in userInfo:
        print(f"Attempting to register for {course.name}...")
        if course.is_registered:
            print("*" * 2, f"{course.name} is already registered.", "*" * 2)
            continue

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

            t.sleep(0.8)

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
                    # Add the courses availaible to add to a list, since the GridViewRowStyle includes courses that are already registered
                    courses = [
                        course_to_add
                        for course_to_add in rows
                        if course_to_add.text.split()[0] == str(course.course_number)
                    ]

                    if len(courses) > 0:
                        break
                except StaleElementReferenceException:
                    print(
                        "StaleElementReferenceException caught. Retrying element searching."
                    )

            print("Found courses:", len(courses))

            for index, section in enumerate(courses):
                section_info = section.text.split()
                course_num = section_info[0]

                if course_num == str(course.course_number):
                    try:
                        day = browser.find_element(
                            By.ID,
                            f"ContentPlaceHolder1_gvRegistrationCoursesSchedule_lblGvDayEn_{index}",
                        )
                        time = browser.find_element(
                            By.ID,
                            f"ContentPlaceHolder1_gvRegistrationCoursesSchedule_lblGvStartTime_{index}",
                        )

                        # Ensure time and day match
                        if time.text == course.time and day.text == course.days:
                            print(
                                "*" * 8,
                                f"Found Matching Course: {course.name}",
                                "*" * 8,
                            )
                            add_button = browser.find_element(
                                By.ID,
                                f"ContentPlaceHolder1_gvRegistrationCoursesSchedule_lbtnAddCourse_{index}",
                            )
                            add_button.click()
                            course.is_registered = True
                            print(
                                "*" * 8,
                                f"Added {course.name} at",
                                time.text,
                                day.text,
                                "*" * 8,
                            )
                            break

                    except NoSuchElementException:
                        print(
                            f"Error locating time/day elements for {course.name}. Skipping.\n"
                        )

                    t.sleep(0.3)

        except NoSuchElementException as e:
            print(f"Error searching for course {course.name}: {e}")
            continue

        t.sleep(0.25)

    if all(info.is_registered for info in userInfo):
        print("All courses added successfully.")
        break

    # Break out if timeout is reached
    if t.time() - START_TIME > TIMEOUT:
        print("Registration timed out. Not all courses were added.")
        break


for course in userInfo:
    print(course)
