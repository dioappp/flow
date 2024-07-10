from django.shortcuts import render
from django.utils import timezone
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.forms.models import model_to_dict
from django.http import JsonResponse, HttpResponse
from ritase.models import ritase, cek_ritase
from hm.models import hmOperator
from django.db.models import Subquery, OuterRef, Q
from django.db.models.functions import Coalesce
from datetime import datetime, timedelta
from pytz import UTC
import pandas as pd
import math

# Create your views here.
def index(request):
    return render(request, 'ritase/index.html')

def load_ritase_to_db(request):
    date = request.POST.get('date')
    shift = request.POST.get('shift')

    subquery_hauler = hmOperator.objects.filter(
        equipment = OuterRef('truck_id__jigsaw'),
        login_time__lte = OuterRef('time_full'),
        logout_time__gte = OuterRef('time_full')).values('id')[:1]
    
    subquery_loader = hmOperator.objects.filter(
        equipment = OuterRef('loader_id__unit'),
        login_time__lte = OuterRef('time_full'),
        logout_time__gte = OuterRef('time_full')).values('id')[:1]
    
    data = ritase.objects.filter(
        deleted_at__isnull = True,
        report_date=date,
        shift=shift
        ).annotate(
            operator_hauler_id=Coalesce(Subquery(subquery_hauler.values('id')),None),
            operator_loader_id=Coalesce(Subquery(subquery_loader.values('id')),None)
        ).values('truck_id__jigsaw','operator_hauler_id','time_full','loader_id__unit','operator_loader_id','type','hour','report_date','shift')
    df = pd.DataFrame(list(data))
    df = df.rename(columns={'loader_id__unit':'loader','truck_id__jigsaw':'hauler'})
    result = df.groupby(['hauler','operator_hauler_id','loader','operator_loader_id','type','hour','report_date','shift'], as_index=False, dropna=False).agg({'time_full':'count'})
    result = result.pivot(index=['report_date','shift','hauler','operator_hauler_id','loader','operator_loader_id','type'], columns='hour',values='time_full').fillna(0).astype(int)
    result = result.sort_values('hauler').reset_index()



    for i, d in result.iterrows():
        cek_ritase.objects.create(
            date = d['report_date'],
            shift = d['shift'],
            hauler = d['hauler'],
            operator_hauler_id = d['operator_hauler_id'] if not math.isnan(d['operator_hauler_id']) else None,
            loader = d['loader'],
            operator_loader_id = d['operator_loader_id'] if not math.isnan(d['operator_loader_id']) else None,
            material = d['type'],
            a = d.get(6,0) if d['shift'] == 1 else d.get(18,0),  #06.30 - 07.00 | 18.00 - 19.00
            b = d.get(7,0) if d['shift'] == 1 else d.get(19,0),  #07.00 - 08.00 | 19.00 - 20.00
            c = d.get(8,0) if d['shift'] == 1 else d.get(20,0),  #08.00 - 09.00 | 20.00 - 21.00
            d = d.get(9,0) if d['shift'] == 1 else d.get(21,0),  #09.00 - 10.00 | 21.00 - 22.00
            e = d.get(10,0) if d['shift'] == 1 else d.get(22,0),  #10.00 - 11.00 | 22.00 - 23.00
            f = d.get(11,0) if d['shift'] == 1 else d.get(23,0),  #11.00 - 12.00 | 23.00 - 00.00
            g = d.get(12,0) if d['shift'] == 1 else d.get(0,0),  #12.00 - 13.00 | 00.00 - 01.00
            h = d.get(13,0) if d['shift'] == 1 else d.get(1,0),  #13.00 - 14.00 | 01.00 - 02.00
            i = d.get(14,0) if d['shift'] == 1 else d.get(2,0),  #14.00 - 15.00 | 02.00 - 03.00
            j = d.get(15,0) if d['shift'] == 1 else d.get(3,0),  #15.00 - 16.00 | 03.00 - 04.00
            k = d.get(16,0) if d['shift'] == 1 else d.get(4,0),  #16.00 - 17.00 | 04.00 - 05.00
            l = d.get(17,0) if d['shift'] == 1 else d.get(5,0),  #17.00 - 18.00 | 05.00 - 06.00
            m =           0 if d['shift'] == 1 else d.get(6,0),  #                06.00 - 06.30
        ) 
    return HttpResponse(status=204)

def operator(request):
    date = request.POST.get('date')
    shift = request.POST.get('shift')
    hauler = request.POST.get('hauler').upper()

    if shift == "1":
        ts = date + " 06:30"
        te = date + " 18:00"
    else:
        ts = date + " 18:00"
        date_date = datetime.strptime(date,"%Y-%m-%d") + timedelta(days=1)
        date_str = datetime.strftime(date_date,"%Y-%m-%d")
        te = date_str + " 06:30"
    
    ts = UTC.localize(datetime.strptime(ts,"%Y-%m-%d %H:%M"))
    te = UTC.localize(datetime.strptime(te,"%Y-%m-%d %H:%M"))

    data = hmOperator.objects.filter(
        Q(equipment = hauler),
        Q(login_time__gte=ts, login_time__lte=te) | Q(logout_time__gte=ts, logout_time__lte=te)
    ).values('id','operator','NRP','hm_start','hm_end').order_by('hm_start')
    
    response = {
        'data': list(data)
    }
    return JsonResponse(response)

def createButton(id):
    button = '<button id="delete-' + str(id) + '" data-id="' + str(id) + '" class="btn btn-icon btn-danger avtar-xs mb-0" onclick="deleteRow(this)"><i class="ti ti-minus" style="color: #FFFFFF"></div>'
    return button

def load_ritase(request):
    date = request.POST.get('date')
    shift = request.POST.get('shift')
    operator_id = request.POST.get('operator_id')

    try:
        data = cek_ritase.objects.get(
            deleted_at__isnull = True,
            date = date,
            shift = shift,
            operator_hauler_id = operator_id,
        )
        data = model_to_dict(data)
        data['action'] = createButton(data['id'])
        data_return = [data]

        response = {
            'draw': request.POST.get('draw'),
            'data': data_return
        }
        return JsonResponse(response)
    
    except MultipleObjectsReturned:
        data = cek_ritase.objects.filter(
            deleted_at__isnull = True,
            date = date,
            shift = shift,
            operator_hauler_id = operator_id,
        )
        data_return = []
        for d in data:
            x = model_to_dict(d)
            x['action'] = createButton(x['id'])
            data_return.append(x)

        response = {
            'draw': request.POST.get('draw'),
            'data': data_return,
        }    
        return JsonResponse(response)

    except ObjectDoesNotExist:
        response = {
            'draw': request.POST.get('draw'),
            'data': [],
        }    
        return JsonResponse(response)

def addrow(request):
    date = request.POST.get('date')
    shift = int(request.POST.get('shift'))
    hauler = request.POST.get('hauler').upper()
    operator_id = int(request.POST.get('id'))

    cek_ritase.objects.create(
        date=datetime.strptime(date,"%Y-%m-%d"),
        shift=shift,
        hauler=hauler,
        operator_hauler_id=operator_id,
        a=0,b=0,c=0,d=0,e=0,f=0,g=0,h=0,i=0,j=0,k=0,l=0,m=0
    )
    return HttpResponse(status=204)

def update(request):
    id = request.POST.get('id')
    col = request.POST.get('fieldName')
    val = request.POST.get('value')
    cek_ritase.objects.filter(pk=id).update(**{col:val})
    
    response = {}
    return JsonResponse(response)

def update_operator(request):
    id = int(request.POST.get('ID'))
    hm_start = float(request.POST.get('HM Start'))
    hm_end = float(request.POST.get('HM End'))

    obj = hmOperator.objects.get(pk=id)
    obj.hm_start = hm_start
    obj.hm_end = hm_end
    obj.save()

    return HttpResponse(status=204)

def delete_row(request):
    id = request.POST.get('id')
    obj = cek_ritase.objects.get(pk=id)
    obj.deleted_at = timezone.now()
    obj.save()
    return HttpResponse(status=204)
