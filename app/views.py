from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ObjectDoesNotExist
from functools import wraps
import json
from .models import User, Concert, Ticket, Comment
from datetime import date, timedelta


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
                "concert_id": bilet.concert.concert_id,
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

    konserler = []
    for c in concerts:
        comments = c.comments.select_related("user").all()
        yorumlar = [
            {
                "kullanici": f"{comment.user.isim} {comment.user.soyisim}",
                "yorum": comment.content,
                "tarih": comment.created_at.isoformat(),
            }
            for comment in comments
        ]

        konserler.append(
            {
                "concert_id": c.concert_id,
                "konser_adi": c.konser_adi,
                "tarih": c.tarih.isoformat(),
                "saat": c.saat.isoformat(),
                "fiyat": c.fiyat,
                "mekan": c.mekan,
                "adres": c.adres,
                "image": c.image,
                "yorumlar": yorumlar,
            }
        )

    return JsonResponse({"konserler": konserler})


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def add_comment(request):
    try:
        data = json.loads(request.body)

        concert_id = data.get("concert_id")
        content = data.get("content")

        if not concert_id or not content:
            return JsonResponse(
                {"detail": "concert_id ve content zorunludur"}, status=400
            )

        try:
            concert = Concert.objects.get(concert_id=concert_id)
        except Concert.DoesNotExist:
            return JsonResponse({"detail": "Konser bulunamadı"}, status=404)

        user_id = request.session.get("user_id")
        user = User.objects.get(id=user_id)

        Comment.objects.create(user=user, concert=concert, content=content)

        return JsonResponse({"detail": "Yorum başarıyla eklendi"}, status=201)

    except json.JSONDecodeError:
        return JsonResponse({"detail": "Geçersiz JSON formatı"}, status=400)
    except Exception as e:
        return JsonResponse({"detail": str(e)}, status=500)


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def cancel_ticket(request):
    try:
        data = json.loads(request.body)
        concert_id = data.get("concert_id")

        if not concert_id:
            return JsonResponse({"detail": "concert_id gerekli"}, status=400)

        user = User.objects.get(id=request.session.get("user_id"))

        try:
            concert = Concert.objects.get(concert_id=concert_id)
        except Concert.DoesNotExist:
            return JsonResponse({"detail": "Konser bulunamadı"}, status=404)

        try:
            ticket = Ticket.objects.get(buyer=user, concert=concert)
        except Ticket.DoesNotExist:
            return JsonResponse({"detail": "Böyle bir bilet bulunamadı"}, status=404)

        # 🔒 İptal için tarih kontrolü
        today = date.today()
        if concert.tarih <= today + timedelta(days=1):
            return JsonResponse(
                {"detail": "Konser tarihi yaklaştığı için bilet iptal edilemez"},
                status=400,
            )

        # Bileti sil
        ticket.delete()

        # Bakiyeyi iade et
        user.bakiye += concert.fiyat
        user.save()

        return JsonResponse(
            {
                "message": "Bilet başarıyla iptal edildi",
                "iade_edilen_tutar": concert.fiyat,
                "guncel_bakiye": user.bakiye,
            }
        )

    except json.JSONDecodeError:
        return JsonResponse({"detail": "Geçersiz JSON formatı"}, status=400)
    except Exception as e:
        return JsonResponse({"detail": str(e)}, status=500)


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def update_user_info(request):
    try:
        data = json.loads(request.body)
        yeni_isim = data.get("isim")
        yeni_soyisim = data.get("soyisim")

        if not yeni_isim or not yeni_soyisim:
            return JsonResponse(
                {"detail": "isim ve soyisim alanları zorunludur"}, status=400
            )

        user = User.objects.get(id=request.session.get("user_id"))
        user.isim = yeni_isim
        user.soyisim = yeni_soyisim
        user.save()

        return JsonResponse(
            {
                "message": "Kullanıcı bilgileri güncellendi",
                "isim": user.isim,
                "soyisim": user.soyisim,
            }
        )

    except json.JSONDecodeError:
        return JsonResponse({"detail": "Geçersiz JSON formatı"}, status=400)
    except Exception as e:
        return JsonResponse({"detail": str(e)}, status=500)
