from rest_framework import serializers
from .models import (
    Product, 
    History, 
    DeviceConnection, 
    Customer, 
    ProductRating,
    ChatMessage,  # Add ChatMessage import
    ShoppingRating  # Add ShoppingRating import
)
import json
from django.contrib.auth.models import User
from django.db import transaction
from rest_framework.exceptions import ValidationError

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'  # Include all fields

class HistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = History
        fields = '__all__'  # Include all fields

class InvoiceSerializer(serializers.ModelSerializer):
    product_details = serializers.SerializerMethodField()

    class Meta:
        model = History
        fields = ['random_id', 'timestamp', 'total_amount', 'product_details']

    def get_product_details(self, obj):
        product_details = json.loads(obj.product)
        for product in product_details:
            product['name'] = product['name'].replace('_', ' ')
            product['unit_price'] = float(product['price'])
            product['total_price'] = float(product['price']) * int(product['quantity'])
        return product_details

class DeviceConnectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceConnection
        fields = ['device_id', 'device_name', 'device_type', 'ip_address', 
                 'is_active', 'app_running', 'last_connected', 'created_at']

class CustomerSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    profile_image = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    fullname = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = ['id', 'password', 'surname', 'firstname', 
                 'fullname', 'phone_number', 'profile_image', 
                 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def get_fullname(self, obj):
        return obj.fullname

    def validate_phone_number(self, value):
        # Basic validation and cleaning
        cleaned_number = value.strip()  # Remove whitespace
        
        # Check both User and Customer models
        user_exists = User.objects.filter(username=cleaned_number).exists()
        customer_exists = Customer.objects.filter(phone_number=cleaned_number).exists()
        
        print(f"Checking existence - User: {user_exists}, Customer: {customer_exists}")
        
        if user_exists or customer_exists:
            # Try to clean up any orphaned records
            if user_exists:
                try:
                    user = User.objects.get(username=cleaned_number)
                    if not hasattr(user, 'customer'):
                        print(f"Found orphaned user, deleting: {user.username}")
                        user.delete()
                    else:
                        raise ValidationError("A user with this phone number already exists.")
                except User.DoesNotExist:
                    pass
            
            if customer_exists:
                try:
                    customer = Customer.objects.get(phone_number=cleaned_number)
                    print(f"Found existing customer: {customer.fullname}")
                    raise ValidationError("A customer with this phone number already exists.")
                except Customer.DoesNotExist:
                    pass

        return cleaned_number

    def validate_profile_image(self, value):
        if not value:
            return value
        if not value.startswith('data:image'):
            raise ValidationError("Invalid image format")
        # Validate base64 format
        try:
            parts = value.split(';base64,')
            if len(parts) != 2:
                raise ValidationError("Invalid image data format")
        except Exception:
            raise ValidationError("Invalid image data")
        return value

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if representation['profile_image'] and representation['profile_image'].startswith('data:image'):
            # Extract image type and actual base64 data
            parts = representation['profile_image'].split(';base64,')
            if len(parts) == 2:
                image_type = parts[0].split(':')[1]
                base64_data = parts[1]
                # Create shorter format
                representation['profile_image'] = {
                    'type': image_type,
                    'data': base64_data
                }
        return representation

    def create(self, validated_data):
        try:
            with transaction.atomic():
                phone_number = validated_data.get('phone_number')
                password = validated_data.pop('password')
                
                # Double-check before creating
                if User.objects.filter(username=phone_number).exists():
                    raise ValidationError("Username already exists")
                if Customer.objects.filter(phone_number=phone_number).exists():
                    raise ValidationError("Phone number already exists")
                
                # Create user
                user = User.objects.create_user(
                    username=phone_number,
                    password=password
                )
                
                # Create customer
                customer = Customer.objects.create(
                    user=user,
                    **validated_data
                )
                return customer
                
        except Exception as e:
            print(f"Error in create: {str(e)}")
            if 'user' in locals():
                user.delete()
            raise ValidationError(str(e))  # Fixed: Added missing closing parenthesis

class ProductRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductRating
        fields = ['product_name', 'star', 'created_at']

class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['id', 'phone_number', 'message', 'is_from_admin', 'created_at', 'read']
        read_only_fields = ['id', 'created_at']

class ShoppingRatingSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(write_only=True)
    random_id = serializers.CharField(write_only=True)
    
    class Meta:
        model = ShoppingRating
        fields = ['phone_number', 'random_id', 'rating', 'comment', 'created_at']
        read_only_fields = ['created_at']

    def create(self, validated_data):
        phone_number = validated_data.pop('phone_number')
        random_id = validated_data.pop('random_id')
        
        try:
            customer = Customer.objects.get(user__username=phone_number)
            history = History.objects.get(random_id=random_id)
            
            # Create or update the rating
            rating, created = ShoppingRating.objects.update_or_create(
                customer=customer,
                history=history,
                defaults={
                    'rating': validated_data.get('rating'),
                    'comment': validated_data.get('comment', '')
                }
            )
            return rating
            
        except Customer.DoesNotExist:
            raise serializers.ValidationError({'phone_number': 'Customer not found'})
        except History.DoesNotExist:
            raise serializers.ValidationError({'random_id': 'History not found'})
