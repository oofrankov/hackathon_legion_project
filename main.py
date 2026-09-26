import cv2
import mediapipe as mp
import numpy as np
import time

# Настройки MediaPipe
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(min_detection_confidence=0.5, min_tracking_confidence=0.5)

# Настройки таймера отвлечения
DISTRACTION_TIME_THRESHOLD = 3.0  # Секунды, после которых срабатывает алерт
distracted_start_time = None
is_distracted = False

# Захват видео с веб-камеры
cap = cv2.VideoCapture(0)

while cap.isOpened():
    success, image = cap.read()
    if not success:
        break

    # Переворачиваем изображение для эффекта зеркала и переводим в RGB
    image = cv2.cvtColor(cv2.flip(image, 1), cv2.COLOR_BGR2RGB)
    image.flags.writeable = False
    
    # Ищем лицо
    results = face_mesh.process(image)
    
    # Возвращаем обратно в BGR для отрисовки OpenCV
    image.flags.writeable = True
# Правильный вариант:
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

    
    img_h, img_w, img_c = image.shape
    face_3d = []
    face_2d = []

    if results.multi_face_landmarks:
        for face_landmarks in results.multi_face_landmarks:
            # Индексы ключевых точек для MediaPipe Face Mesh
            # 1: Кончик носа, 152: Подбородок, 33: Левый глаз, 263: Правый глаз, 61: Левый угол рта, 291: Правый угол рта
            key_points = [1, 152, 33, 263, 61, 291]
            
            for idx in key_points:
                lm = face_landmarks.landmark[idx]
                x, y = int(lm.x * img_w), int(lm.y * img_h)
                
                # 2D координаты на картинке
                face_2d.append([x, y])
                # 3D координаты (z берется из MediaPipe)
                face_3d.append([x, y, lm.z])

            # Преобразуем в numpy массивы
            face_2d = np.array(face_2d, dtype=np.float64)
            face_3d = np.array(face_3d, dtype=np.float64)

            # Матрица камеры (фокусное расстояние)
            focal_length = 1 * img_w
            cam_matrix = np.array([[focal_length, 0, img_h / 2],
                                   [0, focal_length, img_w / 2],
                                   [0, 0, 1]])
            dist_matrix = np.zeros((4, 1), dtype=np.float64)

            # Вычисляем угол поворота (SolvePnP)
            success, rot_vec, trans_vec = cv2.solvePnP(face_3d, face_2d, cam_matrix, dist_matrix)
            rmat, jac = cv2.Rodrigues(rot_vec)
            angles, mtxR, mtxQ, Qx, Qy, Qz = cv2.RQDecomp3x3(rmat)

            # Получаем углы в градусах
            x = angles[0] * 360  # Наклон вверх/вниз (Pitch)
            y = angles[1] * 360  # Поворот влево/вправо (Yaw)

            # Определяем, куда смотрит пользователь
            # Пороги (10-15 градусов) можно настроить под себя
            direction = "Center"
            if y < -10:
                direction = "Looking Left"
            elif y > 10:
                direction = "Looking Right"
            elif x < -10:
                direction = "Looking Down"
            elif x > 15:
                direction = "Looking Up"

            # Логика таймера
            if direction != "Center":
                if distracted_start_time is None:
                    distracted_start_time = time.time()
                else:
                    distracted_duration = time.time() - distracted_start_time
                    if distracted_duration > DISTRACTION_TIME_THRESHOLD:
                        is_distracted = True
            else:
                distracted_start_time = None
                is_distracted = False

            # Отрисовка текста на экране
            cv2.putText(image, f"Status: {direction}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(image, f"X (Pitch): {np.round(x,1)}", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.putText(image, f"Y (Yaw): {np.round(y,1)}", (20, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

            # Вывод алерта
            if is_distracted:
                cv2.putText(image, "ALERT: RETURN TO WORK!", (50, 250), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 4)
                # ЗДЕСЬ МОЖНО ДОБАВИТЬ ЗВУК:
                # Например (Windows): import winsound; winsound.Beep(1000, 200)
                # Или кроссплатформенно: playsound('alert.mp3', block=False)

    else:
        # Лицо не найдено
        cv2.putText(image, "NO FACE DETECTED", (50, 250), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 165, 255), 4)

    cv2.imshow('Focus Tracker Prototype', image)

    # Выход по нажатию клавиши 'Esc'
    if cv2.waitKey(5) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()