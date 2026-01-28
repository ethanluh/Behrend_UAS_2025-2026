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
    """Generate GStreamer pipeline for Jetson Nano camera."""
    return (
        "nvarguscamerasrc sensor-id=%d ! "
        "video/x-raw(memory:NVMM), width=(int)%d, height=(int)%d, format=(string)NV12, framerate=(fraction)%d/1 ! "
        "nvvidconv flip-method=%d ! "
        "video/x-raw, width=(int)%d, height=(int)%d, format=(string)BGRx ! "
        "videoconvert ! "
        "video/x-raw, format=(string)BGR ! appsink"
        % (sensor_id, capture_width, capture_height, framerate, flip_method, display_width, display_height)
    )

def gstreamer_pipeline_alternative(sensor_id=0):
    """Alternative simpler GStreamer pipeline."""
    return (
        "nvarguscamerasrc sensor-id=%d ! "
        "video/x-raw(memory:NVMM), width=1280, height=720, format=NV12, framerate=30/1 ! "
        "nvvidconv ! "
        "video/x-raw, format=BGRx ! "
        "videoconvert ! "
        "video/x-raw, format=BGR ! appsink"
        % sensor_id
    )

def test_camera():
    """Test the camera by displaying a live feed."""
    # Try multiple pipelines and sensor IDs
    pipelines = [
        (gstreamer_pipeline(sensor_id=0), "Main pipeline, sensor 0"),
        (gstreamer_pipeline(sensor_id=1), "Main pipeline, sensor 1"),
        (gstreamer_pipeline_alternative(sensor_id=0), "Alternative pipeline, sensor 0"),
        (gstreamer_pipeline_alternative(sensor_id=1), "Alternative pipeline, sensor 1"),
    ]
    
    cap = None
    for pipeline, description in pipelines:
        print(f"Trying: {description}")
        print(f"Pipeline: {pipeline}")
        cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
        
        if cap.isOpened():
            print(f"Success! Camera opened with {description}")
            break
        else:
            print(f"Failed to open with {description}")
            if cap:
                cap.release()
    
    if not cap or not cap.isOpened():
        print("\nError: Could not open camera with any pipeline")
        print("\nTroubleshooting:")
        print("1. Check camera connection")
        print("2. Verify camera is detected: ls /dev/video*")
        print("3. Check if another app is using the camera")
        print("4. Try running with sudo")
        print("5. Verify GStreamer plugins are installed")
        return False

    print("Camera feed started. Press 'q' to quit.")
    
    try:
        while True:
            ret, frame = cap.read()

            if not ret:
                print("Error: Could not read frame")
                break

            cv2.imshow('Camera Feed', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("Camera test completed")
    
    return True

def main():
    test_camera()

if __name__ == "__main__":
    main()