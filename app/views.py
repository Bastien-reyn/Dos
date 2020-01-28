import csv
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
from django.core.files.storage import FileSystemStorage
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
    PhoneNumber, Repair, RepairState, Invoice, PaymentMethod, RepairPayment, Photos, Promo, Quotation, QuotationDetail, \
    FrenchAddress, Labels
import labels
from reportlab.lib import colors
import barcode

from app.venv import GenericFunctions
from app.venv.GenericFunctions import newClient, newPhone, newAddress, delPhone, delClient, getClientAddress, \
    newQuotation, addCatToQuotation


def make_pdf(empty, data, repairer):
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
        name = ean.save('app/static/barcode/'+dt["sn"])

        label.add(shapes.Image(0, -10, width, 35, name))

    sheet = labels.Sheet(specs, draw_label, border=True)
    for key, value in empty.items():
        sheet.partial_page(key, value)
    for each in data:
        sheet.add_label(each)
    # sheet.add_label("Oversized label here")
    sn = str(uuid.uuid4())[:8]
    sheet.save('app/static/labels/'+sn+'.pdf')
    Labels.objects.create(file_name=sn+'.pdf', repairer=repairer)
    return sn+'.pdf'



@method_decorator(csrf_exempt, name='dispatch')
class LogInView(generic.View):  # Login View : WORKING
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        result = json.loads(request.body.decode('utf8'))
        token = str(uuid.uuid4())
        data = {'token': token}
        user = authenticate(username=result['username'], password=result['password'])
        if user is not None:
            user = User.objects.get(username=result['username'])
            Token.objects.update_or_create(
                user=user,
                defaults={'token': token},
            )
            # Token.objects.update(token=result['token'], user=user)
            data['success'] = True
            dt = {"firstname": user.first_name, "famillyname": user.last_name, "id": user.id, "mail": user.email}
        else:
            data['success'] = False
            dt = {"firstname": None, "famillyname": None, "id": None, "mail": None}
        data['repairer_infos'] = dt
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
                    print(user)
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
            items = []
            for item in result['items']:
                sn = str(uuid.uuid4())[:8]
                #cat = Category.objects.get(category=item['cat'])
                #item_object = Item.objects.create(buy_sn=item['buy_sn'], sn=sn,
                #                                  buy_price=float(item['buy_price'].replace(',', '.')))
                #CategoryItemPhoneRepair.objects.create(item=item_object, category=cat)
                items.append({"sn": sn, "cat": item['cat'], "date": str(datetime.now().strftime("%d/%m/%Y"))})
            previous_empty = 1
            i = 0
            dt = []
            full = {}
            print(result['labels'])
            for empty in result['labels']:
                i += 1
                if previous_empty != int(empty['sheet']):
                    full[int(previous_empty)] = dt
                    dt = [[int(empty['x']), int(empty['y'])]]
                    previous_empty = int(empty['sheet'])
                elif int(i) == int(len(result['labels'])):
                    dt.append([int(empty['x']), int(empty['y'])])
                    full[int(previous_empty)] = dt
                    previous_empty = empty['sheet']
                else:
                    dt.append([int(empty['x']), int(empty['y'])])

            print(full)
            repairer = User.objects.get(username=result['username'])
            pdf_name = make_pdf(full, items, repairer)

            data['success'] = True
            data['msg'] = 'Le pdf a été généré, vous pouvez y acceder avec ce [lien](/label/'+pdf_name+') !'
        else:
            data['success'] = False
            data['msg'] = 'Reconnectez vous !'
        rt = JsonResponse(data, safe=False)
        return rt



@method_decorator(csrf_exempt, name='dispatch')
class AddOrUpdateCatalogEntryView(generic.View):  # Search View
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        result = json.loads(request.body.decode('utf8'))
        data = {'token': result['token']}
        if TokenManager.IsAdmin(result['username'], result['token']):
            try:
                if result['other'] != None:
                    other = Category.objects.get(id=result['other'])
                else:
                    other = None
                catalog_price = result['catalog_price']
                detail = result['detail']
                threshold = result['threshold']
                ioi = result['ioi']
                photo_id = result['photo_id']
                phone = Phone.objects.get(id=result['phone'])
                obj, created = Category.objects.update_or_create(
                    category=result['cat'],
                    defaults={'normal_price': catalog_price,
                              'detail': detail,
                              'threshold': threshold,
                              'others': other,
                              'phone': phone,
                              'is_on_invoice': ioi,
                              'photo_id': photo_id},
                )
                data['success'] = True

                if created is True:
                    data['msg'] = 'La référence a été crée'
                else:
                    data['msg'] = 'La référence a été modifiée'
            except Category.DoesNotExist:
                data['success'] = False
                data['msg'] = 'Erreur dans la REF catalogue pour "Other"'
            except Phone.DoesNotExist:
                data['success'] = False
                data['msg'] = 'Erreur dans l\'ID du téléphone'


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

        phone = {}
        total = 0
        print(result['username'], result['token'])
        if TokenManager.IsAdmin(result['username'], result['token']):
            for p in Phone.objects.all().order_by('detail'):
                items = {}
                for c in Category.objects.filter(phone=p).order_by('category'):

                    cc = CategoryItemPhoneRepair.objects.filter(repair=None, category=c)
                    item = []
                    if cc.count() != 0:
                        for i in cc:
                            repair = {"sn": i.item.sn,
                                      'cat': i.category.category,
                                      'req': "cat_other",
                                      'price': "price",
                                      'detail': i.category.detail,
                                      'photo': i.category.photo.file,
                                      'date_buy': i.item.date_buy}
                            item.append(repair)

                    else:
                        item = [{"sn": "none",
                                 'cat': "none",
                                 'req': "none",
                                 'price': "none",
                                 'photo': "none",
                                 'date_buy': None,
                                 'detail': None}]
                    items[c.category+' : '+c.detail.splitlines()[0]] = item
                phone[p.model]= items
            data['success'] = "true"
            data['stock'] = phone

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
                                      'price': i.category.normal_price,
                                      'photo': i.category.photo.file}
                        else:
                            repair = {"sn": i.item.sn,
                                      'cat': i.category.category,
                                      'req': i.category.others.category,
                                      'price': i.category.normal_price,
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
                                  'price': i.item.sell_price,
                                  'photo': i.category.photo.file,
                                  'coef': i.item.sell_promo.coef}
                    else:
                        repair = {"sn": i.item.sn,
                                  'cat': i.category.category,
                                  'req': i.category.others.category,
                                  'price': i.item.sell_price,
                                  'photo': i.category.photo.file,
                                  'coef': i.item.sell_promo.coef}
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
class GetQuotationDetailView(generic.View):
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        result = json.loads(request.body.decode('utf8'))
        data = {'token': result['token']}
        items = {}
        total = 0
        if TokenManager.IsAdmin(result['username'], result['token']):
            qd = QuotationDetail.objects.filter(quotation_id=result['quotation_id'])
            item = []
            if qd.count() != 0:
                for i in qd:
                    repair = {'cat': i.category.category,

                              'sell_price': i.sell_price,
                              'catalog_price': i.category.normal_price,
                              'photo': i.category.photo.file,
                              'coef': i.sell_promo.coef}
                    item.append(repair)

            else:
                item = [{"sn": "none",
                         'cat': "none",
                         'req': "none",
                         'price': "none",
                         'photo': "none"}]

            data['success'] = "true"
            data['catalog_items'] = item

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
            c = Customer.objects.filter(id=result['user_id'])
            for u in c.values():

                # pprint(u)
                for k, v in u.items():
                    user[k] = v
            try:
                address = getClientAddress(c[0].id)
                user['address'] = {'id':address.id,
                                   'no':address.no,
                                   'street':address.street,
                                   'city':address.city,
                                   'cp':address.cp,
                                   'country': address.country}
            except:
                user['address'] = "No address"
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
            item = Item.objects.get(sn=result['item_sn'].lower())

            CategoryItemPhoneRepair.objects.filter(item=item).update(repair=repair)
            promo = Promo.objects.get(id=result['promo_id'])
            item.sell_price = result['final_price']
            item.sell_promo = promo
            item.save()
            data['success'] = "true"
        else:
            data['success'] = "no adm"
        rt = JsonResponse(data, safe=False)
        return rt


@method_decorator(csrf_exempt, name='dispatch')
class UnLinkItemToRepair(generic.View):
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        result = json.loads(request.body.decode('utf8'))
        data = {'token': result['token']}
        total = 0
        print(result['username'], result['token'])
        if TokenManager.IsAdmin(result['username'], result['token']):

            try:
                item = Item.objects.get(sn=result['item_sn'].lower())
                item.sell_price = 0
                item.sell_promo = Promo.objects.get(tag="NP")
                item.save()
                CIPR = CategoryItemPhoneRepair.objects.get(item=item)
                CIPR.repair = None
                CIPR.save()
                data['success'] = "true"
            except:
                data['success'] = 'false'
                data['msg'] = 'Erreur de suppression ...'



        else:
            data['success'] = 'false'
            data['msg'] = 'Reconnection necessaire !'
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
                    if k == 'status_id':
                        repair['status'] = RepairState.objects.get(id=v).state
                    elif k == 'repairer_id':
                        usr = User.objects.get(id=v)
                        repair['repairer'] = usr.first_name + " " + usr.last_name
                    else:
                        repair[k] = v
                repairs.append(repair)
            data['repairs'] = repairs
            data['success'] = "true"

        else:
            data['success'] = "no adm"
        rt = JsonResponse(data, safe=False)
        return rt


@method_decorator(csrf_exempt, name='dispatch')
class GetQuotationListByUser(generic.View):
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        result = json.loads(request.body.decode('utf8'))
        data = {'token': result['token']}
        repairs = []
        print(result['username'], result['token'])
        if TokenManager.IsAdmin(result['username'], result['token']):
            for q in Quotation.objects.filter(customer_id=result['client_id']):
                repair = {}
                repair['id'] = q.id
                repair['date_add'] = q.date_add
                repair['date_accepted'] = q.date_accepted
                repair['repairer'] = {'id':q.repairer.id, 'last_name':q.repairer.last_name ,'familly_name': q.repairer.first_name}
                if q.repair is not None:
                    repair['repair_id'] = q.repair.id
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
        make_pdf([[1,1],[1,2]], [{"sn": "987654345678", "cat": "MLJGHJK", "date": "12/12/12"},{"sn": "45678765456", "cat": "LKJHGYUIKN", "date": "12/4567/12"}])
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
                            'catalog_price': c.normal_price,
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
                            'catalog_price': c.normal_price,
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
        data = {'success': True}
        phone = {}
        for p in Phone.objects.all().order_by('detail'):
            cat = []
            for c in Category.objects.filter(phone=p).order_by('category'):
                if c.others is not None:
                    cat.append({'id': c.id,
                                'photo': {
                                    'file': c.photo.file,
                                    'id': c.photo.id
                                },
                                'detail': c.detail,
                                'cat': c.category,
                                'ioi': c.is_on_invoice,
                                'catalog_price' : c.normal_price,
                                'threshold': c.threshold,
                                'phone':{
                                    'id': c.phone.id,
                                    'phone': c.phone.detail
                                },
                                'other': {'id': c.others.id,
                                          'photo': c.others.photo.file,
                                          'detail': c.others.detail,
                                          'cat': c.others.category,
                                          'ioi': c.others.is_on_invoice}
                                })
                else:
                    cat.append({'id': c.id,
                                'photo': {
                                    'file': c.photo.file,
                                    'id': c.photo.id
                                },
                                'detail': c.detail,
                                'cat': c.category,
                                'ioi': c.is_on_invoice,
                                'catalog_price' : c.normal_price,
                                'threshold': c.threshold,
                                'phone':{
                                    'id': c.phone.id,
                                    'phone': c.phone.detail
                                },
                                'other': {'id': None,
                                          'photo': None,
                                          'detail': None,
                                          'cat': None,
                                          'ioi': None}
                                })

            phone[p.model] = cat
        data['catalog'] = phone
        rt = JsonResponse(data, safe=False)
        return rt


@method_decorator(csrf_exempt, name='dispatch')
class GetAllPromo(generic.View):  # Search View
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        promos = []
        for p in Promo.objects.all().order_by('-coef'):
            promo = {'id':p.id,
                     'name': p.name,
                     'coef':p.coef}
            promos.append(promo)
        return JsonResponse(promos, safe=False)


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
class GetAllOtherCatView(generic.View):  # Search View
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        cat = []
        for oc in Category.objects.filter(is_on_invoice=False).order_by('category'):
            cat.append({'id': oc.id,
                        'cat': oc.category,
                        'detail': oc.detail})
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
        print(request.body.decode('utf8'))
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
                        try:
                            date = datetime.strptime(pm['date_paid'], '%d/%m/%Y').strftime('%Y-%m-%d')
                        except:
                            date = datetime.now()

                        payment = RepairPayment.objects.create(method=method, repair=repair, amount=pm['amount'],
                                                               id_payment=str(uuid.uuid4())[:8],
                                                               date_paid=date)
                #GenericFunctions.editPaymentStatus(repair_id=repair.id, customer_id=repair.customer.id)
                #GenericFunctions.InvoiceMaker(repair_id=repair.id, customer_id=repair.customer.id)
                data['msg'] = "done"
            else:
                data['msg'] = "Still in quoattion modify repair type"
            data['success'] = "true"


        else:
            data['success'] = "no adm"
        rt = JsonResponse(data, safe=False)
        return rt


@method_decorator(csrf_exempt, name='dispatch')
class UnPay(generic.View):  # Pay a repair
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        print(request.body.decode('utf8'))
        result = json.loads(request.body.decode('utf8'))
        data = {'token': result['token']}
        if TokenManager.IsAdmin(result['username'], result['token']):
            try:
                RepairPayment.objects.filter(id_payment=result['payment_id']).delete()
                data['success'] = "true"
            except:
                data['success'] = "false"
                data['msg'] = "erreur deleting"
        else:
            data['success'] = "no adm"
        rt = JsonResponse(data, safe=False)
        return rt


@method_decorator(csrf_exempt, name='dispatch')
class NewRepair(generic.View):  # create a repair
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        result = json.loads(request.body.decode('utf8'))
        data = {'token': result['token']}

        if TokenManager.IsAdmin(result['username'], result['token']):
            client_id = result['client_id']
            date_add = result['date_add']
            status = RepairState.objects.get(short_state='Q')
            if date_add == 'today':
                date = datetime.now()
            else:
                date = datetime.strptime(date_add, '%d/%m/%Y').strftime('%Y-%m-%d')
            client = Customer.objects.get(id=client_id)
            Repair.objects.create(customer=client, date_add=date, phone_password=None, date_repaired=None,
                                  status=status)
            data['success'] = "true"
        else:
            data['success'] = "no adm"
        rt = JsonResponse(data, safe=False)
        return rt



@method_decorator(csrf_exempt, name='dispatch')
class newClientView(generic.View):  # create a repair
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        result = json.loads(request.body.decode('utf8'))
        data = {'token': result['token']}

        if TokenManager.IsAdmin(result['username'], result['token']):
            success_newClient, client = newClient(result['firstname'],result['famillyname'],result['mail'],result['address_cp'])
            print(success_newClient)
            if success_newClient is True:
                success_newPhone, phone = newPhone(result['phone_number'], client)
                if success_newPhone is True:
                    success_newAddress, address = newAddress(result['address_no'], result['address_street'], result['address_city'],
                                         result['address_cp'], result['address_country'], client)
                    if success_newAddress is True:
                        data['success'] = "true"
                        data['msg'] = "Client créé avec succes"
                    else:
                        data['success'] = "false"
                        data['msg'] = "Verifiez l'adresse"
                        delPhone(phone.id)
                        delClient(client.id)
                else:
                    data['success'] = "false"
                    data['msg'] = "Verifiez le téléphone"
                    delClient(client.id)
            else:
                data['success'] = "false"
                data['msg'] = "Verifiez [Nom, Prenom, Mail, CP]"
        else:
            data['success'] = "no adm"
        rt = JsonResponse(data, safe=False)
        return rt


@method_decorator(csrf_exempt, name='dispatch')
class newQuotationView(generic.View):  # create a repair
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        result = json.loads(request.body.decode('utf8'))
        data = {'token': result['token']}

        if TokenManager.IsAdmin(result['username'], result['token']):
            client = Customer.objects.get(id=result['client_id'])
            repairer = User.objects.get(username=result['username'])
            success_newQuotation, quotation = newQuotation(client=client, repairer=repairer)
            print(success_newQuotation)
            if success_newQuotation is True:
                data['success'] = "true"
                data['msg'] = "Devis n°"+ quotation +" créé"
            else:
                data['success'] = "false"
                data['msg'] = "Erreur"
        else:
            data['success'] = "no adm"
        rt = JsonResponse(data, safe=False)
        return rt


@method_decorator(csrf_exempt, name='dispatch')
class AddCatToQuotationView(generic.View):  # create a repair
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        result = json.loads(request.body.decode('utf8'))
        data = {'token': result['token']}

        if TokenManager.IsAdmin(result['username'], result['token']):
            category = Category.objects.get(category=result['category'])
            quotation = Quotation.objects.get(id=result['quotation_id'])
            success_addCatToQuotation = addCatToQuotation(quotation=quotation, category=category, promo_id=result['promo_id'], sell_price=result['sell_price'])
            print(success_addCatToQuotation)
            if success_addCatToQuotation is True:
                data['success'] = "true"
                data['msg'] = "Cate ajoutée"
            else:
                data['success'] = "false"
                data['msg'] = "Erreur"
        else:
            data['success'] = "no adm"
        rt = JsonResponse(data, safe=False)
        return rt


@method_decorator(csrf_exempt, name='dispatch')
class TestIfLogedView(generic.View):  # create a repair
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        result = json.loads(request.body.decode('utf8'))
        data = {}
        username = result.get('username')
        token = result.get('token')
        if username and token:
            if TokenManager.IsAdmin(result['username'], result['token']):
                data['success'] = True
            else:
                data['success'] = False
        else:
            data['success'] = False
        rt = JsonResponse(data, safe=False)
        return rt


    #TODO delete a repair : unlink the items, delete the payments and DELETE repair itself
    #TODO add msg to json response for every functions
    #TODO create generic functions for multi used functions : unlink item, delete payments ...


@method_decorator(csrf_exempt, name='dispatch')
class simple_upload(generic.View):  # create a repair

    http_method_names = ['post', 'get']

    def get(self, request, *args, **kwargs):
        with open('app/static/adresses-13.csv') as f:
            reader = csv.reader(f, delimiter=';')
            va=0
            for row in reader:
                # row = row[0].split(';')
                va = va + 1
                print(va)
                print(row)
                _, created = FrenchAddress.objects.get_or_create(
                    id_file=row[0],
                    numero=row[2],
                    rep=row[3],
                    nom_voie=row[4],
                    code_postal=row[5],
                    code_insee=row[6],
                    nom_commune=row[7],
                    code_insee_ancienne_commune=row[8],
                    nom_ancienne_commune=row[9],
                    lon=row[12],
                    lat=row[13],
                    nom_afnor=row[17],
                )
                # creates a tuple of the new object or
                # current object and a boolean of if it was created
        #pprint(FrenchAddress.objects.get(id_file='13215_8670_00014'))
        return render(request, 'up.html')
    def post(self, request, *args, **kwargs):
        if request.FILES['myfile']:
            myfile = request.FILES['myfile']
            result = GenericFunctions.upload_img(myfile)
            if result['success']:
                print(result['file_name'])
                va = 0
                with open('app/static/'+result['file_name']) as f:
                    reader = csv.reader(f, delimiter=';')
                    for row in reader:
                        #row = row[0].split(';')
                        va = va + 1
                        print(va)
                        print(row)
                        _, created = FrenchAddress.objects.get_or_create(
                            id_file=row[0],
                            numero = row[2],
                            rep = row[3],
                            nom_voie =row[4],
                            code_postal =row[5],
                            code_insee =row[6],
                            nom_commune =row[7],
                            code_insee_ancienne_commune =row[8],
                            nom_ancienne_commune = row[9],
                            lon = row[12],
                            lat = row[13],
                            nom_afnor = row[17],
                        )
                        # creates a tuple of the new object or
                        # current object and a boolean of if it was created
                return render(request, 'up.html', {
                    'uploaded_file_url': result['file_name']
                })
            else:
                return render(request, 'up.html', {
                    'error': result['msg']
                })


@method_decorator(csrf_exempt, name='dispatch')
class ImportPhotosForCatalog(generic.View):  # create a repair

    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        if request.FILES['myfile']:
            myfile = request.FILES['myfile']
            result = GenericFunctions.upload_img(myfile)
            if result['success']:
                print(result['file_name'])
                return render(request, 'up.html', {
                    'uploaded_file_url': result['file_name']
                })
            else:
                return render(request, 'up.html', {
                    'error': result['msg']
                })


@method_decorator(csrf_exempt, name='dispatch')
class ImgView(generic.View):  # create a repair

    http_method_names = ['get']

    def get(self, request, file, *args, **kwargs):
        if Photos.objects.filter(file=file).count() == 1:
            image_data = open("app/static/img/" + file, "rb").read()
            ext = file[-4:]
            if ext == '.jpg':
                return HttpResponse(image_data, content_type="image/jpg")
            elif ext == '.png':
                return HttpResponse(image_data, content_type="image/png")
        else:
            image_data = open("app/static/img/no_img.png", "rb").read()
            return HttpResponse(image_data, content_type="image/png")


@method_decorator(csrf_exempt, name='dispatch')
class LabelsView(generic.View):  # create a repair

    http_method_names = ['get']

    def get(self, request, file, *args, **kwargs):
        if Photos.objects.filter(file=file).count() == 1:
            image_data = open("app/static/img/" + file, "rb").read()
            ext = file[-4:]
            if ext == '.jpg':
                return HttpResponse(image_data, content_type="image/jpg")
            elif ext == '.png':
                return HttpResponse(image_data, content_type="image/png")
        else:
            pdf_data = open("app/static/labels/" + file, "rb").read()
            return HttpResponse(pdf_data, content_type="application/pdf")

"""
Views for the selling website (public views)
"""

"""
Public views for getting all the products we sell
"""
@method_decorator(csrf_exempt, name='dispatch')
class GetAllCatPublic(generic.View):  # Search View
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        print(request.body.decode('utf8'))
        print(GenericFunctions.get_client_ip(request))
        result = json.loads(request.body.decode('utf8'))
        cat = []
        for c in Category.objects.filter(phone__model__contains=result['phone']).order_by('category'):
            if c.is_on_invoice:
                cat.append({'id': c.id,
                            'photo': c.photo.file,
                            'detail': c.detail,
                            'cat': c.category
                            })
        return JsonResponse(cat, safe=False)

"""
Public views for getting all the Phones
"""
@method_decorator(csrf_exempt, name='dispatch')
class GetAllPhonePublic(generic.View):  # Search View
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        phones = []
        for p in Phone.objects.all().order_by('model'):
            phones.append({'id': p.id,
                           'photo': "",
                           'detail': p.detail,
                           'model': p.model
                           })
        return JsonResponse(phones, safe=False)


@method_decorator(csrf_exempt, name='dispatch')
class ajax(generic.View):  # Search View
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        phones = []
        for p in Phone.objects.all().order_by('model'):
            phones.append({'id': p.id,
                           'photo': "",
                           'detail': p.detail,
                           'model': p.model
                           })
        return JsonResponse(phones, safe=False)