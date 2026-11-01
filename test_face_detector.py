from models.face_manipulation_detector import analyze_face_manipulation

image_path = input("Enter image path: ").strip().strip('"')

result = analyze_face_manipulation(image_path)

print("\n===== DEEPTRUTH FACE ANALYSIS =====")
print("Status:", result.get("status"))
print("Verdict:", result.get("verdict"))
print("Faces detected:", result.get("face_count", 0))

for face in result.get("faces", []):
    print("\nFace:", face["face_number"])
    print("Verdict:", face["verdict"])
    print("Fake probability:", face["fake_probability"], "%")
    print("Real probability:", face["real_probability"], "%")