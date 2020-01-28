"""Dos URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the† include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path

from app.views import SearchView, LogInView, AddStockView, AddressesByCustomerView, RepairByCustomerView, GetLabels, \
    AddItem, GetAllStockView, GetAllCat, Pay, GetAllPhoneModel, AddOrUpdateCatalogEntryView, AddPhoneView, \
    GetAllUserInfos, GetAllUserRepairs, GetSpecificCat, GetItemFromCatInStock, GetItemFromRepair, GetPaymentFromRepair, \
    GetAllPaymentMethod, GenerateInvoice, EditPaymentStatus, GetInfoFromRepair, LinkItemToRepair, UnPay, \
    UnLinkItemToRepair, NewRepair, simple_upload, GetAllPromo, GetAllCatPublic, GetAllPhonePublic, newClientView, \
    newQuotationView, GetQuotationListByUser, AddCatToQuotationView, GetQuotationDetailView, TestIfLogedView, ImgView, \
    GetAllOtherCatView, LabelsView, ajax

urlpatterns = [
    path('admin/', admin.site.urls),
    path('search', SearchView.as_view()),
    path('addstock', AddStockView.as_view()),
    path('customeraddresses', AddressesByCustomerView.as_view()),
    path('customerrepair', RepairByCustomerView.as_view()),
    path('getlabelpdf', GetLabels.as_view()),
    path('additem', AddItem.as_view()),
    path('stock', GetAllStockView.as_view()),
    path('getallcat', GetAllCat.as_view()),
    path('invoice', GenerateInvoice.as_view()),
    path('paymentstatus', EditPaymentStatus.as_view()),
    path('pay', Pay.as_view()),
    path('unpay', UnPay.as_view()),
    path('getallphone', GetAllPhoneModel.as_view()),
    path('addorupdatecatalogentry', AddOrUpdateCatalogEntryView.as_view()),
    path('addphone', AddPhoneView.as_view()),
    path('getalluserinfo', GetAllUserInfos.as_view()),
    path('getallpaymentmethod', GetAllPaymentMethod.as_view()),
    path('getalluserrepair', GetAllUserRepairs.as_view()),
    path('getspecificcat', GetSpecificCat.as_view()),
    path('getitemfromcat', GetItemFromCatInStock.as_view()),
    path('getitemfromrepair', GetItemFromRepair.as_view()),
    path('getinfofromrepair', GetInfoFromRepair.as_view()),
    path('getpaymentfromrepair', GetPaymentFromRepair.as_view()),
    path('linkitemtorepair', LinkItemToRepair.as_view()),
    path('unlinkitemtorepair', UnLinkItemToRepair.as_view()),
    path('newrepair', NewRepair.as_view()),
    path('simple_upload', simple_upload.as_view()),
    path('getallpromo', GetAllPromo.as_view()),
    path('getcatbyphone', GetAllCatPublic.as_view()),
    path('getallphones', GetAllPhonePublic.as_view()),
    # createing things
    path('newclient', newClientView.as_view()),
    path('newquotation', newQuotationView.as_view()),
    # getting data
    path('getquotationlistbyuser', GetQuotationListByUser.as_view()),
    path('addcattoquotation', AddCatToQuotationView.as_view()),
    path('getquotationdetail', GetQuotationDetailView.as_view()),
    path('getallothercat', GetAllOtherCatView.as_view()),
    # User Views
    path('login', LogInView.as_view()),
    path('testifloged', TestIfLogedView.as_view()),


    path('ajax', ajax.as_view()),
    # IMG
    path('img/<file>', ImgView.as_view()),
    path('label/<file>', LabelsView.as_view()),

]
