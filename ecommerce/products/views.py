from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView
from django.shortcuts import render, Http404, get_object_or_404

from analytics.mixins import ObjectViewedMixin
from carts.models import Cart
# Create your views here.
from .models import Product

class ProductFeaturedListView(ListView):
    template_name = "products/list.html"

    def get_queryset(self, *args, **kwargs):
        request = self.request
        return Product.objects.all().featured()

class ProductFeaturedDetailView(ObjectViewedMixin, DetailView):
    queryset = Product.objects.all().featured()
    template_name = "products/featured-detail.html"

class UserProductHistoryView(LoginRequiredMixin, ListView):
    template_name = "products/user-history.html"

    def get_context_data(self, *args, **kwargs):
        context = super(UserProductHistoryView, self).get_context_data(*args, **kwargs)
        request = self.request
        cart_obj, new_obj = Cart.objects.new_or_get(request)
        context['cart'] = cart_obj
        return context

    def get_queryset(self, *args, **kwargs):
        request = self.request
        views = request.user.objectviewed_set.by_model(Product, model_queryset=False)
        return views


class ProductListView(ListView):
    template_name = "products/list.html"

    def get_context_data(self, *args, **kwargs):
        context = super(ProductListView, self).get_context_data(*args, **kwargs)
        request = self.request
        cart_obj, new_obj = Cart.objects.new_or_get(request)
        context['cart'] = cart_obj
        return context

    def get_queryset(self, *args, **kwargs):
        request = self.request
        return Product.objects.all()

class ProductDetailSlugView(ObjectViewedMixin, DetailView):
    queryset = Product.objects.all()
    template_name = "products/detail.html"

    def get_context_data(self, *args, **kwargs): # hacemos override de get_context_data
        context = super(ProductDetailSlugView, self).get_context_data(*args, **kwargs) # definimos como context
        # lo que inicialmente hace el método get_context_data de la clase
        # DetailView
        request = self.request # definimos como request, el objeto request de la
        # sesión actual
        cart_obj, new_obj = Cart.objects.new_or_get(request) # aquí definimos como cart_obj
        # o el Cart que ya existe (si viene en la request.session actual) o sino creamos el cart
        # y ese cart que creamos servirá para el nuevo producto que se seleccione.
        # IMPORTANTE: new_or_get es un method definido para el model objects (dento de su model manager),
        # que toma la información de request.session, y revisa si hay un cart o lo crea.
        # REVISAR carts/models.py
        # Es decir o seleccionamos el cart que ya existe y que viene en la request o creamos uno nuevo
        # que podrá ser utilizado como cart en los productos que más tarde se elijan
        context['cart'] = cart_obj # incluímos el cart dentro del context, para que quede definido
        # el cart para el producto, ya sea para que sea el cart definitivo o para que sea el cart
        # en el cual incluir nuevos productos
        return context

    def get_object(self, *args, **kwargs):
        request = self.request # definimos como request, el objeto request de la
        # sesión actual
        slug = self.kwargs.get('slug') #cuando se crea un producto, con signal,
        # se crea el campo slug. Ese slug es único (por como se crea el slug),
        # por lo que nos sirve para identificar un producto único. En la list.html
        # se muestran los diferentes productos, como instance=object, en el for for
        # se indica for object in object_list. Aquí lo que hacemos es definir como slug
        # el slug asociado al producto, porque esto se hace en la instancia self
        try:
            instance = Product.objects.get(slug=slug, active=True) # seleccionamos
            # como instancia el producto que tiene el slug antes definido
        except Product.DoesNotExist:
            raise Http404("Not Found")
        except Product.MultipleObjectsReturned:
            qs = Products.objects.filter(slug=slug, active=True)
            instance = qs.first()
        except:
            raise Http404("Uhmmmm")
        return instance # generamos el producto como instancia
