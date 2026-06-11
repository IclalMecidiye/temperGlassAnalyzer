import cv2
cv2.setNumThreads(1)  # OpenCV iç thread'leri GIL ile çakışıyor, kapat

from ui.app import App


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
