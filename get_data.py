from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import StaleElementReferenceException
import pandas as pd
import time
import re

# ===============================
# start
# ===============================
def start_driver():
    options = Options()
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 10)

    driver.get("https://vietnamtourism.gov.vn/statistic/international")
    wait.until(lambda d: len(d.find_elements(By.TAG_NAME, "select")) >= 2)

    return driver


driver = start_driver()
final_data = []

# ===============================
# get total
# ===============================
def get_total():
    for _ in range(10):
        try:
            rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")

            for row in rows:
                cols = row.find_elements(By.TAG_NAME, "td")

                if len(cols) >= 2:
                    col_text = cols[0].text
                    if not col_text:
                        continue

                    if "tổng" in col_text.lower():
                        value = cols[1].text
                        if not value:
                            continue

                        value = value.strip().replace(".", "").replace(",", "")
                        if value.isdigit():
                            return int(value)

        except StaleElementReferenceException:
            time.sleep(0.2)

        time.sleep(0.3)

    return None


# ===============================
# get estimate value
# ===============================
def is_invalid(value):
    # Ignore unwanted ranges
    if 1 <= value <= 12:
        return True
    if 1900 <= value <= 2100:
        return True
    return False


def get_estimated_value():
    for _ in range(15):
        try:
            elements = driver.find_elements(By.XPATH, "//*[contains(., 'Ước tính tháng')]")

            for el in elements:
                text = el.text.strip()

                numbers = re.findall(r'[\d\.]+', text)

                for num in numbers:
                    value = int(num.replace(".", ""))

                    if is_invalid(value):
                        continue

                    if 0 <= value <= 20000000:
                        return value

                if not numbers:
                    continue

                value = int(numbers[-1].replace(".", ""))

                if is_invalid(value):
                    continue

                return value

        except:
            pass

        time.sleep(0.5)

    return None
# ===============================
# Check Jan == Dec
# ===============================
def is_jan_equal_dec(month_data):
    if len(month_data) < 12:
        return False

    jan = month_data[0]
    dec = month_data[11]

    if jan is None or dec is None:
        return False

    return jan == dec
# ===============================
# table change
# ===============================
def wait_for_table_change(old_value):
    for _ in range(10):
        time.sleep(0.5)
        val = get_total()
        if val and old_value and val != old_value:
            return val
    return val


# ===============================
# year
# ===============================
def select_year(year):
    selects = driver.find_elements(By.TAG_NAME, "select")
    year_select = Select(selects[0])

    for opt in year_select.options:
        numbers = re.findall(r'\d+', opt.text)
        if numbers and int(numbers[0]) == year:
            opt.click()
            return True

    return False


# ===============================
# month
# ===============================
def select_month(month):
    selects = driver.find_elements(By.TAG_NAME, "select")
    month_select = Select(selects[1])

    for opt in month_select.options:
        numbers = re.findall(r'\d+', opt.text)
        if numbers and int(numbers[0]) == month:
            opt.click()
            return True

    return False

# ===============================
# main
# ===============================
for year in range(2008, 2027):
    print("Year", year)

    if not select_year(year):
        print(" Year not found")
        continue

    time.sleep(1)

    select_month(12)
    time.sleep(1)

    for month in range(12, 0, -1):
        print("  Month", month)

        if not select_month(month):
            print("    Cannot select month")
            continue

        time.sleep(0.8)

        prev_value = final_data[-1]["y"] if final_data else None

        # ===============================
        # jan fix
        # ===============================
        if month == 1:
            print("    getting January estimate")

            total = None

            for _ in range(20):
                time.sleep(0.8)

                est = get_estimated_value()

                if est is not None:
                    total = est
                    break

            if total is None:
                total = get_total()
                continue
        # ===============================
        # dec
        # ===============================
        elif month == 12:
            time.sleep(1.5)
            total = get_estimated_value()

            if total is None:
                total = get_total()
        # ===============================
        # normal month
        # ===============================
        else:
            total = wait_for_table_change(prev_value)

        # fallback
        if total is None:
            total = get_total()

        if total is None:
            print("    failed")
            continue

        print(f"     {total}")

        final_data.append({
            "ds": f"{year}-{month:02d}",
            "y": total
        })


# ===============================
# save cvs
# ===============================
driver.quit()

df = pd.DataFrame(final_data)
df["ds"] = pd.to_datetime(df["ds"])
df = df.sort_values("ds")

df.to_csv("tourism_final.csv", index=False)

print("DONE")