import streamlit as st
from googleapiclient.discovery import build
import pandas as pd
import re
from deep_translator import GoogleTranslator

# 1. 유튜브 영상 ID 추출 함수
def extract_video_id(url):
    regex = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    match = re.search(regex, url)
    if match:
        return match.group(1)
    return None

# 2. 유튜브 댓글 수집 및 번역 함수
def get_youtube_comments(video_id, api_key, max_comments, translate_to_ko=False):
    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        comments_data = []
        
        fetch_limit = min(100, max_comments)
        
        request = youtube.commentThreads().list(
            part='snippet',
            videoId=video_id,
            maxResults=fetch_limit,
            textFormat='plainText'
        )
        
        progress_text = st.empty()
        
        while request and len(comments_data) < max_comments:
            response = request.execute()
            
            for item in response['items']:
                if len(comments_data) >= max_comments:
                    break
                    
                snippet = item['snippet']['topLevelComment']['snippet']
                original_text = snippet['textDisplay']
                
                # 데이터 기본 구조 생성
                comment_entry = {
                    '작성자': snippet['authorDisplayName'],
                    '원문 댓글': original_text,
                    '좋아요수': snippet['likeCount'],
                    '작성일': snippet['publishedAt']
                }
                
                comments_data.append(comment_entry)
            
            progress_text.text(f"⏳ 현재 {len(comments_data)}개 수집 완료...")
            
            if len(comments_data) < max_comments:
                request = youtube.commentThreads().list_next(request, response)
            else:
                break
                
        # --- 번역 기능 처리 ---
        if translate_to_ko and comments_data:
            progress_text.text("🔤 수집된 댓글을 한글로 번역하는 중입니다...")
            
            # 구글 번역기 설정 (자동 감지 -> 한국어)
            translator = GoogleTranslator(source='auto', target='ko')
            
            # 하나씩 번역 적용
            for idx, entry in enumerate(comments_data):
                progress_text.text(f"🔤 번역 진행 중... ({idx+1}/{len(comments_data)}개)")
                try:
                    # 빈 댓글이나 특수문자만 있는 경우 예외 처리
                    if entry['원문 댓글'].strip():
                        entry['한글 번역'] = translator.translate(entry['원문 댓글'])
                    else:
                        entry['한글 번역'] = entry['원문 댓글']
                except Exception:
                    # 번역 실패 시 원문 그대로 유지
                    entry['한글 번역'] = entry['원문 댓글']
                    
        progress_text.empty() 
        return pd.DataFrame(comments_data)
        
    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")
        return None

# --- Streamlit UI 구성 ---
st.set_page_config(page_title="유튜브 댓글 수집 & 번역기", layout="centered")

st.title("📊 유튜브 댓글 추출 & 번역 프로그램")
st.write("유튜브 영상 링크와 원하는 옵션을 선택해 주세요.")

if "YOUTUBE_API_KEY" in st.secrets:
    API_KEY = st.secrets["YOUTUBE_API_KEY"]
else:
    st.info("💡 배포 후 Streamlit Secrets에 'YOUTUBE_API_KEY'를 설정해주세요.")
    API_KEY = st.text_input("YouTube API Key를 입력하세요:", type="password")

video_url = st.text_input("유튜브 동영상 URL을 입력하세요:", placeholder="https://www.youtube.com/watch?v=...")

max_comments_input = st.slider(
    "수집할 최대 댓글 개수를 선택하세요:", 
    min_value=50, 
    max_value=1000, 
    value=500, 
    step=50
)

# --- [추가된 기능] 한글 번역 체크박스 ---
translate_option = st.checkbox("🔄 외국어 댓글 한글로 자동 번역하기", value=False)

if st.button("댓글 수집 시작"):
    if not API_KEY:
        st.warning("API Key가 필요합니다.")
    elif not video_url:
        st.warning("유튜브 URL을 입력해주세요.")
    else:
        video_id = extract_video_id(video_url)
        if not video_id:
            st.error("유효한 유튜브 URL이 아닙니다. 영상 ID를 찾을 수 없습니다.")
        else:
            with st.spinner("작업을 진행하고 있습니다..."):
                df = get_youtube_comments(video_id, API_KEY, max_comments_input, translate_option)
                
                if df is not None and not df.empty:
                    st.success(f"성공! 총 {len(df)}개의 댓글을 처리했습니다.")
                    
                    # 번역을 선택했다면 열 순서를 '작성자', '원문 댓글', '한글 번역' 순으로 보기 좋게 정렬
                    if translate_option and '한글 번역' in df.columns:
                        cols = ['작성자', '원문 댓글', '한글 번역', '좋아요수', '작성일']
                        df = df[cols]
                    
                    st.dataframe(df.head())
                    
                    csv = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
                    st.download_button(
                        label="엑셀(CSV) 파일로 다운로드",
                        data=csv,
                        file_name=f"youtube_comments_{video_id}.csv",
                        mime="text/csv"
                    )
                elif df is not None and df.empty:
                    st.warning("이 영상에는 댓글이 없거나, 댓글 기능이 비활성화되어 있습니다.")
