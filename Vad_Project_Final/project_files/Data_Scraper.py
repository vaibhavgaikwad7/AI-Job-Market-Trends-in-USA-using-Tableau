import os
import time
import random
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

# Initialize Selenium WebDriver
service = Service(ChromeDriverManager().install())
options = webdriver.ChromeOptions()
ua = UserAgent()
options.add_argument(f"user-agent={ua.random}")
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
driver = webdriver.Chrome(service=service, options=options)

# Open LinkedIn Jobs Search Page
search_url = "https://www.linkedin.com/jobs/search/?keywords=AI&location=United%20States"
driver.get(search_url)
time.sleep(5)

# Scroll dynamically to load more jobs
last_height = driver.execute_script("return document.body.scrollHeight")
for _ in range(20):
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(random.uniform(2, 4))


    new_height = driver.execute_script("return document.body.scrollHeight")
    if new_height == last_height:
        break
    last_height = new_height

# Extract job listings
soup = BeautifulSoup(driver.page_source, "html.parser")
job_cards = soup.find_all("div", class_="base-card")


# Load existing data to prevent duplicates
file_path = "linkedin_ai_jobs.csv"
if os.path.exists(file_path):
    df_existing = pd.read_csv(file_path)
    existing_links = set(df_existing["Job Link"])
else:
    df_existing = pd.DataFrame()
    existing_links = set()

job_list = []
for job in job_cards:
    try:
        title = job.find("h3").text.strip()
        company = job.find("h4").text.strip()
        location = job.find("span", class_="job-search-card__location").text.strip()
        link = job.find("a", class_="base-card__full-link")["href"]
        date_posted = job.find("time")["datetime"] if job.find("time") else "Not Provided"

        if link in existing_links:
            continue


        driver.execute_script(f"window.open('{link}', '_blank');")
        driver.switch_to.window(driver.window_handles[1])
        time.sleep(random.uniform(3, 5))
        job_soup = BeautifulSoup(driver.page_source, "html.parser")

        # Extract job description
        job_desc = job_soup.find("div", class_="description__text")
        job_text = job_desc.text.strip() if job_desc else ""

        # Extract AI-related skills
        ai_skills = ["Python", "TensorFlow", "PyTorch", "NLP", "Computer Vision", "C++", "R", "Deep Learning", "Machine Learning", "Data Science"]
        extracted_skills = [skill for skill in ai_skills if skill.lower() in job_text.lower()]

        # Identify Experience Level
        experience_keywords = {
            "Entry Level": ["entry level", "junior", "graduate", "new grad"],
            "Mid Level": ["mid level", "experienced", "intermediate", "2+ years"],
            "Senior Level": ["senior", "lead", "principal", "5+ years", "expert"]
        }
        experience_level = "Not Specified"
        for level, keywords in experience_keywords.items():
            if any(keyword in job_text.lower() for keyword in keywords):
                experience_level = level
                break

        # Identify Job Type with Regex Matching
        import re
        job_types = ["Full-time", "Part-time", "Contract", "Internship", "Temporary", "Freelance"]
        job_type = "Not Specified"
        for jt in job_types:
            if re.search(rf"\b{jt.replace('-', ' ')}\b", job_text, re.IGNORECASE):
                job_type = jt
                break

        # Identify Remote vs. On-site Classification
        remote_keywords = ["remote", "work from home", "fully remote"]
        hybrid_keywords = ["hybrid", "some remote"]
        if any(word in location.lower() for word in remote_keywords) or any(word in job_text.lower() for word in remote_keywords):
            work_type = "Remote"
        elif any(word in job_text.lower() for word in hybrid_keywords):
            work_type = "Hybrid"
        else:
            work_type = "On-site"

        job_list.append({
            "Scrape Date": pd.Timestamp.today().date(),
            "Job Title": title,
            "Company": company,
            "Location": location,
            "Date Posted": date_posted,
            "Experience Level": experience_level,
            "Job Type": job_type,
            "Work Type": work_type,
            "Skills Required": ", ".join(extracted_skills) if extracted_skills else "Not Provided",
            "Job Link": link,
            #"Salary": salary
        })

        # Close tab and switch back to main tab
        driver.close()
        driver.switch_to.window(driver.window_handles[0])

    except AttributeError:
        continue
    except Exception as e:
        print(f"Error processing job {link}: {e}")

driver.quit()

# Convert to DataFrame
df_new = pd.DataFrame(job_list)

# Append only new jobs and save
df_combined = pd.concat([df_existing, df_new], ignore_index=True)
df_combined.to_csv(file_path, index=False)

print(f"{len(df_new)} New AI Job Listings Collected and Saved! (Total: {len(df_combined)})")

