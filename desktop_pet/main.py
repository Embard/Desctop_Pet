import sys

from PySide6.QtWidgets import QApplication

from pet import PetWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Desktop Pet")
    app.setQuitOnLastWindowClosed(True)

    pet = PetWindow()
    pet.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
