from django.utils.http import is_safe_url

class RequestFormAttachMixin(object):
    def get_form_kwargs(self):
        kwargs = super(RequestFormAttachMixin, self).get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

class NextUrlMixin(object):
    default_next = "/"
    def get_next_url(self):
        request = self.request
        next_ = request.GET.get('next') # Este parámetro sirve para cuando este formulario está en en el checkout (en este caso), y lo que se
        # busca es que una vez completado el formulario, tener este atributo dentro del objeto request, que nos permita hacer una redirección
        # a la página que queramos. Es decir, cuando esta view es llamada, se va a defirnir en request el atributo next, que podemos usar
        # para definir a donde queremos redireccionar. Definimos a donde queremos redireccionar al llamar a esta vista y pasamos esa información
        # en el atributo next.En este caso, es cuando llamamos a esta vista desde el template carts/checkout.html (que a su vez llama al template
        # accounts/snippets/forms) se define
        next_post = request.POST.get('next') # esto es igual que antes, pero si el atributo next viene de una request post y no get
        redirect_path = next_ or next_post or None # como la request solo puede ser get o post, lo ponemos dentro de redirect_path. Aquí lo que
        # estamos poniendo es el valor del atributo next, que viene en la request, desde la página en que se llama a esta view
        if is_safe_url(redirect_path, request.get_host()): # si se definió una url a la que queremos redireccionar (es decir, si existió
            # el atributo next, dentro de request.session (ya sea con una request que sea post o get), verificamos si es una url segura
            # con is_safe_url, y redireccionamos, al valor que llegó a través de next y que después pasamos a redirect_path
            return redirect_path # en este caso, esta opción se emplea para redirigir al usuario si viene de la página de checkout, en cuyo caso, lo redirigimos
            # de nuevo a la página de checkout (para que no tenga que volver a dicha página). Es a la página de checkout, porque así se define
            # en carts/checkout.html (así se define en checkout.html, que pasa la información snippets/form.html, que es quien realmente
            # crea el atributo next en la request)
        return self.default_next # este caso gestiona cuando el usuario se logea a través de la página de login y no de la de checkout
        # en este caso, desde login.html, no se pasa ninguna información al formulario para crear el atributo next en la request
        # por lo tanto, no se crea la safe_url, y se redirecciona al usuario a home
