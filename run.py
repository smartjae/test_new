import streamlit as st
from datetime import datetime
from app_streaming import load_emotion_model
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase
import av
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.python.solutions.drawing_utils import draw_landmarks
from mediapipe.python.solutions.drawing_styles import get_default_face_mesh_styles

# ——— Page config & title ———
st.set_page_config(layout='wide', page_title='ethicapp')
st.title('감정을 읽는 기계')

# EmotionProcessor 정의
class EmotionProcessor(VideoProcessorBase):
    def __init__(self):
        # 모델과 라벨 맵 로드
        label_map, model = load_emotion_model()
        self.label_map = label_map
        self.model = model
        # MediaPipe Face Mesh 초기화
        self.face_mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        # 프레임 -> BGR ndarray
        img = frame.to_ndarray(format="bgr24")
        # FaceMesh 처리 (RGB 변환)
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb)
        # 랜드마크 그리기
        if results.multi_face_landmarks:
            for lm in results.multi_face_landmarks:
                draw_landmarks(
                    image=img,
                    landmark_list=lm,
                    connections=mp.solutions.face_mesh.FACE_CONNECTIONS,
                    landmark_drawing_spec=None,
                    connection_drawing_spec=get_default_face_mesh_styles()[1]
                )
        # 감정 분석: 전처리 (모델 입력 형태 맞추기)
        img_resized = cv2.resize(img, (48, 48))
        gray = cv2.cvtColor(img_resized, cv2.COLOR_BGR2GRAY)
        arr = gray.astype('float32') / 255.0
        arr = np.expand_dims(arr, axis=(0, -1))  # (1,48,48,1)
        preds = self.model.predict(arr)
        pred_id = int(np.argmax(preds, axis=1)[0])
        pred_label = self.label_map[str(pred_id)]
        # 예측 결과 텍스트 오버레이
        cv2.putText(
            img,
            pred_label,
            (10, img.shape[0] - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2
        )
        # VideoFrame으로 반환
        return av.VideoFrame.from_ndarray(img, format="bgr24")


# ——— Sidebar navigation menu ———
st.sidebar.subheader('Menu …')
page = st.sidebar.radio(
    '',
    ['Home', 'Teachable Machine','Emotion Analysis', 'Student Data','Help']
)

# ——— Main layout: two columns (4:1) ———
left_col, right_col = st.columns([4, 1])

if page == 'Home':
    with left_col:
        st.subheader('Content')
        st.video('https://www.youtube.com/watch?v=lkT6qg55kpE') #https://youtu.be/CShXWACuGp8?si=ANvHKLLaTQq6jU00


        # 폰트 크기를 키워서 안내 문구 출력
        st.markdown(
            """
            <p style='font-size:20px; font-weight:bold;'>기계가 감정을 읽을 수 있다고 생각하나요?</p>
            """,
            unsafe_allow_html=True
        )
        thoughts = st.text_area('학생 개인 생각을 기록하세요:', height=150)
        if st.button('제출'):
            if thoughts.strip():
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                entry = f'[{timestamp}] {thoughts}\n'
                with open('data.txt', 'a', encoding='utf-8') as f:
                    f.write(entry)
                st.success('생각이 성공적으로 제출되었습니다!')
            else:
                st.warning('생각을 입력한 후 제출해주세요.')



    with right_col:
        st.subheader('Tips & Help')
        st.markdown(
            '''
- 💡 **Tip 1:** 윤리적 딜레마가 발생할 수 있는 상황을 미리 상상해 보세요.  
- 💡 **Tip 2:** AI가 내린 판단을 그대로 믿기보다, 항상 비판적으로 검토하세요.  
- ❓ **Help:** 문제가 있을 때 사이드바의 ‘문의하기’ 버튼을 눌러주세요.
            '''
        )

elif page == 'Teachable Machine':
    # 외부 Teachable Machine 페이지로 이동
    components.html(
        """
        <script>
            window.open('https://teachablemachine.withgoogle.com/train', '_blank')
        </script>
        """
    )
    st.write('Teachable Machine 페이지로 이동 중입니다...')


elif page == 'Emotion Analysis':
    left_col, right_col = st.columns([2, 1])

    with right_col:
        st.subheader('How to use')
        st.markdown(
            '''
- 웹캠 얼굴에 MediaPipe FaceMesh를 적용하고 실시간 감정을 예측합니다.  
- 브라우저에서 카메라 권한을 허용하세요.  
- Start/Stop 버튼으로 스트리밍을 제어합니다.
            '''
        )

    with left_col:
        # 상태 초기화
        if 'emotion_running' not in st.session_state:
            st.session_state['emotion_running'] = False

        # 시작/중단 버튼
        col1, col2 = st.columns(2)
        with col1:
            if st.button('Start Emotion Analysis'):
                st.session_state['emotion_running'] = True
        with col2:
            if st.button('Stop Emotion Analysis'):
                st.session_state['emotion_running'] = False

        # 스트리밍 및 처리
        if st.session_state['emotion_running']:
            webrtc_streamer(
                key="emotion",
                video_processor_factory=EmotionProcessor,
                async_processing=True,
                media_stream_constraints={"video": True, "audio": False},
                rtc_configuration={
                    "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]
                },
            )
        else:
            st.info("▶️ Emotion Analysis is stopped")

        # 학생 피드백 폼
        st.subheader('학생 피드백 기록')
        student_name = st.text_input('학번')
        incorrect = st.text_area('잘못 인식된 감정', height=100)
        reason = st.text_area('이유', height=100)
        if st.button('Submit Feedback'):
            if student_name and incorrect and reason:
                ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                entry = f'[{ts}] {student_name} | {incorrect} | {reason}\n'
                try:
                    with open('analyze.txt', 'a', encoding='utf-8') as f:
                        f.write(entry)
                    st.success('Feedback submitted!')
                except Exception as e:
                    st.error(f'Error saving feedback: {e}')
            else:
                st.warning('모든 필드를 입력해주세요.')













elif page == 'Student Data':
    with left_col:
        st.subheader('Stored Student Data')
        # data.txt 내용 표시
        try:
            with open('data.txt', 'r', encoding='utf-8') as f:
                content = f.read()
            st.text_area('', content, height=300)
        except FileNotFoundError:
            st.error('data.txt 파일이 없습니다.')
        except Exception as e:
            st.error(f'data.txt 불러오기 중 오류 발생: {e}')

        # analyze.txt 데이터를 테이블로 표시
        st.subheader('Emotional Analysis Results')
        try:
            import pandas as pd
            rows = []
            with open('analyze.txt', 'r', encoding='utf-8') as f:
                for line in f:
                    # Expected format: [timestamp] Student: name | Incorrect Analysis: incorrect | Reason: reason
                    try:
                        parts = line.strip().split('|')
                        name = parts[0].split('Student:')[1].strip()
                        incorrect = parts[1].split('Incorrect Analysis:')[1].strip()
                        reason = parts[2].split('Reason:')[1].strip()
                        rows.append({'학번': name, '잘못 인식된 감정': incorrect, '이유': reason})
                    except Exception:
                        continue
            if rows:
                df = pd.DataFrame(rows)
                st.table(df)
            else:
                st.info('analyze.txt에 기록된 데이터가 없습니다.')
        except FileNotFoundError:
            st.warning('analyze.txt 파일이 없습니다.')
        except Exception as e:
            st.error(f'analyze.txt 불러오기 중 오류 발생: {e}')

    with right_col:
        st.write('')








elif page == 'Help':
    with left_col:
        st.subheader('Tips & Help')
        st.markdown(
            '''
- 💡 **Tip 1:** 윤리적 딜레마가 발생할 수 있는 상황을 미리 상상해 보세요.  
- 💡 **Tip 2:** AI가 내린 판단을 그대로 믿기보다, 항상 비판적으로 검토하세요.  
- ❓ **Help:** 문제가 있을 땈 사이드바의 ‘문의하기’ 버튼을 눌러주세요.
            '''
        )
    with right_col:
        st.write('')  # 비어 있는 영역
