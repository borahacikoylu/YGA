from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .db import get_connection  # varsa oradan al
import uuid

# Create your views here.


@csrf_exempt
def register_user(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)

            isim = data.get("isim")
            soyisim = data.get("soyisim")
            mail = data.get("mail")
            yas = data.get("yas")
            password = data.get("password")

            if not all([isim, soyisim, mail, yas, password]):
                return JsonResponse({"error": "Eksik veri var."}, status=400)

            conn = get_connection()
            cursor = conn.cursor(dictionary=True)

            # Kullanıcı daha önce kayıt olmuş mu?
            cursor.execute("SELECT * FROM users WHERE mail = %s", (mail,))
            if cursor.fetchone():
                return JsonResponse(
                    {"error": "Bu mail ile zaten kayıtlı kullanıcı var."}, status=409
                )

            # Yeni kullanıcı ekle
            cursor.execute(
                """
                INSERT INTO users (isim, soyisim, mail, yas, password, bakiye)
                VALUES (%s, %s, %s, %s, %s, %s)
            """,
                (isim, soyisim, mail, yas, password, 1000),
            )  # örnek bakiye 1000 TL

            conn.commit()
            return JsonResponse({"message": "Kayıt başarılı"}, status=201)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    else:
        return JsonResponse({"error": "Sadece POST destekleniyor"}, status=405)


@csrf_exempt
def login_user(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            mail = data.get("mail")
            password = data.get("password")

            if not all([mail, password]):
                return JsonResponse(
                    {"error": "Lütfen boşlukları doldurunuz!"}, status=400
                )

            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            
            # MySQL'den kullanıcı bilgilerini kontrol et
            cursor.execute(
                "SELECT * FROM users WHERE mail = %s AND password = %s",
                (mail, password),
            )
            user = cursor.fetchone()

            if user:
                # Django session'a user_id'yi kaydet
                request.session["user_id"] = user["id"]
                
                return JsonResponse(
                    {
                        "message": "Giriş başarılı",
                        "isim": user["isim"],
                        "soyisim": user["soyisim"],
                        "bakiye": user["bakiye"]
                    },
                    status=200,
                )
            else:
                return JsonResponse({"error": "Geçersiz mail veya şifre."}, status=401)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    else:
        return JsonResponse({"error": "Sadece POST destekleniyor."}, status=405)


def user_profile(request):
    user_id = request.session.get("user_id")

    if not user_id:
        return JsonResponse({"error": "Oturum bulunamadı"}, status=401)

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # 1. Kullanıcı bilgisi
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            return JsonResponse({"error": "Kullanıcı bulunamadı"}, status=404)

        # 2. Bilet bilgileri (tickets + concerts JOIN)
        cursor.execute(
            """
            SELECT c.konser_adi, c.tarih, c.saat, c.fiyat, c.mekan, c.adres
            FROM tickets t
            JOIN concerts c ON t.concert = c.concert_id
            WHERE t.buyer = %s
        """,
            (user_id,),
        )
        biletler = cursor.fetchall()

        return JsonResponse(
            {
                "isim": user["isim"],
                "soyisim": user["soyisim"],
                "mail": user["mail"],
                "yas": user["yas"],
                "bakiye": user["bakiye"],
                "biletler": biletler,  # 👈 eklenen kısım
            },
            status=200,
        )

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@csrf_exempt
def buy_ticket(request):
    if request.method == "POST":
        user_id = request.session.get("user_id")
        if not user_id:
            return JsonResponse(
                {"error": "Oturum bulunamadı. Giriş yapmalısınız."}, status=401
            )

        try:
            data = json.loads(request.body)
            concert_id = data.get("concert_id")

            if not concert_id:
                return JsonResponse({"error": "concert_id gönderilmedi"}, status=400)

            conn = get_connection()
            cursor = conn.cursor()

            # 1. Konser var mı kontrol et
            cursor.execute(
                "SELECT * FROM concerts WHERE concert_id = %s", (concert_id,)
            )
            concert = cursor.fetchone()
            if not concert:
                return JsonResponse(
                    {"error": "Geçerli bir konser bulunamadı"}, status=404
                )

            # 2. Bilet ekle
            cursor.execute(
                """
                INSERT INTO tickets (buyer, concert)
                VALUES (%s, %s)
            """,
                (user_id, concert_id),
            )

            conn.commit()
            return JsonResponse({"message": "Bilet başarıyla alındı"}, status=201)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    else:
        return JsonResponse(
            {"error": "Sadece POST isteklerine izin verilir"}, status=405
        )


@csrf_exempt
def logout_user(request):
    if request.method == "POST":
        try:
            # Session'ı temizle
            request.session.flush()
            return JsonResponse({"message": "Başarıyla çıkış yapıldı"}, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    else:
        return JsonResponse({"error": "Sadece POST destekleniyor"}, status=405)


def get_concerts(request):
    try:
        # URL'den sehir_id parametresini al
        sehir_id = request.GET.get('sehir_id')
        
        if not sehir_id:
            return JsonResponse({"error": "sehir_id parametresi gerekli"}, status=400)
            
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Konserleri sehir_id'ye göre çek
        cursor.execute("""
            SELECT concert_id, konser_adi, tarih, saat, fiyat, mekan, adres, image
            FROM concerts 
            WHERE sehir_id = %s
            ORDER BY tarih ASC
        """, (sehir_id,))
        
        konserler = cursor.fetchall()
        
        # Tarih ve saat formatını düzenle
        for konser in konserler:
            if konser['tarih']:
                # MySQL'den gelen tarihi string'e çevir
                konser['tarih'] = konser['tarih'].isoformat() if hasattr(konser['tarih'], 'isoformat') else str(konser['tarih'])
            if konser['saat']:
                # MySQL'den gelen saati string'e çevir
                konser['saat'] = konser['saat'].isoformat() if hasattr(konser['saat'], 'isoformat') else str(konser['saat'])
        
        return JsonResponse({
            "message": "Konserler başarıyla getirildi",
            "konserler": konserler
        }, status=200)
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
