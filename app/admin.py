from django.contrib import admin

# Register your models here.
from app.models import Customer, Category, Item, Phone, Repair, CategoryItemPhoneRepair, Token

admin.site.register(Customer)
admin.site.register(Phone)
admin.site.register(Item)
admin.site.register(Category)
admin.site.register(CategoryItemPhoneRepair)
admin.site.register(Repair)
admin.site.register(Token)
