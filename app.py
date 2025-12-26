from flask import Flask, request, jsonify
import re
import traceback
# 1. 採用最完整且明確的導入，防止 Python 名稱衝突
import youtube_transcript_api
from youtube_transcript_api import YouTubeTranscriptApi

app = Flask(__name__)

def extract_video_id(url):
    """提取 YouTube 影片 ID"""
    if not url: return None
    # 支援 watch?v=, youtu.be, embed, shorts 等格式
    patterns = [r'(?:v=|be/|embed/|shorts/)([^&\n?#]+)']
    for p in patterns:
        m = re.search(p, url)
        if m: return m.group(1)
    return url if len(url) == 11 else None

@app.route('/', methods=['GET'])
def home():
    """首頁測試，確認服務在線 (解決日誌中的 GET / 404 問題)"""
    return jsonify({
        'status': 'Online',
        'message': 'YouTube Transcript API 運行中',
        'mode': 'Original Language'
    })

@app.route('/transcript', methods=['POST'])
def get_transcript():
    try:
        data = request.json
        if not data or 'url' not in data:
            return jsonify({'success': False, 'error': '請提供 url 參數'}), 200
            
        video_id = extract_video_id(data['url'])
        if not video_id:
            return jsonify({'success': False, 'error': '無效的 YouTube 連結或 ID'}), 200

        transcript_list = None
        
        # --- 核心邏輯：使用全路徑調用，徹底解決 "no attribute" 報錯 ---
        try:
            # 優先嘗試：抓取所有字幕清單並找出「原頻道語言」
            transcript_list_obj = youtube_transcript_api.YouTubeTranscriptApi.list_transcripts(video_id)
            
            try:
                # 優先抓取手動上傳字幕 (Manual)
                transcript_list = transcript_list_obj.find_manually_created_transcript().fetch()
            except:
                # 若無，則抓取第一個可用的字幕 (原語系自動生成)
                transcript_list = next(iter(transcript_list_obj)).fetch()
                
        except Exception as e_list:
            # 次要嘗試：若 list_transcripts 失敗，退回基礎方法
            try:
                transcript_list = youtube_transcript_api.YouTubeTranscriptApi.get_transcript(video_id)
            except Exception as e_final:
                return jsonify({
                    'success': False, 
                    'error': f'此影片確實找不到字幕: {str(e_final)}',
                    'video_id': video_id
                }), 200

        # 串接為純文字內容
        full_text = " ".join([t['text'] for t in transcript_list])
        
        return jsonify({
            'success': True,
            'video_id': video_id,
            'transcript_text': full_text,
            'length': len(full_text)
        })

    except Exception as e:
        # 將技術報錯包裝在 JSON 中，不再回傳 404
        return jsonify({'success': False, 'error': f'程式執行報錯: {str(e)}'}), 200

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    # Zeabur 建議使用 8080 Port
    app.run(host='0.0.0.0', port=8080, debug=False)
