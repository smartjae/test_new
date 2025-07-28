# ===== app_streaming.py =====
import json
import cv2
import numpy as np
import mediapipe as mp
import tensorflow as tf
import streamlit as st

@st.cache_resource  # 모델과 레이블 맵을 캐싱하여 앱 성능 최적화
def load_emotion_model():
    # 1) label_map.json에서 클래스 순서 불러오기
    with open("label_map.json", "r", encoding="utf-8") as f:
        label_map = json.load(f)
    # 2) 학습된 CNN 모델 로드 (.h5 포맷)
    model = tf.keras.models.load_model("fer_cnn_directory.h5")
    return label_map, model


def run_emotion_analysis():
    """
    Streamlit 페이지 내에서 실시간으로 웹캠을 통해 얼굴을 감지하고
    CNN 모델로 감정을 예측해 화면에 프레임과 확률 분포를 표시합니다.
    """
    label_map, model = load_emotion_model()

    # MediaPipe FaceMesh 설정
    mpfm = mp.solutions.face_mesh.FaceMesh(
        static_image_mode=False,
        max_num_faces=1,
        refine_landmarks=False,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )
    mpdraw = mp.solutions.drawing_utils
    draw_spec = mpdraw.DrawingSpec(color=(0,255,0), thickness=1, circle_radius=1)

    # 웹캠 열기
    cap = cv2.VideoCapture(0)

    col1, col2 = st.columns([3, 1])
    frame_placeholder = col1.empty()
    proba_placeholder = col2.empty()

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            st.error("카메라를 열 수 없습니다.")
            break

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, _ = rgb.shape
        results = mpfm.process(rgb)
        if results.multi_face_landmarks:
            lm = results.multi_face_landmarks[0].landmark
            pts = [(int(p.x * w), int(p.y * h)) for p in lm]
            xs, ys = zip(*pts)
            x1, x2 = max(min(xs), 0), min(max(xs), w)
            y1, y2 = max(min(ys), 0), min(max(ys), h)
            if (x2-x1) < 20 or (y2-y1) < 20:
                frame_placeholder.image(frame, channels="BGR")
                continue

            face = rgb[y1:y2, x1:x2]
            gray = cv2.cvtColor(face, cv2.COLOR_RGB2GRAY)
            resized = cv2.resize(gray, (48, 48))
            x = resized.astype("float32") / 255.0
            x = np.expand_dims(x, axis=(0, -1))  # (1,48,48,1)

            proba = model.predict(x)[0]
            proba_dict = { label_map[i]: float(proba[i]) for i in range(len(proba)) }
            proba_placeholder.write(proba_dict)

            idx = int(np.argmax(proba))
            pred_label = label_map[idx]
            status = (
                "Positive" if pred_label == "Happy"
                else "Negative" if pred_label in ["Sad","Angry","Disgust","Fear"]
                else "Neutral"
            )

            mpdraw.draw_landmarks(
                image=frame,
                landmark_list=results.multi_face_landmarks[0],
                connections=mp.solutions.face_mesh.FACEMESH_TESSELATION,
                connection_drawing_spec=draw_spec
            )
            cv2.putText(
                frame,
                f"{status} ({pred_label})",
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 0, 255),
                2
            )

        frame_placeholder.image(frame, channels="BGR")
    cap.release()


