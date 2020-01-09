import json
import os
import uuid
from datetime import datetime
from io import StringIO
from pprint import pprint

import PIL
import pyinvoice
from barcode.writer import ImageWriter
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.http import JsonResponse, HttpResponse

# Create your views here.
from django.shortcuts import render
from django.template.loader import get_template
from django.utils.decorators import method_decorator
from django.views import generic
from django.views.decorators.csrf import csrf_exempt
from pyinvoice.models import InvoiceInfo, ServiceProviderInfo, Transaction, ClientInfo
from pyinvoice.templates import SimpleInvoice
from reportlab.graphics import shapes, barcode

from app.models import Customer, CategoryItemPhoneRepair, Token, TokenManager, Category, Phone, Item, Address, \
    PhoneNumber, Repair, RepairState, Invoice, PaymentMethod, RepairPayment, Photos
import labels
from reportlab.lib import colors
import barcode

from app.venv import GenericFunctions


def make_pdf(empty, data):
    # Create an A4 portrait (210mm x 297mm) sheet with 2 columns and 8 rows of
    # labels. Each label is 90mm x 25mm with a 2mm rounded corner. The margins are
    # automatically calculated.
    specs = labels.Specification(210, 297, 2, 8, 100, 35, corner_radius=0,
                                 left_padding=5, top_padding=5, bottom_padding=5, right_padding=5,
                                 padding_radius=0, top_margin=8, bottom_margin=9, right_margin=5, left_margin=5)

    def draw_label(label, width, height, dt):
        # Write the title.
        sn = dt["sn"]
        cat = "Cat : " + dt["cat"]
        date = "Date d'achat : " + dt["date"]
        snx = "Sn : " + sn
        label.add(shapes.String(0, height - 12, snx, fontName="Helvetica", fontSize=15))
        label.add(shapes.String(0 / 4.0, height - 27, cat, fontName="Helvetica", fontSize=15))
        label.add(shapes.String(0 / 4.0, height - 43, date, fontName="Helvetica", fontSize=15))
        EAN = barcode.get_barcode_class('code128')
        ean = EAN(sn, writer=ImageWriter())
        name = ean.save(dt["sn"])

        label.add(shapes.Image(0, -10, width, 35, name))

    sheet = labels.Sheet(specs, draw_label, border=True)
    sheet.partial_page(1, (
        (1, 1), (1, 2), (2, 1), (2, 2), (3, 1), (3, 2), (4, 1), (4, 2), (5, 1), (5, 2), (6, 1), (6, 2), (7, 1),
        (7, 2), (8, 2)))
    for each in data:
        sheet.add_label(each)
    # sheet.add_label("Oversized label here")
    sheet.save('app/static/labels.pdf')


@method_decorator(csrf_exempt, name='dispatch')
class LogInView(generic.View):  # Login View : WORKING
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        result = json.loads(request.body.decode('utf8'))
        data = {'token': result['token']}
        user = authenticate(username=result['username'], password=result['password'])
        if user is not None:
            user = User.objects.get(username=result['username'])
            Token.objects.update_or_create(
                user=user,
                defaults={'token': result['token']},
            )
            # Token.objects.update(token=result['token'], user=user)
            data['success'] = "true"
            dt = {"firstname": user.first_name, "famillyname": user.last_name, "id": user.id, "mail": user.email}
        else:
            data['success'] = "false"
            dt = {"firstname": None, "famillyname": None, "id": None, "mail": None}
        data['data'] = {'user': [dt]}
        rt = JsonResponse(data, safe=False)
        return rt


@method_decorator(csrf_exempt, name='dispatch')
class SearchView(generic.View):  # Search View
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        result = json.loads(request.body.decode('utf8'))
        data = {'token': result['token']}
        users = []
        total = 0
        if TokenManager.IsAdmin(result['username'], result['token']):
            data['success'] = "true"
            if result['action'] == 0:  # Search by mail
                for customer in Customer.objects.filter(mail__icontains=result['field']).order_by('cp', 'famillyname',
                                                                                                  'firstname'):
                    user = {"firstname": customer.firstname, "famillyname": customer.famillyname, "id": customer.id,
                            "mail": customer.mail, "cp": customer.cp}
                    users.append(user)

            elif result['action'] == 1:  # Search by firstname and famillyname
                for customer in Customer.objects.filter(firstname__icontains=result['firstname'],
                                                        famillyname__icontains=result['famillyname'],
                                                        cp__contains=result['cp']).order_by('cp',
                                                                                            'famillyname',
                                                                                            'firstname'):
                    user = {"firstname": customer.firstname, "famillyname": customer.famillyname, "id": customer.id,
                            "mail": customer.mail, "cp": customer.cp}
                    users.append(user)
            elif result['action'] == 2:  # Search by Order No : WORKING BUT JSON NOT RIGHT
                dt = {}
                repairs = []
                for repair in CategoryItemPhoneRepair.objects.filter(repair_id=result['field']):
                    dt['user'] = {"firstname": repair.repair.customer.firstname,
                                  "famillyname": repair.repair.customer.famillyname,
                                  "customerid": repair.repair.customer.id,
                                  "customermail": repair.repair.customer.mail,
                                  "customercp": repair.repair.customer.cp}
                    try:
                        other = repair.category.others.get().category
                    except repair.category.DoesNotExist:
                        cat_other = ""
                    else:
                        cat_other = other
                    # override prices
                    if repair.custom_price == 0:
                        price = repair.category.normal_price
                    else:
                        price = repair.custom_price
                    repair = {"sn": repair.item.sn,
                              'cat': repair.category.category,
                              'req': cat_other,
                              'price': price}
                    repairs.append(repair)
                    total = price + total
                users.append(dt)
                data['finalprice'] = total
                users.append(repairs)
            elif result['action'] == 3:  # get all customers
                for customer in Customer.objects.all().order_by('cp', 'famillyname', 'firstname'):
                    user = {"firstname": customer.firstname, "famillyname": customer.famillyname, "id": customer.id,
                            "mail": customer.mail, "cp": customer.cp}
                    users.append(user)
            elif result['action'] == 4:  # get by id
                for customer in Customer.objects.filter(id=result['id']).order_by('cp', 'famillyname', 'firstname'):
                    user = {"firstname": customer.firstname, "famillyname": customer.famillyname, "id": customer.id,
                            "mail": customer.mail, "cp": customer.cp}
                    users.append(user)
        else:
            data['success'] = "false"

        data['data'] = {'user': users, "mode": result['action']}
        rt = JsonResponse(data, safe=False)
        return rt


@method_decorator(csrf_exempt, name='dispatch')
class AddStockView(generic.View):  # Search View
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        print(str(uuid.uuid4())[:8])
        result = json.loads(request.body.decode('utf8'))
        data = {'token': result['token']}
        users = []
        if TokenManager.IsAdmin(result['username'], result['token']):
            # Customer.objects.create(firstname='jacques', famillyname='rené')
            cat = Category.objects.get(category=result['category'])
            item = Item.objects.create(buy_sn=result['buy_sn'], sn=str(uuid.uuid4())[:8],
                                       buy_price=float(result['buyprice'].replace(',', '.')))
            CategoryItemPhoneRepair.objects.create(item=item, phone=cat.phone, category=cat)
            data['success'] = "true"
        else:
            data['success'] = "false"
        rt = JsonResponse(data, safe=False)
        return rt


@method_decorator(csrf_exempt, name='dispatch')
class AddCategoryView(generic.View):  # Search View
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        result = json.loads(request.body.decode('utf8'))
        data = {'token': result['token']}
        if TokenManager.IsAdmin(result['username'], result['token']):
            if result['other'] == "None":
                other = None
            else:
                other = Category.objects.get(category=result['other'])
            photo = Photos.objects.get(id=result['photo'])
            phone = Phone.objects.get(id=result['phone'])
            try:
                item = Category.objects.create(category=result['name'], detail=result['caption'],
                                               threhold=result['seuil'], normal_price=result['price'], photo=photo,
                                               phone=phone, is_on_invoice=result['ioi'], others=other)
                data['success'] = "true"
                data['data'] = "Bien ajoutée : " + result['name'] + ", au prix de " + result['price'] + "€ HT (" + str(
                    float(result['price']) * 1.2) + "€ TTC)"
            except IntegrityError:
                data['success'] = "false"
                data['data'] = "La catégory existe deja, verifier la base de donée."
        else:
            data['success'] = "false"
        rt = JsonResponse(data, safe=False)
        return rt


@method_decorator(csrf_exempt, name='dispatch')
class AddPhoneView(generic.View):  # Search View
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        result = json.loads(request.body.decode('utf8'))
        data = {'token': result['token']}
        if TokenManager.IsAdmin(result['username'], result['token']):
            try:
                Phone.objects.create(model=result['model'], detail=result['caption'])
                data['success'] = "true"
            except IntegrityError:
                data['success'] = "false"
        else:
            data['success'] = "false"
        rt = JsonResponse(data, safe=False)
        return rt


@method_decorator(csrf_exempt, name='dispatch')
class AddressesByCustomerView(generic.View):
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        result = json.loads(request.body.decode('utf8'))
        data = {'token': result['token']}
        users = []
        if TokenManager.IsAdmin(result['username'], result['token']):
            for address in Address.objects.filter(customer_id=result['customerid']):
                user = {"no": address.no, "street": address.street, "city": address.city,
                        "cp": address.cp, "country": address.country, 'label': address.label}
                users.append(user)
            data['success'] = "true"
            data['addresses'] = users
        else:
            data['success'] = "false"
        rt = JsonResponse(data, safe=False)
        return rt


@method_decorator(csrf_exempt, name='dispatch')
class RepairByCustomerView(generic.View):
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        result = json.loads(request.body.decode('utf8'))
        data = {'token': result['token']}
        items = {}
        total = 0
        print(result['username'], result['token'])
        if TokenManager.IsAdmin(result['username'], result['token']):
            for repair in CategoryItemPhoneRepair.objects.filter(repair__customer_id=result['customerid']):
                print(repair)
                print("_______")
                try:
                    other = {'cat': repair.category.others.get().category,
                             'photo': repair.category.others.get().photo.file}
                except repair.category.DoesNotExist:
                    cat_other = {'none': 'none'}
                else:
                    cat_other = other
                # override prices
                if repair.custom_price == 0:
                    price = repair.category.normal_price
                else:
                    price = repair.custom_price
                dt = {"sn": repair.item.sn,
                      'cat': repair.category.category,
                      'req': cat_other,
                      'price': price,
                      'photo': repair.category.photo.file}

                items[repair.repair.id] = dt
                total = price + total

            data['success'] = "true"
            data['cart_content'] = items

        else:
            data['success'] = "no adm"
        rt = JsonResponse(data, safe=False)
        return rt


@method_decorator(csrf_exempt, name='dispatch')
class GetAllStockView(generic.View):
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        result = json.loads(request.body.decode('utf8'))
        data = {'token': result['token']}
        items = {}
        total = 0
        print(result['username'], result['token'])
        if TokenManager.IsAdmin(result['username'], result['token']):
            for c in Category.objects.all():
                cc = CategoryItemPhoneRepair.objects.filter(repair=None, category=c)
                item = []
                if cc.count() != 0:
                    for i in cc:
                        repair = {"sn": i.item.sn,
                                  'cat': i.category.category,
                                  'req': "cat_other",
                                  'price': "price",
                                  'photo': i.category.photo.file}
                        item.append(repair)

                else:
                    item = [{"sn": "none",
                             'cat': "none",
                             'req': "none",
                             'price': "none",
                             'photo': "none"}]
                items[c.category] = item

            data['success'] = "true"
            data['stock'] = items

        else:
            data['success'] = "no adm"
        rt = JsonResponse(data, safe=False)
        return rt


@method_decorator(csrf_exempt, name='dispatch')
class GetItemFromCatInStock(generic.View):
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        result = json.loads(request.body.decode('utf8'))
        data = {'token': result['token']}
        items = {}
        total = 0
        print(result['username'], result['token'])
        if TokenManager.IsAdmin(result['username'], result['token']):
            for c in Category.objects.filter(category=result['cat']):
                cc = CategoryItemPhoneRepair.objects.filter(repair=None, category=c)
                item = []
                if cc.count() != 0:
                    for i in cc:
                        if i.category.others is None:
                            repair = {"sn": i.item.sn,
                                      'cat': i.category.category,
                                      'req': "none",
                                      'price': "price",
                                      'photo': i.category.photo.file}
                        else:
                            repair = {"sn": i.item.sn,
                                      'cat': i.category.category,
                                      'req': i.category.others.category,
                                      'price': "price",
                                      'photo': i.category.photo.file}
                        item.append(repair)

                else:
                    item = [{"sn": "none",
                             'cat': "none",
                             'req': "none",
                             'price': "none",
                             'photo': "none"}]
                items[c.category] = item

            data['success'] = "true"
            data['stock'] = item

        else:
            data['success'] = "no adm"
        rt = JsonResponse(data, safe=False)
        return rt


@method_decorator(csrf_exempt, name='dispatch')
class GetItemFromRepair(generic.View):
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        result = json.loads(request.body.decode('utf8'))
        data = {'token': result['token']}
        items = {}
        total = 0
        print(result['username'], result['token'])
        if TokenManager.IsAdmin(result['username'], result['token']):
            cc = CategoryItemPhoneRepair.objects.filter(repair_id=result['repair_id'])
            item = []
            if cc.count() != 0:
                for i in cc:
                    if i.category.others is None:
                        repair = {"sn": i.item.sn,
                                  'cat': i.category.category,
                                  'req': "none",
                                  'price': "price",
                                  'photo': i.category.photo.file}
                    else:
                        repair = {"sn": i.item.sn,
                                  'cat': i.category.category,
                                  'req': i.category.others.category,
                                  'price': "price",
                                  'photo': i.category.photo.file}
                    item.append(repair)

            else:
                item = [{"sn": "none",
                         'cat': "none",
                         'req': "none",
                         'price': "none",
                         'photo': "none"}]

            data['success'] = "true"
            data['items'] = item

        else:
            data['success'] = "no adm"
        rt = JsonResponse(data, safe=False)
        return rt


@method_decorator(csrf_exempt, name='dispatch')
class GetInfoFromRepair(generic.View):
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        result = json.loads(request.body.decode('utf8'))
        data = {'token': result['token']}
        repair = {}
        print(result['username'], result['token'])
        if TokenManager.IsAdmin(result['username'], result['token']):

            try:
                r = Repair.objects.get(id=result['repair_id'])
                repair = {'id': r.id,
                          'status': r.status.state}
            except Repair.DoesNotExist:
                repair = {"id": "none",
                          'status': "none"}

            data['success'] = "true"
            data['repair'] = repair

        else:
            data['success'] = "no adm"
        rt = JsonResponse(data, safe=False)
        return rt


@method_decorator(csrf_exempt, name='dispatch')
class GetPaymentFromRepair(generic.View):
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        result = json.loads(request.body.decode('utf8'))
        data = {'token': result['token']}
        items = {}
        total = 0
        print(result['username'], result['token'])
        if TokenManager.IsAdmin(result['username'], result['token']):
            cc = RepairPayment.objects.filter(repair_id=result['repair_id'])
            payments = []
            if cc.count() != 0:
                for i in cc:
                    payment = {"pid": i.id_payment,
                               'payment_date': i.date_paid,
                               'amount': i.amount,
                               'method': i.method.method}
                    payments.append(payment)

            else:
                payments = [{"pid": "none",
                             'payment_date': "none",
                             'amount': "none",
                             'method': "none"}]

            data['success'] = "true"
            data['payments'] = payments

        else:
            data['success'] = "no adm"
        rt = JsonResponse(data, safe=False)
        return rt


@method_decorator(csrf_exempt, name='dispatch')
class GetAllUserInfos(generic.View):
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        result = json.loads(request.body.decode('utf8'))
        data = {'token': result['token']}
        user = {}
        total = 0
        print(result['username'], result['token'])
        if TokenManager.IsAdmin(result['username'], result['token']):
            for u in Customer.objects.filter(id=result['user_id']).values():

                # pprint(u)
                for k, v in u.items():
                    user[k] = v
            data['user'] = user
            data['success'] = "true"

        else:
            data['success'] = "no adm"
        rt = JsonResponse(data, safe=False)
        return rt


@method_decorator(csrf_exempt, name='dispatch')
class LinkItemToRepair(generic.View):
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        result = json.loads(request.body.decode('utf8'))
        data = {'token': result['token']}
        total = 0
        print(result['username'], result['token'])
        if TokenManager.IsAdmin(result['username'], result['token']):
            repair = Repair.objects.get(id=result['repair_id'])
            print(result['item_sn'])
            item = Item.objects.get(sn=result['item_sn'].lower())
            print(repair.id)
            print(item.sn)
            try:
                CategoryItemPhoneRepair.objects.filter(item=item).update(repair=repair)
                data['success'] = "true"
            except:
                data['success'] = 'False'



        else:
            data['success'] = "no adm"
        rt = JsonResponse(data, safe=False)
        return rt


@method_decorator(csrf_exempt, name='dispatch')
class GetAllUserRepairs(generic.View):
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        result = json.loads(request.body.decode('utf8'))
        data = {'token': result['token']}
        repairs = []
        print(result['username'], result['token'])
        if TokenManager.IsAdmin(result['username'], result['token']):
            for r in Repair.objects.filter(customer_id=result['user_id']).values():
                repair = {}
                pprint(r)
                for k, v in r.items():
                    repair[k] = v
                repairs.append(repair)
            data['repairs'] = repairs
            data['success'] = "true"

        else:
            data['success'] = "no adm"
        rt = JsonResponse(data, safe=False)
        return rt


class GetLabels(generic.View):
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        # print(request.GET["test"])
        # make_pdf("", [{"sn": "987654345678", "cat": "MLJGHJK", "date": "12/12/12"},{"sn": "45678765456", "cat": "LKJHGYUIKN", "date": "12/4567/12"}])
        return render(request, "test.html")


@method_decorator(csrf_exempt, name='dispatch')
class AddItem(generic.View):
    http_method_names = ['get', 'post']

    def get(self, request, *args, **kwargs):
        # print(request.GET["test"])
        # make_pdf("", [{"sn": "987654345678", "cat": "MLJGHJK", "date": "12/12/12"},{"sn": "45678765456", "cat": "LKJHGYUIKN", "date": "12/4567/12"}])
        return render(request, "additemform.html")

    def post(self, request, *args, **kwargs):
        raw = request.body.decode('utf8')
        results = raw.split("&")
        full = {}
        for result in results:
            each = result.split("=")
            full[each[0]] = each[1]
        print(full['t'])
        if full['t'] != "" and full['t'] != "":
            print("test")


@method_decorator(csrf_exempt, name='dispatch')
class GetSpecificCat(generic.View):  # Search View
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        cat = []
        result = json.loads(request.body.decode('utf8'))
        for c in Category.objects.filter(category__contains=result['cat']).order_by('category'):
            if c.others is not None:
                cat.append({'id': c.id,
                            'photo': c.photo.file,
                            'detail': c.detail,
                            'cat': c.category,
                            'ioi': c.is_on_invoice,
                            'other': {'id': c.others.id,
                                      'photo': c.others.photo.file,
                                      'detail': c.others.detail,
                                      'cat': c.others.category,
                                      'ioi': c.others.is_on_invoice}
                            })
            else:
                cat.append({'id': c.id,
                            'photo': c.photo.file,
                            'detail': c.detail,
                            'cat': c.category,
                            'ioi': c.is_on_invoice,
                            'other': {'id': None,
                                      'photo': None,
                                      'detail': None,
                                      'cat': None,
                                      'ioi': None}
                            })
        return JsonResponse(cat, safe=False)


@method_decorator(csrf_exempt, name='dispatch')
class GetAllCat(generic.View):  # Search View
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        cat = []
        for c in Category.objects.all().order_by('category'):
            if c.others is not None:
                cat.append({'id': c.id,
                            'photo': c.photo.file,
                            'detail': c.detail,
                            'cat': c.category,
                            'ioi': c.is_on_invoice,
                            'other': {'id': c.others.id,
                                      'photo': c.others.photo.file,
                                      'detail': c.others.detail,
                                      'cat': c.others.category,
                                      'ioi': c.others.is_on_invoice}
                            })
            else:
                cat.append({'id': c.id,
                            'photo': c.photo.file,
                            'detail': c.detail,
                            'cat': c.category,
                            'ioi': c.is_on_invoice,
                            'other': {'id': None,
                                      'photo': None,
                                      'detail': None,
                                      'cat': None,
                                      'ioi': None}
                            })
        return JsonResponse(cat, safe=False)


@method_decorator(csrf_exempt, name='dispatch')
class GetAllPhoneModel(generic.View):  # Search View
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        cat = []
        for p in Phone.objects.all().order_by('detail'):
            cat.append({'id': p.id,
                        'name': p.detail,
                        'model': p.model})
        return JsonResponse(cat, safe=False)


@method_decorator(csrf_exempt, name='dispatch')
class GetAllPaymentMethod(generic.View):  # Search View
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        cat = []
        for p in PaymentMethod.objects.all().order_by('method'):
            cat.append({'id': p.id,
                        'sm': p.short_method,
                        'method': p.method})
        return JsonResponse(cat, safe=False)


@method_decorator(csrf_exempt, name='dispatch')
class GenerateInvoice(generic.View):  # Search View
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        result = json.loads(request.body.decode('utf8'))
        data = {'token': result['token']}
        GenericFunctions.InvoiceMaker(repair_id=result['repair_id'], customer_id=result['customer_id'])
        return JsonResponse({'success': "true"}, safe=False)


@method_decorator(csrf_exempt, name='dispatch')
class EditPaymentStatus(generic.View):  # Search View
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        result = json.loads(request.body.decode('utf8'))
        data = {'token': result['token']}
        GenericFunctions.editPaymentStatus(repair_id=result['repair_id'], customer_id=result['customer_id'])
        return JsonResponse({'success': "true"}, safe=False)


@method_decorator(csrf_exempt, name='dispatch')
class Pay(generic.View):  # Pay a repair
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        result = json.loads(request.body.decode('utf8'))
        data = {'token': result['token']}
        items = {}
        total = 0
        print(result['username'], result['token'])
        if TokenManager.IsAdmin(result['username'], result['token']):
            repair = Repair.objects.get(id=result['repair_id'])
            if repair.status.short_state != "Q":
                for pm in result['payment_method']:
                    if pm['amount'] != '0':
                        method = PaymentMethod.objects.get(short_method=pm['sm'])

                        payment = RepairPayment.objects.create(method=method, repair=repair, amount=pm['amount'],
                                                               id_payment=str(uuid.uuid4())[:8],
                                                               date_paid=datetime.now())
                GenericFunctions.editPaymentStatus(repair_id=repair.id, customer_id=repair.customer.id)
                GenericFunctions.InvoiceMaker(repair_id=repair.id, customer_id=repair.customer.id)
                data['msg'] = "done"
            else:
                data['msg'] = "Still in quoattion modify repair type"
            data['success'] = "true"


        else:
            data['success'] = "no adm"
        rt = JsonResponse(data, safe=False)
        return rt
