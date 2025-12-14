import cv2

def test_cameras():
    print("Testing Camera Indices 0 to 10...")
    
    for index in range(4, 11):
        cap = cv2.VideoCapture(index)
        if cap.isOpened():
            print(f"[SUCCESS] Camera found at Index {index}")
            ret, frame = cap.read()
            if ret:
                cv2.imshow(f"Camera Index {index} - Press Q to close", frame)
                print(f"   Resolution: {frame.shape[1]}x{frame.shape[0]}")
                print("   Press 'q' in the window to check the next camera...")
                
                # Wait for Q key
                while True:
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
            cap.release()
            cv2.destroyAllWindows()
        else:
            print(f"[FAIL] No camera at Index {index}")

if __name__ == "__main__":
    test_cameras()