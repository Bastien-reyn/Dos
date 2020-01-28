from django.contrib import admin

# Register your models here.
from app.models import Customer, Category, Item, Phone, Repair, CategoryItemPhoneRepair, Token, Address, Photos, \
    RepairPayment, RepairPhoto, PaymentMethod, RepairState, PhoneNumber, Invoice, Promo, Quotation, QuotationDetail, \
    FrenchAddress, Labels

admin.site.register(Customer)
admin.site.register(Phone)
admin.site.register(Item)
admin.site.register(Category)
admin.site.register(CategoryItemPhoneRepair)
admin.site.register(Repair)
admin.site.register(Token)
admin.site.register(Address)
admin.site.register(Photos)
admin.site.register(RepairPayment)
admin.site.register(RepairPhoto)
admin.site.register(PaymentMethod)
admin.site.register(RepairState)
admin.site.register(PhoneNumber)
admin.site.register(Invoice)
admin.site.register(Promo)
admin.site.register(Quotation)
admin.site.register(QuotationDetail)
admin.site.register(FrenchAddress)
admin.site.register(Labels)
