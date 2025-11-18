import cv2

def gstreamer_pipeline(
    sensor_id=0,
    capture_width=1280,
    capture_height=720,
    display_width=1280,
    display_height=720,
    framerate=30,
    flip_method=0,
):
    return (
        "nvgstcamera src=%d !" % sensor_id +
        "video/x-raw, width=(int)%d, height=(int)%d, framerate=(fraction)%d/1 !" % (capture_width, capture_height, framerate) +
        "nvvidconv flip-method=%d !" % flip_method +
        "video/x-raw, width=(int)%d, height=(int)%d, format=(string)BGRx !" % (display_width, display_height) +
        "videoconvert !" +
        "video/x-raw, format=(string)BGR ! appsink"
    )

def test_camera():
        

    """Test the camera by displaying a live feed."""
    cap = cv2.VideoCapture(gstreamer_pipeline(), cv2.CAP_GSTREAMER)

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