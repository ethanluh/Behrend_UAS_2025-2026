from picamera2 import Picamera2
import time

def test_camera():
    """Test the camera by displaying a live feed."""
    try:
        picam2 = Picamera2()
        picam2.start()
        print("Camera started. Press Ctrl+C to stop.")
        
        while True:
            # Capture a frame
            frame = picam2.capture_array()
            
            # Note: picamera2 doesn't have built-in display like cv2.imshow
            # You can process the frame here or use it with other libraries
            # For display, you might want to use matplotlib or convert to PIL Image
            time.sleep(0.1)  # Small delay to prevent excessive CPU usage
            
    except KeyboardInterrupt:
        print("\nStopping camera...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        try:
            picam2.stop()
        except:
            pass
        print("Camera test completed")

def main():
    test_camera()

if __name__ == "__main__":
    main()