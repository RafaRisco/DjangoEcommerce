from django.shortcuts import render, redirect
from django.utils.http import is_safe_url

from billing.models import BillingProfile
from .forms import AddressForm
from .models import Address
# Create your views here.

# en este caso, es cuando se crea una nueva dirección. En este caso, se procesa la información que viene del formulario y se guarda como address
def checkout_address_create_view(request):
    form = AddressForm(request.POST or None) # creamos una instancia de AddressForm, incluyendo la información
    # del formulario completo (por eseo incluímos request.POST)
    context = {
        "form": form # pasamos la instancia de AddressForm como context para la view
    }
    next_ = request.GET.get('next') # Este parámetro sirve para cuando este formulario está en en el checkout (en este caso), y lo que se
    # busca es que una vez completado el formulario, tener este atributo dentro del objeto request, que nos permita hacer una redirección
    # a la página que queramos. Es decir, cuando esta view es llamada, se va a defirnir en request el atributo next, que podemos usar
    # para definir a donde queremos redireccionar. Definimos a donde queremos redireccionar al llamar a esta vista y pasamos esa información
    # en el atributo next.En este caso, es cuando llamamos a esta vista desde el template carts/checkout.html (que a su vez llama al template
    # addresses/forms) se define
    next_post = request.POST.get('next') # esto es igual que antes, pero si el atributo next viene de una request post y no get
    redirect_path = next_ or next_post or None # como la request solo puede ser get o post, lo ponemos dentro de redirect_path. Aquí lo que
    # estamos poniendo es el valor del atributo next, que viene en la request, desde la página en que se llama a esta view
    if form.is_valid(): # si el formulario en el cual se incluye el mail del usuario invitado es válido
        instance = form.save(commit=False) # no guardamos todavía la información del formulario, porque queremos incluir más información

        billing_profile, billing_profile_created = BillingProfile.objects.new_or_get(request) # seleccionamos (o creamos) el billing profile, mediante el method new_or_get
        # que es un method creado en el model manager del model BillingProfile, que lo que hace es, con base en un usuario y un email (información que toma de request), crea
        # o elige un billing profile concreto.

        if billing_profile is not None: # si existe un billing profile
            address_type = request.POST.get('address_type', 'shipping' ) # tomamos la información del formulario pre_addresses.html, que está inserto en checkout.html,
            # con el name de address_type. Si no hay address_type, mostramos por defecto shipping. Esto nos sirve para saber si es la shipping o la billing address.
            instance.billing_profile = billing_profile # incluímos también la información del billing_profile en instance, variable que definimos antes
            instance.address_type = address_type # incluímos la informaicón de address_type en la instance
            instance.save() # una vez hemos incluído la información de billing_profile y de address_type, guardamos la instancia, en este caso la Address

            request.session[address_type + "_address_id"] = instance.id # pasamos la información a request.session, definiendo el address_type y address_id.
        else:
            return redirect("cart:checkout") # si hay un billing_profile, redireccionamos a cart:checkout
        if is_safe_url(redirect_path, request.get_host()): # is_safe_url, verifica que la dirección a la que queremos redireccionar, que en
        # este caso viene dada por redirect_path (y en donde la ), es una URL segura
            return redirect(redirect_path) # aquí, redireccionamos
    return redirect("cart:checkout")


# IMPORTANTE: EL OBJETIVO DE ESTA VIEW, ES PASAR INFORMACIÓN DE LA SHIPPING O BILLING ADDRESS A TRAVÉS DE REQUEST.SESSION. ESA INFORMACIÓN SERÁ TOMADA
# POR LA VIEW CHECKOUT_VIEW (DENTRO DE CART), Y SERVIRÁ PARA DEFINIR LA BILLING Y SHIPPING ADDRESS DEL PEDIDO. ES DECIR, ESTA VIEW, DEFINE LA SHIPPING Y BILLING
# ADDRESS (EN CASO DE QUE SE UTILICE UNA EXISTENTE) Y PASA ESA INFORMACIÓN (MEDIENTE REQUEST) A LA VIEW CHECKOUT_VIEW, PARA QUE LA ADJUNTE AL PEDIDO

def checkout_address_reuse_view(request): # esta es la view que es llamada desde el formulario pre_addresses.html, que está inserto en checkout.html
    if request.user.is_authenticated: # verificamos si el usuario está autenticado
        context = {} # esta vista va a procesar una información, pero no va a mostrar un template en concreto, así que no tiene context, o información que pasar a un template
        next_ = request.GET.get('next') # esta información viene desde el formulario pre_addresses.html, que está inserto en checkout.html. Define a que url hay que navegar.
        # es este caso, lo que hace es obtener la información dentro del objeto request, en caso de que el method sea GET. Esto nos sirve para saber a que dirección se
        # redirecciona cuando se hace submit al formulario
        next_post = request.POST.get('next') # esta información viene desde el formulario pre_addresses.html, que está inserto en checkout.html. Define a que url hay que navegar.
        # es este caso, lo que hace es obtener la información dentro del objeto request, en caso de que el method sea POST. Esto nos sirve para saber a que dirección se
        # redirecciona cuando se hace submit al formulario
        redirect_path = next_ or next_post or None # se define una url a la que redirigir, independientemente de que proventa de un method GET o POST. Lo "unificamos" aquí
        if request.method == 'POST': # como esta vista es llamada desde un formulario, verificamos que es un method=POST
            shipping_address = int(str(request.POST.get('shipping_address', None)).replace("/", ""))
            # tomamos la información del formulario pre_addresses.html, que está inserto en checkout.html,
            # con el name de shipping_address, que es una shipping.id. Con esa información, definimos la variable shipping_address, como un número. Para que realmente sea un
            # número hay que convertirlo en integer (int) y eliminar "/". Esto nos sirve para saber la address.id que proviene del formulario, es decir, la que el usuario seleccionó
            # de entre las addresses que tenía
            address_type = request.POST.get('address_type', 'shipping' ) # tomamos la información del formulario pre_addresses.html, que está inserto en checkout.html,
            # con el name de address_type. Si no hay address_type, mostramos por defecto shipping. Esto nos sirve para saber si es la shipping o la billing address.
            billing_profile, billing_profile_created = BillingProfile.objects.new_or_get(request) # seleccionamos (o creamos) el billing profile, mediante el method new_or_get
            # que es un method creado en el model manager del model BillingProfile, que lo que hace es, con base en un usuario y un email (información que toma de request), crea
            # o elige un billing profile concreto.
            if shipping_address is not None: # si existe una shipping_address (antes definimos esta variable, en función de la shipping.is que recibe del formulario)
                qs = Address.objects.filter(billing_profile=billing_profile, id=shipping_address) # filtamos el model Address, para obtener una Address, con base en la variable
                # billing_profile y a id, que proviene directamente del formulario
                if qs.exists(): # si hay alguna dirección, es decir, si en el query anterior hay algún resultado
                    request.session[address_type + "_address_id"] = shipping_address # pasamos la información a request.session, definiendo el address_type y address_id.
                if is_safe_url(redirect_path, request.get_host()): # Redirecciona a redirect_path, que a su vez proviene de next o next_post, y que toma el valor del fomulario con
                # el name next
                    return redirect(redirect_path)
    return redirect("cart:checkout") # si el usuario no está autenticado, lo manda a la url cart:checkout, que manda al template checkout.html
