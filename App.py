import streamlit as st
from googleapiclient.discovery import build
import pandas as pd
import re

# 1. 유튜브 영상 ID 추출 함수
def extract_video_id(url):
    regex = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    match = re.search(regex, url)
    if match:
        return match.group(1)
    return None

# 2. 유튜브 댓글 수집 함수 (최대 개수 제한 추가)
def get_youtube_comments(video_id, api_key, max_comments):
    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        comments_data = []
        
        # YouTube API는 한 번 요청할 때 최대 100개씩 가져올 수 있습니다.
        fetch_limit = min(100, max_comments)
        
        request = youtube.commentThreads().list(
            part='snippet',
            videoId=video_id,
            maxResults=fetch_limit,
            textFormat='plainText'
        )
        
        # 진행 상황을 보여주기 위한 상태 바
        progress_text = st.empty()
        
        while request and len(comments_data) < max_comments:
            response = request.execute()
            
            for item in response['items']:
                if len(comments_data) >= max_comments:
                    break
                    
                snippet = item['snippet']['topLevelComment']['snippet']
                comments_data.append({
                    '작성자': snippet['authorDisplayName'],
                    '댓글': snippet['textDisplay'],
                    '좋아요수': snippet['likeCount'],
                    '작성일': snippet['publishedAt']
                })
            
            # 현재까지 수집된 개수를 화면에 실시간 표시
            progress_text.text(f"⏳ 현재 {len(comments_data)}개 수집 완료...")
            
            if len(comments_data) < max_comments:
                request = youtube.commentThreads().list_next(request, response)
            else:
                break
                
        progress_text.empty() 
        return pd.DataFrame(comments_data)
        
    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")
        return None

# --- Streamlit UI 구성 ---
st.set_page_config(page_title="유튜브 댓글 수집기", layout="centered")

st.title("📊 유튜브 댓글 추출 프로그램")
st.write("유튜브 영상 링크와 원하는 댓글 개수를 선택해 주세요.")

# Streamlit의 Secrets 시스템에서 API Key 로드
if "YOUTUBE_API_KEY" in st.secrets:
    API_KEY = st.secrets["YOUTUBE_API_KEY"]
else:
    st.info("💡 배포 후 Streamlit Secrets에 'YOUTUBE_API_KEY'를 설정해주세요.")
    API_KEY = st.text_input("YouTube API Key를 입력하세요:", type="password")

# URL 입력창
video_url = st.text_input("유튜브 동영상 URL을 입력하세요:", placeholder="https://www.youtube.com/watch?v=...")

# --- 댓글 개수 선택 슬라이더 (최대 1000개 제한) ---
max_comments_input = st.slider(
    "수집할 최대 댓글 개수를 선택하세요:", 
    min_value=50, 
    max_value=1000, 
    value=500, 
    step=50
)

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
            with st.spinner("댓글을 수집하는 중입니다..."):
                df = get_youtube_comments(video_id, API_KEY, max_comments_input)
                
                if df is not None and not df.empty:
                    st.success(f"성공! 총 {len(df)}개의 댓글을 수집했습니다.")
                    st.dataframe(df.head())
                    
                    # CSV 다운로드 버튼
                    csv = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
                    st.download_button(
                        label="엑셀(CSV) 파일로 다운로드",
                        data=csv,
                        file_name=f"youtube_comments_{video_id}.csv",
                        mime="text/csv"
                    )
                elif df is not None and df.empty:
                    st.warning("이 영상에는 댓글이 없거나, 댓글 기능이 비활성화되어 있습니다.")
