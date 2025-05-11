from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ObjectDoesNotExist
from functools import wraps
import json
from .models import User, Concert, Ticket


def login_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.session.get("user_id"):
            return JsonResponse(
                {"detail": "Oturum bulunamadı. Lütfen giriş yapın.", "status": "error"},
                status=401,
            )
        return view_func(request, *args, **kwargs)

    return _wrapped_view


@csrf_exempt
@require_http_methods(["POST"])
def register_user(request):
    try:
        data = json.loads(request.body)
        if User.objects.filter(mail=data["mail"]).exists():
            return JsonResponse(
                {"detail": "Bu mail ile zaten kayıtlı kullanıcı var."}, status=409
            )

        User.objects.create(
            isim=data["isim"],
            soyisim=data["soyisim"],
            mail=data["mail"],
            yas=data["yas"],
            password=data["password"],
            bakiye=1000,
        )
        return JsonResponse({"message": "Kayıt başarılı"})
    except Exception as e:
        return JsonResponse({"detail": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def login_user(request):
    try:
        data = json.loads(request.body)
        user = User.objects.get(mail=data["mail"], password=data["password"])
        request.session["user_id"] = user.id

        return JsonResponse(
            {
                "message": "Giriş başarılı",
                "isim": user.isim,
                "soyisim": user.soyisim,
                "bakiye": user.bakiye,
            }
        )
    except ObjectDoesNotExist:
        return JsonResponse({"detail": "Geçersiz mail veya şifre."}, status=401)
    except Exception as e:
        return JsonResponse({"detail": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def user_profile(request):
    try:
        user_id = request.session.get("user_id")
        user = User.objects.get(id=user_id)
        biletler = Ticket.objects.filter(buyer=user).select_related("concert")

        bilet_listesi = [
            {
                "konser_adi": bilet.concert.konser_adi,
                "tarih": bilet.concert.tarih.isoformat(),
                "saat": bilet.concert.saat.isoformat(),
                "fiyat": bilet.concert.fiyat,
                "mekan": bilet.concert.mekan,
                "adres": bilet.concert.adres,
                "image": bilet.concert.image,
            }
            for bilet in biletler
        ]

        return JsonResponse(
            {
                "isim": user.isim,
                "soyisim": user.soyisim,
                "mail": user.mail,
                "yas": user.yas,
                "bakiye": user.bakiye,
                "biletler": bilet_listesi,
            }
        )
    except ObjectDoesNotExist:
        return JsonResponse({"detail": "Kullanıcı bulunamadı"}, status=404)
    except Exception as e:
        return JsonResponse({"detail": str(e)}, status=500)


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def change_bakiye(request):
    try:
        data = json.loads(request.body)
        amount = data.get("amount")
        if amount is None:
            return JsonResponse({"detail": "amount parametresi gerekli"}, status=400)

        user = User.objects.get(id=request.session.get("user_id"))
        if user.bakiye + amount < 0:
            return JsonResponse({"detail": "Yetersiz bakiye"}, status=400)

        user.bakiye += amount
        user.save()

        return JsonResponse(
            {"message": "Bakiye güncellendi", "yeni_bakiye": user.bakiye}
        )
    except ObjectDoesNotExist:
        return JsonResponse({"detail": "Kullanıcı bulunamadı"}, status=404)
    except Exception as e:
        return JsonResponse({"detail": str(e)}, status=500)


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def buy_ticket(request):
    try:
        data = json.loads(request.body)
        concert_id = data.get("concert_id")
        concert = Concert.objects.get(concert_id=concert_id)
        user = User.objects.get(id=request.session.get("user_id"))

        if user.bakiye < concert.fiyat:
            return JsonResponse(
                {
                    "detail": "Yetersiz bakiye",
                    "mevcut_bakiye": user.bakiye,
                    "gerekli_bakiye": concert.fiyat,
                },
                status=400,
            )

        user.bakiye -= concert.fiyat
        user.save()

        Ticket.objects.create(buyer=user, concert=concert)

        return JsonResponse(
            {
                "message": "Bilet başarıyla alındı",
                "kalan_bakiye": user.bakiye,
                "odenen_tutar": concert.fiyat,
            }
        )
    except ObjectDoesNotExist:
        return JsonResponse({"detail": "Konser bulunamadı"}, status=404)
    except Exception as e:
        return JsonResponse({"detail": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def logout_user(request):
    request.session.flush()
    return JsonResponse({"message": "Başarıyla çıkış yapıldı"})


@require_http_methods(["GET"])
def get_concerts(request):
    sehir_id = request.GET.get("sehir_id")
    if not sehir_id:
        return JsonResponse({"detail": "sehir_id gerekli"}, status=400)

    concerts = Concert.objects.filter(sehir_id=sehir_id).order_by("tarih")
    konserler = [
        {
            "concert_id": c.concert_id,
            "konser_adi": c.konser_adi,
            "tarih": c.tarih.isoformat(),
            "saat": c.saat.isoformat(),
            "fiyat": c.fiyat,
            "mekan": c.mekan,
            "adres": c.adres,
            "image": c.image,
        }
        for c in concerts
    ]

    return JsonResponse({"konserler": konserler})
