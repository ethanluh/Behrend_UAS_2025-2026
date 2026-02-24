import cv2

def test_usb_camera(camera_index=0, width=None, height=None):
    cap = cv2.VideoCapture(camera_index)

    if not cap.isOpened():
        print(f"❌ Cannot open camera (index {camera_index})")
        return False

    if width:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    if height:
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    print("✅ Camera opened successfully")
    print("Press 'q' to quit")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ Failed to grab frame")
            break

        cv2.imshow("USB Camera Test", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    return True


if __name__ == "__main__":
    test_usb_camera()
