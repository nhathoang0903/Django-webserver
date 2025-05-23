import random
from django.db import models
import json
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
import pytz
from django.conf import settings
from django.core.cache import cache
from .utils import send_device_status_update

class SuperUserInfo(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username

class Product(models.Model):
    product_id = models.AutoField(primary_key=True)  # Unique ID for each product
    name = models.CharField(max_length=255)  # Name of the product
    quantity = models.PositiveIntegerField()  # Available quantity in stock
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Price of the product (e.g., in VND)
    description = models.TextField(blank=True, null=True)  # Optional product description
    category = models.CharField(max_length=100)  # Category (e.g., Beverages, Snacks)
    image_url = models.CharField(max_length=255, blank=True, null=True)  # URL of the product image
    low_stock_threshold = models.PositiveIntegerField(default=10)  # Threshold for low stock notifications

    def is_low_stock(self):
        """Check if product stock is below threshold"""
        return self.quantity <= self.low_stock_threshold

    def __str__(self):
        return self.name

class History(models.Model):
    purchase_id = models.AutoField(primary_key=True)
    random_id = models.CharField(max_length=11, unique=True, editable=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    product = models.TextField()  # JSON string to store multiple products
    note = models.TextField(blank=True, null=True)  # Optional note field

    def save(self, *args, **kwargs):
        if not self.random_id:
            self.random_id = self.generate_unique_random_id()
        # Convert to Vietnam timezone before saving
        if not self.timestamp:
            vietnam_tz = pytz.timezone('Asia/Ho_Chi_Minh')
            self.timestamp = timezone.localtime(timezone.now(), vietnam_tz)
        
        # Check if this is a new history record
        is_new = self._state.adding
        
        # Save the history record first
        super().save(*args, **kwargs)
        
        # Create CustomerHistory
        CustomerHistory.objects.get_or_create(
            history=self,
            defaults={'guest_name': None}
        )
        
        # If this is a new history record, create inventory transactions
        if is_new:
            try:
                product_details = self.get_product_details()
                for item in product_details:
                    product_name = item.get('name')
                    quantity = item.get('quantity', 0)
                    
                    if not product_name or quantity <= 0:
                        continue  # Skip invalid entries
                    
                    # Find the product
                    try:
                        with transaction.atomic():
                            product = Product.objects.select_for_update().get(name=product_name)
                            
                            # Create inventory transaction
                            InventoryTransaction.objects.create(
                                product=product,
                                transaction_type='subtraction',
                                quantity=quantity,
                                reference_id=self.random_id,
                                notes=f"Purchase transaction {self.random_id}"
                            )
                            
                            # Log successful transaction
                            print(f"Successfully processed inventory transaction for: {product_name}, quantity: {quantity}")
                    except Product.DoesNotExist:
                        print(f"Product not found: {product_name}")
                    except Exception as item_error:
                        print(f"Error processing product {product_name}: {item_error}")
            except Exception as e:
                print(f"Error creating inventory transactions: {e}")

    def generate_unique_random_id(self):
        while True:
            random_id = ''.join(random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ') for _ in range(5)) + ''.join(random.choice('0123456789') for _ in range(6))
            if not History.objects.filter(random_id=random_id).exists():
                return random_id

    def get_product_details(self):
        try:
            return json.loads(self.product)
        except json.JSONDecodeError:
            print("Failed to parse product JSON")
            return []

    def __str__(self):
        return f"Purchase {self.purchase_id} on {self.timestamp}"

class DeviceConnection(models.Model):
    device_id = models.CharField(max_length=100, unique=True)  # Unique identifier for the device
    device_name = models.CharField(max_length=100)  # Name or description of the device
    device_type = models.CharField(max_length=50, default='raspberry_pi')  # Type of device (e.g., 'mobile', 'raspberry_pi', 'camera')
    ip_address = models.CharField(max_length=50, null=True, blank=True)  # Device IP address
    is_active = models.BooleanField(default=False)  # Device on/off status
    app_running = models.BooleanField(default=False)  # Application running status
    last_connected = models.DateTimeField(auto_now=True)  # Last connection time
    created_at = models.DateTimeField(auto_now_add=True)  # When the device was first registered

    def __str__(self):
        return f"{self.device_name} ({self.device_type}) - {'Active' if self.is_active else 'Inactive'}"

    def save(self, *args, **kwargs):
        # Save the model
        super().save(*args, **kwargs)
        
        # Update device status WebSocket if it exists
        try:
            device_status = self.devicestatus
            device_status.send_status_update()
        except Exception as e:
            print(f"Error sending connection update: {e}")

class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    surname = models.CharField(max_length=100)
    firstname = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15, unique=True)
    profile_image = models.TextField(null=True, blank=True)
    fcm_token = models.CharField(max_length=255, null=True, blank=True)  # <-- New field lưu FCM token
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    favorites = models.ManyToManyField(Product, related_name='favorited_by', blank=True)

    @property
    def fullname(self):
        """Get full name by combining surname and firstname."""
        return f"{self.surname} {self.firstname}".strip()

    def set_names(self, surname=None, firstname=None):
        """Helper method to set surname and firstname."""
        if surname is not None:
            self.surname = surname
        if firstname is not None:
            self.firstname = firstname

    def __str__(self):
        return f"{self.fullname} ({self.user.username})"

    class Meta:
        ordering = ['surname', 'firstname']

class CustomerHistory(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    guest_name = models.CharField(max_length=200, blank=True, null=True)
    history = models.OneToOneField(History, on_delete=models.CASCADE)
    fullname = models.CharField(max_length=200, editable=False)

    def save(self, *args, **kwargs):
        if self.customer:
            self.fullname = self.customer.fullname
        elif self.guest_name:
            self.fullname = self.guest_name
        else:
            self.fullname = "Dsoft-member"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.fullname} - {self.history.timestamp}"

class ProductRating(models.Model):
    product_name = models.CharField(max_length=255)
    star = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

class DeviceStatus(models.Model):
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('in_use', 'In Use'),
        ('maintenance', 'Under Maintenance'),
        ('offline', 'Offline')
    ]

    device = models.OneToOneField(DeviceConnection, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    current_user = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    session_start = models.DateTimeField(null=True, blank=True)
    last_status_change = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.device.device_name} - {self.status}"
    
    def save(self, *args, **kwargs):
        # Save the model
        super().save(*args, **kwargs)
        
        # Send WebSocket update
        self.send_status_update()
    
    def send_status_update(self):
        """Send status update via WebSocket"""
        try:
            device_id = self.device.device_id
            device_name = self.device.device_name
            status = self.status
            customer_name = self.current_user.fullname if self.current_user else None
            customer_phone = self.current_user.user.username if self.current_user else None
            session_start = self.session_start
            session_duration = self.session_duration
            is_active = self.device.is_active
            app_running = self.device.app_running
            
            # Send update via WebSocket
            send_device_status_update(
                device_id=device_id,
                device_name=device_name,
                status=status,
                customer_name=customer_name,
                customer_phone=customer_phone,
                session_start=session_start,
                session_duration=session_duration,
                is_active=is_active,
                app_running=app_running
            )
        except Exception as e:
            print(f"Error sending status update: {e}")
    
    def start_session(self, customer=None):
        """Start a session for either a registered customer or guest"""
        self.status = 'in_use'
        self.current_user = customer
        self.session_start = timezone.now()
        self.save()

        # Create a session record
        CustomerDeviceSession.objects.create(
            customer=customer,
            device=self.device,
            is_guest=customer is None
        )

    def end_session(self):
        """End the current session"""
        if self.status == 'in_use':
            # Update the session record
            current_session = CustomerDeviceSession.objects.filter(
                device=self.device,
                end_time__isnull=True
            ).first()
            
            if current_session:
                current_session.end_time = timezone.now()
                current_session.save()

            # Clear all payment signals from cache
            device_id = self.device.device_id
            cache.delete(f'payment_signal_{device_id}')
            cache.delete(f'cancel_payment_signal_{device_id}')
            cache.delete(f'payment_success_{device_id}')
            cache.delete(f'payment_success_timestamp_{device_id}')

            # Reset device status
            self.status = 'available'
            self.current_user = None
            self.session_start = None
            self.save()
            return True
        return False

    def set_maintenance(self):
        """Put device in maintenance mode"""
        if self.status == 'in_use':
            self.end_session()
        self.status = 'maintenance'
        self.save()

    def set_offline(self):
        """Mark device as offline"""
        if self.status == 'in_use':
            self.end_session()
        self.status = 'offline'
        self.save()

    @property
    def session_duration(self):
        """Calculate current session duration"""
        if self.status == 'in_use' and self.session_start:
            return timezone.now() - self.session_start
        return None

class CustomerDeviceSession(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True)  # Allow null for guests
    device = models.ForeignKey(DeviceConnection, on_delete=models.CASCADE)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    cart_data = models.JSONField(default=dict)
    is_guest = models.BooleanField(default=False)

    class Meta:
        db_table = 'customer_device_sessions'

    def __str__(self):
        customer_name = self.customer.fullname if self.customer else "Dsoft-member"
        return f"{customer_name} - {self.device.device_name}"

    @property
    def duration(self):
        """Calculate session duration"""
        if self.end_time:
            return self.end_time - self.start_time
        return timezone.now() - self.start_time

    @property
    def is_active(self):
        """Check if session is currently active"""
        return self.end_time is None

class CustomerPreferences(models.Model):
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE)
    preferred_device = models.ForeignKey(
        DeviceConnection, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='preferred_by'
    )
    notification_enabled = models.BooleanField(default=True)
    promo_notification_enabled = models.BooleanField(default=True)
    personal_notification_enabled = models.BooleanField(default=True)
    last_active = models.DateTimeField(auto_now=True)
    session_count = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return f"Preferences for {self.customer.fullname}"

    def increment_session_count(self):
        """Increment the session count"""
        self.session_count += 1
        self.save()

class ChatMessage(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15)  # Store phone number for easier reference
    message = models.TextField()
    is_from_admin = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.phone_number} - {self.created_at}"

class CancelShopping(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    device = models.ForeignKey(DeviceConnection, on_delete=models.CASCADE)
    cancel_time = models.DateTimeField()
    message = models.TextField()

    class Meta:
        ordering = ['-cancel_time']

    def __str__(self):
        return f"{self.customer.fullname} - {self.cancel_time}"

class ShoppingRating(models.Model):
    RATING_CHOICES = [
        (1, '⭐'),
        (2, '⭐⭐'),
        (3, '⭐⭐⭐'),
        (4, '⭐⭐⭐⭐'),
        (5, '⭐⭐⭐⭐⭐'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    history = models.OneToOneField(History, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=RATING_CHOICES)
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.customer.fullname} - Rating: {self.get_rating_display()}"

class PaymentShopping(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True)  # Cho phép null cho khách vãng lai
    device = models.ForeignKey(DeviceConnection, on_delete=models.CASCADE) 
    payment_time = models.DateTimeField()
    status = models.CharField(max_length=50, default='pending')  # pending, completed, failed
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    message = models.TextField()

    class Meta:
        ordering = ['-payment_time']

    def __str__(self):
        return f"{self.customer.fullname if self.customer else 'Guest'} - {self.payment_time} - {self.status}"

class Notification(models.Model):
    NOTIF_TYPE_CHOICES = [
        ('personal', 'Personal'),
        ('promo', 'Promotion'),
    ]
    user = models.ForeignKey(Customer, on_delete=models.CASCADE)
    notif_type = models.CharField(max_length=20, choices=NOTIF_TYPE_CHOICES, default='personal')
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.fullname}: {self.title}"

class NotificationReadStatus(models.Model):
    """Model to track read status of notifications per customer.
    This is especially useful for promotional notifications that are sent to multiple customers."""
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, related_name='read_statuses')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='notification_statuses')
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ('notification', 'customer')
        
    def __str__(self):
        return f"{self.customer.fullname} - {self.notification.title} - {'Read' if self.is_read else 'Unread'}"
    
    def mark_as_read(self):
        """Mark the notification as read and record the timestamp."""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()

class InventoryTransaction(models.Model):
    TRANSACTION_TYPES = (
        ('addition', 'Addition'),
        ('subtraction', 'Subtraction'),
    )

    transaction_id = models.AutoField(primary_key=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='inventory_transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    quantity = models.PositiveIntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)
    reference_id = models.CharField(max_length=100, blank=True, null=True)

    def save(self, *args, **kwargs):
        # Update product quantity based on transaction type
        if self.transaction_type == 'addition':
            self.product.quantity += self.quantity
        else:  # subtraction
            self.product.quantity -= self.quantity
        self.product.save()

        # Check for low stock after the transaction
        is_low_stock = self.product.is_low_stock()
        
        # Save the transaction first to ensure we have a timestamp
        super().save(*args, **kwargs)
        
        # Create notification for low stock
        if is_low_stock:
            try:
                # Create notification for admins
                from .models import Customer, User, Notification
                admin_user = Customer.objects.filter(user__is_staff=True).first()
                
                # Only create notification if we found an admin user
                if admin_user:
                    notification = Notification.objects.create(
                        user=admin_user,  # First admin user
                        notif_type="personal",
                        title="Low Stock Alert",
                        message=f"Product '{self.product.name}' is running low on stock (Current quantity: {self.product.quantity})"
                    )
                
                    # Send FCM notification to all admin users
                    from .views import send_notification
                    admin_users = User.objects.filter(is_staff=True)
                    for user in admin_users:
                        if hasattr(user, 'customer') and user.customer.fcm_token:
                            send_notification(
                                user.customer.fcm_token,
                                "Low Stock Alert",
                                f"Product '{self.product.name}' is running low on stock (Current quantity: {self.product.quantity})",
                                {"type": "low_stock", "product_id": self.product.product_id}
                            )
                
                # Send WebSocket notification to connected clients
                try:
                    from channels.layers import get_channel_layer
                    from asgiref.sync import async_to_sync
                    import json
                    
                    channel_layer = get_channel_layer()
                    async_to_sync(channel_layer.group_send)(
                        "inventory_updates",
                        {
                            "type": "low_stock_alert",
                            "data": {
                                "type": "low_stock_alert",
                                "product_id": self.product.product_id,
                                "name": self.product.name,
                                "current_quantity": self.product.quantity,
                                "low_stock_threshold": self.product.low_stock_threshold,
                                "timestamp": self.timestamp.isoformat() if self.timestamp else timezone.now().isoformat(),
                                "message": f"Low stock alert: {self.product.name} has only {self.product.quantity} units left"
                            }
                        }
                    )
                except Exception as ws_error:
                    print(f"Error sending WebSocket notification: {ws_error}")
            except Exception as notif_error:
                print(f"Error creating notification: {notif_error}")
        
        # Send WebSocket inventory update for all transactions
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            import json
            
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                "inventory_updates",
                {
                    "type": "inventory_update",
                    "data": {
                        "type": "inventory_update",
                        "product_id": self.product.product_id,
                        "name": self.product.name,
                        "current_quantity": self.product.quantity,
                        "transaction_type": self.transaction_type,
                        "transaction_quantity": self.quantity,
                        "timestamp": self.timestamp.isoformat() if self.timestamp else timezone.now().isoformat(),
                        "message": f"Inventory updated: {self.transaction_type} of {self.quantity} units for {self.product.name}"
                    }
                }
            )
        except Exception as ws_error:
            print(f"Error sending WebSocket inventory update: {ws_error}")

    def __str__(self):
        return f"{self.transaction_type.title()} of {self.quantity} for {self.product.name}"

class ProductEditLog(models.Model):
    """Model to track product edits."""
    product_id = models.IntegerField()  # Store product ID for reference even after product deletion
    product_name = models.CharField(max_length=255)
    field_changed = models.CharField(max_length=100)  # name, price, quantity, category, description, image_url
    old_value = models.TextField(blank=True, null=True)
    new_value = models.TextField(blank=True, null=True)
    edited_by = models.CharField(max_length=100, default='admin')  # Who made the edit
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'product_edit_logs'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"Edit {self.product_name} - {self.field_changed} at {self.timestamp}"

class ProductDeletionLog(models.Model):
    """Model to track product deletions."""
    product_id = models.IntegerField()
    product_name = models.CharField(max_length=255)
    product_data = models.JSONField()  # Store complete product data
    deleted_by = models.CharField(max_length=100, default='admin')
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'product_deletion_logs'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"Deleted {self.product_name} at {self.timestamp}"

@receiver(post_save, sender=DeviceConnection)
def create_device_status(sender, instance, created, **kwargs):
    """Create DeviceStatus when a new DeviceConnection is created"""
    if created:
        DeviceStatus.objects.create(device=instance)