import requests
import re
import json
from datetime import datetime
import os
import django
from bs4 import BeautifulSoup
import time

# Django ayarlarını yükle
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "biletci.settings")
django.setup()

from app.models import Concert


def get_location(mekan_id: int):
    url = "https://apiv2.bubilet.com.tr/api/Mekan/GetPaging"

    payload = {"page": 0, "perPage": 999, "filterKeys": [mekan_id]}
    headers = {
        "accept": "application/json",
        "content-type": "application/json; charset=UTF-8",
    }

    response = requests.post(url, headers=headers, data=json.dumps(payload))
    if response.status_code == 200:
        response_text = response.text
        baslik = re.search(r'"baslik"\s*:\s*"([^"]+)"', response_text)
        adres = re.search(r'"adres"\s*:\s*"([^"]+)"', response_text)
        sehir_id = re.search(r'"sehirId"\s*:\s*(\d+)', response_text)

        return {
            "baslik": baslik.group(1) if baslik else None,
            "adres": adres.group(1) if adres else None,
            "sehirId": int(sehir_id.group(1)) if sehir_id else None,
        }
    else:
        return {}


def get_events(il: int):
    url = "https://apiv2.bubilet.com.tr/api/Anasayfa/6/Etkinlikler"
    headers = {
        "accept": "application/json",
        "accept-language": "tr-TR,tr;q=0.9",
        "content-type": "application/json; charset=utf-8",
        "ilid": str(il),
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        try:
            data = response.json()
        except Exception as e:
            print("JSON parse hatası:", e)
            return

        for etkinlik in data:
            etkinlikAdi = etkinlik.get("etkinlikAdi")
            mekanlar = etkinlik.get("mekanlar", [])
            mekan_id = mekanlar[0] if mekanlar else None
            mekan_bilgi = get_location(mekan_id) if mekan_id else {}

            seanslar = etkinlik.get("seanslar", [])
            fiyat = seanslar[0]["fiyat"] if seanslar else None
            tarih = seanslar[0]["tarih"] if seanslar else None

            tarih_str = None
            saat_str = None
            if tarih:
                try:
                    dt = datetime.fromisoformat(tarih.replace("Z", "+00:00"))
                    tarih_str = dt.date()
                    saat_str = dt.time()
                except Exception as e:
                    print(f"Tarih parse hatası: {e}")

            dosyalar = etkinlik.get("dosyalar", [])
            resim_url = next((d["url"] for d in dosyalar if "url" in d), None)

            try:
                if not Concert.objects.filter(
                    konser_adi=etkinlikAdi,
                    tarih=tarih_str,
                    mekan=mekan_bilgi.get("baslik"),
                ).exists():
                    Concert.objects.create(
                        konser_adi=etkinlikAdi,
                        sehir_id=mekan_bilgi.get("sehirId"),
                        adres=mekan_bilgi.get("adres"),
                        tarih=tarih_str,
                        saat=saat_str,
                        fiyat=fiyat if fiyat else 0,
                        mekan=mekan_bilgi.get("baslik"),
                        image=resim_url,
                    )
                    print(f"Yeni konser eklendi: {etkinlikAdi}")
                else:
                    print(f"Konser zaten mevcut: {etkinlikAdi}")
            except Exception as e:
                print(f"Konser ekleme hatası: {e}")

    else:
        print("Etkinlik verisi alınamadı. Status:", response.status_code)


def scrape_concerts():
    # Konserleri çek
    url = "https://www.biletix.com/anasayfa/TURKIYE/tr"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    # Konser kartlarını bul
    concert_cards = soup.find_all("div", class_="event-card")

    for card in concert_cards:
        try:
            # Konser bilgilerini çek
            konser_adi = card.find("h3").text.strip()
            mekan = card.find("div", class_="venue").text.strip()
            tarih = card.find("div", class_="date").text.strip()
            fiyat = card.find("div", class_="price").text.strip()
            image = card.find("img")["src"]

            # Fiyatı temizle ve int'e dönüştür
            fiyat = int(float(fiyat.replace("TL", "").strip()))

            # Tarihi datetime objesine çevir
            tarih_obj = datetime.strptime(tarih, "%d.%m.%Y")

            # Konser zaten var mı kontrol et
            if not Concert.objects.filter(
                konser_adi=konser_adi, tarih=tarih_obj.date(), mekan=mekan
            ).exists():
                # Yeni konser oluştur
                Concert.objects.create(
                    konser_adi=konser_adi,
                    tarih=tarih_obj.date(),
                    saat=datetime.strptime("20:00", "%H:%M").time(),  # varsayılan saat
                    mekan=mekan,
                    fiyat=fiyat,
                    image=image,
                    sehir_id=1,  # Varsayılan olarak İstanbul (1) atandı
                    adres="",  # adres bilgisi mevcut değilse boş
                )
                print(f"Yeni konser eklendi: {konser_adi}")
            else:
                print(f"Konser zaten mevcut: {konser_adi}")

        except Exception as e:
            print(f"Hata oluştu: {str(e)}")
            continue

        time.sleep(1)


if __name__ == "__main__":
    print("Bubilet konserleri çekiliyor...")

    for city_code in range(1, 83):  # Türkiye'deki 81 il (1-82 arası dahil)
        if city_code == 34:
            continue  # 34 (İstanbul) atlanacak
        get_events(city_code)

    print("Biletix konserleri çekiliyor...")
    scrape_concerts()

    print("İşlem tamamlandı!")
