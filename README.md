# ⚡ Lablab Team Finder & Origin Filter

A fast, lightweight tool to search, analyze, and find teams with open slots across [Lablab.ai](https://lablab.ai) hackathons.

<img width="1920" height="2104" alt="screencapture-127-0-0-1-5000-2026-09-06-19_43_32" src="https://github.com/user-attachments/assets/639c8d83-57a5-498c-ba41-88a1be1c7c78" />


---

## 🎥 Watch Video Demo
Click the link below to watch a quick walkthrough of how to use the tool:

👉 **[Watch Demo on Loom (Video Walkthrough)](https://www.loom.com/share/444af5f770ca47dbb7566effb4646804)**

---

## 🎯 Why Was This Created?

Finding the right team on Lablab.ai can be difficult when an event has hundreds of teams:
- Most teams are full or inactive.
- It takes hours to open individual team pages to check open slots and member backgrounds.
- If you only have someone's Discord ID or name, Lablab does not have a global search to find which hackathon or team they are in.

This tool solves all of that by providing:
- **Instant search (0.1s)** in saved data.
- **Open slot filtering** to immediately see teams you can actually join.
- **Origin classification** (Asian vs. International) based on profile country and name heuristics.
- **Global search by Discord ID** (e.g., `1388751820003999816`) or member name across all hackathons simultaneously.

---

## 👥 Who Should Use This?

- **Hackathon participants** looking to join an active team with open slots before deadlines.
- **Developers** seeking international teammates or specific team sizes (e.g., 3+ members).
- **Team leaders & organizers** wanting to look up members or Discord IDs across hackathons.

---

## 🚀 Step-by-Step Installation

### Step 1: Clone the Repository
```bash
git clone https://github.com/abdulmanan093/lablabai-team-finder.git
cd lablabai-team-finder
```

### Step 2: Install Required Packages
```bash
pip install -r requirements.txt
```
*(Only requires standard `requests` and `beautifulsoup4`)*

---

## 💻 How to Run

### Option 1: Web Dashboard (Recommended)
```bash
python app.py
```
Open your browser and navigate to:
👉 **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

### Option 2: Terminal Version
```bash
python lablab_team_finder.py
```

---

## 📖 Step-by-Step Usage Guide

### 1. Browse by Hackathon
1. Select any active hackathon from the top dropdown list.
2. Choose your mode:
   - **⚡ Option A (Fast Search in Saved Data):** Loads cached team data instantly (0.1s).
   - **🔄 Option B (Fetch Fresh Live Data):** Crawls the latest live teams directly from Lablab.ai and automatically saves a new snapshot to `saved_data/`.
3. Use the toolbar to filter:
   - **Keyword Search:** Search team names, idea pitches, or member names.
   - **Member Count:** Filter by 1, 2, 3, 4, 5, 6, 3+, or 4+ members.
   - **Slot Status:** Show only teams with available slots (`Open Slots Only`).
   - **Origin Filter:** Filter by International (1+), Mostly International, All Asian, or All Origins.
4. Click **📥 Download CSV** to export the ranked list to Excel/Google Sheets.

### 2. Global Search (Discord ID & Member Lookup)
1. Click the **🌍 Global Search** tab at the top.
2. Enter a **Discord ID** (e.g., `1388751820003999816`) or **Member Name**.
3. Hit Enter to see:
   - Which **Hackathon** they are in.
   - Their **Team Name** and pitch idea.
   - Their **Whole Team Roster** with the searched user highlighted (`⭐ MATCHED USER`).

---

## 🛠️ Tech Stack
- **Backend:** Python (standard library HTTP server, requests, BeautifulSoup)
- **Frontend:** Vanilla JavaScript, HTML5, Modern CSS (Dark mode & Glassmorphism)
- **Data Persistence:** Local JSON & CSV snapshots in `saved_data/`
