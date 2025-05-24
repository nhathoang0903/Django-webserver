from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from rest_framework import generics
from .models import (
    CustomerPreferences,
    InventoryTransaction,
    Product, 
    History, 
    User, 
    SuperUserInfo, 
    DeviceConnection, 
    Customer,
    CustomerHistory,
    ProductRating, 
    ChatMessage,
    CancelShopping,
    ShoppingRating, 
    PaymentShopping,
    Notification,
    ProductEditLog,
    ProductDeletionLog
)
from .models import SuperUserInfo
from .serializers import (
    ProductSerializer, 
    HistorySerializer,
    ProductRatingSerializer, 
    ChatMessageSerializer
)
from django.core.paginator import Paginator
from .forms import ProductForm
from django.shortcuts import render
import json
from django.db.models import Sum, Count, Avg, Q, F, Value, When, Case, CharField, Min, Max, OuterRef, Subquery, ExpressionWrapper, DurationField
from django.db.models.functions import TruncDate, TruncHour, TruncMonth, ExtractHour, ExtractWeekDay
from rest_framework import status, generics
from datetime import datetime, timedelta
from django.utils.timezone import now, timezone
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework import generics
from rest_framework.generics import ListCreateAPIView
from rest_framework.response import Response
from rest_framework import status
import time
from rest_framework.response import Response
from rest_framework import generics
from django.http import HttpResponse
from django.template.loader import render_to_string
import pdfkit
from xhtml2pdf import pisa
from io import BytesIO
from .serializers import InvoiceSerializer
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework import generics, status
from rest_framework.response import Response
from .models import DeviceConnection
from .serializers import DeviceConnectionSerializer
from django.conf import settings
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from .serializers import CustomerSerializer
from .models import Customer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.decorators import authentication_classes, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.utils import timezone
import pytz
from django.db import transaction  
from django.db.models.functions import Concat
from .models import Customer, DeviceStatus, CustomerDeviceSession, Notification, NotificationReadStatus, CustomerPreferences
from django.http import Http404
from django.core.cache import cache 
import firebase_admin
from firebase_admin import messaging, credentials, initialize_app
import os
from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm
import requests
import re
from .cdn import upload_image
from datetime import timedelta, datetime

from cartv2 import models
from django.db import models
from django.db.models import F, Q
import random

# Hàm gửi notification tổng quát. Kiểm tra cài đặt thông báo trước khi gửi.
def send_notification(token, title, body, extra_data=None):
    try:
        # Tìm người dùng dựa vào token FCM 
        customer = Customer.objects.filter(fcm_token=token).first()
        if not customer:
            print(f"Warning: No customer found with token {token[:20]}...")
            return {"error": "Customer not found"}
        
        # Tạo thông báo trong DB (luôn lưu vào DB bất kể cài đặt)
        notification = Notification.objects.create(
            user=customer,
            notif_type="personal",  # Mặc định là personal
            title=title,
            message=body
        )
        
        # Kiểm tra tùy chọn thông báo của người dùng
        preferences, created = CustomerPreferences.objects.get_or_create(
            customer=customer,
            defaults={
                'notification_enabled': True,
                'promo_notification_enabled': True,
                'personal_notification_enabled': True
            }
        )
        
        # Chỉ gửi push notification nếu đã bật thông báo cá nhân
        if preferences.personal_notification_enabled:
            return send_fcm_legacy(token, title, body, extra_data)
        else:
            print(f"Not sending FCM to {customer.user.username}: personal notifications disabled")
            return {"status": "skipped", "reason": "personal notifications disabled"}
    except Exception as e:
        print(f"Error in send_notification: {str(e)}")
        return {"error": str(e)}

# Initialize Firebase Admin
# cert_path = os.path.join(settings.BASE_DIR, 'cartv2', 'json', 'firebase-service-account.json')
# cred = credentials.Certificate(cert_path)
# if not firebase_admin._apps:
#     initialize_app(cred)

# Sử dụng phương thức FCM HTTP v1 API với OAuth 2.0 Access Token
def send_fcm_v1(token, title, body):
    try:
        # Sử dụng Firebase Admin SDK trực tiếp thay vì HTTP API
        from firebase_admin import messaging
        
        # Đảm bảo thông báo hiển thị khi app đang chạy
        android_config = messaging.AndroidConfig(
            priority='high',
            notification=messaging.AndroidNotification(
                title=title,
                body=body,
                icon='notification_icon',
                color='#f45342',
                sound='default',
                channel_id='high_importance_channel',  # Thêm channel_id để hiển thị thông báo nổi
                default_sound=True,
                default_vibrate_timings=True,
                visibility='public'  # Hiển thị nội dung trên màn hình khóa
            ),
            direct_boot_ok=True,
        )
        
        # Cấu hình cho iOS
        apns_config = messaging.APNSConfig(
            headers={
                'apns-priority': '10',  # Priority cao
            },
            payload=messaging.APNSPayload(
                aps=messaging.Aps(
                    alert=messaging.ApsAlert(
                        title=title,
                        body=body,
                    ),
                    sound='default',
                    badge=1,
                    content_available=True  # Cho phép xử lý khi app đang chạy
                ),
            ),
        )
        
        # Dữ liệu để Flutter xử lý thông báo - Quan trọng cho cả khi app đóng và mở
        data = {
            'click_action': 'FLUTTER_NOTIFICATION_CLICK',
            'id': '1',
            'status': 'done',
            'title': title,  # Duplicate title in data payload for handling in Flutter
            'body': body,    # Duplicate body in data payload for handling in Flutter
            'foreground': 'true',  # Đánh dấu hiển thị khi app đang mở
            'priority': 'high',
            'importance': 'high'
        }
        
        # Log để debug
        print(f"Sending FCM notification via Admin SDK to {token[:20]}...")
        
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            android=android_config,
            apns=apns_config,
            data=data,
            token=token,
        )
        
        # Gửi thông báo
        try:
            response = messaging.send(message)
            print(f"Firebase Admin SDK response: {response}")
            return {"success": True, "message_id": response}
        except Exception as e:
            print(f"Firebase Admin SDK error: {e}")
            error_message = str(e)
            if "SenderId mismatch" in error_message:
                print(f"SenderId mismatch error - Token: {token[:20]}... may have been generated with a different Firebase project")
                return {"error": "SenderId mismatch", "details": "Firebase configuration mismatch between server and app"}
            raise e
    except Exception as e:
        print(f"FCM v1 error: {e}")
        return {"error": str(e)}

# Sử dụng phương thức FCM Legacy HTTP v1 API
def send_fcm_legacy(token, title, body, extra_data=None):
    try:
        from firebase_admin import messaging
        
        print(f"Sending FCM notification via Admin SDK to {token[:20]}...")
        
        # Configure Android notification settings
        android_config = messaging.AndroidConfig(
            priority='high',
            notification=messaging.AndroidNotification(
                title=title, body=body, icon='notification_icon',
                color='#f45342', sound='default', 
                channel_id='high_importance_channel',
                default_sound=True, default_vibrate_timings=True,
                visibility='public'
            ),
            direct_boot_ok=True,
        )
        
        # Configure iOS notification settings
        apns_config = messaging.APNSConfig(
            headers={'apns-priority': '10'},
            payload=messaging.APNSPayload(
                aps=messaging.Aps(
                    alert=messaging.ApsAlert(title=title, body=body),
                    sound='default', badge=1, content_available=True
                ),
            ),
        )
        
        # Base data for Flutter notification handling
        data = {
            'click_action': 'FLUTTER_NOTIFICATION_CLICK',
            'id': '1', 'status': 'done', 'title': title, 'body': body,
            'foreground': 'true', 'priority': 'high', 'importance': 'high'
        }
        
        # Merge additional data if provided
        if extra_data and isinstance(extra_data, dict):
            data.update(extra_data)
        
        # Create the message with all configurations
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            android=android_config, apns=apns_config, data=data, token=token,
        )
        
        # Send the notification and handle response
        try:
            response = messaging.send(message)
            print(f"Firebase Admin SDK response: {response}")
            return {"success": True, "message_id": response}
        except Exception as e:
            print(f"Firebase Admin SDK error: {e}")
            error_message = str(e)
            if "SenderId mismatch" in error_message:
                print(f"SenderId mismatch error - Token: {token[:20]}... may have been generated with a different Firebase project")
                return {"error": "SenderId mismatch", "details": "Firebase configuration mismatch between server and app"}
            return {"error": str(e)}
    except Exception as e:
        print(f"FCM error: {str(e)}")
        return {"error": str(e)}

def format_vietnam_timestamp(timestamp):
    """Format a datetime object to 'DD/MM/YYYY HH:MM' for Vietnam timezone."""
    vietnam_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    vietnam_time = timestamp.astimezone(vietnam_tz)
    return vietnam_time.strftime("%d/%m/%Y %H:%M")

def create_superuser(username, email, password):
    user = User.objects.create_superuser(username=username, email=email, password=password)
    superuser_info = SuperUserInfo.objects.create(user=user, email=email)
    return superuser_info
@login_required
def users_view(request):
    # Retrieve all superuser information
    superusers = SuperUserInfo.objects.all()
    return render(request, 'users.html', {'superusers': superusers})
def login_view(request):
    # Check if there's a 'next' parameter in the referrer URL
    referrer = request.META.get('HTTP_REFERER', '')
    next_url = request.GET.get('next', '')
    
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                # Get the redirect URL from POST data or fall back to dashboard
                redirect_to = request.POST.get('next_url', 'dashboard')
                return redirect(redirect_to)
    else:
        form = AuthenticationForm()
    
    return render(request, 'login.html', {
        'form': form,
        'next_url': next_url,
        'show_auth_dialog': bool(next_url or 'login' not in referrer)
    })
#dashboard view
@login_required
def dashboard_view(request):
    # Existing stats
    total_products = Product.objects.count()
    total_sales = History.objects.aggregate(total=Sum('total_amount'))['total'] or 0
    purchase_history = History.objects.order_by('-timestamp')[:5]

    # Format product names in purchase history
    for history in purchase_history:
        try:
            product_details = json.loads(history.product)
            for product in product_details:
                product['name'] = product['name'].replace('_', ' ')
            history.product_details = product_details
        except json.JSONDecodeError:
            history.product_details = []

    # Calculate chart data - Group total sales by day
    daily_revenue = (
        History.objects
        .annotate(date=TruncDate('timestamp'))
        .values('date')
        .annotate(total_amount=Sum('total_amount'))
        .order_by('date')
    )

    # Convert date objects to strings for JSON serialization
    chart_data = json.dumps([
        {
            'date': entry['date'].strftime('%Y-%m-%d'),
            'total_amount': float(entry['total_amount'])
        }
        for entry in daily_revenue
    ])

    # Add group by clause to avoid duplicates
    recent_customers = Customer.objects.annotate(
        total_spent=Subquery(
            CustomerHistory.objects.filter(
                customer=OuterRef('pk')
            ).values('customer').annotate(
                total=Sum('history__total_amount')
            ).values('total')[:1]
        )
    ).order_by('-created_at')[:5]

    # Format product names in purchase history
    for history in purchase_history:
        try:
            product_details = json.loads(history.product)
            for product in product_details:
                product['name'] = product['name'].replace('_', ' ')
            history.product_details = product_details
        except json.JSONDecodeError:
            history.product_details = []

    # New customer stats
    today = timezone.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    
    total_customers = CustomerHistory.objects.filter(customer__isnull=False).values('customer').distinct().count()
    registered_customers = Customer.objects.count()
    new_customers_today = Customer.objects.filter(created_at__date=today).count()
    new_customers_week = Customer.objects.filter(created_at__date__gte=start_of_week).count()
    active_customers = CustomerHistory.objects.filter(
        history__timestamp__date__gte=start_of_week
    ).values('customer').distinct().count()
    
    # Today's stats
    today_sales = History.objects.filter(
        timestamp__date=today
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    today_orders = History.objects.filter(timestamp__date=today).count()

    # Best Selling Products - Updated calculation
    today = timezone.now().date()
    today_histories = History.objects.filter(timestamp__date=today)
    
    product_stats = {}
    for history in today_histories:
        try:
            products = json.loads(history.product)
            for product in products:
                name = product['name'].replace('_', ' ')  # Format name by replacing underscores
                quantity = int(product['quantity'])
                price = float(product['price'])
                revenue = quantity * price
                
                if name in product_stats:
                    product_stats[name]['quantity'] += quantity
                    product_stats[name]['revenue'] += revenue
                else:
                    product_stats[name] = {
                        'name': name,
                        'quantity': quantity,
                        'revenue': revenue,
                        'category': product.get('category', 'N/A')
                    }
        except (json.JSONDecodeError, KeyError, ValueError):
            continue

    best_sellers = sorted(
        product_stats.values(),
        key=lambda x: x['quantity'],
        reverse=True
    )[:5]

    # Peak Hours Analysis - Updated to use random_id instead of id
    peak_hours = History.objects.filter(
        timestamp__date=today
    ).annotate(
        hour=ExtractHour('timestamp')
    ).values('hour').annotate(
        count=Count('random_id')  # Changed from Count('id') to Count('random_id')
    ).order_by('-count')[:4]

    total_visits = sum(h['count'] for h in peak_hours)
    peak_hours = [{
        'hour': h['hour'],
        'count': h['count'],
        'percentage': (h['count'] / total_visits * 100) if total_visits > 0 else 0,
        'color': ['primary', 'success', 'info', 'warning'][i]
    } for i, h in enumerate(peak_hours)]

    # Customer Metrics
    total_bills = History.objects.filter(timestamp__date=today).count()
    avg_bill_value = today_sales / total_bills if total_bills > 0 else 0
    
    repeat_customers = CustomerHistory.objects.filter(
        customer__isnull=False
    ).values('customer').annotate(
        visit_count=Count('id')
    ).filter(visit_count__gt=1).count()

    # Fix avg_items calculation
    avg_items_query = History.objects.filter(
        timestamp__date=today
    ).annotate(
        items=Count('random_id')  # Changed from Count('product') to Count('random_id')
    ).aggregate(avg=Avg('items'))
    avg_items = avg_items_query['avg'] or 0

    # Customer Demographics
    total_customers = CustomerHistory.objects.count()
    registered_count = CustomerHistory.objects.filter(customer__isnull=False).count()
    
    registered_percentage = (registered_count / total_customers * 100) if total_customers > 0 else 0
    guest_percentage = 100 - registered_percentage

    # Loyalty Metrics
    loyal_customers = CustomerHistory.objects.filter(
        customer__isnull=False
    ).values('customer').annotate(
        visit_count=Count('id')
    ).filter(visit_count__gte=3).count()

    last_month = today - timedelta(days=30)
    active_last_month = CustomerHistory.objects.filter(
        customer__isnull=False,
        history__timestamp__gte=last_month
    ).values('customer').distinct().count()
    
    customer_retention = (active_last_month / registered_customers * 100) if registered_customers > 0 else 0

    context = {
        'total_products': total_products,
        'total_sales': total_sales,
        'total_customers': total_customers,
        'registered_customers': registered_customers,
        'purchase_history': purchase_history,
        'chart_data': chart_data,
        'today_sales': today_sales,
        'today_orders': today_orders,
        'new_customers_today': new_customers_today,
        'new_customers_week': new_customers_week,
        'active_customers': active_customers,
        'recent_customers': recent_customers,
        'best_sellers': best_sellers,
        'peak_hours': peak_hours,
        'avg_bill_value': int(avg_bill_value),
        'repeat_customers': repeat_customers,
        'avg_items_per_bill': round(avg_items, 1),
        'registered_percentage': int(registered_percentage),
        'guest_percentage': int(guest_percentage),
        'loyal_customers': loyal_customers,
        'customer_retention': int(customer_retention),
    }
    
    # NEW FEATURES - Calculate additional statistics
    weekday = today.weekday()
    week_start = today - timedelta(days=weekday)
    week_so_far_revenue = History.objects.filter(
        timestamp__date__gte=week_start, 
        timestamp__date__lte=today
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    days_passed = weekday + 1
    predicted_week_revenue = (week_so_far_revenue / days_passed) * 7 if days_passed > 0 else 0
    
    # Get transaction times
    sessions = CustomerDeviceSession.objects.filter(
        end_time__isnull=False
    ).annotate(
        session_duration=ExpressionWrapper(F('end_time') - F('start_time'), output_field=DurationField())
    )
    
    fastest = sessions.order_by('session_duration').first()
    slowest = sessions.order_by('-session_duration').first()
    
    # Calculate time in minutes if sessions exist
    fastest_time = 0
    slowest_time = 0
    
    if fastest and hasattr(fastest, 'session_duration'):
        fastest_time = fastest.session_duration.total_seconds() / 60
        
    if slowest and hasattr(slowest, 'session_duration'):
        slowest_time = slowest.session_duration.total_seconds() / 60
    
    # Revenue warning
    last_week_start = week_start - timedelta(days=7)
    last_week_end = week_start - timedelta(days=1)
    last_week_avg = History.objects.filter(
        timestamp__date__gte=last_week_start,
        timestamp__date__lte=last_week_end
    ).annotate(day=TruncDate('timestamp')).values('day').annotate(
        daily=Sum('total_amount')
    ).aggregate(avg=Avg('daily'))['avg'] or 0
    
    # Convert to float before comparison to avoid decimal vs float type mismatch
    last_week_avg_float = float(last_week_avg)
    revenue_warning = float(today_sales) < (last_week_avg_float * 0.7)
    revenue_percentage = (float(today_sales) / last_week_avg_float * 100) if last_week_avg_float > 0 else 0
    
    # Low stock products with formatted names
    low_stock_products = []
    for product in Product.objects.filter(quantity__lte=10).order_by('quantity')[:10]:
        low_stock_products.append({
            'name': product.name.replace('_', ' '),
            'category': product.category,
            'quantity': product.quantity,
            'price': float(product.price)
        })
    
    # Failed/Invalid Transactions using CancelShopping
    cancel_history = CancelShopping.objects.order_by('-cancel_time')[:5]
    failed_txns = [
        {
            'id': f"C-{item.id}",
            'timestamp': format_vietnam_timestamp(item.cancel_time),
            'error': "Shopping Cancelled",
            'total_amount': 0,
            'customer': item.customer.fullname
        } for item in cancel_history
    ]
    
    # Add to context
    context.update({
        'predicted_week_revenue': int(predicted_week_revenue),
        'fastest_transaction_time': round(fastest_time, 1),
        'slowest_transaction_time': round(slowest_time, 1),
        'revenue_warning': revenue_warning,
        'revenue_percentage': int(revenue_percentage),
        'low_stock_products': low_stock_products,
        'failed_transactions': failed_txns,
    })
    
    # Calculate additional advanced statistics
    
    # Deadstock Products - not sold in over 30 days
    thirty_days_ago = today - timedelta(days=30)
    sold_product_names = set()
    
    # Get products sold in last 30 days
    for history in History.objects.filter(timestamp__date__gte=thirty_days_ago):
        try:
            products = json.loads(history.product)
            for product in products:
                sold_product_names.add(product['name'])
        except (json.JSONDecodeError, KeyError):
            continue
    
    # Find products not in the sold list
    deadstock_products = []
    for product in Product.objects.all():
        if product.name not in sold_product_names:
            deadstock_products.append({
                'id': product.product_id,
                'name': product.name.replace('_', ' '),  # Format name
                'quantity': product.quantity,
                'days_without_sale': 30,
                'price': float(product.price)
            })
    
    # Price adjustment suggestions
    week_ago = today - timedelta(days=7)
    product_velocity = {}
    
    # Calculate sales velocity
    for history in History.objects.filter(timestamp__date__gte=week_ago):
        try:
            products = json.loads(history.product)
            for product in products:
                name = product['name']
                quantity = int(product['quantity'])
                
                if name in product_velocity:
                    product_velocity[name] += quantity
                else:
                    product_velocity[name] = quantity
        except (json.JSONDecodeError, KeyError, ValueError):
            continue
    
    # Generate pricing suggestions
    pricing_suggestions = []
    for product in Product.objects.all():
        velocity = product_velocity.get(product.name, 0)
        
        # Define thresholds
        if velocity > 20:
            suggestion = "Increase price by 5-10%"
            action = "increase"
        elif velocity > 10:
            suggestion = "Maintain price"
            action = "maintain"
        elif velocity >= 1:
            suggestion = "Consider 5% discount"
            action = "discount_small"
        else:
            suggestion = "Consider 10-15% discount"
            action = "discount_large"
        
        pricing_suggestions.append({
            'name': product.name.replace('_', ' '),  # Format name
            'current_price': float(product.price),
            'weekly_sales': velocity,
            'suggestion': suggestion,
            'action': action
        })
    
    # Revenue by category
    category_revenue = {}
    
    # Create a mapping of product names to their categories from the Product table
    product_categories = {product.name: product.category for product in Product.objects.all()}
    
    for history in History.objects.filter(timestamp__date__gte=thirty_days_ago):
        try:
            products = json.loads(history.product)
            for item in products:
                # Get the raw product name and look up its proper category
                product_name = item.get('name', '')
                
                # Look up the product's true category from our mapping
                category = product_categories.get(product_name, 'Uncategorized')
                
                quantity = int(item.get('quantity', 0))
                price = float(item.get('price', 0))
                revenue = quantity * price
                
                if category in category_revenue:
                    category_revenue[category]['revenue'] += revenue
                    category_revenue[category]['quantity'] += quantity
                else:
                    category_revenue[category] = {
                        'category': category,
                        'revenue': revenue,
                        'quantity': quantity
                    }
        except (json.JSONDecodeError, KeyError, ValueError):
            continue
    
    # Golden hour analysis
    hourly_sales = History.objects.filter(
        timestamp__date__gte=week_ago
    ).annotate(
        hour=ExtractHour('timestamp')
    ).values('hour').annotate(
        total_amount=Sum('total_amount'),
        count=Count('random_id')
    ).order_by('hour')
    
    golden_hours = []
    for i in range(24):
        hour_data = next((h for h in hourly_sales if h['hour'] == i), None)
        if hour_data:
            golden_hours.append({
                'hour': i,
                'start_time': f"{i:02d}:00",
                'end_time': f"{(i+1)%24:02d}:00",
                'sales_count': hour_data['count'],
                'revenue': float(hour_data['total_amount']),
                'avg_transaction': float(hour_data['total_amount']) / hour_data['count'] if hour_data['count'] > 0 else 0
            })
        else:
            golden_hours.append({
                'hour': i,
                'start_time': f"{i:02d}:00",
                'end_time': f"{(i+1)%24:02d}:00",
                'sales_count': 0,
                'revenue': 0,
                'avg_transaction': 0
            })
    
    # Add additional data to context
    context.update({
        'deadstock_products': sorted(deadstock_products, key=lambda x: x['quantity'], reverse=True)[:5],
        'pricing_suggestions': sorted(pricing_suggestions, key=lambda x: x['weekly_sales'], reverse=True)[:5],
        'category_stats': sorted(category_revenue.values(), key=lambda x: x['revenue'], reverse=True)[:5],
        'golden_hours': sorted(golden_hours, key=lambda x: x['revenue'], reverse=True)[:5],
    })
    
    return render(request, 'dashboard.html', context)

def product_list_view(request):
    # Get sort parameter from URL
    sort_param = request.GET.get('sort', 'name')
    
    # Determine ordering based on sort parameter
    if sort_param == 'price-asc':
        ordering = 'price'
    elif sort_param == 'price-desc':
        ordering = '-price'
    elif sort_param == 'stock':
        ordering = '-quantity'
    elif sort_param == 'rating-desc' or sort_param == 'rating-asc':
        # We'll handle rating sorting separately since it requires annotation
        ordering = 'name'  # Default ordering, will be overridden
    else:
        ordering = 'name'
    
    # Get all products
    products = Product.objects.all()
    
    # Calculate items per page based on total count
    total_products_count = products.count()
    items_per_page = 8  # Cố định 8 sản phẩm mỗi trang
    
    # Check if this is an AJAX request for all products
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.GET.get('all_products'):
        # Special handling for rating sort in AJAX request
        if sort_param == 'rating-desc' or sort_param == 'rating-asc':
            # Get all products with their average rating
            products_with_ratings = []
            for product in products:
                ratings = ProductRating.objects.filter(product_name=product.name)
                avg_rating = ratings.aggregate(Avg('star'))['star__avg']
                rating_count = ratings.count()
                
                # Create a sort key that separates products into three categories:
                # 1. Products with rating > 0
                # 2. Products with rating = 0 (but have ratings)
                # 3. Products with no ratings at all
                if avg_rating is not None and avg_rating > 0:
                    rating_category = 1  # Has positive rating
                elif rating_count > 0:
                    rating_category = 2  # Has rating but average is 0
                else:
                    rating_category = 3  # No ratings at all
                    
                # Store tuple with all necessary data for sorting
                products_with_ratings.append((
                    product,                  # The product object
                    rating_category,          # Category (1,2,3)
                    avg_rating or 0,          # The rating value (or 0 if None)
                    rating_count,             # Number of ratings
                    product.name              # Product name for alphabetical sorting
                ))
            
            # Sort products based on the sort direction
            if sort_param == 'rating-desc':
                # High to low: lowest category first, then highest rating, then alphabetical
                products_with_ratings.sort(key=lambda x: (
                    x[1],                    # Category (1=best, 3=worst)
                    -(x[2] or 0),            # Negative rating for desc order
                    x[4]                     # Name for alphabetical tiebreaker
                ))
            else:  # rating-asc
                # Low to high: highest category first, then lowest rating, then alphabetical
                products_with_ratings.sort(key=lambda x: (
                    -x[1],                   # Negative category (so 3=best, 1=worst)
                    x[2] or 0,               # Rating
                    x[4]                     # Name for alphabetical tiebreaker
                ))
            
            # Extract just the products in the correct order
            products = [item[0] for item in products_with_ratings]
        else:
            # Regular ordering
            products = products.order_by(ordering)
            
        # Return all products as JSON
        products_data = []
        for product in products:
            # Get average rating
            ratings = ProductRating.objects.filter(product_name=product.name)
            avg_rating = ratings.aggregate(Avg('star'))['star__avg']
            rating_count = ratings.count()
            
            products_data.append({
                'product_id': product.product_id,
                'name': product.name,
                'price': float(product.price),
                'quantity': product.quantity,
                'category': product.category,
                'description': product.description,
                'image_url': product.image_url,
                'average_rating': round(float(avg_rating), 1) if avg_rating else 0,
                'total_ratings': rating_count
            })
        return JsonResponse({'products': products_data})
    
    # For regular requests
    # Special handling for rating sort
    if sort_param == 'rating-desc' or sort_param == 'rating-asc':
        # Get all products with their average rating
        products_with_ratings = []
        for product in products:
            ratings = ProductRating.objects.filter(product_name=product.name)
            avg_rating = ratings.aggregate(Avg('star'))['star__avg']
            rating_count = ratings.count()
            
            # Create a sort key that separates products into three categories:
            # 1. Products with rating > 0
            # 2. Products with rating = 0 (but have ratings)
            # 3. Products with no ratings at all
            if avg_rating is not None and avg_rating > 0:
                rating_category = 1  # Has positive rating
            elif rating_count > 0:
                rating_category = 2  # Has rating but average is 0
            else:
                rating_category = 3  # No ratings at all
                
            # Store tuple with all necessary data for sorting
            products_with_ratings.append((
                product,                  # The product object
                rating_category,          # Category (1,2,3)
                avg_rating or 0,          # The rating value (or 0 if None)
                rating_count,             # Number of ratings
                product.name              # Product name for alphabetical sorting
            ))
        
        # Sort products based on the sort direction
        if sort_param == 'rating-desc':
            # High to low: lowest category first, then highest rating, then alphabetical
            products_with_ratings.sort(key=lambda x: (
                x[1],                    # Category (1=best, 3=worst)
                -(x[2] or 0),            # Negative rating for desc order
                x[4]                     # Name for alphabetical tiebreaker
            ))
        else:  # rating-asc
            # Low to high: highest category first, then lowest rating, then alphabetical
            products_with_ratings.sort(key=lambda x: (
                -x[1],                   # Negative category (so 3=best, 1=worst)
                x[2] or 0,               # Rating
                x[4]                     # Name for alphabetical tiebreaker
            ))
        
        # Extract just the products in the correct order
        ordered_products = [item[0] for item in products_with_ratings]
        
        # Create paginator with pre-sorted products and dynamic page size
        paginator = Paginator(ordered_products, items_per_page)  # Dynamic number of products per page
    else:
        # Regular ordering and pagination
        products = products.order_by(ordering)
        paginator = Paginator(products, items_per_page)  # Dynamic number of products per page
    
    page = request.GET.get('page')
    products = paginator.get_page(page)
    
    # Get inventory transactions for each product
    for product in products:
        # Get recent inventory transactions
        recent_transactions = InventoryTransaction.objects.filter(
            product=product
        ).order_by('-timestamp')[:5]
        
        # Get average rating
        ratings = ProductRating.objects.filter(product_name=product.name)
        product.avg_rating = ratings.aggregate(Avg('star'))['star__avg'] or 0
        product.rating_count = ratings.count()
        
        # Add inventory data to product object as a custom attribute
        # This avoids the reverse relation issue
        product.recent_inventory_transactions = recent_transactions
    
    context = {
        'products': products,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': products,
        'current_sort': sort_param,  # Pass the current sort to the template
        'total_products_count': total_products_count,  # Pass total count to template
        'items_per_page': items_per_page,  # Pass items per page to template
        'all_products': Product.objects.all().order_by('name'),  # Thêm tất cả sản phẩm cho bulk modal
    }
    
    return render(request, 'product_list.html', context)

def add_product(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        quantity = request.POST.get('quantity')
        price = request.POST.get('price')
        category = request.POST.get('category')
        

        # Create a new product instance
        new_product = Product(
            description=name,
            quantity=quantity,
            price=price,
            category=category
        )
        new_product.save()
        
        messages.success(request, "Product added successfully!")  # display success message
        return redirect('product_list')  # Redirect to product list page

    return render(request, 'product_list.html')
def edit_product(request, product_id):
    # Get the product instance or return 404
    product = get_object_or_404(Product, product_id=product_id)
    
    if request.method == 'POST':
        print(f"[DEBUG] Starting edit for product {product_id}")
        # Store old values BEFORE form validation
        old_values = {
            'name': product.name,
            'quantity': str(product.quantity),
            'price': str(product.price),
            'category': product.category,
            'description': product.description or '',
            'image_url': product.image_url or ''
        }
        print(f"[DEBUG] Old values: {old_values}")
        
        form = ProductForm(request.POST, instance=product)
        
        if form.is_valid():
            print(f"[DEBUG] Form is valid")
            # Handle image upload if present
            if 'image' in request.FILES:
                try:
                    # Upload image and get URL
                    image_url = upload_image(request.FILES['image'])
                    # Update the form's image_url field
                    form.instance.image_url = image_url
                except Exception as e:
                    print(f"[ERROR] Failed to upload image: {e}")
                    messages.error(request, "Failed to upload image. Please try again.")
                    return redirect('product_list')
            
            # Save the form
            updated_product = form.save()
            
            # Get the username of the editor (from request.user or default to 'admin')
            edited_by = request.user.username if request.user.is_authenticated else 'admin'
            
            # Track changes and create log entries
            new_values = {
                'name': updated_product.name,
                'quantity': str(updated_product.quantity),
                'price': str(updated_product.price),
                'category': updated_product.category,
                'description': updated_product.description or '',
                'image_url': updated_product.image_url or ''
            }
            print(f"[DEBUG] New values: {new_values}")
            
            # Compare old and new values and create log entries for changes
            changes_found = 0
            for field, old_value in old_values.items():
                new_value = new_values[field]
                # Convert both values to strings for comparison
                old_str = str(old_value).strip()
                new_str = str(new_value).strip()
                
                if old_str != new_str:
                    print(f"[DEBUG] Change detected in {field}: '{old_str}' -> '{new_str}'")
                    try:
                        ProductEditLog.objects.create(
                            product_id=updated_product.product_id,
                            product_name=updated_product.name,
                            field_changed=field,
                            old_value=old_str,
                            new_value=new_str,
                            edited_by=edited_by
                        )
                        changes_found += 1
                        print(f"[DEBUG] Log entry created for {field}")
                    except Exception as e:
                        print(f"[ERROR] Failed to create log entry: {e}")
                else:
                    print(f"[DEBUG] No change in {field}: '{old_str}' == '{new_str}'")
            
            print(f"[DEBUG] Total changes logged: {changes_found}")
            messages.success(request, f"Product '{updated_product.name}' updated successfully!")
            return redirect('product_list')
        else:
            print(f"[DEBUG] Form is not valid. Errors: {form.errors}")
    else:
        form = ProductForm(instance=product)
    
    # Get inventory transactions for this product
    inventory_transactions = InventoryTransaction.objects.filter(
        product=product
    ).order_by('-timestamp')[:10]  # Get the 10 most recent transactions
    
    context = {
        'product': product,
        'form': form,
        'inventory_transactions': inventory_transactions
    }
    
    return render(request, 'edit_product.html', context)
def delete_product(request, product_id):
    # Get the product instance or return 404
    product = get_object_or_404(Product, product_id=product_id)
    
    if request.method == 'POST':
        # Store product data before deletion for logging
        product_data = {
            'product_id': product.product_id,
            'name': product.name,
            'price': float(product.price),
            'quantity': product.quantity,
            'category': product.category,
            'description': product.description,
            'image_url': product.image_url
        }
        
        # Get the username of the deleter
        deleted_by = request.user.username if request.user.is_authenticated else 'admin'
        
        # Create deletion log
        ProductDeletionLog.objects.create(
            product_id=product.product_id,
            product_name=product.name,
            product_data=product_data,
            deleted_by=deleted_by
        )
        
        # Delete the product
        product.delete()
        
        messages.success(request, f"Product '{product.name}' has been deleted successfully!")
        return redirect('product_list')
    
    return redirect('product_list')

@login_required
def add_stock_note(request, product_id):
    """Add a note to the stock history for a product."""
    product = get_object_or_404(Product, product_id=product_id)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                transaction_type = request.POST.get('transaction_type')
                quantity = int(request.POST.get('quantity', 0))
                notes = request.POST.get('notes', '')
                reference_id = request.POST.get('reference_id', '')
                
                # Re-fetch product with select_for_update to prevent race conditions
                product = Product.objects.select_for_update().get(pk=product_id)
                
                # Handle different transaction types
                if transaction_type == 'note':
                    # Create a note without changing stock
                    InventoryTransaction.objects.create(
                        product=product,
                        transaction_type='addition',  # Default to addition
                        quantity=0,  # No change in quantity
                        notes=f"NOTE: {notes}",
                        reference_id=reference_id if reference_id else None
                    )
                else:
                    # Create actual transaction that affects stock
                    InventoryTransaction.objects.create(
                        product=product,
                        transaction_type=transaction_type,
                        quantity=quantity,
                        notes=notes,
                        reference_id=reference_id if reference_id else None
                    )
                
                messages.success(request, "Stock note added successfully.")
        except Exception as e:
            messages.error(request, f"Error adding stock note: {str(e)}")
            print(f"Error in add_stock_note: {str(e)}")
        
        # Redirect back to product edit page
        return redirect('edit_product', product_id=product_id)
    
    # If not POST, redirect to edit page
    return redirect('edit_product', product_id=product_id)

#statistics board view
def get_today_top_sales():
    """Helper function to get today's top sales consistently"""
    current_time = datetime.now()
    start_time = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
    today_revenue_data = History.objects.filter(timestamp__gte=start_time)

    product_sales = {}
    for record in today_revenue_data:
        try:
            products = json.loads(record.product)
            for product in products:
                name = product['name'].replace('_', ' ')
                quantity = int(product['quantity'])
                if name in product_sales:
                    product_sales[name] += quantity
                else:
                    product_sales[name] = quantity
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Error processing record {record.id}: {str(e)}")
            continue

    top_three = sorted(product_sales.items(), key=lambda x: x[1], reverse=True)[:3]
    return [{'name': name, 'quantity': quantity} for name, quantity in top_three]

def get_top_customers():
    """Helper function to get top customers by spending"""
    top_customers = (
        CustomerHistory.objects.filter(customer__isnull=False)
        .values(
            'customer__surname',
            'customer__firstname',
            'customer_id'
        )
        .annotate(
            total_spent=Sum('history__total_amount'),
            visit_count=Count('history'),
            avg_spent=Sum('history__total_amount') / Count('history'),
            # Concatenate surname and firstname
            name=Concat(
                'customer__surname',
                Value(' '),
                'customer__firstname',
                output_field=CharField()
            )
        )
        .order_by('-total_spent')[:5]
    )
    
    return [{
        'name': item['name'],
        'total_spent': float(item['total_spent']),
        'visit_count': item['visit_count'],
        'avg_spent': float(item['avg_spent'])
    } for item in top_customers]

def statisticsboard_view(request):
    current_time = datetime.now()
    start_time = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
    today_revenue_data = History.objects.filter(timestamp__gte=start_time)
    
    # Calculate total revenue for the day
    total_revenue = today_revenue_data.aggregate(Sum('total_amount'))['total_amount__sum'] or 0

    # Calculate the peaking hour for today only
    peak_hour = today_revenue_data.annotate(hour=TruncHour('timestamp'))\
        .values('hour')\
        .annotate(total_amount=Sum('total_amount'))\
        .order_by('-total_amount').first()
    peak_hour = peak_hour['hour'].strftime('%H:%M') if peak_hour else "No data"

    # Get today's top sales using the shared function
    top_sales = get_today_top_sales()

    # Revenue data by time period
    filter_param = request.GET.get('filter', None)
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Initialize response data
    revenue_data_list = []
    period_total_revenue = total_revenue
    
    if start_date and end_date:
        # Handle custom date range
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').replace(hour=0, minute=0, second=0, microsecond=0)
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # Get data for the custom date range
            custom_data = History.objects.filter(timestamp__gte=start_date_obj, timestamp__lte=end_date_obj)
            
            # Calculate total revenue for this period
            period_total_revenue = custom_data.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
            
            # Get daily breakdown
            revenue_data_list = custom_data.annotate(date=TruncDate('timestamp'))\
                .values('date')\
                .annotate(total_amount=Sum('total_amount'))\
                .order_by('date')\
                .values('date', 'total_amount')
            
            revenue_data_list = [
                {
                    'time': item['date'].strftime('%Y-%m-%d'), 
                    'total_amount': float(item['total_amount'])
                } 
                for item in revenue_data_list
            ]
        except ValueError:
            # Handle invalid date format
            pass
    elif filter_param == 'today':
        revenue_data_list = today_revenue_data\
            .annotate(hour=TruncHour('timestamp'))\
            .values('hour')\
            .annotate(total_amount=Sum('total_amount'))\
            .values('hour', 'total_amount')
        revenue_data_list = [{'time': item['hour'].strftime('%H:%M'), 'total_amount': float(item['total_amount'])} for item in revenue_data_list]
    elif filter_param == 'yesterday':
        yesterday_start = (current_time - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_end = start_time
        yesterday_data = History.objects.filter(timestamp__gte=yesterday_start, timestamp__lt=yesterday_end)
        
        # Calculate total revenue for yesterday
        period_total_revenue = yesterday_data.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        
        revenue_data_list = yesterday_data\
            .annotate(hour=TruncHour('timestamp'))\
            .values('hour')\
            .annotate(total_amount=Sum('total_amount'))\
            .values('hour', 'total_amount')
        revenue_data_list = [{'time': item['hour'].strftime('%H:%M'), 'total_amount': float(item['total_amount'])} for item in revenue_data_list]
    elif filter_param == 'this_week':
        # Get data for the last 7 days (including today)
        seven_days_ago = (current_time - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
        week_data = History.objects.filter(timestamp__gte=seven_days_ago)
        
        # Calculate total revenue for this week
        period_total_revenue = week_data.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        
        revenue_data_list = week_data\
            .annotate(date=TruncDate('timestamp'))\
            .values('date')\
            .annotate(total_amount=Sum('total_amount'))\
            .order_by('date')\
            .values('date', 'total_amount')
        revenue_data_list = [
            {
                'time': item['date'].strftime('%Y-%m-%d'), 
                'total_amount': float(item['total_amount'])
            } 
            for item in revenue_data_list
        ]
    elif filter_param == 'this_month':
        # Get data for the current month (from day 1 to today)
        first_day_of_month = current_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_data = History.objects.filter(timestamp__gte=first_day_of_month)
        
        # Calculate total revenue for this month
        period_total_revenue = month_data.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        
        revenue_data_list = month_data\
            .annotate(date=TruncDate('timestamp'))\
            .values('date')\
            .annotate(total_amount=Sum('total_amount'))\
            .order_by('date')\
            .values('date', 'total_amount')
        revenue_data_list = [
            {
                'time': item['date'].strftime('%Y-%m-%d'), 
                'total_amount': float(item['total_amount'])
            } 
            for item in revenue_data_list
        ]
    else:
        # Default to all data
        revenue_data_list = History.objects.annotate(date=TruncDate('timestamp'))\
            .values('date')\
            .annotate(total_amount=Sum('total_amount'))\
            .values('date', 'total_amount')
        revenue_data_list = [
            {
                'time': item['date'].strftime('%Y-%m-%d'), 
                'total_amount': float(item['total_amount'])
            } 
            for item in revenue_data_list
        ]

    # Calculate trading hours for today only
    trading_hours = today_revenue_data.annotate(hour=ExtractHour('timestamp')) \
        .values('hour') \
        .annotate(total_amount=Sum('total_amount')) \
        .order_by('-total_amount')[:5]
    trading_hours_data = [{'hour': f"{item['hour']:02}:00", 'total_amount': float(item['total_amount'])} for item in trading_hours]

    # Day-Part Analysis for today only 
    day_part_data_query = History.objects.annotate(
        part_of_day=Case(
            When(created_at__hour__lt=12, then=Value('Morning')),
            When(created_at__hour__lt=18, then=Value('Afternoon')),
            default=Value('Evening'),
            output_field=CharField()
        )).values('part_of_day').annotate(total_amount=Sum('total_amount')).order_by('part_of_day')
    day_part_data = [{'part': item['part_of_day'], 'total_amount': float(item['total_amount'])} for item in day_part_data_query]

    # Add top customers data
    top_customers = get_top_customers()
    # Get total counts for mini stats cards
    total_products_count = Product.objects.count()
    orders_count = CustomerHistory.objects.count()
    customers_count = Customer.objects.count()
    low_stock_count = Product.objects.filter(quantity__lte=F('low_stock_threshold')).count()
    
    # 1. Average Order Value by Day
    avg_order_data = History.objects.annotate(
        day=TruncDate('timestamp')
    ).values('day').annotate(
        avg_amount=Avg('total_amount'),
        count=Count('purchase_id')
    ).order_by('day')
    
    avg_order_data_json = [
        {
            'day': item['day'].strftime('%Y-%m-%d'),
            'avg_amount': float(item['avg_amount']),
            'count': item['count']
        } for item in avg_order_data
    ]
    
    # 2. Session Duration Data
    session_duration = CustomerDeviceSession.objects.filter(
        end_time__isnull=False
    ).annotate(
        day=TruncDate('start_time'),
        duration=ExpressionWrapper(F('end_time') - F('start_time'), output_field=DurationField())
    ).values('day').annotate(
        avg_duration=Avg('duration')
    ).order_by('day')
    
    session_duration_json = [
        {
            'day': item['day'].strftime('%Y-%m-%d'),
            'avg_duration': item['avg_duration'].total_seconds() / 60  # Convert to minutes
        } for item in session_duration
    ]
    
    # 3. Payment Status Distribution - Update to compare completed orders vs canceled orders
    # Count completed orders (From CustomerHistory)
    completed_orders_count = CustomerHistory.objects.count()
    
    # Count canceled orders (From CancelShopping)
    canceled_orders_count = CancelShopping.objects.count()
    
    # Create payment status distribution data with more descriptive labels
    payment_status_json = [
        {
            'status': 'Completed Transactions',
            'count': completed_orders_count,
            'color': '#28a745'  # Green
        },
        {
            'status': 'Canceled Shopping',
            'count': canceled_orders_count,
            'color': '#dc3545'  # Red
        }
    ]
    
    # Add pending status from PaymentShopping if it exists
    pending_count = PaymentShopping.objects.filter(status='pending').count()
    if pending_count > 0:
        payment_status_json.append({
            'status': 'Pending Payment',
            'count': pending_count,
            'color': '#ffc107'  # Yellow
        })

    # 4. Low Stock Products
    low_stock_products = Product.objects.filter(
        quantity__lte=F('low_stock_threshold')
    ).order_by('quantity')
    
    low_stock_json = [
        {
            'name': product.name.replace('_', ' '),
            'quantity': product.quantity,
            'low_stock_threshold': product.low_stock_threshold,
            'category': product.category
        } for product in low_stock_products
    ]

    # 5. Restock Suggestion Data (Based on sales trends and current inventory)
    # First get products with recent sales
    product_sales = {}
    recent_histories = History.objects.filter(
        timestamp__gte=current_time - timedelta(days=30)
    )
    
    for record in recent_histories:
        try:
            products = json.loads(record.product)
            for product in products:
                name = product['name'].replace('_', ' ')
                quantity = int(product['quantity'])
                if name in product_sales:
                    product_sales[name] += quantity
                else:
                    product_sales[name] = quantity
        except (json.JSONDecodeError, KeyError, ValueError):
            continue
    
    # Then combine with current inventory levels
    restock_suggestion_json = []
    top_selling_products = sorted(product_sales.items(), key=lambda x: x[1], reverse=True)[:10]
    
    # Include at least 5 products in the suggestions, even if they don't need restocking
    for name, sold_quantity in top_selling_products:
        try:
            product = Product.objects.get(name=name)
            suggested_quantity = max(product.low_stock_threshold * 2, sold_quantity)
            
            # Include products regardless of current quantity to ensure we have data
            restock_suggestion_json.append({
                'product_name': name.replace('_', ' '),
                'current_quantity': product.quantity,
                'suggested_quantity': suggested_quantity,
                'sales_last_30days': sold_quantity
            })
            
        except Product.DoesNotExist:
            continue
    
    # If there are no restock suggestions, add some default data
    if not restock_suggestion_json:
        # Get top 5 products by sales or by low stock
        top_products = Product.objects.all().order_by('-quantity')[:5]
        for product in top_products:
            suggested_quantity = product.low_stock_threshold * 2
            restock_suggestion_json.append({
                'product_name': product.name.replace('_', ' '),
                'current_quantity': product.quantity,
                'suggested_quantity': suggested_quantity,
                'sales_last_30days': 0
            })

    # 6. Weekday vs Weekend Revenue Comparison
    weekday_comparison = History.objects.annotate(
        weekday=ExtractWeekDay('timestamp')
    ).values('weekday').annotate(
        total_amount=Sum('total_amount'),
        count=Count('purchase_id')
    ).order_by('weekday')
    
    # Map weekday numbers to names
    weekday_names = {
        1: 'Monday',
        2: 'Tuesday',
        3: 'Wednesday',
        4: 'Thursday',
        5: 'Friday',
        6: 'Saturday',
        7: 'Sunday'
    }
    
    weekday_comparison_json = [
        {
            'weekday': item['weekday'],
            'day_name': weekday_names.get(item['weekday'], f"Day {item['weekday']}"),
            'total_amount': float(item['total_amount']),
            'count': item['count'],
            'is_weekend': item['weekday'] in [6, 7]  # Saturday and Sunday
        } for item in weekday_comparison
    ]
    
    # 7. Device Status Distribution
    device_status = DeviceStatus.objects.values('status').annotate(
        count=Count('id')
    ).order_by('status')
    
    device_status_json = [
        {
            'status': item['status'].capitalize(),
            'count': item['count']
        } for item in device_status
    ]
    
    # 8. Product Ratings
    product_ratings = ProductRating.objects.values('product_name').annotate(
        avg_star=Avg('star')
    ).order_by('-avg_star')[:10]  # Top 10 by rating
    
    product_ratings_json = [
        {
            'product_name': item['product_name'].replace('_', ' '),
            'avg_star': float(item['avg_star'])
        } for item in product_ratings
    ]
    
    # 9. Most Rated Products
    most_rated = ProductRating.objects.values('product_name').annotate(
        count=Count('id')
    ).order_by('-count')[:10]  # Top 10 most rated
    
    most_rated_json = [
        {
            'product_name': item['product_name'].replace('_', ' '),
            'count': item['count']
        } for item in most_rated
    ]

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        # Get today's revenue data for consistency
        todays_revenue = today_revenue_data.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        
        # Handle the AJAX request - include both today's and period revenue in response
        return JsonResponse({
            'revenue_data': revenue_data_list,
            'total_revenue': period_total_revenue,
            'today_revenue': todays_revenue,
            'top_sales': top_sales,
            'trading_hours': trading_hours_data,
            'day_part_data': day_part_data,
            'peak_hour': peak_hour,
            'avg_order_data': avg_order_data_json,
            'session_duration': session_duration_json,
            'payment_status': payment_status_json,
            'low_stock': low_stock_json,
            'restock_suggestion': restock_suggestion_json,
            'weekday_comparison': weekday_comparison_json,
            'device_status': device_status_json,
            'product_ratings': product_ratings_json,
            'most_rated': most_rated_json
        })

    context = {
        'total_revenue': total_revenue,
        'peak_hour': peak_hour,
        'top_sales': top_sales,
        'revenue_data_json': json.dumps(revenue_data_list),
        'top_sales_json': json.dumps(top_sales),
        'trading_hours_json': json.dumps(trading_hours_data),
        'day_part_data_json': json.dumps(day_part_data),
        'top_customers_json': json.dumps(get_top_customers()),
        'total_products_count': total_products_count,
        'orders_count': orders_count,
        'customers_count': customers_count,
        'low_stock_count': low_stock_count,
        'avg_order_data_json': json.dumps(avg_order_data_json),
        'session_duration_json': json.dumps(session_duration_json),
        'payment_status_json': json.dumps(payment_status_json),
        'low_stock_json': json.dumps(low_stock_json),
        'restock_suggestion_json': json.dumps(restock_suggestion_json),
        'weekday_comparison_json': json.dumps(weekday_comparison_json),
        'device_status_json': json.dumps(device_status_json),
        'product_ratings_json': json.dumps(product_ratings_json),
        'most_rated_json': json.dumps(most_rated_json)
    }

    return render(request, 'statistic.html', context)

class TopThreeProductsView(APIView):
    """API to get the top three products sold today."""
    def get(self, request):
        # Use the shared function for consistency
        top_three = get_today_top_sales()
        return Response(top_three, status=status.HTTP_200_OK)


#history view
@login_required
def history_list_view(request):
    # Get CustomerHistory objects instead of History
    history_query = CustomerHistory.objects.select_related('history', 'customer').all().order_by('-history__timestamp')

    search_term = request.GET.get('search', '')
    search_filter = request.GET.get('filter', 'all')
    start_date_str = request.GET.get('start_date', '')
    end_date_str = request.GET.get('end_date', '')

    is_search = bool(search_term or start_date_str or end_date_str)

    if search_term:
        if search_filter == 'id':
            history_query = history_query.filter(history__random_id__icontains=search_term)
        elif search_filter == 'customer':
            history_query = history_query.filter(
                Q(customer__surname__icontains=search_term) |
                Q(customer__firstname__icontains=search_term) |
                Q(guest_name__icontains=search_term)
            )
        elif search_filter == 'date':
            # Attempt to parse date in various formats
            parsed_date = None
            date_formats = ['%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y', '%d/%m/%Y']
            for fmt in date_formats:
                try:
                    parsed_date = datetime.strptime(search_term, fmt).date()
                    break
                except ValueError:
                    continue
            if parsed_date:
                history_query = history_query.filter(history__timestamp__date=parsed_date)
            else:
                # If date parsing fails, you might want to return an empty queryset or handle the error
                history_query = CustomerHistory.objects.none() 
        elif search_filter == 'note':
             history_query = history_query.filter(history__note__icontains=search_term)
        else: # 'all' fields
            history_query = history_query.filter(
                Q(history__random_id__icontains=search_term) |
                Q(customer__surname__icontains=search_term) |
                Q(customer__firstname__icontains=search_term) |
                Q(guest_name__icontains=search_term) |
                Q(history__note__icontains=search_term)
            )
            # Add date search for 'all' if search_term can be parsed as a date
            try:
                parsed_date_all = datetime.strptime(search_term, '%Y-%m-%d').date()
                history_query = history_query.filter(history__timestamp__date=parsed_date_all)
            except ValueError:
                pass # Not a date, or not in YYYY-MM-DD format
    
    # Date range filtering
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            history_query = history_query.filter(history__timestamp__date__gte=start_date)
        except ValueError:
            pass # Invalid date format, ignore

    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            # Add one day to end_date to make it inclusive for the whole day
            history_query = history_query.filter(history__timestamp__date__lte=end_date)
        except ValueError:
            pass # Invalid date format, ignore

    paginator = Paginator(history_query, 15)  # Show 15 histories per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Process each history record
    for customer_history in page_obj:
        try:
            product_details = json.loads(customer_history.history.product)
            for product in product_details:
                product['name'] = product['name'].replace('_', ' ')
            customer_history.product_details = product_details
            customer_history.random_id = customer_history.history.random_id
            customer_history.timestamp = customer_history.history.timestamp
            customer_history.total_amount = customer_history.history.total_amount
            
            # Handle display name logic
            if customer_history.customer:
                customer_history.fullname = customer_history.customer.fullname
            else:
                customer_history.fullname = customer_history.guest_name or "Dsoft-member"
                
        except json.JSONDecodeError:
            customer_history.product_details = []
    
    # Check if this is an AJAX request for the refresh functionality
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            
    return render(request, 'history_list.html', {
        'history_list': page_obj,
        'page_obj': page_obj,
        'search_term': search_term,
        'search_filter': search_filter,
        'start_date': start_date_str, 
        'end_date': end_date_str,
        'is_search': is_search,
        'user': request.user,
    })


# Product API view
class ProductListCreateView(generics.ListCreateAPIView):
    """API to list and create products."""
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    def dispatch(self, request, *args, **kwargs):
        start_time = time.time()  # Record start time
        response = super().dispatch(request, *args, **kwargs)
        end_time = time.time()  # Record end time
        latency = end_time - start_time
        # Log latency to the console
        print(f"Product API latency: {latency:.15f} seconds")
        return response


def search_by_category(request, category):
    """Search products by category."""
    products = Product.objects.filter(category__iexact=category)
    return JsonResponse({'products': list(products.values())})


# History API view
class HistoryListCreateView(generics.ListCreateAPIView):
    """API to list and create purchase history."""
    queryset = History.objects.all()
    serializer_class = HistorySerializer

    def dispatch(self, request, *args, **kwargs):
        start_time = time.time()  # Record start time
        response = super().dispatch(request, *args, **kwargs)
        end_time = time.time()  # Record end time
        latency = end_time - start_time

        # Log latency to the console
        print(f"History API latency: {latency:.15f} seconds")
        return response

def generate_invoice(request, random_id):
    try:
        history = History.objects.get(random_id=random_id)
        customer_history = CustomerHistory.objects.get(history=history)
        
        # Parse and prepare product details
        product_details = json.loads(history.product)
        for product in product_details:
            product['name'] = product['name'].replace('_', ' ')
            product['unit_price'] = float(product['price'])
            product['total_price'] = float(product['price']) * int(product['quantity'])
            
        # Add customer info and product details to history object
        history.product_details = product_details
        
        # Xác định tên khách hàng từ CustomerHistory
        if customer_history.customer:
            # Nếu là khách hàng đã đăng ký, lấy fullname từ customer
            history.customer_name = customer_history.customer.fullname
            history.guest_name = None
        elif customer_history.guest_name:
            # Nếu là khách vãng lai có tên
            history.customer_name = None
            history.guest_name = customer_history.guest_name
        else:
            # Nếu không có thông tin gì
            history.customer_name = None
            history.guest_name = "Dsoft-member"

        return render(request, 'invoice.html', {'history': history})
        
    except History.DoesNotExist:
        return HttpResponse("Invoice not found", status=404)
    except json.JSONDecodeError:
        return HttpResponse("Invalid product data", status=400)
    except Exception as e:
        return HttpResponse(f"Error generating invoice: {str(e)}", status=500)

class InvoiceAPIView(APIView):
    """API to generate and retrieve invoice details."""
    renderer_classes = [JSONRenderer, TemplateHTMLRenderer]
    
    def get(self, request, random_id, format=None):
        try:
            history = History.objects.get(random_id=random_id)
            customer_history = CustomerHistory.objects.get(history=history)
            
            # If HTML is requested, render the template
            if request.accepted_renderer.format == 'html':
                # Parse product details
                product_details = json.loads(history.product)
                for product in product_details:
                    product['name'] = product['name'].replace('_', ' ')
                    product['unit_price'] = float(product['price'])
                    product['total_price'] = float(product['price']) * int(product['quantity'])
                history.product_details = product_details
                
                # Add customer information
                if customer_history.customer:
                    history.customer_name = customer_history.customer.fullname
                    history.guest_name = None
                elif customer_history.guest_name:
                    history.customer_name = None
                    history.guest_name = customer_history.guest_name
                else:
                    history.customer_name = None
                    history.guest_name = "Dsoft-member"
                
                return Response({'history': history}, template_name='invoice.html')
            
            # Otherwise return JSON
            serializer = InvoiceSerializer(history)
            return Response(serializer.data)
            
        except History.DoesNotExist:
            return Response({'error': 'Invoice not found'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)

class DeviceConnectionView(generics.ListCreateAPIView):
    """API to manage device connections."""
    queryset = DeviceConnection.objects.all()
    serializer_class = DeviceConnectionSerializer
    
    def get_queryset(self):
        device_id = self.request.query_params.get('device_id', None)
        
        # If URL contains device_id, return specific device or 404
        current_path = self.request.path
        if '/api/devices/' in current_path:
            path_device_id = current_path.split('/api/devices/')[-1].strip('/')
            if path_device_id:
                return DeviceConnection.objects.filter(device_id=path_device_id)
        
        # Handle query parameter device_id
        if device_id:
            return DeviceConnection.objects.filter(device_id=device_id)
                
        return DeviceConnection.objects.all()

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            if not queryset.exists():
                return Response(
                    {"message": "Device not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {"message": "Device not found"},
                status=status.HTTP_404_NOT_FOUND
            )

class DeviceDeleteView(generics.DestroyAPIView):
    """API to delete a device."""
    queryset = DeviceConnection.objects.all()
    serializer_class = DeviceConnectionSerializer
    lookup_field = 'device_id'
    http_method_names = ['delete', 'post']  # Cho phép cả POST và DELETE

    def get_object(self):
        try:
            device_id = self.kwargs.get('device_id')
            print(f"Attempting to delete device with ID: {device_id}, Type: {type(device_id)}")
            
            if not device_id or device_id == 'string' or device_id == 'undefined':
                print(f"Invalid device_id received: {device_id}")
                raise Http404(f"Invalid device ID: {device_id}")
                
            device = DeviceConnection.objects.get(device_id=device_id)
            print(f"Found device to delete: {device.device_id} - {device.device_name}")
            return device
        except DeviceConnection.DoesNotExist:
            print(f"Device not found with ID: {device_id}")
            raise Http404("Device not found")
        except Exception as e:
            print(f"Error getting device for deletion: {str(e)}")
            raise

    def post(self, request, *args, **kwargs):
        """Xử lý POST request như DELETE nếu có _method=DELETE"""
        if request.POST.get('_method') == 'DELETE':
            print("Nhận POST với _method=DELETE, xử lý như DELETE request")
            return self.destroy(request, *args, **kwargs)
        return Response(
            {"error": "Method not allowed"},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
            
    def destroy(self, request, *args, **kwargs):
        try:
            device = self.get_object()
            device_id = device.device_id
            device_name = device.device_name
            
            print(f"Deleting device: {device_id} - {device_name}")
            
            # First delete related device status
            try:
                device_status = DeviceStatus.objects.get(device=device)
                print(f"Deleting device status for {device_id}")
                device_status.delete()
            except DeviceStatus.DoesNotExist:
                print(f"No device status found for {device_id}")
                pass  # No device status to delete
            
            # Then delete the device itself
            device.delete()
            print(f"Successfully deleted device: {device_id} - {device_name}")
            
            # Check if we should redirect
            redirect_to = request.query_params.get('redirect_to')
            if redirect_to:
                print(f"Redirecting to: {redirect_to}")
                return redirect(redirect_to)
            
            return Response(
                {"message": f"Device {device_name} (ID: {device_id}) deleted successfully"},
                status=status.HTTP_204_NO_CONTENT
            )
        except Http404 as e:
            print(f"404 Error: {str(e)}")
            # Check if we should redirect
            redirect_to = request.query_params.get('redirect_to')
            if redirect_to:
                messages.error(request, f"Device not found: {str(e)}")
                return redirect(redirect_to)
                
            return Response(
                {"error": str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            print(f"Error deleting device: {str(e)}")
            
            # Check if we should redirect
            redirect_to = request.query_params.get('redirect_to')
            if redirect_to:
                messages.error(request, f"Error deleting device: {str(e)}")
                return redirect(redirect_to)
                
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class DeviceStatusUpdateView(generics.RetrieveUpdateAPIView):
    """API to update the status of a device."""
    queryset = DeviceConnection.objects.all()
    serializer_class = DeviceConnectionSerializer
    lookup_field = 'device_id'

    def get_object(self):
        try:
            with transaction.atomic():
                return super().get_object()
        except DeviceConnection.DoesNotExist:
            raise
        except Exception as e:
            print(f"Error getting device object: {str(e)}")
            raise

    def patch(self, request, *args, **kwargs):
        try:
            # Add lock timeout
            with transaction.atomic(using=None, savepoint=True):
                device = self.get_object()
                serializer = self.serializer_class(device, data=request.data, partial=True)
                if serializer.is_valid():
                    serializer.save()
                    return Response(serializer.data)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except DeviceConnection.DoesNotExist:
            return Response(
                {'error': 'Device not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            print(f"Error updating device: {str(e)}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

@login_required
def device_password_view(request):
    # Check if already verified in current session
    if request.session.get('device_access_verified'):
        return redirect('device_status')

    if request.method == 'POST':
        password = request.POST.get('secondary_password')
        if password == settings.DEVICE_MANAGEMENT_PASSWORD:  # Use password from settings instead
            request.session['device_access_verified'] = True
            request.session.save()
            return redirect('device_status')
        return render(request, 'device_password.html', {'error_message': 'Invalid password'})
    return render(request, 'device_password.html')

@login_required
def device_status_view(request):
    # Add debug print to check session
    print("Session verified:", request.session.get('device_access_verified'))
    
    if not request.session.get('device_access_verified'):
        return redirect('device_password')
    
    devices = DeviceConnection.objects.all()
    return render(request, 'device_status.html', {
        'devices': devices,
        'settings': settings  # Add settings to context
    })

# Thêm view xử lý logout
from django.contrib.auth import logout

def logout_view(request):
    # Clear all session data
    request.session.flush()
    # Logout user
    logout(request)
    # Redirect to login page
    return redirect('login')

class CustomerSignupView(APIView):
    """API for customer registration."""
    @swagger_auto_schema(
        operation_description="API endpoint for customer registration",
        request_body=CustomerSerializer,
        responses={
            201: openapi.Response(
                description="Successfully created",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'token': openapi.Schema(type=openapi.TYPE_STRING),
                        'user_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'username': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            ),
            400: 'Bad Request'
        }
    )
    def post(self, request):
        serializer = CustomerSerializer(data=request.data)
        if (serializer.is_valid()):
            customer = serializer.save()
            token = Token.objects.create(user=customer.user)  # Changed to create() instead of get_or_create()
            return Response({
                'token': token.key,
                'user_id': customer.user.id,
                'username': customer.user.username
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CustomerLoginView(APIView):
    """API for customer login."""
    @swagger_auto_schema(
        operation_description="API endpoint for customer login",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['phone_number', 'password'],
            properties={
                'phone_number': openapi.Schema(type=openapi.TYPE_STRING),
                'password': openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
        responses={
            200: openapi.Response(
                description="Successful login",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'token': openapi.Schema(type=openapi.TYPE_STRING),
                        'user_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'username': openapi.Schema(type=openapi.TYPE_STRING),
                        'fullname': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            ),
            400: 'Bad Request',
            401: 'Invalid Credentials'
        }
    )
    def post(self, request):
        phone_number = request.data.get('phone_number')
        password = request.data.get('password')

        print(f"Login attempt - Phone: {phone_number}")  # Debug log
        
        if not phone_number or not password:
            return Response(
                {'error': 'Phone number and password are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(username=phone_number, password=password)
        
        if user:
            token, _ = Token.objects.get_or_create(user=user)
            try:
                customer = Customer.objects.get(user=user)
                
                # Format profile image if exists
                profile_image = None
                if customer.profile_image:
                    if customer.profile_image.startswith('data:image'):
                        parts = customer.profile_image.split(';base64,')
                        if len(parts) == 2:
                            image_type = parts[0].split(':')[1]
                            profile_image = {
                                'type': image_type,
                                'data': parts[1]
                            }
                
                # Add a token usage example in the response
                return Response({
                    'token': token.key,
                    'user_id': user.id,
                    'username': user.username,
                    'fullname': customer.fullname,
                    'surname': customer.surname,
                    'firstname': customer.firstname,
                    'phone_number': customer.phone_number,
                    'profile_image': profile_image,
                    'created_at': customer.created_at,
                    'token_type': 'Bearer',
                    'token_usage': f'Authorization: Bearer {token.key}'
                })
            except Customer.DoesNotExist:
                Token.objects.filter(user=user).delete()
                return Response(
                    {'error': 'Not a customer account'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(
            {'error': 'Invalid phone number or password'}, 
            status=status.HTTP_401_UNAUTHORIZED
        )

class CustomerDetailView(APIView):
    """API to retrieve and update customer details."""
    permission_classes = [AllowAny]

    def get(self, request, username):
        try:
            customer = Customer.objects.get(user__username=username)
            serializer = CustomerSerializer(customer)
            return Response(serializer.data)
        except Customer.DoesNotExist:
            return Response(
                {'error': 'Customer not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @swagger_auto_schema(
        operation_description="Update customer details. All fields are optional.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'surname': openapi.Schema(type=openapi.TYPE_STRING, description="Optional: New surname"),
                'firstname': openapi.Schema(type=openapi.TYPE_STRING, description="Optional: New firstname"),
                'profile_image': openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    description="Optional: New profile image",
                    properties={
                        'type': openapi.Schema(type=openapi.TYPE_STRING),
                        'data': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            }
        ),
        responses={
            200: "Successfully updated",
            404: "Customer not found"
        }
    )
    def patch(self, request, username):
        try:
            customer = Customer.objects.get(user__username=username)
            
            # Handle each field separately using set_names helper method
            if 'surname' in request.data or 'firstname' in request.data:
                customer.set_names(
                    surname=request.data.get('surname', customer.surname),
                    firstname=request.data.get('firstname', customer.firstname)
                )

            # Handle profile image if present
            if 'profile_image' in request.data:
                image_data = request.data['profile_image']
                if isinstance(image_data, dict) and 'type' in image_data and 'data' in image_data:
                    customer.profile_image = f"data:{image_data['type']};base64,{image_data['data']}"
                else:
                    customer.profile_image = image_data

            # Save changes
            customer.save()

            return Response({
                'message': 'Profile updated successfully',
                'data': CustomerSerializer(customer).data
            })
            
        except Customer.DoesNotExist:
            return Response(
                {'error': 'Customer not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )

class CustomerListView(generics.ListAPIView):
    """API to list all customers."""
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer

    def get_queryset(self):
        queryset = Customer.objects.all().order_by('created_at')
        return queryset

@login_required
def customer_list_view(request):
    customers = Customer.objects.all().order_by('-created_at')  # Order by most recent creation date
    paginator = Paginator(customers, 10)  # Show 10 customers per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'customer_list.html', {
        'page_obj': page_obj,
        'is_paginated': paginator.num_pages > 1
    })

@login_required
def edit_customer_view(request, customer_id):
    customer = get_object_or_404(Customer, id=customer_id)
    if request.method == 'POST':
        # Handle the form submission
        customer.surname = request.POST.get('surname', customer.surname)
        customer.firstname = request.POST.get('firstname', customer.firstname)
        customer.phone_number = request.POST.get('phone_number', customer.phone_number)
        customer.save()
        return redirect('customer_list')
    return render(request, 'edit_customer.html', {'customer': customer})

@login_required
def delete_customer_view(request, customer_id):
    if request.method == 'POST':
        customer = get_object_or_404(Customer, id=customer_id)
        user = customer.user
        customer.delete()
        user.delete()
        messages.success(request, 'Customer deleted successfully.')
    return redirect('customer_list')

class AdminLoginView(APIView):
    """API for admin login to get a token."""
    permission_classes = [AllowAny]
    authentication_classes = []

    @swagger_auto_schema(
        operation_description="Login with admin credentials to get token",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['username', 'password'],
            properties={
                'username': openapi.Schema(type=openapi.TYPE_STRING),
                'password': openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
        responses={
            200: openapi.Response(
                description="Successful login",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'token': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            ),
            401: 'Invalid credentials'
        }
    )
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        
        user = authenticate(username=username, password=password)
        
        if user is not None and user.is_staff:
            token, _ = Token.objects.get_or_create(user=user)
            return Response({
                'token': token.key
            })
        
        return Response(
            {'error': 'Invalid credentials'}, 
            status=status.HTTP_401_UNAUTHORIZED
        )

class ProductsByCategoryView(generics.ListAPIView):
    """API to list products by category."""
    serializer_class = ProductSerializer

    def get_queryset(self):
        category = self.kwargs['category']
        return Product.objects.filter(category=category)

class CustomerChangePasswordView(APIView):
    """API for customers to change their password."""
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="API endpoint for customer password change",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['username', 'old_password', 'new_password'],
            properties={
                'username': openapi.Schema(type=openapi.TYPE_STRING),
                'old_password': openapi.Schema(type=openapi.TYPE_STRING),
                'new_password': openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
        responses={
            200: openapi.Response(
                description="Password changed successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            ),
            400: 'Bad Request',
            401: 'Invalid Credentials',
            404: 'User not found'
        }
    )
    def post(self, request):
        username = request.data.get('username')
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')

        # Validate input
        if not all([username, old_password, new_password]):
            return Response(
                {'error': 'All fields are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verify the user exists and is a customer
        try:
            user = User.objects.get(username=username)
            customer = Customer.objects.get(user=user)
        except (User.DoesNotExist, Customer.DoesNotExist):
            return Response(
                {'error': 'User not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )

        # Verify old password
        if not user.check_password(old_password):
            return Response(
                {'error': 'Invalid old password'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Set new password
        user.set_password(new_password)
        user.save()

        # Invalidate old token and create new one
        Token.objects.filter(user=user).delete()
        new_token = Token.objects.create(user=user)

        return Response({
            'message': 'Password changed successfully',
            'new_token': new_token.key
        })

class CustomerHistoryView(APIView):
    """API to get customer purchase history."""
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="API endpoint to get customer purchase history",
        manual_parameters=[
            openapi.Parameter(
                'username',
                openapi.IN_QUERY,
                description="Customer's username/phone number",
                type=openapi.TYPE_STRING
            ),
        ],
        responses={
            200: "Customer history retrieved successfully",
            404: "Customer not found"
        }
    )
    def get(self, request):
        username = request.query_params.get('username')
        try:
            if (username):
                # Get history for specific customer
                customer = Customer.objects.get(user__username=username)
                histories = CustomerHistory.objects.filter(customer=customer).order_by('-history__timestamp')
            else:
                # Get all histories
                histories = CustomerHistory.objects.all().order_by('-history__timestamp')

            data = []
            for history in histories:
                history_data = {
                    'id': history.id,
                    'customer_name': history.fullname,
                    'timestamp': format_vietnam_timestamp(history.history.timestamp),
                    'total_amount': float(history.history.total_amount),
                    'products': json.loads(history.history.product),
                    'guest_name': history.guest_name,
                    'is_registered': bool(history.customer)
                }
                data.append(history_data)

            return Response(data)
        except Customer.DoesNotExist:
            return Response(
                {'error': 'Customer not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )

class CreateCustomerHistoryView(APIView):
    """API to create customer purchase history."""
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="API endpoint to create customer purchase history",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'username': openapi.Schema(type=openapi.TYPE_STRING),
                'guest_name': openapi.Schema(type=openapi.TYPE_STRING),
                'products': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT)),
                'total_amount': openapi.Schema(type=openapi.TYPE_NUMBER),
            }
        ),
        responses={
            201: "History created successfully",
            400: "Invalid data"
        }
    )
    def post(self, request):
        username = request.data.get('username')
        guest_name = request.data.get('guest_name')
        products = request.data.get('products')
        total_amount = request.data.get('total_amount')

        try:
            # Create History record first
            history = History.objects.create(
                product=json.dumps(products),
                total_amount=total_amount
            )

            # Try to find customer if username provided
            customer = None
            if username:
                try:
                    customer = Customer.objects.get(user__username=username)
                except Customer.DoesNotExist:
                    pass

            # Create CustomerHistory record
            customer_history = CustomerHistory.objects.create(
                customer=customer,
                guest_name=guest_name if not customer else None,
                history=history
            )
            
            # Send notification to the customer if they exist and have FCM token
            if customer and customer.fcm_token:
                # Create notification in the database
                try:
                    # Format product names for notification
                    product_names = []
                    for product in products:
                        name = product.get('name', '').replace('_', ' ')
                        quantity = product.get('quantity', 1)
                        product_names.append(f"{name} x{quantity}")
                    
                    # Create product summary text (limit to 3 products + "and more" if needed)
                    product_summary = ", ".join(product_names[:3])
                    if len(product_names) > 3:
                        product_summary += f" and {len(product_names) - 3} more items"
                    
                    # Create notification message
                    notif_title = "Completed Purchase"
                    notif_message = f"Your order (ID: {history.random_id}) of {product_summary} for {history.total_amount} VND has been completed."
                    
                    # Create notification in database
                    notification = Notification.objects.create(
                        user=customer_history.customer,
                        notif_type='personal',
                        title=notif_title,
                        message=notif_message,
                        is_read=False
                    )
                    
                    # Send Firebase push notification
                    try:
                        msg = messaging.Message(
                            notification=messaging.Notification(
                                title=notif_title,
                                body=notif_message
                            ),
                            data={
                                'type': 'order',
                                'order_id': history.random_id,
                                'timestamp': format_vietnam_timestamp(history.timestamp)
                            },
                            token=customer.fcm_token,
                        )
                        messaging.send(msg)
                    except Exception as e:
                        # If Firebase messaging fails, still continue - we've stored the notification in DB
                        print(f"Failed to send Firebase notification: {str(e)}")
                except Exception as e:
                    # If notification creation fails, log but continue
                    print(f"Failed to create notification: {str(e)}")

            return Response({
                'id': customer_history.id,
                'customer_name': customer_history.fullname,
                'timestamp': format_vietnam_timestamp(history.timestamp),
                'total_amount': float(history.total_amount),
                'products': products
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

class CustomerHistoryLinkView(APIView):
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description="Create or update customer history link, send payment success signal, and end device session",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['random_id', 'device_id'],
            properties={
                'random_id': openapi.Schema(type=openapi.TYPE_STRING),
                'username': openapi.Schema(type=openapi.TYPE_STRING),
                'device_id': openapi.Schema(type=openapi.TYPE_STRING, description="Device ID to end session"),
                'note': openapi.Schema(type=openapi.TYPE_STRING, description="Optional note for the history")
            }
        ),
        responses={
            200: "History linked and device session ended successfully",
            400: "Bad request - Missing required fields", 
            404: "History or device not found"
        }
    )
    def post(self, request):
        random_id = request.data.get('random_id')
        username = request.data.get('username', '').strip()
        device_id = request.data.get('device_id')  # Added device_id
        note = request.data.get('note', '').strip()  # Get optional note

        if not device_id:
            return Response(
                {'error': 'device_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                # Get history and customer history
                history = History.objects.get(random_id=random_id)
                customer_history = CustomerHistory.objects.filter(history=history).first()

                # Get device and status
                device = DeviceConnection.objects.get(device_id=device_id)
                device_status = DeviceStatus.objects.get(device=device)

                # Update customer info
                if username:
                    try:
                        customer = Customer.objects.get(user__username=username)
                        customer_history.customer = customer
                        customer_history.guest_name = None
                    except Customer.DoesNotExist:
                        return Response(
                            {'error': f'Customer with phone number {username} not found'},
                            status=status.HTTP_404_NOT_FOUND
                        )
                else:
                    customer_history.customer = None 
                    customer_history.guest_name = "Dsoft-member"

                # Save history with note if provided
                history.timestamp = timezone.localtime(timezone.now())
                if note:
                    history.note = note
                history.save()
                customer_history.save()

                # End the device session now before setting payment flag
                end_success = device_status.end_session()
                if not end_success:
                    raise Exception("Failed to end device session")

                # Set payment flag and timestamp in cache for 15 seconds
                cache.set(f'payment_success_{device_id}', True, timeout=15)
                device_status.status = 'available'
                device_status.current_user = None
                device_status.session_start = None
                device_status.save()

                # Nếu không phải guest (username được cung cấp và customer tồn tại)
                if customer_history.customer:
                    try:
                        # Get product details for the notification
                        products = json.loads(history.product)
                        
                        # Format product names for notification
                        product_names = []
                        for product in products:
                            name = product.get('name', '').replace('_', ' ')
                            quantity = product.get('quantity', 1)
                            product_names.append(f"{name} x{quantity}")
                        
                        # Create product summary text (limit to 3 products + "and more" if needed)
                        product_summary = ", ".join(product_names[:3])
                        if len(product_names) > 3:
                            product_summary += f" and {len(product_names) - 3} more items"
                        
                        # Create notification message
                        notif_title = "Completed Purchase"
                        notif_message = f"Your order (ID: {history.random_id}) of {product_summary} for {history.total_amount} VND has been completed."
                        if note:
                            notif_message += f"\nNote: {note}"
                        
                        # Create notification in database
                        notification = Notification.objects.create(
                            user=customer_history.customer,
                            notif_type='personal',
                            title=notif_title,
                            message=notif_message,
                            is_read=False
                        )
                        
                        # Send Firebase push notification if user has FCM token
                        sent_notification = False
                        if customer_history.customer.fcm_token:
                            try:
                                # First try with Firebase Admin SDK
                                try:
                                    msg = messaging.Message(
                                        notification=messaging.Notification(
                                            title=notif_title,
                                            body=notif_message
                                        ),
                                        data={
                                            'type': 'order',
                                            'order_id': history.random_id,
                                            'random_id': history.random_id,
                                            'timestamp': format_vietnam_timestamp(history.timestamp),
                                            'title': notif_title,
                                            'message': notif_message,
                                            'notif_type': 'personal'
                                        },
                                        token=customer_history.customer.fcm_token,
                                    )
                                    messaging.send(msg)
                                    sent_notification = True
                                    print(f"Successfully sent notification via Firebase Admin SDK to {username}")
                                except Exception as e:
                                    # If Firebase Admin SDK fails, try legacy method
                                    print(f"Failed to send Firebase notification via Admin SDK: {str(e)}")
                                    
                                    if not sent_notification:
                                        # Try with legacy FCM
                                        fcm_response = send_fcm_legacy(
                                            customer_history.customer.fcm_token, 
                                            notif_title, 
                                            notif_message,
                                            {
                                                'type': 'order',
                                                'order_id': history.random_id,
                                                'random_id': history.random_id,
                                                'timestamp': format_vietnam_timestamp(history.timestamp),
                                                'title': notif_title,
                                                'message': notif_message,
                                                'notif_type': 'personal'
                                            }
                                        )
                                        
                                        if fcm_response.get("success"):
                                            sent_notification = True
                                            print(f"Successfully sent notification via Legacy FCM to {username}")
                                        else:
                                            print(f"Failed to send Legacy FCM notification: {fcm_response.get('error', 'Unknown error')}")
                            except Exception as e:
                                # If all Firebase messaging attempts fail, still continue with order process
                                print(f"All notification attempts failed: {str(e)}")
                    except Exception as e:
                        # If notification creation fails, log but continue with order process
                        print(f"Failed to create order notification: {str(e)}")

                return Response({
                    'customer_name': customer_history.fullname,
                    'device_id': device.device_id,
                    'device_name': device.device_name, 
                    'device_status': device_status.status,
                    'timestamp': format_vietnam_timestamp(history.timestamp),
                    'note': note if note else None,
                    'message': 'History linked and payment_success signal set for 15 seconds'
                })
        except DeviceConnection.DoesNotExist:
            return Response(
                {'error': f'Device with id {device_id} not found'},
                status=status.HTTP_404_NOT_FOUND  
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    @swagger_auto_schema(
        operation_description="Get customer history details by random_id",
        manual_parameters=[
            openapi.Parameter(
                'random_id',
                openapi.IN_QUERY,
                description="Random ID of the history",
                type=openapi.TYPE_STRING,
                required=True
            ),
        ],
        responses={
            200: openapi.Response(
                description="History details retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'random_id': openapi.Schema(type=openapi.TYPE_STRING),
                        'customer_name': openapi.Schema(type=openapi.TYPE_STRING),
                        'timestamp': openapi.Schema(type=openapi.TYPE_STRING),
                        'total_amount': openapi.Schema(type=openapi.TYPE_NUMBER),
                        'products': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT)),
                        'guest_name': openapi.Schema(type=openapi.TYPE_STRING),
                        'is_registered': openapi.Schema(type=openapi.TYPE_BOOLEAN)
                    }
                )
            ),
            400: "Random ID is required",
            404: "History not found"
        }
    )
    def get(self, request):
        random_id = request.query_params.get('random_id')
        if not random_id:
            return Response(
                {'error': 'random_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            history = History.objects.get(random_id=random_id)
            customer_history = CustomerHistory.objects.get(history=history)

            return Response({
                'id': customer_history.id,
                'random_id': history.random_id,
                'customer_name': customer_history.fullname,
                'timestamp': format_vietnam_timestamp(history.timestamp),
                'total_amount': float(history.total_amount),
                'products': json.loads(history.product),
                'guest_name': customer_history.guest_name,
                'is_registered': bool(customer_history.customer)
            })

        except History.DoesNotExist:
            return Response(
                {'error': f'History with random_id {random_id} not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )

class CustomerPurchaseHistoryView(APIView):
    """API to get customer's purchase history by phone number."""
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description="Get customer's purchase history by phone number",
        manual_parameters=[
            openapi.Parameter(
                'phone_number',
                openapi.IN_QUERY,
                description="Customer's phone number",
                type=openapi.TYPE_STRING,
                required=True
            ),
        ],
        responses={
            200: "Purchase history retrieved successfully",
            404: "Customer not found"
        }
    )
    def get(self, request):
        phone_number = request.query_params.get('phone_number')
        if not phone_number:
            return Response(
                {'error': 'Phone number is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Tìm customer theo số điện thoại
            customer = Customer.objects.get(user__username=phone_number)
            
            # Lấy tất cả lịch sử mua hàng của customer này
            histories = CustomerHistory.objects.filter(
                customer=customer
            ).select_related('history').order_by('-history__timestamp')

            data = []
            for history in histories:
                history_data = {
                    'random_id': history.history.random_id,
                    'timestamp': format_vietnam_timestamp(history.history.timestamp),
                    'total_amount': float(history.history.total_amount),
                    'products': json.loads(history.history.product),
                    'customer_name': history.fullname
                }
                data.append(history_data)

            return Response(data)

        except Customer.DoesNotExist:
            return Response(
                {'error': 'Customer not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )

class CustomerTotalSpendingView(APIView):
    """API to get customer's total spending amount by phone number."""
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description="Get customer's total spending amount by phone number",
        manual_parameters=[
            openapi.Parameter(
                'phone_number',
                openapi.IN_QUERY,
                description="Customer's phone number",
                type=openapi.TYPE_STRING,
                required=True
            ),
        ],
        responses={
            200: openapi.Response(
                description="Total spending retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'customer_name': openapi.Schema(type=openapi.TYPE_STRING),
                        'total_spending': openapi.Schema(type=openapi.TYPE_NUMBER),
                        'purchase_count': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'first_purchase': openapi.Schema(type=openapi.TYPE_STRING),
                        'last_purchase': openapi.Schema(type=openapi.TYPE_STRING),
                        'average_amount': openapi.Schema(type=openapi.TYPE_NUMBER),
                    }
                )
            ),
            404: "Customer not found"
        }
    )
    def get(self, request):
        phone_number = request.query_params.get('phone_number')
        if not phone_number:
            return Response(
                {'error': 'Phone number is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            customer = Customer.objects.get(user__username=phone_number)
            customer_histories = CustomerHistory.objects.filter(customer=customer).select_related('history')
            
            if not customer_histories:
                return Response({
                    'customer_name': customer.fullname,
                    'total_spending': 0,
                    'purchase_count': 0,
                    'first_purchase': None,
                    'last_purchase': None,
                    'average_amount': 0
                })

            # Calculate total spending and other stats
            total_spending = sum(history.history.total_amount for history in customer_histories)
            purchase_count = customer_histories.count()
            
            # Get first and last purchase dates
            first_purchase = customer_histories.order_by('history__timestamp').first().history.timestamp
            last_purchase = customer_histories.order_by('-history__timestamp').first().history.timestamp
            
            # Calculate average amount per purchase
            average_amount = total_spending / purchase_count if purchase_count > 0 else 0
            
            return Response({
                'customer_name': customer.fullname,
                'total_spending': float(total_spending),
                'purchase_count': purchase_count,
                'first_purchase': format_vietnam_timestamp(first_purchase),
                'last_purchase': format_vietnam_timestamp(last_purchase),
                'average_amount': float(average_amount)
            })

        except Customer.DoesNotExist:
            return Response(
                {'error': 'Customer not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )

class FavoriteProductView(APIView):
    """API to manage customer's favorite products."""
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Add product to favorites", 
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['phone_number', 'product_number'],
            properties={
                'phone_number': openapi.Schema(type=openapi.TYPE_STRING, description="Customer's phone number"),
                'product_number': openapi.Schema(type=openapi.TYPE_STRING, description="Product name to add to favorites")
            }
        ),
        responses={
            201: "Product added to favorites successfully",
            200: "Product already in favorites",
            404: "Customer or product not found"
        }
    )
    def post(self, request):
        phone_number = request.data.get('phone_number')
        product_number = request.data.get('product_number')

        try:
            customer = Customer.objects.get(user__username=phone_number)
            product = Product.objects.get(name=product_number)
            
            # Check if product already in favorites
            if customer.favorites.filter(name=product_number).exists():
                return Response({
                    'message': 'Product is already in favorites',
                    'is_favorite': True,
                    'product': {
                        'name': product.name,
                        'price': float(product.price),
                        'image_url': product.image_url if product.image_url else None
                    }
                }, status=status.HTTP_200_OK)
            
            # Add to favorites if not exists
            customer.favorites.add(product)
            
            return Response({
                'message': 'Product added to favorites successfully',
                'product': {
                    'name': product.name,
                    'price': float(product.price),
                    'image_url': product.image_url if product.image_url else None
                }
            }, status=status.HTTP_201_CREATED)

        except Customer.DoesNotExist:
            return Response(
                {'error': 'Customer not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Product.DoesNotExist:
            return Response(
                {'error': 'Product not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )

    @swagger_auto_schema(
        operation_description="Get customer's favorite products",
        manual_parameters=[
            openapi.Parameter(
                'phone_number',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="Customer's phone number",
                required=True
            )
        ],
        responses={
            200: "List of favorite products retrieved successfully",
            404: "Customer not found"
        }
    )
    def get(self, request):
        phone_number = request.query_params.get('phone_number')
        if not phone_number:
            return Response(
                {'error': 'Phone number is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            customer = Customer.objects.get(user__username=phone_number)
            favorites = customer.favorites.all()
            
            favorite_products = [{
                'number': product.product_id,
                'name': product.name,
                'price': float(product.price),
                'image_url': product.image_url if hasattr(product, 'image_url') else None
            } for product in favorites]

            return Response(favorite_products)

        except Customer.DoesNotExist:
            return Response(
                {'error': 'Customer not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )

    @swagger_auto_schema(
        operation_description="Check and delete a product from customer's favorites",
        manual_parameters=[
            openapi.Parameter(
                'phone_number',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="Customer's phone number",
                required=True
            ),
            openapi.Parameter(
                'product_number',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="Product name to check/delete",
                required=True
            )
        ],
        responses={
            200: "Product status in favorites",
            204: "Product removed from favorites",
            404: "Customer or product not found"
        }
    )
    def delete(self, request):
        phone_number = request.query_params.get('phone_number')
        product_number = request.query_params.get('product_number')

        try:
            customer = Customer.objects.get(user__username=phone_number)
            product = Product.objects.get(name=product_number)
            
            # Check if product is in favorites
            is_favorite = customer.favorites.filter(name=product_number).exists()
            
            if not is_favorite:
                return Response({
                    'message': 'Product is not in favorites',
                    'is_favorite': False
                }, status=status.HTTP_200_OK)
            
            # Remove from favorites if exists
            customer.favorites.remove(product)
            
            return Response({
                'message': 'Product removed from favorites successfully',
                'is_favorite': False,
                'product': {
                    'name': product.name,
                    'price': float(product.price),
                    'image_url': product.image_url if product.image_url else None
                }
            }, status=status.HTTP_200_OK)

        except Customer.DoesNotExist:
            return Response(
                {'error': 'Customer not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Product.DoesNotExist:
            return Response(
                {'error': 'Product not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )

class ProductDetailByNameView(APIView):
    """API to get product details by product name."""
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description="Get product details by product name",
        manual_parameters=[
            openapi.Parameter(
                'product_name',
                openapi.IN_QUERY,
                description="Name of the product",
                type=openapi.TYPE_STRING,
                required=True
            ),
        ],
        responses={
            200: openapi.Response(
                description="Product details retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'product_id': openapi.Schema(type=openapi.TYPE_INTEGER),  # Add this line
                        'name': openapi.Schema(type=openapi.TYPE_STRING),
                        'price': openapi.Schema(type=openapi.TYPE_NUMBER),
                        'quantity': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'category': openapi.Schema(type=openapi.TYPE_STRING),
                        'description': openapi.Schema(type=openapi.TYPE_STRING),
                        'image_url': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            404: "Product not found"
        }
    )
    def get(self, request):
        product_name = request.query_params.get('product_name')
        if not product_name:
            return Response(
                {'error': 'Product name is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            product = Product.objects.get(name=product_name)
            product_data = {
                'product_id': product.product_id,
                'name': product.name,
                'price': float(product.price),
                'quantity': product.quantity,
                'category': product.category,
                'description': product.description,
                'image_url': product.image_url if product.image_url else None
            }
            return Response(product_data)

        except Product.DoesNotExist:
            return Response(
                {'error': f'Product with name {product_name} not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )

class ProductSearchView(APIView):
    """API to search products by name."""
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description="Search products by name",
        manual_parameters=[
            openapi.Parameter(
                'query',
                openapi.IN_QUERY,
                description="Search term",
                type=openapi.TYPE_STRING,
                required=True
            ),
        ],
        responses={
            200: openapi.Response(
                description="Search results",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'product_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'name': openapi.Schema(type=openapi.TYPE_STRING),
                            'price': openapi.Schema(type=openapi.TYPE_NUMBER),
                            'category': openapi.Schema(type=openapi.TYPE_STRING),
                            'image_url': openapi.Schema(type=openapi.TYPE_STRING),
                        }
                    )
                )
            )
        }
    )
    def get(self, request):
        query = request.query_params.get('query', '').strip()
        if not query:
            return Response(
                {'error': 'Search query is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Sửa lại phần filter và đóng ngoặc cho đúng
        products = Product.objects.filter(
            name__icontains=query
        ).values('product_id', 'name', 'price', 'category', 'image_url')

        results = [{
            'product_id': product['product_id'],
            'name': product['name'],
            'price': float(product['price']),
            'category': product['category'],
            'image_url': product['image_url'] if product['image_url'] else None
        } for product in products]

        return Response(results)

class ProductRatingView(APIView):
    """API to manage product ratings."""
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Add rating for a product",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['product_name', 'star'],
            properties={
                'product_name': openapi.Schema(type=openapi.TYPE_STRING),
                'star': openapi.Schema(type=openapi.TYPE_NUMBER, format='double', minimum=0, maximum=5),
            }
        ),
        responses={
            201: "Rating added successfully",
            400: "Invalid data"
        }
    )
    def post(self, request):
        serializer = ProductRatingSerializer(data=request.data)
        if serializer.is_valid():
            # Validate star rating
            star = float(request.data.get('star', 0))
            if not 0 <= star <= 5:
                return Response(
                    {'error': 'Star rating must be between 0 and 5'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # Save rating
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_description="Get ratings for a product",
        manual_parameters=[
            openapi.Parameter(
                'product_name',
                openapi.IN_QUERY,
                description="Name of the product to get ratings for",
                type=openapi.TYPE_STRING,
                required=True
            ),
        ],
        responses={
            200: openapi.Response(
                description="Product ratings retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'product_name': openapi.Schema(type=openapi.TYPE_STRING),
                        'average_rating': openapi.Schema(type=openapi.TYPE_NUMBER),
                        'total_ratings': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'ratings': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'product_name': openapi.Schema(type=openapi.TYPE_STRING),
                                    'star': openapi.Schema(type=openapi.TYPE_NUMBER),
                                    'created_at': openapi.Schema(type=openapi.TYPE_STRING)
                                }
                            )
                        )
                    }
                )
            ),
            400: "Product name is required",
            404: "Product not found"
        }
    )
    def get(self, request):
        product_name = request.query_params.get('product_name')
        if not product_name:
            return Response(
                {'error': 'Product name is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        ratings = ProductRating.objects.filter(
            product_name=product_name
        ).order_by('-created_at')
        
        serializer = ProductRatingSerializer(ratings, many=True)
        
        # Calculate average rating with 1 decimal place
        avg_rating = ratings.aggregate(Avg('star'))['star__avg'] or 0
        avg_rating = float(format(avg_rating, '.1f'))  # Format to 1 decimal place
        total_ratings = ratings.count()
        
        return Response({
            'product_name': product_name,
            'average_rating': avg_rating,  # Now returns with 1 decimal place
            'total_ratings': total_ratings,
            'ratings': serializer.data
        })

class CustomerDeviceConnectionView(APIView):
    """API to connect customer or guest to a device."""
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description="Connect customer or guest to device. Empty phone_number for guest.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['device_id'],
            properties={
                'phone_number': openapi.Schema(type=openapi.TYPE_STRING, description="Customer phone number (empty for guest)"),
                'device_id': openapi.Schema(type=openapi.TYPE_STRING),
            }
        ),
        responses={
            200: "Connection successful",
            400: "Bad request",
            404: "Device not found"
        }
    )
    def post(self, request):
        phone_number = request.data.get('phone_number', '').strip()
        device_id = request.data.get('device_id')

        if not device_id:
            return Response(
                {'error': 'Device ID is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Get device
            device = DeviceConnection.objects.get(device_id=device_id)
            
            # Update device's last_connected timestamp
            device.save()  # Trigger auto_now for last_connected
            
            # Get or create device status
            device_status, _ = DeviceStatus.objects.get_or_create(
                device=device,
                defaults={'status': 'available'}
            )

            # Check if device is available
            if device_status.status != 'available':
                return Response({
                    'error': f'Device is currently {device_status.status}'
                }, status=status.HTTP_400_BAD_REQUEST)

            # End any existing active sessions for this device
            existing_session = CustomerDeviceSession.objects.filter(
                device=device,
                end_time__isnull=True
            ).first()
            
            if existing_session:
                # End the existing session properly
                existing_session.end_time = timezone.now()
                existing_session.save()

            # Handle registered customer or guest
            customer = None
            is_guest = True
            
            if phone_number:
                try:
                    customer = Customer.objects.get(user__username=phone_number)
                    is_guest = False
                except Customer.DoesNotExist:
                    return Response(
                        {'error': 'Customer not found'}, 
                        status=status.HTTP_404_NOT_FOUND
                    )

            # Start session
            device_status.status = 'in_use'
            device_status.current_user = customer
            device_status.session_start = timezone.now()
            device_status.save()

            # Create a session record with explicit is_guest flag
            CustomerDeviceSession.objects.create(
                customer=customer,
                device=device,
                is_guest=is_guest
            )

            # Convert UTC time to Vietnam timezone
            vietnam_tz = pytz.timezone('Asia/Ho_Chi_Minh')
            session_start_vietnam = device_status.session_start.astimezone(vietnam_tz)

            return Response({
                'message': 'Connected successfully',
                'customer_name': customer.fullname if customer else 'Guest',
                'device_name': device_status.device.device_name,
                'session_start': session_start_vietnam.isoformat(),
                'is_guest': is_guest
            })

        except DeviceConnection.DoesNotExist:
            return Response(
                {'error': 'Device not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )

class DeviceConnectionStatusView(APIView):
    """API to get the status of a device."""
    permission_classes = [AllowAny]

    def get(self, request, device_id):
        try:
            # First check if device exists
            device = DeviceConnection.objects.filter(device_id=device_id).first()
            if not device:
                return Response(
                    {'message': 'Device not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            with transaction.atomic():
                device_status = DeviceStatus.objects.select_for_update().filter(
                    device__device_id=device_id
                ).first()

                if not device_status:
                    return Response(
                        {'message': 'Device not found'},
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                # Ensure database is up to date
                device_status.refresh_from_db()
                print(f"Device status after refresh: {device_status.status}")

                # Build response with customer phone number
                response_data = {
                    'status': device_status.status,
                    'device_name': device_status.device.device_name,
                    'customer_name': device_status.current_user.fullname if device_status.current_user else None,
                    'customer_phone': device_status.current_user.user.username if device_status.current_user else None,
                    'session_start': format_vietnam_timestamp(device_status.session_start) if device_status.session_start else None,
                    'session_duration': str(device_status.session_duration) if device_status.session_duration else None
                }
                
                print(f"Response data: {response_data}")
                return Response(response_data)

        except Exception as e:
            print(f"Error getting device status: {str(e)}")
            return Response(
                {'message': 'Device not found'},
                status=status.HTTP_404_NOT_FOUND
            )

class EndDeviceSessionView(APIView):
    """API to end a device session and record cancel shopping."""
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="End device session and record cancel shopping",
        responses={
            200: "Session ended successfully",
            404: "Device not found",
            400: "Error ending session"
        }
    )
    def post(self, request, device_id):
        try:
            device = DeviceConnection.objects.filter(device_id=device_id).first()
            if not device:
                return Response(
                    {"error": "Device not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
                
            # Update last_connected timestamp
            device.save()

            device_status = DeviceStatus.objects.filter(device=device).first()
            if not device_status:
                return Response(
                    {"error": "Device status not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )

            # Get the current session instead of relying on current_user
            current_session = CustomerDeviceSession.objects.filter(
                device=device,
                end_time__isnull=True
            ).first()

            if not current_session:
                return Response(
                    {"error": "No active session found"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Create cancel record for both registered customers and guests
            # Use proper Vietnam timezone
            vietnam_tz = pytz.timezone('Asia/Ho_Chi_Minh')
            cancel_time = timezone.now().astimezone(vietnam_tz)
            cancel_record = None
            
            if current_session.customer:
                # For registered customers
                cancel_record = CancelShopping.objects.create(
                    customer=current_session.customer,
                    device=device,
                    cancel_time=cancel_time,
                    message=f"Shopping cancelled by {current_session.customer.fullname} on device {device.device_name}"
                )
            else:
                # For guests, find or create a "Guest" customer record
                guest_username = "Dsoft-member"
                guest_customer, created = Customer.objects.get_or_create(
                    phone_number="guest",
                    defaults={
                        'user': User.objects.get_or_create(
                            username=guest_username,
                            defaults={'email': guest_username}
                        )[0],
                        'surname': '',
                        'firstname': 'Dsoft-member'
                    }
                )
                
                cancel_record = CancelShopping.objects.create(
                    customer=guest_customer,
                    device=device,
                    cancel_time=cancel_time,
                    message=f"Shopping cancelled by Dsoft-member on device {device.device_name}"
                )

            # End the session
            success = device_status.end_session()
            if success:
                # Format the cancel time for the response
                formatted_cancel_time = format_vietnam_timestamp(cancel_time)
                
                return Response({
                    "message": "Session ended successfully",
                    "cancel_time": formatted_cancel_time,
                    "device_name": device.device_name,
                    "customer_name": current_session.customer.fullname if current_session.customer else "Guest"
                }, status=status.HTTP_200_OK)
            else:
                return Response(
                    {"error": "Error ending session"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

class ShoppingMonitoringView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Get shopping monitoring data",
        manual_parameters=[
            openapi.Parameter(
                'phone_number',
                openapi.IN_QUERY,
                description="Customer's phone number (optional)",
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'device_id',
                openapi.IN_QUERY,
                description="Device ID",
                type=openapi.TYPE_STRING,
                required=True
            ),
        ],
        responses={
            200: openapi.Response(
                description="Shopping data retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'detected_products': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'product_name': openapi.Schema(type=openapi.TYPE_STRING),
                                    'quantity': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'price': openapi.Schema(type=openapi.TYPE_NUMBER),
                                }
                            )
                        ),
                        'total_bill': openapi.Schema(type=openapi.TYPE_NUMBER)
                    }
                )
            ),
            400: "Device ID is required",
            404: "Device not found"
        }
    )
    def get(self, request):
        phone_number = request.query_params.get('phone_number', '')  # Optional
        device_id = request.query_params.get('device_id')

        if not device_id:
            return Response(
                {'error': 'Device ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            device = DeviceConnection.objects.get(device_id=device_id)
            
            # Update last_connected timestamp
            device.save()
            
            device_status = DeviceStatus.objects.get(device=device)
            
            # Use correct status string "in_use" instead of "in use"
            if device_status.status != 'in_use':
                return Response({'error': 'Device is not in use'}, status=status.HTTP_400_BAD_REQUEST)
            
            current_session = CustomerDeviceSession.objects.filter(
                device=device,
                end_time__isnull=True
            ).select_related('customer').first()

            if not current_session:
                return Response({'error': 'No active session found'}, status=status.HTTP_404_NOT_FOUND)

            # Use current session's cart data if it exists, else return empty cart data
            cart_data = current_session.cart_data if current_session.cart_data else {}
            customer_name = device_status.current_user.fullname if device_status.current_user else "Guest"

            return Response({
                'customer_name': customer_name,
                'detected_products': cart_data.get('detected_products', []),
                'total_bill': cart_data.get('total_bill', 0)
            })
        except DeviceConnection.DoesNotExist:
            return Response(
                {'error': 'Device not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_description="Update shopping session data",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['phone_number', 'device_id', 'cart_data'],
            properties={
                'phone_number': openapi.Schema(type=openapi.TYPE_STRING),
                'device_id': openapi.Schema(type=openapi.TYPE_STRING),
                'cart_data': openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'detected_products': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'product_name': openapi.Schema(type=openapi.TYPE_STRING),
                                    'quantity': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'price': openapi.Schema(type=openapi.TYPE_NUMBER),
                                }
                            )
                        ),
                        'total_bill': openapi.Schema(type=openapi.TYPE_NUMBER)
                    }
                )
            }
        ),
        responses={
            200: "Shopping data updated successfully",
            404: "Customer or device not found",
            400: "Invalid data"
        }
    )
    def post(self, request):
        phone_number = request.data.get('phone_number', '').strip()  # optional for guest
        device_id = request.data.get('device_id')
        cart_data = request.data.get('cart_data')

        if not device_id or not cart_data:
            return Response({'error': 'Device ID and cart data are required'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            device = DeviceConnection.objects.get(device_id=device_id)
            
            # Update last_connected timestamp
            device.save()
            
            # Get the active session (if any)
            current_session = CustomerDeviceSession.objects.filter(
                device=device,
                end_time__isnull=True
            ).select_related('customer').first()

            if not current_session:
                return Response({'error': 'No active session found'},
                                status=status.HTTP_400_BAD_REQUEST)

            # If the session is for a registered customer, check the phone number
            if current_session.customer:
                if current_session.customer.user.username != phone_number:
                    # Update session's customer to the new correct one.
                    new_customer = Customer.objects.get(user__username=phone_number)
                    current_session.customer = new_customer
                    current_session.save()

            # Update session's cart data
            current_session.cart_data = cart_data
            current_session.save()

            return Response({
                'message': 'Shopping data updated successfully',
                'cart_data': current_session.cart_data
            }, status=status.HTTP_200_OK)

        except DeviceConnection.DoesNotExist:
            return Response({'error': 'Device not found'},
                            status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)},
                            status=status.HTTP_400_BAD_REQUEST)

class CheckEndSessionStatusView(APIView):
    """API to check the status of end session request."""
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Check status of end session request",
        responses={
            200: openapi.Response(
                description="Session status retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_STRING),
                        'device_status': openapi.Schema(type=openapi.TYPE_STRING),
                        'last_session_end': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            ),
            404: "Device not found"
        }
    )
    def get(self, request, device_id):
        try:
            with transaction.atomic():
                device_status = DeviceStatus.objects.select_for_update().get(
                    device__device_id=device_id
                )
                
                # Get last session data
                last_session = CustomerDeviceSession.objects.filter(
                    device__device_id=device_id
                ).order_by('-end_time').first()

                response_data = {
                    'status': 'success',
                    'device_status': device_status.status,
                    'last_session_end': (
                        format_vietnam_timestamp(last_session.end_time)
                        if last_session and last_session.end_time 
                        else None
                    )
                }
                
                return Response(response_data)

        except DeviceStatus.DoesNotExist:
            return Response(
                {'error': 'Device not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

@api_view(['GET'])
def get_all_device_status(request):
    """API to get the status of all devices."""
    devices = DeviceConnection.objects.all()
    device_status_list = []
    for device in devices:
        status = DeviceStatus.objects.filter(device=device).first()
        device_status_list.append({
            'device_id': device.device_id,
            'device_name': device.device_name,
            'status': status.status if status else 'unknown',
            'current_user': status.current_user.fullname if status and status.current_user else None,
            'session_start': status.session_start.isoformat() if status and status.session_start else None
        })
    return Response(device_status_list)

class AllDeviceStatusView(APIView):
    """API to get status of all devices."""
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Get status of all devices",
        responses={
            200: openapi.Response(
                description="All devices status retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'device_id': openapi.Schema(type=openapi.TYPE_STRING),
                            'device_name': openapi.Schema(type=openapi.TYPE_STRING),
                            'device_type': openapi.Schema(type=openapi.TYPE_STRING),
                            'ip_address': openapi.Schema(type=openapi.TYPE_STRING),
                            'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                            'app_running': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                            'last_connected': openapi.Schema(type=openapi.TYPE_STRING),
                            'created_at': openapi.Schema(type=openapi.TYPE_STRING),
                            'status': openapi.Schema(type=openapi.TYPE_STRING),
                            'customer_name': openapi.Schema(type=openapi.TYPE_STRING),
                            'customer_phone': openapi.Schema(type=openapi.TYPE_STRING),
                            'session_start': openapi.Schema(type=openapi.TYPE_STRING),
                            'session_duration': openapi.Schema(type=openapi.TYPE_STRING),
                        }
                    )
                )
            )
        }
    )
    def get(self, request):
        try:
            devices = DeviceConnection.objects.all()
            device_status_list = []
            
            for device in devices:
                # Get device status
                device_status = DeviceStatus.objects.filter(device=device).first()
                
                device_info = {
                    # Basic device info
                    'device_id': device.device_id,
                    'device_name': f"Smart Cart Display {device.device_id.split('_')[-1]}",
                    'device_type': device.device_type,
                    'ip_address': device.ip_address or "",
                    'is_active': device.is_active,
                    'app_running': device.app_running,
                    'last_connected': format_vietnam_timestamp(device.last_connected),
                    'created_at': format_vietnam_timestamp(device.created_at),
                    
                    # Additional status info
                    'status': device_status.status if device_status else 'unknown',
                    'customer_name': device_status.current_user.fullname if device_status and device_status.current_user else None,
                    'customer_phone': device_status.current_user.phone_number if device_status and device_status.current_user else None,
                    'session_start': format_vietnam_timestamp(device_status.session_start) if device_status and device_status.session_start else None,
                    'session_duration': str(device_status.session_duration) if device_status and device_status.session_duration else None
                }
                device_status_list.append(device_info)

            return Response(device_status_list)

        except Exception as e:
            print(f"[ERROR] Exception occurred: {str(e)}")
            return Response(
                {"error": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class CustomerChatView(APIView):
    """API to handle customer-admin chat messages."""
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Send chat message to admin",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['phone_number', 'message'],
            properties={
                'phone_number': openapi.Schema(type=openapi.TYPE_STRING),
                'message': openapi.Schema(type=openapi.TYPE_STRING),
            }
        ),
        responses={
            201: "Message sent successfully",
            400: "Invalid data",
            404: "Customer not found"
        }
    )
    def post(self, request):
        phone_number = request.data.get('phone_number')
        message = request.data.get('message')

        if not phone_number or not message:
            return Response(
                {'error': 'Both phone number and message are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            customer = Customer.objects.get(user__username=phone_number)
            chat_message = ChatMessage.objects.create(
                customer=customer,
                phone_number=phone_number,
                message=message,
                is_from_admin=False
            )
            
            serializer = ChatMessageSerializer(chat_message)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Customer.DoesNotExist:
            return Response(
                {'error': 'Customer not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @swagger_auto_schema(
        operation_description="Get chat history",
        manual_parameters=[
            openapi.Parameter(
                'phone_number',
                openapi.IN_QUERY,
                description="Customer's phone number",
                type=openapi.TYPE_STRING,
                required=True
            ),
        ],
        responses={
            200: openapi.Response(
                description="Chat history retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'message': openapi.Schema(type=openapi.TYPE_STRING),
                            'is_from_admin': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                            'created_at': openapi.Schema(type=openapi.TYPE_STRING),
                            'read': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        }
                    )
                )
            ),
            404: "Customer not found"
        }
    )
    def get(self, request):
        phone_number = request.query_params.get('phone_number')
        if not phone_number:
            return Response(
                {'error': 'Phone number is required'},
                status=status.HTTP_400_BAD_REQUEST  
            )

        try:
            customer = Customer.objects.get(user__username=phone_number)
            messages = ChatMessage.objects.filter(customer=customer)
            
            # Mark all admin messages as read
            messages.filter(is_from_admin=True, read=False).update(read=True)
            
            serializer = ChatMessageSerializer(messages, many=True)
            return Response(serializer.data)

        except Customer.DoesNotExist:
            return Response(
                {'error': 'Customer not found'},
                status=status.HTTP_404_NOT_FOUND
            )

# Admin view for chat messages
class AdminChatView(APIView):
    """API for admin to handle chat messages."""
    permission_classes = [AllowAny]  # You might want to add proper admin authentication

    @swagger_auto_schema(
        operation_description="Get all unread messages for admin",
        responses={
            200: "Unread messages retrieved successfully"
        }
    )
    def get(self, request):
        # Get all unique customers with unread messages
        customers_with_messages = ChatMessage.objects.filter(
            is_from_admin=False,
            read=False
        ).values('customer', 'phone_number').distinct()

        unread_messages = []
        for customer in customers_with_messages:
            latest_message = ChatMessage.objects.filter(
                customer_id=customer['customer']
            ).order_by('-created_at').first()

            if latest_message:
                unread_messages.append({
                    'customer_id': customer['customer'],
                    'phone_number': customer['phone_number'],
                    'last_message': latest_message.message,
                    'created_at': format_vietnam_timestamp(latest_message.created_at)
                })

        return Response(unread_messages)

    @swagger_auto_schema(
        operation_description="Send admin reply to customer",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['phone_number', 'message'],
            properties={
                'phone_number': openapi.Schema(type=openapi.TYPE_STRING),
                'message': openapi.Schema(type=openapi.TYPE_STRING),
            }
        ),
        responses={
            201: "Reply sent successfully",
            404: "Customer not found"
        }
    )
    def post(self, request):
        phone_number = request.data.get('phone_number')
        message = request.data.get('message')

        try:
            customer = Customer.objects.get(user__username=phone_number)
            chat_message = ChatMessage.objects.create(
                customer=customer,
                phone_number=phone_number,
                message=message,
                is_from_admin=True
            )

            # Mark all customer messages as read
            ChatMessage.objects.filter(
                customer=customer,
                is_from_admin=False,
                read=False
            ).update(read=True)

            serializer = ChatMessageSerializer(chat_message)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Customer.DoesNotExist:
            return Response(
                {'error': 'Customer not found'},
                status=status.HTTP_404_NOT_FOUND
            )

@login_required
def chat_view(request):
    """View for admin chat interface."""
    return render(request, 'chat.html')

# ...rest of the code...

class CancelShoppingView(APIView):
    """API to handle cancel shopping requests."""
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Cancel shopping session",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['username', 'device_id'],
            properties={
                'username': openapi.Schema(type=openapi.TYPE_STRING),
                'device_id': openapi.Schema(type=openapi.TYPE_STRING),
            }
        ),
        responses={
            201: "Shopping session cancelled successfully",
            404: "Customer or device not found",
            400: "Invalid data"
        }
    )
    def post(self, request):
        try:
            username = request.data.get('username')
            device_id = request.data.get('device_id')

            if not username or not device_id:
                return Response(
                    {"error": "Username and device_id are required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get customer
            customer = Customer.objects.filter(phone_number=username).first()
            if not customer:
                return Response(
                    {"error": "Customer not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )

            # Get device
            device = DeviceConnection.objects.filter(device_id=device_id).first()
            if not device:
                return Response(
                    {"error": "Device not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
                
            # Update last_connected timestamp
            device.save()

            # Create cancel record with proper Vietnam timezone
            vietnam_tz = pytz.timezone('Asia/Ho_Chi_Minh')
            cancel_time = timezone.now().astimezone(vietnam_tz)
            
            CancelShopping.objects.create(
                customer=customer,
                device=device,
                cancel_time=cancel_time,
                message=f"Shopping cancelled by {customer.fullname} on device {device.device_name}"
            )

            # Format the cancel time for the response
            formatted_cancel_time = format_vietnam_timestamp(cancel_time)
            
            return Response({
                "message": "Shopping cancelled successfully",
                "cancel_time": formatted_cancel_time,
                "device_name": device.device_name,
                "customer_name": customer.fullname
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

class CancelShoppingHistoryView(APIView):
    """API to get cancel shopping history."""
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Get cancel shopping history for a customer",
        manual_parameters=[
            openapi.Parameter(
                'username',
                openapi.IN_QUERY,
                description="Customer's username/phone number",
                type=openapi.TYPE_STRING,
                required=True
            ),
        ],
        responses={
            200: openapi.Response(
                description="Cancel history retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'cancel_time': openapi.Schema(type=openapi.TYPE_STRING),
                            'message': openapi.Schema(type=openapi.TYPE_STRING),
                        }
                    )
                )
            ),
            404: "Customer not found"
        }
    )
    def get(self, request):
        try:
            username = request.query_params.get('username')
            if not username:
                return Response(
                    {"error": "Username is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get customer
            customer = Customer.objects.filter(phone_number=username).first()
            if not customer:
                return Response(
                    {"error": "Customer not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )

            # Get cancel history
            cancel_history = CancelShopping.objects.filter(customer=customer).order_by('-cancel_time')
            
            history_data = [{
                'cancel_time': format_vietnam_timestamp(record.cancel_time),
                'message': record.message
            } for record in cancel_history]

            return Response(history_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import ShoppingRatingSerializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

class ShoppingRatingView(APIView):
    """API to handle shopping transaction ratings."""
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Create or update shopping rating",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['phone_number', 'random_id', 'rating'],
            properties={
                'phone_number': openapi.Schema(type=openapi.TYPE_STRING),
                'random_id': openapi.Schema(type=openapi.TYPE_STRING),
                'rating': openapi.Schema(type=openapi.TYPE_INTEGER, enum=[1, 2, 3, 4, 5]),
                'comment': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
            }
        ),
        responses={
            201: "Rating created successfully",
            400: "Invalid data",
            404: "Customer or transaction not found"
        }
    )
    def post(self, request):
        phone_number = request.data.get('phone_number')
        random_id = request.data.get('random_id')
        rating = request.data.get('rating')
        comment = request.data.get('comment')

        try:
            customer = Customer.objects.get(user__username=phone_number)
            history = History.objects.get(random_id=random_id)

            # Validate rating
            if not isinstance(rating, int) or not (1 <= rating <= 5):
                return Response(
                    {'error': 'Rating must be an integer between 1 and 5'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Create or update rating
            shopping_rating, created = ShoppingRating.objects.update_or_create(
                customer=customer,
                history=history,
                defaults={
                    'rating': rating,
                    'comment': comment or ''
                }
            )

            return Response({
                'id': shopping_rating.id,
                'customer_name': customer.fullname,
                'rating': rating,
                'comment': comment,
                'created_at': shopping_rating.created_at
            }, status=status.HTTP_201_CREATED)

        except Customer.DoesNotExist:
            return Response(
                {'error': 'Customer not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except History.DoesNotExist:
            return Response(
                {'error': 'Transaction not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @swagger_auto_schema(
        operation_description="Get rating for a shopping transaction",
        manual_parameters=[
            openapi.Parameter(
                'random_id',
                openapi.IN_QUERY,
                description="Random ID of the shopping transaction",
                type=openapi.TYPE_STRING,
                required=True
            ),
        ],
        responses={
            200: "Rating retrieved successfully",
            404: "Rating not found"
        }
    )
    def get(self, request):
        random_id = request.query_params.get('random_id')
        if not random_id:
            return Response(
                {'error': 'random_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            history = History.objects.get(random_id=random_id)
            rating = ShoppingRating.objects.get(history=history)
            
            return Response({
                'id': rating.id,
                'customer_name': rating.customer.fullname,
                'rating': rating.rating,
                'comment': rating.comment,
                'created_at': rating.created_at
            })
        except History.DoesNotExist:
            return Response(
                {'error': 'Transaction not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ShoppingRating.DoesNotExist:
            return Response(
                {'error': 'Rating not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

class PaymentShoppingView(APIView):
    """API to handle payment shopping requests."""
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Handle payment requests and history",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['device_id'],
            properties={
                'device_id': openapi.Schema(type=openapi.TYPE_STRING),
                'status': openapi.Schema(type=openapi.TYPE_STRING, enum=['pending', 'completed', 'failed']),
                'amount': openapi.Schema(type=openapi.TYPE_NUMBER),
                'phone_number': openapi.Schema(type=openapi.TYPE_STRING, description="Customer's phone number (optional)"),
            }
        ),
        manual_parameters=[
            openapi.Parameter(
                'phone_number',
                openapi.IN_QUERY,
                description="Customer's phone number to get payment history",
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'device_id',
                openapi.IN_QUERY,
                description="Device ID to get payments",
                type=openapi.TYPE_STRING, 
                required=False
            ),
            openapi.Parameter(
                'status',
                openapi.IN_QUERY, 
                description="Filter by payment status",
                type=openapi.TYPE_STRING,
                required=False,
                enum=['pending', 'completed', 'failed']
            )
        ],
        responses={
            200: "Payment history retrieved successfully",
            201: "Payment recorded successfully",
            400: "Invalid request",
            404: "Customer or device not found"
        }
    )
    def post(self, request):
        try:
            # Get payment data
            device_id = request.data.get('device_id')
            status_val = request.data.get('status', 'pending')
            amount = request.data.get('amount')
            phone_number = request.data.get('phone_number')
            
            if not device_id:
                return Response(
                    {"error": "device_id is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate payment status
            if status_val not in ['pending', 'completed', 'failed']:
                return Response(
                    {"error": "Invalid status. Must be 'pending', 'completed', or 'failed'"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # Get device
            device = DeviceConnection.objects.get(device_id=device_id)
            if not device.is_active:
                return Response(
                    {"error": "Device is not active"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            customer = None
            if phone_number:
                try:
                    customer = Customer.objects.get(user__username=phone_number)
                except Customer.DoesNotExist:
                    return Response(
                        {"error": "Customer not found"}, 
                        status=status.HTTP_404_NOT_FOUND
                    )
            
            # Get current session
            current_session = CustomerDeviceSession.objects.filter(
                device=device, end_time__isnull=True
            ).first()
            
            # If explicit customer not provided, use session customer if available
            if not customer and current_session and current_session.customer:
                customer = current_session.customer
                
            # Create payment record
            payment = PaymentShopping.objects.create(
                customer=customer,
                device=device,
                payment_time=timezone.now(),
                status=status_val,
                amount=amount if amount else 0,
                message=f"Payment {status_val}"
            )
            
            # If customer has FCM token, send notification
            if customer and customer.fcm_token:
                try:
                    # Get relevant device details
                    device_name = device.device_name
                    
                    # Create appropriate message based on status
                    if status_val == 'completed':
                        notif_title = "Payment Completed"
                        notif_message = f"Your payment of {amount} VND has been successfully processed."
                    elif status_val == 'failed':
                        notif_title = "Payment Failed"
                        notif_message = f"Your payment of {amount} VND could not be processed. Please try again."
                    else:
                        notif_title = "Payment Processing"
                        notif_message = f"Your payment of {amount} VND is being processed."
                    
                    # Create notification in database
                    notification = Notification.objects.create(
                        user=customer,
                        notif_type='personal',
                        title=notif_title,
                        message=notif_message,
                        is_read=False
                    )
                    
                    # Send Firebase push notification
                    try:
                        msg = messaging.Message(
                            notification=messaging.Notification(
                                title=notif_title,
                                body=notif_message
                            ),
                            data={
                                'type': 'payment',
                                'payment_id': str(payment.id),
                                'status': status_val,
                                'device_id': device_id,
                                'timestamp': format_vietnam_timestamp(payment.payment_time)
                            },
                            token=customer.fcm_token,
                        )
                        messaging.send(msg)
                    except Exception as e:
                        # If Firebase messaging fails, still continue - we've stored the notification in DB
                        print(f"Failed to send Firebase notification: {str(e)}")
                except Exception as e:
                    # If notification creation fails, log but continue with payment process
                    print(f"Failed to create payment notification: {str(e)}")
            
            return Response({
                'id': payment.id,
                'customer_name': customer.fullname if customer else 'Guest',
                'device_name': device.device_name,
                'payment_time': format_vietnam_timestamp(payment.payment_time),
                'status': payment.status,
                'amount': float(payment.amount),
                'message': payment.message
            }, status=status.HTTP_201_CREATED)
            
        except DeviceConnection.DoesNotExist:
            return Response(
                {"error": "Device not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def get(self, request):
        pass


class PaymentSignalView(APIView):
    """API to handle payment signals."""
    permission_classes = [AllowAny]

    def get(self, request, device_id):
        try:
            device = DeviceConnection.objects.get(device_id=device_id)
            if not device.is_active:
                return Response({
                    'error': 'Device is not active',
                    'status': 'offline'
                }, status=status.HTTP_400_BAD_REQUEST)

            device_status = DeviceStatus.objects.get(device=device)

            # When status is available, refresh data by clearing signals
            if device_status.status == 'available':
                cache.delete(f'payment_signal_{device_id}')
                cache.delete(f'cancel_payment_signal_{device_id}')
                return Response({
                    'device_id': device_id,
                    'device_name': device.device_name,
                    'status': 'available',
                    'customer_name': None,
                    'timestamp': None,
                    'message': "Device is available, refreshed.",
                    'signal_type': None
                })

            # Check for an active session
            current_session = CustomerDeviceSession.objects.filter(
                device=device,
                end_time__isnull=True
            ).first()
            if not current_session:
                cache.delete(f'payment_signal_{device_id}')
                cache.delete(f'cancel_payment_signal_{device_id}')
                return Response({
                    'device_id': device_id,
                    'device_name': device.device_name,
                    'status': device_status.status,
                    'customer_name': "Guest",
                    'timestamp': timezone.now().strftime("%d/%m/%Y %H:%M"),
                    'message': "No active session",
                    'signal_type': None
                })

            customer_name = current_session.customer.fullname if current_session and current_session.customer else "Guest"
            payment_signal = cache.get(f'payment_signal_{device_id}')
            cancel_signal = cache.get(f'cancel_payment_signal_{device_id}')

            if cancel_signal:
                response_data = {
                    'device_id': device_id,
                    'device_name': device.device_name,
                    'status': device_status.status,
                    'customer_name': customer_name,
                    'timestamp': timezone.now().strftime("%d/%m/%Y %H:%M"),
                    'message': "Cancel payment signal received",
                    'signal_type': 'cancel'
                }
            elif payment_signal:
                response_data = {
                    'device_id': device_id,
                    'device_name': device.device_name,
                    'status': device_status.status,
                    'customer_name': customer_name,
                    'timestamp': timezone.now().strftime("%d/%m/%Y %H:%M"),
                    'message': "Payment signal received",
                    'signal_type': 'payment'
                }
            else:
                response_data = {
                    'device_id': device_id,
                    'device_name': device.device_name,
                    'status': device_status.status,
                    'customer_name': customer_name,
                    'timestamp': timezone.now().strftime("%d/%m/%Y %H:%M"),
                    'message': "No active payment signal",
                    'signal_type': None
                }
            return Response(response_data)
        except DeviceConnection.DoesNotExist:
            return Response(
                {"error": "Device not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def post(self, request, device_id):
        try:
            device = DeviceConnection.objects.get(device_id=device_id)
            
            if not device.is_active:
                return Response({
                    'error': 'Device is not active',
                    'status': 'offline'
                }, status=status.HTTP_400_BAD_REQUEST)
                
            device_status = DeviceStatus.objects.get(device=device)

            if not device_status or device_status.status != 'in_use':
                return Response(
                    {"error": "No active session found"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            current_session = CustomerDeviceSession.objects.filter(
                device=device,
                end_time__isnull=True  
            ).first()

            if not current_session:
                return Response(
                    {"error": "No active session found"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Set payment signal in cache and clear any cancel signal
            cache_key = f'payment_signal_{device_id}'
            cancel_key = f'cancel_payment_signal_{device_id}'
            cache.set(cache_key, True, timeout=300)  # 5 minutes timeout
            cache.delete(cancel_key)  # Clear any cancel signal

            return Response({
                "message": "Payment signal received",
                "device_id": device_id,
                "device_name": device.device_name, 
                # Use device_status.current_user to show the new session's customer
                "customer_name": device_status.current_user.fullname if device_status.current_user else "Guest",
                "status": device_status.status,
                "timestamp": timezone.now().strftime("%d/%m/%Y %H:%M"),
                "signal_type": "payment"
            }, status=status.HTTP_200_OK)

        except DeviceConnection.DoesNotExist:
            return Response(
                {"error": "Device not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

class CancelPaymentSignalView(APIView):
    """API to handle cancel payment signals."""
    permission_classes = [AllowAny]

    def post(self, request, device_id):
        try:
            device = DeviceConnection.objects.get(device_id=device_id)
            if not device.is_active:
                return Response({
                    "error": "Device is not active"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            device_status = DeviceStatus.objects.get(device=device)
            current_session = CustomerDeviceSession.objects.filter(
                device=device, end_time__isnull=True
            ).first()

            # If no active session, clear stale signals and return default response
            if not current_session:
                cache.delete(f'cancel_payment_signal_{device_id}')
                cache.delete(f'payment_signal_{device_id}')
                return Response({
                    'device_id': device_id,
                    'device_name': device.device_name,
                    'status': device_status.status,
                    'customer_name': "Guest",
                    'timestamp': timezone.now().strftime("%d/%m/%Y %H:%M"),
                    'message': "No active session",
                    'signal_type': None
                }, status=status.HTTP_200_OK)

            customer_name = current_session.customer.fullname if current_session.customer else "Guest"

            # Set cancel signal in cache and clear any payment signal
            cancel_key = f'cancel_payment_signal_{device_id}'
            payment_key = f'payment_signal_{device_id}'
            cache.set(cancel_key, True, timeout=50)  
            cache.delete(payment_key)  # Clear payment signal

            return Response({
                "message": "Cancel payment signal received",
                "device_id": device_id,
                "device_name": device.device_name,
                "customer_name": customer_name,
                "status": device_status.status,
                "timestamp": timezone.now().strftime("%d/%m/%Y %H:%M"),
                "signal_type": "cancel"
            }, status=status.HTTP_200_OK)

        except DeviceConnection.DoesNotExist:
            return Response(
                {"error": "Device not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

class PaymentShoppingView(APIView):
    """API to get payments for a device."""
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Get payments for a device",
        manual_parameters=[
            openapi.Parameter(
                'device_id',
                openapi.IN_QUERY,
                description="Device ID to get payments for",
                type=openapi.TYPE_STRING,
                required=True
            )
        ],
        responses={
            200: openapi.Response(
                description="List of payments retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'customer_name': openapi.Schema(type=openapi.TYPE_STRING),
                            'device_name': openapi.Schema(type=openapi.TYPE_STRING),
                            'payment_time': openapi.Schema(type=openapi.TYPE_STRING),
                            'status': openapi.Schema(type=openapi.TYPE_STRING),
                            'amount': openapi.Schema(type=openapi.TYPE_NUMBER),
                            'message': openapi.Schema(type=openapi.TYPE_STRING)
                        }
                    )
                )
            ),
            400: "Device ID is required",
            404: "Device not found"
        }
    )
    def get(self, request):
        try:
            device_id = request.query_params.get('device_id')
            if not device_id:
                return Response(
                    {"error": "device_id is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get payments for device
            payments = PaymentShopping.objects.filter(
                device__device_id=device_id
            ).order_by('-payment_time')

            # Format response data
            payment_list = []
            for payment in payments:
                payment_data = {
                    'id': payment.id,
                    'customer_name': payment.customer.fullname if payment.customer else 'Guest',
                    'device_name': payment.device.device_name,
                    'payment_time': format_vietnam_timestamp(payment.payment_time),
                    'status': payment.status, 
                    'amount': float(payment.amount),
                    'message': payment.message
                }
                payment_list.append(payment_data)

            return Response(payment_list)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

class PaymentStatusView(APIView):
    """API to check payment status by device_id only."""
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Get payment status using only device_id",
        manual_parameters=[
            openapi.Parameter(
                'device_id',
                openapi.IN_QUERY,
                description="Device ID",
                type=openapi.TYPE_STRING,
                required=True
            )
        ],
        responses={
            200: openapi.Response(
                description="Payment status information",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'payment_success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'device_status': openapi.Schema(type=openapi.TYPE_STRING, description="Device status")
                    }
                )
            ),
            400: "Bad Request",
            404: "Device not found"
        }
    )
    def get(self, request):
        device_id = request.query_params.get('device_id')
        if not device_id:
            return Response(
                {'error': 'device_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            device = DeviceConnection.objects.get(device_id=device_id)
        except DeviceConnection.DoesNotExist:
            return Response(
                {'payment_success': False, 'device_status': 'Device not connected'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check if device is active
        if not device.is_active:
            return Response(
                {'payment_success': False, 'device_status': 'offline'},
                status=status.HTTP_200_OK
            )

        device_status_obj = DeviceStatus.objects.filter(device=device).first()
        if not device_status_obj:
            return Response(
                {'payment_success': False, 'device_status': 'No session'},
                status=status.HTTP_200_OK
            )

        # Check for payment flag in cache regardless of device_status
        payment_flag = cache.get(f'payment_success_{device_id}', False)
        if payment_flag:
            return Response({'payment_success': True, 'device_status': 'in use'}, status=status.HTTP_200_OK)

        if device_status_obj.status == 'in_use':
            return Response(
                {'payment_success': False, 'device_status': 'in use'},
                status=status.HTTP_200_OK
            )
        elif device_status_obj.status == 'not in use':
            ts = cache.get(f'payment_success_timestamp_{device_id}')
            if ts and (timezone.now() - ts).total_seconds() < 15:
                return Response(
                    {'payment_success': True, 'device_status': 'in use'},
                    status=status.HTTP_200_OK
                )
            payment_flag = cache.get(f'payment_success_{device_id}', False)
            return Response(
                {'payment_success': bool(payment_flag), 'device_status': 'not in use'},
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {'payment_success': False, 'device_status': device_status_obj.status},
                status=status.HTTP_200_OK
            )

# API lưu FCM token cho user
class SaveFCMTokenView(APIView):
    @swagger_auto_schema(
        operation_description="Save FCM token for a user",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["fcm_token", "phone_number"],
            properties={
                "fcm_token": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Firebase Cloud Messaging token",
                    example="AAAABBBBCCCC"
                ),
                "phone_number": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="User's phone number",
                    example="0123456789"
                )
            }
        ),
        responses={
            200: openapi.Response(
                description="FCM token saved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING, example="FCM token saved")
                    }
                )
            ),
            400: "fcm_token and phone_number required",
            404: "Customer not found"
        }
    )
    def post(self, request):
        token = request.data.get('fcm_token')
        phone = request.data.get('phone_number')
        
        # Validate inputs
        if not token or not phone:
            return Response({"error": "fcm_token and phone_number required"}, status=400)
        
        if not token.strip() or len(token.strip()) < 20:
            return Response({"error": "Invalid FCM token format"}, status=400)
            
        try:
            customer = Customer.objects.get(user__username=phone)
            old_token = customer.fcm_token
            
            # Store the new token
            customer.fcm_token = token.strip()
            customer.save()
            
            # Check if token changed and log it
            if old_token != token:
                print(f"FCM token updated for user {phone}: {token[:20]}...")
            
            # Try to register token to topic, but don't fail if it doesn't work
            try:
                register_result = register_token_to_topic(token, "all_users")
                if register_result:
                    return Response({
                        "message": "FCM token saved and registered to topics",
                        "status": "success"
                    }, status=200)
                else:
                    return Response({
                        "message": "FCM token saved but topic registration failed",
                        "status": "partial"
                    }, status=200)
            except Exception as e:
                print(f"Error registering token to topic: {str(e)}")
                return Response({
                    "message": "FCM token saved but topic registration failed",
                    "status": "partial",
                    "error": str(e)
                }, status=200)
                
        except Customer.DoesNotExist:
            return Response({"error": "Customer not found"}, status=404)
        except Exception as e:
            return Response({"error": f"Error saving token: {str(e)}"}, status=400)

class SendPersonalNotificationView(APIView):
    @swagger_auto_schema(
        operation_description="Send personal notification via FCM",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["phone_number", "title", "message"],
            properties={
                "phone_number": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Phone number of the user",
                    example="0123456789"
                ),
                "title": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Notification title",
                    example="Test Title"
                ),
                "message": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Notification message",
                    example="This is a test notification message."
                )
            }
        ),
        responses={
            200: openapi.Response(
                description="Notification sent successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING, example="Notification sent"),
                        "fcm_response": openapi.Schema(type=openapi.TYPE_STRING, example="fcm-response-string")
                    }
                )
            ),
            400: "Missing fields / No FCM token for user",
            404: "Customer not found"
        }
    )
    def post(self, request):
        phone = request.data.get('phone_number')
        title = request.data.get('title')
        message_text = request.data.get('message')
        if not phone or not title or not message_text:
            return Response({"error": "Missing fields"}, status=400)
        try:
            customer = Customer.objects.get(user__username=phone)
            if not customer.fcm_token:
                return Response({"error": "No FCM token for user"}, status=400)
            
            # Log the token for debugging
            print(f"Customer FCM token: {customer.fcm_token[:30]}...")
            
            # Create notification in DB (always create regardless of preference)
            Notification.objects.create(user=customer, notif_type='personal', title=title, message=message_text)
            
            # Check if the customer has enabled notifications
            preferences, created = CustomerPreferences.objects.get_or_create(
                customer=customer,
                defaults={
                    'notification_enabled': True,
                    'promo_notification_enabled': True,
                    'personal_notification_enabled': True
                }
            )
            
            # Only send push notification if personal notifications are enabled
            if preferences.personal_notification_enabled:
                # Send FCM notification
                legacy_response = send_fcm_legacy(customer.fcm_token, title, message_text)
                return Response({
                    "message": "Notification sent (using legacy method)", 
                    "fcm_response": legacy_response
                }, status=200)
            else:
                # Notification created in database but not sent as push
                return Response({
                    "message": "Notification created in database but not sent as push (personal notifications disabled)",
                    "fcm_response": None
                }, status=200)
            
        except Customer.DoesNotExist:
            return Response({"error": "Customer not found"}, status=404)

class BroadcastNotificationView(APIView):
    @swagger_auto_schema(
        operation_description="Broadcast promotional notification to all users.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["title", "message"],
            properties={
                "title": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Notification title",
                    example="Promo Alert"
                ),
                "message": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Notification message",
                    example="Big sale coming soon!"
                )
            }
        ),
        responses={
            200: openapi.Response(
                description="Broadcast sent successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING, example="Broadcast sent"),
                        "responses": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    # The key will be the customer's username and value the FCM response.
                                    "customer": openapi.Schema(type=openapi.TYPE_STRING, example="Customer 1")
                                }
                            )
                        )
                    }
                )
            ),
            400: "Missing title or message"
        }
    )
    def post(self, request):
        title = request.data.get('title')
        message_text = request.data.get('message')
        
        if not title or not message_text:
            return Response({"error": "Missing title or message"}, status=400)
        
        # Lấy tất cả khách hàng có FCM token
        customers = Customer.objects.exclude(fcm_token__isnull=True).exclude(fcm_token__exact='')
        
        # Create a single promo notification as a template
        promo_notification = Notification.objects.create(
            user=customers.first() if customers.exists() else None,  # Assign to first customer or None
            notif_type='promo',
            title=title,
            message=message_text
        )
        
        # Create read status entries for each customer
        for customer in customers:
            # Create read status entry for this customer
            NotificationReadStatus.objects.create(
                notification=promo_notification,
                customer=customer,
                is_read=False
            )
        
        # Only send FCM notifications to customers who have enabled promo notifications
        customers_with_promo_enabled = []
        for customer in customers:
            try:
                preference, created = CustomerPreferences.objects.get_or_create(
                    customer=customer,
                    defaults={
                        'notification_enabled': True,
                        'promo_notification_enabled': True,
                        'personal_notification_enabled': True
                    }
                )
                if preference.promo_notification_enabled:
                    customers_with_promo_enabled.append(customer)
            except Exception as e:
                print(f"Error checking notification preferences for {customer.user.username}: {e}")
        
        # Không gửi thông báo qua topic - chỉ gửi trực tiếp đến người dùng đã bật thông báo quảng cáo
        fcm_responses = []
        for customer in customers_with_promo_enabled:
            try:
                # Gửi thông báo bằng FCM Legacy để đảm bảo tương thích
                resp = send_fcm_legacy(customer.fcm_token, title, message_text)
                fcm_responses.append({customer.user.username: resp})
            except Exception as e:
                fcm_responses.append({customer.user.username: str(e)})
        
        return Response({
            "message": f"Broadcast sent to {len(customers_with_promo_enabled)} customers with promo notifications enabled",
            "total_customers": customers.count(),
            "enabled_notifications": len(customers_with_promo_enabled),
            "responses": fcm_responses
        }, status=status.HTTP_201_CREATED)

class NotificationSettingsView(APIView):
    """API to manage notification settings for customers."""
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description="Get notification settings for a customer",
        manual_parameters=[
            openapi.Parameter(
                'phone_number',
                openapi.IN_QUERY,
                description="Customer's phone number",
                type=openapi.TYPE_STRING,
                required=True
            ),
        ],
        responses={
            200: openapi.Response(
                description="Notification settings retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "phone_number": openapi.Schema(type=openapi.TYPE_STRING),
                        "promo_notifications_enabled": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "personal_notifications_enabled": openapi.Schema(type=openapi.TYPE_BOOLEAN)
                    }
                )
            ),
            404: "Customer not found"
        }
    )
    def get(self, request):
        phone_number = request.query_params.get('phone_number')
        if not phone_number:
            return Response({"error": "Phone number is required"}, status=400)
        
        try:
            customer = Customer.objects.get(user__username=phone_number)
            
            # Get or create preferences
            preferences, created = CustomerPreferences.objects.get_or_create(
                customer=customer,
                defaults={
                    'notification_enabled': True,
                    'promo_notification_enabled': True,
                    'personal_notification_enabled': True
                }
            )
            
            return Response({
                "phone_number": phone_number,
                "promo_notifications_enabled": preferences.promo_notification_enabled,
                "personal_notifications_enabled": preferences.personal_notification_enabled
            })
            
        except Customer.DoesNotExist:
            return Response({"error": "Customer not found"}, status=404)
    
    @swagger_auto_schema(
        operation_description="Update notification settings for a customer",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["phone_number"],
            properties={
                "phone_number": openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    description="Customer's phone number"
                ),
                "promo_notifications_enabled": openapi.Schema(
                    type=openapi.TYPE_BOOLEAN,
                    description="Enable/disable promotional notifications"
                ),
                "personal_notifications_enabled": openapi.Schema(
                    type=openapi.TYPE_BOOLEAN,
                    description="Enable/disable personal notifications"
                )
            }
        ),
        responses={
            200: openapi.Response(
                description="Settings updated successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "phone_number": openapi.Schema(type=openapi.TYPE_STRING),
                        "promo_notifications_enabled": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "personal_notifications_enabled": openapi.Schema(type=openapi.TYPE_BOOLEAN)
                    }
                )
            ),
            400: "Invalid data",
            404: "Customer not found"
        }
    )
    def post(self, request):
        phone_number = request.data.get('phone_number')
        promo_enabled = request.data.get('promo_notifications_enabled')
        personal_enabled = request.data.get('personal_notifications_enabled')
        
        if not phone_number:
            return Response({"error": "Phone number is required"}, status=400)
            
        try:
            customer = Customer.objects.get(user__username=phone_number)
            
            # Get or create preferences
            preferences, created = CustomerPreferences.objects.get_or_create(
                customer=customer,
                defaults={
                    'notification_enabled': True,
                    'promo_notification_enabled': True,
                    'personal_notification_enabled': True
                }
            )
            
            # Update notification settings for each type if provided
            if promo_enabled is not None:
                preferences.promo_notification_enabled = promo_enabled
                
            if personal_enabled is not None:
                preferences.personal_notification_enabled = personal_enabled
                
            # Set the general notification_enabled to True if either type is enabled
            preferences.notification_enabled = preferences.promo_notification_enabled or preferences.personal_notification_enabled
            preferences.save()
            
            return Response({
                "message": "Notification settings updated successfully",
                "phone_number": phone_number,
                "promo_notifications_enabled": preferences.promo_notification_enabled,
                "personal_notifications_enabled": preferences.personal_notification_enabled
            })
            
        except Customer.DoesNotExist:
            return Response({"error": "Customer not found"}, status=404)

class ListNotificationsView(APIView):
    @swagger_auto_schema(
        operation_description="Get all notification of a customer contain promo and order",
        manual_parameters=[
            openapi.Parameter(
                'phone_number',
                openapi.IN_QUERY,
                description="Phone number is required",
                required=["phone_number"],
                type=openapi.TYPE_STRING
            )
        ],
        responses={
            200: openapi.Response(
                description="List of notifications",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "random_id": openapi.Schema(type=openapi.TYPE_STRING),
                            "timestamp": openapi.Schema(
                                type=openapi.TYPE_STRING,
                                description="Timestamp formatted as dd/mm/YYYY HH:MM"
                            ),
                            "title": openapi.Schema(type=openapi.TYPE_STRING),
                            "message": openapi.Schema(type=openapi.TYPE_STRING),
                            "notif_type": openapi.Schema(type=openapi.TYPE_STRING),
                            "is_read": openapi.Schema(type=openapi.TYPE_BOOLEAN)
                        }
                    )
                )
            )
        }
    )
    def get(self, request):
        phone = request.query_params.get('phone_number')
        
        if phone:
            try:
                customer = Customer.objects.get(user__username=phone)
                
                # Get personal notifications for this customer
                personal_notifs = Notification.objects.filter(
                    user=customer, 
                    notif_type='personal'
                ).order_by('-created_at')
                
                # Get promo notifications with read status for this customer
                promo_notifs = Notification.objects.filter(
                    notif_type='promo'
                ).order_by('-created_at')
                
                # Get read status for promo notifications
                read_statuses = {
                    status.notification_id: status.is_read 
                    for status in NotificationReadStatus.objects.filter(
                        customer=customer,
                        notification__in=promo_notifs
                    )
                }
                
                # Combine both types of notifications
                data = []
                
                # Add personal notifications
                for notif in personal_notifs:
                    # Xử lý đặc biệt cho thông báo hoàn thành đơn hàng
                    message = notif.message
                    if notif.title in ["Completed Purchase", "Order Linked"]:
                        # Tìm ID đơn hàng trong message
                        match = re.search(r'ID: (\d+)', message)
                        if match:
                            # Nếu tìm thấy ID trong message, chỉ trả về ID
                            message = match.group(1)
                        else:
                            # Hoặc tìm số đầu tiên trong chuỗi
                            match = re.search(r'\d+', message)
                            if match:
                                message = match.group(0)
                            # Nếu không tìm thấy, giữ nguyên message

                    data.append({
                        "random_id": f"{notif.id}",
                        "timestamp": timezone.localtime(notif.created_at).strftime("%d/%m/%Y %H:%M"),
                        "title": notif.title,
                        "message": message,
                        "notif_type": notif.notif_type,
                        "is_read": notif.is_read
                    })
                
                # Add promo notifications with customer-specific read status
                for notif in promo_notifs:
                    # Default to False if no read status exists for this notification
                    is_read = read_statuses.get(notif.id, False)
                    
                    # Xử lý đặc biệt cho thông báo hoàn thành đơn hàng
                    message = notif.message
                    if notif.title in ["Completed Purchase", "Order Linked"]:
                        # Tìm ID đơn hàng trong message
                        match = re.search(r'ID: (\d+)', message)
                        if match:
                            # Nếu tìm thấy ID trong message, chỉ trả về ID
                            message = match.group(1)
                        else:
                            # Hoặc tìm số đầu tiên trong chuỗi
                            match = re.search(r'\d+', message)
                            if match:
                                message = match.group(0)
                            # Nếu không tìm thấy, giữ nguyên message
                    
                    data.append({
                        "random_id": f"{notif.id}",
                        "timestamp": timezone.localtime(notif.created_at).strftime("%d/%m/%Y %H:%M"),
                        "title": notif.title,
                        "message": message,
                        "notif_type": notif.notif_type,
                        "is_read": is_read
                    })
                
                # Sort by created_at (newest first)
                data.sort(key=lambda x: datetime.strptime(x['timestamp'], "%d/%m/%Y %H:%M"), reverse=True)
                
                return Response(data, status=200)
            except Customer.DoesNotExist:
                return Response({"error": "Customer not found"}, status=404)
        else:
            # When no phone number is provided, just return all promo notifications
            promo_notifs = Notification.objects.filter(notif_type='promo').order_by('-created_at')
            
            data = []
            for notif in promo_notifs:
                # Xử lý đặc biệt cho thông báo hoàn thành đơn hàng
                message = notif.message
                if notif.title in ["Completed Purchase", "Order Linked"]:
                    # Tìm ID đơn hàng trong message
                    match = re.search(r'ID: (\d+)', message)
                    if match:
                        # Nếu tìm thấy ID trong message, chỉ trả về ID
                        message = match.group(1)
                    else:
                        # Hoặc tìm số đầu tiên trong chuỗi
                        match = re.search(r'\d+', message)
                        if match:
                            message = match.group(0)
                        # Nếu không tìm thấy, giữ nguyên message
                
                data.append({
                    "random_id": f"{notif.id}",
                    "timestamp": timezone.localtime(notif.created_at).strftime("%d/%m/%Y %H:%M"),
                    "title": notif.title,
                    "message": message,
                    "notif_type": notif.notif_type,
                    "is_read": False  # Default to unread since we don't know the customer
                })
            
            return Response(data, status=200)

# API đánh dấu thông báo đã đọc
class MarkNotificationReadView(APIView):
    @swagger_auto_schema(
        operation_description="Mark notifications as read by providing a list of notification IDs and phone number.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["notification_ids", "phone_number"],
            properties={
                "notification_ids": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_INTEGER),
                    description="IDs of the notifications to mark as read"
                ),
                "phone_number": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Phone number of the customer"
                )
            }
        ),
        responses={
            200: openapi.Response(
                description="Notifications marked as read",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "notification_ids": openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_INTEGER)),
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "message": openapi.Schema(type=openapi.TYPE_STRING, example="3 notifications marked as read")
                    }
                )
            ),
            400: "Required fields missing or customer not found"
        }
    )
    def patch(self, request):
        notif_ids = request.data.get('notification_ids')
        phone_number = request.data.get('phone_number')
        
        if not notif_ids or not phone_number:
            return Response({"error": "notification_ids and phone_number required"}, status=400)
        
        try:
            customer = Customer.objects.get(user__username=phone_number)
            
            # Get all notifications to process
            notifications = Notification.objects.filter(id__in=notif_ids)
            
            # Separate personal and promo notifications
            personal_notifs = [n.id for n in notifications if n.notif_type == 'personal' and n.user_id == customer.id]
            promo_notifs = [n.id for n in notifications if n.notif_type == 'promo']
            
            # Update personal notifications directly
            personal_updated = 0
            if personal_notifs:
                personal_updated = Notification.objects.filter(
                    id__in=personal_notifs, 
                    user=customer
                ).update(is_read=True)
            
            # Update promotional notifications through NotificationReadStatus
            promo_updated = 0
            now = timezone.now()
            
            for notif_id in promo_notifs:
                # Try to get existing read status or create a new one
                read_status, created = NotificationReadStatus.objects.get_or_create(
                    notification_id=notif_id,
                    customer=customer,
                    defaults={'is_read': True, 'read_at': now}
                )
                
                # If it already existed but wasn't read, mark it as read
                if not created and not read_status.is_read:
                    read_status.is_read = True
                    read_status.read_at = now
                    read_status.save()
                    promo_updated += 1
                elif created:
                    promo_updated += 1
            
            total_updated = personal_updated + promo_updated
            
            return Response({
                "notification_ids": notif_ids,
                "success": True,
                "message": f"{total_updated} notifications marked as read ({personal_updated} personal, {promo_updated} promotional)"
            }, status=200)
            
        except Customer.DoesNotExist:
            return Response({"error": "Customer not found"}, status=400)

# Register FCM Token with Topic
def register_token_to_topic(token, topic="all_users"):
    try:
        from firebase_admin import messaging
        
        # Validate token before attempting to register
        if not token or len(token) < 20:
            print(f"Invalid token format for topic registration: {token[:10] if token else 'None'}")
            return False
            
        # Đăng ký token với topic
        print(f"Registering token {token[:20]}... to topic '{topic}'")
        response = messaging.subscribe_to_topic([token], topic)
        print(f"Topic registration result: {response.success_count} success, {response.failure_count} failure")
        
        # Check for specific registration errors
        if response.failure_count > 0:
            print(f"Failed to register token to topic. Errors: {response.errors}")
            
        return response.success_count > 0
    except Exception as e:
        print(f"Error subscribing to topic: {e}")
        return False

# Gửi thông báo đến topic
def send_topic_notification(topic, title, body):
    try:
        from firebase_admin import messaging
        
        # Đảm bảo thông báo hiển thị khi app đang chạy
        android_config = messaging.AndroidConfig(
            priority='high',
            notification=messaging.AndroidNotification(
                title=title,
                body=body,
                icon='notification_icon',
                color='#f45342',
                sound='default',
                channel_id='high_importance_channel',  # Thêm channel_id để hiển thị thông báo nổi
                default_sound=True,
                default_vibrate_timings=True,
                visibility='public'  # Hiển thị nội dung trên màn hình khóa
            ),
            direct_boot_ok=True,
        )
        
        # Cấu hình cho iOS
        apns_config = messaging.APNSConfig(
            headers={
                'apns-priority': '10',  # Priority cao
            },
            payload=messaging.APNSPayload(
                aps=messaging.Aps(
                    alert=messaging.ApsAlert(
                        title=title,
                        body=body,
                    ),
                    sound='default',
                    badge=1,
                    content_available=True  # Cho phép xử lý khi app đang chạy
                ),
            ),
        )
        
        # Dữ liệu để Flutter xử lý thông báo - cần có cả data cho notification
        data = {
            'click_action': 'FLUTTER_NOTIFICATION_CLICK',
            'id': '1',
            'status': 'done',
            'title': title,  # Include title in data payload
            'body': body,    # Include body in data payload
            'foreground': 'true',  # Đánh dấu hiển thị khi app đang mở
            'priority': 'high',
            'importance': 'high'
        }
        
        # Create topic message
        print(f"Sending notification to topic '{topic}'")
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            android=android_config,
            apns=apns_config,
            data=data,
            topic=topic,
        )
        
        # Send the message
        response = messaging.send(message)
        print(f"Topic notification sent successfully: {response}")
        return {"success": True, "message_id": response}
    except Exception as e:
        print(f"Error sending topic notification: {e}")
        if "SenderId mismatch" in str(e):
            return {"error": "SenderId mismatch", "details": str(e)}
        return {"error": str(e)}

class TestFCMNotificationView(APIView):
    """API to test FCM notification delivery."""
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Test FCM notification delivery to a specific customer",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["phone_number"],
            properties={
                "phone_number": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Phone number of the customer to test",
                    example="0123456789"
                ),
                "test_type": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Type of test to run: 'admin' for Firebase Admin SDK, 'legacy' for Legacy FCM, or 'both' for both",
                    enum=["admin", "legacy", "both"],
                    default="both"
                ),
                "notif_type": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Type of notification to test: 'personal' or 'promo'",
                    enum=["personal", "promo"],
                    default="personal"
                )
            }
        ),
        responses={
            200: "Test notification sent",
            404: "Customer not found",
            400: "Missing phone number or customer has no FCM token"
        }
    )
    def post(self, request):
        phone = request.data.get('phone_number')
        test_type = request.data.get('test_type', 'both')
        notif_type = request.data.get('notif_type', 'personal')  # Default to personal
        
        if not phone:
            return Response({"error": "Phone number is required"}, status=400)
            
        try:
            customer = Customer.objects.get(user__username=phone)
            
            if not customer.fcm_token:
                return Response({"error": "Customer has no FCM token registered"}, status=400)
            
            # Create a test notification in the database
            title = f"Test {notif_type.capitalize()} Notification"
            body = f"This is a test {notif_type} notification sent at {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
            Notification.objects.create(
                user=customer,
                notif_type=notif_type,
                title=title,
                message=body,
                is_read=False
            )
            
            # Check notification preferences
            preferences, created = CustomerPreferences.objects.get_or_create(
                customer=customer,
                defaults={
                    'notification_enabled': True,
                    'promo_notification_enabled': True,
                    'personal_notification_enabled': True
                }
            )
            
            results = {}
            
            # Check if appropriate notification type is enabled
            notification_enabled = False
            if notif_type == 'personal':
                notification_enabled = preferences.personal_notification_enabled
            else:  # promo
                notification_enabled = preferences.promo_notification_enabled
                
            if notification_enabled:
                # Test Admin SDK if requested
                if test_type in ['admin', 'both']:
                    try:
                        admin_result = send_fcm_v1(customer.fcm_token, title, f"{body} (via Admin SDK)")
                        results['admin_sdk'] = admin_result
                    except Exception as e:
                        results['admin_sdk'] = {"error": str(e)}
                
                # Test Legacy FCM if requested
                if test_type in ['legacy', 'both']:
                    try:
                        legacy_result = send_fcm_legacy(customer.fcm_token, title, f"{body} (via Legacy FCM)")
                        results['legacy'] = legacy_result
                    except Exception as e:
                        results['legacy'] = {"error": str(e)}
                        
                status_message = f"Test {notif_type} notification(s) sent"
            else:
                status_message = f"Notification created in DB but FCM not sent ({notif_type} notifications disabled)"
                results = {"status": "skipped", "reason": f"{notif_type} notifications disabled"}
            
            return Response({
                "message": status_message,
                "notification_type": notif_type,
                "customer": customer.fullname,
                "fcm_token": f"{customer.fcm_token[:15]}...",
                "personal_notification_enabled": preferences.personal_notification_enabled,
                "promo_notification_enabled": preferences.promo_notification_enabled,
                "results": results
            })
            
        except Customer.DoesNotExist:
            return Response({"error": "Customer not found"}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=400)

class UploadImageView(APIView):
    def post(self, request):
        if 'image' not in request.FILES:
            return Response({'error': 'No image provided'}, status=status.HTTP_400_BAD_REQUEST)
            
        image_file = request.FILES['image']
        product_name = request.POST.get('product_name', '')
        
        try:
            # Upload image to Cloudinary
            image_url = upload_image(image_file.read(), product_name)
            
            if image_url:
                return Response({'url': image_url})
            else:
                return Response({'error': 'Failed to upload image'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CheckNewProductView(APIView):
    def get(self, request):
        try:
            # Get the last 5 products added
            new_products = Product.objects.all().order_by('-product_id')[:5]
            
            serializer = ProductSerializer(new_products, many=True)
            return Response({
                'count': len(new_products),
                'products': serializer.data
            })
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CheckProductEditsView(APIView):
    """API to check recent product edits."""
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description="Get recent product edits",
        manual_parameters=[
            openapi.Parameter(
                'limit',
                openapi.IN_QUERY,
                description="Number of recent edits to retrieve (default: 10)",
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                'product_id',
                openapi.IN_QUERY,
                description="Filter edits by product ID",
                type=openapi.TYPE_INTEGER,
                required=False
            ),
        ],
        responses={
            200: openapi.Response(
                description="Product edits retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'count': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'edits': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'product_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'product_name': openapi.Schema(type=openapi.TYPE_STRING),
                                    'field_changed': openapi.Schema(type=openapi.TYPE_STRING),
                                    'old_value': openapi.Schema(type=openapi.TYPE_STRING),
                                    'new_value': openapi.Schema(type=openapi.TYPE_STRING),
                                    'edited_by': openapi.Schema(type=openapi.TYPE_STRING),
                                    'timestamp': openapi.Schema(type=openapi.TYPE_STRING)
                                }
                            )
                        )
                    }
                )
            ),
            500: "Internal server error"
        }
    )
    def get(self, request):
        try:
            from .models import ProductEditLog
            
            limit = int(request.query_params.get('limit', 10))
            product_id = request.query_params.get('product_id')
            
            # Base queryset
            queryset = ProductEditLog.objects.all()
            
            # Filter by product_id if provided
            if product_id:
                queryset = queryset.filter(product_id=product_id)
            
            # Get recent edits ordered by timestamp
            recent_edits = queryset.order_by('-timestamp')[:limit]
            
            # Format response
            edits_data = []
            for edit in recent_edits:
                edits_data.append({
                    'product_id': edit.product_id,
                    'product_name': edit.product_name,
                    'field_changed': edit.field_changed,
                    'old_value': edit.old_value,
                    'new_value': edit.new_value,
                    'edited_by': edit.edited_by,
                    'timestamp': edit.timestamp.strftime('%Y-%m-%d %H:%M:%S')
                })
            
            return Response({
                'count': len(edits_data),
                'edits': edits_data
            })
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    @swagger_auto_schema(
        operation_description="Check for changes in product data",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['product_id'],
            properties={
                'product_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'name': openapi.Schema(type=openapi.TYPE_STRING),
                'category': openapi.Schema(type=openapi.TYPE_STRING),
                'price': openapi.Schema(type=openapi.TYPE_NUMBER),
                'quantity': openapi.Schema(type=openapi.TYPE_INTEGER),
                'description': openapi.Schema(type=openapi.TYPE_STRING),
                'image_url': openapi.Schema(type=openapi.TYPE_STRING)
            }
        ),
        responses={
            200: openapi.Response(
                description="Changes checked successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'changes': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'field': openapi.Schema(type=openapi.TYPE_STRING),
                                    'old_value': openapi.Schema(type=openapi.TYPE_STRING),
                                    'new_value': openapi.Schema(type=openapi.TYPE_STRING)
                                }
                            )
                        )
                    }
                )
            ),
            404: "Product not found",
            500: "Internal server error"
        }
    )
    def post(self, request):
        try:
            product_id = request.data.get('product_id')
            if not product_id:
                return Response(
                    {'error': 'Product ID is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # Get the product
            product = Product.objects.get(product_id=product_id)
            
            # Compare each field
            changes = []
            fields_to_check = ['name', 'category', 'price', 'quantity', 'description', 'image_url']
            
            for field in fields_to_check:
                new_value = request.data.get(field)
                if new_value is not None:
                    old_value = getattr(product, field)
                    # Convert both values to strings for comparison
                    old_str = str(old_value).strip() if old_value is not None else ''
                    new_str = str(new_value).strip()
                    
                    if old_str != new_str:
                        changes.append({
                            'field': field,
                            'old_value': old_str,
                            'new_value': new_str
                        })
            
            return Response({'changes': changes})
            
        except Product.DoesNotExist:
            return Response(
                {'error': 'Product not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class CheckProductDeletionsView(APIView):
    """API to check recent product deletions."""
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description="Get recent product deletions",
        manual_parameters=[
            openapi.Parameter(
                'limit',
                openapi.IN_QUERY,
                description="Number of recent deletions to retrieve (default: 10)",
                type=openapi.TYPE_INTEGER,
                required=False
            ),
        ],
        responses={
            200: openapi.Response(
                description="Product deletions retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'count': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'deletions': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'product_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'product_name': openapi.Schema(type=openapi.TYPE_STRING),
                                    'product_data': openapi.Schema(type=openapi.TYPE_OBJECT),
                                    'deleted_by': openapi.Schema(type=openapi.TYPE_STRING),
                                    'timestamp': openapi.Schema(type=openapi.TYPE_STRING)
                                }
                            )
                        )
                    }
                )
            ),
            500: "Internal server error"
        }
    )
    def get(self, request):
        try:
            from .models import ProductDeletionLog
            
            limit = int(request.query_params.get('limit', 10))
            
            # Get recent deletions
            recent_deletions = ProductDeletionLog.objects.all().order_by('-timestamp')[:limit]
            
            # Format response
            deletions_data = []
            for deletion in recent_deletions:
                deletions_data.append({
                    'id': deletion.id,
                    'product_id': deletion.product_id,
                    'product_name': deletion.product_name,
                    'product_data': deletion.product_data,
                    'deleted_by': deletion.deleted_by,
                    'timestamp': deletion.timestamp.strftime('%Y-%m-%d %H:%M:%S')
                })
            
            return Response({
                'count': len(deletions_data),
                'deletions': deletions_data
            })
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AddStockView(APIView):
    """API to add stock to products."""
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description="Add stock to a product",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['product_id', 'quantity'],
            properties={
                'product_id': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID of the product"),
                'quantity': openapi.Schema(type=openapi.TYPE_INTEGER, description="Quantity to add"),
                'notes': openapi.Schema(type=openapi.TYPE_STRING, description="Optional notes about this stock addition")
            }
        ),
        responses={
            200: openapi.Response(
                description="Stock added successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'product_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'product_name': openapi.Schema(type=openapi.TYPE_STRING),
                        'new_quantity': openapi.Schema(type=openapi.TYPE_INTEGER)
                    }
                )
            ),
            400: "Invalid data",
            404: "Product not found"
        }
    )
    def post(self, request):
        product_id = request.data.get('product_id')
        quantity = request.data.get('quantity')
        notes = request.data.get('notes', '')
        
        if not product_id or not quantity:
            return Response(
                {"error": "Product ID and quantity are required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            product = Product.objects.get(product_id=product_id)
            
            # Create inventory transaction
            transaction = InventoryTransaction.objects.create(
                product=product,
                transaction_type='addition',
                quantity=quantity,
                notes=notes
            )
            
            return Response({
                "message": "Stock added successfully",
                "product_id": product.product_id,
                "product_name": product.name,
                "new_quantity": product.quantity
            }, status=status.HTTP_200_OK)
            
        except Product.DoesNotExist:
            return Response(
                {"error": "Product not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class InventoryHistoryView(APIView):
    """API to get inventory history for a product."""
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description="Get inventory history for a product",
        manual_parameters=[
            openapi.Parameter(
                'product_id',
                openapi.IN_QUERY,
                description="ID of the product",
                type=openapi.TYPE_INTEGER,
                required=True
            ),
        ],
        responses={
            200: openapi.Response(
                description="Inventory history retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'product_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'product_name': openapi.Schema(type=openapi.TYPE_STRING),
                        'current_quantity': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'transactions': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'transaction_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'transaction_type': openapi.Schema(type=openapi.TYPE_STRING),
                                    'quantity': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'timestamp': openapi.Schema(type=openapi.TYPE_STRING),
                                    'notes': openapi.Schema(type=openapi.TYPE_STRING),
                                    'reference_id': openapi.Schema(type=openapi.TYPE_STRING)
                                }
                            )
                        )
                    }
                )
            ),
            404: "Product not found"
        }
    )
    def get(self, request):
        product_id = request.query_params.get('product_id')
        
        if not product_id:
            return Response(
                {"error": "Product ID is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            product = Product.objects.get(product_id=product_id)
            
            # Get all inventory transactions for this product
            transactions = InventoryTransaction.objects.filter(
                product=product
            ).order_by('-timestamp')
            
            # Format transactions for response
            transactions_data = []
            for transaction in transactions:
                transactions_data.append({
                    'transaction_id': transaction.transaction_id,
                    'transaction_type': transaction.transaction_type,
                    'quantity': transaction.quantity,
                    'timestamp': transaction.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    'notes': transaction.notes,
                    'reference_id': transaction.reference_id
                })
            
            return Response({
                'product_id': product.product_id,
                'product_name': product.name,
                'current_quantity': product.quantity,
                'transactions': transactions_data
            }, status=status.HTTP_200_OK)
            
        except Product.DoesNotExist:
            return Response(
                {"error": "Product not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class LowStockProductsView(APIView):
    """API to get products with low stock levels."""
    permission_classes = [AllowAny]
    
    def get(self, request):
        try:
            # Get all products where quantity is below or equal to low_stock_threshold
            low_stock_products = Product.objects.filter(
                quantity__lte=F('low_stock_threshold')
            ).values(
                'product_id', 'name', 'quantity', 'low_stock_threshold', 'category'
            ).order_by('quantity')  # Order by quantity ascending (lowest first)
            
            # Add transaction timestamp for each product
            products_data = []
            for product in low_stock_products:
                # Get the latest inventory transaction for this product
                latest_transaction = InventoryTransaction.objects.filter(
                    product_id=product['product_id']
                ).order_by('-timestamp').first()
                
                # Try to get the actual product object for additional information
                product_obj = Product.objects.get(product_id=product['product_id'])
                
                # Determine the last updated timestamp
                last_updated = None
                if latest_transaction:
                    last_updated = latest_transaction.timestamp.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    # If no transactions found, use a clear message
                    last_updated = "No inventory transactions recorded"
                
                # Format the product data with additional information
                products_data.append({
                    'product_id': product['product_id'],
                    'name': product['name'],
                    'current_quantity': product['quantity'],
                    'low_stock_threshold': product['low_stock_threshold'],
                    'category': product['category'],
                    'last_updated': last_updated,
                    'status': 'critical' if product['quantity'] == 0 else 'low',
                    'restock_needed': product['low_stock_threshold'] - product['quantity']
                })
            
            return Response({
                'status': 'success',
                'count': len(products_data),
                'data': products_data,
                'timestamp': timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=500)

class WebSocketDebugView(APIView):
    """Simple view for WebSocket debugging."""
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Return WebSocket debug information."""
        from channels.layers import get_channel_layer
        
        # Get the base WebSocket URL
        scheme = 'wss' if request.is_secure() else 'ws'
        host = request.get_host()
        
        # List all WebSocket endpoints
        websocket_endpoints = [
            f"{scheme}://{host}/ws/inventory/",
            f"{scheme}://{host}/ws/device-status/",
            f"{scheme}://{host}/ws/history/"
        ]
        
        # Check if channel layer is available
        channel_layer_available = False
        channel_layer = None
        
        try:
            channel_layer = get_channel_layer()
            channel_layer_available = channel_layer is not None
        except Exception as e:
            channel_layer_error = str(e)
        
        # Return debug info
        return Response({
            'websocket_endpoints': websocket_endpoints,
            'channel_layer_available': channel_layer_available,
            'channel_layer_type': str(type(channel_layer)) if channel_layer else None,
            'asgi_application': settings.ASGI_APPLICATION,
            'server_software': request.META.get('SERVER_SOFTWARE', 'Unknown'),
            'settings_check': {
                'channels_installed': 'channels' in settings.INSTALLED_APPS,
                'asgi_app_set': hasattr(settings, 'ASGI_APPLICATION'),
                'channel_layers_set': hasattr(settings, 'CHANNEL_LAYERS')
            }
        })

class WebSocketHealthCheckView(APIView):
    """API to check WebSocket health and provide inventory data through HTTP as a fallback."""
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Return WebSocket health information and inventory data if needed."""
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        import time
        
        # WebSocket status
        websocket_status = {
            'status': 'unknown',
            'timestamp': timezone.now().isoformat()
        }
        
        # Check if channel layer is available
        channel_layer = None
        try:
            channel_layer = get_channel_layer()
            if channel_layer:
                websocket_status['status'] = 'available'
                
                # Try sending a ping through the channel layer
                try:
                    channel_name = f"healthcheck-{int(time.time())}"
                    async_to_sync(channel_layer.group_add)("inventory_updates", channel_name)
                    async_to_sync(channel_layer.group_send)(
                        "inventory_updates",
                        {
                            "type": "inventory_update",
                            "data": {
                                "type": "health_check",
                                "timestamp": timezone.now().isoformat(),
                                "message": "Health check ping"
                            }
                        }
                    )
                    websocket_status['ping_sent'] = True
                except Exception as e:
                    websocket_status['ping_error'] = str(e)
            else:
                websocket_status['status'] = 'unavailable'
                websocket_status['error'] = 'Channel layer is not available'
        except Exception as e:
            websocket_status['status'] = 'error'
            websocket_status['error'] = str(e)
        
        # Get inventory data as a fallback
        inventory_data = []
        try:
            # Get low stock products
            low_stock_products = Product.objects.filter(
                quantity__lte=F('low_stock_threshold')
            ).values(
                'product_id', 'name', 'quantity', 'low_stock_threshold', 'category'
            ).order_by('quantity')
            
            # Add transaction timestamps
            for product in low_stock_products:
                # Get the latest inventory transaction for this product
                latest_transaction = InventoryTransaction.objects.filter(
                    product_id=product['product_id']
                ).order_by('-timestamp').first()
                
                # Format the product data with additional information
                inventory_data.append({
                    'product_id': product['product_id'],
                    'name': product['name'].replace('_', ' '),
                    'current_quantity': product['quantity'],
                    'low_stock_threshold': product['low_stock_threshold'],
                    'category': product['category'],
                    'last_updated': latest_transaction.timestamp.strftime('%Y-%m-%d %H:%M:%S') if latest_transaction else None,
                    'status': 'critical' if product['quantity'] == 0 else 'low',
                    'restock_needed': product['low_stock_threshold'] - product['quantity']
                })
        except Exception as e:
            pass
            
        return Response({
            'websocket_status': websocket_status,
            'low_stock_products': inventory_data,
            'server_time': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
            'count': len(inventory_data)
        })

@login_required
def inventory_management_view(request):
    # Get all products
    products = Product.objects.all()
    
    # Calculate total stock value and identify low stock items
    total_stock_value = 0
    low_stock_count = 0
    low_stock_threshold = 5  # Default threshold
    
    for product in products:
        # Calculate stock value for each product
        product_value = product.price * product.quantity
        total_stock_value += product_value
        
        # Check if product is low on stock
        if product.quantity <= product.low_stock_threshold:
            low_stock_count += 1
    
    # Get recent inventory transactions
    recent_transactions = InventoryTransaction.objects.all().order_by('-timestamp')[:10]
    
    # Enhance product data with display names 
    for product in products:
        # Create a display name by replacing underscores with spaces
        product.display_name = product.name.replace('_', ' ')
        
        # Set last updated based on most recent transaction
        last_transaction = InventoryTransaction.objects.filter(product=product).order_by('-timestamp').first()
        if last_transaction:
            product.last_updated = last_transaction.timestamp
    
    # Calculate stock distribution percentages
    total_products = len(products)
    if total_products > 0:
        low_stock_items = sum(1 for p in products if p.quantity <= p.low_stock_threshold)
        medium_stock_items = sum(1 for p in products if p.quantity > p.low_stock_threshold and p.quantity <= p.low_stock_threshold + 10)
        high_stock_items = total_products - low_stock_items - medium_stock_items
        
        stock_distribution = {
            'low_percent': round((low_stock_items / total_products) * 100),
            'medium_percent': round((medium_stock_items / total_products) * 100),
            'high_percent': round((high_stock_items / total_products) * 100)
        }
    else:
        stock_distribution = {
            'low_percent': 0,
            'medium_percent': 0,
            'high_percent': 0
        }
    
    # Calculate the valuation of products by category
    category_valuation = {}
    for product in products:
        category = product.category
        value = product.price * product.quantity
        
        if category in category_valuation:
            category_valuation[category] += value
        else:
            category_valuation[category] = value
    
    # Prepare inventory history data
    products_inventory_history = {}
    for product in products:
        # Get inventory transactions for each product
        transactions = InventoryTransaction.objects.filter(product=product).order_by('-timestamp')
        
        # Format the transaction data
        formatted_transactions = []
        for transaction in transactions:
            formatted_transactions.append({
                'transaction_id': transaction.transaction_id,
                'transaction_type': transaction.transaction_type,
                'quantity': transaction.quantity,
                'timestamp': transaction.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'notes': transaction.notes,
                'reference_id': transaction.reference_id
            })
        
        # Store the product's inventory history
        products_inventory_history[product.product_id] = {
            'product_id': product.product_id,
            'product_name': product.name,
            'current_quantity': product.quantity,
            'transactions': formatted_transactions
        }
    
    # Convert to JSON for the template
    import json
    products_inventory_history_json = json.dumps(products_inventory_history)
    
    # Prepare context for the template
    context = {
        'products': products,
        'total_stock_value': total_stock_value,
        'low_stock_count': low_stock_count,
        'recent_transactions': recent_transactions,
        'category_valuation': category_valuation,
        'stock_distribution': stock_distribution,
        'products_inventory_history': products_inventory_history_json
    }
    
    return render(request, 'inventory_management.html', context)

@login_required
def export_inventory_pdf(request):
    """Generate and serve a PDF of inventory data."""
    from django.http import HttpResponse
    from xhtml2pdf import pisa
    from django.template.loader import get_template
    from io import BytesIO
    from datetime import datetime
    import os
    from django.conf import settings
    
    # Get filter parameters from the request
    search_query = request.POST.get('search', '')
    category_filter = request.POST.get('category', '')
    stock_level_filter = request.POST.get('stock_level', '')
    
    # Get all products
    products = Product.objects.all()
    
    # Apply filters if provided
    if search_query:
        products = products.filter(name__icontains=search_query)
    
    if category_filter:
        products = products.filter(category=category_filter)
    
    if stock_level_filter:
        if stock_level_filter == 'low':
            products = [p for p in products if p.quantity <= p.low_stock_threshold]
        elif stock_level_filter == 'medium':
            products = [p for p in products if p.quantity > p.low_stock_threshold and p.quantity <= p.low_stock_threshold + 10]
        elif stock_level_filter == 'high':
            products = [p for p in products if p.quantity > p.low_stock_threshold + 10]
    
    # Calculate statistics for the report
    total_products = len(products)
    total_stock_value = 0
    low_stock_count = 0
    
    for product in products:
        # Calculate stock value
        product_value = product.price * product.quantity
        total_stock_value += product_value
        product.stock_value = product_value
        
        # Enhance product with display name
        product.display_name = product.name.replace('_', ' ').title()
        
        # Get last updated date
        last_transaction = InventoryTransaction.objects.filter(product=product).order_by('-timestamp').first()
        if last_transaction:
            product.last_updated = last_transaction.timestamp
        
        # Check if product is low on stock
        if product.quantity <= product.low_stock_threshold:
            low_stock_count += 1
            product.stock_level = 'low'
        elif product.quantity <= product.low_stock_threshold + 10:
            product.stock_level = 'medium'
        else:
            product.stock_level = 'high'
    
    # Calculate stock distribution
    if total_products > 0:
        low_stock_percent = round((len([p for p in products if getattr(p, 'stock_level', '') == 'low']) / total_products) * 100)
        medium_stock_percent = round((len([p for p in products if getattr(p, 'stock_level', '') == 'medium']) / total_products) * 100)
        high_stock_percent = round((len([p for p in products if getattr(p, 'stock_level', '') == 'high']) / total_products) * 100)
    else:
        low_stock_percent = medium_stock_percent = high_stock_percent = 0
    
    # Prepare context for the template
    context = {
        'products': products,
        'total_products': total_products,
        'total_stock_value': total_stock_value,
        'low_stock_count': low_stock_count,
        'low_stock_percent': low_stock_percent, 
        'medium_stock_percent': medium_stock_percent,
        'high_stock_percent': high_stock_percent,
        'generated_date': datetime.now().strftime('%d/%m/%Y %H:%M'),
        'title': 'Inventory Management Report',
    }
    
    # Define a helper function to link static files
    def link_callback(uri, rel):
        """
        Convert HTML URIs to absolute system paths so xhtml2pdf can access those resources
        """
        # Use short variable names
        sUrl = settings.STATIC_URL      # Typically /static/
        sRoot = settings.STATIC_ROOT    # Typically /home/userX/project_static/
        mUrl = settings.MEDIA_URL       # Typically /media/
        mRoot = settings.MEDIA_ROOT     # Typically /home/userX/project_static/media/

        # Convert URIs to absolute system paths
        if uri.startswith(mUrl):
            path = os.path.join(mRoot, uri.replace(mUrl, ""))
        elif uri.startswith(sUrl):
            path = os.path.join(sRoot, uri.replace(sUrl, ""))
        else:
            return uri  # Handle absolute URLs (i.e. http://domain/img.png)

        # Return the path if it exists
        if not os.path.isfile(path):
            raise Exception('Media URI could not be resolved to a file: ' + path)
        return path
    
    # Render template to string
    template = get_template('inventory_pdf.html')
    html = template.render(context)
    
    # Create a file-like buffer to receive PDF data
    buffer = BytesIO()
    
    # Generate PDF with enhanced options
    pdf_options = {
        'encoding': 'UTF-8',
        'link_callback': link_callback,
    }
    
    pisa_status = pisa.CreatePDF(
        src=html, 
        dest=buffer,
        **pdf_options
    )
    
    # If error creating PDF
    if pisa_status.err:
        return HttpResponse('Error generating PDF: ' + str(pisa_status.err), content_type='text/plain')
    
    # File response with PDF
    buffer.seek(0)
    
    # Create the response with appropriate filename
    filename = f"inventory_report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response

def index_view(request):
    """
    View for the index/home page of the application.
    If user is already logged in, redirect to dashboard.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'index.html')

def signup_view(request):
    """
    View for admin/superuser signup page.
    """
    if request.method == 'POST':
        # Get form data
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_again = request.POST.get('password_again')
        
        # Validate password match
        if password != password_again:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'signup.html')
            
        # Check if username is already registered
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username is already taken.')
            return render(request, 'signup.html')
        
        # Check if email is already registered
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email is already registered.')
            return render(request, 'signup.html')
        
        try:
            # Create superuser
            superuser_info = create_superuser(username=username, email=email, password=password)
            
            messages.success(request, 'Admin account created successfully. Please sign in.')
            return redirect('login')
                
        except Exception as e:
            messages.error(request, f'Error creating account: {str(e)}')
    
    return render(request, 'signup.html')

def check_static_file(request, filename):
    """View to test static file serving and log access details"""
    import os
    from django.conf import settings
    
    # Check if file exists in static folder
    static_file_path = os.path.join(settings.STATIC_ROOT, 'img', filename)
    static_src_path = os.path.join(settings.BASE_DIR, 'cartv2', 'static', 'img', filename)
    
    file_exists_static = os.path.exists(static_file_path)
    file_exists_src = os.path.exists(static_src_path)
    
    if file_exists_static:
        file_size_static = os.path.getsize(static_file_path)
    else:
        file_size_static = 0
        
    if file_exists_src:
        file_size_src = os.path.getsize(static_src_path)
    else:
        file_size_src = 0
    
    # Log information
    print(f"Static file check for {filename}:")
    print(f"STATIC_ROOT path: {static_file_path}")
    print(f"Source path: {static_src_path}")
    print(f"Exists in STATIC_ROOT: {file_exists_static} (Size: {file_size_static} bytes)")
    print(f"Exists in source: {file_exists_src} (Size: {file_size_src} bytes)")
    
    # Return info as HTML
    html = f"""
    <html>
    <head><title>Static File Check: {filename}</title></head>
    <body>
        <h1>Static File Check for {filename}</h1>
        <ul>
            <li>STATIC_ROOT path: {static_file_path}</li>
            <li>Source path: {static_src_path}</li>
            <li>Exists in STATIC_ROOT: {file_exists_static} (Size: {file_size_static} bytes)</li>
            <li>Exists in source: {file_exists_src} (Size: {file_size_src} bytes)</li>
        </ul>
        <p>Check the image display:</p>
        <img src="/static/img/{filename}" alt="Test image" style="border: 1px solid red;">
        <p>URL used: /static/img/{filename}</p>
    </body>
    </html>
    """
    
    return HttpResponse(html)








