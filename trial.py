from backend.main_guardrails.image_guard import ImageSafetyGuard


def main():
    guard = ImageSafetyGuard(
        model="gemma3:4b"
    )

    # Test with the exact kind of URL that previously crashed
    image_url = (
        "hhttps://media.istockphoto.com/id/1533529011/photo/beauty-shot-of-beautiful-black-woman-in-monochromatic-pink-stock-photo-copy-space.jpg?s=2048x2048&w=is&k=20&c=kd8mewqMZrL3wqhAkqxWljkJfoR0vNuiOjzMdXVKhcQ="
    )

    print("Testing image safety guard...")
    print(f"URL: {image_url}")

    result = guard.check_image(image_url)

    print()
    print("Result:", result)

    if result is True:
        print("PASS: Image classified as SAFE")

    elif result is False:
        print("PASS: Image classified as UNSAFE")

    else:
        print("ERROR: Image safety check failed")


if __name__ == "__main__":
    main()