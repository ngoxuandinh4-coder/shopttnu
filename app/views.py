from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from .models import *
import json
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .forms import CreateUserForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.core.cache import cache
from django.db import transaction
from django.db.models import Sum, Q
from django.utils import timezone
from .models import Voucher



@login_required(login_url='login')
def add_review(request, product_id):
    if request.method != 'POST':
        return redirect('detail', id=product_id)

    product = Product.objects.get(id=product_id)

    # Chỉ khách đã mua và đơn đã giao mới được đánh giá
    has_bought = OrderItem.objects.filter(
        product=product,
        order__customer=request.user,
        order__complete=True,
        order__status='Đã giao'
    ).exists()

    if not has_bought:
        messages.error(request, 'Bạn chỉ có thể đánh giá sản phẩm sau khi đã mua và đơn hàng đã giao thành công!')
        return redirect('detail', id=product_id)

    if Review.objects.filter(product=product, customer=request.user).exists():
        messages.warning(request, 'Bạn đã đánh giá sản phẩm này rồi!')
        return redirect('detail', id=product_id)

    content = (request.POST.get('content') or '').strip()
    try:
        rating = int(request.POST.get('rating', 5))
    except (TypeError, ValueError):
        rating = 5
    rating = max(1, min(rating, 5))

    if not content:
        messages.error(request, 'Vui lòng nhập nội dung đánh giá!')
        return redirect('detail', id=product_id)

    Review.objects.create(
        product=product,
        customer=request.user,
        content=content,
        rating=rating
    )
    messages.success(request, 'Cảm ơn bạn đã đánh giá sản phẩm!')
    return redirect('detail', id=product_id)

@login_required(login_url='login')
def returnOrder(request, id):
    if request.method == 'POST':
        try:
            order = Order.objects.get(id=id, customer=request.user, complete=True)
            reason = (request.POST.get('reason') or '').strip()

            # Chỉ cho phép trả hàng khi đơn đã ở trạng thái "Đã giao"
            if order.status == 'Đã giao':
                order.status = 'Yêu cầu trả hàng'
                order.return_reason = reason
                order.save(update_fields=['status', 'return_reason'])
                messages.success(request, f'Đã gửi yêu cầu trả hàng cho đơn #{order.id}. Shop sẽ liên hệ bạn sớm!')
            else:
                messages.error(request, 'Đơn hàng chưa giao hoặc đã xử lý, không thể yêu cầu trả hàng!')

        except Order.DoesNotExist:
            messages.error(request, 'Đơn hàng không tồn tại!')

    return redirect('cart')

@login_required(login_url='login')
def cancelOrder(request, id):
    try:
        order = Order.objects.get(id=id, customer=request.user, complete=True)

        # Chỉ cho phép hủy nếu đơn chưa giao đi xa
        if order.status in ['Chờ xác nhận', 'Đã xác nhận']:
            order.status = 'Đã hủy'
            order.save(update_fields=['status'])
            order.restore_stock()
            messages.success(request, f'✅ Đã hủy thành công đơn hàng #{order.id} và hoàn lại tồn kho!')
        else:
            messages.error(request, 'Không thể hủy đơn hàng này do đang giao hoặc đã hoàn thành!')

    except Order.DoesNotExist:
        messages.error(request, 'Đơn hàng không tồn tại!')

    return redirect('cart')

@login_required(login_url='login')
def profile(request):
    customer = request.user
    customer_profile, created = CustomerProfile.objects.get_or_create(user=customer)
    
    if request.method == 'POST':
        new_username = request.POST.get('username')
        new_email = request.POST.get('email')
        new_phone = request.POST.get('phone')
        new_address = request.POST.get('address')
        new_password = request.POST.get('password')
        
        try:
            customer.username = new_username
            customer.email = new_email
            if new_password:
                customer.set_password(new_password)
                customer.save()
                update_session_auth_hash(request, customer) 
            else:
                customer.save()

            customer_profile.phone = new_phone
            customer_profile.address = new_address
            customer_profile.save()
            messages.success(request, 'Cập nhật thông tin cá nhân thành công!')
        except Exception as e:
            messages.error(request, 'Có lỗi xảy ra hoặc tên đăng nhập đã tồn tại!')
        return redirect('profile')

    order_cart, created = Order.objects.get_or_create(customer=customer, complete=False)
    context = {
        'cartItems': order_cart.get_cart_items, 
        'customer_profile': customer_profile,
        'categories': Category.objects.all(),
    }
    return render(request, 'app/profile.html', context)
def detail(request, id):
    product = Product.objects.get(id=id)

    if request.user.is_authenticated:
        customer = request.user
        order, created = Order.objects.get_or_create(customer=customer, complete=False)
        cartItems = order.get_cart_items
        has_bought = OrderItem.objects.filter(
            product=product,
            order__customer=customer,
            order__complete=True,
            order__status='Đã giao'
        ).exists()
        has_reviewed = Review.objects.filter(product=product, customer=customer).exists()
        can_review = has_bought and not has_reviewed
    else:
        order = {'get_cart_total': 0, 'get_cart_items': 0}
        cartItems = order['get_cart_items']
        has_bought = False
        has_reviewed = False
        can_review = False

    categories = Category.objects.all()

    context = {
        'product': product,
        'cartItems': cartItems,
        'categories': categories,
        'can_review': can_review,
        'has_bought': has_bought,
        'has_reviewed': has_reviewed,
    }
    return render(request, 'app/detail.html', context)
def category(request):
    if request.user.is_authenticated:
        order, created = Order.objects.get_or_create(customer=request.user, complete=False)
        cartItems = order.get_cart_items
    else:
        cartItems = 0

    categories = Category.objects.filter(is_sub=False)
    active_category = request.GET.get('category', '')
    products = Product.objects.all()

    if active_category:
        products = Product.objects.filter(category__slug=active_category)

    context = {
        'categories': categories,
        'products': products,
        'active_category': active_category,
        'cartItems': cartItems,
    }
    return render(request, 'app/category.html', context)
def search(request):
    # --- PHẦN 1: TÍNH SỐ LƯỢNG GIỎ HÀNG (Giống hệt hàm home) ---
    if request.user.is_authenticated:
        customer = request.user 
        order, created = Order.objects.get_or_create(customer=customer, complete=False)
        cartItems = order.get_cart_items
    else:
        order = {'get_cart_total': 0, 'get_cart_items': 0}
        cartItems = order['get_cart_items']

    # --- PHẦN 2: TÌM KIẾM SẢN PHẨM ---
    query = request.GET.get('searched', '')
    if query:
        all_products = Product.objects.all()
        products = [product for product in all_products if query.lower() in product.name.lower()]
    else:
        products = []

    # --- PHẦN 3: GỬI CẢ SẢN PHẨM LẪN SỐ GIỎ HÀNG SANG HTML ---
    # THÊM 'cartItems': cartItems vào đây để giao diện nhận được số
    context = {'query': query, 'products': products, 'cartItems': cartItems, 'categories': Category.objects.all()}
    return render(request, 'app/search.html', context)
def register(request):
    form = CreateUserForm()
    if request.method == "POST":
        form = CreateUserForm(request.POST)
        if form.is_valid():
            user = form.save()
            # KHÔNG CẦN TẠO CUSTOMER NỮA
            return redirect('login')
    return render(request, 'app/register.html', {'form': form})

def loginPage(request):
    if request.user.is_authenticated:
        return redirect('home')
        
    if request.method == "POST":
        username = request.POST.get('username')    
        password = request.POST.get('password')   
        
        # Tạo chìa khóa lưu số lần sai và cờ khóa theo tên đăng nhập
        cache_key = f'login_attempts_{username}' 
        lock_key = f'login_locked_{username}'    

        # 1. KIỂM TRA BỊ KHÓA
        if cache.get(lock_key):
            messages.error(request, 'Tài khoản đang bị khóa 5 phút do nhập sai quá nhiều lần. Vui lòng thử lại sau!')
            return render(request, 'app/login.html', {})

        # 2. KIỂM TRA ĐĂNG NHẬP
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # Đăng nhập thành công -> Xóa lịch sử nhập sai
            cache.delete(cache_key)
            login(request, user)
            return redirect('home')
        else:
            # Đăng nhập thất bại -> Tăng số lần sai lên 1
            attempts = cache.get(cache_key, 0) + 1
            cache.set(cache_key, attempts, timeout=300) # Nhớ trong 5 phút (300s)

            if attempts >= 5:
                # Nếu sai 5 lần -> Khóa 5 phút
                cache.set(lock_key, True, timeout=300)
                messages.error(request, 'Bạn đã nhập sai 5 lần! Tài khoản bị khóa tạm thời 5 phút.')
            else:
                messages.warning(request, f'Sai mật khẩu! Bạn còn {5 - attempts} lần thử.')
                
    return render(request, 'app/login.html', {})

def logoutPage(request):
    logout(request)
    return redirect('login')

def home(request):
    if request.user.is_authenticated:
        
        customer = request.user 
        order, created = Order.objects.get_or_create(customer=customer, complete=False)
        cartItems = order.get_cart_items
    else:
        items = []
        order = {'get_cart_total': 0, 'get_cart_items': 0}
        cartItems = order['get_cart_items']
    categories = Category.objects.all()
    
    
    category_id = request.GET.get('category')
    if category_id:
       
        products = Product.objects.filter(category=category_id)
    else:
       
        products = Product.objects.all()

    
    context = {'products': products, 'cartItems': cartItems, 'categories': categories}
    return render(request, 'app/home.html', context)

def cart(request):
    if request.user.is_authenticated:
        customer = request.user
        order, created = Order.objects.get_or_create(customer=customer, complete=False)
        items = order.orderitem_set.all()
        cartItems = order.get_cart_items
        orders_history = Order.objects.filter(customer=customer, complete=True).order_by('-date_order')

        context = {'items': items, 'order': order, 'cartItems': cartItems,'orders_history': orders_history, # PHẢI CÓ DÒNG NÀY
        'categories': Category.objects.all(),}
        return render(request, 'app/cart.html', context)
    else:
        # NẾU CHƯA ĐĂNG NHẬP -> ĐÁ VĂNG VỀ TRANG LOGIN
        messages.warning(request, 'Bạn cần đăng nhập để xem giỏ hàng!')
        return redirect('login')


@login_required(login_url='login')
def checkout(request):
    customer = request.user
    current_order, created = Order.objects.get_or_create(customer=customer, complete=False)

    selected_ids = request.GET.getlist('id')
    selected_sizes = request.GET.getlist('size')
    voucher_code = request.GET.get('voucher', '').strip()

    items = []
    total_selected = 0
    count_selected = 0

    if selected_ids:
        all_items = current_order.orderitem_set.select_related('product').all()
        for i in range(len(selected_ids)):
            s_size = selected_sizes[i] if i < len(selected_sizes) and selected_sizes[i] != '' else None
            item = all_items.filter(product_id=selected_ids[i], size=s_size).first()
            if item:
                items.append(item)
                total_selected += item.get_total
                count_selected += item.quantity
    else:
        return redirect('cart')

    if not items:
        messages.error(request, 'Không tìm thấy sản phẩm hợp lệ để thanh toán!')
        return redirect('cart')

    voucher = None
    voucher_discount = 0
    final_total = total_selected

    if voucher_code:
        try:
            voucher = Voucher.objects.get(code__iexact=voucher_code, active=True)
            voucher_discount = voucher.get_discount(total_selected)
            final_total = max(0, total_selected - voucher_discount)
        except Voucher.DoesNotExist:
            voucher = None
            voucher_discount = 0
            final_total = total_selected

    # Mã này sẽ được lưu thật vào Order.transaction_id để QR không còn dùng nhầm ID giỏ tạm
    checkout_transaction_id = request.session.get('checkout_transaction_id')
    if not checkout_transaction_id:
        checkout_transaction_id = f"DH{customer.id}{timezone.now().strftime('%Y%m%d%H%M%S')}"
        request.session['checkout_transaction_id'] = checkout_transaction_id

    if request.method == 'POST':
        phone = request.POST.get('phone')
        address = request.POST.get('address')
        payment_method = request.POST.get('payment_method', 'COD')

        # Kiểm tra tồn kho lần cuối trước khi chốt đơn
        for item in items:
            product = item.product
            if product and product.stock is not None and item.quantity > product.stock:
                messages.error(request, f'Sản phẩm "{product.name}" chỉ còn {product.stock} chiếc, không đủ để đặt {item.quantity} chiếc!')
                return redirect('cart')

        with transaction.atomic():
            new_order = Order.objects.create(
                customer=customer,
                complete=True,
                transaction_id=checkout_transaction_id,
                payment_method=payment_method,
                voucher=voucher,
                voucher_discount=voucher_discount,
                final_total=final_total,
                status='Đã xác nhận' if payment_method == 'COD' else 'Chờ xác nhận'
            )

            for item in items:
                item.order = new_order
                item.save(update_fields=['order'])

            # Trừ kho thật sau khi chuyển item sang đơn mới
            new_order.reduce_stock()

            ShippingAddress.objects.create(
                customer=customer,
                order=new_order,
                address=address,
                mobile=phone,
                city='Thái Nguyên'
            )

        request.session.pop('checkout_transaction_id', None)

        if payment_method == 'Banking':
            messages.success(request, f'🎉 Đơn #{new_order.id} đang chờ xác nhận chuyển khoản! Nội dung chuyển khoản: {new_order.transaction_id}')
        else:
            messages.success(request, f'🎉 Đơn #{new_order.id} đã được đặt thành công! Cảm ơn bạn đã mua sắm.')

        return redirect('home')

    context = {
        'items': items,
        'order': current_order,
        'cartItems': current_order.get_cart_items,
        'total_selected': total_selected,
        'voucher': voucher,
        'voucher_discount': voucher_discount,
        'final_total': final_total,
        'count_selected': count_selected,
        'checkout_transaction_id': checkout_transaction_id,
    }
    return render(request, 'app/checkout.html', context)

@login_required(login_url='login')
def updateItem(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Phương thức không hợp lệ'}, status=405)

    try:
        data = json.loads(request.body)
        productId = data.get('productId')
        action = data.get('action')
        size = data.get('size')
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Dữ liệu gửi lên không hợp lệ'}, status=400)

    if size == '' or size == 'None':
        size = None

    if action not in ['add', 'remove', 'delete']:
        return JsonResponse({'status': 'error', 'message': 'Hành động không hợp lệ'}, status=400)

    try:
        product = Product.objects.get(id=productId)
    except Product.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Sản phẩm không tồn tại'}, status=404)

    order, created = Order.objects.get_or_create(customer=request.user, complete=False)
    orderItem, created = OrderItem.objects.get_or_create(order=order, product=product, size=size)

    if action == 'add':
        if product.stock is not None and orderItem.quantity >= product.stock:
            return JsonResponse({
                'status': 'error',
                'message': f'Rất tiếc, sản phẩm này chỉ còn {product.stock} chiếc trong kho!'
            })
        orderItem.quantity += 1
    elif action == 'remove':
        orderItem.quantity -= 1
    elif action == 'delete':
        orderItem.quantity = 0

    if orderItem.quantity <= 0:
        orderItem.delete()
    else:
        orderItem.save()

    return JsonResponse({'status': 'success', 'message': 'Cập nhật thành công'})
from django.db.models import Count

@login_required(login_url='login')
def dashboard(request):
    # Chỉ cho phép Admin (nhân viên/chủ shop) xem trang này
    if not request.user.is_staff:
        messages.error(request, 'Bạn không có quyền truy cập trang Thống kê!')
        return redirect('home')

    # 1. Tính toán các con số tổng quan
    completed_orders = Order.objects.filter(complete=True)
    total_orders = completed_orders.count()
    total_customers = User.objects.count()
    
    # Tính tổng doanh thu từ các đơn hàng
    total_revenue = 0
    for order in completed_orders:
        if order.status == 'Đã giao' or order.status == 'Đã xác nhận':
            total_revenue += order.get_cart_total_after_discount

    # 2. Lấy dữ liệu cho biểu đồ (Thống kê trạng thái đơn hàng)
    status_counts = Order.objects.values('status').annotate(count=Count('id'))
    
    # Chuẩn bị mảng dữ liệu để gửi sang JavaScript (Chart.js)
    labels = []
    data = []
    for item in status_counts:
        status_name = item['status'] if item['status'] else 'Giỏ hàng đang chọn'
        labels.append(status_name)
        data.append(item['count'])

    context = {
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'total_customers': total_customers,
        'labels': json.dumps(labels),  # Chuyển list Python sang chuỗi JSON cho JS
        'data': json.dumps(data),
    }
    return render(request, 'app/dashboard.html', context)


@login_required(login_url='login')
def manage_inventory(request):
    # Chặn không cho khách hàng vào trang này
    if not request.user.is_staff:
        messages.error(request, 'Bạn không có quyền truy cập trang Quản lý Kho!')
        return redirect('home')

    # XỬ LÝ KHI BẤM NÚT NHẬP KHO HOẶC CẬP NHẬT TỒN KHO
    if request.method == 'POST':
        action = request.POST.get('action', 'import')
        product_id = request.POST.get('product_id')

        try:
            product = Product.objects.get(id=product_id)
        except (Product.DoesNotExist, TypeError, ValueError):
            messages.error(request, 'Sản phẩm không tồn tại!')
            return redirect('manage_inventory')

        if action == 'import':
            try:
                quantity_added = int(request.POST.get('quantity', 0))
            except (TypeError, ValueError):
                quantity_added = 0

            note = request.POST.get('note', '').strip()

            if quantity_added <= 0:
                messages.error(request, 'Số lượng nhập phải lớn hơn 0!')
                return redirect('manage_inventory')

            # 1. Tạo 1 dòng lịch sử nhập kho
            StockReceipt.objects.create(product=product, quantity=quantity_added, note=note)

            # 2. Cộng dồn số lượng vào tồn kho hiện tại của sản phẩm
            product.stock = (product.stock or 0) + quantity_added
            product.save(update_fields=['stock'])

            messages.success(request, f'✅ Đã nhập thêm {quantity_added} "{product.name}" vào kho thành công!')
            return redirect('manage_inventory')

        if action == 'update_stock':
            try:
                new_stock = int(request.POST.get('stock', 0))
            except (TypeError, ValueError):
                messages.error(request, 'Số tồn kho không hợp lệ!')
                return redirect('manage_inventory')

            if new_stock < 0:
                messages.error(request, 'Tồn kho không được nhỏ hơn 0!')
                return redirect('manage_inventory')

            old_stock = product.stock or 0
            product.stock = new_stock
            product.save(update_fields=['stock'])

            messages.success(request, f'✅ Đã cập nhật tồn kho "{product.name}" từ {old_stock} thành {new_stock}!')
            return redirect('manage_inventory')

        messages.error(request, 'Thao tác không hợp lệ!')
        return redirect('manage_inventory')

    keyword = request.GET.get('q', '').strip()
    products = Product.objects.all().order_by('name')
    if keyword:
        products = products.filter(Q(name__icontains=keyword) | Q(category__name__icontains=keyword)).distinct()

    total_products = Product.objects.count()
    total_stock = Product.objects.aggregate(total=Sum('stock'))['total'] or 0
    low_stock_count = Product.objects.filter(stock__gt=0, stock__lte=5).count()
    out_of_stock_count = Product.objects.filter(Q(stock__lte=0) | Q(stock__isnull=True)).count()

    # Lấy 50 lần nhập kho gần nhất
    receipts = StockReceipt.objects.select_related('product').all().order_by('-date_added')[:50]

    context = {
        'products': products,
        'receipts': receipts,
        'keyword': keyword,
        'total_products': total_products,
        'total_stock': total_stock,
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
    }
    return render(request, 'app/manage_inventory.html', context)

from django.http import JsonResponse
import json

def apply_voucher(request):
    data = json.loads(request.body)
    voucher_code = data.get('code', '').strip()
    total = data.get('total', 0)

    try:
        total = float(total)
    except (TypeError, ValueError):
        total = 0

    if not voucher_code:
        return JsonResponse({'success': False, 'message': 'Vui lòng nhập mã voucher!'})
    
    try:
        voucher = Voucher.objects.get(code__iexact=voucher_code, active=True)
        discount = voucher.get_discount(total)

        if voucher.discount_type == 'percent':
            message = f'✅ Đã áp dụng giảm {voucher.discount_percent}% (-{discount:,.0f}đ)'
        else:
            message = f'✅ Đã áp dụng giảm {discount:,.0f}đ'

        return JsonResponse({
            'success': True,
            'discount': discount,
            'discount_type': voucher.discount_type,
            'discount_percent': voucher.discount_percent,
            'message': message.replace(',', '.')
        })
    except Voucher.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Mã không tồn tại hoặc đã hết hạn!'})
