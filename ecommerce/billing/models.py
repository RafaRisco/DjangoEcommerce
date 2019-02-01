from django.conf import settings
from django.db import models
from django.db.models.signals import post_save, pre_save
from django.urls import reverse

from accounts.models import GuestEmail
User = settings.AUTH_USER_MODEL

import stripe
STRIPE_SECRET_KEY = getattr(settings, "STRIPE_SECRET_KEY", "sk_test_7he6WFXWOAYrQ0JEyi8uRENZ")
stripe.api_key = STRIPE_SECRET_KEY

class BillingProfileManager(models.Manager):
    def new_or_get(self, request):
        user = request.user # tomamos el user que viene de la request
        guest_email_id = request.session.get('guest_email_id') # si existe dentro de request.session,
        # tomamos el mail_id del usuario invitado
        created = False
        obj = None
        if user.is_authenticated:
            if user.email:
                obj, created = self.model.objects.get_or_create(
                                                        user=user, email=user.email) # si el usuario (que tomamos antes
                # de request.user) está autenticado y tiene mail, creamos un BillingProfile, pasado como argumento el usuario
                # y su email. Si existe un BillingProfile para ese usuario y mail, accedemos a dicho BillingProfile
                # IMPORTANTE: en este caso, obj hace referencia al BillingProfile
        elif guest_email_id is not None: # si hay mail del usuario invitado (porque hay id de dicho mail, es decir, no es None)
            guest_email_obj = GuestEmail.objects.get(id=guest_email_id) # obtenemos el mail del usuario invitado con base en la id
            # del guest email, que obtuvimos antes de request.session. Obtenemos el mail del model GuestEmail, que es un model de la
            # app accounts
            obj, created  = self.model .objects.get_or_create(
                                                        email=guest_email_obj.email) # creamos un BillingProfile con el mail del
                                                                # usuario invitado
        else: # en este caso no hay usuario registrado (ni con mail) ni hay un mail de un usuario invitado
            pass
        return obj, created


# Create your models here.
class BillingProfile(models.Model): # este model tiene los perfiles de facturación
    user        = models.OneToOneField(User, null=True, blank=True, on_delete=models.CASCADE) # esto es similar a ForeignKey y a poner unique=True
    email       = models.EmailField()
    active      = models.BooleanField(default=True)
    update      = models.DateTimeField(auto_now=True)
    timestamp   = models.DateTimeField(auto_now_add=True)
    customer_id = models.CharField(max_length=120, null=True, blank=True)

    objects = BillingProfileManager()

    def __str__(self):
        return self.email

    def charge(self, order_obj, card=None):
        return Charge.objects.do(self, order_obj, card)

    def get_cards(self):
        return self.card_set.all()

    def get_payment_method_url(self):
        return reverse('billing-payment-method')

    @property
    def has_card(self):
        card_qs = self.get_cards()
        return card_qs.exists()

    @property
    def default_card(self):
        default_cards = self.get_cards().filter(active=True, default=True)
        if default_cards.exists():
            return default_cards.first()
        return None

    def set_cards_inactive(self):
        cards_qs = self.get_cards()
        cards_qs.update(active=False)
        return cards_qs.filter(active=True).count()

def billing_profile_created_receiver(sender, instance, *args, **kwargs):
    if not instance.customer_id and instance.email:
        print("ACTUAL API REQUEST Send to stripe/braintree")
        customer = stripe.Customer.create(
            email = instance.email
        )
        print(customer)
        instance.customer_id = customer.id
        print("hola")

pre_save.connect(billing_profile_created_receiver, sender=BillingProfile)

def user_created_receiver(sender, instance, created, *args, **kwargs): # esto es signals. Nos permite ejecutar una función determinada, antes o después
    # de que se guarde un model (puede ser este model, BillingProfile, u otro, como en este caso que es User, porque abajo así lo indica como sender)
    # en ese caso, cuando se crea un usuario, se crea un BillingProfile con ese usuario y el mail de ese usuario
    if created and instance.email: # en este caso, si hay un usuario creado y tienen un email, en este caso del model User, que es el sender
        BillingProfile.objects.get_or_create(user=instance, email=instance.email) # se crea o se obtiene el BillingProfile con ese usuario (instance) y ese Email
                                                                                # no hay que hacer save, porque esta función lo hace automáticamente
post_save.connect(user_created_receiver, sender=User) # aquí conectamos la función con el model, en este caso es user.

class CardManager(models.Manager):
    def all(self, *args, **kwargs):
        return self.get_queryset().filter(active=True)

    def add_new(self, billing_profile, token):
        if token:
            customer = stripe.Customer.retrieve(billing_profile.customer_id)
            stripe_card_response = customer.sources.create(source=token)
            new_card = self.model(
                    billing_profile=billing_profile,
                    stripe_id = stripe_card_response.id,
                    brand=stripe_card_response.brand,
                    country=stripe_card_response.country,
                    exp_month=stripe_card_response.exp_month,
                    exp_year=stripe_card_response.exp_year,
                    last4=stripe_card_response.last4
                )
            new_card.save()
            return new_card
        return None

class Card(models.Model):
    billing_profile     = models.ForeignKey(BillingProfile, on_delete=models.CASCADE)
    stripe_id           = models.CharField(max_length=120)
    brand               = models.CharField(max_length=120, null=True, blank=True)
    country             = models.CharField(max_length=20, null=True, blank=True)
    exp_month           = models.IntegerField(null=True, blank=True)
    exp_year            = models.IntegerField(null=True, blank=True)
    last4               = models.CharField(max_length=4, null=True, blank=True)
    default             = models.BooleanField(default=True)
    active              = models.BooleanField(default=True)
    timestamp           = models.DateTimeField(auto_now_add=True)

    objects = CardManager()

    def __str__(self):
        return "{} {}".format(self.brand, self.last4)

def new_card_post_save_receiver(sender, instance, created, *args, **kwargs):
    if instance.default:
        billing_profile = instance.billing_profile
        qs = Card.objects.filter(billing_profile=billing_profile).exclude(pk=instance.pk)
        qs.update(default=False)

post_save.connect(new_card_post_save_receiver, sender=Card)

class ChargeManager(models.Manager):
    def do(self, billing_profile, order_obj, card=None):
        card_obj = card
        if card_obj is None:
            cards = billing_profile.card_set.filter(default=True)
            if cards.exists():
                card_obj = cards.first()
        if card_obj is None:
            return False, "No cards Available"
        c = stripe.Charge.create(
                amount = int(order_obj.total * 100),
                currency = "usd",
                customer = billing_profile.customer_id,
                source = card_obj.stripe_id,
                metadata = {"order_id": order_obj.order_id},
            )
        new_charge_obj = self.model(
                billing_profile = billing_profile,
                stripe_id = c.id,
                paid = c.paid,
                refunded = c.refunded,
                outcome = c.outcome,
                outcome_type = c.outcome['type'],
                seller_message = c.outcome.get('seller_message'),
                risk_level = c.outcome.get('risk_level')
        )
        new_charge_obj.save()
        return new_charge_obj.paid, new_charge_obj.seller_message



class Charge(models.Model):
    billing_profile     = models.ForeignKey(BillingProfile, on_delete=models.CASCADE)
    stripe_id           = models.CharField(max_length=120)
    paid                = models.BooleanField(default=False)
    refunded            = models.BooleanField(default=False)
    outcome             = models.TextField(null=True, blank=True)
    outcome_type        = models.CharField(max_length=120, null=True, blank=True)
    seller_message      = models.CharField(max_length=120, null=True, blank=True)
    risk_level          = models.CharField(max_length=120, null=True, blank=True)

    objects = ChargeManager()
