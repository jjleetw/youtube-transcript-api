from flask import Flask, request, jsonify
import re
import traceback
# 核心修正：只導入最外層模組，徹底避開名稱衝突
import youtube_transcript_api

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
    """首頁驗證：看到此訊息代表路由已正確更新"""
    return jsonify({
        'status': 'Online',
        'message': 'API 已採用全路徑防禦模式運行 (v2.1)',
        'mode': 'Original Language'
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

        transcript_list = None
        
        # --- 核心修正：全路徑調用路徑 ---
        # 格式：模組名.類別名.方法名
        try:
            # 優先嘗試：直接抓取影片原語系字幕
            transcript_list = youtube_transcript_api.YouTubeTranscriptApi.get_transcript(video_id)
        except Exception as e1:
            # 備援策略：如果基礎方法失敗，嘗試獲取字幕清單並抓取第一個
            try:
                # 再次確認使用的是全路徑調用
                proxy = youtube_transcript_api.YouTubeTranscriptApi.list_transcripts(video_id)
                transcript_list = next(iter(proxy)).fetch()
            except Exception as e2:
                return jsonify({
                    'success': False, 
                    'error': f'影片確實無字幕軌道: {str(e2)}',
                    'video_id': video_id
                }), 200

        # 將字幕片段串接為長文字
        full_text = " ".join([t['text'] for t in transcript_list])
        
        return jsonify({
            'success': True,
            'video_id': video_id,
            'transcript_text': full_text
        })

    except Exception as e:
        # 將技術報錯包裝在 JSON 中，不再回傳 404
        return jsonify({'success': False, 'error': f'系統全域異常: {str(e)}'}), 200

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    # Zeabur 建議使用 8080 Port
    app.run(host='0.0.0.0', port=8080)
