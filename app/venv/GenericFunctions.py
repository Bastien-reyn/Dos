import uuid
from datetime import datetime

import pyinvoice
from django.core.files.storage import FileSystemStorage
from pyinvoice.models import InvoiceInfo, ServiceProviderInfo, ClientInfo, Transaction
from pyinvoice.templates import SimpleInvoice

from app.models import CategoryItemPhoneRepair, Address, PhoneNumber, Repair, Invoice, RepairPayment, RepairState, \
    Photos, Customer, Quotation, QuotationDetail


def InvoiceMaker(repair_id=None, customer_id=None):
    if repair_id is not None and customer_id is not None:
        # Declare dictionaries and arrays
        item = []
        full = {}
        # Get repair infos
        rep = Repair.objects.get(id=repair_id)
        # Get Invoice No
        invoice = Invoice.objects.get(repair=rep)
        no_invoice = f"{invoice.period}-{invoice.id:03d}"
        # Get items for this repair
        for repair in CategoryItemPhoneRepair.objects.filter(repair__customer_id=customer_id, repair_id=repair_id):
            if repair.custom_price == 0:
                price = repair.category.normal_price
            else:
                price = repair.custom_price
            print(repair.category.normal_price)
            print(repair.custom_price)
            dt = {"sn": repair.item.sn,
                  'cat': repair.category.category,
                  'price': price,
                  'prix': repair.category.normal_price,
                  'caption': repair.category.detail}
            item.append(dt)
            full['usr'] = repair.repair.customer
        full['pcs'] = item
        # Create the invoice pdf
        doc = SimpleInvoice('app/static/Facture-' + no_invoice + '.pdf')

        try:
            address = Address.objects.get(customer=full['usr'])
            print(address)
        except Address.DoesNotExist:
            address = Address.objects
            address.no = ""
            address.street = ""
            address.city = ""
            address.cp = ""
            address.country = ""

        try:
            phone = PhoneNumber.objects.get(customer=full['usr'])
            phone = phone.no_phone
        except PhoneNumber.DoesNotExist:
            phone = "0000000000"

        # TODO Make invoice and quotation
        # if full['state'].short_state == "Q":
        #     type = "Devis"
        # elif full['state'].short_state == "HF" or full['state'].short_state == "P":
        #     type = "Facture"

        doc.invoice_info = InvoiceInfo(no_invoice, rep.date_repaired, datetime.now().date())  # Invoice info, optional

        if rep.status.short_state == 'P':
            doc.is_paid = True
        else:
            doc.is_paid = False
        # Company Info, optional
        doc.service_provider_info = ServiceProviderInfo(
            name='SARL Hinna',
            street='70 Rue de la coquillarde, Espace Eole, Hall A',
            phone='06 66 69 65 56',
            city='Puyricard',
            state='PACA',
            country='France',
            post_code='13540',
            vat_tax_number='FR 71 879062552',
            siren="879 062 552 R.C.S. Aix-en-Provence",
            capital="1 000,00 Euros",
            denomination="Société à responsabilité limitée (SARL)",
            formated_address='70 Rue de la coquillarde,<br/> Espace Eole, Hall A, <br/>13540 Puyricard, France',
            email='client@example.com',
        )
        # Client info, optional
        t = iter(phone)
        nophone = ' '.join(a + b for a, b in zip(t, t))
        doc.client_info = ClientInfo(
            email=full['usr'].mail + 'ff',
            name=full['usr'].famillyname.capitalize() + " " + full['usr'].firstname.capitalize(),
            street=address.no + ' ' + address.street,
            city=address.city,
            country=address.country,
            post_code=address.cp,
            client_id=f"{full['usr'].id:03d}",
            phone=nophone
        )

        # Add Items
        for i in item:
            i['caption'] = "<br />".join(i['caption'].split("\n"))
            doc.add_item(pyinvoice.models.Item(1, i['caption'], i['sn'], i['prix'], i['prix']))

        # TVA
        doc.set_item_tax_rate(20)  # 20%

        # Payments details
        for p in RepairPayment.objects.filter(repair=rep):
            doc.add_transaction(
                Transaction(transaction_id=p.id_payment, gateway=p.method.method, transaction_datetime=p.date_paid,
                            amount=p.amount))

        # Footer
        doc.set_bottom_tip('<para>' + doc.service_provider_info.name +
                           '<br/>' + doc.service_provider_info.formated_address +
                           '<br/>' + doc.service_provider_info.email +
                           '<br/>TVA Intracommunautaire : ' + doc.service_provider_info.vat_tax_number +
                           '<br/>' + doc.service_provider_info.denomination +
                           ' Au capital de ' + doc.service_provider_info.capital +
                           ' - ' + doc.service_provider_info.siren +
                           '<br/> Le défaut de paiement total ou partiel à la date d\'échéance indiquée sur la facture fera courir de façon automatique des intérêts, dès le premier jour de retard, au taux d\'intérêt légal. La totalité des frais de recouvrement demeureront à la charge du client débiteur. Aucun escompte ne sera pratiqué en cas de paiement anticipé.' +
                           '<br/>Facture éditée le ' + str(datetime.now().date()) +
                           '</para>')

        doc.finish()
        return True


def editPaymentStatus(repair_id=None, customer_id=None):
    total = total_payment = 0
    for i in CategoryItemPhoneRepair.objects.filter(repair_id=repair_id):
        total += i.category.normal_price
    ttc = total * 1.2
    for pp in RepairPayment.objects.filter(repair_id=repair_id):
        total_payment += float(pp.amount.replace(',', '.'))
    if ttc == total_payment and ttc + total_payment != 0:
        state = RepairState.objects.get(short_state="P")
    elif total_payment != 0 and ttc < total_payment:
        state = RepairState.objects.get(short_state="T")
    elif total_payment != 0 and ttc != total_payment:
        state = RepairState.objects.get(short_state="HP")
    else:
        state = RepairState.objects.get(short_state="A")
    Repair.objects.filter(id=repair_id).update(status=state)
    try:
        invoice = Invoice.objects.get(repair_id=repair_id)
        Invoice.objects.filter(repair_id=repair_id).update(due=ttc - total_payment)
    except Invoice.DoesNotExist:
        invoice = Invoice.objects.create(repair_id=repair_id, due=ttc - total_payment)


def upload_img(uploaded_file):
    ext = uploaded_file.name[-4:]
    if ext == '.png' or ext == '.jpg':
        fs = FileSystemStorage(location='app/static/img/')
        filename = fs.save(str(uuid.uuid4())[:8] + ext, uploaded_file)
        uploaded_file_url = 'img/' + filename
        Photos.objects.create(file=filename)
        return {'success': True,
                'file_name': uploaded_file_url,
                'msg': 'File uploaded'}
    else:
        return {'success': False,
                'msg': 'Bad file extension'}


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


"""
——————————————————————————————————————
Get DB entry(ies)
——————————————————————————————————————
"""

def getClientAddress(client_id):
    return Address.objects.get(customer_id=client_id)


"""
——————————————————————————————————————
Create DB entry
——————————————————————————————————————
"""


def newAddress(no, street, city, cp, country, client):
    # TODO make all the verifications
    try:
        address = Address.objects.create(no=no, street=street, city=city, cp=cp, country=country, customer=client)
        return True, address
    except:
        return False, None


def newPhone(no, client):
    # TODO make all the verifications
    try:
        phone_number = PhoneNumber.objects.create(no_phone=no, customer=client)
        return True, phone_number
    except:
        return False, None


def newClient(firstname, famillyname, mail, cp):
    # TODO make all the verifications
    try:
        today = datetime.now()
        client = Customer.objects.create(firstname=firstname, famillyname=famillyname, mail=mail, cp=cp, date_signup=today)
        return True, client
    except:
        print(Exception)
        return False, None


def newQuotation(client, repairer):
    # TODO make all the verifications
    try:
        today = datetime.now()
        quotation = Quotation.objects.create(customer=client, repairer=repairer, date_add=today)
        return True, quotation
    except:
        print(Exception)
        return False, None


def addCatToQuotation(category, quotation, promo_id, sell_price):
    # TODO make all the verifications
    try:
        QuotationDetail.objects.create(quotation=quotation, category=category, sell_promo_id=promo_id, sell_price=sell_price)
        return True
    except:
        print(Exception)
        return False

"""
——————————————————————————————————————
Delete DB entry
——————————————————————————————————————
"""


def delAddress(address_id):
    # TODO make all the verifications
    try:
        address = Address.objects.get(id=address_id).delete()
        return True
    except:
        return False


def delPhone(phone_number_id):
    # TODO make all the verifications
    try:
        PhoneNumber.objects.get(id=phone_number_id).delete()
        return True
    except:
        return False


def delClient(client_id):
    # TODO make all the verifications
    try:
        today = datetime.now()
        client = Customer.objects.get(id=client_id).delete()
        return True
    except:
        return False


