import requests
import re
import json
from datetime import datetime
from db import insert_concert


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

            insert_concert(
                konser_adi=etkinlikAdi,
                sehir_id=mekan_bilgi.get("sehirId"),
                adres=mekan_bilgi.get("adres"),
                tarih=tarih_str,
                saat=saat_str,
                fiyat=fiyat,
                mekan=mekan_bilgi.get("baslik"),
                image=resim_url,
            )

    else:
        print("Etkinlik verisi alınamadı. Status:", response.status_code)


if __name__ == "__main__":
    get_events(55)
