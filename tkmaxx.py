import os
import csv
import time
import threading
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from tkinter import ttk
import tkinter as tk
from tkinter import filedialog, messagebox

# Global variable to store selected folder
selected_folder = None


def configure_driver():
    """Configures and returns a Selenium WebDriver."""
    options = Options()
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-webgl")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("start-maximized")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
    )

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def scrape_tkmaxx(category, sort, save_folder, progress_bar, status_label):
    """Scrapes product data from TKMaxx."""
    driver = configure_driver()
    try:
        site_url = "https://www.tkmaxx.com"
        full_url = f"{site_url}/uk/en/search?st={category}&sort={sort}&facet=&page=0"
        print(f"Navigating to: {full_url}")
        status_label.config(text="Navigating to the TKMaxx site...")
        driver.get(full_url)

        # Handle the cookie banner
        try:
            allow_all_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
            )
            allow_all_button.click()
            print("Clicked 'ALLOW ALL' on cookie banner.")
            time.sleep(3)
        except Exception:
            print("Cookie banner not found or could not be clicked.")

        # Check for product count
        soup = BeautifulSoup(driver.page_source, "html.parser")
        product_elements = soup.find_all("li", class_="c-product-grid__item")
        product_links = []

        if len(product_elements) < 72:
            print(f"Found {len(product_elements)} products, no need to paginate.")
        else:
            # Scroll and click "LOAD MORE" until all products are loaded
            while True:
                try:
                    load_more_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CLASS_NAME, "load-more-btn"))
                    )
                    driver.execute_script(
                        "arguments[0].scrollIntoView(true);", load_more_button
                    )
                    time.sleep(2)
                    load_more_button.click()
                    print("Clicked 'LOAD MORE' button.")
                    time.sleep(5)
                except Exception:
                    print("No more 'LOAD MORE' button found.")
                    break

        # Collect product links
        soup = BeautifulSoup(driver.page_source, "html.parser")
        product_elements = soup.find_all("li", class_="c-product-grid__item")
        for product in product_elements:
            link = product.find("a", class_="c-product-card")
            if link and link["href"]:
                product_links.append(site_url + link["href"])

        print(f"Found {len(product_links)} product links.")

        # Update progress bar maximum
        progress_bar["maximum"] = len(product_links)

        # Scrape product details
        data = []
        for index, link in enumerate(product_links, start=1):
            driver.get(link)
            time.sleep(2)

            soup = BeautifulSoup(driver.page_source, "html.parser")
            pdp_block = soup.find("div", class_="pdp-info-block")
            name = (
                pdp_block.find("h1").get_text(strip=True)
                if pdp_block and pdp_block.find("h1")
                else "N/A"
            )
            price = (
                pdp_block.find("p", class_="item-price-original").get_text(strip=True)
                if pdp_block and pdp_block.find("p", class_="item-price-original")
                else "N/A"
            )
            description = (
                soup.find("div", class_="pdp-tabs-product-description").get_text(strip=True)
                if soup.find("div", class_="pdp-tabs-product-description")
                else "N/A"
            )
            data.append([name, description, price, link])

            # Update progress bar
            progress_bar["value"] = index
            status_label.config(text=f"Processing product: {name}")
            root.update_idletasks()

        save_to_csv(save_folder, data, ["Name", "Description", "Price", "Link"])
        status_label.config(text="Scraping complete! Check the output folder.")
    finally:
        driver.quit()


def save_to_csv(folder, data, headers):
    """Saves data to a CSV file."""
    if not folder:
        folder = os.getcwd()
    csv_file = os.path.join(folder, "tkmaxx_products.csv")
    with open(csv_file, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        writer.writerows(data)
    print(f"Data saved to {csv_file}")


def select_folder():
    """Opens a folder selection dialog."""
    global selected_folder
    selected_folder = filedialog.askdirectory()
    if selected_folder:
        messagebox.showinfo("Folder Selected", f"Files will be saved in: {selected_folder}")
    else:
        messagebox.showinfo(
            "No Folder Selected", "Files will be saved in the script's directory."
        )


def start_scraping_thread():
    """Starts the scraping process in a separate thread."""
    category = category_entry.get()
    sort_text = sort_option.get()
    sort_value = SORT_OPTIONS.get(sort_text, "")

    if not category:
        messagebox.showwarning("Input Error", "Please provide a product category.")
        return

    progress_bar["value"] = 0
    status_label.config(text="Starting the scraping process...")
    threading.Thread(
        target=scrape_tkmaxx,
        args=(category, sort_value, selected_folder, progress_bar, status_label),
        daemon=True,
    ).start()


# Mapping of descriptive text to option values
SORT_OPTIONS = {
    "": "",
    "Recommended": "Recommended",
    "Price (low to high)": "price_asc",
    "Price (high to low)": "price_des",
    "Newest": "published_date",
    "Wow savings (high to low)": "percent_saving",
    "Alphabetical": "brand_asc",
}

# Set up Tkinter GUI
root = tk.Tk()
root.title("TKMaxx Scraper")

# Add padding and headers
frame = ttk.Frame(root, padding="10")
frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

# Product category
ttk.Label(frame, text="Enter Product Category:").grid(row=0, column=0, sticky=tk.W)
category_entry = ttk.Entry(frame, width=50)
category_entry.grid(row=0, column=1, sticky=tk.E)

# Sort option
ttk.Label(frame, text="Select Sort Option:").grid(row=1, column=0, sticky=tk.W)
sort_option = tk.StringVar(value="")
sort_menu = ttk.OptionMenu(frame, sort_option, *SORT_OPTIONS.keys())
sort_menu.grid(row=1, column=1, sticky=tk.E)

# Folder selection and scrape buttons
ttk.Button(frame, text="Select Folder", command=select_folder).grid(row=2, column=0, sticky=tk.W)
ttk.Button(frame, text="Scrape", command=start_scraping_thread).grid(row=2, column=1, sticky=tk.E)

# Progress bar
progress_bar = ttk.Progressbar(frame, orient="horizontal", length=400, mode="determinate")
progress_bar.grid(row=3, column=0, columnspan=2, pady=10)

# Status label
status_label = ttk.Label(frame, text="")
status_label.grid(row=4, column=0, columnspan=2, sticky=tk.W)

root.mainloop()
