from .models import FlashSale
from django.contrib import admin
from django.utils.html import format_html
from .models import * # --- CẤU HÌNH GIAO DIỆN CHUNG ---
admin.site.site_header = 'Hệ thống Quản trị Shoppyy Fashion'
admin.site.site_title = 'Quản trị Shoppyy'
admin.site.index_title = 'Bảng điều khiển quản lý cửa hàng'

# --- 1. QUẢN LÝ DANH MỤC ---
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'is_sub', 'sub_category']
    prepopulated_fields = {'slug': ('name',)} # Tự động tạo slug khi gõ tên

# --- 2. QUẢN LÝ SẢN PHẨM (Hiển thị ảnh và Size) ---
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    def image_tag(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width: 45px; height:45px; border-radius:5px; object-fit:cover;" />', obj.image.url)
        return "No Image"
    image_tag.short_description = 'Ảnh'

    list_display = ('name', 'price', 'flash_sale', 'discount_percent')
    list_filter = ['category', 'sizes']
    search_fields = ['name']
    list_editable = ('flash_sale', 'discount_percent')
    # Hàm để hiển thị danh sách size ngoài bảng
    def display_sizes(self, obj):
        return ", ".join([s.name for s in obj.sizes.all()])
    display_sizes.short_description = 'Các Size'

# --- 3. QUẢN LÝ ĐƠN HÀNG (Phân loại màu sắc) ---
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    def status_color(self, obj):
        colors = {
            'Đang giao': '#ffc107',
            'Đã xác nhận': '#6f42c1',
            'Đã giao': '#28a745',
            'Đã hủy': '#dc3545',
            'Yêu cầu trả hàng': '#fd7e14',
            'Đã trả hàng/Hoàn tiền': '#343a40',
            'Chờ xác nhận': '#17a2b8',
        }
        color = colors.get(obj.status, '#6c757d')
        text_color = 'black' if obj.status == 'Đang giao' else 'white'
        return format_html('<span style="background-color: {}; color: {}; padding: 5px 10px; border-radius: 5px; font-weight: bold;">{}</span>', color, text_color, obj.status)
    
    status_color.short_description = 'Trạng thái'

    list_display = ['id', 'customer', 'payment_method', 'date_order', 'status_color','status']
    list_editable = ['status']
    list_filter = ['status', 'payment_method']
    search_fields = ['id', 'customer__username']

    def get_queryset(self, request):
        # Chỉ hiện các đơn đã bấm đặt hàng (complete=True)
        return super().get_queryset(request).filter(complete=True)

# --- 4. CHI TIẾT ĐƠN HÀNG (Hiển thị Size khách chọn) ---
@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product', 'size', 'quantity', 'get_total']
    list_filter = ['order']

# --- 5. ĐỊA CHỈ GIAO HÀNG ---
@admin.register(ShippingAddress)
class ShippingAddressAdmin(admin.ModelAdmin):
    list_display = ['order', 'customer', 'mobile', 'city', 'address']

# --- 7. QUẢN LÝ SIZE ---
@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']

# --- 8. QUẢN LÝ ĐÁNH GIÁ (FEEDBACK) ---
@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['customer', 'product', 'rating', 'date_added']
    list_filter = ['rating', 'date_added']

# --- 6. HỒ SƠ KHÁCH HÀNG ---
@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'address']

@admin.register(Voucher)
class VoucherAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_amount', 'active')
    list_editable = ('active', 'discount_amount') # Sửa trực tiếp ngoài bảng

@admin.register(FlashSale)
class FlashSaleAdmin(admin.ModelAdmin):
    list_display = ('name', 'discount_percent', 'start_date', 'end_date', 'active')
    list_editable = ('active', 'discount_percent')