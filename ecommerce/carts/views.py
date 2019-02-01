from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render, redirect


from accounts.forms import LoginForm, GuestForm
from accounts.models import GuestEmail

from addresses.models import Address
from addresses.forms import AddressForm

from billing.models import BillingProfile
from orders.models import Order
from products.models import Product
from .models import Cart

import stripe
STRIPE_SECRET_KEY = getattr(settings, "STRIPE_SECRET_KEY", "sk_test_7he6WFXWOAYrQ0JEyi8uRENZ")
STRIPE_PUB_KEY = getattr(settings, "STRIPE_PUB_KEY", "pk_test_ZmSXcc08zVzpIXu0Q97jOebQ")
stripe.api_key = STRIPE_SECRET_KEY
# Create your views here.

# creamos esta view para ajax. Esta view, está asociada a la url (que esta en ecommerce.urls.py) con el name api-cart
def cart_detail_api_view(request):
    cart_obj, new_obj = Cart.objects.new_or_get(request) # empleamos el method creado en el model manager de Cart, new_or_get, que nos permite
    # crear un cart si no existe o seleccionarlo si existe (mediante la información en request.session)
    products = [{
            "id": x.id,
            "url": x.get_absolute_url(),
            "name": x.name,
            "price": x.price
            } for x in cart_obj.products.all()] # definimos la información para usar en ajax. Hacemos un loop por los productos del cart creado o seleccionado
            # , asignando diferentes variables del producto (id, url, name, price), y toda esa información la incluímos dentro de prodcuts como un diccionario
    cart_data = {"products": products, "subtotal": cart_obj.subtotal, "total": cart_obj.total} #
    return JsonResponse(cart_data)

def cart_home(request):
    cart_obj, new_obj = Cart.objects.new_or_get(request) # seleccionamos el cart
    # que proviene de request.session o lo creamos
    # IMPORTANTE: new_or_get es un method definido para el model objects (dento de su model manager),
    # que toma la información de request.session, y revisa si hay un cart o lo crea.
    # REVISAR carts/models.py
    # si el cart esta vacío, se mostrará vacío.
    # si se añade un producto al cart, a traves de la vista cart_update (está abajo), se habrá definido
    # un cart, que ya tendrá productos, y que será el que se pasará como argumento a esta vista, y no se creará uno nuevo
    return render(request, "carts/home.html", {'cart': cart_obj})

def cart_update(request):
    product_id = request.POST.get('product_id') # seleccionamos el producto, para
    # eso, utilizamos la información que viene de detail.html, y en concreto de
    # update-cart.html, que está dentro de detail.html, que tiene un formulario,
    # que manda la información de product.id con el nombre de product_id. Esa información
    # se traspasa mediante request.
    if product_id is not None:
        try:
            product_obj = Product.objects.get(id=product_id) # seleccionamos el
            #producto en función de la id
        except Product.DoesNotExist:
            redirect("cart:home") # redireccionamos a cart:home (donde aparece el cart). Esta view no
            # tiene su html propio. No hay un html que se llame cart-update.html
        cart_obj, new_obj = Cart.objects.new_or_get(request) # seleccionamos el cart
        # que proviene de request.session o lo creamos
        # IMPORTANTE: new_or_get es un method definido para el model objects (dento de su model manager),
        # que toma la información de request.session, y revisa si hay un cart o lo crea.
        # REVISAR carts/models.py
        # Es decir o seleccionamos el cart que ya existe y que viene en la request o creamos uno nuevo
        # que podrá ser utilizado como cart en los productos que más tarde se elijan
        if product_obj in cart_obj.products.all(): # si el producto esta en el cart, lo eliminamos
            cart_obj.products.remove(product_obj)
            added = False
        else:
            cart_obj.products.add(product_obj) # si el producto no está en el cart, lo eliminamos
            added = True
        request.session['cart_items'] = cart_obj.products.count() # definimos el atributo cart_items (no cart_id)
        # , que define el total de productos en el cart, en request.session
        if request.is_ajax():
            print("Ajax request")
            json_data = {
                "added": added,
                "removed": not added,
                "cartItemCount": cart_obj.products.count()
            }
            return JsonResponse(json_data)
    return redirect("cart:home") # redireccionamos a cart:home (donde aparece el cart). Esta view no
    # tiene su html propio. No hay un html que se llame cart-update.html

def checkout_home(request):
    cart_obj, cart_created = Cart.objects.new_or_get(request) # seleccionamos el cart
    # que proviene de request.session o lo creamos
    # IMPORTANTE: new_or_get es un method definido para el model objects (dento de su model manager),
    # que toma la información de request.session, y revisa si hay un cart o lo crea.
    # REVISAR carts/models.py
    # Es decir o seleccionamos el cart que ya existe y que viene en la request o creamos uno nuevo
    # que podrá ser utilizado como cart en los productos que más tarde se elijan
    order_obj = None
    if cart_created or cart_obj.products.count() == 0: # si hemos creado el cart, o está vacía, se redirige
    # al cart (cart:home), porque el cart estará vacío (y no se podrá hacer checkout, porque no hay productos
    # en el cart para hacer checkout)
        return redirect("cart:home")

    login_form = LoginForm(request=request) # creamos una instancia del formulario para logearse como usuario
    guest_form = GuestForm(request=request) # creamos una instancia del formulario para loguearse como usuario invitado
    billing_address_id = request.session.get('billing_address_id', None)
    shipping_address_id = request.session.get('shipping_address_id', None)
    address_form = AddressForm()

    billing_profile, billing_profile_created = BillingProfile.objects.new_or_get(request) # new_or_ger es un method definido en el model manager del
    # model BillingProfile, que lo que hace es tomando el user y el guest_email_id que están en request, crea un BillingProfile para el usuario
    # o para el usuario invitado, según corresponda
    address_qs = None
    has_card = False

    if billing_profile is not None: # en este caso, ya hay un BillingProfile
        if request.user.is_authenticated:
            address_qs = Address.objects.filter(billing_profile=billing_profile)
        order_obj, order_obj_created = Order.objects.new_or_get(billing_profile, cart_obj) # este es un method creado al hacer override el model Manager
        # del model Order. El methos new_or_get, lo que hace es tomar las instancias del model order vinculados a un BillingProfile y
        # un cart en particular, y que están activas, y si es una, esa es la order, si no hay una la crea.
        # si hay más de una, hay un signal, que lo que hace es que cuando se crea una order, hace un query de todas las orders vinculadas
        # al cart y excluyendo las que están vinculadas al mismo BillingProfile de esa order, y modifica el estatus de esas otras orders
        # a incativas
        if shipping_address_id:
            order_obj.shipping_address = Address.objects.get(id=shipping_address_id)
            del request.session['shipping_address_id']
        if billing_address_id:
            order_obj.billing_address = Address.objects.get(id=billing_address_id)
            del request.session['billing_address_id']
        if billing_address_id or shipping_address_id:
            order_obj.save()
        has_card = billing_profile.has_card

    if request.method == "POST":
        is_prepared = order_obj.check_done()
        if is_prepared:
            did_charge, crg_msg = billing_profile.charge(order_obj)
            if did_charge:
                order_obj.mark_paid()
                request.session['cart_items'] = 0
                del request.session['cart_id']
                if not billing_profile.user:
                    billing_profile.set_cards_inactive()
                return redirect("cart:success")
            else:
                print(crg_msg)
                return redirect("cart:checkout")

    context = { # definimos los elementos del context
        "object": order_obj,
        "billing_profile": billing_profile,
        "login_form": login_form,
        "guest_form": guest_form,
        "address_form": address_form,
        "address_qs": address_qs,
        "has_card": has_card,
        "publish_key": STRIPE_PUB_KEY
    }
    return render(request, "carts/checkout.html", context)

def checkout_done_view(request):
    return render(request, "carts/checkout-done.html", {})
