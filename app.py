from flask import Flask, request, jsonify
import re
import os
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
import requests

app = Flask(__name__)

# 免費代理列表（定期更新）
FREE_PROXIES = [
    'http://proxy.example.com:8080',  # 佔位符
    # 以下是一些常見的免費代理格式
    # 實際使用時需要從代理列表網站獲取最新的可用代理
]

# 從環境變數取得代理列表（可選）
PROXY_LIST_URL = os.getenv('PROXY_LIST_URL', '')

def extract_video_id(url):
    """提取 YouTube 影片 ID"""
    if not url: 
        return None
    patterns = [r'(?:v=|be/|embed/|shorts/)([^&\n?#]+)']
    for p in patterns:
        m = re.search(p, url)
        if m: 
            return m.group(1)
    return url if len(url) == 11 else None

def get_free_proxies():
    """從免費代理網站獲取最新的代理列表"""
    try:
        # 使用 free-proxy-list.net 的代理
        response = requests.get('https://www.proxy-list.download/api/v1/get?type=http', timeout=5)
        if response.status_code == 200:
            data = response.json()
            proxies = data.get('LISTA', [])
            return [f'http://{proxy}' for proxy in proxies[:10]]  # 取前 10 個
    except Exception as e:
        print(f"無法從代理列表網站獲取代理: {e}")
    
    # 備援：使用硬編碼的代理列表
    return [
        'http://103.145.45.97:55443',
        'http://103.152.100.155:8080',
        'http://103.159.46.15:8080',
        'http://103.168.36.28:8080',
        'http://103.169.186.28:3128',
        'http://103.175.46.12:8080',
        'http://103.179.253.5:8080',
        'http://103.180.113.90:8080',
        'http://103.183.60.110:8080',
        'http://103.197.251.202:80',
    ]

@app.route('/', methods=['GET'])
def home():
    """首頁驗證"""
    return jsonify({
        'status': 'Online',
        'message': 'YouTube Transcript API (使用免費代理) 已正確運行',
        'mode': 'Original Language',
        'proxy_method': 'Free Proxy List'
    })

@app.route('/transcript', methods=['POST'])
def get_transcript():
    """獲取原頻道語言逐字稿"""
    try:
        data = request.json
        if not data or 'url' not in data:
            return jsonify({'success': False, 'error': '請提供 url 參數'}), 200
            
        video_id = extract_video_id(data['url'])
        if not video_id:
            return jsonify({'success': False, 'error': '無效的影片連結'}), 200

        # 獲取可用的代理列表
        proxies_list = get_free_proxies()
        
        if not proxies_list:
            return jsonify({
                'success': False, 
                'error': '無法獲取代理列表',
                'video_id': video_id
            }), 200

        transcript_list = None
        last_error = None

        # 嘗試使用不同的代理
        for proxy_url in proxies_list:
            try:
                proxy_dict = {
                    'http': proxy_url,
                    'https': proxy_url
                }
                
                api = YouTubeTranscriptApi()
                transcript_list = api.fetch(
                    video_id, 
                    languages=['en', 'zh-TW', 'zh-CN', 'ja', 'ko'],
                    proxies=proxy_dict
                )
                
                # 成功則跳出迴圈
                print(f"成功使用代理: {proxy_url}")
                break
                
            except (TranscriptsDisabled, NoTranscriptFound) as e:
                # 影片無字幕，不需要繼續嘗試其他代理
                return jsonify({
                    'success': False, 
                    'error': '影片確實無字幕軌道',
                    'video_id': video_id
                }), 200
            except Exception as e:
                # 代理失敗，記錄錯誤並嘗試下一個
                last_error = str(e)
                print(f"代理 {proxy_url} 失敗: {e}")
                continue

        if transcript_list is None:
            error_msg = last_error or '所有代理都失敗了'
            return jsonify({
                'success': False, 
                'error': f'無法獲取字幕: {error_msg}',
                'video_id': video_id,
                'hint': '免費代理可能不穩定，建議使用付費代理或 yt-dlp'
            }), 200

        # 將字幕片段串接為長文字
        full_text = " ".join([t['text'] for t in transcript_list])
        
        return jsonify({
            'success': True,
            'video_id': video_id,
            'transcript': full_text,
            'count': len(transcript_list)
        }), 200

    except Exception as e:
        return jsonify({
            'success': False, 
            'error': f'伺服器錯誤: {str(e)}'
        }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
