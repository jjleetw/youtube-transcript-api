from flask import Flask, request, jsonify
import re
# 核心修正 1：只導入整個模組，避免與類別名稱產生衝突
import youtube_transcript_api

app = Flask(__name__)

def extract_video_id(url):
    """提取影片 ID"""
    if not url: return None
    patterns = [r'(?:v=|be/|embed/|shorts/)([^&\n?#]+)']
    for p in patterns:
        m = re.search(p, url)
        if m: return m.group(1)
    return url if len(url) == 11 else None

@app.route('/', methods=['GET'])
def home():
    """首頁驗證：若看到此訊息，代表 API 部署成功且路由已更新"""
    return jsonify({
        'status': 'Online',
        'message': 'API 已採用全路徑防禦模式運行',
        'mode': 'Original Language'
    })

@app.route('/transcript', methods=['POST'])
def get_transcript():
    """獲取原頻道語言逐字稿"""
    try:
        data = request.json
        if not data or 'url' not in data:
            return jsonify({'success': False, 'error': '未提供 URL'}), 200
            
        video_id = extract_video_id(data['url'])
        if not video_id:
            return jsonify({'success': False, 'error': '無效的連結'}), 200

        transcript_list = None
        
        # 核心修正 2：採用全路徑調用 (模組名.類別名.方法名)
        try:
            # 優先嘗試：直接抓取影片原語系字幕 (不帶語言參數則自動鎖定原頻道)
            transcript_list = youtube_transcript_api.YouTubeTranscriptApi.get_transcript(video_id)
        except Exception as e1:
            # 備援策略：如果基礎方法失敗，嘗試獲取字幕清單
            try:
                proxy = youtube_transcript_api.YouTubeTranscriptApi.list_transcripts(video_id)
                transcript_list = next(iter(proxy)).fetch()
            except Exception as e2:
                return jsonify({
                    'success': False, 
                    'error': f'此影片確實找不到任何字幕: {str(e2)}',
                    'video_id': video_id
                }), 200

        # 串接逐字稿文字
        full_text = " ".join([t['text'] for t in transcript_list])
        
        return jsonify({
            'success': True,
            'video_id': video_id,
            'transcript_text': full_text
        })

    except Exception as e:
        # 將技術錯誤包裝在 JSON 中回傳
        return jsonify({'success': False, 'error': f'系統執行報錯: {str(e)}'}), 200

if __name__ == '__main__':
    # Zeabur 部署必須使用 8080 Port
    app.run(host='0.0.0.0', port=8080)
