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
from .models import Voucher


def add_review(request, product_id):
    if request.method == 'POST' and request.user.is_authenticated:
        content = request.POST.get('content')
        rating = request.POST.get('rating')
        product = Product.objects.get(id=product_id)
        
        Review.objects.create(
            product=product,
            customer=request.user,
            content=content,
            rating=rating
        )
        messages.success(request, "Cảm ơn bạn đã đánh giá sản phẩm!")
    return redirect(request.META.get('HTTP_REFERER'))
@login_required(login_url='login')
def returnOrder(request, id):
    if request.method == 'POST':
        try:
            order = Order.objects.get(id=id, customer=request.user)
            reason = request.POST.get('reason')
            
            # Chỉ cho phép trả hàng khi đơn đã ở trạng thái "Đã giao"
            if order.status == 'Đã giao':
                order.status = 'Yêu cầu trả hàng'
                order.return_reason = reason
                order.save()
                messages.success(request, f'Đã gửi yêu cầu trả hàng cho đơn #{order.id}. Shop sẽ liên hệ bạn sớm!')
            else:
                messages.error(request, 'Đơn hàng chưa giao hoặc đã xử lý, không thể yêu cầu trả hàng!')
                
        except Order.DoesNotExist:
            messages.error(request, 'Đơn hàng không tồn tại!')
            
    return redirect('profile')
@login_required(login_url='login')
def cancelOrder(request, id):
    try:
        # Tìm đơn hàng dựa trên ID và người dùng hiện tại
        order = Order.objects.get(id=id, customer=request.user)
        
        # Chỉ cho phép hủy nếu đơn ở trạng thái 'Chờ xác nhận' hoặc 'Đã xác nhận'
        if order.status in ['Chờ xác nhận', 'Đã xác nhận']:
            order.status = 'Đã hủy'
            order.save()
            messages.success(request, f'✅ Đã hủy thành công đơn hàng #{order.id}!')
        else:
            messages.error(request, 'Không thể hủy đơn hàng này do đang giao hoặc đã hoàn thành!')
            
    except Order.DoesNotExist:
        messages.error(request, 'Đơn hàng không tồn tại!')
        
    # --- ĐỔI TẠI ĐÂY: Chuyển hướng về trang giỏ hàng (cart) ---
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
    # 1. Tìm đúng sản phẩm theo ID
    product = Product.objects.get(id=id)
    
    # 2. Copy đoạn code lấy Giỏ hàng & Danh mục (để thanh Menu không bị lỗi)
    if request.user.is_authenticated:
        customer = request.user 
        order, created = Order.objects.get_or_create(customer=customer, complete=False)
        cartItems = order.get_cart_items
    else:
        order = {'get_cart_total': 0, 'get_cart_items': 0}
        cartItems = order['get_cart_items']
        
    categories = Category.objects.all()

    # 3. Gửi dữ liệu sang trang HTML
    context = {'product': product, 'cartItems': cartItems, 'categories': categories}
    return render(request, 'app/detail.html', context)
def category(request):
    categories=Category.objects.filter(is_sub=False)
    active_category=request.GET.get('category','')
    if active_category:
        products=Product.objects.filter(category__slug=active_category)
    context = {'categories':categories,'products':products,'active_category':active_category}
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
    context = {'query': query, 'products': products, 'cartItems': cartItems}
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

def checkout(request):
    if request.user.is_authenticated:
        customer = request.user
        # Lấy giỏ hàng hiện tại của khách
        current_order, created = Order.objects.get_or_create(customer=customer, complete=False)
        
        # Lấy danh sách ID và Size khách đã tích chọn từ URL (Giỏ hàng gửi sang)
        selected_ids = request.GET.getlist('id')
        selected_sizes = request.GET.getlist('size')
        
        items = []
        total_selected = 0
        count_selected = 0

        if selected_ids:
            all_items = current_order.orderitem_set.all()
            for i in range(len(selected_ids)):
                # Xử lý size rỗng từ URL để khớp với Database (None)
                s_size = selected_sizes[i] if i < len(selected_sizes) and selected_sizes[i] != '' else None
                
                # Tìm item khớp ID và Size
                item = all_items.filter(product_id=selected_ids[i], size=s_size).first()
                if item:
                    items.append(item)
                    total_selected += item.get_total
                    count_selected += item.quantity
        else:
            # Nếu không có sản phẩm nào được chọn, quay về giỏ hàng
            return redirect('cart')

        # XỬ LÝ KHI BẤM NÚT "XÁC NHẬN ĐẶT HÀNG" (POST)
        if request.method == 'POST':
            name = request.POST.get('name')
            phone = request.POST.get('phone')
            address = request.POST.get('address')
            payment_method = request.POST.get('payment_method', 'COD')

            # 1. Tạo đơn hàng mới (Chốt đơn)
            new_order = Order.objects.create(
                customer=customer, 
                complete=True, 
                payment_method=payment_method,
                # Tự động để trạng thái Chờ xác nhận (Banking) hoặc Đã xác nhận (COD)
                status='Đã xác nhận' if payment_method == 'COD' else 'Chờ xác nhận'
            )

            # 2. Chuyển các món khách ĐÃ CHỌN sang đơn hàng mới này
            for item in items:
                item.order = new_order
                item.save()

            # 3. Lưu địa chỉ giao hàng
            ShippingAddress.objects.create(
                customer=customer,
                order=new_order,
                address=address,
                mobile=phone,
                city="Thái Nguyên" # Bạn có thể thêm input tỉnh thành nếu muốn
            )

            # --- THÊM THÔNG BÁO THEO PHƯƠNG THỨC THANH TOÁN ---
            if payment_method == 'Banking':
                messages.success(request, f'🎉 Đơn #{new_order.id} đang chờ xác nhận chuyển khoản! Shop sẽ kiểm tra và gửi hàng cho bạn ngay.')
            else:
                messages.success(request, f'🎉 Đơn #{new_order.id} đã được đặt thành công! Cảm ơn bạn đã mua sắm.')

            return redirect('home')

        # Gửi dữ liệu sang HTML
        context = {
            'items': items, 
            'order': current_order, 
            'cartItems': current_order.get_cart_items,
            'total_selected': total_selected, 
            'count_selected': count_selected  
        }
        return render(request, 'app/checkout.html', context)
    else:
        return redirect('login')


def updateItem(request):
    data = json.loads(request.body)
    productId = data['productId']
    action = data['action']
    
    # 1. Lấy size từ data
    size = data.get('size') 
    
    # 2. FIX: Nếu size là chuỗi rỗng thì chuyển thành None để khớp với Database
    if size == "" or size == "None":
        size = None

    customer = request.user
    product = Product.objects.get(id=productId)
    order, created = Order.objects.get_or_create(customer=customer, complete=False)

    # 3. Tìm hoặc tạo OrderItem
    orderItem, created = OrderItem.objects.get_or_create(
        order=order, 
        product=product, 
        size=size   
    )

   # XỬ LÝ LOGIC TỒN KHO TẠI ĐÂY
    if action == 'add':
        # Kiểm tra: Nếu số lượng trong giỏ >= tồn kho thì BÁO LỖI VÀ CHẶN LẠI
        if hasattr(product, 'stock') and product.stock is not None:
            if orderItem.quantity >= product.stock:
                return JsonResponse({
                    'status': 'error', 
                    'message': f'Rất tiếc, sản phẩm này chỉ còn {product.stock} chiếc trong kho!'
                })
        
        # Nếu kho vẫn còn hàng thì mới cho cộng thêm
        orderItem.quantity = (orderItem.quantity + 1)
        
    elif action == 'remove':
        orderItem.quantity = (orderItem.quantity - 1)
    elif action == 'delete':
        orderItem.quantity = 0

    orderItem.save()

    if orderItem.quantity <= 0:
        orderItem.delete()

    # Nếu thành công, trả về status success
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
            total_revenue += order.get_cart_total

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
    
    # XỬ LÝ KHI BẤM NÚT NHẬP KHO
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        quantity_added = int(request.POST.get('quantity', 0))
        note = request.POST.get('note', '')
        
        if quantity_added > 0:
            product = Product.objects.get(id=product_id)
            
            # 1. Tạo 1 dòng lịch sử nhập kho
            StockReceipt.objects.create(product=product, quantity=quantity_added, note=note)
            
            # 2. Cộng dồn số lượng vào Tồn kho hiện tại của sản phẩm
            product.stock = (product.stock or 0) + quantity_added
            product.save()
            
            messages.success(request, f'✅ Đã nhập thêm {quantity_added} "{product.name}" vào kho thành công!')
        return redirect('manage_inventory')
        
    products = Product.objects.all()
    # Lấy 50 lần nhập kho gần nhất
    receipts = StockReceipt.objects.all().order_by('-date_added')[:50] 
    
    context = {'products': products, 'receipts': receipts}
    return render(request, 'app/manage_inventory.html', context)


from django.http import JsonResponse
import json

