from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# 7. BẢNG QUẢN LÝ SIZE (Mới thêm)
class Size(models.Model):
    name = models.CharField(max_length=10, verbose_name="Tên Size (S, M, L, XL...)")
    
    class Meta:
        verbose_name = "Size"
        verbose_name_plural = "7. Quản lý Size"

    def __str__(self):
        return self.name


# 1. BẢNG DANH MỤC
class Category(models.Model):
    sub_category = models.ForeignKey('self', on_delete=models.CASCADE, related_name='sub_categories', null=True, blank=True, verbose_name="Danh mục cha")
    is_sub = models.BooleanField(default=False, verbose_name="Là danh mục con")
    name = models.CharField(max_length=200, null=True, verbose_name="Tên danh mục")
    slug = models.SlugField(max_length=200, unique=True, verbose_name="Đường dẫn tĩnh (Slug)")

    class Meta:
        verbose_name = "Danh mục"
        verbose_name_plural = "1. Quản lý Danh mục"

    def __str__(self):
        return self.name


# 2. BẢNG SẢN PHẨM
class Product(models.Model):
    category = models.ManyToManyField(Category, related_name='product', verbose_name="Thuộc danh mục")
    name = models.CharField(max_length=200, null=True, verbose_name="Tên sản phẩm")
    price = models.FloatField(verbose_name="Giá tiền")
    digital = models.BooleanField(default=False, null=True, blank=True, verbose_name="Sản phẩm số")
    image = models.ImageField(null=True, blank=True, verbose_name="Hình ảnh")
    stock = models.IntegerField(default=10, null=True, blank=True) # Số lượng tồn kho mặc định là 10
    flash_sale = models.ForeignKey('FlashSale', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Tham gia Sự kiện Sale")
    discount_percent = models.IntegerField(default=0, verbose_name="Giảm bao nhiêu % ?")


    # === THÊM LIÊN KẾT VỚI SIZE ===
    sizes = models.ManyToManyField(Size, blank=True, verbose_name="Các size hiện có")

    class Meta:
        verbose_name = "Sản phẩm"
        verbose_name_plural = "2. Quản lý Sản phẩm"

    def __str__(self):
        return self.name

    @property
    def final_price(self):
        # 1. Kiểm tra sản phẩm này có tham gia Sự kiện nào không và sự kiện đó có đang Bật không
        if self.flash_sale and self.flash_sale.active:
            now = timezone.now()
            # 2. Kiểm tra hiện tại có đang trong thời gian diễn ra sự kiện không
            if self.flash_sale.start_date <= now <= self.flash_sale.end_date:
                # 3. Tính giá trị giảm dựa trên % riêng của sản phẩm này
                if self.discount_percent > 0:
                    discount_amount = (self.price * self.discount_percent) / 100
                    return self.price - discount_amount
        
        # Nếu không có Sale hoặc hết giờ Sale -> Bán giá gốc
        return self.price

    @property
    def ImageURL(self):
        try:
            url = self.image.url
        except:
            url = ''
        return url


# === THÊM DANH SÁCH TRẠNG THÁI ĐƠN HÀNG ===
STATUS_CHOICES = (
    ('Chờ xác nhận', 'Chờ xác nhận'),
    ('Đã xác nhận', 'Đã xác nhận'),
    ('Đang giao', 'Đang giao'),
    ('Đã giao', 'Đã giao'),
    ('Yêu cầu trả hàng', 'Yêu cầu trả hàng'),
    ('Đã trả hàng/Hoàn tiền', 'Đã trả hàng/Hoàn tiền'),
    ('Đã hủy', 'Đã hủy'),
)

# 3. BẢNG ĐƠN HÀNG
class Order(models.Model):
    customer = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, verbose_name="Khách hàng")
    date_order = models.DateTimeField(auto_now_add=True, verbose_name="Ngày đặt")
    complete = models.BooleanField(default=False, null=True, blank=True, verbose_name="Đã hoàn thành")
    transaction_id = models.CharField(max_length=200, null=True, verbose_name="Mã giao dịch")
    payment_method = models.CharField(max_length=50, default='COD', verbose_name="Phương thức thanh toán")
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Chờ xác nhận', verbose_name="Trạng thái đơn hàng")
    return_reason = models.TextField(null=True, blank=True, verbose_name="Lý do trả hàng")

    # === VOUCHER ĐÃ ÁP DỤNG CHO ĐƠN HÀNG ===
    voucher = models.ForeignKey('Voucher', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Voucher đã dùng")
    voucher_discount = models.FloatField(default=0, verbose_name="Số tiền được giảm")
    final_total = models.FloatField(default=0, verbose_name="Tổng tiền sau giảm")
    stock_restored = models.BooleanField(default=False, verbose_name="Đã hoàn kho")
    
    class Meta:
        verbose_name = "Đơn hàng"
        verbose_name_plural = "3. Quản lý Đơn hàng"

    def __str__(self):
        return str(self.id)
    
    @property
    def get_cart_total(self):
        orderitems = self.orderitem_set.all()
        total = sum([item.get_total for item in orderitems])
        return total

    @property
    def get_cart_items(self):
        orderitems = self.orderitem_set.all()
        total = sum([item.quantity for item in orderitems])
        return total

    @property
    def get_cart_total_after_discount(self):
        # Nếu đơn đã chốt và có lưu final_total thì ưu tiên lấy tổng đã giảm
        if self.complete and self.final_total and self.final_total > 0:
            return self.final_total

        total = self.get_cart_total - self.voucher_discount
        if total < 0:
            total = 0
        return total

    def has_enough_stock(self):
        """Kiểm tra toàn bộ sản phẩm trong đơn còn đủ tồn kho để chốt đơn hay không."""
        for item in self.orderitem_set.select_related('product').all():
            if item.product and item.product.stock is not None and item.quantity > item.product.stock:
                return False, item
        return True, None

    def reduce_stock(self):
        """Trừ tồn kho sau khi đặt hàng thành công."""
        for item in self.orderitem_set.select_related('product').all():
            product = item.product
            if product and product.stock is not None:
                product.stock = max(0, product.stock - item.quantity)
                product.save(update_fields=['stock'])

    def restore_stock(self):
        """Cộng lại tồn kho khi đơn bị hủy hoặc được hoàn hàng. Chỉ hoàn kho 1 lần."""
        if self.stock_restored:
            return

        for item in self.orderitem_set.select_related('product').all():
            product = item.product
            if product:
                product.stock = (product.stock or 0) + item.quantity
                product.save(update_fields=['stock'])

        self.stock_restored = True
        self.save(update_fields=['stock_restored'])


# 4. BẢNG CHI TIẾT ĐƠN HÀNG
class OrderItem(models.Model):
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, blank=True, null=True, verbose_name="Sản phẩm")
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, blank=True, null=True, verbose_name="Đơn hàng")
    quantity = models.IntegerField(default=0, null=True, blank=True, verbose_name="Số lượng")
    date_added = models.DateTimeField(auto_now_add=True, verbose_name="Ngày thêm")
    
    # === THÊM CỘT LƯU SIZE KHI MUA ===
    size = models.CharField(max_length=20, null=True, blank=True)

    class Meta:
        verbose_name = "Chi tiết đơn hàng"
        verbose_name_plural = "4. Chi tiết Đơn hàng"

    @property
    def get_total(self):
        if self.product is None:
            return 0
        total = self.product.final_price * self.quantity
        return total


# 8. BẢNG ĐÁNH GIÁ - FEEDBACK (Mới thêm)
class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews', verbose_name="Sản phẩm")
    customer = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Người đánh giá")
    content = models.TextField(verbose_name="Nội dung đánh giá")
    rating = models.IntegerField(default=5, verbose_name="Số sao (1-5)")
    date_added = models.DateTimeField(auto_now_add=True, verbose_name="Ngày gửi")

    class Meta:
        verbose_name = "Đánh giá"
        verbose_name_plural = "8. Quản lý Đánh giá"

    def __str__(self):
        return f"{self.customer.username} - {self.product.name}"


# 5. BẢNG ĐỊA CHỈ GIAO HÀNG
class ShippingAddress(models.Model):
    customer = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, verbose_name="Khách hàng")
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, blank=True, null=True, verbose_name="Đơn hàng")
    address = models.CharField(max_length=200, null=True, verbose_name="Địa chỉ cụ thể")
    city = models.CharField(max_length=200, null=True, verbose_name="Tỉnh/Thành phố")
    state = models.CharField(max_length=200, null=True, verbose_name="Quận/Huyện")
    mobile = models.CharField(max_length=10, null=True, verbose_name="Số điện thoại")
    date_added = models.DateTimeField(auto_now_add=True, verbose_name="Ngày thêm")

    class Meta:
        verbose_name = "Địa chỉ giao hàng"
        verbose_name_plural = "5. Địa chỉ Giao hàng"

    def __str__(self):
        return self.address


# 6. BẢNG HỒ SƠ KHÁCH HÀNG
class CustomerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Tài khoản")
    phone = models.CharField(max_length=15, null=True, blank=True, verbose_name="Số điện thoại")
    address = models.CharField(max_length=200, null=True, blank=True, verbose_name="Địa chỉ")

    class Meta:
        verbose_name = "Hồ sơ khách hàng"
        verbose_name_plural = "6. Hồ sơ Khách hàng"

    def __str__(self):
        return self.user.username
    
    
class StockReceipt(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, verbose_name="Sản phẩm")
    quantity = models.IntegerField(default=0, verbose_name="Số lượng nhập")
    date_added = models.DateTimeField(auto_now_add=True, verbose_name="Ngày nhập")
    note = models.CharField(max_length=200, null=True, blank=True, verbose_name="Ghi chú")

    class Meta:
        verbose_name = "Phiếu nhập kho"
        verbose_name_plural = "9. Quản lý Kho"

    def __str__(self):
        product_name = self.product.name if self.product else "Sản phẩm đã xóa"
        return f"Nhập {self.quantity} {product_name} - {self.date_added.strftime('%d/%m/%Y')}"
    

class Voucher(models.Model):
    DISCOUNT_TYPE_CHOICES = (
        ('amount', 'Giảm theo số tiền'),
        ('percent', 'Giảm theo phần trăm'),
    )

    code = models.CharField(max_length=50, unique=True, verbose_name="Mã Voucher")
    discount_type = models.CharField(
        max_length=20,
        choices=DISCOUNT_TYPE_CHOICES,
        default='amount',
        verbose_name="Loại giảm giá"
    )
    discount_amount = models.IntegerField(default=0, verbose_name="Số tiền giảm (VND)")
    discount_percent = models.IntegerField(default=0, verbose_name="Phần trăm giảm (%)")
    active = models.BooleanField(default=True, verbose_name="Kích hoạt")

    def get_discount(self, total):
        try:
            total = float(total)
        except (TypeError, ValueError):
            total = 0

        if self.discount_type == 'percent':
            percent = max(0, min(self.discount_percent, 100))
            discount = total * percent / 100
        else:
            discount = self.discount_amount

        # Không cho giảm vượt quá tổng đơn
        return min(float(discount), total)

    def __str__(self):
        if self.discount_type == 'percent':
            return f"{self.code} - Giảm {self.discount_percent}%"
        return f"{self.code} - Giảm {self.discount_amount} VND"

class FlashSale(models.Model):
    name = models.CharField(max_length=100, verbose_name="Tên sự kiện (VD: Đại lễ 30/4)")
    discount_percent = models.IntegerField(verbose_name="Phần trăm giảm (%)", default=0)
    start_date = models.DateTimeField(verbose_name="Bắt đầu từ")
    end_date = models.DateTimeField(verbose_name="Kết thúc lúc")
    active = models.BooleanField(default=True, verbose_name="Kích hoạt")

    def __str__(self):
        return f"{self.name} - Giảm {self.discount_percent}%"
