from django.contrib.auth.models import User
from django.db import models

# Create your models here.


class Token(models.Model):
    token = models.CharField(max_length=50, blank=False,null=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}  : ({self.token})"


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


class Item(models.Model):
    sn = models.CharField(max_length=4, null=False, unique=True)
    date_buy = models.DateField(auto_now_add=True)
    is_available = models.BooleanField(default=True)
    buy_price = models.FloatField(default=0.0)

    def __str__(self):
        return f"{self.sn}"


class Category(models.Model):
    category = models.CharField(max_length=12, null=False, unique=True)
    detail = models.TextField(default=None)
    others = models.ManyToManyField('self', blank=True)
    threhold = models.IntegerField(default=2)

    def __str__(self):
        return f"{self.category} : {self.detail}"


class Repair(models.Model):
    customer = models.ForeignKey(Customer, blank=False, null=False, on_delete=models.DO_NOTHING)
    date_add = models.DateField(auto_now_add=True, blank=False)
    date_repaired = models.DateField(blank=True)
    date_paid = models.DateField(blank=True)

    def __str__(self):
        return f"{self.id} : {self.customer.famillyname} {self.customer.firstname}"


class CategoryItemPhoneRepair(models.Model):
    item = models.ForeignKey(Item, blank=False, null=False, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, blank=False, null=False, on_delete=models.CASCADE)
    phone = models.ForeignKey(Phone, blank=False, null=False, on_delete=models.CASCADE)
    repair = models.ForeignKey(Repair, blank=True, null=True, on_delete=models.CASCADE)