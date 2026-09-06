#!/usr/bin/env python3
"""
Lablab.ai Team Finder Web App
==============================
A local web application with an interactive UI to:
- Browse currently active hackathons (filtered for unexpired events)
- Save and version team data automatically per hackathon
- Choose between:
    1. ⚡ Instant Search in previously saved data files (offline/instant)
    2. 🔄 Fetch Fresh Live Data from Lablab.ai (creates a new versioned file)
- Live client-side filters:
    * Search keyword in team name, idea, or member names
    * Member count dropdown filter (1, 2, 3, 4, 5, 6, 3+, 4+)
    * Slot status filter (Open slots only vs All)
    * Origin filter (All, At least 1 International, Mostly International)
- Export directly to CSV with 1 click
"""

import sys
import os
import re
import json
import csv
import time
import urllib.parse
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from typing import List, Dict, Optional, Tuple
import webbrowser
import threading

# Ensure UTF-8 output on Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVED_DATA_DIR = os.path.join(BASE_DIR, "saved_data")
os.makedirs(SAVED_DATA_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}

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

SOUTH_ASIAN_NAME_TOKENS = {
    "muhammad", "mohammad", "mohammed", "md", "ahmed", "ahmad", "ali", "khan",
    "hussain", "hussein", "hassan", "hasan", "malik", "sheikh", "syed", "sayed",
    "choudhury", "chowdhury", "rehman", "rahman", "zubair", "asad", "razi",
    "fayaz", "farooq", "iqbal", "tariq", "akhtar", "ansari", "siddiqui", "qureshi",
    "usman", "bilal", "hamza", "nisha", "islam", "abdul", "ahad", "basim",
    "palijo", "fatima", "ayesha", "zainab", "marium", "mariam", "shahzad",
    "nadeem", "waqar", "kamran", "imran", "irfan", "salman", "rizwan", "shoaib",
    "javed", "rashid", "asif", "saqib", "mudassir", "mudassar", "sohail", "naveed",
    "khurram", "zafar", "arshad", "shahid", "mahmood", "mehmood", "bhatti", "cheema",
    "bajwa", "warraich", "butt", "dar", "lone", "mir", "wani", "bhat", "pirzada",
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
    "perera", "fernando", "silva", "wickramasinghe", "rajapaksa", "jayawardene",
    "bandara", "dissanayake", "senanayake", "gunasekara", "ratnayake", "herath",
    "karunaratne", "peiris", "wijesinghe", "de silva", "ranasinghe", "kumara",
    "thapa", "shrestha", "gurung", "tamang", "magar", "rai", "limbu", "adhikari",
    "bhandari", "karki", "bhattarai", "pokhrel", "subedi", "pandit", "basnet",
    "noor", "areeba", "jha", "gowtham", "gautam", "kanthwal", "hardik", "chaudhari",
    "chaudhary", "aryan", "thakur", "tyagi", "ismail", "sami", "ullah", "obaida",
    "gul", "yameen", "saim", "ifrah", "jadhav", "saini", "mishra", "keshav",
    "om", "atharv", "chorghe", "sambhav", "shreya", "ananya", "pooja", "priya",
    "sneha", "divya", "kavita", "deepa", "sunita", "rekha", "mona", "tanvi"
}

WESTERN_NAME_TOKENS = {
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
    "ferrari", "esposito", "bianchi", "romano", "jansen", "de jong", "bakker"
}

SESSION = requests.Session()
CACHED_RESULTS = []
CURRENT_EVENT_NAME = "Lablab Teams"


def extract_rsc_text(html: str) -> str:
    chunks = re.findall(r'self\.__next_f\.push\(\[\d+,\s*"(.*?)"\]\)', html, re.DOTALL)
    combined = ""
    for c in chunks:
        try:
            combined += json.loads(f'"{c}"')
        except Exception:
            combined += c
    return combined if combined else html


def get_truly_active_events() -> List[Dict]:
    """Fetches only active, ongoing, or upcoming events (endAt >= today)."""
    url = "https://lablab.ai/event"
    try:
        resp = SESSION.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        print(f"Error fetching events: {e}")
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
            reg_cnt = 0
            if isinstance(e.get("_count"), dict):
                reg_cnt = e.get("_count", {}).get("participants", 0)
            elif e.get("initialParticipants"):
                reg_cnt = e.get("initialParticipants", 0)

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
                "registeredParticipants": reg_cnt,
                "url": f"https://lablab.ai/ai-hackathons/{e.get('slug')}"
            })

    active_events.sort(key=lambda ev: ev.get("startAt") or "", reverse=True)
    return active_events


def classify_member(name: str, username: str, location: Optional[str]) -> Tuple[str, str, str, Optional[str]]:
    loc_clean = (location or "").strip().lower()

    if loc_clean:
        for ac in SOUTH_ASIAN_COUNTRIES:
            if ac in loc_clean:
                flag = COUNTRY_FLAGS.get(ac, "🌏")
                return "Asian", f"Country: {location.strip()}", flag, location.strip()

        for ic in INTERNATIONAL_COUNTRIES:
            if ic in loc_clean:
                flag = COUNTRY_FLAGS.get(ic, "🌎")
                return "International", f"Country: {location.strip()}", flag, location.strip()

        return "International", f"Location: {location.strip()}", "🌐", location.strip()

    full_text = f"{name} {username}".lower()
    cleaned = re.sub(r'[^a-zA-Z\s]', ' ', full_text)
    tokens = set(cleaned.split())

    sa_hits = [t for t in tokens if t in SOUTH_ASIAN_NAME_TOKENS]
    w_hits = [t for t in tokens if t in WESTERN_NAME_TOKENS]

    if sa_hits and not w_hits:
        return "Asian", f"Name match ({', '.join(sa_hits[:2])})", "🌏", None
    elif w_hits and not sa_hits:
        return "International", f"Name match ({', '.join(w_hits[:2])})", "🌎", None
    elif len(sa_hits) > len(w_hits):
        return "Asian", f"Name match ({sa_hits[0]})", "🌏", None
    elif len(w_hits) > len(sa_hits):
        return "International", f"Name match ({w_hits[0]})", "🌎", None

    return "Unclassified", "Unspecified", "❓", None


def enrich_team_details(event_slug: str, team_slug: str, session: Optional[requests.Session] = None) -> Optional[Dict]:
    req_session = session or SESSION
    url = f"https://lablab.ai/ai-hackathons/{event_slug}/{team_slug}"
    try:
        resp = req_session.get(url, headers=HEADERS, timeout=15)
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
        return json.loads(combined[start:end])
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Snapshot Persistence (Save & Load per Hackathon)
# ---------------------------------------------------------------------------
def save_snapshot(event_slug: str, event_name: str, teams: List[Dict], registered_participants: int = 0) -> str:
    """Saves a versioned snapshot of teams for a hackathon to both JSON and CSV."""
    timestamp_key = datetime.now().strftime("%Y%m%d_%H%M%S")
    display_time = datetime.now().strftime("%b %d, %Y %H:%M")
    base_name = f"{event_slug}_{timestamp_key}"

    # 1. Save JSON
    json_path = os.path.join(SAVED_DATA_DIR, f"{base_name}.json")
    meta = {
        "eventSlug": event_slug,
        "eventName": event_name,
        "timestamp": timestamp_key,
        "displayTime": display_time,
        "teamCount": len(teams),
        "registeredParticipants": registered_participants,
        "teams": teams
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    # 2. Save CSV
    csv_path = os.path.join(SAVED_DATA_DIR, f"{base_name}.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Team Name", "Score", "Match Tag", "Open Slots", "Members Count",
            "Max Limit", "Join Mode", "Asian Count", "International Count",
            "Unclassified Count", "International Members", "Asian Members",
            "All Member Details", "Project Idea", "URL"
        ])
        for t in teams:
            asian_str = "; ".join([f"{m['name']} ({m['reason']})" for m in t['members'] if m['group'] == "Asian"])
            intl_str = "; ".join([f"{m['name']} ({m['reason']})" for m in t['members'] if m['group'] == "International"])
            all_str = "; ".join([f"{m['name']} [{m['group']} - {m['reason']}]" for m in t['members']])
            writer.writerow([
                t["name"], t["score"], t["matchTag"], t["openSlots"], t["memberCount"],
                t["limit"], t["joinMode"], t["asianCount"], t["intlCount"],
                t["unclassCount"], intl_str, asian_str, all_str,
                t["description"], t["url"]
            ])

    print(f"[+] Saved snapshot to {json_path} and {csv_path}")
    return base_name


def get_saved_snapshots(event_slug: Optional[str] = None) -> List[Dict]:
    """Retrieves all saved snapshots, filtered by eventSlug if provided."""
    snapshots = []
    if not os.path.exists(SAVED_DATA_DIR):
        return []

    for fname in os.listdir(SAVED_DATA_DIR):
        if fname.endswith(".json"):
            fpath = os.path.join(SAVED_DATA_DIR, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                    slug = meta.get("eventSlug")
                    if not event_slug or slug == event_slug:
                        snapshots.append({
                            "filename": fname,
                            "eventSlug": slug,
                            "eventName": meta.get("eventName", slug),
                            "displayTime": meta.get("displayTime", "Unknown"),
                            "teamCount": meta.get("teamCount", len(meta.get("teams", []))),
                            "csvFile": fname.replace(".json", ".csv")
                        })
            except Exception:
                pass

    # Sort newest first
    snapshots.sort(key=lambda s: s.get("displayTime", ""), reverse=True)
    return snapshots


def load_snapshot(filename: str) -> Tuple[List[Dict], Dict]:
    fpath = os.path.join(SAVED_DATA_DIR, filename)
    with open(fpath, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data.get("teams", []), data


def global_search_snapshots(query: str) -> List[Dict]:
    """Searches across ALL local saved snapshot files for a Discord ID, member name, username, or team."""
    q = query.strip().lower()
    if not q:
        return []

    if not os.path.exists(SAVED_DATA_DIR):
        return []

    # Get all json files sorted newest first
    json_files = [os.path.join(SAVED_DATA_DIR, f) for f in os.listdir(SAVED_DATA_DIR) if f.endswith(".json")]
    json_files.sort(key=lambda p: os.path.getmtime(p), reverse=True)

    results = []
    seen_team_keys = set()

    for fpath in json_files:
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)

            event_slug = data.get("eventSlug", "")
            event_name = data.get("eventName", event_slug)
            display_time = data.get("displayTime", "")
            fname = os.path.basename(fpath)

            for t in data.get("teams", []):
                t_id = t.get("id") or t.get("name")
                team_key = (event_slug, t_id)
                if team_key in seen_team_keys:
                    continue

                matched_reasons = []
                matched_discords = []
                matched_names = []

                # Check members
                for m in t.get("members", []):
                    m_name = (m.get("name") or "").lower()
                    m_user = (m.get("username") or "").lower()
                    m_disc = str(m.get("discord") or "").lower()
                    m_role = (m.get("role") or "").lower()

                    if q == m_disc or (len(q) >= 4 and q in m_disc):
                        matched_reasons.append(f"Discord ID: {m.get('discord')}")
                        matched_discords.append(str(m.get('discord')))
                    elif q in m_name:
                        matched_reasons.append(f"Member: {m.get('name')}")
                        matched_names.append(m.get('name'))
                    elif q in m_user:
                        matched_reasons.append(f"Username: @{m.get('username')}")
                        matched_names.append(m.get('name'))
                    elif len(q) > 3 and q in m_role:
                        matched_reasons.append(f"Role: {m.get('role')}")

                # Check team name or description
                t_name = (t.get("name") or "").lower()
                t_desc = (t.get("description") or "").lower()
                if q in t_name:
                    matched_reasons.append(f"Team: {t.get('name')}")
                elif len(q) > 3 and q in t_desc:
                    matched_reasons.append("Idea description match")

                if matched_reasons:
                    seen_team_keys.add(team_key)
                    results.append({
                        "eventSlug": event_slug,
                        "eventName": event_name,
                        "snapshotTime": display_time,
                        "snapshotFile": fname,
                        "matchedReasons": list(dict.fromkeys(matched_reasons)),
                        "matchedDiscords": matched_discords,
                        "matchedNames": matched_names,
                        "team": t
                    })
        except Exception as err:
            print(f"Error reading {fpath}: {err}")

    return results




# ---------------------------------------------------------------------------
# Team Analyzer
# ---------------------------------------------------------------------------
def analyze_teams_api(event_id: str, event_slug: str, event_name: str, min_members: int = 1, open_only: bool = False, group_filter: int = 1, limit: int = 50, registered_participants: int = 0) -> Dict:
    global CACHED_RESULTS, CURRENT_EVENT_NAME
    CURRENT_EVENT_NAME = event_name

    thread_session = requests.Session()
    api_url = f"https://lablab.ai/api/v4/teams?eventId={event_id}"
    try:
        resp = thread_session.get(api_url, headers=HEADERS, timeout=25)
        if resp.status_code != 200:
            return {"teams": [], "csvFile": ""}
        teams_raw = resp.json().get("teams", [])
    except Exception as e:
        print(f"Error fetching teams: {e}")
        return {"teams": [], "csvFile": ""}

    # Pre-filter
    eligible = [t for t in teams_raw if len(t.get("participants", [])) >= min_members]
    if open_only:
        eligible = [t for t in eligible if t.get("joinMode") == "OPEN"]

    results = []
    inspect_count = min(len(eligible), limit)

    for i, t_raw in enumerate(eligible[:inspect_count]):
        slug = t_raw.get("slug")
        enriched = enrich_team_details(event_slug, slug, session=thread_session)
        t = enriched if enriched else t_raw

        participants_raw = t.get("participants", [])
        member_count = len(participants_raw)
        team_limit = t.get("limit", 6) or 6
        open_slots = max(0, team_limit - member_count)
        join_mode = t.get("joinMode", "OPEN")

        members = []
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

            group, reason, flag, country_name = classify_member(name, username, loc)
            if group == "Asian":
                asian_count += 1
            elif group == "International":
                intl_count += 1
            else:
                unclass_count += 1

            members.append({
                "name": name,
                "username": username,
                "location": loc,
                "country": country_name,
                "flag": flag,
                "group": group,
                "reason": reason,
                "role": role,
                "discord": discord_id
            })

        # Apply group filter
        if group_filter == 2 and intl_count < 1:
            continue
        if group_filter == 3 and intl_count <= asian_count:
            continue

        # Score
        score = 0.0
        breakdown = []
        if join_mode == "OPEN" and open_slots >= 1:
            s_val = min(open_slots * 15.0, 30.0)
            score += s_val
            breakdown.append(f"Open slots ({open_slots}): +{s_val:.0f}")
        elif open_slots > 0:
            score += 10.0
            breakdown.append(f"Slots open ({open_slots}) but {join_mode}: +10")

        if intl_count > 0:
            i_val = min(intl_count * 20.0, 40.0)
            score += i_val
            breakdown.append(f"International members ({intl_count}): +{i_val:.0f}")
        elif asian_count > 0 and intl_count == 0:
            score += 5.0
            breakdown.append("All Asian team: +5")

        core_val = min(member_count * 3.5, 15.0)
        score += core_val
        breakdown.append(f"Core team ({member_count}): +{core_val:.0f}")

        desc = t.get("description", "").strip()
        if len(desc) > 30:
            score += 15.0
            breakdown.append("Has active idea: +15")

        score = max(0.0, round(score, 1))

        if intl_count >= 1 and open_slots >= 1:
            match_tag = "🔥 International Match"
        elif open_slots >= 1:
            match_tag = "✅ Open Team (Ready)"
        else:
            match_tag = "🔒 Team Full"

        results.append({
            "id": t.get("id", ""),
            "name": t.get("name", "Unnamed"),
            "slug": slug,
            "url": f"https://lablab.ai/ai-hackathons/{event_slug}/{slug}",
            "description": desc,
            "joinMode": join_mode,
            "limit": team_limit,
            "memberCount": member_count,
            "openSlots": open_slots,
            "members": members,
            "asianCount": asian_count,
            "intlCount": intl_count,
            "unclassCount": unclass_count,
            "score": score,
            "matchTag": match_tag,
            "scoreBreakdown": "; ".join(breakdown)
        })

        time.sleep(0.15)

    results.sort(key=lambda x: (x["intlCount"], x["score"]), reverse=True)
    CACHED_RESULTS = results

    # Automatically persist snapshot to saved_data
    base_name = save_snapshot(event_slug, event_name, results, registered_participants=registered_participants)

    return {
        "teams": results,
        "csvFile": f"{base_name}.csv",
        "jsonFile": f"{base_name}.json",
        "eventName": event_name,
        "eventSlug": event_slug
    }


# ---------------------------------------------------------------------------
# Single Page Web App (HTML + CSS + Vanilla JS)
# ---------------------------------------------------------------------------
HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lablab Team Finder & Origin Analyzer</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #090d16;
            --surface: #111726;
            --surface-hover: #172033;
            --card: #141c2e;
            --border: #232f48;
            --border-focus: #38bdf8;
            --text: #f1f5f9;
            --muted: #94a3b8;
            --accent: #38bdf8;
            --accent-glow: rgba(56, 189, 248, 0.15);
            --asian: #fb923c;
            --intl: #4ade80;
            --unclass: #94a3b8;
            --radius: 14px;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Plus Jakarta Sans', -apple-system, sans-serif; }
        body { background: var(--bg); color: var(--text); padding: 25px 20px; line-height: 1.5; min-height: 100vh; }
        .container { max-width: 1240px; margin: 0 auto; }

        /* Header */
        header { text-align: center; margin-bottom: 25px; }
        .hero-badge { display: inline-flex; align-items: center; gap: 8px; background: rgba(56, 189, 248, 0.1); border: 1px solid rgba(56, 189, 248, 0.3); padding: 5px 14px; border-radius: 30px; font-size: 0.85rem; color: var(--accent); margin-bottom: 10px; font-weight: 600; }
        h1 { font-size: 2.4rem; font-weight: 800; letter-spacing: -0.5px; background: linear-gradient(135deg, #fff 30%, #93c5fd 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 6px; }
        .subtitle { color: var(--muted); font-size: 1.02rem; }

        /* Control Panel */
        .controls-panel { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 22px 24px; margin-bottom: 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); }

        .form-top { display: flex; flex-direction: column; gap: 14px; margin-bottom: 18px; }
        label { font-size: 0.82rem; font-weight: 700; color: #cbd5e1; text-transform: uppercase; letter-spacing: 0.5px; }
        select, input[type="number"], input[type="text"] { background: var(--bg); border: 1px solid var(--border); color: #fff; padding: 11px 14px; border-radius: 10px; font-size: 0.95rem; outline: none; transition: border-color 0.2s; width: 100%; }
        select:focus, input:focus { border-color: var(--border-focus); }

        /* Snapshot Mode Selector Section */
        .snapshot-bar { background: #0c1220; border: 1px solid #1f2c45; border-radius: 12px; padding: 14px 18px; display: flex; flex-wrap: wrap; gap: 16px; align-items: center; justify-content: space-between; margin-bottom: 18px; }
        .snapshot-info { display: flex; align-items: center; gap: 10px; }
        .snapshot-badge { background: rgba(56, 189, 248, 0.15); color: var(--accent); border: 1px solid var(--accent); padding: 3px 10px; border-radius: 20px; font-size: 0.8rem; font-weight: 700; }

        /* Two Primary Action Modes (Buttons) */
        .action-modes { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
        @media (max-width: 780px) { .action-modes { grid-template-columns: 1fr; } }

        .mode-card { background: #0d1424; border: 1px solid var(--border); border-radius: 12px; padding: 16px 18px; display: flex; flex-direction: column; gap: 12px; }
        .mode-title { font-size: 0.95rem; font-weight: 700; color: #fff; display: flex; align-items: center; gap: 8px; }
        .mode-desc { font-size: 0.82rem; color: var(--muted); }

        .btn-fast { background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: #fff; border: none; padding: 12px 20px; border-radius: 10px; font-weight: 700; font-size: 0.95rem; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px; transition: opacity 0.2s, transform 0.15s; }
        .btn-fast:hover { opacity: 0.95; transform: translateY(-1px); }

        .btn-fetch { background: linear-gradient(135deg, #0284c7 0%, #2563eb 100%); color: #fff; border: none; padding: 12px 20px; border-radius: 10px; font-weight: 700; font-size: 0.95rem; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px; transition: opacity 0.2s, transform 0.15s; }
        .btn-fetch:hover { opacity: 0.95; transform: translateY(-1px); }

        /* Realtime Filter Toolbar */
        .toolbar { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 14px 18px; margin-bottom: 22px; display: flex; flex-wrap: wrap; gap: 14px; align-items: center; }
        .search-wrap { flex: 2; min-width: 260px; position: relative; }
        .search-icon { position: absolute; left: 12px; top: 50%; transform: translateY(-50%); color: var(--muted); }
        .search-wrap input { padding-left: 38px; background: var(--bg); }

        .filter-select { flex: 1; min-width: 150px; }

        .btn-download:hover { background: #334155; color: #fff; }

        /* View Navigation Tabs */
        .view-tabs { display: flex; justify-content: center; gap: 12px; margin-bottom: 24px; flex-wrap: wrap; }
        .view-tab { background: var(--surface); border: 1px solid var(--border); color: var(--muted); padding: 12px 22px; border-radius: 12px; font-weight: 700; font-size: 0.95rem; cursor: pointer; display: inline-flex; align-items: center; gap: 10px; transition: all 0.2s; }
        .view-tab:hover { border-color: var(--accent); color: #fff; background: var(--surface-hover); }
        .view-tab.active { background: #1e293b; border-color: var(--accent); color: #fff; box-shadow: 0 0 20px var(--accent-glow); }
        .view-tab-badge { background: rgba(56, 189, 248, 0.2); color: var(--accent); font-size: 0.75rem; padding: 2px 8px; border-radius: 12px; font-weight: 800; }

        /* Global Search Console */
        .global-search-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 24px 28px; margin-bottom: 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); }
        .global-search-title { font-size: 1.35rem; font-weight: 800; color: #fff; margin-bottom: 6px; display: flex; align-items: center; gap: 10px; }
        .global-search-desc { font-size: 0.88rem; color: var(--muted); margin-bottom: 18px; }
        .global-input-wrap { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; margin-bottom: 12px; }
        .global-input-box { flex: 1; min-width: 280px; position: relative; }
        .global-input-box input { padding-left: 42px; font-size: 1.02rem; padding-top: 13px; padding-bottom: 13px; border-radius: 12px; border-color: #3b82f6; }
        .global-input-box input:focus { border-color: var(--accent); box-shadow: 0 0 15px rgba(56,189,248,0.25); }
        .global-input-icon { position: absolute; left: 14px; top: 50%; transform: translateY(-50%); font-size: 1.2rem; }
        .btn-global-search { background: linear-gradient(135deg, #38bdf8 0%, #2563eb 100%); color: #fff; border: none; padding: 13px 26px; border-radius: 12px; font-weight: 700; font-size: 0.98rem; cursor: pointer; display: inline-flex; align-items: center; gap: 8px; transition: transform 0.15s, opacity 0.2s; white-space: nowrap; }
        .btn-global-search:hover { opacity: 0.95; transform: translateY(-1px); }

        .quick-pills { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-top: 8px; }
        .quick-pill-label { font-size: 0.78rem; color: var(--muted); font-weight: 700; text-transform: uppercase; }
        .quick-pill { background: #0c1220; border: 1px solid var(--border); color: #cbd5e1; padding: 4px 11px; border-radius: 20px; font-size: 0.8rem; cursor: pointer; transition: all 0.15s; }
        .quick-pill:hover { border-color: var(--accent); color: var(--accent); background: rgba(56, 189, 248, 0.12); }

        /* Card Event Origin Banner */
        .card-event-header { background: linear-gradient(90deg, #172554 0%, #1e1b4b 100%); border: 1px solid #3b82f6; border-radius: 10px; padding: 10px 14px; display: flex; justify-content: space-between; align-items: center; gap: 10px; margin-bottom: 14px; flex-wrap: wrap; }
        .event-header-left { display: flex; align-items: center; gap: 8px; font-weight: 700; font-size: 0.95rem; color: #93c5fd; }
        .event-header-meta { font-size: 0.8rem; color: #cbd5e1; }
        .matched-reason-tag { background: rgba(74, 222, 128, 0.2); border: 1px solid #4ade80; color: #4ade80; font-size: 0.75rem; font-weight: 700; padding: 3px 10px; border-radius: 16px; }

        /* Highlight Matched Member */
        .member-card.matched-user { border-color: #38bdf8 !important; background: rgba(56, 189, 248, 0.1) !important; box-shadow: 0 0 16px rgba(56, 189, 248, 0.25); }
        .badge-matched-user { background: #38bdf8; color: #090d16; font-size: 0.7rem; font-weight: 800; padding: 2px 7px; border-radius: 10px; text-transform: uppercase; }

        /* Stat Counter Summary */
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 10px; margin-bottom: 24px; }
        .stat-card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 12px 10px; text-align: center; }
        .stat-val { font-size: 1.6rem; font-weight: 800; color: var(--accent); }
        .stat-val.asian { color: var(--asian); }
        .stat-val.intl { color: var(--intl); }
        .stat-name { font-size: 0.74rem; color: var(--muted); font-weight: 600; margin-top: 3px; text-transform: uppercase; }

        /* Loader */
        .loader-box { text-align: center; padding: 50px 20px; display: none; }
        .spinner { width: 44px; height: 44px; border: 4px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.8s linear infinite; margin: 0 auto 16px; }
        @keyframes spin { to { transform: rotate(360deg); } }

        /* Teams Grid */
        .teams-list { display: flex; flex-direction: column; gap: 18px; }
        .team-card { background: var(--card); border: 1px solid var(--border); border-radius: var(--radius); padding: 22px; transition: transform 0.2s, border-color 0.2s; box-shadow: 0 4px 20px rgba(0,0,0,0.2); }
        .team-card:hover { transform: translateY(-2px); border-color: var(--accent); }

        .card-top { display: flex; justify-content: space-between; align-items: flex-start; gap: 14px; margin-bottom: 12px; flex-wrap: wrap; }
        .team-name { font-size: 1.35rem; font-weight: 700; color: #fff; }
        .ratio-pill { display: inline-flex; align-items: center; gap: 6px; font-size: 0.85rem; font-weight: 600; padding: 4px 12px; border-radius: 20px; background: rgba(255,255,255,0.06); border: 1px solid var(--border); margin-top: 6px; }
        .score-wrap { text-align: right; }
        .score-num { font-size: 1.8rem; font-weight: 800; color: var(--accent); }
        .match-badge { font-size: 0.75rem; font-weight: 700; padding: 3px 10px; border-radius: 20px; border: 1px solid var(--accent); color: var(--accent); background: var(--accent-glow); }

        .pills-row { display: flex; gap: 10px; margin-bottom: 14px; flex-wrap: wrap; }
        .pill { font-size: 0.82rem; font-weight: 600; padding: 4px 10px; border-radius: 8px; background: #1e293b; border: 1px solid var(--border); }
        .pill-open { color: #4ade80; border-color: rgba(74, 222, 128, 0.4); background: rgba(74, 222, 128, 0.1); }
        .pill-full { color: var(--muted); }

        .idea-box { background: #0b101b; padding: 12px 16px; border-radius: 10px; font-size: 0.92rem; color: #cbd5e1; border-left: 3px solid var(--accent); margin-bottom: 16px; }
        .idea-box.empty { font-style: italic; color: var(--muted); border-left-color: var(--border); }

        .members-title { font-size: 0.8rem; font-weight: 700; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px; }
        .members-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(290px, 1fr)); gap: 10px; }
        .member-card { background: #0e1524; border: 1px solid var(--border); border-radius: 10px; padding: 10px 14px; display: flex; flex-direction: column; gap: 4px; }
        .member-header { display: flex; align-items: center; justify-content: space-between; gap: 6px; }
        .member-name { font-size: 0.92rem; font-weight: 600; color: #fff; }
        .tag-group { font-size: 0.72rem; font-weight: 700; padding: 2px 8px; border-radius: 12px; }
        .tag-asian { background: rgba(251, 146, 60, 0.15); color: var(--asian); border: 1px solid var(--asian); }
        .tag-intl { background: rgba(74, 222, 128, 0.15); color: var(--intl); border: 1px solid var(--intl); }
        .tag-unclass { background: rgba(148, 163, 184, 0.15); color: var(--unclass); border: 1px solid var(--unclass); }
        .member-meta { font-size: 0.78rem; color: var(--muted); display: flex; flex-wrap: wrap; gap: 8px; }
        .discord-tag { color: #a78bfa; font-weight: 500; }

        .card-footer { display: flex; justify-content: space-between; align-items: center; margin-top: 16px; padding-top: 14px; border-top: 1px solid var(--border); }
        .btn-view { background: var(--accent); color: #090d16; padding: 8px 16px; border-radius: 8px; font-weight: 700; font-size: 0.88rem; text-decoration: none; transition: opacity 0.2s; }
        .btn-view:hover { opacity: 0.9; }

        .no-results { text-align: center; padding: 50px 20px; color: var(--muted); font-size: 1.1rem; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="hero-badge">⚡ Lablab.ai Active Hackathons</div>
            <h1>Lablab Team Finder & Origin Filter</h1>
            <p class="subtitle">Search, save, and filter teams with member size, available slots, and Asian vs. International origin.</p>
        </header>

        <!-- View Navigation Switcher -->
        <div class="view-tabs">
            <button class="view-tab active" id="tabBrowser" onclick="switchMainTab('browser')">
                <span>🎯 Hackathon Browser</span>
            </button>
            <button class="view-tab" id="tabGlobal" onclick="switchMainTab('global')">
                <span>🌍 Global Search (All Saved Files & Discord IDs)</span>
                <span class="view-tab-badge">⚡ Instant</span>
            </button>
        </div>

        <!-- VIEW 1: Single Hackathon Browser -->
        <div id="viewBrowser">
            <!-- Main Control Panel -->
            <section class="controls-panel">
                <div class="form-top">
                    <label>1. Select Active Hackathon</label>
                <select id="eventSelect">
                    <option value="">Loading active hackathons...</option>
                </select>
            </div>

            <!-- Saved Snapshot Status Bar -->
            <div class="snapshot-bar" id="snapshotBar">
                <div class="snapshot-info">
                    <span class="snapshot-badge" id="snapshotStatusBadge">Checking saved data...</span>
                    <span id="snapshotStatusText" style="font-size: 0.85rem; color: #cbd5e1;"></span>
                </div>
            </div>

            <!-- 2-Action Choices: Fast Saved Data vs Fetch Fresh -->
            <div class="action-modes">
                <!-- Option A: Fast Search in Saved Data -->
                <div class="mode-card" id="modeSaved">
                    <div class="mode-title">
                        <span>⚡ Option A: Fast Search in Saved Data</span>
                    </div>
                    <div class="mode-desc">Load previously scraped data instantly (0.1s) without waiting for web scraping.</div>
                    <div style="display: flex; flex-direction: column; gap: 6px;">
                        <label style="font-size: 0.75rem;">Choose Saved Version:</label>
                        <select id="savedFileSelect" style="padding: 9px 12px; font-size: 0.88rem;">
                            <option value="">No saved files available</option>
                        </select>
                    </div>
                    <button class="btn-fast" id="btnLoadSaved">
                        <span>📂 Load Saved Snapshot (Instant)</span>
                    </button>
                </div>

                <!-- Option B: Fetch Fresh Live Data -->
                <div class="mode-card">
                    <div class="mode-title">
                        <span>🔄 Option B: Fetch Fresh Live Data</span>
                    </div>
                    <div class="mode-desc">Crawl the latest live teams from Lablab.ai and automatically save a new version.</div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                        <div>
                            <label style="font-size: 0.75rem;">Min Members:</label>
                            <input type="number" id="minMembers" min="1" max="6" value="1" style="padding: 8px 10px; font-size: 0.88rem;">
                        </div>
                        <div>
                            <label style="font-size: 0.75rem;">Crawl Limit:</label>
                            <input type="number" id="inspectLimit" min="10" max="300" value="90" style="padding: 8px 10px; font-size: 0.88rem;">
                        </div>
                    </div>
                    <button class="btn-fetch" id="btnFetchLive">
                        <span>🌐 Fetch & Save New Version</span>
                    </button>
                </div>
            </div>
        </section>

        <!-- Stats Bar -->
        <div class="stats-grid" id="statsBar" style="display: none;">
            <div class="stat-card">
                <div class="stat-val" id="statQualified">0</div>
                <div class="stat-name">Matching Teams</div>
            </div>
            <div class="stat-card" title="Total registered hackers enrolled on Lablab.ai for this hackathon">
                <div class="stat-val" id="statEnrolled" style="color: #c084fc;">0</div>
                <div class="stat-name">Enrolled on Lablab</div>
            </div>
            <div class="stat-card" title="Total participants placed inside formed teams">
                <div class="stat-val" id="statTotalParticipants" style="color: #38bdf8;">0</div>
                <div class="stat-name">Members in Teams</div>
            </div>
            <div class="stat-card" title="Registered hackers who have not joined or formed any team yet">
                <div class="stat-val" id="statSoloHackers" style="color: #facc15;">0</div>
                <div class="stat-name">Solo (Looking for Team)</div>
            </div>
            <div class="stat-card">
                <div class="stat-val" id="statOpen">0</div>
                <div class="stat-name">Teams with Open Slots</div>
            </div>
            <div class="stat-card">
                <div class="stat-val intl" id="statIntlTeams">0</div>
                <div class="stat-name">International Teams</div>
            </div>
            <div class="stat-card">
                <div class="stat-val asian" id="statAsianMembers">0</div>
                <div class="stat-name">Asian Members</div>
            </div>
            <div class="stat-card">
                <div class="stat-val intl" id="statIntlMembers">0</div>
                <div class="stat-name">Int'l Members</div>
            </div>
        </div>

        <!-- Real-Time Filter & Search Toolbar -->
        <div class="toolbar" id="toolbar" style="display: none;">
            <!-- Keyword Search -->
            <div class="search-wrap">
                <span class="search-icon">🔍</span>
                <input type="text" id="searchInput" placeholder="Filter by team name, idea, or member name...">
                <div style="margin-top: 6px; display: flex; justify-content: flex-end;">
                    <a href="javascript:void(0)" onclick="jumpToGlobalSearch()" style="font-size: 0.76rem; color: #38bdf8; text-decoration: none;">
                        🌍 Looking for a Discord ID or member across all hackathons? <b>Search Globally ↗</b>
                    </a>
                </div>
            </div>

            <!-- Member Count Dropdown -->
            <div class="filter-select">
                <select id="memberSizeFilter">
                    <option value="all">👥 All Member Sizes</option>
                    <option value="3+">👥 3+ Members (Ready)</option>
                    <option value="4+">👥 4+ Members</option>
                    <option value="1">1 Member</option>
                    <option value="2">2 Members</option>
                    <option value="3">3 Members</option>
                    <option value="4">4 Members</option>
                    <option value="5">5 Members</option>
                    <option value="6">6 Members</option>
                </select>
            </div>

            <!-- Slot Status Filter -->
            <div class="filter-select">
                <select id="slotStatusFilter">
                    <option value="all" selected>🔓 All Slots (Open & Full)</option>
                    <option value="open">✅ Open Slots Only</option>
                    <option value="full">❌ Full Teams Only</option>
                </select>
            </div>

            <!-- Origin Composition Filter -->
            <div class="filter-select">
                <select id="originFilter">
                    <option value="all">🌐 All Origins</option>
                    <option value="intl">🌎 With International (1+)</option>
                    <option value="mostly_intl">🌎 Mostly International</option>
                    <option value="asian">🌏 All Asian</option>
                </select>
            </div>

            <!-- Download CSV -->
            <a href="/api/export-csv" class="btn-download" id="btnExport">
                📥 Download CSV
            </a>
        </div>

        <!-- Loader Box -->
        <div class="loader-box" id="loader">
            <div class="spinner"></div>
            <p style="font-size: 1.15rem; color: #fff; font-weight: 700;" id="loaderMsg">Fetching & Analyzing Teams...</p>
            <p style="font-size: 0.88rem; color: var(--muted); margin-top: 4px;">Checking profile countries, name patterns, and open slots...</p>
        </div>

        <!-- Teams List Container -->
        <div class="teams-list" id="teamsContainer"></div>
    </div><!-- /#viewBrowser -->

    <!-- VIEW 2: Global Cross-Hackathon & Discord ID Search -->
    <div id="viewGlobal" style="display: none;">
        <section class="global-search-card">
            <div class="global-search-title">
                <span>🌍 Global Member & Discord ID Search</span>
            </div>
            <div class="global-search-desc">
                Search across all local saved snapshots simultaneously. Enter a <b>Discord ID number</b>, <b>Member name</b>, or <b>Username</b> to find which hackathon and team they belong to.
            </div>
            <div class="global-input-wrap">
                <div class="global-input-box">
                    <span class="global-input-icon">🎮</span>
                    <input type="text" id="globalSearchInput" placeholder="Enter Discord ID (e.g. 1388751820003999816), member name, or username...">
                </div>
                <button class="btn-global-search" id="btnRunGlobalSearch">
                    <span>🔍 Search All Hackathons</span>
                </button>
                <button class="btn-download" id="btnClearGlobalSearch" style="padding: 13px 18px;">
                    <span>✕ Clear</span>
                </button>
            </div>
            <div class="quick-pills">
                <span class="quick-pill-label">Try Example:</span>
                <button class="quick-pill" onclick="quickSearchGlobal('1388751820003999816')">🎮 1388751820003999816</button>
                <button class="quick-pill" onclick="quickSearchGlobal('Julien')">👤 Julien</button>
                <button class="quick-pill" onclick="quickSearchGlobal('Dalson')">👤 Dalson</button>
                <button class="quick-pill" onclick="quickSearchGlobal('Thu Ta')">👤 Thu Ta</button>
            </div>
        </section>

        <!-- Global Search Loader -->
        <div class="loader-box" id="globalLoader">
            <div class="spinner"></div>
            <p style="font-size: 1.15rem; color: #fff; font-weight: 700;">Searching across all saved hackathons...</p>
            <p style="font-size: 0.88rem; color: var(--muted); margin-top: 4px;">Checking Discord IDs, usernames, and member profiles...</p>
        </div>

        <!-- Global Search Stats Summary -->
        <div id="globalResultsHeader" style="margin-bottom: 18px; display: none;">
            <span id="globalResultsCount" style="font-size: 1.1rem; font-weight: 700; color: #38bdf8;"></span>
        </div>

        <!-- Global Search Results List -->
        <div class="teams-list" id="globalResultsContainer">
            <div class="no-results" style="padding: 50px 20px; text-align: center;">
                <div style="font-size: 2.2rem; margin-bottom: 10px;">🔍</div>
                <div style="font-size: 1.15rem; font-weight: 700; color: #f1f5f9; margin-bottom: 6px;">Global Hackathon & Discord Lookup</div>
                <div style="color: var(--muted); font-size: 0.92rem;">Enter any Discord ID (like <code>1388751820003999816</code>) or member name above to find their team and hackathon instantly.</div>
            </div>
        </div>
    </div><!-- /#viewGlobal -->
</div><!-- /.container -->

    <script>
        let allLoadedTeams = [];
        let currentEventSlug = "";
        let currentEventName = "";
        let currentEventParticipants = 0;

        // 1. Fetch truly active events on page load
        async function loadActiveEvents() {
            const sel = document.getElementById('eventSelect');
            try {
                const res = await fetch('/api/events');
                const events = await res.json();
                sel.innerHTML = '';
                if (!events.length) {
                    sel.innerHTML = '<option>No active hackathons found</option>';
                    return;
                }
                events.forEach(ev => {
                    const opt = document.createElement('option');
                    opt.value = ev.id;
                    opt.dataset.slug = ev.slug;
                    opt.dataset.name = ev.name;
                    opt.dataset.participants = ev.registeredParticipants || 0;
                    const partsText = ev.registeredParticipants ? ` | 👥 ${ev.registeredParticipants.toLocaleString()} enrolled` : '';
                    const dates = ev.endAt ? `Ends: ${ev.endAt.slice(0, 10)}` : 'Active';
                    opt.textContent = `${ev.name} (${dates}${partsText})`;
                    sel.appendChild(opt);
                });

                // Check snapshots for initial event
                onEventChange();
            } catch (err) {
                sel.innerHTML = '<option>Error loading active events</option>';
            }
        }

        function resetFilters() {
            const search = document.getElementById('searchInput');
            if (search) search.value = '';
            const size = document.getElementById('memberSizeFilter');
            if (size) size.value = 'all';
            const slot = document.getElementById('slotStatusFilter');
            if (slot) slot.value = 'all';
            const origin = document.getElementById('originFilter');
            if (origin) origin.value = 'all';
        }

        function resetFiltersAndApply() {
            resetFilters();
            applyFilters();
        }

        // 2. When user switches event, check for existing saved files
        async function onEventChange(skipAutoLoad = false) {
            const sel = document.getElementById('eventSelect');
            const opt = sel.options[sel.selectedIndex];
            if (!opt || !opt.value) return;

            currentEventSlug = opt.dataset.slug;
            currentEventName = opt.dataset.name || opt.textContent;
            currentEventParticipants = parseInt(opt.dataset.participants || "0", 10);

            if (!skipAutoLoad) {
                resetFilters();
                allLoadedTeams = [];
                document.getElementById('teamsContainer').innerHTML = '';
                document.getElementById('statsBar').style.display = 'none';
                document.getElementById('toolbar').style.display = 'none';
            }

            const badge = document.getElementById('snapshotStatusBadge');
            const text = document.getElementById('snapshotStatusText');
            const savedSelect = document.getElementById('savedFileSelect');
            const btnLoad = document.getElementById('btnLoadSaved');

            badge.textContent = "Checking...";
            badge.style.background = "rgba(148, 163, 184, 0.15)";
            badge.style.color = "var(--muted)";
            badge.style.borderColor = "var(--border)";

            try {
                const res = await fetch(`/api/snapshots?eventSlug=${encodeURIComponent(currentEventSlug)}`);
                const snapshots = await res.json();

                savedSelect.innerHTML = '';
                if (snapshots.length > 0) {
                    badge.textContent = `📁 ${snapshots.length} Saved Snapshot(s) Available`;
                    badge.style.background = "rgba(16, 185, 129, 0.15)";
                    badge.style.color = "#34d399";
                    badge.style.borderColor = "#10b981";
                    text.textContent = `Latest snapshot from ${snapshots[0].displayTime} with ${snapshots[0].teamCount} teams.`;

                    snapshots.forEach(s => {
                        const sOpt = document.createElement('option');
                        sOpt.value = s.filename;
                        sOpt.textContent = `📄 ${s.displayTime} (${s.teamCount} teams)`;
                        savedSelect.appendChild(sOpt);
                    });
                    btnLoad.disabled = false;
                    btnLoad.style.opacity = "1";

                    // Automatically load newest snapshot immediately on event switch!
                    if (!skipAutoLoad) {
                        await loadSavedSnapshot(snapshots[0].filename);
                    }
                } else {
                    badge.textContent = "ℹ️ No Saved Files Yet";
                    text.textContent = "First time? Click 'Fetch & Save New Version' to crawl and save live data.";
                    savedSelect.innerHTML = '<option value="">No saved files for this hackathon</option>';
                    btnLoad.disabled = true;
                    btnLoad.style.opacity = "0.4";

                    if (!skipAutoLoad) {
                        document.getElementById('teamsContainer').innerHTML = `
                            <div class="no-results" style="padding: 40px 20px; text-align: center;">
                                <div style="font-size: 1.15rem; font-weight: 700; color: #f1f5f9; margin-bottom: 8px;">No saved snapshot found for this hackathon yet</div>
                                <div style="color: var(--muted); font-size: 0.9rem;">Click <b>"🌐 Fetch & Save New Version"</b> below to crawl the latest teams from Lablab.ai.</div>
                            </div>
                        `;
                    }
                }
            } catch (err) {
                badge.textContent = "Error checking saved files";
            }
        }

        // 3. Option A: Instant Load from Saved Snapshot
        async function loadSavedSnapshot(targetFilename) {
            const fileSelect = document.getElementById('savedFileSelect');
            const filename = (typeof targetFilename === 'string' && targetFilename) ? targetFilename : fileSelect.value;
            if (!filename) return;

            showLoader("Loading Saved Snapshot...", "Parsing cached JSON file...");
            try {
                const res = await fetch('/api/load-snapshot', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ filename })
                });
                const data = await res.json();
                allLoadedTeams = data.teams || [];
                if (data.meta && data.meta.registeredParticipants) {
                    currentEventParticipants = data.meta.registeredParticipants;
                }
                if (data.csvFile) {
                    document.getElementById('btnExport').href = `/api/export-csv?file=${encodeURIComponent(data.csvFile)}`;
                }
                applyFilters();
            } catch (err) {
                document.getElementById('teamsContainer').innerHTML = `<div class="no-results">Error loading saved snapshot: ${err.message}</div>`;
            } finally {
                hideLoader();
            }
        }

        // 4. Option B: Fetch Fresh Live Data
        async function fetchFreshLiveData() {
            const sel = document.getElementById('eventSelect');
            const opt = sel.options[sel.selectedIndex];
            if (!opt || !opt.value) return;

            const eventId = opt.value;
            const eventSlug = opt.dataset.slug;
            const eventName = opt.dataset.name;
            const minMembers = parseInt(document.getElementById('minMembers').value) || 1;
            const limit = parseInt(document.getElementById('inspectLimit').value) || 90;
            const registeredParticipants = parseInt(opt.dataset.participants || "0", 10);

            showLoader("Crawling & Analyzing Live Teams...", "Fetching from Lablab.ai API and saving snapshot file...");

            try {
                const res = await fetch('/api/analyze', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ eventId, eventSlug, eventName, minMembers, limit, registeredParticipants })
                });
                const data = await res.json();
                allLoadedTeams = data.teams || [];
                if (data.csvFile) {
                    document.getElementById('btnExport').href = `/api/export-csv?file=${encodeURIComponent(data.csvFile)}`;
                }
                applyFilters();
                // Refresh snapshot list without wiping live data
                onEventChange(true);
            } catch (err) {
                document.getElementById('teamsContainer').innerHTML = `<div class="no-results">Error fetching live data: ${err.message}</div>`;
            } finally {
                hideLoader();
            }
        }

        // 5. Multi-Filter Logic (Keyword, Member Size, Slot Status, Origin)
        function applyFilters() {
            const query = document.getElementById('searchInput').value.toLowerCase().trim();
            const sizeFilter = document.getElementById('memberSizeFilter').value;
            const slotFilter = document.getElementById('slotStatusFilter').value;
            const originFilter = document.getElementById('originFilter').value;

            let filtered = allLoadedTeams.filter(t => {
                // Member Size filter
                if (sizeFilter === "3+" && t.memberCount < 3) return false;
                if (sizeFilter === "4+" && t.memberCount < 4) return false;
                if (["1","2","3","4","5","6"].includes(sizeFilter) && t.memberCount !== parseInt(sizeFilter)) return false;

                // Slot filter
                if (slotFilter === "open" && t.openSlots < 1) return false;
                if (slotFilter === "full" && t.openSlots > 0) return false;

                // Origin filter
                if (originFilter === "intl" && t.intlCount < 1) return false;
                if (originFilter === "mostly_intl" && t.intlCount <= t.asianCount) return false;
                if (originFilter === "asian" && (t.asianCount === 0 || t.intlCount > 0)) return false;

                // Keyword search
                if (query) {
                    const inName = t.name.toLowerCase().includes(query);
                    const inDesc = (t.description || '').toLowerCase().includes(query);
                    const inMembers = t.members.some(m => m.name.toLowerCase().includes(query) || (m.role || '').toLowerCase().includes(query) || (m.reason || '').toLowerCase().includes(query));
                    if (!inName && !inDesc && !inMembers) return false;
                }

                return true;
            });

            renderTeams(filtered);
            updateStats(filtered);
        }

        // 6. Render Team Cards
        function renderTeams(teams) {
            const container = document.getElementById('teamsContainer');
            container.innerHTML = '';

            if (!teams.length) {
                if (!allLoadedTeams.length) {
                    container.innerHTML = `
                        <div class="no-results" style="padding: 40px 20px; text-align: center;">
                            <div style="font-size: 1.15rem; font-weight: 700; color: #f1f5f9; margin-bottom: 8px;">No teams found in this snapshot</div>
                            <div style="color: var(--muted); font-size: 0.9rem;">Click <b>"🌐 Fetch & Save New Version"</b> above to crawl live teams from Lablab.ai.</div>
                        </div>
                    `;
                } else {
                    container.innerHTML = `
                        <div class="no-results" style="padding: 35px 20px; text-align: center;">
                            <div style="font-size: 1.15rem; font-weight: 700; color: #f1f5f9; margin-bottom: 8px;">No teams match the current filters</div>
                            <div style="color: var(--muted); font-size: 0.9rem; margin-bottom: 16px;">
                                You have <b>${allLoadedTeams.length} teams</b> loaded, but your search text or dropdown filters hidden all of them.
                            </div>
                            <button onclick="resetFiltersAndApply()" style="background: #38bdf8; color: #090d16; font-weight: 700; border: none; padding: 9px 20px; border-radius: 8px; cursor: pointer; font-size: 0.92rem; box-shadow: 0 2px 10px rgba(56,189,248,0.25);">
                                🔄 Reset All Filters (Show All ${allLoadedTeams.length} Teams)
                            </button>
                        </div>
                    `;
                }
                return;
            }

            teams.forEach((t, idx) => {
                const card = document.createElement('div');
                card.className = 'team-card';

                const membersHtml = t.members.map(m => `
                    <div class="member-card">
                        <div class="member-header">
                            <span class="member-name">${m.flag} ${m.name} (@${m.username})</span>
                            <span class="tag-group tag-${m.group.toLowerCase()}">${m.group}</span>
                        </div>
                        <div class="member-meta">
                            <span>📌 ${m.reason}</span>
                            ${m.role ? `<span>💼 ${m.role}</span>` : ''}
                            ${m.discord ? `<span class="discord-tag">🎮 Discord: ${m.discord}</span>` : ''}
                        </div>
                    </div>
                `).join('');

                card.innerHTML = `
                    <div class="card-top">
                        <div>
                            <div class="team-name">#${idx+1} ${t.name}</div>
                            <div class="ratio-pill">
                                <span>🌏 ${t.asianCount} Asian</span>
                                <span>•</span>
                                <span>🌎 ${t.intlCount} International</span>
                                ${t.unclassCount > 0 ? `<span>• ❓ ${t.unclassCount} Other</span>` : ''}
                            </div>
                        </div>
                        <div class="score-wrap">
                            <div class="score-num">${t.score}</div>
                            <div class="match-badge">${t.matchTag}</div>
                        </div>
                    </div>

                    <div class="pills-row">
                        <span class="pill">👥 ${t.memberCount}/${t.limit} Members</span>
                        <span class="pill ${t.openSlots > 0 ? 'pill-open' : 'pill-full'}">
                            ${t.openSlots > 0 ? `✅ ${t.openSlots} Slot(s) Available` : '❌ Team Full'}
                        </span>
                        <span class="pill">🔒 Mode: ${t.joinMode}</span>
                    </div>

                    ${t.description ? `<div class="idea-box">💡 ${t.description}</div>` : '<div class="idea-box empty">No idea description provided yet.</div>'}

                    <div class="members-title">Team Members (${t.members.length}):</div>
                    <div class="members-grid">${membersHtml}</div>

                    <div class="card-footer">
                        <span style="font-size: 0.8rem; color: var(--muted);">${t.scoreBreakdown}</span>
                        <a href="${t.url}" target="_blank" class="btn-view">Open on Lablab ↗</a>
                    </div>
                `;
                container.appendChild(card);
            });

            document.getElementById('statsBar').style.display = 'grid';
            document.getElementById('toolbar').style.display = 'flex';
        }

        // 7. Stats
        function updateStats(teams) {
            document.getElementById('statQualified').textContent = teams.length;
            const totalParts = teams.reduce((sum, t) => sum + (t.memberCount || (t.members ? t.members.length : 0)), 0);
            document.getElementById('statTotalParticipants').textContent = totalParts;

            const enrolled = currentEventParticipants || 0;
            if (enrolled > 0) {
                document.getElementById('statEnrolled').textContent = enrolled.toLocaleString();
                const solo = Math.max(0, enrolled - totalParts);
                document.getElementById('statSoloHackers').textContent = solo.toLocaleString();
            } else {
                document.getElementById('statEnrolled').textContent = totalParts;
                document.getElementById('statSoloHackers').textContent = '—';
            }

            document.getElementById('statOpen').textContent = teams.filter(t => t.openSlots > 0).length;
            document.getElementById('statIntlTeams').textContent = teams.filter(t => t.intlCount > 0).length;
            document.getElementById('statAsianMembers').textContent = teams.reduce((sum, t) => sum + t.asianCount, 0);
            document.getElementById('statIntlMembers').textContent = teams.reduce((sum, t) => sum + t.intlCount, 0);
        }

        function showLoader(title, subtitle) {
            document.getElementById('loaderMsg').textContent = title;
            document.getElementById('loader').style.display = 'block';
            document.getElementById('teamsContainer').innerHTML = '';
            document.getElementById('statsBar').style.display = 'none';
            document.getElementById('toolbar').style.display = 'none';
            document.getElementById('btnLoadSaved').disabled = true;
            document.getElementById('btnFetchLive').disabled = true;
        }

        function hideLoader() {
            document.getElementById('loader').style.display = 'none';
            document.getElementById('btnLoadSaved').disabled = false;
            document.getElementById('btnFetchLive').disabled = false;
        }

        // -------------------------------------------------------------
        // View Switching & Global Search Logic
        // -------------------------------------------------------------
        function switchMainTab(mode) {
            const tabBrowser = document.getElementById('tabBrowser');
            const tabGlobal = document.getElementById('tabGlobal');
            const viewBrowser = document.getElementById('viewBrowser');
            const viewGlobal = document.getElementById('viewGlobal');

            if (mode === 'global') {
                tabBrowser.classList.remove('active');
                tabGlobal.classList.add('active');
                viewBrowser.style.display = 'none';
                viewGlobal.style.display = 'block';
                document.getElementById('globalSearchInput').focus();
            } else {
                tabGlobal.classList.remove('active');
                tabBrowser.classList.add('active');
                viewGlobal.style.display = 'none';
                viewBrowser.style.display = 'block';
            }
        }

        function jumpToGlobalSearch() {
            const val = document.getElementById('searchInput').value.trim();
            switchMainTab('global');
            if (val) {
                document.getElementById('globalSearchInput').value = val;
                runGlobalSearch();
            }
        }

        function quickSearchGlobal(term) {
            document.getElementById('globalSearchInput').value = term;
            runGlobalSearch();
        }

        async function runGlobalSearch() {
            const input = document.getElementById('globalSearchInput');
            const query = input.value.trim();
            if (!query) {
                input.focus();
                return;
            }

            const loader = document.getElementById('globalLoader');
            const resultsContainer = document.getElementById('globalResultsContainer');
            const resultsHeader = document.getElementById('globalResultsHeader');
            const countSpan = document.getElementById('globalResultsCount');

            loader.style.display = 'block';
            resultsContainer.innerHTML = '';
            resultsHeader.style.display = 'none';

            try {
                const res = await fetch(`/api/global-search?q=${encodeURIComponent(query)}`);
                const data = await res.json();
                const results = data.results || [];

                loader.style.display = 'none';
                resultsHeader.style.display = 'block';
                countSpan.textContent = `Found ${results.length} team match${results.length === 1 ? '' : 'es'} across all saved hackathons for "${query}"`;

                if (!results.length) {
                    resultsContainer.innerHTML = `
                        <div class="no-results" style="padding: 50px 20px; text-align: center;">
                            <div style="font-size: 2.2rem; margin-bottom: 10px;">🔍</div>
                            <div style="font-size: 1.15rem; font-weight: 700; color: #f1f5f9; margin-bottom: 6px;">No matches found for "${query}"</div>
                            <div style="color: var(--muted); font-size: 0.92rem;">
                                Checked all local saved snapshots. No Discord ID, name, username, or team matched this query.<br>
                                Try verifying the Discord ID or name spelling.
                            </div>
                        </div>
                    `;
                    return;
                }

                results.forEach(item => {
                    const t = item.team;
                    const card = document.createElement('div');
                    card.className = 'team-card';

                    const membersHtml = t.members.map(m => {
                        const mDiscStr = String(m.discord || '');
                        const isMatched = (item.matchedDiscords && item.matchedDiscords.includes(mDiscStr)) ||
                                          (item.matchedNames && item.matchedNames.includes(m.name)) ||
                                          (m.name && m.name.toLowerCase().includes(query.toLowerCase())) ||
                                          (mDiscStr && (mDiscStr === query || (query.length >= 5 && mDiscStr.includes(query))));

                        return `
                            <div class="member-card ${isMatched ? 'matched-user' : ''}">
                                <div class="member-header">
                                    <span class="member-name">${m.flag} ${m.name} (@${m.username})</span>
                                    <div style="display: flex; gap: 4px; align-items: center;">
                                        ${isMatched ? '<span class="badge-matched-user">⭐ MATCHED</span>' : ''}
                                        <span class="tag-group tag-${m.group.toLowerCase()}">${m.group}</span>
                                    </div>
                                </div>
                                <div class="member-meta">
                                    <span>📌 ${m.reason}</span>
                                    ${m.role ? `<span>💼 ${m.role}</span>` : ''}
                                    ${m.discord ? `<span class="discord-tag" style="${isMatched ? 'background: #38bdf8; color: #090d16; font-weight: 800; border-color: #38bdf8;' : ''}">🎮 Discord: ${m.discord}</span>` : ''}
                                </div>
                            </div>
                        `;
                    }).join('');

                    card.innerHTML = `
                        <!-- Event Origin Header -->
                        <div class="card-event-header">
                            <div class="event-header-left">
                                <span>🏆 Hackathon: ${item.eventName}</span>
                                <span class="event-header-meta">(Saved: ${item.snapshotTime})</span>
                            </div>
                            <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
                                ${item.matchedReasons.map(r => `<span class="matched-reason-tag">🎯 ${r}</span>`).join('')}
                            </div>
                        </div>

                        <div class="card-top">
                            <div>
                                <span class="team-name">${t.name}</span>
                                <div class="ratio-pill">
                                    <span>👥 ${t.memberCount}/${t.limit} Members</span>
                                    <span style="color: var(--asian)">• 🌏 ${t.asianCount} Asian</span>
                                    <span style="color: var(--intl)">• 🌎 ${t.intlCount} Int'l</span>
                                </div>
                            </div>
                            <div class="score-wrap">
                                <span class="score-num">${t.score}</span>
                                <div class="match-badge">${t.matchTag}</div>
                            </div>
                        </div>

                        <div class="pills-row">
                            <span class="pill ${t.openSlots > 0 ? 'pill-open' : 'pill-full'}">
                                ${t.openSlots > 0 ? `🔓 ${t.openSlots} Open Slot(s)` : '🔒 Team Full'}
                            </span>
                            <span class="pill">${t.joinMode === 'OPEN' ? '⚡ Open to Join' : '📩 ' + t.joinMode}</span>
                        </div>

                        <div class="idea-box ${t.description ? '' : 'empty'}">
                            <b>💡 Project Idea:</b> ${t.description ? t.description : 'No idea pitch provided yet.'}
                        </div>

                        <div class="members-title">Team Roster (${t.members.length} Members)</div>
                        <div class="members-grid">
                            ${membersHtml}
                        </div>

                        <div style="margin-top: 14px; display: flex; justify-content: space-between; align-items: center; border-top: 1px solid var(--border); padding-top: 12px; flex-wrap: wrap; gap: 8px;">
                            <span style="font-size: 0.8rem; color: var(--muted);">${t.scoreBreakdown || ''}</span>
                            <a href="${t.url}" target="_blank" class="btn-view">Open on Lablab ↗</a>
                        </div>
                    `;

                    resultsContainer.appendChild(card);
                });
            } catch (err) {
                loader.style.display = 'none';
                resultsContainer.innerHTML = `<div class="no-results">Error executing global search: ${err.message}</div>`;
            }
        }

        // Event Listeners
        document.getElementById('eventSelect').addEventListener('change', () => onEventChange(false));
        document.getElementById('savedFileSelect').addEventListener('change', () => loadSavedSnapshot());
        document.getElementById('btnLoadSaved').addEventListener('click', () => loadSavedSnapshot());
        document.getElementById('btnFetchLive').addEventListener('click', fetchFreshLiveData);

        // Realtime search & dropdown filter listeners (Single Hackathon View)
        document.getElementById('searchInput').addEventListener('input', applyFilters);
        document.getElementById('memberSizeFilter').addEventListener('change', applyFilters);
        document.getElementById('slotStatusFilter').addEventListener('change', applyFilters);
        document.getElementById('originFilter').addEventListener('change', applyFilters);

        // Global Search Listeners
        document.getElementById('btnRunGlobalSearch').addEventListener('click', runGlobalSearch);
        document.getElementById('globalSearchInput').addEventListener('keydown', (e) => {
            if (e.key === 'Enter') runGlobalSearch();
        });
        document.getElementById('btnClearGlobalSearch').addEventListener('click', () => {
            document.getElementById('globalSearchInput').value = '';
            document.getElementById('globalResultsContainer').innerHTML = `
                <div class="no-results" style="padding: 50px 20px; text-align: center;">
                    <div style="font-size: 2.2rem; margin-bottom: 10px;">🔍</div>
                    <div style="font-size: 1.15rem; font-weight: 700; color: #f1f5f9; margin-bottom: 6px;">Global Hackathon & Discord Lookup</div>
                    <div style="color: var(--muted); font-size: 0.92rem;">Enter any Discord ID (like <code>1388751820003999816</code>) or member name above to find their team and hackathon instantly.</div>
                </div>
            `;
            document.getElementById('globalResultsHeader').style.display = 'none';
            document.getElementById('globalSearchInput').focus();
        });

        window.addEventListener('DOMContentLoaded', loadActiveEvents);
    </script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# HTTP Server API Routing
# ---------------------------------------------------------------------------
class AppRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))

        elif path == "/api/events":
            events = get_truly_active_events()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(events).encode("utf-8"))

        elif path == "/api/snapshots":
            event_slug = query.get("eventSlug", [None])[0]
            snapshots = get_saved_snapshots(event_slug)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(snapshots).encode("utf-8"))

        elif path == "/api/global-search":
            q = query.get("q", [""])[0]
            results = global_search_snapshots(q)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "query": q,
                "totalMatches": len(results),
                "results": results
            }).encode("utf-8"))

        elif path == "/api/export-csv":
            target_file = query.get("file", [None])[0]
            if target_file:
                safe_name = os.path.basename(target_file)
                full_csv_path = os.path.join(SAVED_DATA_DIR, safe_name)
                if os.path.exists(full_csv_path):
                    self.send_response(200)
                    self.send_header("Content-Type", "text/csv; charset=utf-8")
                    self.send_header("Content-Disposition", f"attachment; filename={safe_name}")
                    self.end_headers()
                    with open(full_csv_path, "rb") as f:
                        self.wfile.write(f.read())
                    return

            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", f"attachment; filename={CURRENT_EVENT_NAME.replace(' ', '_')}_teams.csv")
            self.end_headers()

            import io
            out = io.StringIO()
            writer = csv.writer(out)
            writer.writerow([
                "Team Name", "Score", "Match Tag", "Open Slots", "Members Count",
                "Max Limit", "Join Mode", "Asian Count", "International Count",
                "Unclassified Count", "International Members", "Asian Members",
                "All Member Details", "Project Idea", "URL"
            ])
            for t in CACHED_RESULTS:
                asian_str = "; ".join([f"{m['name']} ({m['reason']})" for m in t['members'] if m['group'] == "Asian"])
                intl_str = "; ".join([f"{m['name']} ({m['reason']})" for m in t['members'] if m['group'] == "International"])
                all_str = "; ".join([f"{m['name']} [{m['group']} - {m['reason']}]" for m in t['members']])
                writer.writerow([
                    t["name"], t["score"], t["matchTag"], t["openSlots"], t["memberCount"],
                    t["limit"], t["joinMode"], t["asianCount"], t["intlCount"],
                    t["unclassCount"], intl_str, asian_str, all_str,
                    t["description"], t["url"]
                ])
            self.wfile.write(out.getvalue().encode("utf-8"))

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        data = json.loads(body) if body else {}

        if self.path == "/api/load-snapshot":
            filename = data.get("filename")
            teams, meta = load_snapshot(filename)
            global CACHED_RESULTS, CURRENT_EVENT_NAME
            CACHED_RESULTS = teams
            CURRENT_EVENT_NAME = meta.get("eventName", "Lablab Teams")
            csv_file = meta.get("csvFile") or os.path.basename(filename).replace(".json", ".csv")

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"teams": teams, "meta": meta, "csvFile": csv_file}).encode("utf-8"))

        elif self.path == "/api/analyze":
            event_id = data.get("eventId")
            event_slug = data.get("eventSlug")
            event_name = data.get("eventName", event_slug)
            min_members = int(data.get("minMembers", 1))
            limit = int(data.get("limit", 90))
            registered_participants = int(data.get("registeredParticipants", 0))

            print(f"[*] Web Request: Crawling {event_slug} (limit {limit}, min {min_members})...")
            results = analyze_teams_api(event_id, event_slug, event_name, min_members=min_members, limit=limit, registered_participants=registered_participants)

            try:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(results).encode("utf-8"))
            except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
                print(f"[*] Note: Browser tab disconnected before receiving response for {event_slug}. Snapshot was safely saved.")

        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        return


class QuietThreadingHTTPServer(ThreadingHTTPServer):
    """Suppresses noisy Windows socket abort tracebacks when a browser tab closes or refreshes."""
    def handle_error(self, request, client_address):
        exc_type, _, _ = sys.exc_info()
        if exc_type in (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            return
        super().handle_error(request, client_address)


def run_server(port=5000):
    server_address = ("127.0.0.1", port)
    try:
        httpd = QuietThreadingHTTPServer(server_address, AppRequestHandler)
    except OSError:
        port = 5001
        server_address = ("127.0.0.1", port)
        httpd = QuietThreadingHTTPServer(server_address, AppRequestHandler)

    url = f"http://127.0.0.1:{port}"
    print("==================================================================")
    print(f"   🚀 LABLAB TEAM FINDER WEB APP RUNNING")
    print(f"   👉 URL: {url}")
    print("==================================================================")
    print("[*] Opening Web UI in your default browser...")
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
        httpd.server_close()


if __name__ == "__main__":
    run_server()
