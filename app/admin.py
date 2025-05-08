from django.contrib import admin
from .models import User, Concert, Ticket

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'isim', 'soyisim', 'mail', 'yas', 'bakiye')
    search_fields = ('isim', 'soyisim', 'mail')
    list_filter = ('yas',)

@admin.register(Concert)
class ConcertAdmin(admin.ModelAdmin):
    list_display = ('concert_id', 'konser_adi', 'tarih', 'saat', 'fiyat', 'mekan', 'sehir_id')
    search_fields = ('konser_adi', 'mekan')
    list_filter = ('sehir_id', 'tarih')

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'buyer', 'concert')
    search_fields = ('buyer__isim', 'buyer__soyisim', 'concert__konser_adi')
