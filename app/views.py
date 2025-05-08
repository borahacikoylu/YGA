from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ObjectDoesNotExist
from functools import wraps
import json
import uuid
from .models import User, Concert, Ticket
from datetime import datetime

def login_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.session.get('user_id'):
            return JsonResponse({
                "detail": "Oturum bulunamadı. Lütfen giriş yapın.",
                "status": "error"
            }, status=401)
        return view_func(request, *args, **kwargs)
    return _wrapped_view

# Create your views here.


@csrf_exempt
@require_http_methods(["POST"])
def register_user(request):
    try:
        data = json.loads(request.body)
        # Kullanıcı kontrolü
        if User.objects.filter(mail=data['mail']).exists():
            return JsonResponse({"detail": "Bu mail ile zaten kayıtlı kullanıcı var."}, status=409)
        
        # Yeni kullanıcı oluştur
        user = User.objects.create(
            isim=data['isim'],
            soyisim=data['soyisim'],
            mail=data['mail'],
            yas=data['yas'],
            password=data['password'],
            bakiye=1000
        )
        return JsonResponse({"message": "Kayıt başarılı"})
    except Exception as e:
        return JsonResponse({"detail": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def login_user(request):
    try:
        data = json.loads(request.body)
        user = User.objects.get(mail=data['mail'], password=data['password'])
        
        # Session'a user_id'yi kaydet
        request.session['user_id'] = user.id
        
        return JsonResponse({
            "message": "Giriş başarılı",
            "isim": user.isim,
            "soyisim": user.soyisim,
            "bakiye": user.bakiye,
            "user_id": user.id
        })
    except ObjectDoesNotExist:
        return JsonResponse({"detail": "Geçersiz mail veya şifre."}, status=401)
    except Exception as e:
        return JsonResponse({"detail": str(e)}, status=500)


@require_http_methods(["GET"])
@login_required
def user_profile(request, user_id):
    try:
        # Session'daki user_id ile istenen user_id'yi karşılaştır
        if request.session.get('user_id') != user_id:
            return JsonResponse({
                "detail": "Bu profili görüntüleme yetkiniz yok.",
                "status": "error"
            }, status=403)
            
        user = User.objects.get(id=user_id)
        biletler = Ticket.objects.filter(buyer=user).select_related('concert')
        
        bilet_listesi = []
        for bilet in biletler:
            bilet_listesi.append({
                "konser_adi": bilet.concert.konser_adi,
                "tarih": bilet.concert.tarih,
                "saat": bilet.concert.saat,
                "fiyat": bilet.concert.fiyat,
                "mekan": bilet.concert.mekan,
                "adres": bilet.concert.adres
            })
        
        return JsonResponse({
            "isim": user.isim,
            "soyisim": user.soyisim,
            "mail": user.mail,
            "yas": user.yas,
            "bakiye": user.bakiye,
            "biletler": bilet_listesi
        })
    except ObjectDoesNotExist:
        return JsonResponse({"detail": "Kullanıcı bulunamadı"}, status=404)
    except Exception as e:
        return JsonResponse({"detail": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def change_bakiye(request, user_id):
    try:
        # Session'daki user_id ile istenen user_id'yi karşılaştır
        if request.session.get('user_id') != user_id:
            return JsonResponse({
                "detail": "Bu işlemi yapma yetkiniz yok.",
                "status": "error"
            }, status=403)
            
        data = json.loads(request.body)
        amount = data.get("amount")

        if amount is None:
            return JsonResponse({"detail": "amount parametresi gerekli"}, status=400)

        user = User.objects.get(id=user_id)
        new_balance = user.bakiye + amount

        if new_balance < 0:
            return JsonResponse({"detail": "Yetersiz bakiye"}, status=400)

        user.bakiye = new_balance
        user.save()

        return JsonResponse({
            "message": "Bakiye güncellendi",
            "yeni_bakiye": new_balance
        })

    except ObjectDoesNotExist:
        return JsonResponse({"detail": "Kullanıcı bulunamadı"}, status=404)
    except Exception as e:
        return JsonResponse({"detail": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def buy_ticket(request, user_id):
    try:
        # Session'daki user_id ile istenen user_id'yi karşılaştır
        if request.session.get('user_id') != user_id:
            return JsonResponse({
                "detail": "Bu işlemi yapma yetkiniz yok.",
                "status": "error"
            }, status=403)
            
        data = json.loads(request.body)
        concert_id = data['concert_id']
        
        # Konser ve kullanıcı bilgilerini al
        concert = Concert.objects.get(concert_id=concert_id)
        user = User.objects.get(id=user_id)
        
        # Bakiye kontrolü
        if user.bakiye < concert.fiyat:
            return JsonResponse({
                "detail": "Yetersiz bakiye",
                "mevcut_bakiye": user.bakiye,
                "gerekli_bakiye": concert.fiyat
            }, status=400)
        
        # Bakiyeyi güncelle
        user.bakiye -= concert.fiyat
        user.save()
        
        # Bilet oluştur
        Ticket.objects.create(buyer=user, concert=concert)
        
        return JsonResponse({
            "message": "Bilet başarıyla alındı",
            "kalan_bakiye": user.bakiye,
            "odenen_tutar": concert.fiyat
        })
    except ObjectDoesNotExist:
        return JsonResponse({"detail": "Geçerli bir konser veya kullanıcı bulunamadı"}, status=404)
    except Exception as e:
        return JsonResponse({"detail": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def logout_user(request):
    try:
        # Session'ı temizle
        request.session.flush()
        return JsonResponse({
            "message": "Başarıyla çıkış yapıldı",
            "status": "success"
        })
    except Exception as e:
        return JsonResponse({
            "detail": str(e),
            "status": "error"
        }, status=500)


@require_http_methods(["GET"])
def get_concerts(request):
    try:
        # URL'den sehir_id parametresini al
        sehir_id = request.GET.get('sehir_id')
        
        if not sehir_id:
            return JsonResponse({"detail": "sehir_id parametresi gerekli"}, status=400)
            
        # Konserleri sehir_id'ye göre çek
        konserler = Concert.objects.filter(sehir_id=sehir_id).order_by('tarih')
        
        # Konserleri JSON formatına dönüştür
        konser_listesi = []
        for konser in konserler:
            konser_listesi.append({
                "concert_id": konser.concert_id,
                "konser_adi": konser.konser_adi,
                "tarih": konser.tarih.isoformat() if konser.tarih else None,
                "saat": konser.saat.isoformat() if konser.saat else None,
                "fiyat": konser.fiyat,
                "mekan": konser.mekan,
                "adres": konser.adres,
                "image": konser.image
            })
        
        return JsonResponse({
            "message": "Konserler başarıyla getirildi",
            "konserler": konser_listesi
        })
        
    except Exception as e:
        return JsonResponse({"detail": str(e)}, status=500)
