from flask import Flask, request, jsonify
import re
# 核心修正：僅導入模組，避免類別與變數名稱衝突
import youtube_transcript_api
from youtube_transcript_api import YouTubeTranscriptApi

app = Flask(__name__)

def extract_video_id(url):
    """提取 YouTube 影片 ID"""
    if not url: return None
    patterns = [r'(?:v=|be/|embed/|shorts/)([^&\n?#]+)']
    for p in patterns:
        m = re.search(p, url)
        if m: return m.group(1)
    return url if len(url) == 11 else None

@app.route('/', methods=['GET'])
def home():
    """驗證路由：解決日誌中的 GET / 404 錯誤"""
    return jsonify({
        'status': 'Online',
        'message': 'YouTube Transcript API 運行中 (官方規範版)',
        'note': '請發送 POST 請求至 /transcript'
    })

@app.route('/transcript', methods=['POST'])
def get_transcript():
    try:
        data = request.json
        if not data or 'url' not in data:
            return jsonify({'success': False, 'error': 'Missing URL'}), 200
            
        video_id = extract_video_id(data['url'])
        if not video_id:
            return jsonify({'success': False, 'error': 'Invalid Video ID'}), 200

        transcript_list = None
        
        # --- 根據官方文件 (GitHub) 的標準調用流程 ---
        try:
            # 1. 獲取所有字幕清單 (支援原頻道語系)
            transcript_list_obj = YouTubeTranscriptApi.list_transcripts(video_id)
            
            # 2. 優先抓取手動上傳的原始字幕
            try:
                transcript_list = transcript_list_obj.find_manually_created_transcript().fetch()
            except:
                # 3. 若無手動，則抓取第一個可用的字幕 (通常為自動生成之原語系)
                transcript_list = next(iter(transcript_list_obj)).fetch()
                
        except Exception as e_list:
            # 備援方案：若 list_transcripts 屬性仍報錯，直接使用最基礎的獲取方法
            try:
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            except Exception as e_final:
                return jsonify({
                    'success': False, 
                    'error': f'此影片找不到字幕: {str(e_final)}',
                    'video_id': video_id
                }), 200

        # 將字幕片段串接為長字串，方便 n8n 使用
        full_text = " ".join([t['text'] for t in transcript_list])
        
        return jsonify({
            'success': True,
            'video_id': video_id,
            'transcript_text': full_text
        })

    except Exception as e:
        # 將技術報錯包裝在 JSON 中回傳
        return jsonify({'success': False, 'error': f'系統全域異常: {str(e)}'}), 200

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    # Zeabur 建議使用 8080 Port
    app.run(host='0.0.0.0', port=8080)
