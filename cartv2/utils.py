from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json
from datetime import datetime

def send_device_status_update(device_id, device_name, status, customer_name=None, customer_phone=None, 
                            session_start=None, session_duration=None, is_active=None, app_running=None):
    """
    Send a device status update to all WebSocket clients.
    
    Args:
        device_id: The ID of the device
        device_name: The name of the device
        status: The current status (in_use, available, etc.)
        customer_name: Optional customer name if in use
        customer_phone: Optional customer phone if in use
        session_start: Optional session start time if in use
        session_duration: Optional session duration if in use
        is_active: Optional device online/offline status
        app_running: Optional app running status
    """
    try:
        channel_layer = get_channel_layer()
        
        # Format the data for WebSocket
        data = {
            'device_id': device_id,
            'device_name': device_name,
            'status': status,
            'timestamp': datetime.now().isoformat(),
        }
        
        # Add optional fields if provided
        if customer_name is not None:
            data['customer_name'] = customer_name
        if customer_phone is not None:
            data['customer_phone'] = customer_phone
        if session_start is not None:
            data['session_start'] = session_start.isoformat() if hasattr(session_start, 'isoformat') else session_start
        if session_duration is not None:
            data['session_duration'] = str(session_duration)
        if is_active is not None:
            data['is_active'] = is_active
        if app_running is not None:
            data['app_running'] = app_running
            
        # Send to device_status_updates group
        async_to_sync(channel_layer.group_send)(
            'device_status_updates',
            {
                'type': 'device_status_update',
                'data': data
            }
        )
        print(f"WebSocket update sent for device {device_id}")
        return True
    except Exception as e:
        print(f"Error sending WebSocket update: {e}")
        return False 