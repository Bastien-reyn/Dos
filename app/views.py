import json

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.serializers import serialize
from django.http import JsonResponse
from django.shortcuts import render

# Create your views here.
from django.utils.decorators import method_decorator
from django.views import generic
from django.views.decorators.csrf import csrf_exempt

from app.models import Customer, CategoryItemPhoneRepair, Token, TokenManager


@method_decorator(csrf_exempt, name='dispatch')
class LogInView(generic.View):  # Login View : WORKING
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        result = json.loads(request.body.decode('utf8'))
        data = {'token': result['token']}
        user = authenticate(username=result['username'], password=result['password'])
        if user is not None:
            user = User.objects.get(username=result['username'])
            Token.objects.update(token=result['token'], user=user)
            data['success'] = "true"
            dt = {"firstname": user.first_name, "famillyname": user.last_name, "id": user.id, "mail": user.email}
        else:
            data['success'] = "false"
            dt = {"firstname": None, "famillyname": None, "id": None, "mail": None}
        users = [dt]
        data['user'] = users
        rt = JsonResponse(data, safe=False)
        return rt


@method_decorator(csrf_exempt, name='dispatch')
class SearchView(generic.View):  # Search View
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        result = json.loads(request.body.decode('utf8'))
        data = {'token': result['token']}
        users = []
        if TokenManager.IsAdmin(result['username'], result['token']):
            if result['action'] == 1:  # Search by mail
                for customer in Customer.objects.filter(mail__icontains=result['field']).order_by('cp', 'famillyname', 'firstname'):
                    user = {"firstname": customer.firstname, "famillyname": customer.famillyname, "id": customer.id, "mail": customer.mail, "cp": customer.cp}
                    users.append(user)

            elif result['action'] == 2:  # Search by firstname and famillyname
                for customer in Customer.objects.filter(firstname__icontains=result['field'], famillyname__icontains=result['fieldd']).order_by('cp', 'famillyname', 'firstname'):
                    user = {"firstname": customer.firstname, "famillyname": customer.famillyname, "id": customer.id,
                            "mail": customer.mail, "cp": customer.cp}
                    users.append(user)
            elif result['action'] == 3:  # Search by Order No : WORKING BUT JSON NOT RIGHT
                dt = {}
                repairs = []
                for repair in CategoryItemPhoneRepair.objects.filter(repair_id=result['field']):
                    dt['user'] = {"firstname": repair.repair.customer.firstname, "famillyname": repair.repair.customer.famillyname, "customerid": repair.repair.customer.id,
                            "customermail": repair.repair.customer.mail, "customercp": repair.repair.customer.cp}
                    repair = {"sn": repair.item.sn}
                    repairs.append(repair)
                users.append(dt)
                users.append(repairs)
            elif result['action'] == 4:  # get all customers
                for customer in Customer.objects.all().order_by('cp', 'famillyname', 'firstname'):
                    user = {"firstname": customer.firstname, "famillyname": customer.famillyname, "id": customer.id,
                            "mail": customer.mail, "cp": customer.cp}
                    users.append(user)
        else:
            data['success'] = "false"

        data['user'] = users
        rt = JsonResponse(data, safe=False)
        return rt


@method_decorator(csrf_exempt, name='dispatch')
class ModelBySnView(generic.View):
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        result = json.loads(request.body.decode('utf8'))
        print(result['arg'])
        cip = CategoryItemPhoneRepair.objects.get(item__sn=result['arg'])
        # Customer.objects.create(firstname='jacques',famillyname='rené')
        # for customer in Customer.objects.all():
        # result.append(customer.lastname)
        return JsonResponse(cip.phone.id, safe=False)
