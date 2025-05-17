from channels.generic.websocket import AsyncWebsocketConsumer
import json
from asgiref.sync import sync_to_async
from .models import DeviceConnection, DeviceStatus

class HistoryConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        print('connect')
		# await self.accept()
        await self.channel_layer.group_add("history_updates", self.channel_name)
        # print(f"Add {self.channel_name} channel to users's group")
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("history_updates", self.channel_name)

    async def history_update(self, event):
        await self.send(text_data=json.dumps(event['data']))

class DeviceStatusConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for device status updates."""
    
    async def connect(self):
        """Handle WebSocket connection."""
        # Add client to the device_status group for broadcasts
        await self.channel_layer.group_add("device_status_updates", self.channel_name)
        await self.accept()
        print(f"Device status WebSocket connected: {self.channel_name}")

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        # Remove from group
        await self.channel_layer.group_discard("device_status_updates", self.channel_name)
        print(f"Device status WebSocket disconnected: {self.channel_name}, code: {close_code}")

    async def receive(self, text_data):
        """Handle message from WebSocket client."""
        try:
            # This can be used to handle specific commands from the client
            data = json.loads(text_data)
            command = data.get('command')
            
            if command == 'request_update':
                # Client is requesting an update - send updates for all devices
                await self.send_all_device_updates()
        except Exception as e:
            print(f"Error processing WebSocket message: {e}")
    
    async def device_status_update(self, event):
        """Send device status update to WebSocket client."""
        try:
            # Forward the update data to the client
            await self.send(text_data=json.dumps(event['data']))
        except Exception as e:
            print(f"Error sending device status update: {e}")
            
    @sync_to_async
    def get_all_device_status(self):
        """Get status information for all devices."""
        devices = DeviceConnection.objects.all()
        device_status_list = []
        
        for device in devices:
            try:
                device_status = DeviceStatus.objects.filter(device=device).first()
                
                if device_status:
                    status_info = {
                        'device_id': device.device_id,
                        'device_name': device.device_name,
                        'status': device_status.status,
                        'is_active': device.is_active,
                        'app_running': device.app_running,
                        'timestamp': device.last_connected.isoformat() if device.last_connected else None,
                    }
                    
                    # Add customer information if in use
                    if device_status.current_user:
                        status_info['customer_name'] = device_status.current_user.fullname
                        status_info['customer_phone'] = device_status.current_user.user.username
                    
                    # Add session information if available
                    if device_status.session_start:
                        status_info['session_start'] = device_status.session_start.isoformat()
                        if device_status.session_duration:
                            status_info['session_duration'] = str(device_status.session_duration)
                    
                    device_status_list.append(status_info)
            except Exception as e:
                print(f"Error getting status for device {device.device_id}: {e}")
                
        return device_status_list
            
    async def send_all_device_updates(self):
        """Send status updates for all devices to the requesting client."""
        try:
            device_updates = await self.get_all_device_status()
            
            # Send each device update individually
            for device_data in device_updates:
                await self.send(text_data=json.dumps(device_data))
                
            print(f"Sent updates for {len(device_updates)} devices")
        except Exception as e:
            print(f"Error sending all device updates: {e}")

class InventoryConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for inventory updates and low stock alerts."""
    
    async def connect(self):
        """Handle WebSocket connection."""
        # Add client to the inventory_updates group for broadcasts
        await self.channel_layer.group_add("inventory_updates", self.channel_name)
        await self.accept()
        print(f"Inventory WebSocket connected: {self.channel_name}")

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        # Remove from group
        await self.channel_layer.group_discard("inventory_updates", self.channel_name)
        print(f"Inventory WebSocket disconnected: {self.channel_name}, code: {close_code}")

    async def receive(self, text_data):
        """Handle message from WebSocket client."""
        try:
            # This can be used to handle specific commands from the client
            data = json.loads(text_data)
            command = data.get('command')
            
            if command == 'request_low_stock':
                # Client is requesting current low stock data
                await self.send_low_stock_data()
        except Exception as e:
            print(f"Error processing inventory WebSocket message: {e}")
    
    async def inventory_update(self, event):
        """Send inventory update to WebSocket client."""
        try:
            # Forward the update data to the client
            await self.send(text_data=json.dumps(event['data']))
        except Exception as e:
            print(f"Error sending inventory update: {e}")
            
    async def low_stock_alert(self, event):
        """Send low stock alert to WebSocket client."""
        try:
            # Forward the alert data to the client
            await self.send(text_data=json.dumps(event['data']))
        except Exception as e:
            print(f"Error sending low stock alert: {e}")

    @sync_to_async
    def get_low_stock_products(self):
        """Get all products with low stock levels."""
        from django.db.models import F
        from .models import Product, InventoryTransaction
        from django.utils import timezone
        
        # Get low stock products
        try:
            low_stock_products = Product.objects.filter(
                quantity__lte=F('low_stock_threshold')
            ).values(
                'product_id', 'name', 'quantity', 'low_stock_threshold', 'category'
            ).order_by('quantity')
            
            # Add transaction timestamps
            products_data = []
            for product in low_stock_products:
                # Get the latest inventory transaction for this product
                latest_transaction = InventoryTransaction.objects.filter(
                    product_id=product['product_id']
                ).order_by('-timestamp').first()
                
                # Format the product data with additional information
                products_data.append({
                    'product_id': product['product_id'],
                    'name': product['name'],
                    'current_quantity': product['quantity'],
                    'low_stock_threshold': product['low_stock_threshold'],
                    'category': product['category'],
                    'last_updated': latest_transaction.timestamp.isoformat() if latest_transaction else None,
                    'status': 'critical' if product['quantity'] == 0 else 'low',
                    'restock_needed': product['low_stock_threshold'] - product['quantity']
                })
            
            return {
                'status': 'success',
                'count': len(products_data),
                'data': products_data,
                'timestamp': timezone.now().isoformat()
            }
        except Exception as e:
            print(f"Error getting low stock products: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
            
    async def send_low_stock_data(self):
        """Send low stock data to the requesting client."""
        try:
            low_stock_data = await self.get_low_stock_products()
            
            # Send the data as a single message
            await self.send(text_data=json.dumps({
                'type': 'low_stock_data',
                'data': low_stock_data
            }))
            
        except Exception as e:
            print(f"Error sending low stock data: {e}")
            # Send error message
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f"Failed to retrieve low stock data: {str(e)}"
            }))