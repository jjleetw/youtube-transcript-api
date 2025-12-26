from flask import Flask, request, jsonify
import youtube_transcript_api # 修改導入方式以確保模組路徑正確
from youtube_transcript_api import YouTubeTranscriptApi
import re
import traceback

app = Flask(__name__)

def extract_video_id(url):
    """Extract YouTube video ID from URL"""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

@app.route('/transcript', methods=['POST'])
def get_transcript():
    """Get YouTube transcript"""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        url = data.get('url')
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        video_id = extract_video_id(url)
        if not video_id:
            # 如果傳入的已經是 ID 而非 URL，直接使用
            video_id = url if len(url) == 11 else None
            
        if not video_id:
            return jsonify({'error': 'Invalid YouTube URL or ID'}), 400
        
        # --- 修改重點 1: 使用靜態方法並支援多國語言 ---
        # 優先順序：繁體中文 (zh-Hant) > 簡體 (zh-Hans) > 英文 (en)
        transcript_list = YouTubeTranscriptApi.get_transcript(
            video_id, 
            languages=['zh-Hant', 'zh-Hans', 'zh', 'en']
        )
        
        # --- 修改重點 2: 轉換為 n8n 易讀的純文本格式 ---
        # 原本回傳的是包含時間軸的 List，n8n 通常需要長字串來寫入 Google Docs
        full_text = " ".join([t['text'] for t in transcript_list])
        
        return jsonify({
            'success': True,
            'video_id': video_id,
            'transcript_text': full_text,  # 回傳純文字
            'raw_transcript': transcript_list # 同時保留原始資料供進階使用
        })

    except Exception as e:
        error_msg = str(e)
        # 針對常見錯誤提供更友善的訊息
        if "Subtitles are disabled" in error_msg:
            return jsonify({'error': '此影片已關閉字幕功能'}), 404
        elif "No transcript found" in error_msg:
            return jsonify({'error': '找不到符合語言要求的字幕'}), 404
            
        print(f"Error: {error_msg}")
        print(traceback.format_exc())
        return jsonify({'error': error_msg}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    # 在 Zeabur 部署時，確保 Port 與環境變數一致
    app.run(host='0.0.0.0', port=8080, debug=True)
