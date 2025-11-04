import cv2

def test_camera():
    """Test the camera by displaying a live feed."""
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Error: Could not open camera")
        exit()

    while True:
        ret, frame = cap.read()

        if not ret:
            print("Error: Could not read frame")
            break

        cv2.imshow('frame', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("Camera test completed")

def main():
    test_camera()

if __name__ == "__main__":
    main()