from django.contrib import admin
from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
urlpatterns = [
    path('', views.home,name="home"),
    path('register/', views.register, name="register"),
    path('login/', views.loginPage, name="login"),
    path('search/', views.search, name="search"),
    path('category/', views.category, name="category"),
    path('logout/', views.logoutPage, name="logout"),
    path('cart/', views.cart, name="cart"),
    path('checkout/', views.checkout, name="checkout"),
    path('update_item/', views.updateItem, name="update_item"),
    path('detail/<int:id>/', views.detail, name="detail"),
    path('profile/', views.profile, name="profile"),
    path('cancel_order/<int:id>/', views.cancelOrder, name="cancelOrder"),
   path('reset_password/', auth_views.PasswordResetView.as_view(template_name="app/password_reset.html"), name="reset_password"),
    path('reset_password_sent/', auth_views.PasswordResetDoneView.as_view(template_name="app/password_reset_sent.html"), name="password_reset_done"),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name="app/password_reset_form.html"), name="password_reset_confirm"),
    path('reset_password_complete/', auth_views.PasswordResetCompleteView.as_view(template_name="app/password_reset_done.html"), name="password_reset_complete"),
    path('return_order/<int:id>/', views.returnOrder, name="return_order"),
    path('add_review/<int:product_id>/', views.add_review, name="add_review"),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('inventory/', views.manage_inventory, name='manage_inventory'),
    path('apply_voucher/', views.apply_voucher, name='apply_voucher'),
]

