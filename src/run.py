from PyQt5.QtWidgets import QApplication
from page1_welcome import WelcomePage
import sys

def main():
    app = QApplication(sys.argv)
    welcome = WelcomePage()
    welcome.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
