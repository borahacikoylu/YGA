from django.db import models


class User(models.Model):
    isim = models.CharField(max_length=100)
    soyisim = models.CharField(max_length=100)
    mail = models.EmailField(unique=True)
    yas = models.IntegerField()
    password = models.CharField(max_length=100)
    bakiye = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.isim} {self.soyisim}"


class Concert(models.Model):
    concert_id = models.AutoField(primary_key=True)
    konser_adi = models.CharField(max_length=200)
    sehir_id = models.IntegerField()
    adres = models.CharField(max_length=255)
    tarih = models.DateField()
    saat = models.TimeField()
    fiyat = models.IntegerField()
    mekan = models.CharField(max_length=200)
    image = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.konser_adi


class Ticket(models.Model):
    buyer = models.ForeignKey(User, on_delete=models.CASCADE)
    concert = models.ForeignKey(Concert, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.buyer} - {self.concert}"
