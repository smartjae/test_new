
import streamlit as st
from datetime import datetime
from PIL import Image
from app_streaming import run_emotion_analysis
import streamlit.components.v1 as components
# ① webrtc 관련 import
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase
import av

# ——— Page config & title ———
st.set_page_config(layout='wide', page_title='ethicapp')
st.title('감정을 읽는 기계')

# ① 필요한 임포트 (최상단에 있어야 합니다)
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase
import av

# EmotionProcessor 정의 (상단에 위치)
class EmotionProcessor(VideoProcessorBase):
    def __init__(self):
        # 모델과 Face Mesh 솔루션을 한 번만 로드
        self.model = load_emotion_model()
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
        # Face Mesh 처리: BGR -> RGB
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb)
        # 랜드마크가 감지되면 그리기
        if results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:
                draw_landmarks(
                    image=img,
                    landmark_list=face_landmarks,
                    connections=mp.solutions.face_mesh.FACE_CONNECTIONS,
                    landmark_drawing_spec=None,
                    connection_drawing_spec=get_default_face_mesh_styles()[1]
                )
        # 감정 분석 실행
        result = self.model.predict(img)
        # 예측 결과 텍스트 오버레이
        cv2.putText(
            img,
            result,
            (10, img.shape[0] - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2
        )
        # VideoFrame으로 변환 후 반환
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
- 웹캠으로 얼굴을 실시간 감지하며 Facemesh를 그립니다.  
- 브라우저에서 카메라 권한을 허용해 주세요.  
- Start 버튼 클릭 시 스트리밍이 시작됩니다.
            '''
        )

    with left_col:
        # 세션 상태 초기화
        if 'emotion_running' not in st.session_state:
            st.session_state['emotion_running'] = False

        # 스트리밍 제어 버튼
        btn_start, btn_stop = st.columns(2)
        if btn_start.button('Start Emotion Analysis'):
            st.session_state['emotion_running'] = True
        if btn_stop.button('Stop Emotion Analysis'):
            st.session_state['emotion_running'] = False

        # 스트리밍 및 분석
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

        # 학생 피드백 기록
        st.subheader('학생 피드백 기록')
        student_name = st.text_input('학번')
        incorrect = st.text_area('잘못 인식된 감정', height=100)
        reason = st.text_area('이유', height=100)
        if st.button('Submit Feedback'):
            if student_name.strip() and incorrect.strip() and reason.strip():
                ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                entry = f'[{ts}] Student: {student_name} | Incorrect Analysis: {incorrect} | Reason: {reason}\n'
                try:
                    with open('analyze.txt', 'a', encoding='utf-8') as f:
                        f.write(entry)
                    st.success('Feedback submitted!')
                except Exception as e:
                    st.error(f'Error saving feedback: {e}')
            else:
                st.warning('모든 필드를 입력한 후 제출해주세요.')













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
