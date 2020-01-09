import uuid

from django.contrib.auth.models import User
from django.db import models

# Create your models here.
from django.db.models.functions import datetime


class Token(models.Model):
    token = models.CharField(max_length=50, blank=False,null=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}  : ({self.token})"

class Photos(models.Model):
    file = models.CharField(default="default.png",max_length=100, blank=False, null=False)

class TokenManager(models.Model):
    @staticmethod
    def IsAdmin(username, token):
        try:
            Token.objects.get(user__username=username, token=token)
        except Token.DoesNotExist:
            return False
        else:
            return True


class Customer(models.Model):
    firstname = models.CharField(max_length=40, null=False)
    famillyname = models.CharField(max_length=40, null=False)
    admin = models.OneToOneField(User, on_delete=models.CASCADE, blank=True, null=True)
    mail = models.EmailField(blank=False)
    cp = models.CharField(max_length=5, blank=False)
    date_signup = models.DateField(auto_now_add=True, blank=False)

    def __str__(self):
        return f"{self.firstname} {self.famillyname} ({self.cp})"


class Phone(models.Model):
    model = models.CharField(max_length=40, null=False, unique=True)
    detail = models.TextField(default=None)

    def __str__(self):
        return f"{self.model}"


class Address(models.Model):
    no = models.CharField(max_length=10, null=False)
    street = models.CharField(max_length=255, null=False)
    city = models.CharField(max_length=50, null=False)
    state = models.CharField(max_length=50, null=True, blank=True)
    cp = models.CharField(max_length=5, null=False)
    country = models.CharField(max_length=20, null=False, default="France")
    customer = models.ForeignKey(Customer, blank=False,null=False, on_delete=models.CASCADE)
    def full(self):
        return  f"{self.no} {self.street}, {self.cp} {self.city}"

    def __str__(self):
        return f"{self.customer.firstname} {self.customer.famillyname} : {self.no} {self.street} {self.cp} {self.city}"


class Item(models.Model):
    sn = models.CharField(max_length=8, null=False, unique=True)
    date_buy = models.DateField(auto_now_add=True)
    is_available = models.BooleanField(default=True)
    buy_price = models.FloatField(default=0.0)
    buy_sn = models.CharField(max_length=8, null=True)


    def __str__(self):
        return f"{self.sn}"


class Category(models.Model):
    category = models.CharField(max_length=12, null=False, unique=True)
    detail = models.TextField(default=None)
    others = models.ForeignKey('self', related_name='oth',related_query_name="oth", blank=True, null=True, on_delete=models.CASCADE)
    threhold = models.IntegerField(default=2)
    normal_price = models.FloatField(blank=False, null=False)
    photo = models.ForeignKey(Photos, null=False, blank=False, on_delete=models.DO_NOTHING)
    phone = models.ForeignKey(Phone, blank=False, null=False, on_delete=models.CASCADE)
    is_on_invoice = models.BooleanField()

    def __str__(self):
        if self.others is None:
            return f"{self.category} : {self.detail} | None "
        else:
            return f"{self.category} : {self.detail} | {self.others.category} "



class PhoneNumber(models.Model):
    no_phone = models.CharField(max_length=20, null=False)
    customer = models.ForeignKey(Customer, blank=False, null=False, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.customer.firstname} : {self.no_phone}"


class RepairState(models.Model):
    state = models.CharField(max_length=30, null=False)
    short_state = models.CharField(max_length=5, null=False)

    def __str__(self):
        return f"{self.state}"


class PaymentMethod(models.Model):
    method = models.CharField(max_length=30, null=False)
    short_method = models.CharField(max_length=5, null=False)

    def __str__(self):
        return f"{self.method}"


class Repair(models.Model):
    customer = models.ForeignKey(Customer, blank=False, null=False, on_delete=models.DO_NOTHING)
    date_add = models.DateField(auto_now_add=True, blank=False)
    date_repaired = models.DateField(blank=True)
    phone_password = models.CharField(max_length=20, blank=True, null=True)
    status = models.ForeignKey(RepairState, blank=False, null=False, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.id} : {self.customer.famillyname} {self.customer.firstname} {self.status.state}"


class RepairPayment(models.Model):
    method = models.ForeignKey(PaymentMethod, blank=False, null=False, on_delete=models.CASCADE)
    repair = models.ForeignKey(Repair, blank=False, null=False, on_delete=models.CASCADE)
    amount = models.CharField(max_length=20, null=False)
    date_paid = models.DateField(blank=True, null=False)
    id_payment = models.CharField(max_length=8, null=False, unique=True)  # UID

    def __str__(self):
        return f"{self.repair.id}"


class RepairPhoto(models.Model):
    photo = models.ForeignKey(Photos, blank=False, null=False, on_delete=models.CASCADE)
    repair = models.ForeignKey(Repair, blank=False, null=False, on_delete=models.CASCADE)
    caption = models.CharField(max_length=50, null=False)

    def __str__(self):
        return f"{self.repair.id}"


class Invoice(models.Model):
    period = models.CharField(max_length=6, default=datetime.datetime.now().year, blank=False, null=False)
    due = models.CharField(max_length=20, blank=False, null=False)
    repair = models.ForeignKey(Repair, blank=False, null=False, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.repair.id}"

class CategoryItemPhoneRepair(models.Model):
    item = models.OneToOneField(Item, blank=False, null=False, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, blank=False, null=False, on_delete=models.CASCADE)
    phone = models.ForeignKey(Phone, blank=False, null=False, on_delete=models.CASCADE)
    repair = models.ForeignKey(Repair, blank=True, null=True, on_delete=models.CASCADE)
    custom_price = models.FloatField(blank=True, default=0.0)

    def __str__(self):
        if self.repair != None:
            used = "used"
        else:
            used = "stock"
        return f"#{self.id} : SN:{self.item.sn} | Category:{self.category.category} | Phone: {self.phone.model} | {used}"
