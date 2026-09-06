#!/usr/bin/env python3
"""
Lablab.ai Team Finder & Member Origin Classifier (Asian vs International)
========================================================================

Features:
1. Automatically fetches all currently active hackathons on Lablab.ai.
2. Prompts user in terminal for:
   - Which event number to analyze
   - Minimum team member count (e.g., 3 members)
   - Whether to require open slots
   - Group filtering preference (All, At least 1 International, Mostly International)
3. Analyzes all eligible teams:
   - Inspects both profile location AND member names
   - Classifies each member into:
       * 🌏 Asian (India, Pakistan, Bangladesh, Nepal, Sri Lanka)
       * 🌎 International (USA, Canada, UK, Germany, France, Europe, Australia, etc.)
       * ❓ Unclassified / Other
   - Shows total Asian vs International breakdown for every team!
4. Exports comprehensive results to CSV and updates the visual HTML dashboard.
"""

import sys
import os
import re
import json
import csv
import time
import argparse
import webbrowser
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timezone

# Ensure UTF-8 output on Windows terminal
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Error: Missing required packages. Please run: pip install requests beautifulsoup4")
    sys.exit(1)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}

# ---------------------------------------------------------------------------
# Country Reference Sets
# ---------------------------------------------------------------------------
SOUTH_ASIAN_COUNTRIES = {
    "pakistan", "india", "bangladesh", "sri lanka", "nepal", "bhutan", "maldives", "afghanistan"
}

INTERNATIONAL_COUNTRIES = {
    "united states", "usa", "us", "canada", "united kingdom", "uk", "great britain",
    "england", "scotland", "wales", "germany", "france", "netherlands", "australia",
    "sweden", "norway", "denmark", "finland", "italy", "spain", "switzerland",
    "poland", "austria", "belgium", "ireland", "new zealand", "portugal", "greece",
    "czech", "romania", "hungary", "bulgaria", "brazil", "argentina", "mexico",
    "chile", "colombia", "peru", "south africa", "japan", "south korea", "singapore",
    "taiwan", "estonia", "latvia", "lithuania", "ukraine", "croatia", "serbia"
}

COUNTRY_FLAGS = {
    "united states": "🇺🇸", "usa": "🇺🇸", "us": "🇺🇸",
    "united kingdom": "🇬🇧", "uk": "🇬🇧", "great britain": "🇬🇧",
    "canada": "🇨🇦", "germany": "🇩🇪", "france": "🇫🇷",
    "netherlands": "🇳🇱", "australia": "🇦🇺", "sweden": "🇸🇪",
    "norway": "🇳🇴", "denmark": "🇩🇰", "finland": "🇫🇮",
    "italy": "🇮🇹", "spain": "🇪🇸", "switzerland": "🇨🇭",
    "poland": "🇵🇱", "austria": "🇦🇹", "belgium": "🇧🇪",
    "ireland": "🇮🇪", "japan": "🇯🇵", "singapore": "🇸🇬",
    "pakistan": "🇵🇰", "india": "🇮🇳", "bangladesh": "🇧🇩",
    "sri lanka": "🇱🇰", "nepal": "🇳🇵", "nigeria": "🇳🇬",
    "brazil": "🇧🇷", "mexico": "🇲🇽", "saudi arabia": "🇸🇦",
    "uae": "🇦🇪", "turkey": "🇹🇷", "egypt": "🇪🇬",
    "vietnam": "🇻🇳", "indonesia": "🇮🇩", "philippines": "🇵🇭"
}

# ---------------------------------------------------------------------------
# Name-based heuristic vocabulary (South Asian vs Western/International)
# ---------------------------------------------------------------------------
SOUTH_ASIAN_NAME_TOKENS = {
    # Pakistani / Bangladeshi / Muslim subcontinent names
    "muhammad", "mohammad", "mohammed", "md", "ahmed", "ahmad", "ali", "khan",
    "hussain", "hussein", "hassan", "hasan", "malik", "sheikh", "syed", "sayed",
    "choudhury", "chowdhury", "rehman", "rahman", "zubair", "asad", "razi",
    "fayaz", "farooq", "iqbal", "tariq", "akhtar", "ansari", "siddiqui", "qureshi",
    "usman", "bilal", "hamza", "nisha", "islam", "abdul", "ahad", "basim",
    "palijo", "fatima", "ayesha", "zainab", "marium", "mariam", "tariq", "shahzad",
    "nadeem", "waqar", "kamran", "imran", "irfan", "salman", "rizwan", "shoaib",
    "javed", "rashid", "asif", "saqib", "mudassir", "mudassar", "sohail", "naveed",
    "khurram", "zafar", "arshad", "shahid", "mahmood", "mehmood", "bhatti", "cheema",
    "bajwa", "warraich", "butt", "dar", "lone", "mir", "wani", "bhat", "pirzada",
    # Indian / Hindu / Sikh names
    "sharma", "patel", "kumar", "singh", "gupta", "verma", "shah", "reddy",
    "rao", "nair", "iyer", "joshi", "mehta", "bhatt", "shukla", "mishra",
    "pandey", "tiwari", "yadav", "chatterjee", "mukherjee", "banerjee", "das",
    "ghosh", "sen", "roy", "dey", "saxena", "agarwal", "agrawal", "jain",
    "chauhan", "chouhan", "rajput", "kaur", "preet", "deep", "pal", "anand",
    "kapoor", "chopra", "sahu", "swain", "jena", "rout", "behera", "vishrut",
    "potdar", "sarthak", "junankar", "shlok", "kishor", "salve", "ritvik",
    "arsha", "shaik", "sumanth", "lokeshwari", "hukumathirao", "purvesh", "thakre",
    "suhas", "aditya", "raghuwanshi", "sanjay", "rahul", "amit", "rohit",
    "ajay", "vijay", "vikram", "vivek", "alok", "deepak", "manish", "ashok",
    "rajesh", "suresh", "ramesh", "mahesh", "dinesh", "pradeep", "praveen", "naveen",
    "sandeep", "sunil", "anil", "pankaj", "rakesh", "nitin", "harish", "satish",
    "anurag", "abhishek", "varun", "gaurav", "kunal", "mayank", "piyush", "siddharth",
    "aniket", "sourabh", "saurabh", "prashant", "chetan", "nikhil", "tarun",
    # Sri Lankan names
    "perera", "fernando", "silva", "wickramasinghe", "rajapaksa", "jayawardene",
    "bandara", "dissanayake", "senanayake", "gunasekara", "ratnayake", "herath",
    "karunaratne", "peiris", "wijesinghe", "de silva", "ranasinghe", "kumara",
    # Additional common names
    "noor", "areeba", "jha", "gowtham", "gautam", "kanthwal", "hardik", "chaudhari",
    "chaudhary", "aryan", "thakur", "tyagi", "ismail", "sami", "ullah", "obaida",
    "gul", "yameen", "saim", "ifrah", "jadhav", "saini", "mishra", "keshav",
    "om", "atharv", "chorghe", "sambhav", "shreya", "ananya", "pooja", "priya",
    "sneha", "divya", "kavita", "deepa", "sunita", "rekha", "mona", "tanvi"
}

WESTERN_NAME_TOKENS = {
    # Common English / European / American given names and surnames
    "alex", "alexander", "john", "michael", "david", "chris", "christopher",
    "james", "thomas", "robert", "william", "richard", "daniel", "matthew",
    "mark", "paul", "steven", "andrew", "joshua", "kevin", "brian", "eric",
    "luke", "lucas", "adam", "benjamin", "samuel", "nathan", "oliver", "peter",
    "jack", "henry", "george", "simon", "julian", "maximilian", "max", "felix",
    "florian", "sebastian", "pierre", "antoine", "nicolas", "matteo", "marco",
    "luca", "andrea", "francesco", "alessandro", "giovanni", "gabriel", "leo",
    "hugo", "lars", "sven", "erik", "magnus", "niklas", "mads", "christian",
    "stefan", "markus", "smith", "johnson", "williams", "brown", "jones",
    "miller", "davis", "wilson", "anderson", "taylor", "thomas", "moore",
    "martin", "jackson", "thompson", "white", "harris", "clark", "lewis",
    "robinson", "walker", "hall", "allen", "young", "king", "wright",
    "scott", "green", "baker", "adams", "nelson", "carter", "mitchell",
    "marabate", "mueller", "müller", "schmidt", "schneider", "fischer",
    "weber", "meyer", "wagner", "becker", "schulz", "hoffmann", "dupont",
    "bernard", "dubois", "moreau", "laurent", "garcia", "martinez", "rodriguez",
    "lopez", "gonzalez", "perez", "sanchez", "ramirez", "rossi", "russo",
    "ferrari", "esposito", "bianchi", "romano", "jansen", "de jong", "bakker",
    "visser", "smit", "meijer", "boer", "van de", "van den", "van der"
}


@dataclass
class Member:
    name: str
    username: str
    location: Optional[str] = None
    country: Optional[str] = None
    flag: str = "🌐"
    group: str = "Unclassified"   # 'Asian' | 'International' | 'Unclassified'
    origin_reason: str = ""       # e.g., 'Location: Pakistan' or 'Name: Patel'
    role: Optional[str] = None
    discord_id: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None


@dataclass
class Team:
    id: str
    name: str
    slug: str
    url: str
    description: str
    join_mode: str
    limit: int
    member_count: int
    open_slots: int
    members: List[Member] = field(default_factory=list)
    professions: List[str] = field(default_factory=list)
    countries: List[str] = field(default_factory=list)
    flags: List[str] = field(default_factory=list)
    asian_count: int = 0
    international_count: int = 0
    unclassified_count: int = 0
    score: float = 0.0
    match_tag: str = ""
    score_breakdown: str = ""


# ---------------------------------------------------------------------------
# Classification Engine (Location + Name)
# ---------------------------------------------------------------------------
def classify_member(name: str, username: str, location: Optional[str]) -> Tuple[str, str, str, Optional[str]]:
    """
    Classifies a member as 'Asian' or 'International' or 'Unclassified'.
    Returns: (group, origin_reason, flag_emoji, country_name)
    """
    loc_clean = (location or "").strip().lower()

    # 1. Primary Check: Profile location specified
    if loc_clean:
        # Check Asian countries
        for ac in SOUTH_ASIAN_COUNTRIES:
            if ac in loc_clean:
                flag = COUNTRY_FLAGS.get(ac, "🌏")
                return "Asian", f"Country: {location.strip()}", flag, location.strip()

        # Check International countries
        for ic in INTERNATIONAL_COUNTRIES:
            if ic in loc_clean:
                flag = COUNTRY_FLAGS.get(ic, "🌎")
                return "International", f"Country: {location.strip()}", flag, location.strip()

        # Other location
        return "International", f"Location: {location.strip()}", "🌐", location.strip()

    # 2. Secondary Check: Name token analysis
    full_text = f"{name} {username}".lower()
    # clean out numbers and punctuation
    cleaned = re.sub(r'[^a-zA-Z\s]', ' ', full_text)
    tokens = set(cleaned.split())

    # Check matches with South Asian vocabulary
    sa_hits = [t for t in tokens if t in SOUTH_ASIAN_NAME_TOKENS]
    # Check matches with Western / International vocabulary
    w_hits = [t for t in tokens if t in WESTERN_NAME_TOKENS]

    if sa_hits and not w_hits:
        return "Asian", f"Name analysis ({', '.join(sa_hits[:2])})", "🌏", None
    elif w_hits and not sa_hits:
        return "International", f"Name analysis ({', '.join(w_hits[:2])})", "🌎", None
    elif len(sa_hits) > len(w_hits):
        return "Asian", f"Name match ({sa_hits[0]})", "🌏", None
    elif len(w_hits) > len(sa_hits):
        return "International", f"Name match ({w_hits[0]})", "🌎", None

    return "Unclassified", "Location/Name unknown", "❓", None


# ---------------------------------------------------------------------------
# Extraction Helpers
# ---------------------------------------------------------------------------
def extract_rsc_text(html: str) -> str:
    chunks = re.findall(r'self\.__next_f\.push\(\[\d+,\s*"(.*?)"\]\)', html, re.DOTALL)
    combined = ""
    for c in chunks:
        try:
            combined += json.loads(f'"{c}"')
        except Exception:
            combined += c
    return combined if combined else html


def get_active_events(session: requests.Session) -> List[Dict]:
    url = "https://lablab.ai/event"
    try:
        resp = session.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        print(f"Error fetching active events from {url}: {e}")
        return []

    combined_text = extract_rsc_text(resp.text)
    events_raw = []
    seen_ids = set()

    for match in re.finditer(r'\{"id":"([a-zA-Z0-9]+)","name":"([^"]+)"', combined_text):
        start = match.start()
        brace = 0
        end = start
        for i in range(start, min(len(combined_text), start + 4000)):
            if combined_text[i] == '{':
                brace += 1
            elif combined_text[i] == '}':
                brace -= 1
                if brace == 0:
                    end = i + 1
                    break
        if end > start:
            try:
                obj = json.loads(combined_text[start:end])
                eid = obj.get("id")
                if eid and eid not in seen_ids and "slug" in obj and "name" in obj:
                    seen_ids.add(eid)
                    events_raw.append(obj)
            except Exception:
                pass

    now = datetime.now(timezone.utc)
    active_events = []
    for e in events_raw:
        end_at_str = e.get("endAt")
        is_finished = False
        if end_at_str:
            try:
                end_dt = datetime.fromisoformat(end_at_str.replace("Z", "+00:00"))
                if end_dt < now:
                    is_finished = True
            except Exception:
                pass

        if is_finished:
            continue

        if e.get("signupActive") or e.get("active"):
            s_at = e.get("startAt") or "N/A"
            e_at = e.get("endAt") or "N/A"
            active_events.append({
                "id": e.get("id"),
                "name": e.get("name"),
                "slug": e.get("slug"),
                "startAt": s_at,
                "endAt": e_at,
                "signupActive": e.get("signupActive", False),
                "teamsActive": e.get("teamsActive", False),
                "teamLimit": e.get("teamMembersLimit", 6) or 6,
                "teamMin": e.get("teamMembersMinimum", 1) or 1,
                "url": f"https://lablab.ai/ai-hackathons/{e.get('slug')}"
            })

    # Sort so latest / upcoming events are first
    active_events.sort(key=lambda ev: ev.get("startAt") or "", reverse=True)
    return active_events


def fetch_event_teams(event_id: str, session: requests.Session) -> List[Dict]:
    api_url = f"https://lablab.ai/api/v4/teams?eventId={event_id}"
    try:
        resp = session.get(api_url, headers=HEADERS, timeout=25)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("teams", [])
    except Exception as e:
        print(f"Error calling teams API: {e}")
    return []


def enrich_team_details(event_slug: str, team_slug: str, session: requests.Session) -> Optional[Dict]:
    url = f"https://lablab.ai/ai-hackathons/{event_slug}/{team_slug}"
    try:
        resp = session.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return None

        combined = extract_rsc_text(resp.text)
        m = re.search(r'"team":\s*\{', combined)
        if not m:
            return None

        start = m.end() - 1
        brace = 0
        end = start
        for i in range(start, len(combined)):
            if combined[i] == '{':
                brace += 1
            elif combined[i] == '}':
                brace -= 1
                if brace == 0:
                    end = i + 1
                    break
        team_data = json.loads(combined[start:end])
        return team_data
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Team Analyzer & Scorer
# ---------------------------------------------------------------------------
def analyze_and_score_team(
    team_data: Dict,
    event_slug: str,
    min_members: int = 3,
    open_only: bool = False
) -> Optional[Team]:
    participants_raw = team_data.get("participants", [])
    member_count = len(participants_raw)

    # Filter: Minimum member count requirement
    if member_count < min_members:
        return None

    limit = team_data.get("limit", 6) or 6
    open_slots = max(0, limit - member_count)
    join_mode = team_data.get("joinMode", "OPEN")

    if open_only and open_slots < 1:
        return None

    members = []
    countries = []
    flags = []
    asian_count = 0
    intl_count = 0
    unclass_count = 0

    for p in participants_raw:
        u = p.get("user", {}) or {}
        prof = u.get("profile", {}) or {}
        name = f"{prof.get('firstName') or ''} {prof.get('lastName') or ''}".strip() or u.get("name") or "Anonymous"
        username = prof.get("userName") or u.get("id") or "user"
        loc = prof.get("location")
        role = prof.get("role")
        discord_id = prof.get("discordId")
        linkedin = prof.get("linkedinUrl")
        github = prof.get("githubUrl")

        group, reason, flag, country_name = classify_member(name, username, loc)

        if group == "Asian":
            asian_count += 1
        elif group == "International":
            intl_count += 1
        else:
            unclass_count += 1

        flags.append(flag)
        if country_name:
            countries.append(country_name)

        members.append(Member(
            name=name,
            username=username,
            location=loc,
            country=country_name,
            flag=flag,
            group=group,
            origin_reason=reason,
            role=role,
            discord_id=discord_id,
            linkedin_url=linkedin,
            github_url=github
        ))

    # Scoring formulation
    score = 0.0
    breakdown = []

    # 1. Open Slots (30 pts)
    if join_mode == "OPEN" and open_slots >= 1:
        slot_score = min(open_slots * 15.0, 30.0)
        score += slot_score
        breakdown.append(f"Open slots ({open_slots}): +{slot_score:.0f}")
    elif open_slots > 0:
        score += 10.0
        breakdown.append(f"Slots open ({open_slots}) but {join_mode}: +10")
    else:
        breakdown.append("Team full (0 slots)")

    # 2. International presence (40 pts)
    if intl_count > 0:
        intl_score = min(intl_count * 20.0, 40.0)
        score += intl_score
        breakdown.append(f"International members ({intl_count}): +{intl_score:.0f}")
    elif asian_count > 0 and intl_count == 0:
        score += 5.0
        breakdown.append("All Asian team: +5")

    # 3. Base team size (15 pts) - already 3+ members ready
    size_score = min(member_count * 3.5, 15.0)
    score += size_score
    breakdown.append(f"Core team ({member_count} members): +{size_score:.0f}")

    # 4. Idea description (15 pts)
    desc = team_data.get("description", "").strip()
    if len(desc) > 30:
        score += 15.0
        breakdown.append("Active idea: +15")

    score = max(0.0, round(score, 1))

    # Match Tagging
    if intl_count >= 1 and open_slots >= 1:
        match_tag = "🔥 International Match"
    elif open_slots >= 1:
        match_tag = "✅ Open Team (Ready)"
    else:
        match_tag = "🔒 Team Full"

    professions = []
    for prof_obj in team_data.get("professions", []):
        p_name = prof_obj.get("profession", {}).get("name")
        if p_name:
            professions.append(p_name)

    slug = team_data.get("slug") or ""
    return Team(
        id=team_data.get("id", ""),
        name=team_data.get("name", "Unnamed Team"),
        slug=slug,
        url=f"https://lablab.ai/ai-hackathons/{event_slug}/{slug}",
        description=desc,
        join_mode=join_mode,
        limit=limit,
        member_count=member_count,
        open_slots=open_slots,
        members=members,
        professions=professions,
        countries=countries,
        flags=flags,
        asian_count=asian_count,
        international_count=intl_count,
        unclassified_count=unclass_count,
        score=score,
        match_tag=match_tag,
        score_breakdown="; ".join(breakdown)
    )


# ---------------------------------------------------------------------------
# HTML Dashboard Generator
# ---------------------------------------------------------------------------
def generate_html_report(event_name: str, teams: List[Team]) -> str:
    cards_html = ""
    for t in teams:
        members_html = "".join([
            f"""<li class="member-item">
                <div class="member-top">
                    <span class="member-flag">{m.flag}</span>
                    <span class="member-name"><strong>{m.name}</strong> (@{m.username})</span>
                    <span class="group-pill group-{m.group.lower()}">{m.group}</span>
                </div>
                <div class="member-details">
                    <span class="detail-tag">📌 {m.origin_reason}</span>
                    {f'<span class="detail-tag">💼 {m.role}</span>' if m.role else ''}
                    {f'<span class="detail-tag discord">🎮 Discord: {m.discord_id}</span>' if m.discord_id else ''}
                </div>
            </li>""" for m in t.members
        ])

        ratio_str = f"🌏 {t.asian_count} Asian &nbsp;|&nbsp; 🌎 {t.international_count} International"
        if t.unclassified_count > 0:
            ratio_str += f" &nbsp;|&nbsp; ❓ {t.unclassified_count} Unclassified"

        cards_html += f"""
        <div class="team-card">
            <div class="team-header">
                <div>
                    <h3 class="team-title">{t.name}</h3>
                    <div class="group-summary">{ratio_str}</div>
                </div>
                <div class="score-box">
                    <div class="score-val">{t.score}</div>
                    <div class="match-badge">{t.match_tag}</div>
                </div>
            </div>
            <div class="team-stats">
                <span class="stat-pill">👥 {t.member_count}/{t.limit} Members</span>
                <span class="stat-pill {'slot-open' if t.open_slots > 0 else 'slot-full'}">
                    {'✅ ' + str(t.open_slots) + ' Slot(s) Available' if t.open_slots > 0 else '❌ Team Full'}
                </span>
                <span class="stat-pill">🔒 Mode: {t.join_mode}</span>
            </div>
            {f'<p class="team-desc">💡 {t.description}</p>' if t.description else '<p class="team-desc empty">No idea description provided yet.</p>'}
            <div class="members-section">
                <h4>Team Members ({len(t.members)}):</h4>
                <ul class="members-list">{members_html}</ul>
            </div>
            <div class="team-footer">
                <span class="breakdown">📊 {t.score_breakdown}</span>
                <a href="{t.url}" target="_blank" class="btn-visit">View on Lablab ↗</a>
            </div>
        </div>
        """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lablab Team Finder - {event_name}</title>
    <style>
        :root {{
            --bg: #0d1117; --card: #161b22; --border: #30363d;
            --text: #c9d1d9; --muted: #8b949e; --accent: #58a6ff;
            --asian: #f0883e; --intl: #3fb950; --unclass: #8b949e;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
        body {{ background: var(--bg); color: var(--text); padding: 30px 20px; }}
        .container {{ max-width: 1100px; margin: 0 auto; }}
        .header {{ text-align: center; margin-bottom: 30px; border-bottom: 1px solid var(--border); padding-bottom: 20px; }}
        .header h1 {{ font-size: 2.2rem; color: #fff; margin-bottom: 8px; }}
        .header p {{ color: var(--muted); font-size: 1.1rem; }}
        .summary-bar {{ display: flex; justify-content: space-around; background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 16px; margin-bottom: 30px; flex-wrap: wrap; gap: 15px; }}
        .summary-item {{ text-align: center; }}
        .summary-num {{ font-size: 1.8rem; font-weight: bold; color: var(--accent); }}
        .summary-label {{ font-size: 0.85rem; color: var(--muted); }}
        .team-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 14px; padding: 22px; margin-bottom: 24px; transition: transform 0.2s, border-color 0.2s; }}
        .team-card:hover {{ transform: translateY(-3px); border-color: var(--accent); }}
        .team-header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }}
        .team-title {{ font-size: 1.35rem; color: #fff; }}
        .group-summary {{ font-size: 0.95rem; color: #e6edf3; margin-top: 5px; font-weight: 500; }}
        .score-box {{ text-align: right; }}
        .score-val {{ font-size: 1.8rem; font-weight: bold; color: #38bdf8; }}
        .match-badge {{ display: inline-block; padding: 4px 10px; border-radius: 20px; font-size: 0.8rem; font-weight: 600; background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid #38bdf8; margin-top: 4px; }}
        .team-stats {{ display: flex; gap: 10px; margin-bottom: 14px; flex-wrap: wrap; }}
        .stat-pill {{ background: #21262d; border: 1px solid var(--border); padding: 5px 12px; border-radius: 8px; font-size: 0.85rem; }}
        .slot-open {{ color: #3fb950; border-color: #238636; font-weight: 600; }}
        .slot-full {{ color: var(--muted); }}
        .team-desc {{ background: #0d1117; padding: 12px 16px; border-radius: 8px; font-size: 0.95rem; line-height: 1.5; color: #e6edf3; margin-bottom: 16px; border-left: 3px solid var(--accent); }}
        .team-desc.empty {{ color: var(--muted); border-left-color: var(--border); font-style: italic; }}
        .members-section h4 {{ font-size: 0.85rem; color: var(--muted); margin-bottom: 10px; text-transform: uppercase; letter-spacing: 0.5px; }}
        .members-list {{ list-style: none; display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 10px; }}
        .member-item {{ background: #21262d; padding: 12px 14px; border-radius: 8px; border: 1px solid var(--border); display: flex; flex-direction: column; gap: 6px; }}
        .member-top {{ display: flex; align-items: center; gap: 8px; }}
        .member-name {{ font-size: 0.95rem; color: #fff; flex: 1; }}
        .group-pill {{ padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }}
        .group-asian {{ background: rgba(240, 136, 62, 0.2); color: var(--asian); border: 1px solid var(--asian); }}
        .group-international {{ background: rgba(63, 185, 80, 0.2); color: var(--intl); border: 1px solid var(--intl); }}
        .group-unclassified {{ background: rgba(139, 148, 158, 0.2); color: var(--unclass); border: 1px solid var(--unclass); }}
        .member-details {{ display: flex; flex-wrap: wrap; gap: 6px; font-size: 0.8rem; color: var(--muted); }}
        .detail-tag {{ background: #161b22; padding: 2px 8px; border-radius: 6px; }}
        .detail-tag.discord {{ color: #a371f7; }}
        .team-footer {{ display: flex; justify-content: space-between; align-items: center; margin-top: 16px; padding-top: 14px; border-top: 1px solid var(--border); }}
        .breakdown {{ font-size: 0.8rem; color: var(--muted); }}
        .btn-visit {{ background: var(--accent); color: #0d1117; padding: 8px 16px; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 0.9rem; }}
        .btn-visit:hover {{ opacity: 0.9; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏆 Lablab Team Origin & Fit Analyzer</h1>
            <p>Hackathon: <strong>{event_name}</strong> | Grouped by Asian & International Members</p>
        </div>
        <div class="summary-bar">
            <div class="summary-item">
                <div class="summary-num">{len(teams)}</div>
                <div class="summary-label">Qualified Teams</div>
            </div>
            <div class="summary-item">
                <div class="summary-num">{len([t for t in teams if t.open_slots > 0])}</div>
                <div class="summary-label">Teams With Open Slots</div>
            </div>
            <div class="summary-item">
                <div class="summary-num">{len([t for t in teams if t.international_count > 0])}</div>
                <div class="summary-label">Teams with International Members</div>
            </div>
            <div class="summary-item">
                <div class="summary-num">{sum(t.asian_count for t in teams)}</div>
                <div class="summary-label">Total Asian Members</div>
            </div>
            <div class="summary-item">
                <div class="summary-num">{sum(t.international_count for t in teams)}</div>
                <div class="summary-label">Total International Members</div>
            </div>
        </div>
        <div class="teams-container">
            {cards_html}
        </div>
    </div>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Interactive Terminal Flow
# ---------------------------------------------------------------------------
def run_interactive_terminal():
    session = requests.Session()

    print("==================================================================")
    print("   🌐 LABLAB.AI TEAM FINDER & MEMBER ORIGIN CLASSIFIER")
    print("==================================================================\n")

    # STEP 1: Fetch active events
    print("[*] Fetching all currently active hackathons on Lablab.ai...")
    events = get_active_events(session)
    if not events:
        print("[!] No active events found. Please check internet connection.")
        return

    print(f"\n[+] Found {len(events)} active hackathons with registration open:\n")
    display_limit = min(15, len(events))
    for i in range(display_limit):
        ev = events[i]
        s_at = ev.get('startAt') or 'N/A'
        e_at = ev.get('endAt') or 'N/A'
        if s_at != 'N/A' and e_at != 'N/A':
            dates = f"{s_at[:10]} to {e_at[:10]}"
        elif s_at != 'N/A':
            dates = f"Starts {s_at[:10]}"
        else:
            dates = "Active / TBA"
        print(f"  [{i+1:>2}] {ev['name']}")
        print(f"       Slug: {ev['slug']} | Dates: {dates} | Max Team Limit: {ev['teamLimit']}")

    print("\n" + "-" * 66)

    # STEP 2: Ask user which event number
    while True:
        try:
            choice = input(f"👉 Select event number (1-{display_limit}) [default: 1]: ").strip()
            if not choice:
                selected_event = events[0]
                break
            if choice.isdigit() and 1 <= int(choice) <= len(events):
                selected_event = events[int(choice) - 1]
                break
            # check slug match
            matched = [e for e in events if e["slug"] == choice or choice.lower() in e["name"].lower()]
            if matched:
                selected_event = matched[0]
                break
            print(f"[!] Invalid selection. Please enter a number between 1 and {display_limit}.")
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            return

    # STEP 3: Ask for minimum team member count (default: 3)
    max_limit = selected_event.get("teamLimit") or 6
    while True:
        try:
            min_m_input = input(f"👉 Minimum team members count (e.g., 3, max {max_limit}) [default: 3]: ").strip()
            if not min_m_input:
                min_members = 3
                break
            if min_m_input.isdigit() and 1 <= int(min_m_input) <= max_limit:
                min_members = int(min_m_input)
                break
            print(f"[!] Please enter a valid number between 1 and {max_limit}.")
        except (KeyboardInterrupt, EOFError):
            return

    # STEP 4: Ask if open slots are required
    try:
        open_slot_input = input("👉 Must have OPEN slot(s) available to join? (y/n) [default: y]: ").strip().lower()
        open_only = (open_slot_input != "n")
    except (KeyboardInterrupt, EOFError):
        open_only = True

    # STEP 5: Ask for group preference filter
    print("\n👉 Filter preference:")
    print("   [1] Show all teams with Asian & International breakdown")
    print("   [2] Only teams with at least 1 International member")
    print("   [3] Mostly International teams (more International than Asian members)")
    group_pref_input = input("   Select option (1-3) [default: 1]: ").strip()
    group_filter = 1
    if group_pref_input in ["2", "3"]:
        group_filter = int(group_pref_input)

    # STEP 6: Ask for analysis depth
    limit_input = input("\n👉 How many teams to inspect in detail? [default: 35]: ").strip()
    inspect_limit = int(limit_input) if limit_input.isdigit() and int(limit_input) > 0 else 35

    print("\n" + "=" * 66)
    print(f"[*] Starting Analysis for: {selected_event['name']}")
    print(f"    Min Members Required:  {min_members}")
    print(f"    Open Slots Required:   {'YES' if open_only else 'NO'}")
    print(f"    Group Preference:      Option {group_filter}")
    print("=" * 66 + "\n")

    # Fetch all teams
    print("[*] Fetching all teams from Lablab.ai...")
    all_teams_raw = fetch_event_teams(selected_event['id'], session)
    print(f"[+] Total teams in hackathon: {len(all_teams_raw)}")

    # Pre-filter by member count
    eligible_raw = [t for t in all_teams_raw if len(t.get("participants", [])) >= min_members]
    if open_only:
        eligible_raw = [t for t in eligible_raw if t.get("joinMode") == "OPEN"]

    print(f"[+] Teams meeting basic member/slot criteria: {len(eligible_raw)}")
    if not eligible_raw:
        print("[!] No teams found matching your criteria. Try lowering the minimum member count.")
        return

    # In-depth analysis of profiles and names
    actual_count = min(len(eligible_raw), inspect_limit)
    print(f"[*] Inspecting {actual_count} teams (country profiles & name analysis)...")

    scored_teams: List[Team] = []
    for i, t_raw in enumerate(eligible_raw[:actual_count], 1):
        slug = t_raw.get("slug")
        print(f"    [{i}/{actual_count}] Analyzing: {t_raw.get('name')} ...", end="\r", flush=True)

        enriched = enrich_team_details(selected_event['slug'], slug, session)
        team_data = enriched if enriched else t_raw

        team_obj = analyze_and_score_team(
            team_data,
            event_slug=selected_event['slug'],
            min_members=min_members,
            open_only=open_only
        )

        if team_obj:
            # Apply group filter preference
            if group_filter == 2 and team_obj.international_count < 1:
                continue
            if group_filter == 3 and team_obj.international_count <= team_obj.asian_count:
                continue

            scored_teams.append(team_obj)

        time.sleep(0.25)

    print("\n[+] Analysis complete!\n")

    # Sort by score descending
    scored_teams.sort(key=lambda t: (t.international_count, t.score), reverse=True)

    # STEP 7: Print Formatted Terminal Results
    print("=" * 70)
    print(f"   🏆 TEAM RESULTS FOR: {selected_event['name'].upper()}")
    print(f"   (Minimum {min_members} members | Open slots: {'YES' if open_only else 'ANY'})")
    print("=" * 70 + "\n")

    if not scored_teams:
        print("[!] No teams matched after applying the group origin filter.")
    else:
        for idx, t in enumerate(scored_teams, 1):
            slot_info = f"✅ {t.open_slots} Open Slot(s)" if t.open_slots > 0 else "❌ Full"
            print(f"[{idx:>2}] TEAM: {t.name}  |  Score: {t.score:>4.1f}  |  {t.match_tag}")
            print(f"     Slots: {t.member_count}/{t.limit} Members ({slot_info})  |  Join Mode: {t.join_mode}")
            print(f"     Origin Breakdown: 🌏 {t.asian_count} Asian  |  🌎 {t.international_count} International  |  ❓ {t.unclassified_count} Unclassified")

            # Member Details Breakdown
            asian_members = [f"{m.name} ({m.origin_reason})" for m in t.members if m.group == "Asian"]
            intl_members = [f"{m.name} ({m.origin_reason})" for m in t.members if m.group == "International"]
            unclass_members = [f"{m.name}" for m in t.members if m.group == "Unclassified"]

            if intl_members:
                print(f"     🌎 International: {'; '.join(intl_members)}")
            if asian_members:
                print(f"     🌏 Asian:         {'; '.join(asian_members)}")
            if unclass_members:
                print(f"     ❓ Unclassified:  {', '.join(unclass_members)}")

            if t.description:
                desc_snip = t.description[:130] + "..." if len(t.description) > 130 else t.description
                print(f"     💡 Idea:          {desc_snip}")

            print(f"     🔗 Link:          {t.url}")
            print("     " + "-" * 62)

    # STEP 8: Export to CSV
    csv_file = "lablab_teams_ranked.csv"
    try:
        f_csv = open(csv_file, "w", newline="", encoding="utf-8")
    except PermissionError:
        csv_file = f"lablab_teams_ranked_{int(time.time())}.csv"
        f_csv = open(csv_file, "w", newline="", encoding="utf-8")
        print(f"\n[!] Note: 'lablab_teams_ranked.csv' is open in Excel/another program. Saving to '{csv_file}' instead.")

    with f_csv:
        writer = csv.writer(f_csv)
        writer.writerow([
            "Team Name", "Score", "Match Tag", "Open Slots", "Members Count",
            "Max Limit", "Join Mode", "Asian Count", "International Count",
            "Unclassified Count", "International Members", "Asian Members",
            "All Member Details", "Project Idea", "URL"
        ])
        for t in scored_teams:
            asian_str = "; ".join([f"{m.name} ({m.origin_reason})" for m in t.members if m.group == "Asian"])
            intl_str = "; ".join([f"{m.name} ({m.origin_reason})" for m in t.members if m.group == "International"])
            all_str = "; ".join([f"{m.name} [{m.group} - {m.origin_reason}]" for m in t.members])
            writer.writerow([
                t.name, t.score, t.match_tag, t.open_slots, t.member_count,
                t.limit, t.join_mode, t.asian_count, t.international_count,
                t.unclassified_count, intl_str, asian_str, all_str,
                t.description, t.url
            ])

    print(f"\n[+] CSV Report saved to: {os.path.abspath(csv_file)}")

    # STEP 9: Generate HTML Dashboard
    html_file = "lablab_teams_dashboard.html"
    try:
        f_html = open(html_file, "w", encoding="utf-8")
    except PermissionError:
        html_file = f"lablab_teams_dashboard_{int(time.time())}.html"
        f_html = open(html_file, "w", encoding="utf-8")

    html_content = generate_html_report(selected_event['name'], scored_teams)
    with f_html:
        f_html.write(html_content)
    print(f"[+] HTML Visual Dashboard saved to: {os.path.abspath(html_file)}")


if __name__ == "__main__":
    run_interactive_terminal()
