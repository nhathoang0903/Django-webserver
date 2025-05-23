from django.contrib import admin
from django.urls import path, re_path
from .views import (
    ProductListCreateView,
    HistoryListCreateView,
    login_view,
    dashboard_view,
    product_list_view,
    search_by_category,
    add_product,
    edit_product,
    delete_product,
    history_list_view, 
    statisticsboard_view,
    InvoiceAPIView,
    TemplateHTMLRenderer,
    DeviceConnectionView,
    DeviceStatusUpdateView,
    DeviceDeleteView,
    device_password_view,
    logout_view,
    CustomerSignupView,
    CustomerLoginView,
    CustomerDetailView,
    CustomerListView,
    AdminLoginView,
    TopThreeProductsView,  
    ProductsByCategoryView,  
    CustomerChangePasswordView,
    CustomerHistoryView,
    CreateCustomerHistoryView,
    CustomerHistoryLinkView,  
    CustomerPurchaseHistoryView,
    CustomerTotalSpendingView,  
    ProductSearchView,  
    FavoriteProductView,  
    ProductDetailByNameView,  
    ProductRatingView,  
    CustomerDeviceConnectionView,  
    DeviceConnectionStatusView,   
    ShoppingMonitoringView, 
    # CheckEndSessionStatusView, 
    # AllDeviceStatusAPIView,  
    AllDeviceStatusView,
    CustomerListView,
    EndDeviceSessionView,
    CustomerChatView,
    AdminChatView,
    CancelShoppingHistoryView,
    ShoppingMonitoringView,
    ShoppingRatingView,
    PaymentShoppingView,  
    PaymentSignalView, 
    CancelPaymentSignalView,
    PaymentStatusView,
    SaveFCMTokenView,
    SendPersonalNotificationView,
    BroadcastNotificationView,
    ListNotificationsView,
    MarkNotificationReadView,
    TestFCMNotificationView,
    UploadImageView,
    CheckNewProductView,
    CheckProductEditsView,
    CheckProductDeletionsView,
    AddStockView,
    InventoryHistoryView,
    LowStockProductsView,
    WebSocketDebugView,
    WebSocketHealthCheckView,
    add_stock_note,
    inventory_management_view,
    export_inventory_pdf,
    NotificationSettingsView,
    index_view,
    signup_view,
    check_static_file,
)
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.views import LogoutView
from .views import login_view 
from . import views
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="Cartsy System API",
        default_version='v1',
        description="API documentation for Smart Cart System"
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path('admin/', admin.site.urls),
    # path('users/', users_view, name='users'), #user view
    path('', index_view, name='index'),  # Set the root URL to the index page
    path('login/', login_view, name='login'),  # Login page
    path('signup/', signup_view, name='signup'),  # Signup page
    path('logout/', logout_view, name='logout'),  
    path('dashboard/', dashboard_view, name='dashboard'), #dashboard page
    path('product_list/', product_list_view, name='product_list'),
    path('search/category/<str:category>/', search_by_category, name='search_by_category'),
    path('add-product/', add_product, name='add_product'),
    # Define URL patterns for edit and delete product
    path('product_list/edit/<int:product_id>/', edit_product, name='edit_product'),
    path('product_list/edit/<int:product_id>/', edit_product, name='edit_product'),
    path('product_list/delete/<int:product_id>/', delete_product, name='delete_product'),
    path('product_list/add_stock_note/<int:product_id>/', add_stock_note, name='add_stock_note'),
    path('history_list/', history_list_view, name='history_list'),
    path('statistic/', statisticsboard_view, name='statistic'),
    path('inventory/', inventory_management_view, name='inventory_management'),
    path('inventory/export-pdf/', export_inventory_pdf, name='export_inventory_pdf'),
    path('products/', ProductListCreateView.as_view(), name='product-list-create'), #api for product
    path('history/', HistoryListCreateView.as_view(), name='history-list-create'), #api for history
    path('generate_invoice/<str:random_id>/', views.generate_invoice, name='generate_invoice'),
    # path('api/history/', HistoryCreateView.as_view(), name='create_history'),
    path('api/invoice/<str:random_id>/', InvoiceAPIView.as_view(), name='invoice_api'),
    path('invoice/<str:random_id>/', InvoiceAPIView.as_view(renderer_classes=[TemplateHTMLRenderer]), name='invoice_html'),
    path('devices/password/', device_password_view, name='device_password'),
    path('devices/status/', views.device_status_view, name='device_status'),
    # Device connection API endpoints
    path('api/devices/', DeviceConnectionView.as_view(), name='device-connection'),
    path('api/devices/all-status/', AllDeviceStatusView.as_view(), name='all-device-status'),
    path('api/devices/<str:device_id>/status/', DeviceStatusUpdateView.as_view(), name='device-status'),
    path('api/devices/<str:device_id>/', DeviceConnectionView.as_view(), name='device-info'),
    path('api/devices/<str:device_id>/delete/', DeviceDeleteView.as_view(), name='device-delete'),
    path('api/device/end-session/<str:device_id>/', EndDeviceSessionView.as_view(), name='end-device-session'),
    path('api/device/end-session/<str:device_id>/status/', views.CheckEndSessionStatusView.as_view(), name='check-end-session-status'),
    
    # Customer API endpoints
    path('api/customers/signup/', CustomerSignupView.as_view(), name='customer-signup'),
    path('api/customers/login/', CustomerLoginView.as_view(), name='customer-login'),
    path('api/customers/<str:username>/', CustomerDetailView.as_view(), name='customer-detail'),
    path('api/customers/', CustomerListView.as_view(), name='customer-list'),
    path('api/customer/change-password/', CustomerChangePasswordView.as_view(), name='customer-change-password'),
    path('customers/', views.customer_list_view, name='customer_list'),
    path('customers/<int:customer_id>/edit/', views.edit_customer_view, name='edit_customer'),
    path('customers/<int:customer_id>/delete/', views.delete_customer_view, name='delete_customer'),
    
    # Swagger documentation URLs
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    
    # Admin login API endpoint
    path('api/admin/login/', AdminLoginView.as_view(), name='admin-login'),
    path('api/top-three-products/', TopThreeProductsView.as_view(), name='top_three_products_api'),
    path('api/products/category/<str:category>/', ProductsByCategoryView.as_view(), name='products-by-category'),
    path('api/customer-history-link/', CustomerHistoryLinkView.as_view(), name='customer-history-link'),
    path('api/customer/purchases/', CustomerPurchaseHistoryView.as_view(), name='customer-purchases'),
    path('api/customer/total-spending/', CustomerTotalSpendingView.as_view(), name='customer-total-spending'),
    path('api/products/search/', ProductSearchView.as_view(), name='product-search'), 
    path('api/customer/favorites/', FavoriteProductView.as_view(), name='customer-favorites'),  
    path('api/products/detail/', ProductDetailByNameView.as_view(), name='product-detail-by-name'), 
    path('api/device/connect/', CustomerDeviceConnectionView.as_view(), name='device-connect'),
    path('api/device/status/<str:device_id>/', DeviceConnectionStatusView.as_view(), name='device-status'),
    path('api/shopping/monitor/', ShoppingMonitoringView.as_view(), name='shopping-monitor'),
    path('api/chat/customer/', CustomerChatView.as_view(), name='customer-chat'),
    path('api/chat/admin/', AdminChatView.as_view(), name='admin-chat'),
    path('chat/', views.chat_view, name='chat'),
    path('api/shopping/cancel-history/', CancelShoppingHistoryView.as_view(), name='cancel-shopping-history'),
    path('api/shopping/payment-signal/<str:device_id>/', PaymentSignalView.as_view(), name='payment-signal'),
    path('api/shopping/cancel-payment-signal/<str:device_id>/', views.CancelPaymentSignalView.as_view(), name='cancel-payment-signal'),
    path('api/payment/status/', PaymentStatusView.as_view(), name='payment-status'),
    # path('api/shopping/payment/', PaymentShoppingView.as_view(), name='payment-shopping'),
    path('api/products/check-new/', CheckNewProductView.as_view(), name='check-new-products'),
    path('api/products/check-edits/', CheckProductEditsView.as_view(), name='check-product-edits'),
    path('api/products/check-deletions/', CheckProductDeletionsView.as_view(), name='check-product-deletions'),
    path('api/inventory/history/<int:product_id>/', InventoryHistoryView.as_view(), name='inventory_history'),
    path('api/inventory/low-stock/', LowStockProductsView.as_view(), name='low_stock_products'),
]

if settings.DEBUG:
    from django.views.static import serve
    urlpatterns += [
        path('static/<path:path>', serve, {'document_root': settings.STATIC_ROOT}),
    ]
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
else:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

urlpatterns += [
    path('api/product/rating/', ProductRatingView.as_view(), name='product-rating'),
    path('api/shopping/rating/', ShoppingRatingView.as_view(), name='shopping-rating'),
    path('api/notifications/token/', SaveFCMTokenView.as_view(), name='save-fcm-token'),
    path('api/notifications/send/', SendPersonalNotificationView.as_view(), name='send-personal-notif'),
    path('api/notifications/broadcast/', BroadcastNotificationView.as_view(), name='broadcast-notif'),
    path('api/notifications/', ListNotificationsView.as_view(), name='list-notifications'),
    path('api/notifications/read/', MarkNotificationReadView.as_view(), name='mark-notif-read'),
    path('api/notifications/test/', TestFCMNotificationView.as_view(), name='test-fcm-notification'),
    path('api/notifications/settings/', NotificationSettingsView.as_view(), name='notification-settings'),
    path('upload_image/', UploadImageView.as_view(), name='upload_image'),
    path('api/product/add-stock/', AddStockView.as_view(), name='add-stock'),
    path('api/websocket-debug/', WebSocketDebugView.as_view(), name='websocket-debug'),
    path('api/websocket-health/', WebSocketHealthCheckView.as_view(), name='websocket-health'),
    path('test-static/<str:filename>/', check_static_file, name='check-static-file'),
]
