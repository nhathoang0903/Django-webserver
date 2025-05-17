from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/history/$', consumers.HistoryConsumer.as_asgi()),
    re_path(r'ws/device-status/$', consumers.DeviceStatusConsumer.as_asgi()),
    re_path(r'ws/inventory/$', consumers.InventoryConsumer.as_asgi()),
    
    # Alternative patterns that might work in different environments
    re_path(r'^ws/device-status/$', consumers.DeviceStatusConsumer.as_asgi()), 
    re_path(r'^ws/device-status$', consumers.DeviceStatusConsumer.as_asgi()),
    re_path(r'ws/device-status$', consumers.DeviceStatusConsumer.as_asgi()),
    re_path(r'^ws/inventory/$', consumers.InventoryConsumer.as_asgi()),
    re_path(r'^ws/inventory$', consumers.InventoryConsumer.as_asgi()),
    re_path(r'ws/inventory$', consumers.InventoryConsumer.as_asgi()),
    
    # Patterns without ws/ prefix (for some setups)
    re_path(r'^device-status/$', consumers.DeviceStatusConsumer.as_asgi()),
    re_path(r'device-status/$', consumers.DeviceStatusConsumer.as_asgi()),
    re_path(r'^inventory/$', consumers.InventoryConsumer.as_asgi()),
    re_path(r'inventory/$', consumers.InventoryConsumer.as_asgi()),
]