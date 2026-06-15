import sys
import os
import requests
import json

def test_lyrics_endpoints():
    base_url = "http://127.0.0.1:5100"
    
    # 1. Test Config Endpoint
    config_url = f"{base_url}/api/lyrics-config"
    print(f"Testing GET {config_url}...")
    try:
        res = requests.get(config_url, timeout=5)
        if res.status_code == 200:
            print("[OK] Successfully fetched lyrics config.")
            print(json.dumps(res.json(), indent=2, ensure_ascii=False)[:300] + "...\n")
        else:
            print(f"[FAIL] GET /api/lyrics-config: {res.status_code}\n")
            return
    except Exception as e:
        print(f"[FAIL] Error connecting: {e}\n")
        return

    # 2. Test Preview Lyrics Endpoint (Bilingual)
    preview_url = f"{base_url}/api/preview-lyrics"
    payload = {
        "title": "奇异恩典 (Amazing Grace)",
        "lyrics": (
            "[Verse 1]\n"
            "Amazing grace! how sweet the sound\n"
            "奇异恩典 何等甘甜\n"
            "That saved a wretch like me!\n"
            "我罪已得赦免\n"
            "I once was lost, but now am found\n"
            "前我失丧 今被寻回\n"
            "Was blind, but now I see.\n"
            "瞎眼今得看见\n"
            "\n"
            "[Chorus]\n"
            "Amazing grace! how sweet the sound\n"
            "奇异恩典 何等甘甜"
        ),
        "lines_per_slide": 2,
        "theme": "deep_blue",
        "language_mode": "bilingual",
        "chinese_script_mode": "original",
        "extended_single_lines": False,
        "language_config": {
            "primary": "zh",
            "secondary": "en"
        },
        "add_title_slide": True,
        "add_amen_slide": True
    }
    
    print(f"Testing POST {preview_url}...")
    try:
        res = requests.post(preview_url, json=payload, timeout=10)
        if res.status_code == 200:
            print("[OK] Successfully generated lyrics preview.")
            res_data = res.json()
            print(f"Total Pages: {res_data.get('total_pages')}")
            print(f"Detected Structure: {json.dumps(res_data.get('detected_structure'), ensure_ascii=False)}")
            print("Slides Breakdown:")
            for slide in res_data.get("slides", []):
                print(f"  Page {slide.get('page')} ({slide.get('type')}): {slide.get('lines')}")
            print()
        else:
            print(f"[FAIL] POST /api/preview-lyrics: {res.status_code}")
            try:
                print(res.json())
            except Exception:
                print(res.text)
            print()
            return
    except Exception as e:
        print(f"[FAIL] Error connecting: {e}\n")
        return

    # 3. Test Generate Lyrics PPTX Endpoint
    gen_url = f"{base_url}/api/generate-lyrics-pptx"
    print(f"Testing POST {gen_url}...")
    try:
        res = requests.post(gen_url, json=payload, timeout=10)
        if res.status_code == 200:
            filename = "test_lyrics_output.pptx"
            with open(filename, "wb") as f:
                f.write(res.content)
            print(f"[OK] Successfully generated {filename}")
            print(f"File size: {os.path.getsize(filename)} bytes")
        else:
            print(f"[FAIL] POST /api/generate-lyrics-pptx: {res.status_code}")
            try:
                print(res.json())
            except Exception:
                print(res.text)
    except Exception as e:
        print(f"[FAIL] Error connecting: {e}")

if __name__ == "__main__":
    test_lyrics_endpoints()
