"""ecommerce URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static

from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.urls import path, include
from django.views.generic import TemplateView, RedirectView

from accounts.views import LoginView, RegisterView, GuestRegisterView
from addresses.views import checkout_address_create_view, checkout_address_reuse_view
from billing.views import payment_method_view, payment_method_create_view
from carts.views import cart_detail_api_view
from marketing.views import MarketingPreferenceUpdateView, MailchimpWebhookView
from .views import home_page, about_page, contact_page

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home_page, name='home'),
    path('about/', about_page, name='about'),
    path('login/', LoginView.as_view(), name='login'),
    path('checkout/address/create/', checkout_address_create_view, name='checkout_address_create'),
    path('checkout/address/reuse/', checkout_address_reuse_view, name='checkout_address_reuse'),
    path('register/guest/', GuestRegisterView.as_view(), name='guest_register'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('api/cart/', cart_detail_api_view, name='api-cart'),
    path('billing/payment-method/', payment_method_view, name='billing-payment-method'),
    path('billing/payment-method/create/', payment_method_create_view, name='billing-payment-method-endpoint'),
    path('register/', RegisterView.as_view(), name='register'),
    path('bootstrap/', TemplateView.as_view(template_name='bootstrap/example.html')),
    path('contact/', contact_page, name='contact'),
    path('products/', include(("products.urls", 'products'), namespace="Products")), # Así incluímos las urls de otras apps
    path('search/', include(("search.urls", 'search'), namespace="search")), # Así incluímos las urls de otras apps
    path('settings/email/', MarketingPreferenceUpdateView.as_view(), name='marketing-pref'),
    path('webhooks/mailchimp/', MailchimpWebhookView.as_view(), name='webhook-mailchimp'),
    path('cart/', include(("carts.urls", 'cart'), namespace="cart")), # Así incluímos las urls de otras apps
    path('accounts/', RedirectView.as_view(url='/account')),
    path('settings/', RedirectView.as_view(url='/account')),
    path('account/', include(("accounts.urls", 'accounts'), namespace="account")), # Así incluímos las urls de otras apps
    path('accounts/', include("accounts.passwords.urls")),
]

if settings.DEBUG: # Así incluímos los archivos estáticos
    urlpatterns + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
