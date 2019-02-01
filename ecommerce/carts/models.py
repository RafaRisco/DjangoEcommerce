from decimal import Decimal
from django.conf import settings
from django.db import models
from django.db.models.signals import pre_save, post_save, m2m_changed


User = settings.AUTH_USER_MODEL

from products.models import Product

# Create your models here.
class CartManager(models.Manager): # modificamos el model manager. En este caso
# creamos nuevos methods, sin hacer override de ninguno. Para crear un model manager nuevo
# extendemos la class models.Manager

    def new_or_get(self, request):
        cart_id = request.session.get("cart_id", None) # revisamos si dentro de
        # request.session existe el atributo cart_id
        qs = self.get_queryset().filter(id=cart_id) # hacemos un query, asumiendo que
        # dentro de request.session existe el atributo cart_id
        if qs.count() == 1: # revisamos si en el query se generó algún elemento, eso
        # significaría que existe el atributo cart_id dentro de request.session
            new_obj = False # indicamos que no hemos tenido que crear un nuevo cart
            cart_obj = qs.first() # seleccionamos el primer elemento del query realizado
            # con el atributo cart_id de request.session
            if request.user.is_authenticated and cart_obj.user is None: # revisamos que el usuario
            # está registrado con request.user.is_authenticated y que el cart seleccionado en el
            # query, no tiene ningún usuario definido
                cart_obj.user = request.user # definimos el usuario del cart antes seleccionado en el query
                cart_obj.save() # salvamos el cart, una vez que ya definimos el usuario
        else: #en el caso de que dentro de request.session no exixte el atributo cart_id
            cart_obj = Cart.objects.new(user=request.user) # creamos el cart, y asignamos el usuario. Para crear
            # el cart, usamos el method new, que definimos abajo, dentro de este model manager
            # con base en request.user
            new_obj = True #indicamos que en este caso si se creo un nuevo cart
            request.session['cart_id'] = cart_obj.id # definimos el atributo cart_id para request_session
        return cart_obj, new_obj

    def new(self, user=None): # en este caso, definimos el method new, que crea un usaurio (para eso definimos arriba User = settings.AUTH_USER_MODEL)
        user_obj = None
        if user is not None: # si hay un usuario
            if user.is_authenticated: # y si el user está autenticado
                user_obj = user # definimos como user_obj el usuario autenticado
            return self.model.objects.create(user=user_obj) # aquí creamos el cart (porque self.model se refiere al model cart), y le asignamos como usuario
            # el usuario

class Cart(models.Model):
    user            = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)
    products        = models.ManyToManyField(Product, blank=True) # ManyToManyField significa que un producto puede estar en muchos cart, y un cart puede tener muchos productos
    subtotal        = models.DecimalField(default=0.00, max_digits=100, decimal_places=2)
    total           = models.DecimalField(default=0.00, max_digits=100, decimal_places=2)
    updated         = models.DateTimeField(auto_now=True)
    timestamp       = models.DateTimeField(auto_now_add=True)

    objects = CartManager() # definimos como model manager, el nuevo model manager definido, CartManager

    def __str__(self):
        return str(self.id)

def m2m_changed_cart_receiver(sender, instance, action, *args, **kwargs): # m2m es también un signal (nos permite ejecutar una función, en este caso, cuando
# cuando se ejecuta una acción en un model)
    if action == 'post_add' or action == 'post_remove' or action == 'post_clear': # las acciones en el model que van a ejecutar esta función son post_add
    # post_remove y post_clear (esto viene de la documentación)
        products = instance.products.all() # seleccionamos todos los productos del carro correspondiente
        total = 0 # definimos un valor inicial para el valor total del carro. Este es el valor de la suma de los productos del carro. ESTE TOTAL, ES UNA VARIABLE
        # QUE CREAMOS AQUÍ, NO EL ATRIBUTO TOTAL DEL MODEL CART
        for x in products: # iteramos por todos los productos del carro
            total += x.price # y vamos sumando al total, el valor de cada producto
        if instance.subtotal != total: # si el monto de total y de subtotan son diferentes
            instance.subtotal = total # ajustamos el valor de subtotal al de total
            instance.save()

m2m_changed.connect(m2m_changed_cart_receiver, sender=Cart.products.through) # conectamos la función de django signal, con el model
# en este caso, es el model Cart, y en concreto, lo conectamos con cuando haya un cambio en un producto del cart

def pre_save_cart_receiver(sender, instance, *args, **kwargs): # definimos otro signal, para calcular el total del valor del cart, en función
# del valor de los prodcutos más un % (imaginemos un impuesto o algo similar)
    if instance.subtotal > 0: # si el valor de los productos es mayor que 0
        instance.total = Decimal(instance.subtotal) * Decimal(1.08) # calculamos el total, multiplicando el subtotal (igual a la suma del valor
        # de los productos) por 1,08 (es decir, agregamos el 8%). IMPORTANTE: tenemos que convertir los valores de decimal, para poder
        # operar con ellos
    else:
        instance.total = 0.00

pre_save.connect(pre_save_cart_receiver, sender=Cart) # conectamos la función de django signal, con el model
# en este caso, es el model Cart
