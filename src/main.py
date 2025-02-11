from PyQt5.QtWidgets import QApplication
import sys
from import_module import ImportModule

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Get the product page instance (will create it)
    product_page = ImportModule.get_product_page()
    
    # Show the initial page
    product_page.show()
    
    sys.exit(app.exec_())
