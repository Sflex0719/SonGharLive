import requests
import json
import os
import re
from datetime import datetime
from collections import defaultdict

# ==============================
# FETCH THROUGH API (FROM SECRET)
# ==============================
def fetch_m3u(url):
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Error fetching M3U: {e}")
        return None

# ==============================
# SONY CHANNEL FILTER
# ==============================
def is_sony_channel(channel_name):
    name_lower = channel_name.lower()
    sony_keywords = [
        "sony", "set", "sab", "pal", "aath",
        "pix", "wah",
        "max", "max1", "max 1", "max 2",
        "ten 1", "ten 2", "ten 3", "ten 4", "ten 5",
        "sony yay"
    ]
    return any(word in name_lower for word in sony_keywords)

# ==============================
# CATEGORY DETECTION (UNCHANGED)
# ==============================
def detect_category(channel_name):
    """Detect category based on channel name"""
    name_lower = channel_name.lower()
    
    # Sports channels
    if any(word in name_lower for word in ['sports', 'ten 1', 'ten 2', 'ten 3', 'ten 4', 'ten 5', 'six']):
        return "Sports"
    
    # Movies channels
    if any(word in name_lower for word in ['max', 'pix', 'wah', 'movie']):
        return "Movies"
    
    # Kids channels
    if any(word in name_lower for word in ['yay', 'kids', 'cartoon']):
        return "Kids"
    
    # Regional channels
    if any(word in name_lower for word in ['marathi', 'aath', 'bengali', 'tamil', 'telugu', 'kannada']):
        return "Regional"
    
    # Entertainment channels (SET, SAB, Pal etc)
    if any(word in name_lower for word in ['set', 'sab', 'pal', 'sony tv', 'entertainment']):
        return "Entertainment"
    
    # News channels
    if any(word in name_lower for word in ['news', 'aaj tak', 'india tv', 'ndtv']):
        return "News"
    
    # Music channels
    if any(word in name_lower for word in ['music', 'mtv', 'vh1', '9xm']):
        return "Music"
    
    # Default
    return "Entertainment"

# ==============================
# PARSE M3U
# ==============================
def parse_m3u(content):
    channels = []
    lines = content.strip().split('\n')
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        if line.startswith('#EXTINF:'):
            channel_info = {}

            tvg_id = re.search(r'tvg-id="([^"]*)"', line)
            tvg_name = re.search(r'tvg-name="([^"]*)"', line)
            tvg_logo = re.search(r'tvg-logo="([^"]*)"', line)
            group = re.search(r'group-title="([^"]*)"', line)
            name_match = re.search(r',(.+)$', line)

            if tvg_id:
                channel_info['tvg_id'] = tvg_id.group(1)
            if tvg_name:
                channel_info['tvg_name'] = tvg_name.group(1)
            if tvg_logo:
                channel_info['tvg_logo'] = tvg_logo.group(1)

            if name_match:
                name = name_match.group(1).strip()
                channel_info['name'] = name
                if group and group.group(1).strip():
                    channel_info['group_title'] = group.group(1).strip()
                else:
                    channel_info['group_title'] = detect_category(name)

            if i + 1 < len(lines):
                url = lines[i + 1].strip()
                if url and not url.startswith('#'):
                    channel_info['url'] = url
                    channels.append(channel_info)
                    i += 1
        i += 1

    return channels

# ==============================
# CREATE M3U
# ==============================
def create_m3u(channels):
    m3u_content = '''#EXTM3U
# ===============================
#  StreamFlex™ Official Playlist
#  AU • Secure • Private
#  Join: https://t.me/streamflex19
# ===============================

'''
    categories = defaultdict(list)
    for ch in channels:
        categories[ch['group_title']].append(ch)

    category_order = ['Entertainment', 'Movies', 'Sports', 'Kids', 'Regional', 'News', 'Music']
    sorted_categories = [c for c in category_order if c in categories]
    sorted_categories += sorted(c for c in categories if c not in category_order)

    for category in sorted_categories:
        m3u_content += f'# ========== {category} ==========\n'
        for ch in categories[category]:
            extinf = "#EXTINF:-1"
            if ch.get("tvg_id"):
                extinf += f' tvg-id="{ch["tvg_id"]}"'
            if ch.get("tvg_name"):
                extinf += f' tvg-name="{ch["tvg_name"]}"'
            if ch.get("tvg_logo"):
                extinf += f' tvg-logo="{ch["tvg_logo"]}"'
            extinf += f' group-title="{category}",{ch["name"]}\n'
            m3u_content += extinf
            m3u_content += ch["url"] + "\n\n"

    return m3u_content

# ==============================
# CREATE JSON
# ==============================
def create_json(channels):
    categories = defaultdict(list)

    for ch in channels:
        categories[ch['group_title']].append({
            "name": ch["name"],
            "tvg_id": ch.get("tvg_id", ""),
            "tvg_name": ch.get("tvg_name", ""),
            "logo": ch.get("tvg_logo", ""),
            "group": ch["group_title"],
            "url": ch["url"]
        })

    data = {
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "total_channels": len(channels),
        "categories": categories,
        "all_channels": [c for cat in categories.values() for c in cat]
    }

    return json.dumps(data, indent=2, ensure_ascii=False)

# ==============================
# MAIN
# ==============================
def main():
    SOURCE_URL = os.environ.get("API_KEY")  # 🔐 SECRET SOURCE

    if not SOURCE_URL:
        print("ERROR: API_KEY secret not set")
        return

    print("Fetching playlist from secret source...")
    m3u_content = fetch_m3u(SOURCE_URL)

    if not m3u_content:
        print("Failed to fetch M3U")
        return

    all_channels = parse_m3u(m3u_content)

    sony_channels = [
        ch for ch in all_channels
        if is_sony_channel(ch.get("name", ""))
    ]

    print(f"✓ Sony channels found: {len(sony_channels)}")

    with open("SL.m3u", "w", encoding="utf-8") as f:
        f.write(create_m3u(sony_channels))

    with open("sl.json", "w", encoding="utf-8") as f:
        f.write(create_json(sony_channels))

    print("✓ SL.m3u & sl.json updated successfully")

if __name__ == "__main__":
    main()
