import requests
import json
import os
import re
from datetime import datetime
from collections import defaultdict

def fetch_m3u(url):
    """Fetch content from URL"""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Error fetching M3U: {e}")
        return None

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

def parse_m3u(content):
    """Parse content and extract channel info"""
    channels = []
    lines = content.strip().split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if line.startswith('#EXTINF:'):
            # Extract channel info
            channel_info = {}
            
            # Extract tvg-id
            tvg_id_match = re.search(r'tvg-id="([^"]*)"', line)
            if tvg_id_match:
                channel_info['tvg_id'] = tvg_id_match.group(1)
            
            # Extract tvg-name
            tvg_name_match = re.search(r'tvg-name="([^"]*)"', line)
            if tvg_name_match:
                channel_info['tvg_name'] = tvg_name_match.group(1)
            
            # Extract tvg-logo
            tvg_logo_match = re.search(r'tvg-logo="([^"]*)"', line)
            if tvg_logo_match:
                channel_info['tvg_logo'] = tvg_logo_match.group(1)
            
            # Extract group-title (if exists)
            group_match = re.search(r'group-title="([^"]*)"', line)
            if group_match and group_match.group(1).strip():
                channel_info['group_title'] = group_match.group(1).strip()
            
            # Extract channel name (after last comma)
            name_match = re.search(r',(.+)$', line)
            if name_match:
                channel_name = name_match.group(1).strip()
                channel_info['name'] = channel_name
                
                # If no group-title, detect category from name
                if 'group_title' not in channel_info:
                    channel_info['group_title'] = detect_category(channel_name)
            
            # Get URL from next line
            if i + 1 < len(lines):
                url_line = lines[i + 1].strip()
                if url_line and not url_line.startswith('#'):
                    channel_info['url'] = url_line
                    channels.append(channel_info)
                    i += 1
        
        i += 1
    
    return channels

def create_m3u(channels):
    """Create M3U playlist content with categories"""
    # Header
    m3u_content = '''#EXTM3U x-tvg-url="https://www.tsepg.cf/epg.xml.gz"
# ===============================
#  StreamFlex™ Official Playlist
#  AU • Secure • Private
#  Join: https://t.me/streamflex19
# ===============================

'''
    
    # Group channels by category
    categories = defaultdict(list)
    for channel in channels:
        category = channel.get('group_title', 'Entertainment')
        categories[category].append(channel)
    
    # Define category order
    category_order = ['Entertainment', 'Movies', 'Sports', 'Kids', 'Regional', 'News', 'Music']
    
    # Add categories in order, then remaining ones alphabetically
    sorted_categories = [cat for cat in category_order if cat in categories]
    remaining = sorted([cat for cat in categories.keys() if cat not in category_order])
    sorted_categories.extend(remaining)
    
    # Add channels category by category
    for category in sorted_categories:
        # Add category separator
        m3u_content += f'# ========== {category} ==========\n'
        
        for channel in categories[category]:
            # Build EXTINF line
            extinf = "#EXTINF:-1"
            
            if 'tvg_id' in channel:
                extinf += f' tvg-id="{channel["tvg_id"]}"'
            if 'tvg_name' in channel:
                extinf += f' tvg-name="{channel["tvg_name"]}"'
            if 'tvg_logo' in channel:
                extinf += f' tvg-logo="{channel["tvg_logo"]}"'
            if 'group_title' in channel:
                extinf += f' group-title="{channel["group_title"]}"'
            
            extinf += f',{channel.get("name", "Unknown")}\n'
            
            m3u_content += extinf
            m3u_content += f'{channel.get("url", "")}\n\n'
        
        # Add spacing between categories
        m3u_content += '\n'
    
    # Footer 
    m3u_content += '''# =====================================
# Generated by StreamFlex
# Thank you
# =====================================
'''
    
    return m3u_content

def create_json(channels):
    """Create JSON with channel info organized by categories"""
    # Group channels by category
    categories = defaultdict(list)
    for channel in channels:
        category = channel.get('group_title', 'Entertainment')
        categories[category].append({
            "name": channel.get("name", "Unknown"),
            "tvg_id": channel.get("tvg_id", ""),
            "tvg_name": channel.get("tvg_name", ""),
            "logo": channel.get("tvg_logo", ""),
            "group": category,
            "url": channel.get("url", "")
        })
    
    # Create final JSON structure
    json_data = {
        "StreamFlex_A_updated_at": datetime.utcnow().isoformat() + "Z",
        "StreamFlex_SL_total_channels": len(channels),
        "total_categories": len(categories),
        "categories": {}
    }
    
    # Add categories with their channels
    for category in sorted(categories.keys()):
        json_data["categories"][category] = {
            "count": len(categories[category]),
            "channels": categories[category]
        }
    
    # Also add flat channel list for backward compatibility
    json_data["all_channels"] = []
    for channel in channels:
        category = channel.get("group_title", "Entertainment")
        json_data["all_channels"].append({
            "name": channel.get("name", "Unknown"),
            "tvg_id": channel.get("tvg_id", ""),
            "tvg_name": channel.get("tvg_name", ""),
            "logo": channel.get("tvg_logo", ""),
            "group": category,
            "url": channel.get("url", "")
        })
    
    return json.dumps(json_data, indent=2, ensure_ascii=False)

def main():
    # Get source from environment variable (GitHub Secret)
    api_key = os.environ.get('API_KEY')
    
    if not api_key:
        print("ERROR: API_KEY environment variable not set!")
        return
    
    print(f"Fetching playlist...")
    
    # Using Api
    m3u_content = fetch_m3u(api_key)
    
    if not m3u_content:
        print("Failed to fetch M3U content")
        return
    
    print(f"Parsing {len(m3u_content)} characters...")
    
    # Sl Api By StreamFlex 
    channels = parse_m3u(m3u_content)
    
    # Count categories
    categories = defaultdict(int)
    for ch in channels:
        category = ch.get('group_title', 'Entertainment')
        categories[category] += 1
    
    print(f"Found {len(channels)} channels in {len(categories)} categories")
    for cat, count in sorted(categories.items()):
        print(f"  - {cat}: {count} channels")
    
    # Create new M3U file
    new_m3u = create_m3u(channels)
    with open('SL.m3u', 'w', encoding='utf-8') as f:
        f.write(new_m3u)
    
    print("\n✓ SL.m3u created (with auto-detected categories)")
    
    # Create JSON file
    json_content = create_json(channels)
    with open('sl.json', 'w', encoding='utf-8') as f:
        f.write(json_content)
    
    print("✓ sl.json created (with category structure)")
    print(f"\nSuccessfully processed {len(channels)} channels!")

if __name__ == "__main__":
    main()
