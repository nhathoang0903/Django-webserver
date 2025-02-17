
class ImportModule:
    product_page = None
    shopping_page = None

    @classmethod
    def get_product_page(cls):
        if not cls.product_page:
            from page3_productsinfo import ProductPage
            cls.product_page = ProductPage()
            print("Product page opened")
        return cls.product_page

    @classmethod
    def get_shopping_page(cls):
        if not cls.shopping_page:
            from page4_shopping import ShoppingPage
            cls.shopping_page = ShoppingPage()
            print("Shopping page opened")
        return cls.shopping_page