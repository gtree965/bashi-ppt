import sys
import os

# Add backend to path so we can import directly to test without running a full server if we want,
# but testing against a running server is better.
import requests
import json

def test_generate_pptx():
    url = "http://127.0.0.1:5000/api/generate-pptx"
    
    payload = {
        "template_id": "teaching",
        "outline": {
            "title": "测试生成PPT",
            "slides": [
                {
                    "page_number": 1,
                    "title": "欢迎使用 SlideForge",
                    "content_points": ["本地AI驱动的演示文稿生成器", "零外部依赖，保护隐私"],
                    "slide_type": "title"
                },
                {
                    "page_number": 2,
                    "title": "核心特性",
                    "content_points": [
                        "支持多种精美模板", 
                        "基于先进大语言模型结构化生成", 
                        "智能长文本溢出处理（自动缩小字体和调整间距）",
                        "这是第五个很长很长的句子用来测试字体的溢出截断表现"
                    ],
                    "slide_type": "content"
                },
                {
                    "page_number": 3,
                    "title": "感谢观看",
                    "content_points": ["期待您的反馈", "开启本地AI创作之旅"],
                    "slide_type": "conclusion"
                }
            ]
        }
    }
    
    print(f"Sending request to {url}...")
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            with open("test_output.pptx", "wb") as f:
                f.write(response.content)
            print("[OK] Successfully generated test_output.pptx")
            print(f"File size: {os.path.getsize('test_output.pptx')} bytes")
        else:
            print(f"[FAIL] Failed to generate PPTX: {response.status_code}")
            try:
                print(response.json())
            except Exception:
                print(response.text)
    except Exception as e:
        print(f"[FAIL] Error connecting to server: {e}")
        print("[TIP] Make sure the Flask server is running on port 5000.")

if __name__ == "__main__":
    test_generate_pptx()
