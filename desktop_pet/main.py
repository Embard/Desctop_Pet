import os
import sys

from PySide6.QtWidgets import QApplication

from pet import PetWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Desktop Pet")
    app.setQuitOnLastWindowClosed(True)

    pet = PetWindow()
    pet.show()

    code = app.exec()
    os._exit(0)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
