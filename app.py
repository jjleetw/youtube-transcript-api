from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi
import re
import traceback

app = Flask(__name__)

def extract_video_id(url):
    """提取 YouTube 影片 ID"""
    if not url: return None
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|shorts\/)([^&\n?#]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    # 若傳入的是 11 位字元，視為 ID
    return url if len(url) == 11 else None

@app.route('/', methods=['GET'])
def home():
    """首頁測試路由，用來確認服務部署成功 (解決日誌中的 GET / 404)"""
    return jsonify({
        'status': 'Online',
        'message': 'YouTube Transcript API 已經成功啟動',
        'version': '2.0 - Original Language Mode'
    })

@app.route('/transcript', methods=['POST'])
def get_transcript():
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 200
            
        url = data.get('url')
        if not url:
            return jsonify({'success': False, 'error': 'URL is required'}), 200
        
        video_id = extract_video_id(url)
        if not video_id:
            return jsonify({'success': False, 'error': 'Invalid YouTube URL or ID'}), 200
        
        # --- 核心邏輯：以原頻道語言為主 ---
        transcript_list = None
        
        try:
            # 策略 1：使用 list_transcripts 尋找原始語言 (最精準)
            # 使用 getattr 避開某些環境下導致的 "has no attribute" 報錯
            if hasattr(YouTubeTranscriptApi, 'list_transcripts'):
                transcript_metadata = YouTubeTranscriptApi.list_transcripts(video_id)
                # find_manually_created_transcript 會抓取原創者上傳的語言
                try:
                    transcript_list = transcript_metadata.find_manually_created_transcript().fetch()
                except:
                    # 若無手動字幕，抓取第一個可用的（通常是原語系自動生成）
                    transcript_list = next(iter(transcript_metadata)).fetch()
            
            # 策略 2：若上述方法失敗，使用基礎 get_transcript (最相容)
            if not transcript_list:
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
                
        except Exception as transcript_err:
            return jsonify({
                'success': False, 
                'error': f'找不到任何字幕: {str(transcript_err)}',
                'video_id': video_id
            }), 200
        
        # 轉換為純文本，方便 n8n 直接使用
        full_text = " ".join([t['text'] for t in transcript_list])
        
        return jsonify({
            'success': True,
            'video_id': video_id,
            'transcript_text': full_text,
            'raw_count': len(transcript_list)
        })

    except Exception as e:
        # 統一回傳 200 伴隨 success: false，方便 n8n 判斷內容而非直接斷線
        return jsonify({'success': False, 'error': str(e)}), 200

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    # Zeabur 部署必須使用 8080 端口
    app.run(host='0.0.0.0', port=8080, debug=False)
